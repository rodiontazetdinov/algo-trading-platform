"""FastAPI entrypoint. Serves the demo page + API + Prometheus /metrics."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from prometheus_client import make_asgi_app

from app.api.routes import router
from app.config import get_settings
from app.core.logging import configure_logging, get_logger

WEB_DIR = Path(__file__).parent / "web"

settings = get_settings()
configure_logging(settings.log_level)
log = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("startup", mode=settings.trading_mode)
    yield
    log.info("shutdown")


app = FastAPI(title="Algo Trading Platform", version="0.1.0", lifespan=lifespan)
app.include_router(router, prefix="/api")
app.mount("/metrics", make_asgi_app())


@app.get("/", include_in_schema=False)
async def root():
    """Serve the interactive demo page (falls back to JSON if it's missing)."""
    index = WEB_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    return JSONResponse({"service": "algo-trading-platform", "docs": "/docs", "metrics": "/metrics"})
