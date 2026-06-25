"""Verify Supabase Auth JWTs for dashboard API access."""

import jwt
from fastapi import HTTPException

from app.config import settings

ALGORITHM = "HS256"
AUDIENCE = "authenticated"


def is_supabase_auth_configured() -> bool:
    return len((settings.supabase_jwt_secret or "").strip()) >= 16


def decode_supabase_access_token(token: str) -> str:
    """Return the signed-in user's email (or user id) from a Supabase access token."""
    secret = settings.supabase_jwt_secret.strip()
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=[ALGORITHM],
            audience=AUDIENCE,
        )
    except jwt.InvalidAudienceError:
        payload = jwt.decode(
            token,
            secret,
            algorithms=[ALGORITHM],
            options={"verify_aud": False},
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired session") from exc

    email = payload.get("email")
    if email:
        return str(email)
    sub = payload.get("sub")
    if sub:
        return str(sub)
    raise HTTPException(status_code=401, detail="Invalid token")
