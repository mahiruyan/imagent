from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models.scan import ScanBatch
from app.schemas.scan import ScanBatchResponse, ScanCreateRequest
from app.services.audit import record_audit_event
from app.services.scan_service import ScanService

router = APIRouter(prefix="/api/scans", tags=["scans"])


@router.post("", response_model=ScanBatchResponse)
async def create_scan(
    payload: ScanCreateRequest,
    session: DbSession,
    request: Request,
    current_user: CurrentUser,
) -> ScanBatch:
    service = ScanService(session)
    try:
        batch = await service.create_batch(payload, created_by=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    await record_audit_event(
        session,
        action="scan.create",
        request=request,
        actor_id=current_user.id,
        entity_type="scan_batch",
        entity_id=batch.id,
        metadata=payload.model_dump(mode="json"),
    )
    await session.commit()
    await session.refresh(batch)
    return batch


@router.get("", response_model=list[ScanBatchResponse])
async def list_scans(session: DbSession, current_user: CurrentUser) -> list[ScanBatch]:
    rows = await session.scalars(select(ScanBatch).order_by(ScanBatch.created_at.desc()).limit(100))
    return list(rows)


@router.get("/{batch_id}", response_model=ScanBatchResponse)
async def get_scan(batch_id: uuid.UUID, session: DbSession, current_user: CurrentUser) -> ScanBatch:
    batch = await session.get(ScanBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Scan batch not found")
    return batch
