import logging
import threading
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import auth, conversations, documents, health, search
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.services.processing import run_worker

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """In development, run the document worker in a background thread of the API process."""
    stop = threading.Event()
    worker = None
    if get_settings().run_worker_in_api:
        worker = threading.Thread(target=run_worker, args=(stop,), name="worker", daemon=True)
        worker.start()
    yield
    stop.set()
    if worker:
        worker.join(timeout=10)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Daleel API",
        version="0.3.0",
        description="Ask questions about Arabic and English documents and get cited answers.",
        # Hide interactive docs in production; keep them for local development.
        docs_url=None if settings.is_production else "/api/docs",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )
    register_error_handlers(app)
    app.include_router(health.router, prefix="/api")
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(documents.router, prefix="/api/v1")
    app.include_router(search.router, prefix="/api/v1")
    app.include_router(conversations.router, prefix="/api/v1")
    return app


app = create_app()
