from typing import Any

from ....models import Accommodation, Chat, CourseClass, Message, Note, User
from ..routes import (
    BadRequestError,
    _apply_field_updates,
    _assert_chat_permissions,
    _parse_optional_datetime,
    _parse_required_date,
    _require_record,
)


class MutationHelpers:
    @staticmethod
    def _apply_chat_mutations(chat: Chat, payload: dict[str, Any]) -> None:
        if "class_id" in payload:
            class_record = _require_record("class", CourseClass, int(payload["class_id"]))
            chat.class_id = int(class_record.id)

        if "user_id" in payload:
            _require_record("user", User, int(payload["user_id"]))
            chat.user_id = int(payload["user_id"])

        if "title" in payload:
            chat.title = payload["title"] or ""or chat.title

        if "model" in payload:
            chat.model = payload["model"] or ""or chat.model

        if "started_at" in payload:
            parsed = _parse_optional_datetime(payload["started_at"])
            if parsed is not None:
                chat.started_at = parsed

    @staticmethod
    def _apply_message_mutations(message: Message, payload: dict[str, Any]) -> None:
        if "chat_id" in payload:
            _require_record("chat", Chat, int(payload["chat_id"]))
            message.chat_id = int(payload["chat_id"])
        _apply_field_updates(
            message,
            payload,
            (
                "message_text",
                'vote',
                'note',
                'help_intent'
            )
        )

    @staticmethod
    def _apply_note_mutations(note: Note, payload: dict[str, Any]) -> None:
        if "class_id" in payload:
            _require_record("class", CourseClass, int(payload["class_id"]))
            note.class_id = int(payload["class_id"])
        if "chat_id" in payload:
            chat = _require_record("chat", Chat, int(payload['chat_id']))
            deny = _assert_chat_permissions(chat)
            if deny is not None:
                # return deny
                raise BadRequestError("chat id is not accessible")
            note.chat_id = int(payload["chat_id"])
        if "noted_on" in payload:
            note.noted_on = _parse_required_date(payload["noted_on"], field_name="noted_on")
        if "content" in payload:
            note.content = str(payload["content"] or "").strip()

    @staticmethod
    def _apply_class_mutations(class_record: CourseClass, payload: dict[str, Any]) -> None:
        _apply_field_updates(
            class_record,
            payload,
            (
                'name',
                'description',
                'active'
            )
        )

        if "instructor_id" in payload:
            _require_record("user", User, int(payload["instructor_id"]))
            class_record.instructor_id = int(payload["instructor_id"])

    @staticmethod
    def _apply_feature_mutations(feature: Accommodation, payload: dict[str, Any]) -> None:
        _apply_field_updates(
            feature,
            payload,
            (
                'title',
                'details',
                'active'
            )
        )


_apply_chat_mutations = MutationHelpers._apply_chat_mutations
_apply_message_mutations = MutationHelpers._apply_message_mutations
_apply_note_mutations = MutationHelpers._apply_note_mutations
_apply_class_mutations = MutationHelpers._apply_class_mutations
_apply_feature_mutations = MutationHelpers._apply_feature_mutations
