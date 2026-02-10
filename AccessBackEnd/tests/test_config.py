# external
import importlib
from pathlib import Path
from datetime import timedelta

# local
from AccessBackEnd.app import config

#todo
# This test file currently validates configuration behavior by overriding environment inputs and asserting deterministic outcomes.
# In the future, this file will be rewritten to define performance expectations and system-level guarantees rather than static configuration values.
# These tests will evolve into benchmarks and regression checks that assert acceptable behavior under load, latency, and resource constraints.

# paths
def test_base_and_instance_dir():
    expected_base = Path(config.__file__).resolve().parent
    expected_instance = expected_base.parent / "app"

    assert config._BASE_DIR == expected_base
    assert config._INSTANCE_DIR == expected_instance

#monkeypatch testing ... if env variables are changed beyond expectations
def _reload_with_env(monkeypatch, **env):
    for k, v in env.items():
        if v is None:
            monkeypatch.delenv(k, raising=False)
        else:
            monkeypatch.setenv(k, str(v))
    return importlib.reload(config)

def test_app_section_override(monkeypatch):
    c = _reload_with_env(monkeypatch, APP_NAME="MyDemoApp")
    assert c.BaseConfig.APP_NAME == "MyDemoApp"

def test_sql_section_override(monkeypatch):
    c = _reload_with_env(monkeypatch, DATABASE_URL="sqlite:///override.db")
    assert c.BaseConfig.SQLALCHEMY_DATABASE_URI == "sqlite:///override.db"

def test_migrations_section_override(monkeypatch):
    c = _reload_with_env(monkeypatch, MIGRATIONS_DIR="db_migrations")
    assert c.BaseConfig.MIGRATIONS_DIR == "db_migrations"

def test_jwt_section_override(monkeypatch):
    c = _reload_with_env(
        monkeypatch,
        JWT_HEADER_NAME="X-Auth",
        JWT_HEADER_TYPE="Token",
        JWT_ACCESS_TOKEN_MINUTES="12",
        JWT_REFRESH_TOKEN_DAYS="3",
    )
    assert c.BaseConfig.JWT_HEADER_NAME == "X-Auth"
    assert c.BaseConfig.JWT_HEADER_TYPE == "Token"
    assert isinstance(c.BaseConfig.JWT_ACCESS_TOKEN_EXPIRES, timedelta)
    assert isinstance(c.BaseConfig.JWT_REFRESH_TOKEN_EXPIRES, timedelta)
    assert c.BaseConfig.JWT_ACCESS_TOKEN_EXPIRES == timedelta(minutes=12)
    assert c.BaseConfig.JWT_REFRESH_TOKEN_EXPIRES == timedelta(days=3)

def test_session_cookie_section_override(monkeypatch):
    c = _reload_with_env(
        monkeypatch,
        SESSION_COOKIE_NAME="demo_session",
        SESSION_COOKIE_SAMESITE="Strict",
        SESSION_COOKIE_SECURE="true",
    )
    assert c.BaseConfig.SESSION_COOKIE_NAME == "demo_session"
    assert c.BaseConfig.SESSION_COOKIE_SAMESITE == "Strict"
    assert c.BaseConfig.SESSION_COOKIE_SECURE is True


def test_auth_section_override(monkeypatch):
    c = _reload_with_env(monkeypatch, AUTH_PROVIDER="oauth", PASSWORD_MIN_LENGTH="16")
    assert c.BaseConfig.AUTH_PROVIDER == "oauth"
    assert c.BaseConfig.PASSWORD_MIN_LENGTH == 16

def test_cors_section_override(monkeypatch):
    c = _reload_with_env(monkeypatch, CORS_ORIGINS="http://localhost:3000", CORS_SUPPORTS_CREDENTIALS="false")
    assert c.BaseConfig.CORS_ORIGINS == "http://localhost:3000"
    assert c.BaseConfig.CORS_SUPPORTS_CREDENTIALS is False

def test_session_cookie_section_override(monkeypatch):
    c = _reload_with_env(
        monkeypatch,
        SESSION_COOKIE_NAME="demo_session",
        SESSION_COOKIE_SAMESITE="Strict",
        SESSION_COOKIE_SECURE="true",
    )
    assert c.BaseConfig.SESSION_COOKIE_NAME == "demo_session"
    assert c.BaseConfig.SESSION_COOKIE_SAMESITE == "Strict"
    assert c.BaseConfig.SESSION_COOKIE_SECURE is True

def test_rate_limit_section_override(monkeypatch):
    c = _reload_with_env(monkeypatch, RATE_LIMIT_ENABLED="true", RATE_LIMIT_DEFAULT="10 per minute")
    assert c.BaseConfig.RATE_LIMIT_ENABLED is True
    assert c.BaseConfig.RATE_LIMIT_DEFAULT == "10 per minute"


def test_logging_section_override(monkeypatch):
    c = _reload_with_env(monkeypatch, LOG_LEVEL="DEBUG", LOG_JSON="true")
    assert c.BaseConfig.LOG_LEVEL == "DEBUG"
    assert c.BaseConfig.LOG_JSON is True


def test_ai_section_override(monkeypatch):
    c = _reload_with_env(monkeypatch, AI_PROVIDER="openai", AI_TIMEOUT_SECONDS="5", AI_MODEL_NAME="gpt-4.1-mini")
    assert c.BaseConfig.AI_PROVIDER == "openai"
    assert c.BaseConfig.AI_TIMEOUT_SECONDS == 5
    assert c.BaseConfig.AI_MODEL_NAME == "gpt-4.1-mini"


def test_get_config_selects_by_app_config(monkeypatch):
    c = _reload_with_env(monkeypatch, APP_CONFIG="testing")
    assert c.get_config() is c.TestingConfig


def test_get_config_selects_by_flask_env_when_app_config_missing(monkeypatch):
    c = _reload_with_env(monkeypatch, APP_CONFIG=None, FLASK_ENV="production")
    assert c.get_config() is c.ProductionConfig