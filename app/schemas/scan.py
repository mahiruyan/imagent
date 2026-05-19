from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ScanCreateRequest(BaseModel):
    provider: str = "google"
    city: str | None = None
    category: str | None = None
    query_catalog_ids: list[uuid.UUID] = Field(default_factory=list)
    query_texts: list[str] = Field(default_factory=list)


class ScanBatchResponse(BaseModel):
    id: uuid.UUID
    provider: str
    trigger_type: str
    city: str | None
    category: str | None
    status: str
    total_jobs: int
    done_jobs: int
    error_jobs: int
    companies_found: int
    companies_created: int
    companies_updated: int
    companies_deduped: int
    created_at: datetime

    model_config = {"from_attributes": True}
