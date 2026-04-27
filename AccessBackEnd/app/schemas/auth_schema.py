"""Auth payload/response contract placeholders.

These TypedDict declarations document expected auth request/response keys for API v1 routes.
They are intentionally lightweight and complement (not replace) runtime validation performed in
Marshmallow schemas and route-level logic.

Handoff note: these auth contracts are currently TypedDict placeholders. If auth payload
validation needs to align with the rest of runtime request validation, migrating this module
to Marshmallow schemas would provide consistent required/optional/nullable enforcement.
"""

from __future__ import annotations

from typing import TypedDict


class RegisterRequest(TypedDict, total=False):
    """Placeholder payload for ``POST /api/v1/auth/register``."""

    email: str
    password: str
    display_name: str


class RegisterResponse(TypedDict, total=False):
    """Placeholder response for register success/failure envelopes."""

    message: str
    user_id: int
    access_token: str
    refresh_token: str


class LoginRequest(TypedDict, total=False):
    """Placeholder payload for ``POST /api/v1/auth/login``."""

    email: str
    password: str


class LoginResponse(TypedDict, total=False):
    """Placeholder response for login success/failure envelopes."""

    message: str
    user_id: int
    access_token: str
    refresh_token: str
