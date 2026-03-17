from __future__ import annotations

from pathlib import Path
from typing import Protocol


class PromptTemplateRepositoryInterface(Protocol):
    def get_prompt_template(self, prompt_id: int) -> str: ...


class ModelLocatorInterface(Protocol):
    def resolve(self, model_name: str) -> str | Path: ...


class AIResponseServiceInterface(Protocol):
    def get_response(self, *, prompt_id: int, user_prompt: str) -> str: ...
