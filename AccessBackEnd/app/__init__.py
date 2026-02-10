from __future__ import annotations

from flask import Flask

from . import config
from .api.v1.routes import api_v1_bp
from .blueprints.auth.routes import auth_bp
from .extensions import cors, db, jwt, login_manager, migrate
from .logging_config import EventBus, LoggingObserver, configure_logging
from .models import User
from .services import AIPipelineService


def create_app(config_name: str | None = None) -> Flask:
    app = Flask(__name__)

    cfg = config.get_config() if config_name is None else config.CONFIG_BY_NAME.get(config_name, config.DevelopmentConfig)
    app.config.from_object(cfg)

    configure_logging(app.config["LOG_LEVEL"])

    db.init_app(app)
    migrate.init_app(app, db)
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

    app.extensions["ai_service"] = AIPipelineService(
        provider=app.config["AI_PROVIDER"],
        mock_resource_path=app.config["AI_MOCK_RESOURCE_PATH"],
        live_endpoint=app.config["AI_LIVE_ENDPOINT"],
        timeout_seconds=app.config["AI_TIMEOUT_SECONDS"],
    )

    app.register_blueprint(api_v1_bp)
    app.register_blueprint(auth_bp)

    @login_manager.user_loader
    def load_user(user_id: str):
        return User.query.get(int(user_id))

    return app
