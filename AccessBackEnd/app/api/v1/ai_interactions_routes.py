import time

from flask import current_app, jsonify

from flask_login import current_user, login_required

from ...utils.ai_checker import _normalize_interaction_response, _persist_ai_interaction, _resolve_chat_id, _resolve_initiated_by, prepare_interaction_inputs
from .routes import (
    _assert_chat_permissions,
    _publish,
    _read_json_object,
    _require_record,
    _serialize_record,
    _validate_payload,
    api_v1_bp,
    db,
)
from ...models import AIInteraction, Chat
from ...schemas.validation import AIInteractionPayloadSchema
from ...utils.chat_access import ChatAccessHelper
from ...services.ai_pipeline_contracts import AIPipelineServiceInterface
from ...services.ai_pipeline_runtime_selection import ModelSelectionError, resolve_provider_model_selection




def _log_payload(raw: dict, payload: dict) -> None:
    current_app.logger.debug(
        "api.ai.interactions.payload.raw path=%s json_keys=%s",
        "/api/v1/ai/interactions",
        sorted(raw.keys())
    )
    current_app.logger.debug(
        "api.ai.interactions.payload.validated keys=%s",
        sorted(payload.keys())
    )


def _log_request(payload: dict) -> None:
    user_identity = (
        getattr(current_user, "email", None)
        or getattr(current_user, "id", None)
        or "anonymous"
    )
    current_app.logger.debug(
        "api.ai_interactions.request method=%s path=%s user=%s json_keys=%s",
        "POST",
        "/api/v1/ai/interactions",
        user_identity,
        sorted(payload.keys()),
    )


def _log_interaction_start(payload: dict, request_id: str, prompt: str) -> None:
    current_app.logger.debug(
        "api.ai_interactions.create.start request_id=%s provider=%s model=%s timeout_seconds=%s prompt_len=%s messages_count=%s prompt_preview=%r",
        request_id,
        current_app.config.get("AI_PROVIDER"),
        current_app.config.get("AI_MODEL_NAME"),
        current_app.config.get("AI_TIMEOUT_SECONDS"),
        len(prompt),
        len(payload.get("messages")) if isinstance(payload.get("messages"), list) else 0,
        prompt[:200],
    )


def _publish_request_summary(prompt: str, messages: list[dict], payload: dict, system_prompt: str | None, system_instructions: bool) -> None:
    _publish(
        "api.ai_interaction_requested",
        {
            "has_prompt": bool(prompt),
            "has_messages": bool(messages),
            "has_system_prompt": bool(payload.get("system_prompt")),
            "has_guardrail_system_prompt": bool(current_app.config.get("AI_SYSTEM_GUARDRAIL_PROMPT")),
            "has_db_system_instructions": system_instructions,
            "has_composed_system_prompt": bool(system_prompt),
        },
    )


def _run(
    ai_service: AIPipelineServiceInterface,
    payload: dict,
    prepared: dict,
    chat_id: int | None,
    initiated_by: str,
):
    result = ai_service.run_interaction(
        prepared["prompt"],
        context=prepared["context_payload"],
        messages=prepared["messages"],
        system_prompt=prepared["system_prompt"],
        request_id=prepared["request_id"],
        chat_id=chat_id,
        initiated_by=initiated_by,
        class_id=payload.get("class_id"),
        user_id=payload.get("user_id"),
    )
    return _normalize_interaction_response(result)


def _warn_if_empty_response(request_id: str, normalized_result: dict) -> None:
    if not normalized_result.get("assistant_text"):
        current_app.logger.warning(
            "api.ai_interactions.normalize.empty_assistant request_id=%s provider=%s model=%s notes_count=%s",
            request_id,
            normalized_result["meta"].get("provider"),
            normalized_result["meta"].get("model"),
            len(normalized_result.get("notes") or []),
        )


def _persist_interaction(payload: dict, prompt: str, normalized_result: dict):
    return _persist_ai_interaction(payload, prompt, normalized_result)

def _validate_interaction_payload() -> tuple[dict, dict]:
    raw = _read_json_object()
    payload = _validate_payload(raw, AIInteractionPayloadSchema())
    return raw, payload


@api_v1_bp.post("/ai/interactions")
@login_required
def create_ai_interaction():
    """Run a single AI interaction.

    Runtime model resolution order is:
    1) explicit request override (`provider`/`model_id`) when allowed/valid,
    2) persisted session selection (`/api/v1/ai/selection`),
    3) app config default (`AI_PROVIDER` + `AI_MODEL_NAME`).

    Per-request/per-session resolution does not mutate app config at runtime.
    """
    raw, payload = _validate_interaction_payload()
    _log_payload(raw, payload)
    _log_request(payload)
    prepared = prepare_interaction_inputs(payload)
    _log_interaction_start(payload, prepared["request_id"], prepared["prompt"])
    _publish_request_summary(prepared["prompt"], prepared["messages"], payload, prepared["system_prompt"], bool(prepared["system_prompt"]))

    chat_state = _resolve_chat_id(payload)
    if chat_state is not None:
        chat = _require_record("chat", Chat, chat_state)
        deny = _assert_chat_permissions(chat)
        if deny is not None:
            return deny

    ai_service: AIPipelineServiceInterface = current_app.extensions["ai_service"]
    # Resolve runtime selection from request/session/config precedence without mutating
    # process-wide app config values for individual users.
    selection_input = {
        "provider": payload.get("provider"),
        "model_id": payload.get("model_id"),
    }
    try:
        selected_runtime = resolve_provider_model_selection(selection_input, ai_service)
    except ModelSelectionError as exc:
        return jsonify(exc.payload), exc.status_code

    prepared["context_payload"]["runtime_model_selection"] = selected_runtime

    try:
        normalized_result = _run(
            ai_service,
            payload,
            prepared,
            chat_state,
            _resolve_initiated_by(payload),
        )
    except Exception as exc:  # noqa: BLE001
        current_app.logger.error("api.ai_interactions.run.failed request_id=%s error=%s", prepared["request_id"], str(exc))
        return (
            jsonify(
                {
                    "error": {
                        "code": "runtime_unavailable",
                        "message": "There was a problem with the model contact the administrator.",
                        "details": {"exception": exc.__class__.__name__},
                    }
                }
            ),
            503,
        )
    _warn_if_empty_response(prepared["request_id"], normalized_result)
    persistence_error = _persist_interaction(payload, prepared["prompt"], normalized_result)
    if persistence_error is not None:
        current_app.logger.debug(
            "api.ai_interactions.persistence.error request_id=%s chat_id=%s has_error=%s",
            prepared["request_id"],
            payload.get("chat_id"),
            True,
        )
        return persistence_error
    current_app.logger.debug(
        "api.ai_interactions.persistence.end request_id=%s chat_id=%s response_text_len=%s",
        prepared["request_id"],
        payload.get("chat_id"),
        len(normalized_result.get("assistant_text") or ""),
    )
    return jsonify(normalized_result), 200



@api_v1_bp.get("/chats/<int:chat_id>/ai/interactions")
@login_required
def list_chat_ai_interactions(chat_id: int):
    """List AI interactions for a target chat when visible to the authenticated user."""
    current_app.logger.debug(
        "api.ai_interactions.list.request method=%s path=%s user_id=%s",
        "GET",
        f"/api/v1/chats/{chat_id}/ai/interactions",
        ChatAccessHelper.get_authenticated_user_id(),
    )
    chat = _require_record("chat", Chat, chat_id)
    deny = _assert_chat_permissions(chat)
    if deny is not None:
        return deny

    interactions = (
        db.session.query(AIInteraction)
        .filter(AIInteraction.chat_id == chat_id)
        .order_by(AIInteraction.created_at.asc(), AIInteraction.id.asc())
        .all()
    )
    current_app.logger.debug(
        "api.ai_interactions.list.response chat_id=%s status=%s count=%s",
        chat_id,
        200,
        len(interactions),
    )
    return jsonify([_serialize_record("ai_interaction", interaction) for interaction in interactions]), 200
