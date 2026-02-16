from __future__ import annotations

from ..models import Chat, CourseClass, UserClassEnrollment


class ChatAccessService:
    """Placeholder access-service contract for chat-flow authorization checks.

    This module intentionally exposes method signatures and sequencing intent only.
    Endpoint handlers should call these methods once implementation work begins.
    """

    @staticmethod
    def get_authenticated_user_id() -> int:
        """Return the authenticated user id used by chat access checks.

        TODO sequence:
        1) Resolve principal from auth/session context.
        2) Validate principal identity is present and castable to int.
        3) Return normalized user id for downstream checks.
        """
        raise NotImplementedError("TODO: implement authenticated user id resolution")

    @classmethod
    def assert_chat_owner(cls, *, chat: Chat, user_id: int) -> None:
        """Ensure the given user is the owner of ``chat``.

        TODO sequence:
        1) Validate chat/user inputs.
        2) Compare chat.user_id with user_id.
        3) Raise authorization error when ownership check fails.
        """
        raise NotImplementedError("TODO: implement chat owner authorization check")

    @classmethod
    def assert_class_instructor(cls, *, class_record: CourseClass, user_id: int) -> None:
        """Ensure the given user is the instructor for ``class_record``.

        TODO sequence:
        1) Validate class/user inputs.
        2) Compare class_record.instructor_id with user_id.
        3) Raise authorization error when instructor check fails.
        """
        raise NotImplementedError("TODO: implement class instructor authorization check")

    @classmethod
    def assert_active_enrollment(
        cls,
        *,
        enrollments: list[UserClassEnrollment],
        user_id: int,
        allowed_roles: set[str] | None = None,
    ) -> UserClassEnrollment:
        """Ensure user has active class enrollment and optional role membership.

        TODO sequence:
        1) Locate enrollment where ``enrollment.user_id == user_id`` and not dropped.
        2) Validate role membership when ``allowed_roles`` is provided.
        3) Return matched enrollment or raise authorization error.
        """
        raise NotImplementedError("TODO: implement active enrollment authorization check")

    @classmethod
    def assert_can_access_chat(cls, *, chat: Chat, user_id: int) -> None:
        """Authorize chat read access via owner, instructor, or enrollment checks.

        TODO sequence:
        1) Allow owner access via ``assert_chat_owner``.
        2) Allow instructor access via ``assert_class_instructor``.
        3) Allow enrolled users via ``assert_active_enrollment``.
        4) Raise authorization error when no access path applies.
        """
        raise NotImplementedError("TODO: implement chat access authorization policy")

    @classmethod
    def assert_can_create_chat(
        cls,
        *,
        class_record: CourseClass,
        actor_user_id: int,
        requested_user_id: int | None,
    ) -> int:
        """Authorize chat creation and return normalized owner id.

        TODO sequence:
        1) Validate requested ownership semantics for actor/requested user ids.
        2) Authorize through instructor or active enrollment checks.
        3) Return persisted owner id for chat creation.
        """
        raise NotImplementedError("TODO: implement chat create authorization policy")


__all__ = ["ChatAccessService"]
