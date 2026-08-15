"""
Central place for all configuration. Nothing else in the app should call
os.environ directly — import `settings` from here instead. This is what
lets us swap providers, rotate keys, or point at a different DB without
hunting through business logic.
"""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"

    # Database — async URL for the running app, sync URL for Alembic only.
    database_url: str
    database_url_sync: str

    # LLM providers
    groq_api_key: str = ""
    gemini_api_key: str = ""
    huggingface_api_key: str = ""

    jwt_secret: str = "dev-secret-change-me"

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    # cached so we parse .env once per process, not on every import
    return Settings()


settings = get_settings()
