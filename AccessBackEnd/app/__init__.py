from __future__ import annotations

from pathlib import Path

from flask import Flask

from . import config
from .api.errors import register_api_error_handlers
from .api.v1.routes import api_v1_bp
from .blueprints.auth.routes import auth_bp
from .db import init_flask_database
from .db.settings import resolve_database_url
from .extensions import cors, db as db_ext, jwt, login_manager, migrate
from .logging_config import EventBus, LoggingObserver, configure_logging
from .models import User
from .services import AIPipelineConfig, AIPipelineService
from .services.db_logger import InteractionLoggingService, RotatingTextLogWriter


def _register_cli_commands(app: Flask) -> None:
    @app.cli.command("init-db")
    def init_db_command() -> None:
        """Create all configured database tables for the current app profile."""

        init_flask_database(app)
        print("Database schema initialized.")


def build_ai_service(app: Flask) -> AIPipelineService:
    provider = app.config["AI_PROVIDER"]
    if provider in {"live", "live_agent", "http"} and not app.config.get("AI_LIVE_ENDPOINT"):
        raise ValueError("AI_LIVE_ENDPOINT must be configured when AI_PROVIDER=live_agent")

    return AIPipelineService(
        AIPipelineConfig(
            provider=provider,
            mock_resource_path=app.config["AI_MOCK_RESOURCE_PATH"],
            live_endpoint=app.config["AI_LIVE_ENDPOINT"],
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

    cfg = config.get_config() if config_name is None else config.CONFIG_BY_NAME.get(config_name, config.DevelopmentConfig)
    app.config.from_object(cfg)
    app.config.from_pyfile("config.py", silent=True)

    app.config["SQLALCHEMY_DATABASE_URI"] = resolve_database_url(
        instance_path=app.instance_path,
        configured_url=app.config.get("SQLALCHEMY_DATABASE_URI"),
    )

    if app.config.get("DATA_BACKEND_FACTORY"):
        app.extensions["data_backend"] = app.config["DATA_BACKEND_FACTORY"]()

    configure_logging(app.config["LOG_LEVEL"])

    db_ext.init_app(app)
    migrate.init_app(app, db_ext)
    jwt.init_app(app)
    cors.init_app(
        app,
        resources={r"/*": {"origins": app.config["CORS_ORIGINS"]}},
        supports_credentials=app.config["CORS_SUPPORTS_CREDENTIALS"],
    )
    login_manager.init_app(app)

    event_bus = EventBus()
    event_bus.subscribe(LoggingObserver())
    app.extensions["event_bus"] = event_bus

    ai_service = build_ai_service(app)
    db_log_directory = app.config.get("DB_LOG_DIRECTORY") or (Path(app.root_path) / "instance").as_posix()
    app.extensions["ai_service"] = InteractionLoggingService(
        wrapped=ai_service,
        writer=RotatingTextLogWriter(log_dir=Path(db_log_directory)),
    )

    app.register_blueprint(api_v1_bp)
    app.register_blueprint(auth_bp)
    register_api_error_handlers(app)
    _register_cli_commands(app)

    @login_manager.user_loader
    def load_user(user_id: str):
        return User.query.get(int(user_id))

    return app
