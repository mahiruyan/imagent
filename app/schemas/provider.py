from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class GeoBounds(BaseModel):
    north: float
    east: float
    south: float
    west: float


class CompanyCandidate(BaseModel):
    source_provider: Literal["yandex", "google", "manual", "scrape"]
    source_id: str | None
    source_url: str | None = None
    name: str
    normalized_name: str
    address: str | None = None
    city: str | None = None
    district: str | None = None
    osb: str | None = None
    lat: float | None = None
    lng: float | None = None
    phone: str | None = None
    normalized_phone: str | None = None
    website: str | None = None
    categories: list[str] = Field(default_factory=list)
    rating: float | None = None
    review_count: int | None = None
    raw_payload: dict

