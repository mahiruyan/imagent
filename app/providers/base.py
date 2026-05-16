from __future__ import annotations

from typing import Protocol

from app.schemas.provider import CompanyCandidate, GeoBounds


class MapProvider(Protocol):
    provider_name: str

    async def search_organizations(
        self,
        query: str,
        city: str | None = None,
        bounds: GeoBounds | None = None,
        limit: int = 50,
    ) -> list[CompanyCandidate]:
        ...

    async def get_organization_details(self, provider_entity_id: str) -> CompanyCandidate:
        ...

