from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from marshmallow import Schema, ValidationError

from ...api.errors import BadRequestError
from .interfaces import Payload


class ApiMonolithHelper:
    """Centralized, compact API helper surface for v1 routes."""

    FIELD_ALIASES: dict[str, dict[str, str]] = {
        "chat": {
            "class": "class_id",
            "user": "user_id",
            "start": "started_at",
        },
        "message": {
            "chat": "chat_id",
            "text": "message_text",
        },
        "note": {
            "class": "class_id",
            "chat": "chat_id",
            "date": "noted_on",
        },
    }

    @classmethod
    def deserialize(cls, resource: str, payload: Payload) -> Payload:
        mapping = cls.FIELD_ALIASES.get(resource, {})
        return {mapping.get(key, key): value for key, value in payload.items()}

    @staticmethod
    def validate(payload: Payload, schema: Schema) -> Payload:
        try:
            return schema.load(payload)
        except ValidationError as exc:
            raise BadRequestError("request validation failed", details={"fields": exc.messages}) from exc

    @staticmethod
    def parse_optional_datetime(value: Any, field_name: str = "started_at") -> datetime | None:
        if value in (None, ""):
            return None
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=UTC)
        if isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError as exc:
                raise BadRequestError(f"{field_name} must be an ISO-8601 datetime") from exc
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
        raise BadRequestError(f"{field_name} must be an ISO-8601 datetime")

    @staticmethod
    def parse_required_date(value: Any, field_name: str) -> date:
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            try:
                return date.fromisoformat(value)
            except ValueError as exc:
                raise BadRequestError(f"{field_name} must be YYYY-MM-DD") from exc
        raise BadRequestError(f"{field_name} must be YYYY-MM-DD")

    @staticmethod
    def parse_int(value: Any, field_name: str, *, required: bool = False) -> int | None:
        if value in (None, ""):
            if required:
                raise BadRequestError(f"{field_name} is required")
            return None
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise BadRequestError(f"{field_name} must be an integer") from exc

    @staticmethod
    def _serialize_chat(record: Any) -> Payload:
        started_at = getattr(record, "started_at", None)
        started = started_at.isoformat() if started_at else None
        return {
            "id": record.id,
            "class": record.class_id,
            "class_id": record.class_id,
            "user": record.user_id,
            "user_id": record.user_id,
            "title": record.title,
            "model": record.model,
            "start": started,
            "started_at": started,
        }

    @staticmethod
    def _serialize_message(record: Any) -> Payload:
        return {
            "id": record.id,
            "chat_id": record.chat_id,
            "message_text": record.message_text,
            "vote": record.vote,
            "note": record.note,
            "help_intent": record.help_intent,
        }

    @staticmethod
    def _serialize_note(record: Any) -> Payload:
        noted_on = getattr(record, "noted_on", None)
        noted = noted_on.isoformat() if noted_on else None
        return {
            "id": record.id,
            "class": record.class_id,
            "class_id": record.class_id,
            "chat": record.chat_id,
            "chat_id": record.chat_id,
            "date": noted,
            "noted_on": noted,
            "content": record.content,
        }

    @staticmethod
    def serialize(resource: str, record: Any) -> Payload:
        if resource == "chat":
            return ApiMonolithHelper._serialize_chat(record)
        if resource == "message":
            return ApiMonolithHelper._serialize_message(record)
        if resource == "note":
            return ApiMonolithHelper._serialize_note(record)
        return {}

    @staticmethod
    def apply_updates(record: Any, payload: Payload, allowed_fields: set[str]) -> list[str]:
        changed: list[str] = []
        for field in allowed_fields:
            if field in payload:
                setattr(record, field, payload[field])
                changed.append(field)
        return changed


api_monolith_helper = ApiMonolithHelper()
