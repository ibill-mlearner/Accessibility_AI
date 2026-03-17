from flask import Flask
from app.services.ai_pipeline_v2.model_selection import (
    extract_available_model_ids,
    normalize_model_id,
    resolve_catalog_selection,
    resolve_provider_model_selection,
)


class _FakeService:
    def __init__(self, payload):
        self._payload = payload

    def list_available_models(self):
        return self._payload


def test_extract_available_model_ids_supports_local_and_huggingface_local_buckets():
    extracted = extract_available_model_ids(
        {
            "local": {"models": [{"id": "Qwen/Qwen2.5-0.5B-Instruct"}]},
            "huggingface_local": {"models": [{"id": "models--Meta--Llama-3.1-8B-Instruct"}]},
        }
    )

    assert "qwen/qwen2.5-0.5b-instruct" in extracted["huggingface"]
    assert "meta/llama-3.1-8b-instruct" in extracted["huggingface"]


def test_resolve_provider_model_selection_accepts_available_inventory_ids_without_manual_alias_conversion():
    inventory = {
        "huggingface_local": {
            "models": [
                {
                    "id": "/workspace/instance/models/models--Qwen--Qwen2.5-0.5B-Instruct/snapshots/123abc",
                }
            ]
        }
    }
    service = _FakeService(inventory)

    selected_direct = resolve_provider_model_selection(
        {
            "provider": "huggingface",
            "model_id": "/workspace/instance/models/models--Qwen--Qwen2.5-0.5B-Instruct/snapshots/123abc",
        },
        service,
        allow_session=False,
        require_explicit=True,
    )
    assert selected_direct["source"] == "request_override"
    assert selected_direct["model_id"] == "qwen/qwen2.5-0.5b-instruct"

    selected_alias = resolve_provider_model_selection(
        {
            "provider": "huggingface",
            "model_id": "Qwen/Qwen2.5-0.5B-Instruct",
        },
        service,
        allow_session=False,
        require_explicit=True,
    )
    assert selected_alias["source"] == "request_override"
    assert selected_alias["model_id"] == "qwen/qwen2.5-0.5b-instruct"


def test_resolve_catalog_selection_matches_config_default_with_canonical_normalizer():
    canonical_id = normalize_model_id("models--Qwen--Qwen2.5-0.5B-Instruct")
    selected = resolve_catalog_selection(
        persisted_selection=None,
        active_user_id=None,
        active_session_id=None,
        config_provider="huggingface",
        config_model_id="Qwen/Qwen2.5-0.5B-Instruct",
        available_by_provider={"huggingface": {canonical_id}},
        ordered_models=[{"provider": "huggingface", "id": "fallback-model"}],
    )

    assert selected == {
        "provider": "huggingface",
        "model_id": "qwen/qwen2.5-0.5b-instruct",
        "source": "config_default",
    }


def test_resolve_provider_model_selection_normalizes_session_selection_model_id():
    app = Flask(__name__)
    app.secret_key = "test-secret"
    app.config.update(AI_PROVIDER="huggingface", AI_MODEL_NAME="Qwen/Qwen2.5-0.5B-Instruct")
    service = _FakeService({"huggingface_local": {"models": [{"id": "Qwen/Qwen2.5-0.5B-Instruct"}]}})

    with app.test_request_context("/api/v1/ai/interactions"):
        from flask import session

        session["ai_model_selection"] = {"provider": "huggingface", "model_id": "Qwen/Qwen2.5-0.5B-Instruct"}
        selected = resolve_provider_model_selection({}, service, allow_session=True)

    assert selected == {
        "provider": "huggingface",
        "model_id": "qwen/qwen2.5-0.5b-instruct",
        "source": "session_selection",
    }


def test_normalize_model_id_converts_huggingface_cache_style_delimiter_to_repo_id():
    assert normalize_model_id("huggingfacetb--smollm-135m-instruct") == "huggingfacetb/smollm-135m-instruct"