from __future__ import annotations

from flask import Blueprint, Response, current_app, render_template

from ....logging_config import DomainEvent


_ENDPOINT_COMPONENTS: list[str] = [
    "api_view/endpoints/health.html",
    "api_view/endpoints/ai_interactions.html",
    "api_view/endpoints/chats_collection.html",
    "api_view/endpoints/chats_item.html",
    "api_view/endpoints/messages_collection.html",
    "api_view/endpoints/messages_item.html",
    "api_view/endpoints/classes_collection.html",
    "api_view/endpoints/classes_item.html",
    "api_view/endpoints/features_collection.html",
    "api_view/endpoints/features_item.html",
    "api_view/endpoints/notes_collection.html",
    "api_view/endpoints/notes_item.html",
    "api_view/endpoints/api_view.html",
]


def api_view() -> Response:
    """Render a template-based built-in API test page for v1 endpoints."""
    current_app.extensions["event_bus"].publish(DomainEvent("api.viewed"))
    return Response(render_template("api_view/index.html", endpoint_components=_ENDPOINT_COMPONENTS), mimetype="text/html")


def register_api_view_route(api_v1_bp: Blueprint) -> None:
    """Attach the standalone API view route to the v1 blueprint."""
    api_v1_bp.add_url_rule("/api_view", endpoint="api_view", view_func=api_view, methods=["GET"])
