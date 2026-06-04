from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Always load whatsapp/.env regardless of process working directory
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "sqlite+aiosqlite:///./kannans.db"
    port: int = 8000

    gemini_api_key: str = ""
    gemini_model: str = "gemini-flash-latest"

    # Meta WhatsApp Cloud API
    whatsapp_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_verify_token: str = "kannans-verify-token"
    meta_app_secret: str = ""  # optional – verifies webhook signatures

    owner_phone_number: str = "917899102165"
    cors_origins: str = "http://localhost:5173,http://localhost:5174,http://localhost:5175"

    # Demo dashboard data (Settings → Load demo data, or POST /dev/seed)
    seed_demo_on_startup: bool = False
    dev_seed_token: str = ""  # optional X-Dev-Seed-Token header when set


def _load_settings() -> Settings:
    s = Settings()
    # Strip quotes if present in .env
    if s.gemini_api_key:
        s.gemini_api_key = s.gemini_api_key.strip().strip('"').strip("'")
    return s


settings = _load_settings()
