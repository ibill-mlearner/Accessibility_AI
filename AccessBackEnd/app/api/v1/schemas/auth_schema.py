"""Auth payload shape definitions used by v1 contracts."""

from __future__ import annotations

from typing import TypedDict


class RegisterRequest(TypedDict, total=False):
    """Payload for user registration.

    Logic intent:
    - Accept email/password exactly as provided.
    - Forward values to auth domain logic without API-level data mutation.
    """

    email: str
    password: str


class LoginRequest(TypedDict, total=False):
    """Payload for authentication."""

    email: str
    password: str
