from starlette.middleware.base import BaseHTTPMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.auth_tokens import decode_access_token
from app.config import settings

PUBLIC_EXACT = {"/", "/docs", "/openapi.json", "/redoc", "/health"}
PUBLIC_PREFIXES = (
    "/api/health",
    "/api/auth/login",
    "/webhook",
)

# Dev seed routes may authenticate with X-Dev-Seed-Token instead of Supabase JWT.
DEV_SEED_PATHS = {
    "/dev/seed",
    "/dev/seed-excel-refs",
    "/dev/clear-demo",
    "/dev/reset",
}


def _is_public(path: str) -> bool:
    if path in PUBLIC_EXACT:
        return True
    return any(path.startswith(p) for p in PUBLIC_PREFIXES)


def _dev_seed_token_ok(request: Request) -> bool:
    required = settings.dev_seed_token.strip()
    if not required:
        return False
    return request.headers.get("X-Dev-Seed-Token", "") == required


class AuthMiddleware(BaseHTTPMiddleware):
    """Require Bearer JWT on /api and /dev routes (WhatsApp webhook stays public)."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if request.method == "OPTIONS" or _is_public(path):
            return await call_next(request)
        if not (path.startswith("/api") or path.startswith("/dev")):
            return await call_next(request)

        if path in DEV_SEED_PATHS and _dev_seed_token_ok(request):
            request.state.user = {"sub": "dev-seed-token"}
            return await call_next(request)

        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"detail": "Login required"})
        token = auth[7:].strip()
        if not token:
            return JSONResponse(status_code=401, content={"detail": "Login required"})
        try:
            request.state.user = decode_access_token(token)
        except StarletteHTTPException as exc:
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
        except Exception:
            return JSONResponse(status_code=401, content={"detail": "Invalid or expired session"})

        return await call_next(request)
