"""Standalone demo script for the AI pipeline package.

Run from the backend folder:
    python "app/services/hello world ai.py"
"""

from __future__ import annotations

from pathlib import Path
import json
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.ai_pipeline import AIPipelineConfig, AIPipelineService


DEFAULT_SYSTEM_PROMPT = (
    "You are Access AI assistant. Follow accessibility-first guidance and return concise, actionable support."
)


def build_prompt_with_system_instructions(system_prompt: str, user_prompt: str) -> str:
    """Rough-in system prompt composition for sprint-level experimentation.

    Current AI pipeline entry point accepts a single `prompt` string.
    This helper demonstrates how system instructions can be prepended while
    preserving the existing pipeline contract.
    """

    return f"System instructions:\n{system_prompt}\n\nUser request:\n{user_prompt}".strip()


def main() -> None:
    mock_resource = BACKEND_ROOT / "app" / "resources" / "mock_ai_response.json"

    pipeline = AIPipelineService(
        AIPipelineConfig(
            provider="mock_json",
            mock_resource_path=str(mock_resource),
        )
    )

    user_prompt = "Generate accessibility support suggestions for a lecture chat tool."
    composed_prompt = build_prompt_with_system_instructions(DEFAULT_SYSTEM_PROMPT, user_prompt)

    # Rough-in structure for future provider support where system prompts can be
    # passed separately instead of being flattened into one prompt string.
    context = {
        "system_prompt": DEFAULT_SYSTEM_PROMPT,
        "sprint_note": "Demo scaffold only; providers can adopt dedicated system prompt channels later.",
    }

    response = pipeline.run_interaction(composed_prompt, context=context)

    print("=== Pipeline input payload (demo) ===")
    print(json.dumps({"prompt": composed_prompt, "context": context}, indent=2))
    print("\n=== Pipeline response ===")
    print(json.dumps(response, indent=2))


if __name__ == "__main__":
    main()
