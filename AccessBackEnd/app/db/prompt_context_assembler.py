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


class PromptContextAssembler:
    """Builds prompt-related DB context payloads for debugging/runtime composition."""

    def __init__(self, *, session: Session, models: dict[str, type[Any]]) -> None:
        self._session = session
        self._models = models
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
        UserAccessibilityFeature = self._models["user_accessibility_feature"]
        Accommodation = self._models["accommodation"]

        try:
            resolved_ids = selected_feature_ids or [
                int(accommodation_id)
                for (accommodation_id,) in (
                    self._session.query(UserAccessibilityFeature.accommodation_id)
                    .filter(UserAccessibilityFeature.user_id == user_id, UserAccessibilityFeature.enabled.is_(True))
                    .order_by(UserAccessibilityFeature.accommodation_id.asc())
                    .all()
                )
            ]
        except (OperationalError, ProgrammingError):
            self.feature_context = {"selected_feature_ids": [], "feature_details": [], "instructions_text": ""}
            return self.feature_context

        if not resolved_ids:
            self.feature_context = {"selected_feature_ids": [], "feature_details": [], "instructions_text": ""}
            return self.feature_context

        try:
            rows = (
                self._session.query(Accommodation.id, Accommodation.title, Accommodation.details)
                .filter(Accommodation.id.in_(resolved_ids))
                .order_by(Accommodation.id.asc())
                .all()
            )
        except (OperationalError, ProgrammingError):
            self.feature_context = {"selected_feature_ids": resolved_ids, "feature_details": [], "instructions_text": ""}
            return self.feature_context

        feature_details: list[dict[str, Any]] = []
        instruction_parts: list[str] = []
        for row in rows:
            title = str(row.title or "").strip()
            details = str(row.details or "").strip()
            if exclude_standard_profiles and details.lower().startswith("standard;") and ":" in title:
                continue
            feature_details.append({"id": int(row.id), "title": title, "details": details})
            if details:
                instruction_parts.append(details)

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
        AIInteraction = self._models["ai_interaction"]
        Message = self._models["message"]

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
        messages: list[dict[str, str]] = []
        if selected_chat_id is not None:
            try:
                interactions = (
                    self._session.query(AIInteraction)
                    .filter(AIInteraction.chat_id == selected_chat_id)
                    .order_by(AIInteraction.created_at.asc(), AIInteraction.id.asc())
                    .all()
                )
                for interaction in interactions:
                    prompt_text = str(getattr(interaction, "prompt", "") or "").strip()
                    response_text = str(getattr(interaction, "response_text", "") or "").strip()
                    if prompt_text:
                        messages.append({"role": "user", "content": prompt_text})
                    if response_text:
                        messages.append({"role": "assistant", "content": response_text})

                if not messages:
                    raw_messages = (
                        self._session.query(Message)
                        .filter(Message.chat_id == selected_chat_id)
                        .order_by(Message.id.asc())
                        .all()
                    )
                    for row in raw_messages:
                        content = str(getattr(row, "message_text", "") or "").strip()
                        if content:
                            messages.append({"role": "user", "content": content})
            except (OperationalError, ProgrammingError):
                messages = []

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
