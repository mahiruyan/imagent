from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company, CompanySource
from app.schemas.provider import CompanyCandidate


@dataclass(frozen=True)
class DedupeDecision:
    action: Literal["create", "update_existing", "needs_review", "ignore"]
    company_id: uuid.UUID | None
    confidence: float
    reason: str


class DedupeService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def decide(self, candidate: CompanyCandidate) -> DedupeDecision:
        if candidate.source_id:
            existing_source = await self.session.scalar(
                select(CompanySource).where(
                    CompanySource.provider == candidate.source_provider,
                    CompanySource.provider_entity_id == candidate.source_id,
                )
            )
            if existing_source:
                return DedupeDecision(
                    action="update_existing",
                    company_id=existing_source.company_id,
                    confidence=1.0,
                    reason="provider_id",
                )

        if candidate.normalized_phone:
            company = await self.session.scalar(
                select(Company).where(Company.normalized_phone == candidate.normalized_phone)
            )
            if company:
                return DedupeDecision(
                    action="update_existing",
                    company_id=company.id,
                    confidence=0.95,
                    reason="phone",
                )

        if candidate.normalized_name:
            query = select(Company).where(Company.normalized_name == candidate.normalized_name)
            if candidate.city:
                query = query.where(Company.city == candidate.city)
            company = await self.session.scalar(query)
            if company:
                return DedupeDecision(
                    action="update_existing",
                    company_id=company.id,
                    confidence=0.82,
                    reason="name_city",
                )

        return DedupeDecision(action="create", company_id=None, confidence=1.0, reason="new")

