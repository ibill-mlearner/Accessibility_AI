from __future__ import annotations

from flask_login import current_user

from ...models import Chat, CourseClass, UserClassEnrollment


class ChatAccessHelper:
    """Authorization checks for chat read/create operations."""

    @staticmethod
    def get_authenticated_user_id() -> int:
        """Return authenticated user id from flask-login context."""
        if not getattr(current_user, "is_authenticated", False):
            raise PermissionError("user is not authenticated")

        try:
            return int(current_user.get_id())
        except (TypeError, ValueError) as exc:
            raise PermissionError("invalid authenticated user context") from exc

    @classmethod
    def assert_chat_owner(
        cls,
        *,
        chat: Chat,
        user_id: int,
    ) -> None:
        """Ensure the given user is the owner of ``chat``."""
        if chat is None or int(chat.user_id) != int(user_id):
            raise PermissionError("user is not chat owner")

    @classmethod
    def assert_class_instructor(
        cls,
        *,
        class_record: CourseClass,
        user_id: int,
    ) -> None:
        """Ensure the given user is the instructor for ``class_record``."""
        if class_record is None or int(class_record.instructor_id) != int(user_id):
            raise PermissionError("user is not class instructor")

    @staticmethod
    def _is_admin_user(
        *,
        user_id: int,
    ) -> bool:
        role = (getattr(current_user, "role", "") or "").strip().lower()
        try:
            current_id = int(current_user.get_id())
        except (TypeError, ValueError):
            return False
        return role == "admin" and current_id == int(user_id)

    @classmethod
    def assert_active_enrollment(
        cls,
        *,
        enrollments: list[UserClassEnrollment],
        user_id: int,
    ) -> UserClassEnrollment:
        """Ensure user has active class enrollment."""
        for enrollment in enrollments:
            if int(enrollment.user_id) != int(user_id):
                continue
            if not enrollment.active:
                continue
            return enrollment

        raise PermissionError("user is not actively enrolled in this class")

    @classmethod
    def assert_can_access_chat(
        cls,
        *,
        chat: Chat,
        user_id: int,
    ) -> None:
        """Authorize chat read access via owner, instructor, or enrollment checks."""
        if cls._is_admin_user(user_id=user_id):
            return

        try:
            cls.assert_chat_owner(chat=chat, user_id=user_id)
            return
        except PermissionError:
            pass

        class_record = chat.course_class

        try:
            cls.assert_class_instructor(class_record=class_record, user_id=user_id)
            return
        except PermissionError:
            pass

        cls.assert_active_enrollment(enrollments=class_record.enrollments, user_id=user_id)

    @classmethod
    def assert_can_create_chat(
        cls,
        *,
        class_record: CourseClass,
        actor_user_id: int,
        requested_user_id: int | None,
    ) -> int:
        """Authorize chat creation and return normalized owner id."""
        owner_user_id = int(actor_user_id if requested_user_id is None else requested_user_id)

        if cls._is_admin_user(user_id=actor_user_id):
            return owner_user_id

        if owner_user_id != int(actor_user_id):
            cls.assert_class_instructor(class_record=class_record, user_id=actor_user_id)
            cls.assert_active_enrollment(enrollments=class_record.enrollments, user_id=owner_user_id)
            return owner_user_id

        try:
            cls.assert_class_instructor(class_record=class_record, user_id=actor_user_id)
            return owner_user_id
        except PermissionError:
            cls.assert_active_enrollment(enrollments=class_record.enrollments, user_id=actor_user_id)
            return owner_user_id


__all__ = ["ChatAccessHelper"]
