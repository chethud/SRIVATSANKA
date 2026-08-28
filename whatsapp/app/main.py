import logging

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import SessionLocal, init_db
from app.middleware.auth import AuthMiddleware
from app.routers import api, auth, chat, dev, orders, photos, resources, webhook
from app.services.gemini_conversation import is_gemini_configured
from app.services.scheduler import start_scheduler

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    log = logging.getLogger(__name__)
    try:
        await init_db()
    except OSError as exc:
        if getattr(exc, "errno", None) == 101:
            log.error(
                "Database host unreachable (errno 101). On Render set DATABASE_URL to Supabase "
                "Session pooler (pooler.supabase.com:5432), not Direct (db.xxx.supabase.co)."
            )
        raise
    except Exception as exc:
        err = str(exc).lower()
        if "tenant/user" in err or "tenant or user not found" in err:
            log.error(
                "Supabase pooler host/region does not match your project (tenant/user not found). "
                "Open Supabase → Connect → Session pooler and paste the full URI — do not guess "
                "aws-0 vs aws-1 or the region in the hostname."
            )
        elif "name or service not known" in err or "gaierror" in err:
            log.error(
                "Invalid DATABASE_URL host. Use Supabase Session pooler URI and URL-encode @ in password."
            )
        elif "password authentication failed" in err:
            log.error("Supabase rejected DATABASE_URL password — check password and URL-encoding.")
        else:
            log.error("Database startup failed: %s", exc)
        raise

    from app.supabase_auth import is_supabase_auth_configured, warmup_jwks

    if is_supabase_auth_configured():
        warmup_jwks()

    from app.data.seed_demo_data import clear_demo_rows, seed_demo_data
    from app.data.seed_excel_reference_orders import ensure_excel_reference_orders

    async with SessionLocal() as session:
        # Always strip demo-marked rows; keep dish catalog (seeded in init_db).
        cleared = await clear_demo_rows(session)
        log.info("Demo data cleared on startup: %s", cleared)
        if settings.seed_demo_on_startup:
            result = await seed_demo_data(session, force=True)
            log.info("Demo data seeded on startup (SEED_DEMO_ON_STARTUP=true): %s", result)
        if settings.seed_excel_refs_on_startup:
            try:
                excel_refs = await ensure_excel_reference_orders(session)
                log.info("Excel-reference orders on startup: %s", excel_refs)
            except Exception as exc:
                log.exception("Excel-reference seed failed (API will still start): %s", exc)
    start_scheduler()
    if is_gemini_configured():
        log.info("Gemini AI enabled for WhatsApp conversations (model=%s)", settings.gemini_model)
    else:
        log.warning(
            "GEMINI_API_KEY not configured — WhatsApp will use template replies. "
            "Set GEMINI_API_KEY in whatsapp/.env"
        )
    if settings.is_production:
        log.info("Running in PRODUCTION mode (dev routes and OpenAPI docs disabled)")
    yield


_docs_url = None if settings.is_production else "/docs"
_redoc_url = None if settings.is_production else "/redoc"
_openapi_url = None if settings.is_production else "/openapi.json"

app = FastAPI(
    title="SRIVATSANKA EVENTS API",
    description="WhatsApp AI agent and owner dashboard API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=_docs_url,
    redoc_url=_redoc_url,
    openapi_url=_openapi_url,
)

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
# Auth runs inside CORS so 401 responses still get CORS headers (browser otherwise shows "Failed to fetch").
app.add_middleware(AuthMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(webhook.router)
app.include_router(api.router)
app.include_router(chat.router)
app.include_router(orders.router)
app.include_router(resources.router)
app.include_router(photos.router)
if not settings.is_production:
    app.include_router(dev.router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    logging.getLogger(__name__).exception("Unhandled error: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/")
async def root() -> dict:
    payload = {
        "service": "Kannans WhatsApp AI Agent",
        "health": "/api/health",
        "environment": settings.environment,
    }
    if not settings.is_production:
        payload["docs"] = "/docs"
    return payload
