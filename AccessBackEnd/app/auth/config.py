from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from app.utils.env_config import parse_env


@dataclass(slots=True)
class AuthModuleConfig:
    provider: str = "local"
    password_min_length: int = 10
    jwt_header_name: str = "Authorization"
    jwt_header_type: str = "Bearer"
    jwt_access_minutes: int = 30
    jwt_refresh_days: int = 14

    @classmethod
    def from_env(cls) -> "AuthModuleConfig":
        return cls(
            provider=parse_env("AUTH_PROVIDER", "local"),
            password_min_length=parse_env("PASSWORD_MIN_LENGTH", 10, int),
            jwt_header_name=parse_env("JWT_HEADER_NAME", "Authorization"),
            jwt_header_type=parse_env("JWT_HEADER_TYPE", "Bearer"),
            jwt_access_minutes=parse_env("JWT_ACCESS_TOKEN_MINUTES", 30, int),
            jwt_refresh_days=parse_env("JWT_REFRESH_TOKEN_DAYS", 14, int),
        )

    @property
    def jwt_access_expires(self) -> timedelta:
        return timedelta(minutes=self.jwt_access_minutes)

    @property
    def jwt_refresh_expires(self) -> timedelta:
        return timedelta(days=self.jwt_refresh_days)

    def summary(self) -> dict[str, str]:
        return {"section": "auth", "provider": self.provider}
