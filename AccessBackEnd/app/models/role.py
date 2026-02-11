from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    """Canonical user roles for authorization and model defaults."""

    STUDENT = "student"
    INSTRUCTOR = "instructor"
    ADMIN = "admin"
