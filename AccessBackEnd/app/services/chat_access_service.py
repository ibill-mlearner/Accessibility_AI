from __future__ import annotations

from flask_login import current_user

from ..api.errors import BadRequestError
from ..models import Chat, CourseClass, UserClassEnrollment


class ChatAccessService:
    """Authorization helpers for chat reads and writes."""

    @staticmethod
    def _current_user_id() -> int:
        user_id = current_user.get_id()
        if user_id is None:
            raise BadRequestError("authenticated user id is required")
        return int(user_id)

    @classmethod
    def assert_can_access_chat(cls, chat: Chat) -> None:
        """Ensure the current user can read the requested chat."""
        user_id = cls._current_user_id()
        if chat.user_id == user_id:
            return

        if chat.course_class.instructor_id == user_id:
            return

        enrollment = next(
            (
                item
                for item in chat.course_class.enrollments
                if item.user_id == user_id and item.dropped_at is None
            ),
            None,
        )
        if enrollment is not None:
            return

        raise BadRequestError("user is not authorized for this chat", status_code=403)

    @classmethod
    def assert_can_create_chat(
        cls, *, class_record: CourseClass, requested_user_id: int | None
    ) -> int:
        """Ensure current user can create chats for the given class context."""
        user_id = cls._current_user_id()

        if requested_user_id is not None and requested_user_id != user_id:
            raise BadRequestError(
                "chat user must match authenticated user", status_code=403
            )

        if class_record.instructor_id == user_id:
            return user_id

        enrollment = next(
            (
                item
                for item in class_record.enrollments
                if item.user_id == user_id and item.dropped_at is None
            ),
            None,
        )
        if enrollment is None:
            raise BadRequestError(
                "user is not enrolled in this class", status_code=403
            )

        if enrollment.role not in {"student", "ta"}:
            raise BadRequestError("unsupported enrollment role", status_code=403)

        return user_id


__all__ = ["ChatAccessService"]
