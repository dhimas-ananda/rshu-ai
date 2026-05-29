"""app/main.py v3.2 — production ready"""
import asyncio
import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

APP_VERSION  = "3.2.0"
MAX_CONCURRENT = int(os.getenv("MAX_CONCURRENT", "10"))
PORT           = int(os.getenv("PORT", "8000"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("RSHU AI v%s memulai (PORT=%s, MAX_CONCURRENT=%s)...",
                APP_VERSION, PORT, MAX_CONCURRENT)
    from .engine.pipeline import DiagnosisPipeline
    pipeline = DiagnosisPipeline()
    try:
        pipeline.load_master_data()
    except Exception as exc:
        logger.warning("Master data belum bisa dimuat (%s). Mode demo aktif.", exc)
    app.state.matcher   = pipeline
    app.state.semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    yield
    logger.info("RSHU AI v%s berhenti.", APP_VERSION)


app = FastAPI(
    title="RSHU AI Diagnosa Keperawatan",
    version=APP_VERSION,
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
)

_static = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(_static):
    app.mount("/static", StaticFiles(directory=_static), name="static")

from .routers import form, predict, test, admin
app.include_router(form.router)
app.include_router(predict.router)
app.include_router(test.router)
app.include_router(admin.router)


@app.get("/health")
async def health():
    from .db import check_connection
    db_ok = False
    try: db_ok = check_connection()
    except Exception: pass
    matcher = getattr(app.state, "matcher", None)
    loaded  = matcher is not None and getattr(matcher, "loaded", False)
    stats   = getattr(matcher, "_stats", {}) if loaded else {}
    sem     = getattr(app.state, "semaphore", None)
    active  = (MAX_CONCURRENT - sem._value) if sem else 0
    return {
        "status":          "ok"         if (db_ok and loaded) else "degraded",
        "database":        "connected"  if db_ok  else "disconnected",
        "master_data":     "loaded"     if loaded else "not_loaded",
        "diagnosa_count":  stats.get("diagnosa",   0),
        "phrase_count":    stats.get("frasa_unik", 0),
        "active_requests": active,
        "max_concurrent":  MAX_CONCURRENT,
        "version":         APP_VERSION,
    }
