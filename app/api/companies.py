from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models.company import Company
from app.schemas.company import CompanyListItem, CompanyUpdate
from app.services.audit import record_audit_event
from app.services.normalization import normalize_name, normalize_phone, normalize_website

router = APIRouter(prefix="/api/companies", tags=["companies"])


@router.get("", response_model=list[CompanyListItem])
async def list_companies(
    session: DbSession,
    current_user: CurrentUser,
    city: str | None = None,
    status: str | None = None,
    q: str | None = None,
    limit: int = Query(default=100, le=500),
) -> list[Company]:
    stmt = select(Company).order_by(Company.created_at.desc()).limit(limit)
    if city:
        stmt = stmt.where(Company.city == city)
    if status:
        stmt = stmt.where(Company.status == status)
    if q:
        stmt = stmt.where(Company.normalized_name.contains(normalize_name(q)))
    return list(await session.scalars(stmt))


@router.get("/map")
async def company_map_markers(
    session: DbSession,
    current_user: CurrentUser,
    city: str | None = None,
) -> list[dict]:
    stmt = select(Company).where(Company.lat.is_not(None), Company.lng.is_not(None)).limit(1000)
    if city:
        stmt = stmt.where(Company.city == city)
    companies = await session.scalars(stmt)
    return [
        {
            "id": str(company.id),
            "name": company.canonical_name,
            "lat": company.lat,
            "lng": company.lng,
            "status": company.status,
        }
        for company in companies
    ]


@router.patch("/{company_id}", response_model=CompanyListItem)
async def update_company(
    company_id: uuid.UUID,
    payload: CompanyUpdate,
    session: DbSession,
    request: Request,
    current_user: CurrentUser,
) -> Company:
    company = await session.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(company, key, value)

    if "canonical_name" in updates and company.canonical_name:
        company.normalized_name = normalize_name(company.canonical_name)
    if "phone" in updates:
        company.normalized_phone = normalize_phone(company.phone)
    if "website" in updates and company.website:
        company.website = normalize_website(company.website)
    company.updated_by = current_user.id

    await record_audit_event(
        session,
        action="company.update",
        request=request,
        actor_id=current_user.id,
        entity_type="company",
        entity_id=company.id,
        metadata={"fields": sorted(updates.keys())},
    )
    await session.commit()
    await session.refresh(company)
    return company
