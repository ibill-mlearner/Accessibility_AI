from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

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
        cache_dir: str | None = None,
        allow_download: bool = False
    ) -> None:
    
        # Logic intent:
        # - Store model identity and cache target so callers can reuse one bootstrap object.
        self.model_id = model_id
        self.cache_dir = cache_dir
        self.allow_download = allow_download

    def _resolve_cached_snapshot_path(self) -> Path | None:
        if not self.cache_dir:
            return None

        cache_root = Path(self.cache_dir).expanduser()
        if not cache_root.exists():
            return None

        org_repo = self.model_id.replace("/", "--")
        snapshot_root = cache_root / f"models--{org_repo}" / "snapshots"
        if not snapshot_root.exists() or not snapshot_root.is_dir():
            return None

        snapshots = [path for path in snapshot_root.iterdir() if path.is_dir()]
        if not snapshots:
            return None

        return max(snapshots, key=lambda path: path.stat().st_mtime)


    def _resolve_cache_alias_path(self) -> Path | None:
        """Resolve pre-downloaded local alias directories under cache_dir.

        Supports workflows where models are materialized as
        `<cache_dir>/<alias>` (for example via download_models_once.py)
        instead of HuggingFace's snapshot cache layout.
        """
        if not self.cache_dir:
            return None

        model_alias = str(self.model_id or "").strip()
        if not model_alias or "/" in model_alias:
            return None

        alias_path = Path(self.cache_dir).expanduser() / model_alias
        if alias_path.exists() and alias_path.is_dir():
            return alias_path
        return None

    def ensure_model(self) -> Path:
        # Logic intent:
        # 1) Download/sync model snapshots from HuggingFace Hub when needed.
        # 2) Return a local path that can be consumed by transformers/LangChain.
        if not self.model_id:
            raise ValueError("model_id must be configured for HuggingFace bootstrap")

        candidate_path = Path(self.model_id).expanduser()
        if candidate_path.exists() and candidate_path.is_dir():
            return candidate_path

        cached_snapshot = self._resolve_cached_snapshot_path()
        if cached_snapshot:
            return cached_snapshot

        cache_alias_path = self._resolve_cache_alias_path()
        if cache_alias_path:
            return cache_alias_path

        if not self.allow_download:
            logger.warning(
                "ai_pipeline.bootstrap.skip_download model_id=%s reason=local_only_mode",
                self.model_id,
            )
            raise RuntimeError(
                "HuggingFace dynamic download is disabled in local-only mode for this POC. "
                "Provide a local model path in AI_MODEL_NAME or pre-download into AI_HUGGINGFACE_CACHE_DIR."
            )


        try:
            from huggingface_hub import snapshot_download
        except Exception as exc:  # pragma: no cover - dependency and env specific
            raise RuntimeError(
                "huggingface_hub is required for model bootstrap. Install it to enable model download."
            ) from exc

        path = snapshot_download(repo_id=self.model_id, cache_dir=self.cache_dir)
        return Path(path)
