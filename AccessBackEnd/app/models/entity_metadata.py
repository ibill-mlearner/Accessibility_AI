"""Entity metadata contracts for non-SQL stores.

Table/entity map:
- metadata definitions for `users`, `ai_interactions`, and `system_prompts` field requirements.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EntityMetadata:
    """Minimal metadata contract that non-SQL backends can validate against.

    Field map:
    - `entity_name`: canonical entity key used by validators and adapters.
    - `required_fields`: tuple of field names that must exist for valid records.
    """

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
        ("id", "prompt", "response_text", "ai_model_id"),
    ),
    "system_prompt": EntityMetadata(
        "system_prompts",
        ("id", "instructor_id", "class_id", "text"),
    ),
}


def get_entity_metadata_bundle() -> dict[str, EntityMetadata]:
    """Return metadata contract for entity stores outside SQLAlchemy."""

    return ENTITY_METADATA
