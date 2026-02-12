from __future__ import annotations

from flask import Blueprint, jsonify

from .. import role_guard, user_context_payload


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.get("/overview")
@role_guard("admin")
def admin_overview():
    return (
        jsonify(
            {
                "user": user_context_payload(),
                "workspace": {
                    "controls": ["user_management", "audit_review", "role_assignment"],
                    "system_health": {
                        "api": "operational",
                        "auth": "operational",
                        "ai_pipeline": "operational",
                    },
                },
            }
        ),
        200,
    )


__all__ = ["admin_bp"]
