from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any

# When this file is executed directly (python AccessBackEnd/app/services/demo_v2.py),
# Python puts the services directory on sys.path first, which can shadow the standard
# library `logging` module with `app/services/logging`. Remove that path and add repo root.
if __package__ in (None, ""):
    _CURRENT_DIR = Path(__file__).resolve().parent
    _REPO_ROOT = _CURRENT_DIR.parents[2]
    try:
        sys.path.remove(str(_CURRENT_DIR))
    except ValueError:
        pass
    if str(_REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT))

from flask import current_app

from AccessBackEnd.app import create_app
from AccessBackEnd.app.extensions import db
from AccessBackEnd.app.models import AIModel, SystemPrompt

def _load_ai_tool() -> Any:
    candidates = ("ai_pipeline_thin.ai_pipeline", "AccessBackEnd.app.services.ai_pipeline_thin.ai_pipeline")
    for module_path in candidates:
        try:
            return importlib.import_module(module_path)
        except ModuleNotFoundError:
            continue
    raise ModuleNotFoundError(
        "No module named 'ai_pipeline_thin'. Install the ai runtime package or provide a local "
        "AccessBackEnd.app.services.ai_pipeline_thin.ai_pipeline module."
    )


def _resolve_active_model_name() -> str:
    configured_model = current_app.config.get("AI_MODEL_NAME")
    if isinstance(configured_model, str) and configured_model:
        return configured_model

    active_model = (
        db.session.query(AIModel)
        .filter(AIModel.active.is_(True))
        .order_by(AIModel.updated_at.desc(), AIModel.id.desc())
        .first()
    )
    if active_model and isinstance(active_model.model_id, str) and active_model.model_id:
        return active_model.model_id

    raise RuntimeError("Unable to resolve model name from AI_MODEL_NAME config or active AIModel database row.")


def _fetch_accessibility_prompt_texts() -> list[str]:
    # Placeholder first iteration: pulls system prompt records to prove DB wiring.
    rows = db.session.query(SystemPrompt).order_by(SystemPrompt.id.asc()).all()
    return [str(row.text).strip() for row in rows if row.text and str(row.text).strip()]


def _build_system_content_placeholder() -> str:
    guardrail_prompt = current_app.config.get("AI_SYSTEM_GUARDRAIL_PROMPT")
    if not isinstance(guardrail_prompt, str) or not guardrail_prompt:
        raise RuntimeError("AI_SYSTEM_GUARDRAIL_PROMPT is required for demo_v2 and was not found in Flask config.")

    accessibility_prompts = _fetch_accessibility_prompt_texts()

    parts: list[str] = [guardrail_prompt]
    if accessibility_prompts:
        parts.append("\n\n".join(accessibility_prompts))

    return "\n\n".join(part for part in parts if part)


def run_single_v2(prompt: str) -> None:
    ai_tool = _load_ai_tool()
    system_content = _build_system_content_placeholder()
    print(f"[demo_v2] system_content_sent_to_model:\n{system_content}\n")

    pipeline = ai_tool.AIPipeline(
        model_name_value=_resolve_active_model_name(),
        system_content=system_content,
        prompt_value=prompt,
        download_locally=bool(current_app.config.get("AI_DOWNLOAD_LOCALLY", True)),
    )

    pipeline.model_loader.device_map = "auto"
    if hasattr(pipeline.model_loader, "dtype"):
        pipeline.model_loader.dtype = "auto"
    else:
        pipeline.model_loader.torch_dtype = "auto"

    model = pipeline.build_model()
    tokenizer = pipeline.build_tokenizer()

    text = pipeline.build_text(tokenizer=tokenizer)
    model_inputs = pipeline.build_model_inputs(
        tokenizer=tokenizer,
        text=text,
        model=model,
    )

    raw_ids = pipeline.build_raw_generated_ids(
        model=model,
        model_inputs=model_inputs,
        max_new_tokens=int(current_app.config.get("AI_MAX_NEW_TOKENS", 100)),
    )

    generated_ids = pipeline.build_generated_ids(
        model_inputs=model_inputs,
        raw_generated_ids=raw_ids,
    )

    response = pipeline.build_response(
        tokenizer=tokenizer,
        generated_ids=generated_ids,
    )

    print(response)


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        run_single_v2("Explain what an AI pipeline is in 2 sentences.")
