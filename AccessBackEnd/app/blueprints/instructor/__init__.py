from __future__ import annotations

from flask import Blueprint, jsonify

from .. import role_guard, user_context_payload


instructor_bp = Blueprint("instructor", __name__, url_prefix="/instructor")


@instructor_bp.get("/overview")
@role_guard("instructor", "admin")
def instructor_overview():
    return (
        jsonify(
            {
                "user": user_context_payload(),
                "workspace": {
                    "controls": ["prompt_controls", "course_visibility", "feature_toggles"],
                    "insights": [
                        "class engagement summary",
                        "high-friction prompts",
                        "accommodation usage snapshots",
                    ],
                },
            }
        ),
        200,
    )


__all__ = ["instructor_bp"]
