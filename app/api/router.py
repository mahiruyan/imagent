from __future__ import annotations

from fastapi import APIRouter

from app.api import auth, companies, exports, health, query_catalog, scans

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(companies.router)
api_router.include_router(scans.router)
api_router.include_router(exports.router)
api_router.include_router(query_catalog.router)
