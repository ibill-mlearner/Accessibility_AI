"""Auth payload contract placeholders for API v1 chat-flow endpoints."""

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
