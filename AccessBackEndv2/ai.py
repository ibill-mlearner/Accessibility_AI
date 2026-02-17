from __future__ import annotations

AI_PROVIDER = "v2-single-model"


def ai_workflow(prompt: str, context=None, initiated_by="anonymous") -> dict:
    text = (prompt or "").strip()
    if not text:
        text = "(empty prompt)"
    prefix = "I can help with that." if "help" in text.lower() else "I understand."
    return {
        "provider": AI_PROVIDER,
        "response_text": f"{prefix} You said: {text}",
        "meta": {"initiated_by": initiated_by, "context": context},
    }
