from __future__ import annotations

from pathlib import Path


class HuggingFaceModelBootstrap:
    """Ensure a HuggingFace model is available locally.

    # Logic intent:
    # - Support first-run model download during application setup.
    # - Centralize model caching rules so providers can remain focused on inference.
    """

    def __init__(
        self, 
        *, 
        model_id: str, 
        cache_dir: str | None = None
    ) -> None:
    
        # Logic intent:
        # - Store model identity and cache target so callers can reuse one bootstrap object.
        self.model_id = model_id
        self.cache_dir = cache_dir

    def ensure_model(self) -> Path:
        # Logic intent:
        # 1) Download/sync model snapshots from HuggingFace Hub when needed.
        # 2) Return a local path that can be consumed by transformers/LangChain.
        if not self.model_id:
            raise ValueError("model_id must be configured for HuggingFace bootstrap")

        candidate_path = Path(self.model_id).expanduser()
        if candidate_path.exists() and candidate_path.is_dir():
            return candidate_path

        try:
            from huggingface_hub import snapshot_download
        except Exception as exc:  # pragma: no cover - dependency and env specific
            raise RuntimeError(
                "huggingface_hub is required for model bootstrap. Install it to enable model download."
            ) from exc

        path = snapshot_download(repo_id=self.model_id, cache_dir=self.cache_dir)
        return Path(path)
