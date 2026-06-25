import logging

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import SessionLocal, init_db
from app.middleware.auth import AuthMiddleware
from app.routers import api, auth, chat, dev, orders, resources, webhook
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
        if "name or service not known" in err or "gaierror" in err:
            log.error(
                "Invalid DATABASE_URL host. Use Supabase Session pooler URI and URL-encode @ in password."
            )
        elif "password authentication failed" in err:
            log.error("Supabase rejected DATABASE_URL password — check password and URL-encoding.")
        else:
            log.error("Database startup failed: %s", exc)
        raise

    from sqlalchemy import func, select

    from app.data.seed_demo_data import seed_demo_data
    from app.models import Enquiry

    async with SessionLocal() as session:
        count = await session.scalar(select(func.count()).select_from(Enquiry)) or 0
        should_seed = settings.seed_demo_on_startup or count == 0
        if should_seed:
            result = await seed_demo_data(session, force=settings.seed_demo_on_startup or count == 0)
            logging.getLogger(__name__).info("Demo data seeded on startup: %s", result)
    start_scheduler()
    log = logging.getLogger(__name__)
    if is_gemini_configured():
        log.info("Gemini AI enabled for WhatsApp conversations (model=%s)", settings.gemini_model)
    else:
        log.warning(
            "GEMINI_API_KEY not configured — WhatsApp will use template replies. "
            "Set GEMINI_API_KEY in whatsapp/.env"
        )
    yield


app = FastAPI(
    title="Kannans Catering API",
    description="WhatsApp AI agent and owner dashboard API",
    version="1.0.0",
    lifespan=lifespan,
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
app.include_router(dev.router)


@app.get("/")
async def root() -> dict:
    return {
        "service": "Kannans WhatsApp AI Agent",
        "docs": "/docs",
        "health": "/api/health",
    }
