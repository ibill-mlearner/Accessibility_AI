from __future__ import annotations

from typing import Any

from flask import current_app, jsonify
from flask_login import current_user
from sqlalchemy.exc import SQLAlchemyError

from ...db.repositories.interaction_repo import AIInteractionRepository
from ...models import AIInteraction, AIModel, Chat
from ...models.ai import AccommodationSystemPrompt
from .mutations import AIInteractionMutations
from .validators import AIInteractionValidator


class AIInteractionHelperOps:
    _LEGACY_PROVIDER_ALIASES: dict[str, str] = {
        "huggingface_langchain": "huggingface",
        "huggingface_local": "huggingface",
        "huggingface": "huggingface",
        "ollama": "ollama",
        "live_agent": "live_agent",
    }

    def __init__(self) -> None:
        self.current_ai_model_id: int | None = None

    def derive_selection_from_chat(self, chat: Chat | None) -> tuple[str, str]:
        if chat is None:
            return "", ""
        raw_model = str(getattr(chat, "model", "") or "").strip()
        if not raw_model:
            return "", ""

        if "::" in raw_model:
            provider_token, model_token = raw_model.split("::", 1)
            provider = AIInteractionValidator.to_clean_text(provider_token, lower=True)
            model_id = AIInteractionValidator.to_clean_model_id(model_token)
            return provider, model_id

        normalized_provider = AIInteractionValidator.to_clean_text(raw_model, lower=True)
        if normalized_provider in self._LEGACY_PROVIDER_ALIASES:
            return self._LEGACY_PROVIDER_ALIASES[normalized_provider], ""

        return "", AIInteractionValidator.to_clean_model_id(raw_model)

    def resolve_chat_id(self, payload: dict[str, Any]) -> int | None:
        chat_id = payload.get("chat_id")
        if chat_id is None:
            return None
        return int(chat_id)

    def resolve_initiated_by(self, payload: dict[str, Any]) -> str:
        if getattr(current_user, "is_authenticated", False):
            return str(current_user.get_id() or getattr(current_user, "email", "authenticated_user"))
        return str(payload.get("user") or payload.get("user_id") or "anonymous")

    def normalize_interaction_response(self, result: Any) -> dict[str, Any]:
        envelope = AIInteractionMutations.normalize_payload(result)
        normalized = {
            "assistant_text": AIInteractionMutations.strip_prompt_template_echo(envelope.assistant_text),
            "confidence": envelope.confidence,
            "notes": envelope.notes,
            "meta": envelope.meta.copy() if isinstance(envelope.meta, dict) else {},
        }
        if not normalized["assistant_text"]:
            normalized["notes"].append("assistant_empty_after_normalization")
            normalized.setdefault("meta", {}).setdefault("debug", {})["raw_payload_preview"] = AIInteractionMutations.truncate_debug_payload(result)
        return normalized

    def resolve_ai_model_id(self, result: Any, *, db_session: Any) -> int:
        meta = result.get("meta") if isinstance(result, dict) else {}
        provider = AIInteractionValidator.to_clean_text(
            (meta or {}).get("provider") or current_app.config.get("AI_PROVIDER") or "huggingface",
            lower=True,
        ) or "huggingface"
        model_name = AIInteractionValidator.to_clean_text(
            (meta or {}).get("model_id")
            or (meta or {}).get("model")
            or (result.get("model_id") if isinstance(result, dict) else None)
            or (result.get("model") if isinstance(result, dict) else None)
            or current_app.config.get("AI_MODEL_NAME")
            or "",
        ) or f"{provider}-default"

        model = db_session.query(AIModel).filter(AIModel.provider == provider, AIModel.model_id == model_name).first()
        if model is None:
            model = AIModel(provider=provider, model_id=model_name, active=True)
            db_session.add(model)
            db_session.flush()
        else:
            model.active = True
        self.current_ai_model_id = int(model.id)
        return self.current_ai_model_id

    def persist_interaction(
        self,
        *,
        payload: dict[str, Any],
        prompt: str,
        normalized_result: dict[str, Any],
        db_session: Any,
        require_record: Any,
    ) -> tuple[Any, int] | None:
        try:
            chat_id = self.resolve_chat_id(payload)
            prompt_link_id = payload.get("accommodations_id_system_prompts_id")
            if prompt_link_id is not None:
                prompt_link_id = int(prompt_link_id)
                require_record("accommodation_system_prompt", AccommodationSystemPrompt, prompt_link_id)

            interaction = AIInteractionRepository(AIInteraction).create(
                db_session,
                prompt=prompt,
                response_text=normalized_result.get("assistant_text") or "",
                chat_id=chat_id,
                ai_model_id=self.resolve_ai_model_id(normalized_result, db_session=db_session),
                accommodations_id_system_prompts_id=prompt_link_id,
            )

            if chat_id is not None:
                chat = require_record("chat", Chat, chat_id)
                chat.ai_interaction_id = interaction.id

            db_session.commit()
            return None
        except (TypeError, ValueError, SQLAlchemyError) as exc:
            db_session.rollback()
            code = "persistence_error" if isinstance(exc, SQLAlchemyError) else "bad_request"
            status = 500 if isinstance(exc, SQLAlchemyError) else 400
            return jsonify({"error": {"code": code, "message": "Failed to persist AI interaction", "details": {"exception": exc.__class__.__name__}}}), status


_DEFAULT_INTERACTION_HELPER_OPS = AIInteractionHelperOps()

derive_selection_from_chat = _DEFAULT_INTERACTION_HELPER_OPS.derive_selection_from_chat
resolve_chat_id = _DEFAULT_INTERACTION_HELPER_OPS.resolve_chat_id
resolve_initiated_by = _DEFAULT_INTERACTION_HELPER_OPS.resolve_initiated_by
normalize_interaction_response = _DEFAULT_INTERACTION_HELPER_OPS.normalize_interaction_response
resolve_ai_model_id = _DEFAULT_INTERACTION_HELPER_OPS.resolve_ai_model_id
persist_interaction = _DEFAULT_INTERACTION_HELPER_OPS.persist_interaction
