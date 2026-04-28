import json
import os
from datetime import timedelta
from pathlib import Path

_BASE_DIR = Path(__file__).resolve().parent  # expect AccessBackEnd\app
_INSTANCE_DIR = _BASE_DIR.parent / "instance"
_DEFAULT_LOCAL_MODEL_DIR = _INSTANCE_DIR / "models" / "Qwen2.5-0.5B-Instruct"

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


def _env_positive_int(key: str, default: int) -> int:
    value = _env(key, default, int)
    if value <= 0:
        raise ValueError(f"{key} must be a positive integer; got {value}")
    return value


def _env_json(key: str, default: dict | None = None):
    raw = os.getenv(key)
    if raw is None:
        return default

    value = raw.strip()
    if not value:
        return default

    parsed = json.loads(value)
    if parsed is None:
        return default
    if not isinstance(parsed, dict):
        raise ValueError(f"Invalid JSON object for {key}: {raw}")
    return parsed


def _default_ai_model_name() -> str:
    """Use a local model path by default for runtime inference."""
    return str(_DEFAULT_LOCAL_MODEL_DIR)


class AppCoreConfig:
    """Core Flask/runtime identity settings shared by all environments.

    These values control app mode (`ENV`/`DEBUG`/`TESTING`), base app
    metadata, and foundational security behavior through `SECRET_KEY`.
    `SECRET_KEY` is consumed by Flask session signing and can also serve
    as a fallback secret for other subsystems when not explicitly set.
    """

    ENV = _env("FLASK_ENV", "development")
    DEBUG = _env("FLASK_DEBUG", False, bool)
    TESTING = False

    SECRET_KEY = _env("SECRET_KEY", "catsaregreat  ")
    JSON_SORT_KEYS = False

    APP_NAME = _env("APP_NAME", "AIAccess")


class ApiRoutingConfig:
    """HTTP route prefix settings for API namespace organization.

    `API_PREFIX` and `API_V1_PREFIX` define canonical mount paths used by
    route registration and client integrations. Keeping them centralized
    avoids hardcoded URL fragments across blueprint modules.
    """

    API_PREFIX = _env("API_PREFIX", "/api")
    API_V1_PREFIX = _env("API_V1_PREFIX", "/api/v1")


class DatabaseConfig:
    """Database connectivity and migration-path settings.

    Controls SQLAlchemy database URI selection and migration folder
    location. `SQLALCHEMY_TRACK_MODIFICATIONS` remains disabled to avoid
    unnecessary overhead and warning noise.
    """

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = _env("SQLALCHEMY_DATABASE_URI")
    MIGRATIONS_DIR = _env("MIGRATIONS_DIR", "migrations")


class JwtConfig:
    """JWT authentication header and token lifetime configuration.

    `JWT_SECRET_KEY` signs JWTs, defaulting to `SECRET_KEY` when a dedicated
    JWT secret is not provided. Access and refresh expiration windows are
    controlled independently to support short-lived access tokens and
    longer refresh sessions.
    """

    JWT_SECRET_KEY = _env("JWT_SECRET_KEY", _env("SECRET_KEY", "catsaregreat  "))
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        minutes=_env("JWT_ACCESS_TOKEN_MINUTES", 30, int)
    )
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(
        days=_env("JWT_REFRESH_TOKEN_DAYS", 14, int)
    )
    JWT_TOKEN_LOCATION = ("headers",)
    JWT_HEADER_NAME = _env("JWT_HEADER_NAME", "Authorization")
    JWT_HEADER_TYPE = _env("JWT_HEADER_TYPE", "Bearer")


class CorsConfig:
    """Cross-Origin Resource Sharing policy settings.

    `CORS_ORIGINS` lists allowed front-end origins and
    `CORS_SUPPORTS_CREDENTIALS` enables cookie/credential exchange where
    required by authenticated browser clients.
    """

    CORS_ORIGINS = _env("CORS_ORIGINS", "http://localhost:5173")
    CORS_SUPPORTS_CREDENTIALS = _env("CORS_SUPPORTS_CREDENTIALS", True, bool)


class SessionConfig:
    """Browser session-cookie hardening and transport behavior.

    These options control cookie naming and security flags:
    - `SESSION_COOKIE_HTTPONLY` blocks JavaScript access.
    - `SESSION_COOKIE_SAMESITE` limits cross-site send behavior.
    - `SESSION_COOKIE_SECURE` restricts transport to HTTPS when enabled.
    """

    SESSION_COOKIE_NAME = _env("SESSION_COOKIE_NAME", "aiaccess_session")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = _env("SESSION_COOKIE_SAMESITE", "Lax")
    SESSION_COOKIE_SECURE = _env("SESSION_COOKIE_SECURE", False, bool)


class AuthConfig:
    """Authentication provider and password-policy defaults.

    `AUTH_PROVIDER` selects the active authentication strategy and
    `PASSWORD_MIN_LENGTH` sets baseline credential complexity for local
    account flows.
    """

    AUTH_PROVIDER = _env("AUTH_PROVIDER", "local")
    PASSWORD_MIN_LENGTH = _env("PASSWORD_MIN_LENGTH", 10, int)


class RateLimitConfig:
    """Application-level request throttling controls.

    `RATE_LIMIT_ENABLED` toggles throttling behavior and
    `RATE_LIMIT_DEFAULT` provides the default rate string used by
    upstream limiter integration.
    """

    RATE_LIMIT_ENABLED = _env("RATE_LIMIT_ENABLED", False, bool)
    RATE_LIMIT_DEFAULT = _env("RATE_LIMIT_DEFAULT", "200 per day;50 per hour")


class LoggingConfig:
    """Structured logging verbosity and output format settings.

    `LOG_LEVEL` controls minimum emitted severity while `LOG_JSON`
    switches logging output between plain text and JSON serialization.
    """

    LOG_LEVEL = _env("LOG_LEVEL", "INFO")
    LOG_JSON = _env("LOG_JSON", False, bool)


class StartupTestRunnerConfig:
    """Optional startup-time test execution safeguards.

    Enables an opt-in preflight test runner command with configurable
    command arguments, timeout, and working directory. Useful for local
    development validation gates before serving requests.
    """

    STARTUP_TEST_RUNNER_ENABLED = _env("STARTUP_TEST_RUNNER_ENABLED", False, bool)
    STARTUP_TEST_RUNNER_COMMAND = _env(
        "STARTUP_TEST_RUNNER_COMMAND",
        "python -m pytest AccessBackEnd/tests -q",
        lambda value: str(value).strip().split(),
    )
    STARTUP_TEST_RUNNER_TIMEOUT_SECONDS = _env(
        "STARTUP_TEST_RUNNER_TIMEOUT_SECONDS",
        180,
        int,
    )
    STARTUP_TEST_RUNNER_WORKDIR = _env("STARTUP_TEST_RUNNER_WORKDIR")


class DataBackendConfig:
    """Pluggable data backend factory hook.

    `DATA_BACKEND_FACTORY` is intentionally nullable and can be populated
    by environment-specific bootstrap logic to inject alternate storage
    backends without changing caller code.
    """

    DATA_BACKEND_FACTORY = None


class AiConfig:
    """AI provider, model runtime, fallback, and guardrail settings.

    This section centralizes default AI behavior:
    - provider and model selection (`AI_PROVIDER`, `AI_MODEL_NAME`)
    - runtime controls (timeouts, endpoint selection, fallback behavior)
    - model option payloads and interaction logging paths
    - system guardrail prompt used as a baseline instruction
    """

    AI_PROVIDER = _env("AI_PROVIDER", "huggingface")
    AI_MODEL_NAME = _env("AI_MODEL_NAME", _default_ai_model_name())
    AI_HUGGINGFACE_CACHE_DIR = _env("AI_HUGGINGFACE_CACHE_DIR")
    AI_ENABLE_OLLAMA_FALLBACK = _env("AI_ENABLE_OLLAMA_FALLBACK", True, bool)
    AI_TIMEOUT_SECONDS = _env("AI_TIMEOUT_SECONDS", 60, int)
    AI_OLLAMA_ENDPOINT = _env(
        "AI_OLLAMA_ENDPOINT",
        "http://localhost:11434/api/chat",
    )

    AI_OLLAMA_MODEL = _env("AI_OLLAMA_MODEL", AI_MODEL_NAME)
    AI_OLLAMA_OPTIONS = _env_json("AI_OLLAMA_OPTIONS", {})
    AI_LIVE_ENDPOINT = _env("AI_LIVE_ENDPOINT", AI_OLLAMA_ENDPOINT)
    AI_MODEL_FAMILIES_JSON = _env("AI_MODEL_FAMILIES_JSON")
    AI_INTERACTION_LOG_DIR = _env("AI_INTERACTION_LOG_DIR") or _env(
        "INTERACTION_LOG_DIR"
    )
    DB_LOG_DIRECTORY = _env("DB_LOG_DIRECTORY")  # Deprecated: use AI_INTERACTION_LOG_DIR
    AI_SYSTEM_GUARDRAIL_PROMPT = _env(
        "AI_SYSTEM_GUARDRAIL_PROMPT",
        "You are an accessibility-focused educational assistant. Refuse or safely redirect requests that are harmful, illegal, privacy-invasive, or outside educational support. Keep responses factual and classroom-appropriate.",
    )


class BaseConfig(
    AppCoreConfig,
    ApiRoutingConfig,
    DatabaseConfig,
    JwtConfig,
    CorsConfig,
    SessionConfig,
    AuthConfig,
    RateLimitConfig,
    LoggingConfig,
    StartupTestRunnerConfig,
    DataBackendConfig,
    AiConfig,
):
    """Composed default configuration shared across concrete environments.

    This class combines all focused config sections into a single object
    expected by Flask app initialization and extension bootstrap code.
    """

    pass


class DevelopmentConfig(BaseConfig):
    """Local development overrides prioritizing debug visibility."""

    DEBUG = True
    LOG_LEVEL = _env("LOG_LEVEL", "DEBUG")


class TestingConfig(BaseConfig):
    """Test environment overrides for isolated and fast test execution."""

    TESTING = True
    DEBUG = False
    AI_PROVIDER = _env("TEST_AI_PROVIDER", "huggingface")
    SQLALCHEMY_DATABASE_URI = _env("TEST_DATABASE_URL", "sqlite:///:memory:")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=5)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(minutes=10)
    SESSION_COOKIE_SECURE = False


class ProductionConfig(BaseConfig):
    """Production overrides emphasizing secure defaults."""

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
