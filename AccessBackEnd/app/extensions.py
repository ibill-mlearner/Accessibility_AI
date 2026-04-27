"""Shared Flask extension and module-config wiring surface.

This module owns process-level extension singletons (SQLAlchemy, migrations, auth/session helpers,
CORS, JWT) and keeps initialization centralized for the app-factory pattern. `load_module_configs(...)`
also resolves module-scoped config objects (auth, logging, db, AI thin config), stores them in
`app.extensions["module_configs"]`, and mirrors selected values into `app.config` for backward compatibility.

Handoff note: this is the primary place to understand where module config objects are loaded and how
legacy config keys are still populated while migration to module-owned config continues.
"""

from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from .auth import AuthModuleConfig
from .db.configs import DBModuleConfig
from .services.logging.module_config import LoggingModuleConfig
from .utils.env_config import parse_env


db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
cors = CORS()
login_manager = LoginManager()
login_manager.login_view = "auth.login"


# Handoff note: AI thin-config construction currently lives in extensions for centralized startup wiring;
# moving this into an AI-owned config module later would reduce cross-domain coupling.
def _build_ai_pipeline_thin_config() -> dict[str, object]:
    return {
        "model_name": str(parse_env("AI_MODEL_NAME", "HuggingFaceTB/SmolLM2-360M-Instruct")).strip(),
        "system_content": str(parse_env("AI_SYSTEM_CONTENT", "You are a concise assistant.")).strip(),
        "download_locally": str(parse_env("AI_DOWNLOAD_LOCALLY", "true")).strip().lower() in {"1", "true", "yes", "on"},
        "max_new_tokens": int(parse_env("AI_MAX_NEW_TOKENS", 256)),
    }


def load_module_configs(app: Flask) -> dict[str, object]:
    module_configs = {
        "ai_pipeline_thin": _build_ai_pipeline_thin_config(),
        "auth": AuthModuleConfig.from_env(),
        "logging": LoggingModuleConfig.from_env(),
        "db": DBModuleConfig.from_env(),
    }
    app.extensions["module_configs"] = module_configs
    app.config["AI_PIPELINE_THIN_CONFIG"] = module_configs["ai_pipeline_thin"]
    app.config["AUTH_CONFIG"] = module_configs["auth"]
    app.config["LOGGING_CONFIG"] = module_configs["logging"]
    app.config["DB_CONFIG"] = module_configs["db"]

    ai_cfg = module_configs["ai_pipeline_thin"]
    app.config["AI_PROVIDER"] = "huggingface"
    app.config["AI_MODEL_NAME"] = ai_cfg["model_name"]
    app.config["AI_SYSTEM_CONTENT"] = ai_cfg["system_content"]
    app.config["AI_DOWNLOAD_LOCALLY"] = ai_cfg["download_locally"]
    app.config["AI_MAX_NEW_TOKENS"] = ai_cfg["max_new_tokens"]
    app.config["AI_DEVICE_MAP"] = "auto"
    app.config["AI_TORCH_DTYPE"] = "auto"

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
