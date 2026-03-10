from typing import Any
from flask import current_app, jsonify, session
from flask_login import current_user
from sqlalchemy.exc import SQLAlchemyError

from ...db.interfaces import InteractionRepositoryFactory
from ...db.repositories.interaction_repo import AIInteractionRepository
from ...models import AIInteraction, AIModel, Chat, CourseClass
from ...models.ai_interaction import AccommodationSystemPrompt
from ...services.ai_pipeline.model_catelog import family_id_from_model_id, resolve_model_selection
from ...api.v1.routes import _raise_bad_request_from_exception, _require_record, db
from .mutations import AIInteractionMutations
from .validators import AIInteractionValidator
from .interfaces import AIInteractionMutationsInterface, AIInteractionValidatorInterface


class AIInteractionOps:
    _EMPTY_ASSISTANT_NOTE = "assistant_empty_after_normalization"
    interaction_repository_factory: InteractionRepositoryFactory = AIInteractionRepository
    _validator: AIInteractionValidatorInterface = AIInteractionValidator
    _mutations: AIInteractionMutationsInterface = AIInteractionMutations

    @staticmethod
    def _extract_response_text(result: Any) -> str:
        """Normalize provider payload into a storable interaction response string."""
        normalized = AIInteractionOps._normalize_interaction_response(result)
        return normalized["assistant_text"]

    # moved to AIInteractionMutations.truncate_debug_payload.
    # @staticmethod
    # def _truncate_debug_payload(value: Any, *, limit: int = 1200) -> str:
    #     return AIInteractionMutations.truncate_debug_payload(value, limit=limit)

    # moved to AIInteractionMutations.strip_prompt_template_echo to reduce helper duplication.
    # @staticmethod
    # def _strip_prompt_template_echo(text: str) -> str:
    #     return AIInteractionMutations.strip_prompt_template_echo(text)

    @staticmethod
    def _normalize_interaction_response(result: Any) -> dict[str, Any]:
        """Normalize provider payload into canonical UI response shape."""
        envelope = AIInteractionOps._mutations.normalize_payload(result)
        normalized_response: dict[str, Any] = {
            "assistant_text": AIInteractionOps._mutations.strip_prompt_template_echo(envelope.assistant_text),
            "confidence": envelope.confidence,
            "notes": envelope.notes,
            "meta": envelope.meta.copy() if isinstance(envelope.meta, dict) else {},
        }

        # Keep raw provider payload only in debug metadata for investigation.
        if not normalized_response["assistant_text"]:
            normalized_response["notes"].append(AIInteractionOps._EMPTY_ASSISTANT_NOTE)
            normalized_response["meta"].setdefault("debug", {})[
                "raw_payload_preview"] = AIInteractionOps._mutations.truncate_debug_payload(result)

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

        model_id = AIInteractionOps._validator.to_clean_text(persisted.get("model_id"))
        provider = AIInteractionOps._validator.to_clean_text(persisted.get("provider"), lower=True)
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
        selected = AIInteractionOps._resolve_session_model_selection()
        if selected is not None:
            return selected
        provider_defaults = payload.get("provider_defaults")
        if not isinstance(provider_defaults, dict):
            provider_defaults = {}

        provider = AIInteractionOps._validator.to_clean_text(
            provider_defaults.get("provider")
            or current_app.config.get("AI_PROVIDER")
            or "",
            lower=True,
        )
        selected_model_id = ""

        if provider == "ollama":
            selected_model_id = AIInteractionOps._validator.to_clean_text(
                provider_defaults.get("ollama_model_id")
                or current_app.config.get("AI_OLLAMA_MODEL")
                or current_app.config.get("AI_MODEL_NAME")
                or ""
            )
        elif provider == "huggingface":
            selected_model_id = AIInteractionOps._validator.to_clean_text(
                provider_defaults.get("huggingface_model_id")
                or current_app.config.get("AI_MODEL_NAME")
                or ""
            )
        else:
            selected_model_id = AIInteractionOps._validator.to_clean_text(
                provider_defaults.get("model_name")
                or current_app.config.get("AI_MODEL_NAME")
                or ""
            )

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
                    model_id = AIInteractionOps._validator.to_clean_text(model.get("id"), lower=True)
                    if model_id:
                        provider_models["ollama"].add(model_id)

        huggingface_payload = payload.get("huggingface_local")
        if isinstance(huggingface_payload, dict):
            models = huggingface_payload.get("models")
            if isinstance(models, list):
                for model in models:
                    if not isinstance(model, dict):
                        continue
                    model_id = AIInteractionOps._validator.to_clean_text(model.get("id"))
                    if model_id:
                        provider_models["huggingface"].update(
                            AIInteractionOps._expand_huggingface_model_aliases(model_id)
                        )

        return provider_models

    @staticmethod
    def _resolve_provider_model_metadata(
            result: Any
    ) -> tuple[str, str, str | None, str | None]:

        provider_name = AIInteractionOps._validator.to_clean_text(AIInteractionOps._resolve_provider(result),
                                                                  lower=True) or "unknown"
        source: str | None = None
        path: str | None = None

        model_name = (
                current_app.config.get("AI_OLLAMA_MODEL")
                or current_app.config.get("AI_MODEL_NAME")
                or ""
        )
        if isinstance(result, dict):
            meta_payload = result.get("meta")
            if isinstance(meta_payload, dict):
                model_name = (
                        meta_payload.get("model_id")
                        or meta_payload.get("model")
                        or meta_payload.get("name")
                        or model_name
                )
                source = AIInteractionOps._validator.to_clean_text(meta_payload.get("source")) or None
                path = AIInteractionOps._validator.to_clean_text(meta_payload.get("path")) or None
            model_name = (
                    result.get("model_id")
                    or result.get("model")
                    or result.get("name")
                    or model_name
            )

        normalized_model_id = AIInteractionOps._validator.to_clean_text(model_name) or f"{provider_name}-default"
        return provider_name, normalized_model_id, source, path

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
        provider_name, model_id, source, path = AIInteractionOps._resolve_provider_model_metadata(result)
        # model = db.session.query(AIModel).filter(AIModel.provider == provider_name).first()
        model = (
            db.session.query(AIModel)
            .filter(AIModel.provider == provider_name, AIModel.model_id == model_id)
            .first()
        )

        if model is None:
            # model = AIModel(provider=provider_name, active=True)
            model = AIModel(
                provider=provider_name,
                model_id=model_id,
                source=source,
                path=path,
                active=True
            )
            db.session.add(model)
            db.session.flush()
            return int(model_id)

        model.active = True
        if source:
            model.source = source
        if path:
            model.path = path
        return int(model_id)

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

        selected_feature_ids = payload.get("selected_accessibility_link_ids")
        if isinstance(selected_feature_ids, list):
            normalized_feature_ids: list[int] = []
            for f_id in selected_feature_ids:
                try:
                    normalized_feature_ids.append(int(f_id))
                except (TypeError, ValueError):
                    continue
                    # I should find some error catching for this here in a future patch

            # this could cause too much DB lookup, need to watchout for how many query actions happen when using the app
            if normalized_feature_ids:
                mapped_link = (
                    db.session.query(AccommodationSystemPrompt.id)
                    .filter(AccommodationSystemPrompt.accommodation_id.in_(normalized_feature_ids))
                    .order_by(AccommodationSystemPrompt.id.asc())
                    .first()
                )
                if mapped_link is not None:
                    return int(mapped_link[0])

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
    def _expand_huggingface_model_aliases(model_id: str) -> set[str]:
        """Expand local cache ids into canonical huggingface repo-id variants."""
        normalized = AIInteractionOps._validator.to_clean_text(model_id, lower=True)
        if not normalized:
            return set()

        aliases = {normalized}

        # HuggingFace cache folders typically look like models--org--repo.
        if normalized.startswith("models--"):
            repo_id = normalized[len("models--"):].replace("--", "/")
            if repo_id:
                aliases.add(repo_id)

        return aliases

    @staticmethod
    def _build_interaction_persistence_payload(payload: dict[str, Any], result: Any) -> dict[str, int | None]:
        """Resolve and validate FK inputs needed for interaction persistence."""
        chat_id = AIInteractionOps._resolve_chat_id(payload)
        prompt_link_id = AIInteractionOps._resolve_prompt_link_id(payload)
        if prompt_link_id is not None:
            _require_record("accommodation_system_prompt", AccommodationSystemPrompt, prompt_link_id)

        return {
            "chat_id": chat_id,
            "prompt_link_id": prompt_link_id,
            "model_id": AIInteractionOps._resolve_ai_model_id(result),
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
        interaction_repo = AIInteractionOps.interaction_repository_factory(AIInteraction)

        try:
            normalized = AIInteractionOps._normalize_interaction_response(result)
            persistence_ids = AIInteractionOps._build_interaction_persistence_payload(payload, result)

            interaction = interaction_repo.create(
                db.session,
                prompt=prompt,
                response_text=normalized["assistant_text"],
                chat_id=persistence_ids["chat_id"],
                ai_model_id=persistence_ids["model_id"],
                accommodations_id_system_prompts_id=persistence_ids["prompt_link_id"],
            )
            AIInteractionOps._sync_chat_latest_interaction(persistence_ids["chat_id"], interaction.id)

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
        prompt_link_id = AIInteractionOps._resolve_prompt_link_id(payload)
        prompt_link = None

        if prompt_link_id is not None:
            prompt_link = _require_record(
                "accommodation_system_prompt",
                AccommodationSystemPrompt,
                prompt_link_id
            )
        class_id: int | None = None

        raw_class_id = payload.get("class_id")

        if raw_class_id is not None:
            try:
                class_id = int(raw_class_id)
            except (TypeError, ValueError) as e:
                _raise_bad_request_from_exception(
                    e,
                    message="class id must be an integer/number"
                )
        else:
            chat_id = AIInteractionOps._resolve_chat_id(payload)
            if chat_id is not None:
                chat = _require_record("chat", Chat, chat_id)
                class_id = int(chat.class_id)

        class_record = _require_record(
            "class",
            CourseClass,
            class_id
        ) if class_id is not None else None

        parts = [
            AIInteractionOps._validator.to_clean_text(
                prompt_link.system_prompt.text) if prompt_link and prompt_link.system_prompt else "",
            AIInteractionOps._validator.to_clean_text(
                prompt_link.accommodation.details) if prompt_link and prompt_link.accommodation else "",
            AIInteractionOps._validator.to_clean_text(class_record.description) if class_record else ""
        ]

        return "\n\n".join(p for p in parts if p)


__all__ = [
    "AIInteractionOps",
    "resolve_model_selection",
]