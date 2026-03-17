from app.services.ai_pipeline_v2.model_selection import resolve_catalog_selection


def test_resolve_catalog_selection_prefers_valid_session_selection():
    selected = resolve_catalog_selection(
        persisted_selection={
            "user_id": 5,
            "auth_session_id": 11,
            "provider": "huggingface",
            "model_id": "Qwen/Qwen2.5-0.5B-Instruct",
        },
        active_user_id=5,
        active_session_id=11,
        config_provider="huggingface",
        config_model_id="Other/Model",
        available_by_provider={"huggingface": {"qwen/qwen2.5-0.5b-instruct"}},
        ordered_models=[{"provider": "huggingface", "id": "Qwen/Qwen2.5-0.5B-Instruct"}],
    )

    assert selected["source"] == "session_selection"
    assert selected["provider"] == "huggingface"


def test_resolve_catalog_selection_falls_back_to_db_first_available():
    selected = resolve_catalog_selection(
        persisted_selection={"user_id": 5, "provider": "huggingface", "model_id": "missing"},
        active_user_id=5,
        active_session_id=11,
        config_provider="huggingface",
        config_model_id="still-missing",
        available_by_provider={"huggingface": set()},
        ordered_models=[{"provider": "ollama", "id": "llama3.2:3b"}],
    )

    assert selected == {
        "provider": "ollama",
        "model_id": "llama3.2:3b",
        "source": "db_first_available",
    }
