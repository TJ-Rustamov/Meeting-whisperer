from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes_meetings import router as meetings_router
from app.api.routes_settings import router as settings_router
from app.api.routes_ws import router as ws_router
from app.core.config import settings
from app.db.base import Base
from app.db.migrations import ensure_meetings_schema
from app.db.session import engine

Base.metadata.create_all(bind=engine)
ensure_meetings_schema(engine)

logging.basicConfig(
    level=getattr(logging, settings.log_level, logging.INFO),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)
logger.info(
    "Booting %s (log_level=%s, fake_model=%s, ws_sample_rate=%s)",
    settings.app_name,
    settings.log_level,
    settings.fake_model,
    settings.ws_sample_rate,
)

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/media", StaticFiles(directory=str(settings.audio_dir)), name="media")

app.include_router(meetings_router, prefix=settings.api_prefix)
app.include_router(settings_router, prefix=settings.api_prefix)
app.include_router(ws_router)


@app.get("/health")
def health():
    return {"ok": True}


if settings.frontend_dist_dir.exists():
    logger.info("Serving frontend dist from %s", settings.frontend_dist_dir)
    app.mount("/", StaticFiles(directory=str(settings.frontend_dist_dir), html=True), name="frontend")
