from __future__ import annotations

"""DB-backed prompt context assembly utilities.

This module intentionally keeps prompt-context composition close to the database
layer so API and debugging flows can share one implementation for:
1) accessibility feature context
2) conversation context
3) final system-prompt composition
"""

from typing import Any

from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session

from .utilities import PromptContextDBUtilities


class PromptContextAssembler:
    """Builds prompt-related DB context payloads for debugging/runtime composition."""

    def __init__(self, *, session: Session, models: dict[str, type[Any]]) -> None:
        self._session = session
        self._models = models
        self._database_utilities = PromptContextDBUtilities(session=session, models=models)
        self.feature_context: dict[str, Any] = {}
        self.conversation_context: dict[str, Any] = {}
        self.composed_system_prompt: str = ""

    def build_feature_context(
        self,
        *,
        user_id: int,
        selected_feature_ids: list[int] | None = None,
        exclude_standard_profiles: bool = True,
    ) -> dict[str, Any]:
        """Build accessibility feature context for a user or explicit feature list.

        Returns a normalized payload:
        {
          "selected_feature_ids": list[int],
          "feature_details": list[dict],
          "instructions_text": str
        }
        """
        try:
            resolved_ids = self._database_utilities.resolve_selected_feature_ids(
                user_id=user_id,
                selected_feature_ids=selected_feature_ids,
            )
        except (OperationalError, ProgrammingError):
            self.feature_context = {"selected_feature_ids": [], "feature_details": [], "instructions_text": ""}
            return self.feature_context

        if not resolved_ids:
            self.feature_context = {"selected_feature_ids": [], "feature_details": [], "instructions_text": ""}
            return self.feature_context

        try:
            rows = self._database_utilities.load_feature_rows(feature_ids=resolved_ids)
        except (OperationalError, ProgrammingError):
            self.feature_context = {"selected_feature_ids": resolved_ids, "feature_details": [], "instructions_text": ""}
            return self.feature_context

        feature_details, instruction_parts = self._database_utilities.assemble_feature_payload_from_rows(
            rows,
            exclude_standard_profiles=exclude_standard_profiles,
        )

        self.feature_context = {
            "selected_feature_ids": [entry["id"] for entry in feature_details],
            "feature_details": feature_details,
            "instructions_text": "\n\n".join(instruction_parts),
        }
        return self.feature_context

    def build_conversation_context(self, *, user_id: int, chat_id: int | None = None) -> dict[str, Any]:
        """Build chat/message context for a user.

        If ``chat_id`` is omitted, the newest chat for the user is selected.
        Response includes selected chat id, message list, and available chats.
        """
        Chat = self._models["chat"]

        try:
            chats = (
                self._session.query(Chat)
                .filter(Chat.user_id == user_id)
                .order_by(Chat.id.desc())
                .all()
            )
        except (OperationalError, ProgrammingError):
            self.conversation_context = {"chat_id": None, "messages": [], "available_chats": []}
            return self.conversation_context

        selected_chat_id = chat_id or (int(chats[0].id) if chats else None)
        messages = self.build_chat_messages_for_user(user_id=user_id, chat_id=selected_chat_id)

        self.conversation_context = {
            "chat_id": selected_chat_id,
            "messages": messages,
            "available_chats": [
                {
                    "id": int(chat.id),
                    "title": str(getattr(chat, "title", "") or ""),
                    "class_id": int(getattr(chat, "class_id", 0) or 0) or None,
                    "active": bool(getattr(chat, "active", True)),
                }
                for chat in chats
            ],
        }
        return self.conversation_context

    def build_chat_messages_for_user(self, *, user_id: int, chat_id: int | None) -> list[dict[str, str]]:
        """Return ordered chat messages for one user+chat scope.

        Query contract:
        - `user_id` and `chat_id` must both be provided and match an existing chat row.
        - Returns a normalized role/content list ordered oldest -> newest.
        - Prefers `ai_interactions` prompt/response pairs; falls back to `messages`.
        """
        Chat = self._models["chat"]
        if chat_id is None:
            return []

        try:
            chat_exists = (
                self._session.query(Chat.id)
                .filter(Chat.id == int(chat_id), Chat.user_id == int(user_id))
                .first()
            )
        except (OperationalError, ProgrammingError):
            return []

        if chat_exists is None:
            return []

        try:
            ordered_messages = self._database_utilities.messages_from_interactions(chat_id=int(chat_id))
        except (OperationalError, ProgrammingError):
            ordered_messages = []

        if ordered_messages:
            return ordered_messages

        try:
            fallback_messages = self._database_utilities.messages_from_legacy_chat_rows(chat_id=int(chat_id))
        except (OperationalError, ProgrammingError):
            return []
        return fallback_messages

    def build_composed_system_prompt(
        self,
        *,
        guardrail_prompt: str,
        feature_context: dict[str, Any] | None = None,
        request_scoped_system_prompt: str = "",
    ) -> str:
        """Compose guardrail + feature instructions + request-scoped prompt text."""
        features = feature_context or self.feature_context
        instructions_text = str((features or {}).get("instructions_text") or "").strip()
        self.composed_system_prompt = "\n\n".join(
            part.strip()
            for part in [guardrail_prompt or "", instructions_text, request_scoped_system_prompt or ""]
            if str(part or "").strip()
        )
        return self.composed_system_prompt
