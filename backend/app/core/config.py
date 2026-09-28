"""Application configuration, loaded only from environment variables / .env.

No API key is ever hardcoded here or anywhere else in this codebase -- see
README.md for the two keys that were hardcoded in the original prototype
and must be rotated before this key material is trusted again.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    news_api_key: str | None = None
    fred_api_key: str | None = None
    naver_clova_api_key: str | None = None

    cors_allow_origins: list[str] = ["http://localhost:3000"]

    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
