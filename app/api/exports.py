from __future__ import annotations

from io import BytesIO

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models.company import Company
from app.models.export import ExportBatch, ExportItem
from app.models.scan import ScanResult
from app.schemas.export import ExportRequest
from app.services.audit import record_audit_event
from app.services.export_service import ExportService

router = APIRouter(prefix="/api/exports", tags=["exports"])


@router.post("")
async def export_companies(
    payload: ExportRequest,
    session: DbSession,
    request: Request,
    current_user: CurrentUser,
) -> StreamingResponse:
    companies = await _load_companies_for_export(session, payload)
    service = ExportService()
    content = service.build_workbook_bytes(companies)

    file_name = f"imagent_suppliers_{payload.export_type}.xlsx"
    export_batch = ExportBatch(
        export_type=payload.export_type,
        source_batch_id=payload.source_batch_id,
        filters=payload.filters,
        file_name=file_name,
        row_count=len(companies),
        created_by=current_user.id,
    )
    session.add(export_batch)
    await session.flush()

    for index, company in enumerate(companies, start=2):
        session.add(
            ExportItem(export_batch_id=export_batch.id, company_id=company.id, row_number=index)
        )

    await record_audit_event(
        session,
        action="export.create",
        request=request,
        actor_id=current_user.id,
        entity_type="export_batch",
        entity_id=export_batch.id,
        metadata={"export_type": payload.export_type, "row_count": len(companies)},
    )
    await session.commit()

    headers = {"Content-Disposition": f'attachment; filename="{file_name}"'}
    return StreamingResponse(
        BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


async def _load_companies_for_export(session: DbSession, payload: ExportRequest) -> list[Company]:
    if payload.export_type == "latest_scan":
        if not payload.source_batch_id:
            raise HTTPException(status_code=400, detail="source_batch_id is required")
        company_ids = select(ScanResult.company_id).where(ScanResult.batch_id == payload.source_batch_id)
        rows = await session.scalars(select(Company).where(Company.id.in_(company_ids)))
        return list(rows)

    if payload.export_type == "selected":
        if not payload.company_ids:
            raise HTTPException(status_code=400, detail="company_ids are required")
        rows = await session.scalars(select(Company).where(Company.id.in_(payload.company_ids)))
        return list(rows)

    stmt = select(Company).where(Company.status != "archived").order_by(Company.created_at.desc())
    if city := payload.filters.get("city"):
        stmt = stmt.where(Company.city == city)
    if status := payload.filters.get("status"):
        stmt = stmt.where(Company.status == status)
    rows = await session.scalars(stmt)
    return list(rows)
