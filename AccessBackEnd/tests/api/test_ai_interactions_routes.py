from app.api.v1.ai_interactions_routes import _derive_selection_from_chat


def test_derive_selection_from_chat_returns_empty_without_chat(app):
    with app.app_context():
        provider, model_id = _derive_selection_from_chat(None)
    assert provider == ""
    assert model_id == ""
