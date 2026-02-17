from __future__ import annotations

import os

import torch
import torch.nn as nn


class PrototypeTalkModel(nn.Module):
    def __init__(self, model_name: str):
        super().__init__()
        self.model_name = model_name
        self.proj = nn.Linear(1, 1)

    def talk(self, prompt: str) -> str:
        text = (prompt or "").strip() or "hello let me talk"
        _ = self.proj(torch.tensor([[1.0]], dtype=torch.float32))
        return f"hello let me talk -> {text}"


MODEL_ID = os.environ.get("ACCESS_V2_MODEL", "prototype-torch-model")
MODEL = PrototypeTalkModel(MODEL_ID)


def available_models() -> list[str]:
    return [MODEL_ID]


def default_model() -> str:
    return MODEL_ID


def ai_workflow(prompt: str, context=None, initiated_by="anonymous") -> dict:
    return {
        "provider": MODEL_ID,
        "available_models": [MODEL_ID],
        "response_text": MODEL.talk(prompt),
        "meta": {"initiated_by": initiated_by, "context": context},
    }
