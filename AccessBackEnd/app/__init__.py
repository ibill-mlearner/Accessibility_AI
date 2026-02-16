from __future__ import annotations

from flask import Flask
from flask import jsonify

from . import config
from .api.errors import register_api_error_handlers
from .api.v1.routes import api_v1_bp
from .blueprints.auth.routes import auth_bp
from .db import init_flask_database
from .db.settings import resolve_database_url
from .extensions import cors, db as db_ext, jwt, login_manager, migrate
from .services.logging import initialize_logging
from .models import User
from .services import AIPipelineConfig, AIPipelineService


def _register_cli_commands(app: Flask) -> None:
    @app.cli.command("init-db")
    def init_db_command() -> None:
        """Create all configured database tables for the current app profile."""

        print(
            f"Resolved SQLALCHEMY_DATABASE_URI: {app.config['SQLALCHEMY_DATABASE_URI']}"
        )
        init_flask_database(app)
        print("Database schema initialized.")


def build_ai_service(app: Flask) -> AIPipelineService:
    provider = app.config["AI_PROVIDER"]
    ollama_endpoint = app.config.get("AI_OLLAMA_ENDPOINT")
    live_endpoint = app.config.get("AI_LIVE_ENDPOINT")

    if provider in {"ollama", "ollama_local"} and not ollama_endpoint:
        raise ValueError("AI_OLLAMA_ENDPOINT must be configured when AI_PROVIDER=ollama")

    if provider in {"live", "live_agent", "http"} and not live_endpoint:
        raise ValueError("AI_LIVE_ENDPOINT must be configured for live endpoint providers")

    return AIPipelineService(
        AIPipelineConfig(
            provider=provider,
            mock_resource_path=app.config["AI_MOCK_RESOURCE_PATH"],
            live_endpoint=live_endpoint or "",
            ollama_endpoint=ollama_endpoint or "",
            ollama_model_id=app.config.get("AI_OLLAMA_MODEL", app.config.get("AI_MODEL_NAME", "")),
            ollama_options=app.config.get("AI_OLLAMA_OPTIONS"),
            timeout_seconds=app.config["AI_TIMEOUT_SECONDS"],
            huggingface_model_id=app.config["AI_MODEL_NAME"],
        )
    )


def create_app(config_name: str | None = None) -> Flask:
    app = Flask(
        __name__,
        instance_relative_config=True,
        instance_path=config._INSTANCE_DIR.as_posix(),
    )

    cfg = (
        config.get_config()
        if config_name is None
        else config.CONFIG_BY_NAME.get(config_name, config.DevelopmentConfig)
    )
    app.config.from_object(cfg)
    app.config.from_pyfile("config.py", silent=True)

    app.config["SQLALCHEMY_DATABASE_URI"] = resolve_database_url(
        instance_path=app.instance_path,
        configured_url=app.config.get("SQLALCHEMY_DATABASE_URI"),
    )

    if app.config.get("DATA_BACKEND_FACTORY"):
        app.extensions["data_backend"] = app.config["DATA_BACKEND_FACTORY"]()

    db_ext.init_app(app)
    migrate.init_app(app, db_ext)
    jwt.init_app(app)
    cors.init_app(
        app,
        resources={r"/*": {"origins": app.config["CORS_ORIGINS"]}},
        supports_credentials=app.config["CORS_SUPPORTS_CREDENTIALS"],
    )
    login_manager.init_app(app)

    @login_manager.unauthorized_handler
    def _unauthorized_response():
        return (
            jsonify(
                {
                    "error": {
                        "code": "unauthorized",
                        "message": "authentication required",
                        "details": {},
                    }
                }
            ),
            401,
        )

    app.extensions["ai_service"] = build_ai_service(app)
    initialize_logging(app)

    app.register_blueprint(api_v1_bp)
    app.register_blueprint(auth_bp)
    register_api_error_handlers(app)
    _register_cli_commands(app)

    @login_manager.user_loader
    def load_user(user_id: str):
        return db_ext.session.get(User, int(user_id))

    return app
