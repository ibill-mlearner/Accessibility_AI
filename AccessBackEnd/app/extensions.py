"""

Shared Flask extension singletons.

.. dev note
These were made as single entry points for readability
Issues:
flask_jwt_extended was not fully implemented
flask_login is not the best use for session management, should just be using flask_jwt
no migration setup yet

.. codex note
These are initialized in :func:`app.create_app` to keep the application
factory pattern clean and test-friendly. (instantiate here, make available everywhere)

"""

from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from .auth import AuthModuleConfig
from .db.configs import DBModuleConfig
from .services.ai_pipeline_v2.config import AIPipelineV2ModuleConfig
from .services.logging.module_config import LoggingModuleConfig


db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
cors = CORS()
login_manager = LoginManager()
login_manager.login_view = "auth.login"


def load_module_configs(app: Flask) -> dict[str, object]:
    module_configs = {
        "ai_pipeline_v2": AIPipelineV2ModuleConfig.from_env(),
        "auth": AuthModuleConfig.from_env(),
        "logging": LoggingModuleConfig.from_env(),
        "db": DBModuleConfig.from_env(),
    }
    app.extensions["module_configs"] = module_configs
    app.config["AI_PIPELINE_V2_CONFIG"] = module_configs["ai_pipeline_v2"]
    app.config["AUTH_CONFIG"] = module_configs["auth"]
    app.config["LOGGING_CONFIG"] = module_configs["logging"]
    app.config["DB_CONFIG"] = module_configs["db"]

    # Transitional adapter for legacy config keys.
    ai_cfg = module_configs["ai_pipeline_v2"]
    app.config["AI_PROVIDER"] = ai_cfg.provider
    app.config["AI_MODEL_NAME"] = ai_cfg.model_name
    app.config["AI_OLLAMA_ENDPOINT"] = ai_cfg.ollama_endpoint
    app.config["AI_LIVE_ENDPOINT"] = ai_cfg.live_endpoint
    app.config["AI_OLLAMA_MODEL"] = ai_cfg.ollama_model_id
    app.config["AI_OLLAMA_OPTIONS"] = ai_cfg.ollama_options
    app.config["AI_TIMEOUT_SECONDS"] = ai_cfg.timeout_seconds
    app.config["AI_HUGGINGFACE_CACHE_DIR"] = ai_cfg.huggingface_cache_dir
    app.config["AI_ENABLE_OLLAMA_FALLBACK"] = ai_cfg.enable_ollama_fallback
    app.config["AI_INVENTORY_CACHE_TTL_SECONDS"] = ai_cfg.inventory_cache_ttl_seconds

    auth_cfg = module_configs["auth"]
    app.config["AUTH_PROVIDER"] = auth_cfg.provider
    app.config["PASSWORD_MIN_LENGTH"] = auth_cfg.password_min_length
    app.config["JWT_HEADER_NAME"] = auth_cfg.jwt_header_name
    app.config["JWT_HEADER_TYPE"] = auth_cfg.jwt_header_type
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = auth_cfg.jwt_access_expires
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = auth_cfg.jwt_refresh_expires

    log_cfg = module_configs["logging"]
    app.config["LOG_LEVEL"] = log_cfg.level
    app.config["LOG_JSON"] = log_cfg.json
    app.config["STARTUP_TEST_RUNNER_ENABLED"] = log_cfg.startup_test_runner_enabled
    app.config["STARTUP_TEST_RUNNER_COMMAND"] = log_cfg.startup_test_runner_command
    app.config["STARTUP_TEST_RUNNER_TIMEOUT_SECONDS"] = log_cfg.startup_test_runner_timeout_seconds
    app.config["STARTUP_TEST_RUNNER_WORKDIR"] = log_cfg.startup_test_runner_workdir

    db_cfg = module_configs["db"]
    if db_cfg.sqlalchemy_database_uri:
        app.config["SQLALCHEMY_DATABASE_URI"] = db_cfg.sqlalchemy_database_uri
    app.config["MIGRATIONS_DIR"] = db_cfg.migrations_dir

    return module_configs
