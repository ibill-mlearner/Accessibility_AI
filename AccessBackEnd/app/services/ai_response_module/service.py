from __future__ import annotations

from pathlib import Path
import sqlite3

from transformers import AutoModelForCausalLM, AutoTokenizer

from .interfaces import AIResponseServiceInterface, ModelLocatorInterface, PromptTemplateRepositoryInterface


class SQLitePromptTemplateRepository(PromptTemplateRepositoryInterface):
    def __init__(self, *, db_path: str | Path, table_name: str = "prompt_templates"):
        self.db_path = Path(db_path)
        self.table_name = table_name

    def get_prompt_template(self, prompt_id: int) -> str:
        with sqlite3.connect(self.db_path) as connection:
            row = connection.execute(
                f"SELECT prompt FROM {self.table_name} WHERE id = ?",
                (int(prompt_id),),
            ).fetchone()
        if row is None:
            raise ValueError(f"Prompt template not found for id={prompt_id}")
        return str(row[0])


class LocalInstanceModelLocator(ModelLocatorInterface):
    def __init__(self, *, models_dir: str | Path | None = None):
        self.models_dir = Path(models_dir) if models_dir else Path(__file__).resolve().parents[3] / "instance" / "models"

    def resolve(self, model_name: str) -> str | Path:
        explicit_candidate = self.models_dir / model_name
        if explicit_candidate.exists():
            return explicit_candidate

        huggingface_cache_name = f"models--{model_name.replace('/', '--')}"
        snapshot_root = self.models_dir / huggingface_cache_name / "snapshots"
        if snapshot_root.exists():
            snapshots = sorted(snapshot_root.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
            if snapshots:
                return snapshots[0]

        return model_name


class AIResponseService(AIResponseServiceInterface):
    """Single entry point for AI generation calls via ``get_response``."""

    def __init__(
        self,
        *,
        prompt_repository: PromptTemplateRepositoryInterface,
        model_locator: ModelLocatorInterface | None = None,
        model_name: str = "Qwen/Qwen2.5-3B-Instruct",
        model_loader=AutoModelForCausalLM.from_pretrained,
        tokenizer_loader=AutoTokenizer.from_pretrained,
    ):
        self.prompt_repository = prompt_repository
        self.model_locator = model_locator or LocalInstanceModelLocator()

        model_source = self.model_locator.resolve(model_name)
        self.model = model_loader(
            model_source,
            torch_dtype="auto",
            device_map="auto",
        )
        self.tokenizer = tokenizer_loader(model_source)

    def get_response(self, *, prompt_id: int, user_prompt: str) -> str:
        system_prompt = self.prompt_repository.get_prompt_template(prompt_id)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
        model_inputs = self.tokenizer([text], return_tensors="pt").to(self.model.device)

        generated_ids = self.model.generate(
            **model_inputs,
            max_new_tokens=512,
        )
        generated_ids = [
            output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
        ]
        return self.tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
