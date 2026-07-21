from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException

from app.config import settings
from app.supabase_auth import decode_supabase_access_token, is_supabase_auth_configured

ALGORITHM = "HS256"


def create_access_token(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expire_hours)
    payload = {"sub": username, "exp": expire, "iat": datetime.now(timezone.utc)}
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def _decode_legacy_access_token(token: str) -> str:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired session") from exc
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Invalid token")
    return str(sub)


def decode_access_token(token: str) -> str:
    """Accept Supabase Auth tokens, with legacy dashboard JWT as fallback."""
    if is_supabase_auth_configured():
        try:
            return decode_supabase_access_token(token)
        except HTTPException:
            # Local/dev: allow Admin JWT if Supabase verification fails
            try:
                return _decode_legacy_access_token(token)
            except HTTPException:
                raise
    return _decode_legacy_access_token(token)
