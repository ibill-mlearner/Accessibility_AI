from __future__ import annotations

from flask import Flask
from flask import jsonify, request, session
from flask_login import current_user, logout_user
from sqlalchemy import inspect

from . import config
from .api.errors import register_api_error_handlers
from .api.v1.routes import api_v1_bp
from .utils.ai_checker import sync_ai_models_with_local_inventory
from .db import ensure_sqlite_compat_schema, init_flask_database
from .db.settings import resolve_database_url
from .extensions import cors, db as db_ext, jwt, load_module_configs, login_manager, migrate
from .services.logging import initialize_logging
from .models import User
from .services.ai_pipeline_gateway import AIPipelineGateway

def _register_cli_commands(app: Flask) -> None:
    @app.cli.command("init-db")
    def init_db_command() -> None:
        """Create all configured database tables for the current app profile."""

        print(
            f"Resolved SQLALCHEMY_DATABASE_URI: {app.config['SQLALCHEMY_DATABASE_URI']}"
        )
        init_flask_database(app)
        print("Database schema initialized.")


def build_ai_service(app: Flask) -> AIPipelineGateway:
    module_config = app.config.get("AI_PIPELINE_THIN_CONFIG")
    return AIPipelineGateway(config=app.config, module_config=module_config)


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
    module_configs = load_module_configs(app)

    app.config["SQLALCHEMY_DATABASE_URI"] = resolve_database_url(
        instance_path=app.instance_path,
        configured_url=app.config.get("SQLALCHEMY_DATABASE_URI"),
    )

    if app.config.get("DATA_BACKEND_FACTORY"):
        app.extensions["data_backend"] = app.config["DATA_BACKEND_FACTORY"]()

    db_ext.init_app(app)
    ensure_sqlite_compat_schema(app)
    migrate.init_app(app, db_ext)
    jwt.init_app(app)
    cors.init_app(
        app,
        resources={r"/*": {"origins": app.config["CORS_ORIGINS"]}},
        supports_credentials=app.config["CORS_SUPPORTS_CREDENTIALS"],
        # Allows credentialed cross-origin requests when frontend explicitly includes credentials.
    )

    login_manager.init_app(app)
    # Flask-Login manages server-side session identity via Flask session cookies.


    #wrapper to validate against common entity fiels setup in the users model
    @app.before_request
    def _validate_session_security_stamp():
        if not request.path.startswith("/api/"):
            return None
        if not getattr(current_user, "is_authenticated", False):
            return None

        user_stamp = getattr(current_user, "security_stamp", None)
        session_stamp = session.get("security_stamp")
        if not user_stamp or not session_stamp or session_stamp != user_stamp:
            logout_user()
            return (
                jsonify(
                    {
                        "error": {
                            "code": "unauthorized",
                            "message": "session invalid",
                            "details": {"reason": "security stamp mismatch"}
                        }
                    }
                ),
                401,
            )
        return None

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
    with app.app_context():
        try:
            if inspect(db_ext.engine).has_table("ai_models"):
                sync_ai_models_with_local_inventory(app)
            else:
                app.logger.info("Skipping AI model sync during app init because ai_models table is not created yet.")
        except Exception as exc:  # noqa: BLE001
            app.logger.warning("AI model sync skipped during app init: %s", exc)
    initialize_logging(app)
    app.logger.info("Loaded module configs: %s", ", ".join(sorted(module_configs.keys())))

    app.register_blueprint(api_v1_bp)
    register_api_error_handlers(app)
    _register_cli_commands(app)

    @login_manager.user_loader
    def load_user(user_id: str):
        return db_ext.session.get(User, int(user_id))

    return app
