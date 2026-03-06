from datetime import UTC, datetime, timedelta
import secrets

from flask import current_app, jsonify, session
from flask_login import current_user

from ..models import UserSession
from ..api.v1.routes import db


class AuthHelpers:
    @staticmethod
    def _normalize_auth_email(value:str | None) -> str:
        return (value or "").strip().lower()

    @staticmethod
    def _resolve_session_timetolive() -> timedelta:
        ttl_value = current_app.config.get("JWT_ACCESS_TOKEN_EXPIRES")

        # early exit to send back time value from configs
        if isinstance(ttl_value, timedelta):
            return ttl_value

        # if ttl is set as a numeric value
        if isinstance(ttl_value, (int, float)):
            return timedelta(minutes=float(ttl_value))

        # 30 minute timeout default config is already 30 minutes though
        return timedelta(minutes=30)

    @staticmethod
    def _revoke_session_record(session_id: int | None) -> None:
        if not session_id:
            return

        session_record = db.session.get(UserSession, int(session_id))
        if session_record is None:
            return
        now = datetime.now(UTC)
        revoked_at = AuthHelpers._as_utc(session_record.revoked_at)
        if revoked_at is not None and revoked_at <= now:
            return

        session_record.revoked_at = now
        db.session.commit()

    @staticmethod
    def _as_utc(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @staticmethod
    def _create_user_session(*, user_id: int) -> UserSession:
        now = datetime.now(UTC)
        ttl = AuthHelpers._resolve_session_timetolive()
        session_record = UserSession(
            user_id=user_id,
            token_hash=secrets.token_urlsafe(48),
            expires_at=now + ttl,
            last_seen_at=now,
            revoked_at=datetime.max.replace(tzinfo=UTC)
        )
        db.session.add(session_record)
        db.session.flush()
        return session_record

    @staticmethod
    def revoke_flask_session_lifecycle_record() -> None:
        mapped_sessionID = session.get("auth_session_id")
        AuthHelpers._revoke_session_record(mapped_sessionID)

    @staticmethod
    def _unauthorized_auth_envelope(message: str, *, details: dict | None = None):
        return (jsonify(
            {
                "error": {
                    "code": "unauthorized",
                    "message": message,
                    "details": details or {}
                }
            }
        ), 401)

    #todo: move onto db
    @staticmethod
    def _resolved_allowed_actions(user_role: str) -> list[str]:
        role_val = (user_role or "").strip().lower()
        action_map = {
            "admin": ["users:read", "users:write", "classes:read", "classes:write", "classes:delete"],
            "instructor": ["classes:read", "classes:write", "students:read"],
            "student": ["classes:read", "profile:read", "profile:write"]
        }
        return action_map.get(role_val, ["profile:read"])

    @staticmethod
    def _resolve_authenticated_session_state() -> tuple[UserSession | None, datetime, tuple | None]:
        this_time = datetime.now(UTC)

        if not current_user.is_authenticated:
            return None, this_time, AuthHelpers._unauthorized_auth_envelope("authentication required")

        persisted_session_id = session.get("auth_session_id")
        if not persisted_session_id:
            return (
                None,
                this_time,
                AuthHelpers._unauthorized_auth_envelope(
                    "session not found",
                    details={"reason": "missing session ID"}
                )
            )

        session_record = db.session.get(UserSession, int(persisted_session_id))
        if session_record is None:
            return (
                None,
                this_time,
                AuthHelpers._unauthorized_auth_envelope(
                    "session not found",
                    details={"reason": "missing session record"}
                )
            )

        if int(session_record.user_id) != int(current_user.id):
            return (
                None,
                this_time,
                AuthHelpers._unauthorized_auth_envelope(
                    "session user mismatch",
                    # this should cover the auth bypass from session storage in front end earlier
                    details={"reason": "session user mismatch"}
                )
            )

        revoked_at = AuthHelpers._as_utc(session_record.revoked_at)
        if revoked_at is not None and revoked_at <= this_time:
            return (
                None,
                this_time,
                AuthHelpers._unauthorized_auth_envelope(
                    "session revoked",
                    details={"reason": "revoked", "revoked_at": f"{revoked_at}"}
                )
            )

        expires_at = AuthHelpers._as_utc(session_record.expires_at)
        if expires_at and expires_at <= this_time:
            session_record.revoked_at = this_time
            db.session.commit()
            return (
                None,
                this_time,
                AuthHelpers._unauthorized_auth_envelope(
                    "session expired",
                    details={"reason": "expired", "expires_at": f"{expires_at}"}
                )
            )

        return session_record, this_time, None

    @staticmethod
    def _enforce_roles(*allowed_roles: str):

        allowed_role = {role.strip().lower() for role in allowed_roles if role}

        if not current_user.is_authenticated:
            return jsonify({"error": "authentication required"}), 401

        user_role = (getattr(current_user, "role") or "").strip().lower()
        if allowed_role and user_role not in allowed_role:
            return (
                jsonify(
                    {
                        "error": "forbidden",
                        "required_roles": sorted(allowed_role),
                        "current_role": user_role or None,
                    }
                ),
                403,
            )


_normalize_auth_email = AuthHelpers._normalize_auth_email
_resolve_session_timetolive = AuthHelpers._resolve_session_timetolive
_revoke_session_record = AuthHelpers._revoke_session_record
_as_utc = AuthHelpers._as_utc
_create_user_session = AuthHelpers._create_user_session
revoke_flask_session_lifecycle_record = AuthHelpers.revoke_flask_session_lifecycle_record
_unauthorized_auth_envelope = AuthHelpers._unauthorized_auth_envelope
_resolved_allowed_actions = AuthHelpers._resolved_allowed_actions
_resolve_authenticated_session_state = AuthHelpers._resolve_authenticated_session_state
_enforce_roles = AuthHelpers._enforce_roles
