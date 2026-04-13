from __future__ import annotations

"""Standalone prompt composition debugger.

Usage example:
    python AccessBackEnd/app/db/prompt_debug_dump.py --user-id 4

This script is intentionally app-bootstrap-free and runs directly against the
standalone DB runtime. It is useful for validating prompt composition inputs
without invoking model execution.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import inspect
from sqlalchemy.exc import OperationalError, ProgrammingError

_BACKEND_ROOT = str(Path(__file__).resolve().parents[2])
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

from app.config import BaseConfig
from app.db.base import DatabaseConfig, StandaloneDatabase
from app.db.prompt_context_assembler import PromptContextAssembler
from app.db.settings import resolve_database_url
from app.models.db_schema import get_schema_bundle

SECTION_BAR = "=" * 88


def _default_database_url() -> str:
    instance_path = (Path(__file__).resolve().parents[2] / "instance").as_posix()
    configured = os.getenv("SQLALCHEMY_DATABASE_URI")
    return resolve_database_url(instance_path=instance_path, configured_url=configured)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Standalone DB prompt debug dumper (no Flask app bootstrap).")
    parser.add_argument("--database-url", default=_default_database_url(), help="SQLAlchemy URL for standalone DB runtime.")
    parser.add_argument("--create-schema", action="store_true", help="Create schema before querying (safe for empty/new DBs).")
    parser.add_argument("--user-id", type=int, default=1, help="Seed user id used to infer accessibility + class context.")
    parser.add_argument("--chat-id", type=int, default=None, help="Optional chat id for conversation history.")
    parser.add_argument("--class-id", type=int, default=None, help="Optional class id override.")
    parser.add_argument("--prompt", default="", help="Optional user prompt override.")
    parser.add_argument("--system-prompt", default="", help="Optional system prompt override.")
    parser.add_argument(
        "--selected-accessibility-link-id",
        dest="feature_ids",
        type=int,
        action="append",
        default=[],
        help="Repeatable accommodation ids. When omitted, enabled features for --user-id are used.",
    )
    return parser.parse_args()


def _print_section(title: str, body: str | list[str] | dict[str, Any]) -> None:
    print(f"\n{SECTION_BAR}\n{title}\n{SECTION_BAR}")
    if isinstance(body, (dict, list)):
        print(json.dumps(body, indent=2, ensure_ascii=False))
    else:
        print(body or "<empty>")


def _safe_query(label: str, query_fn):
    try:
        result = query_fn()
        print(f"[prompt_debug_dump] {label}: succeeded")
        return result
    except (OperationalError, ProgrammingError) as exc:
        print(f"[prompt_debug_dump] {label}: failed -> {exc.__class__.__name__}: {exc}")
        return None


def run_prompt_debug_dump(args: argparse.Namespace) -> None:
    """Inspect and print prompt composition pieces for one user/chat context."""
    print(f"[prompt_debug_dump] standalone mode start; args={vars(args)}")
    runtime = StandaloneDatabase(DatabaseConfig(database_url=args.database_url, echo=False))
    runtime.bind_schema(get_schema_bundle)
    if args.create_schema:
        runtime.create_schema()
        print("[prompt_debug_dump] create_schema enabled: schema creation attempted.")

    db_file_hint = args.database_url.replace("sqlite:///", "", 1) if args.database_url.startswith("sqlite:///") else None
    if db_file_hint:
        print(f"[prompt_debug_dump] sqlite file path hint: {db_file_hint}")
        print(f"[prompt_debug_dump] sqlite file exists: {Path(db_file_hint).exists()}")

    inspector = inspect(runtime.engine)
    table_names = sorted(inspector.get_table_names())
    _print_section("DB Diagnostics", {"database_url": args.database_url, "tables_found": table_names, "table_count": len(table_names)})

    models = runtime.models
    UserClassEnrollment = models["user_class_enrollment"]
    User = models["user"]
    SystemPrompt = models["system_prompt"]
    CourseClass = models["course_class"]

    guardrail_prompt = str(BaseConfig.AI_SYSTEM_GUARDRAIL_PROMPT or "").strip()

    with runtime.session_scope() as session:
        assembler = PromptContextAssembler(session=session, models=models)
        # User identity lookup is printed separately so debug runs clearly show
        # which account context is being inspected.
        user_record = _safe_query(
            f"user lookup for user_id={args.user_id}",
            lambda: session.query(User).filter(User.id == args.user_id).first(),
        )
        user_info = {
            "id": args.user_id,
            "email": str(getattr(user_record, "email", "") or ""),
            "normalized_email": str(getattr(user_record, "normalized_email", "") or ""),
            "role": str(getattr(user_record, "role", "") or ""),
            "exists": bool(user_record),
        }

        conversation_context = assembler.build_conversation_context(user_id=args.user_id, chat_id=args.chat_id)
        selected_chat_id = conversation_context.get("chat_id")
        user_chats = conversation_context.get("available_chats") or []

        feature_context = assembler.build_feature_context(
            user_id=args.user_id,
            selected_feature_ids=args.feature_ids,
            exclude_standard_profiles=True,
        )
        selected_feature_ids = feature_context.get("selected_feature_ids") or []

        enrollment_row = _safe_query(
            f"class enrollment for user_id={args.user_id}",
            lambda: (
                session.query(UserClassEnrollment.class_id)
                .filter(UserClassEnrollment.user_id == args.user_id, UserClassEnrollment.active.is_(True))
                .order_by(UserClassEnrollment.class_id.asc())
                .first()
            ),
        )
        selected_class_id = args.class_id or (int(enrollment_row[0]) if enrollment_row else None)
        if selected_class_id is None and user_chats:
            selected_class_id = int(getattr(user_chats[0], "class_id", 0) or 0) or None

        class_record = _safe_query(
            f"class details for class_id={selected_class_id}",
            lambda: session.query(CourseClass).filter(CourseClass.id == selected_class_id).first(),
        ) if selected_class_id is not None else None
        class_details = str(getattr(class_record, "description", "") or "").strip()

        class_prompt_rows = _safe_query(
            f"class system prompts for class_id={selected_class_id}",
            lambda: (
                session.query(SystemPrompt.text)
                .filter(SystemPrompt.class_id == selected_class_id)
                .order_by(SystemPrompt.id.asc())
                .all()
            ),
        ) if selected_class_id is not None else []
        class_prompts = [str(text).strip() for (text,) in (class_prompt_rows or []) if str(text or "").strip()]
        messages = conversation_context.get("messages") or []
        accessibility_instructions = str(feature_context.get("instructions_text") or "")

    resolved_prompt = str(args.prompt or "").strip()
    if not resolved_prompt and messages:
        for message in reversed(messages):
            if str(message.get("role") or "").lower() == "user" and str(message.get("content") or "").strip():
                resolved_prompt = str(message["content"]).strip()
                break
    if not resolved_prompt:
        resolved_prompt = "Debug prompt placeholder: inspect assembled AI prompt components."

    request_scoped_system_prompt = str(args.system_prompt or "").strip()
    if not request_scoped_system_prompt and class_prompts:
        request_scoped_system_prompt = "\n\n".join(class_prompts)

    composed_system_prompt = assembler.build_composed_system_prompt(
        guardrail_prompt=guardrail_prompt,
        feature_context=feature_context,
        request_scoped_system_prompt=request_scoped_system_prompt,
    )

    _print_section("1) Guardrail Prompt", guardrail_prompt)
    _print_section(
        "User Diagnostics",
        {
            "selected_user": user_info,
            "selected_chat_id": selected_chat_id,
            "available_chats": user_chats,
        },
    )
    _print_section(
        "2) Accessibility Feature Context",
        {
            "selected_feature_ids": selected_feature_ids,
            "feature_details": feature_context.get("feature_details") or [],
            "instructions_text": accessibility_instructions,
        },
    )
    _print_section(
        "3) Class Details / Request System Prompt",
        {
            "selected_class_id": selected_class_id,
            "class_details": class_details,
            "class_system_prompts": class_prompts,
            "request_scoped_system_prompt": request_scoped_system_prompt,
        },
    )
    _print_section("4) User Prompt", resolved_prompt)
    _print_section("Conversation Context", {"chat_id": selected_chat_id, "messages": messages})
    _print_section("Composed System Prompt", composed_system_prompt)


if __name__ == "__main__":
    parsed = _parse_args()
    run_prompt_debug_dump(parsed)
