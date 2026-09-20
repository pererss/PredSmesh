from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    bot_token: str = Field(..., min_length=10)
    telegram_proxy: str = ""
    admin_id: int = Field(...)
    database_url: str = Field(..., min_length=10)
    direct_url: str = Field(..., min_length=10)

    supabase_url: str = ""
    supabase_publishable_key: str = ""

    reward_amount: int = Field(default=15, ge=1, le=100000)
    app_env: str = "production"
    log_level: str = "INFO"

    @field_validator("bot_token")
    @classmethod
    def _validate_bot_token(cls, value: str) -> str:
        token = value.strip()
        if token in {"", "YOUR_NEW_BOT_TOKEN", "YOUR_BOT_TOKEN"} or ":" not in token:
            raise ValueError(
                "BOT_TOKEN не задан или имеет неверный формат. "
                "Укажи токен в .env или в Environment Variables."
            )
        return token

    @field_validator("log_level")
    @classmethod
    def _validate_log_level(cls, value: str) -> str:
        return value.strip().upper()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
