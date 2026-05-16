from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field


class ExportRequest(BaseModel):
    export_type: Literal["latest_scan", "selected", "all", "filtered"]
    source_batch_id: uuid.UUID | None = None
    company_ids: list[uuid.UUID] = Field(default_factory=list)
    filters: dict = Field(default_factory=dict)

