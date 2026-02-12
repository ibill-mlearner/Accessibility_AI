from __future__ import annotations

from flask import Blueprint, jsonify

from .. import role_guard, user_context_payload


student_bp = Blueprint("student", __name__, url_prefix="/student")


@student_bp.get("/overview")
@role_guard("student")
def student_overview():
    return (
        jsonify(
            {
                "user": user_context_payload(),
                "workspace": {
                    "active_tools": ["note_taking", "restating", "summaries"],
                    "next_actions": [
                        "continue previous study chat",
                        "review latest class notes",
                        "start guided prompt",
                    ],
                },
            }
        ),
        200,
    )


__all__ = ["student_bp"]
