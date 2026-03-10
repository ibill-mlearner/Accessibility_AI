from __future__ import annotations

from typing import Protocol

from ...models import Chat, CourseClass, UserClassEnrollment


class ChatAccessInterface(Protocol):
    """Behavior contract for chat authorization helper implementations."""

    @staticmethod
    def get_authenticated_user_id() -> int:
        ...

    @classmethod
    def assert_chat_owner(cls, *, chat: Chat, user_id: int) -> None:
        ...

    @classmethod
    def assert_class_instructor(cls, *, class_record: CourseClass, user_id: int) -> None:
        ...

    @classmethod
    def assert_active_enrollment(
        cls,
        *,
        enrollments: list[UserClassEnrollment],
        user_id: int,
    ) -> UserClassEnrollment:
        ...

    @classmethod
    def assert_can_access_chat(cls, *, chat: Chat, user_id: int) -> None:
        ...

    @classmethod
    def assert_can_create_chat(
        cls,
        *,
        class_record: CourseClass,
        actor_user_id: int,
        requested_user_id: int | None,
    ) -> int:
        ...


__all__ = ["ChatAccessInterface"]
