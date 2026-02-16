import os
from datetime import timedelta
from pathlib import Path

_BASE_DIR = Path(__file__).resolve().parent # expect AccessBackEnd\app
_INSTANCE_DIR = _BASE_DIR.parent / "instance"

def _env(key: str, default=None, cast=None):
    val = os.getenv(key, default)
    if val is None:
        return None
    if cast is None:
        return val
    if cast is bool:
        s = str(val).strip().lower()
        if s in {"1", "true", "t", "yes", "y", "on"}:
            return True
        if s in {"0", "false", "f", "no", "n", "off"}:
            return False
        raise ValueError(f"Invalid boolean for {key}: {val}")
    if cast is int:
        return int(val)
    if cast is float:
        return float(val)
    return cast(val)


class BaseConfig:
    ENV = _env("FLASK_ENV", "development")
    DEBUG = _env("FLASK_DEBUG", False, bool)
    TESTING = False

    SECRET_KEY = _env("SECRET_KEY", "catsaregreat  ")
    JSON_SORT_KEYS = False

    APP_NAME = _env("APP_NAME", "AIAccess")

    API_PREFIX = _env("API_PREFIX", "/api")
    API_V1_PREFIX = _env("API_V1_PREFIX", "/api/v1")

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = _env("SQLALCHEMY_DATABASE_URI")

    MIGRATIONS_DIR = _env("MIGRATIONS_DIR", "migrations")

    JWT_SECRET_KEY = _env("JWT_SECRET_KEY", SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        minutes=_env("JWT_ACCESS_TOKEN_MINUTES", 30, int)
    )
    #todo: token time limit enforcement
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(
        days=_env("JWT_REFRESH_TOKEN_DAYS", 14, int)
    )
    JWT_TOKEN_LOCATION = ("headers",)
    JWT_HEADER_NAME = _env("JWT_HEADER_NAME", "Authorization")
    JWT_HEADER_TYPE = _env("JWT_HEADER_TYPE", "Bearer")

    CORS_ORIGINS = _env("CORS_ORIGINS", "http://localhost:5173")
    CORS_SUPPORTS_CREDENTIALS = _env("CORS_SUPPORTS_CREDENTIALS", True, bool)

    SESSION_COOKIE_NAME = _env("SESSION_COOKIE_NAME", "aiaccess_session")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = _env("SESSION_COOKIE_SAMESITE", "Lax")
    SESSION_COOKIE_SECURE = _env("SESSION_COOKIE_SECURE", False, bool)

    AUTH_PROVIDER = _env("AUTH_PROVIDER", "local")
    PASSWORD_MIN_LENGTH = _env("PASSWORD_MIN_LENGTH", 10, int)

    RATE_LIMIT_ENABLED = _env("RATE_LIMIT_ENABLED", False, bool)
    RATE_LIMIT_DEFAULT = _env("RATE_LIMIT_DEFAULT", "200 per day;50 per hour")

    LOG_LEVEL = _env("LOG_LEVEL", "INFO")
    LOG_JSON = _env("LOG_JSON", False, bool)

    DATA_BACKEND_FACTORY = None

    AI_PROVIDER = _env("AI_PROVIDER", "mock_json")
    AI_MODEL_NAME = _env("AI_MODEL_NAME", "default-model")
    AI_TIMEOUT_SECONDS = _env("AI_TIMEOUT_SECONDS", 60, int)
    AI_LIVE_ENDPOINT = _env("AI_LIVE_ENDPOINT", "")
    AI_MOCK_RESOURCE_PATH = _env(
        "AI_MOCK_RESOURCE_PATH",
        (_BASE_DIR / "resources" / "mock_ai_response.json").as_posix(),
    )
    AI_INTERACTION_LOG_DIR = _env("AI_INTERACTION_LOG_DIR") or _env("INTERACTION_LOG_DIR")
    DB_LOG_DIRECTORY = _env("DB_LOG_DIRECTORY")  # Deprecated: use AI_INTERACTION_LOG_DIR

class DevelopmentConfig(BaseConfig):
    DEBUG = True

class TestingConfig(BaseConfig):
    TESTING = True
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = _env("TEST_DATABASE_URL", "sqlite:///:memory:")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=5)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(minutes=10)
    SESSION_COOKIE_SECURE = False

class ProductionConfig(BaseConfig):
    DEBUG = False
    SESSION_COOKIE_SECURE = True

CONFIG_BY_NAME = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}

def get_config():
    name = _env("APP_CONFIG", _env("FLASK_ENV", "development")).strip().lower()
    return CONFIG_BY_NAME.get(name, DevelopmentConfig)
