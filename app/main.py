from __future__ import annotations

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from app.api.router import api_router
from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(title="imagent", version="0.1.0")
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key,
        same_site="lax",
        https_only=settings.environment == "production",
    )
    app.include_router(api_router)

    @app.get("/")
    async def root() -> dict[str, str]:
        return {
            "service": "imagent",
            "environment": settings.environment,
            "map_provider": settings.map_provider,
        }

    return app


app = create_app()
