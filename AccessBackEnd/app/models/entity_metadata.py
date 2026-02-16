from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EntityMetadata:
    """Minimal metadata contract that non-SQL backends can validate against."""

    entity_name: str
    required_fields: tuple[str, ...]


ENTITY_METADATA = {
    "user": EntityMetadata(
        "users",
        (
            "id",
            "email",
            "normalized_email",
            "password_hash",
            "role",
            "created_at",
            "updated_at",
            "last_login_at",
            "is_active",
            "email_confirmed",
            "lockout_end",
            "access_failed_count",
            "lockout_enabled",
            "security_stamp",
        ),
    ),
    "ai_interaction": EntityMetadata(
        "ai_interactions",
        ("id", "prompt", "response_text", "provider"),
    ),
    "system_prompt": EntityMetadata(
        "system_prompts",
        ("id", "key", "content", "provider", "version"),
    ),
}


def get_entity_metadata_bundle() -> dict[str, EntityMetadata]:
    """Return metadata contract for entity stores outside SQLAlchemy."""

    return ENTITY_METADATA
