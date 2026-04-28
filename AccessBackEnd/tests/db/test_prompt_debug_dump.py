"""Manual prompt-context debug harness kept in tests instead of app runtime code.

Why this lives here:
- it is intentionally diagnostic and not part of production request handling;
- developers can run it on demand while keeping the app/db package lean.
"""

from __future__ import annotations

import os

import pytest

from app.db import create_standalone_db
from app.db.prompt_context_assembler import PromptContextAssembler
from app.models.db_schema import get_schema_bundle


def _should_run_debug_harness() -> bool:
    """Gate expensive/manual debug execution behind an explicit environment flag."""
    return os.getenv("RUN_PROMPT_DEBUG_DUMP_TEST", "").strip().lower() in {"1", "true", "yes"}


@pytest.mark.skipif(
    not _should_run_debug_harness(),
    reason="Manual debug harness; set RUN_PROMPT_DEBUG_DUMP_TEST=1 to run explicitly.",
)
def test_prompt_debug_dump_harness_smoke() -> None:
    """Exercise prompt-context assembly paths and dump compact diagnostics for one user id."""
    runtime, _repositories = create_standalone_db(database_url="sqlite:///:memory:", create_schema=True)
    runtime.bind_schema(get_schema_bundle)

    with runtime.session_scope() as session:
        assembler = PromptContextAssembler(session=session, models=runtime.models)
        conversation_context = assembler.build_conversation_context(user_id=1, chat_id=None)
        feature_context = assembler.build_feature_context(
            user_id=1,
            selected_feature_ids=[],
            exclude_standard_profiles=True,
        )
        composed_prompt = assembler.build_composed_system_prompt(
            guardrail_prompt="",
            feature_context=feature_context,
            request_scoped_system_prompt="",
        )

    assert isinstance(conversation_context, dict)
    assert isinstance(feature_context, dict)
    assert isinstance(composed_prompt, str)
