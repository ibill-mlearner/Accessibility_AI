from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from ...logging_config import DomainEvent


api_v1_bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")


@api_v1_bp.get("/health")
def health():
    current_app.extensions["event_bus"].publish(DomainEvent("api.health_checked"))
    return jsonify({"status": "ok", "ai_provider": current_app.config.get("AI_PROVIDER")})


@api_v1_bp.post("/ai/interactions")
def create_ai_interaction():
    payload = request.get_json(silent=True) or {}
    prompt = (payload.get("prompt") or "").strip()

    current_app.extensions["event_bus"].publish(
        DomainEvent("api.ai_interaction_requested", {"has_prompt": bool(prompt)})
    )

    try:
        result = current_app.extensions["ai_service"].run_interaction(prompt=prompt)
    except (FileNotFoundError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 502

    return jsonify(result), 200
