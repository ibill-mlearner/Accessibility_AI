from typing import Any
from flask import current_app, jsonify, session
from flask_login import current_user
from sqlalchemy.exc import SQLAlchemyError

from ...api.errors import BadRequestError
from ...db.interfaces import InteractionRepositoryFactory
from ...db.repositories.interaction_repo import AIInteractionRepository
from ...models import AIInteraction, AIModel, Chat, UserAccessibilityFeature
from ...models.ai import AccommodationSystemPrompt
from ...api.v1.routes import _raise_bad_request_from_exception, _require_record, db
from .mutations import AIInteractionMutations
from .validators import AIInteractionValidator, ModelSelectionError
from .interfaces import AIInteractionMutationsInterface, AIInteractionValidatorInterface


class AIPipelineUpstreamError(RuntimeError):
    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.details = details or {}


def resolve_provider_model_selection(payload: dict[str, Any], ai_service: Any, *, allow_session: bool = True, require_explicit: bool = False) -> dict[str, str]:
    inventory = ai_service.list_available_models() if hasattr(ai_service, "list_available_models") else {}
    persisted = session.get("ai_model_selection") if allow_session and isinstance(session.get("ai_model_selection"), dict) else None
    return AIInteractionValidator.resolve_model_selection(
        payload,
        inventory=inventory,
        persisted=persisted,
        config_provider=str(current_app.config.get("AI_PROVIDER") or "huggingface"),
        config_model_id=str(current_app.config.get("AI_MODEL_NAME") or ""),
        require_explicit=require_explicit,
    )



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
            "family_id": None,
        }

    @staticmethod
    def _resolve_default_model_id(provider: str, provider_defaults: dict[str, Any]) -> str:
        _ = provider
        value = provider_defaults.get("huggingface_model_id") or provider_defaults.get("model_name") or current_app.config.get("AI_MODEL_NAME") or ""
        return AIInteractionOps._validator.to_clean_text(value)

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
            provider_defaults.get("provider") or current_app.config.get("AI_PROVIDER") or "",
            lower=True,
        )
        selected_model_id = AIInteractionOps._resolve_default_model_id(provider, provider_defaults)
        return {
            "provider": provider or None,
            "model_id": selected_model_id or None,
            "family_id": None,
        }

    @staticmethod
    def _extract_available_model_ids(payload: dict[str, Any]) -> dict[str, set[str]]:
        """Build provider-indexed model id sets from model inventory payload."""
        provider_models: dict[str, set[str]] = {
            "huggingface": set(),
        }

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
    def _default_model_name() -> str:
        return current_app.config.get("AI_MODEL_NAME") or ""

    @staticmethod
    def _model_metadata_from_result(result: Any, model_name: str) -> tuple[str, str | None, str | None]:
        source: str | None = None
        path: str | None = None
        if not isinstance(result, dict):
            return model_name, source, path

        meta_payload = result.get("meta")
        if isinstance(meta_payload, dict):
            model_name = meta_payload.get("model_id") or meta_payload.get("model") or meta_payload.get("name") or model_name
            source = AIInteractionOps._validator.to_clean_text(meta_payload.get("source")) or None
            path = AIInteractionOps._validator.to_clean_text(meta_payload.get("path")) or None

        model_name = result.get("model_id") or result.get("model") or result.get("name") or model_name
        return model_name, source, path

    @staticmethod
    def _resolve_provider_model_metadata(result: Any) -> tuple[str, str, str | None, str | None]:
        provider_name = AIInteractionOps._validator.to_clean_text(AIInteractionOps._resolve_provider(result), lower=True) or "unknown"
        model_name, source, path = AIInteractionOps._model_metadata_from_result(result, AIInteractionOps._default_model_name())
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
            model = AIModel(
                provider=provider_name,
                model_id=model_id,
                source=source,
                path=path,
                active=True
            )
            db.session.add(model)
            db.session.flush()
            resolved_model_pk = int(model.id)
            return resolved_model_pk

        model.active = True
        if source:
            model.source = source
        if path:
            model.path = path
        resolved_model_pk = int(model.id)
        return resolved_model_pk

    @staticmethod
    def _first_valid_prompt_link_id(selected_link_ids: Any) -> int | None:
        if not isinstance(selected_link_ids, list):
            return None
        for candidate in selected_link_ids:
            try:
                resolved_id = int(candidate)
            except (TypeError, ValueError):
                continue
            prompt_link = db.session.query(AccommodationSystemPrompt.id).filter(AccommodationSystemPrompt.id == resolved_id).first()
            if prompt_link is not None:
                return resolved_id
        return None


    @staticmethod
    def _resolve_user_selected_feature_ids(user_id: int | None) -> list[int]:
        if user_id is None:
            return []
        rows = (
            db.session.query(UserAccessibilityFeature.accommodation_id)
            .filter(
                UserAccessibilityFeature.user_id == int(user_id),
                UserAccessibilityFeature.enabled.is_(True),
            )
            .order_by(UserAccessibilityFeature.accommodation_id.asc())
            .all()
        )
        return [int(row[0]) for row in rows]

    @staticmethod
    def _mapped_prompt_link_from_features(selected_feature_ids: Any) -> int | None:
        if not isinstance(selected_feature_ids, list):
            return None
        normalized_feature_ids: list[int] = []
        for feature_id in selected_feature_ids:
            try:
                normalized_feature_ids.append(int(feature_id))
            except (TypeError, ValueError):
                continue
        if not normalized_feature_ids:
            return None
        mapped_link = (
            db.session.query(AccommodationSystemPrompt.id)
            .filter(AccommodationSystemPrompt.accommodation_id.in_(normalized_feature_ids))
            .order_by(AccommodationSystemPrompt.id.asc())
            .first()
        )
        return int(mapped_link[0]) if mapped_link is not None else None

    @staticmethod
    def _resolve_prompt_link_id(payload: dict[str, Any]) -> int | None:
        selected_link = AIInteractionOps._first_valid_prompt_link_id(payload.get("selected_accommodations_id_system_prompts_ids"))
        if selected_link is not None:
            return selected_link

        mapped_link = AIInteractionOps._mapped_prompt_link_from_features(payload.get("selected_accessibility_link_ids"))
        if mapped_link is not None:
            return mapped_link

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
    def _create_interaction_record(payload: dict[str, Any], prompt: str, result: Any) -> None:
        interaction_repo = AIInteractionOps.interaction_repository_factory(AIInteraction)
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

    @staticmethod
    def _persist_ai_interaction(payload: dict[str, Any], prompt: str, result: Any) -> tuple[Any, int] | None:
        """Persist an AI interaction; return error response tuple when persistence fails."""
        try:
            AIInteractionOps._create_interaction_record(payload, prompt, result)
            db.session.commit()
        except SQLAlchemyError as exc:
            db.session.rollback()
            return jsonify({"error": {"code": "persistence_error", "message": "Failed to persist AI interaction", "details": {"exception": exc.__class__.__name__}}}), 500
        return None

    @staticmethod
    def _resolve_class_id(payload: dict[str, Any]) -> int | None:
        raw_class_id = payload.get("class_id")
        if raw_class_id is not None:
            try:
                return int(raw_class_id)
            except (TypeError, ValueError) as exc:
                _raise_bad_request_from_exception(exc, message="class id must be an integer/number")

        chat_id = AIInteractionOps._resolve_chat_id(payload)
        if chat_id is None:
            return None
        chat = _require_record("chat", Chat, chat_id)
        return int(chat.class_id)

    @staticmethod
    def _resolve_system_instructions(payload: dict[str, Any]) -> str:
        """Resolve accessibility-only system instructions for AI providers."""
        selected_feature_ids = payload.get("selected_accessibility_link_ids")
        normalized_feature_ids: list[int] = []
        if isinstance(selected_feature_ids, list):
            for feature_id in selected_feature_ids:
                try:
                    normalized_feature_ids.append(int(feature_id))
                except (TypeError, ValueError):
                    continue

        parts: list[str] = []
        if normalized_feature_ids:
            rows = (
                db.session.query(UserAccessibilityFeature)
                .filter(UserAccessibilityFeature.accommodation_id.in_(normalized_feature_ids))
                .order_by(UserAccessibilityFeature.accommodation_id.asc())
                .all()
            )
            for row in rows:
                if row.accommodation and row.accommodation.details:
                    parts.append(AIInteractionOps._validator.to_clean_text(row.accommodation.details))

        if not parts:
            prompt_link_id = AIInteractionOps._resolve_prompt_link_id(payload)
            prompt_link = _require_record("accommodation_system_prompt", AccommodationSystemPrompt, prompt_link_id) if prompt_link_id is not None else None
            if prompt_link and prompt_link.accommodation and prompt_link.accommodation.details:
                parts.append(AIInteractionOps._validator.to_clean_text(prompt_link.accommodation.details))

        return "\n\n".join(part for part in parts if part)


__all__ = [
    "AIInteractionOps",
    "resolve_model_selection",
]

from pathlib import Path
from flask import Flask


def _discover_model_ids(models_root: Path) -> list[str]:
    if not models_root.exists() or not models_root.is_dir():
        return []
    return sorted(child.name for child in models_root.iterdir() if child.is_dir())


def _resolve_local_models_root(app: Flask) -> Path:
    project_root = Path(app.root_path).resolve().parents[1]
    thin_models_root = project_root / "app" / "services" / "ai_pipeline_thin" / "models"
    if thin_models_root.exists() and thin_models_root.is_dir():
        return thin_models_root
    return Path(app.instance_path) / "models"


def _relative_model_path(models_root: Path, model_id: str) -> str:
    return (models_root / model_id).as_posix()


def _index_records_by_model_id(records: list[AIModel]) -> dict[str, AIModel]:
    return {record.model_id: record for record in records}


def _upsert_discovered_models(*, provider: str, models_root: Path, discovered_model_ids: list[str], by_model_id: dict[str, AIModel], default_model_id: str) -> int:
    counter = 0
    for model_id in discovered_model_ids:
        record = by_model_id.get(model_id)
        model_path = _relative_model_path(models_root, model_id)
        is_default = bool(default_model_id and model_id == default_model_id)
        if record is None:
            db.session.add(AIModel(provider=provider, model_id=model_id, source="instance_models", path=model_path, active=is_default))
            counter += 1
            continue
        record.source = "instance_models"
        record.path = model_path
        record.active = is_default
        counter += 1
    return counter


def _mark_stale_models_inactive(records: list[AIModel], discovered_set: set[str]) -> int:
    marked_inactive = 0
    for record in records:
        if record.model_id in discovered_set:
            continue
        if record.active:
            marked_inactive += 1
        record.active = False
    return marked_inactive


def sync_ai_models_with_local_inventory(app: Flask) -> dict[str, int | str | None]:
    # TODO(ai-pipeline-thin): move model inventory source-of-truth to the new pipeline adapter
    # so this sync reads available model ids from the pipeline runtime instead of local folders.
    provider = AIInteractionValidator.to_clean_text(app.config.get("AI_PROVIDER"), lower=True) or "huggingface"
    models_root = _resolve_local_models_root(app)
    discovered_model_ids = _discover_model_ids(models_root)
    default_model_id = str(app.config.get("AI_MODEL_NAME") or "").strip()
    records = db.session.query(AIModel).filter(AIModel.provider == provider).all()
    by_model_id = _index_records_by_model_id(records)
    discovered_set = set(discovered_model_ids)
    upserted = _upsert_discovered_models(provider=provider, models_root=models_root, discovered_model_ids=discovered_model_ids, by_model_id=by_model_id, default_model_id=default_model_id)
    marked_inactive = _mark_stale_models_inactive(records, discovered_set)
    if default_model_id:
        default_record = by_model_id.get(default_model_id)
        if default_record is None:
            default_path = _relative_model_path(models_root, default_model_id)
            db.session.add(AIModel(provider=provider, model_id=default_model_id, source="config_default", path=default_path, active=True))
            upserted += 1
        else:
            default_record.active = True
    db.session.commit()
    return {"provider": provider, "discovered": len(discovered_model_ids), "upserted": upserted, "marked_inactive": marked_inactive, "default_model_id": default_model_id or None}


def compose_system_prompt(system_instructions: str, payload: dict[str, Any]) -> str | None:
    configured_guardrail = str(current_app.config.get("AI_SYSTEM_GUARDRAIL_PROMPT") or "").strip()
    request_system_prompt = str(payload.get("system_prompt") or "").strip()
    parts = [configured_guardrail, (system_instructions or "").strip(), request_system_prompt]
    combined = "\n\n".join(part for part in parts if part)
    return combined or None


SAFE_MODEL_CONTACT_ERROR_MESSAGE = "There was a problem with the model contact the administrator."

def validate_runtime_model_selection(payload: dict[str, Any], ai_service: Any) -> tuple[dict[str, Any], int] | None:
    """Validate/resolve runtime selection through the canonical resolver."""
    try:
        _ = resolve_provider_model_selection(payload, ai_service)
    except ModelSelectionError as exc:
        return exc.payload, exc.status_code
    return None

def classify_upstream_error(
    exc: AIPipelineUpstreamError,
    *,
    runtime_model_selection: dict[str, Any],
    request_id: str,
) -> tuple[str, int, dict[str, Any]]:
    details = exc.details if isinstance(exc.details, dict) else {}
    runtime_selection = runtime_model_selection if isinstance(runtime_model_selection, dict) else {}
    upstream_status = details.get("upstream_status")
    selected_source = AIInteractionOps._validator.to_clean_text(runtime_selection.get("source"))
    source = str(details.get("source") or selected_source or "provider_runtime")
    message_lower = str(exc).lower()
    error_code = str(details.get("error_code") or "upstream_error")
    status_code = 502
    if error_code == "provider_unavailable":
        status_code = 503
    if isinstance(upstream_status, int):
        if upstream_status in (401, 403):
            error_code = "provider_auth_failed"
        elif upstream_status == 404:
            error_code = "provider_model_not_found"
    if error_code == "upstream_error":
        if "gated" in message_lower and "model" in message_lower:
            error_code = "provider_gated_model"
        elif any(token in message_lower for token in ("unauthorized", "invalid token", "forbidden", "authentication")):
            error_code = "provider_auth_failed"
        elif any(token in message_lower for token in ("not found", "no such model", "404")):
            error_code = "provider_model_not_found"
    selected_model_id = AIInteractionOps._validator.to_clean_text(runtime_selection.get("model_id"))
    raw_model_id = AIInteractionOps._validator.to_clean_text(selected_model_id or details.get("model_id") or "")
    normalized_model_id = AIInteractionOps._validator.to_clean_model_id(raw_model_id) or "unknown"

    normalized_details = {
        **details,
        "source": source,
        "provider": AIInteractionOps._validator.to_clean_text(runtime_selection.get("provider"), lower=True)
        or details.get("provider")
        or "unknown",
        "model_id": raw_model_id or "unknown",
        "model_id_normalized": normalized_model_id,
        "upstream_status": upstream_status,
        "request_id": request_id
    }

    return error_code, status_code, normalized_details


def build_prompt_and_messages(payload: dict[str, Any]):
    prompt = (payload.get("prompt") or "").strip()
    raw_messages = payload.get("messages")
    messages = raw_messages if isinstance(raw_messages, list) else []
    if not prompt:
        for message in reversed(messages):
            if not isinstance(message, dict):
                continue
            if (message.get("role") or "").lower() != "user":
                continue
            content = message.get("content")
            if isinstance(content, str) and content.strip():
                prompt = content.strip()
                break
    return prompt, messages


def build_context_and_system_instructions(payload: dict[str, Any], messages: list[dict[str, Any]]) -> tuple[dict[str, Any], str]:
    system_instructions = AIInteractionOps._resolve_system_instructions(payload)
    context_payload = payload.get("context")
    if not isinstance(context_payload, dict):
        context_payload = {}

    explicit_selected_ids = payload.get("selected_accessibility_link_ids")
    if payload.get("use_user_feature_preferences"):
        selected_ids = AIInteractionOps._resolve_user_selected_feature_ids(getattr(current_user, "id", None))
        payload["selected_accessibility_link_ids"] = selected_ids
        context_payload["selected_accessibility_link_ids"] = selected_ids
    elif isinstance(explicit_selected_ids, list):
        selected_ids = [
            int(feature_id)
            for feature_id in explicit_selected_ids
            if isinstance(feature_id, int) and feature_id > 0
        ]
        payload["selected_accessibility_link_ids"] = selected_ids
        context_payload["selected_accessibility_link_ids"] = selected_ids

    if messages and "messages" not in context_payload:
        context_payload["messages"] = messages
    return context_payload, system_instructions


def resolve_model_override(payload: dict[str, Any], ai_service: Any, context_payload: dict[str, Any], request_id: str) -> None:
    """Compatibility shim now delegated to the canonical model resolver."""
    _ = request_id
    selected = resolve_provider_model_selection(payload, ai_service)
    context_payload["runtime_model_selection"] = selected


def ensure_runtime_model_selection(
    payload: dict[str, Any],
    ai_service: Any,
    context_payload: dict[str, Any],
    request_id: str,
) -> tuple[dict[str, Any], int] | None:
    """Resolve and attach runtime model selection using canonical model resolver."""
    _ = request_id
    try:
        selected = resolve_provider_model_selection(payload, ai_service)
    except ModelSelectionError as exc:
        return exc.payload, exc.status_code
    context_payload["runtime_model_selection"] = selected
    return None

def prepare_interaction_inputs(payload: dict[str, Any]) -> dict[str, Any]:
    prompt, messages = build_prompt_and_messages(payload)
    context_payload, system_instructions = build_context_and_system_instructions(payload, messages)
    return {
        "prompt": prompt,
        "messages": messages,
        "context_payload": context_payload,
        "system_prompt": compose_system_prompt(system_instructions, payload),
        "request_id": str(payload.get("request_id") or "n/a"),
    }


def create_pipeline_request(
    payload: dict[str, Any],
    *,
    prompt: str,
    messages: list[dict[str, Any]],
    system_prompt: str | None,
    context_payload: dict[str, Any],
    chat_id: int | None,
    initiated_by: str,
) -> dict[str, Any]:
    return dict(
        prompt=prompt,
        messages=messages,
        system_prompt=system_prompt,
        context=context_payload,
        chat_id=chat_id,
        initiated_by=initiated_by,
        class_id=payload.get("class_id"),
        user_id=payload.get("user_id"),
        request_id=payload.get("request_id"),
    )


def run_pipeline(ai_service: Any, dto: dict[str, Any], request_id: str, prompt: str) -> Any:
    _ = prompt

    runtime_selection = dto.context.get("runtime_model_selection") if isinstance(dto.context, dict) else {}
    if not isinstance(runtime_selection, dict):
        runtime_selection = {}

    configured_provider = AIInteractionOps._validator.to_clean_text(
        current_app.config.get("AI_PROVIDER") or "",
        lower=True,
    )
    provider = AIInteractionOps._validator.to_clean_text(runtime_selection.get("provider"), lower=True) or configured_provider

    default_model_from_config = current_app.config.get("AI_MODEL_NAME")
    resolved_runtime_selection = {
        **runtime_selection,
        "provider": provider or runtime_selection.get("provider"),
        "model_id": AIInteractionOps._validator.to_clean_text(runtime_selection.get("model_id"))
        or AIInteractionOps._validator.to_clean_text(default_model_from_config or ""),
        "source": AIInteractionOps._validator.to_clean_text(runtime_selection.get("source")) or runtime_selection.get("source"),
    }

    try:
        return ai_service.run_interaction(dto.get("prompt") or "", context=dto.get("context") or {}, messages=dto.get("messages") or [], system_prompt=dto.get("system_prompt"), request_id=dto.get("request_id"), chat_id=dto.get("chat_id"), initiated_by=dto.get("initiated_by"), class_id=dto.get("class_id"), user_id=dto.get("user_id"))
    except AIPipelineUpstreamError as exc:
        error_code, status_code, normalized_details = classify_upstream_error(
            exc,
            runtime_model_selection=resolved_runtime_selection,
            request_id=request_id,
        )
        current_app.logger.error(
            "ai_interaction.pipeline.upstream_error request_id=%s code=%s status=%s details=%s",
            request_id,
            error_code,
            status_code,
            normalized_details,
        )
        safe_error_codes = {
            "runtime_unavailable",
            "provider_unavailable",
            "provider_auth_failed",
            "provider_model_not_found",
            "provider_gated_model",
            "upstream_error",
        }
        response_message = SAFE_MODEL_CONTACT_ERROR_MESSAGE if error_code in safe_error_codes else str(exc)
        return jsonify({"error": {"code": error_code, "message": response_message, "details": normalized_details}}), status_code


_extract_response_text = AIInteractionOps._extract_response_text
_truncate_debug_payload = AIInteractionMutations.truncate_debug_payload
_strip_prompt_template_echo = AIInteractionMutations.strip_prompt_template_echo
_normalize_interaction_response = AIInteractionOps._normalize_interaction_response
_resolve_selected_model = AIInteractionOps._resolve_selected_model
_extract_available_model_ids = AIInteractionOps._extract_available_model_ids
_resolve_initiated_by = AIInteractionOps._resolve_initiated_by
_resolve_system_instructions = AIInteractionOps._resolve_system_instructions
_resolve_provider = AIInteractionOps._resolve_provider
_resolve_ai_model_id = AIInteractionOps._resolve_ai_model_id
_resolve_prompt_link_id = AIInteractionOps._resolve_prompt_link_id
_resolve_chat_id = AIInteractionOps._resolve_chat_id
_build_interaction_persistence_payload = AIInteractionOps._build_interaction_persistence_payload
_sync_chat_latest_interaction = AIInteractionOps._sync_chat_latest_interaction
_resolve_session_model_selection = AIInteractionOps._resolve_session_model_selection
_persist_ai_interaction = AIInteractionOps._persist_ai_interaction
