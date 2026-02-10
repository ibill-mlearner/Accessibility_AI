import importlib.util
import sys
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CONFIG_PATH = ROOT / "AccessBackEnd" / "app" / "config.py"
SPEC = importlib.util.spec_from_file_location("backend_config_module", CONFIG_PATH)
config = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(config)


def test_base_and_instance_dir():
    expected_base = Path(config.__file__).resolve().parent
    expected_instance = expected_base.parent / "app"

    assert config._BASE_DIR == expected_base
    assert config._INSTANCE_DIR == expected_instance


def _reload_with_env(monkeypatch, **env):
    for k, v in env.items():
        if v is None:
            monkeypatch.delenv(k, raising=False)
        else:
            monkeypatch.setenv(k, str(v))

    spec = importlib.util.spec_from_file_location("backend_config_module", CONFIG_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


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


def test_logging_section_override(monkeypatch):
    c = _reload_with_env(monkeypatch, LOG_LEVEL="DEBUG", LOG_JSON="true")
    assert c.BaseConfig.LOG_LEVEL == "DEBUG"
    assert c.BaseConfig.LOG_JSON is True


def test_ai_section_override(monkeypatch):
    c = _reload_with_env(
        monkeypatch,
        AI_PROVIDER="live_agent",
        AI_TIMEOUT_SECONDS="12",
        AI_LIVE_ENDPOINT="http://localhost:9999/agent",
        AI_MOCK_RESOURCE_PATH="/tmp/mock.json",
    )
    assert c.BaseConfig.AI_PROVIDER == "live_agent"
    assert c.BaseConfig.AI_TIMEOUT_SECONDS == 12
    assert c.BaseConfig.AI_LIVE_ENDPOINT == "http://localhost:9999/agent"
    assert c.BaseConfig.AI_MOCK_RESOURCE_PATH == "/tmp/mock.json"


def test_get_config_selects_by_app_config(monkeypatch):
    c = _reload_with_env(monkeypatch, APP_CONFIG="testing")
    assert c.get_config() is c.TestingConfig
