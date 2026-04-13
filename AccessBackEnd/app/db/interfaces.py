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


class PromptContextAssemblerInterface(Protocol):
    """Interface for prompt-context composition helpers backed by DB data.

    Notes:
    - Intended for API/runtime composition and developer debugging utilities.
    - Keeps feature, conversation, and system-prompt composition under one
      contract so call-sites can swap implementations without changing behavior.
    """

    feature_context: dict[str, Any]
    conversation_context: dict[str, Any]
    composed_system_prompt: str

    def build_feature_context(
        self,
        *,
        user_id: int,
        selected_feature_ids: list[int] | None = None,
        exclude_standard_profiles: bool = True,
    ) -> dict[str, Any]:
        """Build accessibility feature context payload for prompt composition."""

    def build_conversation_context(self, *, user_id: int, chat_id: int | None = None) -> dict[str, Any]:
        """Build conversation payload (chat selection + messages) for prompt composition."""

    def build_composed_system_prompt(
        self,
        *,
        guardrail_prompt: str,
        feature_context: dict[str, Any] | None = None,
        request_scoped_system_prompt: str = "",
    ) -> str:
        """Build final system prompt text from guardrail + feature + request-level inputs."""
