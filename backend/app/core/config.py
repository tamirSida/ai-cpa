from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    firebase_project_id: str = ""
    google_application_credentials: str = ""
    openai_api_key: str = ""
    openai_command_model: str = "gpt-4.1-mini"
    openai_vision_model: str = "gpt-4.1-mini"
    cloudinary_url: str = ""
    receipt_signing_p12_path: str = "secrets/receipt-signing.p12"
    receipt_signing_p12_password: str = ""
    cors_origins: list[str] = ["http://localhost:3000"]
    annual_limit_ils: int = 122833
    env: str = "dev"


# Cached for the process lifetime: env var changes after the first call are invisible.
# Tests must set env vars (or call get_settings.cache_clear()) BEFORE importing app.main.
@lru_cache
def get_settings() -> Settings:
    return Settings()
