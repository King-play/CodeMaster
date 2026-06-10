from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "CodeMate"
    database_url: str = "sqlite:///./data/codemate.db"
    secret_key: str = "change-this-in-production"
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-5-mini"
    codemate_demo_mode: bool = True
    frontend_origin: str = "http://localhost:5173"
    max_code_chars: int = Field(default=60000, ge=1000)
    access_token_expire_minutes: int = Field(default=480, ge=15)
    allow_registration: bool = True
    codemate_enable_external_analyzers: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def db_path(self) -> Optional[Path]:
        prefix = "sqlite:///"
        if not self.database_url.startswith(prefix):
            return None
        path = self.database_url.removeprefix(prefix)
        if path.startswith("./"):
            return Path.cwd() / path[2:]
        return Path(path)


@lru_cache
def get_settings() -> Settings:
    return Settings()
