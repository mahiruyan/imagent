from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class CompanyListItem(BaseModel):
    id: uuid.UUID
    supplier_code: str | None
    canonical_name: str
    city: str | None
    district: str | None
    osb: str | None
    phone: str | None
    website: str | None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CompanyUpdate(BaseModel):
    canonical_name: str | None = None
    canonical_address: str | None = None
    city: str | None = None
    district: str | None = None
    osb: str | None = None
    phone: str | None = None
    website: str | None = None
    email: str | None = None
    status: str | None = None
    notes: str | None = None

