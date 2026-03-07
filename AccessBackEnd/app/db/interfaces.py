from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Any, Protocol


class DatabaseRuntime(Protocol):
    """Interface for pluggable DB runtimes used by the backend."""

    models: dict[str, type]

    def session_scope(self) -> AbstractContextManager[Any]:
        """Open a unit-of-work/session context for reads and writes."""


class UserRepositoryInterface(Protocol):
    """Interface for user persistence operations."""

    def create(self, session: Any, *, email: str, password_hash: str, role: str = "student") -> Any:
        ...

    def get_by_id(self, session: Any, user_id: int) -> Any | None:
        ...

    def get_by_email(self, session: Any, email: str) -> Any | None:
        ...


class AIInteractionRepositoryInterface(Protocol):
    """Interface for AI interaction persistence operations."""

    def create(
        self,
        session: Any,
        *,
        prompt: str,
        response_text: str,
        chat_id: int | None = None,
        ai_model_id: int | None = None,
        accommodations_id_system_prompts_id: int | None = None,
    ) -> Any:
        ...

    def list_for_chat(self, session: Any, chat_id: int) -> list[Any]:
        ...


class InteractionRepositoryFactory(Protocol):
    """Factory interface used by helpers to build interaction repositories."""

    def __call__(self, interaction_model: type) -> AIInteractionRepositoryInterface:
        ...