"""Models package surface and ownership map.

This package centralizes ORM-facing domain entities and related model helpers used by API routes,
repositories, and service orchestration. During handoff, treat this file as the quick index for where
different model concerns live so maintainers can navigate domain boundaries without reading every file.

File map (one-line summary per file):
- `base.py` — SQLAlchemy base/metadata foundation shared by model declarations.
- `users.py` — primary user/account model and user-centric identity/profile fields.
- `identity.py` — auth/session lifecycle models (for example `UserSession`) tied to login state.
- `learning.py` — core app domain models (classes, chats, messages, notes, accommodations, enrollments).
- `ai.py` — AI-facing models for model catalog and interaction/system-prompt linkage.
- `audit_log.py` — audit/event persistence model for traceability and operational history.
- `entity_metadata.py` — shared metadata entity helpers/constants for cross-model metadata patterns.
- `db_schema.py` — standalone-schema bridge objects/helpers (including `DBUser` and schema bundle wiring).
"""

from .ai import AIInteraction, AIModel, AccommodationSystemPrompt, SystemPrompt
from .audit_log import AuditLog
from .learning import Accommodation, Chat, CourseClass, Message, Note, UserAccessibilityFeature, UserClassEnrollment
from .db_schema import DBUser, get_schema_bundle
from .identity import UserSession
from .users import User

__all__ = [
    "Accommodation",
    "AIInteraction",
    "AIModel",
    "AccommodationSystemPrompt",
    "AuditLog",
    "Chat",
    "CourseClass",
    "DBUser",
    "Message",
    "Note",
    "SystemPrompt",
    "User",
    "UserAccessibilityFeature",
    "UserClassEnrollment",
    "UserSession",
    "get_schema_bundle",
]
