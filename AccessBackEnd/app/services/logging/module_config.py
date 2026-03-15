from __future__ import annotations

from dataclasses import dataclass

from app.utils.env_config import parse_csv_words, parse_env, parse_positive_int


@dataclass(slots=True)
class LoggingModuleConfig:
    level: str = "INFO"
    json: bool = False
    startup_test_runner_enabled: bool = False
    startup_test_runner_command: list[str] | None = None
    startup_test_runner_timeout_seconds: int = 180
    startup_test_runner_workdir: str | None = None

    @classmethod
    def from_env(cls) -> "LoggingModuleConfig":
        default_command = "python -m pytest AccessBackEnd/tests -q"
        return cls(
            level=parse_env("LOG_LEVEL", "INFO"),
            json=parse_env("LOG_JSON", False, bool),
            startup_test_runner_enabled=parse_env("STARTUP_TEST_RUNNER_ENABLED", False, bool),
            startup_test_runner_command=parse_csv_words(parse_env("STARTUP_TEST_RUNNER_COMMAND", default_command)),
            startup_test_runner_timeout_seconds=parse_positive_int("STARTUP_TEST_RUNNER_TIMEOUT_SECONDS", 180),
            startup_test_runner_workdir=parse_env("STARTUP_TEST_RUNNER_WORKDIR"),
        )

    def summary(self) -> dict[str, object]:
        return {"section": "logging", "level": self.level}
