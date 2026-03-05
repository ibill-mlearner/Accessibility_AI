import json

from typing import Any
from flask import current_app, jsonify, session
from flask_login import current_user
from sqlalchemy.exc import SQLAlchemyError

from app.db.repositories.interaction_repo import AIInteractionRepository
from app.models import AIInteraction, AIModel, Chat
from app.models.ai_interaction import AccommodationSystemPrompt
from app.services.ai_pipeline.model_catelog import family_id_from_model_id, resolve_model_selection
from app.api.v1.routes import _raise_bad_request_from_exception, _require_record, db


class AIInteractionHelpers:
    _EMPTY_ASSISTANT_NOTE = "assistant_empty_after_normalization"

    @staticmethod
    def _extract_response_text(result: Any) -> str:
        """Normalize provider payload into a storable interaction response string."""
        normalized = AIInteractionHelpers._normalize_interaction_response(result)
        return normalized["assistant_text"]

    @staticmethod
    def _truncate_debug_payload(value: Any, *, limit: int = 1200) -> str:
        """Safely serialize payload snippets for metadata without exposing oversized blobs."""
        serialized = value if isinstance(value, str) else json.dumps(value, default=str)
        return serialized if len(serialized) <= limit else f"{serialized[:limit]}… [truncated]"

    @staticmethod
    def _strip_prompt_template_echo(text: str) -> str:
        """Drop obvious prompt-template scaffolding from assistant output fields."""
        template_tokens = ("{prompt}", "{context}", "{question}", "{{", "}}")
        cleaned_lines = [
            line.strip()
            for line in text.splitlines()
            if line.strip() and not any(token in line.lower() for token in template_tokens)
        ]
        cleaned = "\n".join(cleaned_lines).strip()
        return cleaned.removeprefix("Answer:").strip()

    @staticmethod
    def _normalize_interaction_response(result: Any) -> dict[str, Any]:
        """Normalize provider payload into canonical UI response shape."""
        normalized_response: dict[str, Any] = {
            "assistant_text": "",
            "confidence": None,
            "notes": [],
            "meta": {},
        }

        if isinstance(result, dict):
            candidate = next(
                (result.get(key) for key in ("assistant_text", "result", "answer", "response_text", "response", "output", "text") if result.get(key) is not None),
                "",
            )
            normalized_response["assistant_text"] = AIInteractionHelpers._strip_prompt_template_echo(str(candidate))

            confidence = result.get("confidence")
            normalized_response["confidence"] = float(confidence) if isinstance(confidence, (int, float)) else None

            notes = result.get("notes")
            if isinstance(notes, list):
                normalized_response["notes"] = [str(note) for note in notes]
            elif isinstance(notes, str) and notes.strip():
                normalized_response["notes"] = [notes.strip()]

            meta_payload = result.get("meta")
            normalized_response["meta"] = meta_payload.copy() if isinstance(meta_payload, dict) else {}
        else:
            normalized_response["assistant_text"] = AIInteractionHelpers._strip_prompt_template_echo(str(result or ""))

        # Keep raw provider payload only in debug metadata for investigation.
        if not normalized_response["assistant_text"]:
            if AIInteractionHelpers._EMPTY_ASSISTANT_NOTE not in normalized_response["meta"]:
                normalized_response['notes'].append(AIInteractionHelpers._EMPTY_ASSISTANT_NOTE)
            normalized_response["meta"].setdefault("debug", {})["raw_payload_preview"] = AIInteractionHelpers._truncate_debug_payload(result)

        return normalized_response

    @staticmethod
    def _resolve_session_model_selection() -> dict[str, str | None] | None:
        persisted = session.get("ai_model_selection")
        if not isinstance(persisted, dict):
            return None

        persisted_user_id = persisted.get("user_id")
        active_user_id = getattr(current_user, "id", None)
        if persisted_user_id is None or active_user_id is None:
            return None
        if int(persisted_user_id) != int(active_user_id):
            return None

        persisted_session_id = persisted.get("auth_session_id")
        active_session_id = session.get("auth_session_id")
        if persisted_session_id and active_session_id and int(persisted_session_id) != int(active_session_id):
            return None

        model_id = str(persisted.get("model_id") or "").strip()
        provider = str(persisted.get("provider") or "").strip().lower()
        if not provider or not model_id:
            return None

        return {
            "provider": provider,
            "model_id": model_id,
            "family_id": family_id_from_model_id(model_id),
        }

    @staticmethod
    def _resolve_selected_model(payload: dict[str, Any]) -> dict[str, str | None]:
        """Resolve currently active provider/model/family from discovered defaults."""
        selected = AIInteractionHelpers._resolve_session_model_selection()
        if selected is not None:
            return selected
        provider_defaults = payload.get("provider_defaults")
        if not isinstance(provider_defaults, dict):
            provider_defaults = {}

        provider = str(
            provider_defaults.get("provider")
            or current_app.config.get("AI_PROVIDER")
            or ""
        ).strip().lower()
        selected_model_id = ""

        if provider == "ollama":
            selected_model_id = str(
                provider_defaults.get("ollama_model_id")
                or current_app.config.get("AI_OLLAMA_MODEL")
                or current_app.config.get("AI_MODEL_NAME")
                or ""
            ).strip()
        elif provider == "huggingface":
            selected_model_id = str(
                provider_defaults.get("huggingface_model_id")
                or current_app.config.get("AI_MODEL_NAME")
                or ""
            ).strip()
        else:
            selected_model_id = str(
                provider_defaults.get("model_name")
                or current_app.config.get("AI_MODEL_NAME")
                or ""
            ).strip()

        return {
            "provider": provider or None,
            "model_id": selected_model_id or None,
            "family_id": family_id_from_model_id(selected_model_id) if selected_model_id else None,
        }

    @staticmethod
    def _extract_available_model_ids(payload: dict[str, Any]) -> dict[str, set[str]]:
        """Build provider-indexed model id sets from model inventory payload."""
        provider_models: dict[str, set[str]] = {
            "ollama": set(),
            "huggingface": set(),
        }

        ollama_payload = payload.get("ollama")
        if isinstance(ollama_payload, dict):
            models = ollama_payload.get("models")
            if isinstance(models, list):
                for model in models:
                    if not isinstance(model, dict):
                        continue
                    model_id = str(model.get("id") or "").strip()
                    if model_id:
                        provider_models["ollama"].add(model_id.lower())

        huggingface_payload = payload.get("huggingface_local")
        if isinstance(huggingface_payload, dict):
            models = huggingface_payload.get("models")
            if isinstance(models, list):
                for model in models:
                    if not isinstance(model, dict):
                        continue
                    model_id = str(model.get("id") or "").strip()
                    if model_id:
                        provider_models["huggingface"].add(model_id.lower())

        return provider_models

    @staticmethod
    def _resolve_initiated_by(payload: dict[str, Any]) -> str:
        """Resolve actor identifier used for AI interaction auditing."""
        if getattr(current_user, "is_authenticated", False):
            return str(
                current_user.get_id()
                or getattr(current_user, "email", "authenticated_user")
            )
        if payload.get("user"):
            return str(payload["user"])
        if payload.get("user_id"):
            return str(payload["user_id"])
        return "anonymous"

    @staticmethod
    def _resolve_provider(result: Any) -> str:
        """Resolve persisted provider name from response payload or app config."""
        provider = current_app.config.get("AI_PROVIDER") or "unknown"
        if isinstance(result, dict):
            meta_payload = result.get("meta")
            if isinstance(meta_payload, dict) and meta_payload.get("provider"):
                return str(meta_payload["provider"])
            if result.get("provider"):
                return str(result["provider"])
        return str(provider)

    @staticmethod
    def _resolve_ai_model_id(result: Any) -> int:
        provider_name = AIInteractionHelpers._resolve_provider(result)
        model = db.session.query(AIModel).filter(AIModel.provider == provider_name).first()
        if model is None:
            model = AIModel(provider=provider_name, active=True)
            db.session.add(model)
            db.session.flush()
        return int(model.id)

    @staticmethod
    def _resolve_prompt_link_id(payload: dict[str, Any]) -> int | None:
        selected_link_ids = payload.get("selected_accommodations_id_system_prompts_ids")
        if isinstance(selected_link_ids, list):
            for candidate in selected_link_ids:
                try:
                    resolved_id = int(candidate)
                except (TypeError, ValueError):
                    continue
                prompt_link = (
                    db.session.query(AccommodationSystemPrompt.id)
                    .filter(AccommodationSystemPrompt.id == resolved_id)
                    .first()
                )
                if prompt_link is not None:
                    return resolved_id
        link_id = payload.get("accommodations_id_system_prompts_id")
        if link_id is None:
            return None
        try:
            return int(link_id)
        except (TypeError, ValueError) as exc:
            _raise_bad_request_from_exception(exc, message="accommodations_id_system_prompts_id must be an integer")

    @staticmethod
    def _resolve_chat_id(payload: dict[str, Any]) -> int | None:
        """Extract optional chat id and validate integer shape when present."""
        chat_id = payload.get("chat_id")
        if chat_id is None:
            return None
        try:
            return int(chat_id)
        except (TypeError, ValueError) as exc:
            _raise_bad_request_from_exception(
                exc,
                message="chat_id must be an integer",
            )

    @staticmethod
    def _build_interaction_persistence_payload(payload: dict[str, Any], result: Any) -> dict[str, int | None]:
        """Resolve and validate FK inputs needed for interaction persistence."""
        chat_id = AIInteractionHelpers._resolve_chat_id(payload)
        prompt_link_id = AIInteractionHelpers._resolve_prompt_link_id(payload)
        if prompt_link_id is not None:
            _require_record("accommodation_system_prompt", AccommodationSystemPrompt, prompt_link_id)

        return {
            "chat_id": chat_id,
            "prompt_link_id": prompt_link_id,
            "model_id": AIInteractionHelpers._resolve_ai_model_id(result),
        }

    @staticmethod
    def _sync_chat_latest_interaction(chat_id: int | None, interaction_id: int) -> None:
        """Attach latest AI interaction id onto the chat when chat linkage exists."""
        if chat_id is None:
            return

        chat = _require_record("chat", Chat, chat_id)
        chat.ai_interaction_id = interaction_id

    @staticmethod
    def _persist_ai_interaction(
        payload: dict[str, Any], prompt: str, result: Any
    ) -> tuple[Any, int] | None:
        """Persist an AI interaction; return error response tuple when persistence fails."""
        interaction_repo = AIInteractionRepository(AIInteraction)

        try:
            normalized = AIInteractionHelpers._normalize_interaction_response(result)
            persistence_ids = AIInteractionHelpers._build_interaction_persistence_payload(payload, result)

            interaction = interaction_repo.create(
                db.session,
                prompt=prompt,
                response_text=normalized["assistant_text"],
                chat_id=persistence_ids["chat_id"],
                ai_model_id=persistence_ids["model_id"],
                accommodations_id_system_prompts_id=persistence_ids["prompt_link_id"],
            )
            AIInteractionHelpers._sync_chat_latest_interaction(persistence_ids["chat_id"], interaction.id)

            db.session.commit()
        except SQLAlchemyError as exc:
            db.session.rollback()
            return (
                jsonify(
                    {
                        "error": {
                            "code": "persistence_error",
                            "message": "Failed to persist AI interaction",
                            "details": {"exception": exc.__class__.__name__},
                        }
                    }
                ),
                500,
            )

        return None

    @staticmethod
    def _resolve_system_instructions(payload: dict[str, Any]) -> str:
        """Resolve DB backed system instructions for AI providers"""
        prompt_link_id = AIInteractionHelpers._resolve_prompt_link_id(payload)
        if prompt_link_id is None:
            return ""

        prompt_link = _require_record("accommodation_system_prompt", AccommodationSystemPrompt, prompt_link_id)
        parts = [
            (prompt_link.system_prompt.text or "").strip() if prompt_link.system_prompt else "",
            (prompt_link.accommodation.details or "").strip() if prompt_link.accommodation else ""
        ]

        return "\n\n".join(p for p in parts if p)


_extract_response_text = AIInteractionHelpers._extract_response_text
_truncate_debug_payload = AIInteractionHelpers._truncate_debug_payload
_strip_prompt_template_echo = AIInteractionHelpers._strip_prompt_template_echo
_normalize_interaction_response = AIInteractionHelpers._normalize_interaction_response
_resolve_selected_model = AIInteractionHelpers._resolve_selected_model
_extract_available_model_ids = AIInteractionHelpers._extract_available_model_ids
_resolve_initiated_by = AIInteractionHelpers._resolve_initiated_by
_resolve_system_instructions = AIInteractionHelpers._resolve_system_instructions
_resolve_provider = AIInteractionHelpers._resolve_provider
_resolve_ai_model_id = AIInteractionHelpers._resolve_ai_model_id
_resolve_prompt_link_id = AIInteractionHelpers._resolve_prompt_link_id
_resolve_chat_id = AIInteractionHelpers._resolve_chat_id
_build_interaction_persistence_payload = AIInteractionHelpers._build_interaction_persistence_payload
_sync_chat_latest_interaction = AIInteractionHelpers._sync_chat_latest_interaction
_resolve_session_model_selection = AIInteractionHelpers._resolve_session_model_selection
_persist_ai_interaction = AIInteractionHelpers._persist_ai_interaction
