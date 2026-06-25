"""Verify Supabase Auth JWTs for dashboard API access."""

import logging

import jwt
from fastapi import HTTPException
from jwt import PyJWKClient

from app.config import settings

logger = logging.getLogger(__name__)

ALGORITHM = "HS256"
AUDIENCE = "authenticated"
_JWK_CLIENT: PyJWKClient | None = None


def _supabase_base_url() -> str:
    return (settings.supabase_url or "").strip().rstrip("/")


def _jwks_url() -> str | None:
    base = _supabase_base_url()
    if not base:
        return None
    return f"{base}/auth/v1/.well-known/jwks.json"


def _get_jwk_client() -> PyJWKClient | None:
    global _JWK_CLIENT
    url = _jwks_url()
    if not url:
        return None
    if _JWK_CLIENT is None:
        _JWK_CLIENT = PyJWKClient(url, cache_keys=True)
    return _JWK_CLIENT


def is_supabase_auth_configured() -> bool:
    if _jwks_url():
        return True
    return len((settings.supabase_jwt_secret or "").strip()) >= 16


def _identity_from_payload(payload: dict) -> str:
    email = payload.get("email")
    if email:
        return str(email)
    sub = payload.get("sub")
    if sub:
        return str(sub)
    raise HTTPException(status_code=401, detail="Invalid token")


def _decode_with_jwks(token: str) -> dict:
    client = _get_jwk_client()
    if client is None:
        raise HTTPException(status_code=401, detail="Supabase auth not configured")
    try:
        signing_key = client.get_signing_key_from_jwt(token)
        algorithms = [signing_key.algorithm_name] if signing_key.algorithm_name else ["ES256", "HS256", "RS256"]
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=algorithms,
            audience=AUDIENCE,
            leeway=30,
        )
    except jwt.InvalidAudienceError:
        signing_key = client.get_signing_key_from_jwt(token)
        algorithms = [signing_key.algorithm_name] if signing_key.algorithm_name else ["ES256", "HS256", "RS256"]
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=algorithms,
            options={"verify_aud": False},
            leeway=30,
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired session") from exc
    except Exception as exc:
        logger.warning("Supabase JWKS verification failed: %s", exc)
        raise HTTPException(status_code=401, detail="Invalid or expired session") from exc


def _decode_with_shared_secret(token: str) -> dict:
    secret = settings.supabase_jwt_secret.strip()
    try:
        return jwt.decode(
            token,
            secret,
            algorithms=[ALGORITHM],
            audience=AUDIENCE,
        )
    except jwt.InvalidAudienceError:
        return jwt.decode(
            token,
            secret,
            algorithms=[ALGORITHM],
            options={"verify_aud": False},
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired session") from exc


def warmup_jwks() -> None:
    """Load Supabase public keys at startup so the first API request does not fail auth."""
    client = _get_jwk_client()
    if client is None:
        return
    try:
        client.fetch_data()
        logger.info("Supabase JWKS loaded from %s", _jwks_url())
    except Exception as exc:
        logger.warning("Supabase JWKS warmup failed: %s", exc)


def decode_supabase_access_token(token: str) -> str:
    """Return the signed-in user's email (or user id) from a Supabase access token."""
    if _jwks_url():
        return _identity_from_payload(_decode_with_jwks(token))
    return _identity_from_payload(_decode_with_shared_secret(token))
