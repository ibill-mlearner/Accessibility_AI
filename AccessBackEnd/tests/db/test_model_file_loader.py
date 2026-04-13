import json


def _write_valid_model_dir(models_root, folder_name: str):
    model_dir = models_root / folder_name
    model_dir.mkdir(parents=True, exist_ok=True)
    (model_dir / "config.json").write_text(json.dumps({"model_type": "qwen2"}), encoding="utf-8")
    (model_dir / "tokenizer.json").write_text("{}", encoding="utf-8")
    (model_dir / "model.safetensors").write_text("weights", encoding="utf-8")
    return model_dir


def test_model_file_loader_queries_folder_updates_db_and_delivers_payload(app, monkeypatch, tmp_path):
    from app.db import init_flask_database
    from app.db.model_file_loader import ModelFileLoader
    from app.extensions import db
    from app.models import AIModel
    from app.db import model_file_loader as loader_module

    models_root = tmp_path / "models"
    _write_valid_model_dir(models_root, "models--Qwen--Qwen2.5-0.5B-Instruct")

    with app.app_context():
        init_flask_database(app)
        app.config["AI_PROVIDER"] = "huggingface"
        app.config["AI_MODEL_NAME"] = "Qwen/Qwen2.5-0.5B-Instruct"

        monkeypatch.setattr(
            loader_module,
            "discover_local_model_inventory",
            lambda _app: {
                "provider": "huggingface",
                "models_root": models_root,
                "model_ids": [],
            },
        )

        loader = ModelFileLoader(app)
        sync_payload = loader.query_folder_and_update_database()
        delivered = loader.deliver_models_from_database()

        row = db.session.query(AIModel).filter(
            AIModel.provider == "huggingface",
            AIModel.model_id == "Qwen/Qwen2.5-0.5B-Instruct",
        ).one()

    assert sync_payload["provider"] == "huggingface"
    assert sync_payload["discovered"] == 1
    assert row.source == "model_file_loader"
    assert delivered["local"]["count"] == 1
    assert delivered["local"]["models"][0]["id"] == "Qwen/Qwen2.5-0.5B-Instruct"
