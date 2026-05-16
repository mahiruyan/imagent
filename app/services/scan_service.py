from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.query_catalog import QueryCatalog
from app.models.scan import ScanBatch, ScanJob
from app.schemas.scan import ScanCreateRequest


class ScanService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_batch(
        self,
        payload: ScanCreateRequest,
        *,
        created_by: uuid.UUID | None = None,
        trigger_type: str = "manual",
    ) -> ScanBatch:
        query_texts = list(payload.query_texts)

        if payload.query_catalog_ids:
            rows = await self.session.scalars(
                select(QueryCatalog)
                .where(QueryCatalog.id.in_(payload.query_catalog_ids))
                .order_by(QueryCatalog.priority.asc())
            )
            query_texts.extend(row.query_text for row in rows)

        if not query_texts:
            raise ValueError("At least one query text or query catalog id is required")

        batch = ScanBatch(
            provider=payload.provider,
            trigger_type=trigger_type,
            city=payload.city,
            category=payload.category,
            status="pending",
            total_jobs=len(query_texts),
            created_by=created_by,
        )
        self.session.add(batch)
        await self.session.flush()

        for query_text in query_texts:
            self.session.add(
                ScanJob(
                    batch_id=batch.id,
                    provider=payload.provider,
                    type="organization_search",
                    query_text=query_text,
                    payload={
                        "query": query_text,
                        "city": payload.city,
                        "category": payload.category,
                    },
                    status="pending",
                )
            )

        await self.session.flush()
        return batch

