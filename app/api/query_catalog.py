from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models.query_catalog import QueryCatalog

router = APIRouter(prefix="/api/query-catalog", tags=["query-catalog"])


class QueryCatalogCreate(BaseModel):
    city: str
    district: str | None = None
    osb: str | None = None
    category: str
    keyword: str
    query_text: str
    language: str | None = None
    priority: int = 100


@router.get("")
async def list_query_catalog(session: DbSession, current_user: CurrentUser) -> list[dict]:
    rows = await session.scalars(
        select(QueryCatalog).where(QueryCatalog.is_active.is_(True)).order_by(QueryCatalog.priority.asc())
    )
    return [
        {
            "id": str(row.id),
            "city": row.city,
            "district": row.district,
            "osb": row.osb,
            "category": row.category,
            "keyword": row.keyword,
            "query_text": row.query_text,
            "language": row.language,
            "priority": row.priority,
        }
        for row in rows
    ]


@router.post("")
async def create_query_catalog(
    payload: QueryCatalogCreate,
    session: DbSession,
    current_user: CurrentUser,
) -> dict[str, str]:
    row = QueryCatalog(**payload.model_dump())
    session.add(row)
    await session.commit()
    return {"id": str(row.id)}


@router.patch("/{query_id}")
async def update_query_catalog(
    query_id: uuid.UUID,
    payload: QueryCatalogCreate,
    session: DbSession,
    current_user: CurrentUser,
) -> dict[str, str]:
    row = await session.get(QueryCatalog, query_id)
    if not row:
        raise HTTPException(status_code=404, detail="Query catalog row not found")
    for key, value in payload.model_dump().items():
        setattr(row, key, value)
    await session.commit()
    return {"id": str(row.id)}
