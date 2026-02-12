from __future__ import annotations

from functools import wraps
from typing import Any, Callable

from flask import jsonify
from flask_login import current_user


def role_guard(*allowed_roles: str):
    """Require authenticated users with one of the expected roles."""

    allowed = {role.strip().lower() for role in allowed_roles if role}

    def decorator(func: Callable[..., Any]):
        @wraps(func)
        def wrapped(*args: Any, **kwargs: Any):
            if not current_user.is_authenticated:
                return jsonify({"error": "authentication required"}), 401

            user_role = (getattr(current_user, "role", "") or "").strip().lower()
            if allowed and user_role not in allowed:
                return (
                    jsonify(
                        {
                            "error": "forbidden",
                            "required_roles": sorted(allowed),
                            "current_role": user_role or None,
                        }
                    ),
                    403,
                )

            return func(*args, **kwargs)

        return wrapped

    return decorator


def user_context_payload() -> dict[str, Any]:
    """Normalize current user fields for role-specific blueprint responses."""

    return {
        "id": current_user.id,
        "email": current_user.email,
        "role": current_user.role,
    }


__all__ = ["role_guard", "user_context_payload"]
