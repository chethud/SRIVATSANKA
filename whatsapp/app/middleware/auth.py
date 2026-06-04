from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.auth_tokens import decode_access_token

PUBLIC_EXACT = {"/", "/docs", "/openapi.json", "/redoc"}
PUBLIC_PREFIXES = (
    "/api/health",
    "/api/auth/login",
    "/webhook",
)


def _is_public(path: str) -> bool:
    if path in PUBLIC_EXACT:
        return True
    return any(path.startswith(p) for p in PUBLIC_PREFIXES)


class AuthMiddleware(BaseHTTPMiddleware):
    """Require Bearer JWT on /api and /dev routes (WhatsApp webhook stays public)."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if request.method == "OPTIONS" or _is_public(path):
            return await call_next(request)
        if not (path.startswith("/api") or path.startswith("/dev")):
            return await call_next(request)

        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"detail": "Login required"})
        token = auth[7:].strip()
        if not token:
            return JSONResponse(status_code=401, content={"detail": "Login required"})
        try:
            request.state.user = decode_access_token(token)
        except HTTPException as exc:
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

        return await call_next(request)
