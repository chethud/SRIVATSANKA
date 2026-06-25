from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Always load whatsapp/.env regardless of process working directory
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def normalize_database_url(url: str) -> str:
    """Accept Supabase/Render URLs and convert to SQLAlchemy async PostgreSQL."""
    raw = url.strip().strip('"').strip("'")
    if raw.startswith("postgres://"):
        raw = "postgresql://" + raw[len("postgres://") :]
    if raw.startswith("postgresql://") and "+asyncpg" not in raw and "+psycopg" not in raw:
        raw = "postgresql+asyncpg://" + raw[len("postgresql://") :]
    return raw


def is_sqlite_database(url: str) -> bool:
    return url.startswith("sqlite")


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

    owner_phone_number: str = "917899410254"
    cors_origins: str = "http://localhost:5173,http://localhost:5174,http://localhost:5175"

    # Supabase — PostgreSQL data + dashboard auth (JWT from Supabase Auth)
    supabase_url: str = ""
    supabase_jwt_secret: str = ""

    # Demo dashboard data (Settings → Load demo data, or POST /dev/seed)
    seed_demo_on_startup: bool = False
    dev_seed_token: str = ""  # optional X-Dev-Seed-Token header when set

    # Owner dashboard login (JWT — multiple members can sign in at once)
    dashboard_username: str = "Admin"
    dashboard_password: str = "Admin@123"
    jwt_secret: str = "kannans-change-this-secret-in-production"
    jwt_expire_hours: int = 168  # 7 days per session


def _load_settings() -> Settings:
    s = Settings()
    s.database_url = normalize_database_url(s.database_url)
    # Strip quotes if present in .env
    for attr in ("gemini_api_key", "jwt_secret", "dashboard_password", "supabase_jwt_secret"):
        val = getattr(s, attr, None)
        if val and isinstance(val, str):
            setattr(s, attr, val.strip().strip('"').strip("'"))
    return s


settings = _load_settings()
