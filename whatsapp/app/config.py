from pathlib import Path
from urllib.parse import urlparse
import logging

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# Always load whatsapp/.env regardless of process working directory
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def normalize_database_url(url: str) -> str:
    """Accept Supabase/Render URLs and convert to SQLAlchemy async PostgreSQL."""
    raw = url.strip().strip('"').strip("'")
    if raw.lower().startswith(("http://", "https://")):
        raise ValueError(
            "DATABASE_URL must be the Postgres connection URI from Supabase → Database, "
            "not the project URL (https://xxxx.supabase.co)."
        )
    if raw.startswith("postgres://"):
        raw = "postgresql://" + raw[len("postgres://") :]
    if raw.startswith("postgresql://") and "+asyncpg" not in raw and "+psycopg" not in raw:
        raw = "postgresql+asyncpg://" + raw[len("postgresql://") :]
    return raw


def validate_database_url(url: str) -> None:
    """Fail fast with a helpful message when DATABASE_URL is malformed."""
    if is_sqlite_database(url):
        return

    lower = url.lower()
    if any(
        marker in lower
        for marker in (
            "host-from-connect",
            "paste-full",
            "your_db_password",
            "your-password",
            "[your-password]",
            "connect-button",
        )
    ):
        raise ValueError(
            "DATABASE_URL still contains placeholder text from the docs. On Render, set the real "
            "Session pooler URI from Supabase → Connect (port 5432) and URL-encode @ in the password."
        )

    parse_target = url
    for prefix in ("postgresql+asyncpg://", "postgresql://", "postgres://"):
        if parse_target.startswith(prefix):
            parse_target = "postgresql://" + parse_target[len(prefix) :]
            break

    try:
        parsed = urlparse(parse_target)
    except ValueError as exc:
        raise ValueError(
            f"DATABASE_URL is not a valid Postgres URI ({exc}). "
            "Copy Session pooler URI from Supabase → Connect and URL-encode special characters in the password."
        ) from exc
    host = (parsed.hostname or "").strip()
    user = (parsed.username or "").strip()
    if host and user and "pooler.supabase.com" in host:
        logger.info("DATABASE_URL pooler host=%s user=%s", host, user)
    if not host:
        raise ValueError(
            "DATABASE_URL could not be parsed — the database host is missing. "
            "If your password contains @, #, /, or %, URL-encode it, or reset the Supabase DB password to letters and numbers only."
        )

    if host.startswith("db.") and host.endswith(".supabase.co"):
        logger.warning(
            "DATABASE_URL uses Supabase direct host (%s). On Render, use Session pooler "
            "(aws-0-REGION.pooler.supabase.com:5432) or deploy may fail with 'Network is unreachable'.",
            host,
        )

    if host.endswith(".supabase.co") and not host.startswith("db.") and "pooler" not in host:
        raise ValueError(
            f"DATABASE_URL host '{host}' is the Supabase API domain, not the database host. "
            "Copy the URI from Supabase → Project Settings → Database → Connection string → Direct. "
            "Host should look like: db.hlzndlmcvpmsxzkawsbz.supabase.co"
        )


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
    supabase_anon_key: str = ""  # publishable/anon key — fallback token verification via Auth API
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
    validate_database_url(s.database_url)
    # Strip quotes if present in .env
    for attr in ("gemini_api_key", "jwt_secret", "dashboard_password", "supabase_jwt_secret", "supabase_anon_key"):
        val = getattr(s, attr, None)
        if val and isinstance(val, str):
            setattr(s, attr, val.strip().strip('"').strip("'"))
    return s


settings = _load_settings()
