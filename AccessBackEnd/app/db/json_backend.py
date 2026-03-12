from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from .interfaces import AIInteractionRepositoryInterface, DatabaseRuntime, UserRepositoryInterface

from ..models.entity_metadata import EntityMetadata
import hashlib


MetadataProvider = Callable[[], dict[str, EntityMetadata]]


@dataclass
class JsonUser:
    id: int
    email: str
    normalized_email: str
    password_hash: str
    role: str
    created_at: str
    updated_at: str
    last_login_at: str | None
    is_active: bool
    email_confirmed: bool
    lockout_end: str | None
    access_failed_count: int
    lockout_enabled: bool
    security_stamp: str


@dataclass
class JsonAIInteraction:
    id: int
    prompt: str
    response_text: str
    ai_model_id: int | None
    chat_id: int | None = None


class JsonDatabaseRuntime(DatabaseRuntime):
    """In-memory JSON runtime with a DB-like session_scope API."""

    def __init__(self, *, json_path: str):
        self.json_path = Path(json_path)
        self.metadata: dict[str, EntityMetadata] = {}
        self.models: dict[str, type] = {
            "user": JsonUser,
            "ai_interaction": JsonAIInteraction,
        }
        self._records: dict[str, list[dict]] = {}

    def bind_metadata(self, metadata_provider: MetadataProvider) -> None:
        self.metadata = metadata_provider()

    def load(self) -> None:
        payload = json.loads(self.json_path.read_text(encoding="utf-8"))
        for key, meta in self.metadata.items():
            records = payload.get(meta.entity_name, [])
            if not isinstance(records, list):
                raise ValueError(f"{meta.entity_name} must be a list")
            for record in records:
                missing = [field for field in meta.required_fields if field not in record]
                if missing:
                    raise ValueError(f"{meta.entity_name} record missing required fields: {missing}")
            self._records[key] = records

    @contextmanager
    def session_scope(self) -> Iterator["JsonDatabaseRuntime"]:
        yield self


class JsonUserRepository(UserRepositoryInterface):
    def __init__(self, runtime: JsonDatabaseRuntime):
        self.runtime = runtime
        self.user_model = runtime.models["user"]

    def create(self, session: JsonDatabaseRuntime, *, email: str, password_hash: str, role: str = "student"):
        records = session._records["user"]
        next_id = max((record["id"] for record in records), default=0) + 1
        normalized_email = email.lower().strip()
        now_iso = datetime.now(timezone.utc).isoformat()
        record = {
            "id": next_id,
            "email": normalized_email,
            "normalized_email": normalized_email,
            "password_hash": password_hash,
            "role": role,
            "created_at": now_iso,
            "updated_at": now_iso,
            "is_active": True,
            "email_confirmed": False,
            "access_failed_count": 0,
            "lockout_enabled": True,
            "lockout_end": None,
            "security_stamp": f"transitional-{hashlib.sha256(normalized_email.encode('utf-8')).hexdigest()[:32]}",
            "last_login_at": None,
        }
        records.append(record)
        return self.user_model(**record)

    def get_by_id(self, session: JsonDatabaseRuntime, user_id: int):
        for record in session._records["user"]:
            if record["id"] == user_id:
                return self.user_model(**record)
        return None

    def get_by_email(self, session: JsonDatabaseRuntime, email: str):
        normalized = email.lower().strip()
        for record in session._records["user"]:
            if record.get("normalized_email") == normalized or record["email"] == normalized:
                return self.user_model(**record)
        return None


class JsonAIInteractionRepository(AIInteractionRepositoryInterface):
    def __init__(self, runtime: JsonDatabaseRuntime):
        self.runtime = runtime
        self.interaction_model = runtime.models["ai_interaction"]

    def create(
        self,
        session: JsonDatabaseRuntime,
        *,
        prompt: str,
        response_text: str,
        ai_model_id: int | None = None,
        chat_id: int | None = None,
    ):
        records = session._records["ai_interaction"]
        next_id = max((record["id"] for record in records), default=0) + 1
        record = {
            "id": next_id,
            "prompt": prompt,
            "response_text": response_text,
            "ai_model_id": ai_model_id,
            "chat_id": chat_id,
        }
        records.append(record)
        return self.interaction_model(**record)

    def list_for_chat(self, session: JsonDatabaseRuntime, chat_id: int):
        return [
            self.interaction_model(**record)
            for record in session._records["ai_interaction"]
            if record.get("chat_id") == chat_id
        ]


def create_json_backed_db(*, json_path: str, metadata_provider: MetadataProvider):
    """Build a drop-in backend that swaps SQL DB with a JSON file source."""

    runtime = JsonDatabaseRuntime(json_path=json_path)
    runtime.bind_metadata(metadata_provider)
    runtime.load()
    repositories = {
        "users": JsonUserRepository(runtime),
        "ai_interactions": JsonAIInteractionRepository(runtime),
    }
    return runtime, repositories
