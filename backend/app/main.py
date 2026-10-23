import logging

from fastapi import FastAPI

from app.api.routes import auth, health
from app.core.config import get_settings
from app.core.errors import register_error_handlers

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Daleel API",
        version="0.1.0",
        description="Ask questions about Arabic and English documents and get cited answers.",
        # Hide interactive docs in production; keep them for local development.
        docs_url=None if settings.is_production else "/api/docs",
        openapi_url="/api/openapi.json",
    )
    register_error_handlers(app)
    app.include_router(health.router, prefix="/api")
    app.include_router(auth.router, prefix="/api/v1")
    return app


app = create_app()
