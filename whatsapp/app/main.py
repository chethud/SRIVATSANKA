import logging

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routers import api, dev, orders, resources, webhook
from app.services.scheduler import start_scheduler

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await init_db()
    start_scheduler()
    yield


app = FastAPI(
    title="Kannans Catering API",
    description="WhatsApp AI agent and owner dashboard API",
    version="1.0.0",
    lifespan=lifespan,
)

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhook.router)
app.include_router(api.router)
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
