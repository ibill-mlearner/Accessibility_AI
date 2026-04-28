from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session
from sqlalchemy.engine import make_url



class PromptContextDBUtilities:
    """Reusable database helper methods for prompt-context assembly."""

    def __init__(self, *, session: Session, models: dict[str, type[Any]]) -> None:
        self._session = session
        self._models = models

    def resolve_selected_feature_ids(
        self,
        *,
        user_id: int,
        selected_feature_ids: list[int] | None = None,
    ) -> list[int]:
        """Resolve selected feature ids from explicit input or user preferences."""
        if selected_feature_ids:
            return selected_feature_ids

        UserAccessibilityFeature = self._models["user_accessibility_feature"]
        return [
            int(accommodation_id)
            for (accommodation_id,) in (
                self._session.query(UserAccessibilityFeature.accommodation_id)
                .filter(UserAccessibilityFeature.user_id == user_id, UserAccessibilityFeature.enabled.is_(True))
                .order_by(UserAccessibilityFeature.accommodation_id.asc())
                .all()
            )
        ]

    def load_feature_rows(self, *, feature_ids: list[int]) -> list[Any]:
        """Load accommodation rows for selected feature ids in stable order."""
        Accommodation = self._models["accommodation"]
        return (
            self._session.query(Accommodation.id, Accommodation.title, Accommodation.details)
            .filter(Accommodation.id.in_(feature_ids))
            .order_by(Accommodation.id.asc())
            .all()
        )

    @staticmethod
    def assemble_feature_payload_from_rows(
        rows: list[Any],
        *,
        exclude_standard_profiles: bool,
    ) -> tuple[list[dict[str, Any]], list[str]]:
        """Build feature detail records plus instruction fragments from DB rows."""
        feature_details: list[dict[str, Any]] = []
        instruction_parts: list[str] = []
        for row in rows:
            title = str(row.title or "").strip()
            details = str(row.details or "").strip()
            if exclude_standard_profiles and details.lower().startswith("standard;") and ":" in title:
                continue
            feature_details.append({"id": int(row.id), "title": title, "details": details})
            if details:
                instruction_parts.append(details)
        return feature_details, instruction_parts

    def messages_from_interactions(self, *, chat_id: int) -> list[dict[str, str]]:
        AIInteraction = self._models["ai_interaction"]
        ordered_messages: list[dict[str, str]] = []
        interactions = (
            self._session.query(AIInteraction)
            .filter(AIInteraction.chat_id == int(chat_id))
            .order_by(AIInteraction.created_at.asc(), AIInteraction.id.asc())
            .all()
        )
        for interaction in interactions:
            prompt_text = str(getattr(interaction, "prompt", "") or "").strip()
            response_text = str(getattr(interaction, "response_text", "") or "").strip()
            if prompt_text:
                ordered_messages.append({"role": "user", "content": prompt_text})
            if response_text:
                ordered_messages.append({"role": "assistant", "content": response_text})
        return ordered_messages

    def messages_from_legacy_chat_rows(self, *, chat_id: int) -> list[dict[str, str]]:
        Message = self._models["message"]
        raw_messages = (
            self._session.query(Message)
            .filter(Message.chat_id == int(chat_id))
            .order_by(Message.id.asc())
            .all()
        )
        fallback_messages: list[dict[str, str]] = []
        next_role = "user"
        for row in raw_messages:
            content = str(getattr(row, "message_text", "") or "").strip()
            if not content:
                continue
            fallback_messages.append({"role": next_role, "content": content})
            next_role = "assistant" if next_role == "user" else "user"
        return fallback_messages


class ModelFileLoaderDBUtilities:
    """Reusable database helper methods for model-file-loader flows."""

    @staticmethod
    def empty_model_validation_result() -> tuple[str, str]:
        return "", ""

    @staticmethod
    def is_valid_model_candidate(normalized: str, *, candidate_dir: Path) -> bool:
        from ..utils.ai_checker.model_artifacts import AIModelArtifactOps

        return (
            bool(normalized)
            and candidate_dir.exists()
            and candidate_dir.is_dir()
            and AIModelArtifactOps.has_valid_artifacts_for_path(candidate_dir)
        )

    @staticmethod
    def collect_validated_models(
        *,
        discovered_raw_ids: list[str],
        models_root: Path,
        formatter: Any,
    ) -> dict[str, str]:
        validated_models: dict[str, str] = {}
        for raw_id in discovered_raw_ids:
            model_id, resolved_path = formatter(str(raw_id), models_root=models_root)
            if not model_id:
                continue
            validated_models[model_id] = resolved_path
        return validated_models

    @staticmethod
    def upsert_provider_models(
        *,
        records: list[Any],
        provider: str,
        discovered_set: set[str],
        validated_models: dict[str, str],
        models_root: Path,
        add_record: Any,
    ) -> int:
        from ..models import AIModel

        by_model_id = {str(record.model_id): record for record in records}
        upserted = 0
        for model_id in sorted(discovered_set):
            record = by_model_id.get(model_id)
            path = validated_models.get(model_id, (models_root / model_id).as_posix())
            if record is None:
                add_record(AIModel(provider=provider, model_id=model_id, source="model_file_loader", path=path, active=False))
                upserted += 1
                continue
            record.source = "model_file_loader"
            record.path = path
            upserted += 1
        return upserted

    @staticmethod
    def deactivate_missing_models(*, records: list[Any], discovered_set: set[str]) -> int:
        deactivated = 0
        for record in records:
            if record.model_id in discovered_set:
                continue
            if record.active:
                deactivated += 1
            record.active = False
        return deactivated


class DatabaseSettingsUtilities:
    """Reusable helpers for database settings/url normalization."""

    @staticmethod
    def _normalize_sqlite_home_prefixed_path(sqlite_path: str) -> str:
        normalized_path = sqlite_path
        if sqlite_path.startswith("~"):
            home_override = os.getenv("HOME")
            if home_override and (
                sqlite_path == "~" or sqlite_path.startswith("~/") or sqlite_path.startswith("~\\")
            ):
                relative = sqlite_path[1:].lstrip("/\\")
                normalized_path = str(Path(home_override) / relative) if relative else home_override
        return normalized_path

    @staticmethod
    def _resolve_sqlite_path_for_instance(*, sqlite_path: str, instance_path: str) -> Path:
        normalized = Path(sqlite_path).expanduser()
        if not normalized.is_absolute():
            normalized = Path(instance_path) / normalized
        return normalized

    @staticmethod
    def normalize_sqlite_url(configured: str, *, instance_path: str) -> str:
        parsed = make_url(configured)
        if not parsed.drivername.startswith("sqlite"):
            return configured

        sqlite_path = parsed.database
        if not sqlite_path or sqlite_path == ":memory:" or sqlite_path.startswith("file:"):
            return configured

        #todo: review this later, i think the path is too static to my own system
        # normalized = Path(sqlite_path).expanduser() OLD LOGIC

        normalized_path = DatabaseSettingsUtilities._normalize_sqlite_home_prefixed_path(sqlite_path)
        normalized = DatabaseSettingsUtilities._resolve_sqlite_path_for_instance(
            sqlite_path=normalized_path,
            instance_path=instance_path,
        )

        normalized.parent.mkdir(parents=True, exist_ok=True)
        resolved = normalized.resolve().as_posix()
        return parsed.set(database=resolved).render_as_string(hide_password=False)
