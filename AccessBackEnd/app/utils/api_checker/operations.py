from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
import secrets

from flask import current_app, jsonify, request, session
from flask_login import current_user
from sqlalchemy import and_, or_

from ...api.errors import BadRequestError, NotFoundError
from ...extensions import db
from ...models import Accommodation, Chat, CourseClass, Message, Note, SystemPrompt, User, UserClassEnrollment, UserSession
from ...models.identity import Role
from ...utils.chat_access import ChatAccessHelper
from ...services.logging import DomainEvent
from .validator import api_monolith_helper


class AuthOps:
    TEMP_ROLE_ACTION_POLICY: dict[str, list[str]] = {
        Role.ADMIN.value: ["users:read", "users:write", "classes:read", "classes:write", "classes:delete"],
        Role.INSTRUCTOR.value: ["classes:read", "classes:write", "students:read"],
        Role.STUDENT.value: ["classes:read", "profile:read", "profile:write"],
    }
    FALLBACK_ALLOWED_ACTIONS: list[str] = ["profile:read"]

    @staticmethod
    def normalize_auth_email(value: str | None) -> str:
        return (value or "").strip().lower()


    @staticmethod
    def _normalize_auth_email(value: str | None) -> str:
        return AuthOps.normalize_auth_email(value)

    @staticmethod
    def _resolve_session_timetolive() -> timedelta:
        return AuthOps.resolve_session_timetolive()

    @staticmethod
    def _as_utc(value: datetime | None) -> datetime | None:
        return AuthOps.as_utc(value)

    @staticmethod
    def _resolved_allowed_actions(user_role: str) -> list[str]:
        return AuthOps.resolved_allowed_actions(user_role)
    @staticmethod
    def resolve_session_timetolive() -> timedelta:
        ttl_value = current_app.config.get("JWT_ACCESS_TOKEN_EXPIRES")
        if isinstance(ttl_value, timedelta):
            return ttl_value
        if isinstance(ttl_value, (int, float)):
            return timedelta(minutes=float(ttl_value))
        return timedelta(minutes=30)

    @staticmethod
    def as_utc(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @staticmethod
    def revoke_session_record(session_id: int | None) -> None:
        if not session_id:
            return
        session_record = db.session.get(UserSession, int(session_id))
        if session_record is None:
            return
        now = datetime.now(UTC)
        revoked_at = AuthOps.as_utc(session_record.revoked_at)
        if revoked_at is not None and revoked_at <= now:
            return
        session_record.revoked_at = now
        db.session.commit()

    @staticmethod
    def create_user_session(*, user_id: int) -> UserSession:
        now = datetime.now(UTC)
        ttl = AuthOps.resolve_session_timetolive()
        session_record = UserSession(
            user_id=user_id,
            token_hash=secrets.token_urlsafe(48),
            expires_at=now + ttl,
            last_seen_at=now,
            revoked_at=datetime.max.replace(tzinfo=UTC),
        )
        db.session.add(session_record)
        db.session.flush()
        return session_record

    @staticmethod
    def revoke_flask_session_lifecycle_record() -> None:
        AuthOps.revoke_session_record(session.get("auth_session_id"))

    @staticmethod
    def unauthorized_auth_envelope(message: str, *, details: dict | None = None):
        return jsonify({"error": {"code": "unauthorized", "message": message, "details": details or {}}}), 401

    @staticmethod
    def resolved_allowed_actions(user_role: str) -> list[str]:
        role_val = (user_role or "").strip().lower()
        try:
            configured_policy = current_app.config.get("AUTH_ROLE_ACTION_POLICY")
        except RuntimeError:
            configured_policy = None
        policy_source = configured_policy if isinstance(configured_policy, dict) else AuthOps.TEMP_ROLE_ACTION_POLICY
        normalized_policy: dict[str, list[str]] = {}
        for role_name, allowed_actions in policy_source.items():
            normalized_role = str(role_name or "").strip().lower()
            if not normalized_role or not isinstance(allowed_actions, list):
                continue
            normalized_policy[normalized_role] = [str(action).strip() for action in allowed_actions if str(action or "").strip()]
        return normalized_policy.get(role_val, AuthOps.FALLBACK_ALLOWED_ACTIONS.copy())

    @staticmethod
    def resolve_authenticated_session_state() -> tuple[UserSession | None, datetime, tuple | None]:
        this_time = datetime.now(UTC)
        if not current_user.is_authenticated:
            return None, this_time, AuthOps.unauthorized_auth_envelope("authentication required")
        persisted_session_id = session.get("auth_session_id")
        if not persisted_session_id:
            return None, this_time, AuthOps.unauthorized_auth_envelope("session not found", details={"reason": "missing session ID"})
        session_record = db.session.get(UserSession, int(persisted_session_id))
        if session_record is None:
            return None, this_time, AuthOps.unauthorized_auth_envelope("session not found", details={"reason": "missing session record"})
        if int(session_record.user_id) != int(current_user.id):
            return None, this_time, AuthOps.unauthorized_auth_envelope("session user mismatch", details={"reason": "session user mismatch"})
        revoked_at = AuthOps.as_utc(session_record.revoked_at)
        if revoked_at is not None and revoked_at <= this_time:
            return None, this_time, AuthOps.unauthorized_auth_envelope("session revoked", details={"reason": "revoked", "revoked_at": f"{revoked_at}"})
        expires_at = AuthOps.as_utc(session_record.expires_at)
        if expires_at and expires_at <= this_time:
            session_record.revoked_at = this_time
            db.session.commit()
            return None, this_time, AuthOps.unauthorized_auth_envelope("session expired", details={"reason": "expired", "expires_at": f"{expires_at}"})
        return session_record, this_time, None


def _user_context_payload() -> dict[str, Any]:
    return {"id": current_user.id, "email": current_user.email, "role": current_user.role}


def _deserialize_payload(resource: str, payload: dict[str, Any]) -> dict[str, Any]:
    return api_monolith_helper.deserialize(resource, payload)


def _validate_payload(payload: dict[str, Any], schema: Any) -> dict[str, Any]:
    return api_monolith_helper.validate(payload, schema)


def _serialize_record(resource: str, record: Any) -> dict[str, Any]:
    if resource in {"chat", "message", "note"}:
        return api_monolith_helper.serialize(resource, record)
    if resource == "class":
        return {"id": record.id, "name": record.name, "description": record.description, "instructor_id": record.instructor_id, "active": record.active}
    if resource == "feature":
        return {"id": record.id, "title": record.title, "details": record.details, "active": record.active, "description": record.details, "enabled": record.active}
    if resource == "ai_interaction":
        created_at = record.created_at.isoformat() if getattr(record, "created_at", None) else None
        return {
            "id": record.id,
            "chat_id": record.chat_id,
            "prompt": record.prompt,
            "response_text": record.response_text,
            "ai_model_id": record.ai_model_id,
            "provider": record.ai_model.provider if getattr(record, "ai_model", None) else None,
            "accommodations_id_system_prompts_id": record.accommodations_id_system_prompts_id,
            "created_at": created_at,
        }
    if resource == "system_prompt":
        return {"id": record.id, "text": record.text, "class_id": record.class_id, "instructor_id": record.instructor_id}
    if resource == "accommodation_system_prompt_link":
        return {
            "id": record.id,
            "accommodation_id": record.accommodation_id,
            "system_prompt_id": record.system_prompt_id,
            "accommodation_title": record.accommodation.title if getattr(record, "accommodation", None) else None,
            "system_prompt_text": record.system_prompt.text if getattr(record, "system_prompt", None) else None,
        }
    return {}


def _publish(event_name: str, payload: dict[str, Any] | None = None) -> None:
    current_app.extensions["event_bus"].publish(DomainEvent(event_name, payload or {}))


def _read_json_object() -> dict[str, Any]:
    payload = request.get_json(silent=True)
    if payload is None:
        raise BadRequestError("json body required")
    if not isinstance(payload, dict):
        raise BadRequestError("json object body required")
    return payload


def _forbidden_response(message: str = "access denied"):
    return jsonify({"error": {"code": "forbidden", "message": message, "details": {}}}), 403


def _raise_bad_request_from_exception(exc: Exception, *, source: str | None = None, message: str | None = None) -> None:
    details = {"exception": exc.__class__.__name__}
    if source:
        details["source"] = source
    raise BadRequestError(message or str(exc), details=details) from exc


def _parse_optional_datetime(value: Any) -> datetime | None:
    return api_monolith_helper.parse_optional_datetime(value, "started_at")


def _parse_required_date(value: Any, *, field_name: str = "noted_on"):
    return api_monolith_helper.parse_required_date(value, field_name)


def _resolve_default_class_id_for_user(user_id: int) -> int | None:
    class_record = (
        db.session.query(CourseClass)
        .outerjoin(UserClassEnrollment, UserClassEnrollment.class_id == CourseClass.id)
        .filter(
            or_(
                CourseClass.instructor_id == user_id,
                and_(UserClassEnrollment.user_id == user_id, UserClassEnrollment.active.is_(True)),
            )
        )
        .order_by(CourseClass.id.asc())
        .first()
    )
    return None if class_record is None else int(class_record.id)


def _parse_int_field(value: Any, *, field_name: str, required: bool = False) -> int | None:
    return api_monolith_helper.parse_int(value, field_name, required=required)


def _assert_chat_permissions(chat: Any) -> tuple[dict[str, Any], int] | None:
    user_id = ChatAccessHelper.get_authenticated_user_id()
    if chat.user_id != user_id:
        return _forbidden_response()
    return None


def _require_record(resource_name: str, model: Any, record_id: int) -> Any:
    record = db.session.get(model, record_id)
    if record is None:
        raise NotFoundError(f"{resource_name} not found", details={"id": record_id})
    return record


def _apply_field_updates(record: Any, payload: dict[str, Any], fields: tuple[str, ...]) -> None:
    api_monolith_helper.apply_updates(record, payload, set(fields))


def _apply_chat_mutations(chat: Chat, payload: dict[str, Any]) -> None:
    if "class_id" in payload:
        class_record = _require_record("class", CourseClass, int(payload["class_id"]))
        chat.class_id = int(class_record.id)
    if "user_id" in payload:
        _require_record("user", User, int(payload["user_id"]))
        chat.user_id = int(payload["user_id"])
    api_monolith_helper.apply_updates(chat, payload, {"title", "model"})
    if "started_at" in payload:
        parsed = _parse_optional_datetime(payload["started_at"])
        if parsed is not None:
            chat.started_at = parsed


def _apply_message_mutations(message: Message, payload: dict[str, Any]) -> None:
    if "chat_id" in payload:
        _require_record("chat", Chat, int(payload["chat_id"]))
        message.chat_id = int(payload["chat_id"])
    api_monolith_helper.apply_updates(message, payload, {"message_text", "vote", "note", "help_intent"})


def _apply_note_mutations(note: Note, payload: dict[str, Any]) -> None:
    if "class_id" in payload:
        _require_record("class", CourseClass, int(payload["class_id"]))
        note.class_id = int(payload["class_id"])
    if "chat_id" in payload:
        chat = _require_record("chat", Chat, int(payload["chat_id"]))
        deny = _assert_chat_permissions(chat)
        if deny is not None:
            raise BadRequestError("chat id is not accessible")
        note.chat_id = int(payload["chat_id"])
    if "noted_on" in payload:
        note.noted_on = _parse_required_date(payload["noted_on"], field_name="noted_on")
    if "content" in payload:
        note.content = str(payload["content"] or "").strip()


def _apply_class_mutations(class_record: CourseClass, payload: dict[str, Any]) -> None:
    api_monolith_helper.apply_updates(class_record, payload, {"name", "description", "active"})
    if "instructor_id" in payload:
        _require_record("user", User, int(payload["instructor_id"]))
        class_record.instructor_id = int(payload["instructor_id"])


def _apply_feature_mutations(feature: Accommodation, payload: dict[str, Any]) -> None:
    api_monolith_helper.apply_updates(feature, payload, {"title", "details", "active"})


def _enforce_roles(*allowed_roles: str):
    allowed_role = {role.strip().lower() for role in allowed_roles if role}
    if not current_user.is_authenticated:
        return jsonify({"error": "authentication required"}), 401
    user_role = (getattr(current_user, "role") or "").strip().lower()
    if allowed_role and user_role not in allowed_role:
        return jsonify({"error": "forbidden", "required_roles": sorted(allowed_role), "current_role": user_role or None}), 403


def forbidden_scope_response(message: str, *, action: str, class_id: int | None, system_prompt_id: int | None = None):
    details = {
        "action": action,
        "class_id": class_id,
        "current_role": (getattr(current_user, "role", "") or "").strip().lower() or None,
        "current_user_id": int(current_user.id),
    }
    if system_prompt_id is not None:
        details["system_prompt_id"] = system_prompt_id
    return jsonify({"error": "forbidden", "message": message, "details": details}), 403


def ensure_instructor_owns_system_prompt_class(*, class_id: int | None, action: str):
    role = (getattr(current_user, "role", "") or "").strip().lower()
    if role != "instructor":
        return None
    if class_id is None:
        return forbidden_scope_response("instructors can only manage system prompts tied to classes they own", action=action, class_id=None)
    class_record = db.session.get(CourseClass, int(class_id))
    if class_record is None or int(class_record.instructor_id) != int(current_user.id):
        return forbidden_scope_response("instructors can only manage system prompts for classes they own", action=action, class_id=class_id)
    return None


def ensure_instructor_owns_system_prompt_scope(*, system_prompt: SystemPrompt, action: str):
    role = (getattr(current_user, "role", "") or "").strip().lower()
    if role != "instructor":
        return None
    class_id = system_prompt.class_id
    if class_id is None:
        return forbidden_scope_response(
            "instructors can only manage links for class-scoped system prompts they own",
            action=action,
            class_id=None,
            system_prompt_id=int(system_prompt.id),
        )
    class_record = db.session.get(CourseClass, int(class_id))
    if class_record is None or int(class_record.instructor_id) != int(current_user.id):
        return forbidden_scope_response(
            "instructors can only manage links for classes they own",
            action=action,
            class_id=class_id,
            system_prompt_id=int(system_prompt.id),
        )
    return None


_normalize_auth_email = AuthOps.normalize_auth_email
_resolve_session_timetolive = AuthOps.resolve_session_timetolive
_revoke_session_record = AuthOps.revoke_session_record
_as_utc = AuthOps.as_utc
_create_user_session = AuthOps.create_user_session
revoke_flask_session_lifecycle_record = AuthOps.revoke_flask_session_lifecycle_record
_unauthorized_auth_envelope = AuthOps.unauthorized_auth_envelope
_resolved_allowed_actions = AuthOps.resolved_allowed_actions
_resolve_authenticated_session_state = AuthOps.resolve_authenticated_session_state
