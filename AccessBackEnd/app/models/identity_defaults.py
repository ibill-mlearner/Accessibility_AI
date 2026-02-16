from __future__ import annotations

import hashlib


def build_transitional_security_stamp(identifier: str | None) -> str:
    """Return a deterministic placeholder security stamp for transitional identity flows."""
    normalized_identifier = (identifier or "").strip().lower()
    digest_input = normalized_identifier or "identity-placeholder"
    digest = hashlib.sha256(digest_input.encode("utf-8")).hexdigest()[:32]
    return f"transitional-{digest}"


def build_transitional_identity_defaults(identifier: str | None) -> dict[str, object]:
    """Return stable defaults for identity fields pending full policy enforcement."""
    return {
        # Transitional defaults until full identity policy enforcement is implemented.
        "email_confirmed": False,
        "access_failed_count": 0,
        "lockout_enabled": True,
        "lockout_end": None,
        "security_stamp": build_transitional_security_stamp(identifier),
        "last_login_at": None,
    }
