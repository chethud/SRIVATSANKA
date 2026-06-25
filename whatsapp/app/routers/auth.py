import secrets

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.auth_tokens import create_access_token, decode_access_token
from app.config import settings

from app.supabase_auth import is_supabase_auth_configured

router = APIRouter(prefix="/api/auth", tags=["auth"])
_bearer = HTTPBearer(auto_error=False)


class LoginIn(BaseModel):
    username: str
    password: str


class LoginOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str


class MeOut(BaseModel):
    username: str
    auth_provider: str = "legacy"


def _verify_login(username: str, password: str) -> bool:
    expected_user = settings.dashboard_username
    expected_pass = settings.dashboard_password
    user_ok = secrets.compare_digest(username.strip(), expected_user)
    pass_ok = secrets.compare_digest(password, expected_pass)
    return user_ok and pass_ok


@router.post("/login", response_model=LoginOut)
async def login(payload: LoginIn) -> LoginOut:
    if is_supabase_auth_configured():
        raise HTTPException(
            status_code=400,
            detail="Dashboard sign-in uses Supabase. Open the website and sign in with your email.",
        )
    if not _verify_login(payload.username, payload.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    name = payload.username.strip()
    token = create_access_token(name)
    return LoginOut(access_token=token, username=name)


@router.get("/me", response_model=MeOut)
async def me(credentials: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> MeOut:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Login required")
    username = decode_access_token(credentials.credentials)
    provider = "supabase" if is_supabase_auth_configured() else "legacy"
    return MeOut(username=username, auth_provider=provider)
