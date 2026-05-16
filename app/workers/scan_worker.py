from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.company import Company, CompanyCategory, CompanySource
from app.models.scan import ScanBatch, ScanJob, ScanResult
from app.providers.factory import get_map_provider
from app.schemas.provider import CompanyCandidate
from app.services.dedupe import DedupeDecision, DedupeService
from app.services.normalization import normalize_name, normalize_phone, normalize_website

WORKER_ID = os.getenv("WORKER_ID", f"scan-worker-{os.getpid()}")
POLL_SECONDS = float(os.getenv("SCAN_WORKER_POLL_SECONDS", "2"))


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def duration_ms(start: datetime, end: datetime) -> int:
    return int((end - start).total_seconds() * 1000)


async def main() -> None:
    while True:
        processed = await process_one_job()
        if not processed:
            await asyncio.sleep(POLL_SECONDS)


async def process_one_job() -> bool:
    async with AsyncSessionLocal() as session:
        job = await session.scalar(
            select(ScanJob)
            .where(ScanJob.status == "pending")
            .order_by(ScanJob.created_at.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if not job:
            return False

        now = utcnow()
        job.status = "running"
        job.locked_by = WORKER_ID
        job.locked_at = now
        job.started_at = now
        job.attempt_count += 1

        batch = await session.get(ScanBatch, job.batch_id)
        if batch and batch.status == "pending":
            batch.status = "running"
            batch.started_at = now

        await session.commit()

    async with AsyncSessionLocal() as session:
        job = await session.get(ScanJob, job.id)
        if not job:
            return True

        start = job.started_at or utcnow()
        try:
            provider = get_map_provider(job.provider)
            candidates = await provider.search_organizations(
                query=job.payload["query"],
                city=job.payload.get("city"),
            )
            stats = await persist_candidates(session, job, candidates)
            finished = utcnow()
            job.status = "done"
            job.finished_at = finished
            job.duration_ms = duration_ms(start, finished)
            await update_batch_after_job(
                session,
                job,
                found_count=len(candidates),
                created_count=stats["created"],
                deduped_count=stats["deduped"],
                error=False,
            )
        except Exception as exc:
            finished = utcnow()
            job.status = "error" if job.attempt_count >= job.max_attempts else "pending"
            job.error_message = str(exc)
            job.finished_at = finished
            job.duration_ms = duration_ms(start, finished)
            await update_batch_after_job(
                session,
                job,
                found_count=0,
                created_count=0,
                deduped_count=0,
                error=True,
            )
        await session.commit()

    return True


async def persist_candidates(
    session,
    job: ScanJob,
    candidates: list[CompanyCandidate],
) -> dict[str, int]:
    dedupe = DedupeService(session)
    stats = {"created": 0, "deduped": 0}
    for candidate in candidates:
        decision = await dedupe.decide(candidate)
        company, source, result_type = await apply_dedupe_decision(session, candidate, decision)
        if result_type == "created":
            stats["created"] += 1
        elif result_type == "deduped":
            stats["deduped"] += 1

        session.add(
            ScanResult(
                batch_id=job.batch_id,
                job_id=job.id,
                company_id=company.id,
                company_source_id=source.id if source else None,
                result_type=result_type,
                match_reason=decision.reason,
                score=decision.confidence,
            )
        )

        category = job.payload.get("category")
        if category:
            await ensure_company_category(session, company.id, category)
    return stats


async def apply_dedupe_decision(
    session,
    candidate: CompanyCandidate,
    decision: DedupeDecision,
) -> tuple[Company, CompanySource | None, str]:
    if decision.action == "create":
        company = Company(
            canonical_name=candidate.name,
            normalized_name=candidate.normalized_name,
            canonical_address=candidate.address,
            city=candidate.city,
            district=candidate.district,
            osb=candidate.osb,
            lat=candidate.lat,
            lng=candidate.lng,
            phone=candidate.phone,
            normalized_phone=candidate.normalized_phone,
            website=normalize_website(candidate.website),
            rating=candidate.rating,
            review_count=candidate.review_count,
            status="new",
        )
        session.add(company)
        await session.flush()
        source = create_company_source(company.id, candidate, confidence=decision.confidence)
        session.add(source)
        await session.flush()
        return company, source, "created"

    company = await session.get(Company, decision.company_id)
    if not company:
        raise RuntimeError("Dedupe matched a missing company")

    merge_candidate_into_company(company, candidate)
    source = await ensure_company_source(session, company.id, candidate, confidence=decision.confidence)
    return company, source, "deduped"


def create_company_source(
    company_id,
    candidate: CompanyCandidate,
    *,
    confidence: float,
) -> CompanySource:
    return CompanySource(
        company_id=company_id,
        provider=candidate.source_provider,
        provider_entity_id=candidate.source_id,
        provider_url=candidate.source_url,
        source_name=candidate.name,
        source_address=candidate.address,
        raw_payload=candidate.raw_payload,
        confidence=confidence,
    )


async def ensure_company_source(
    session,
    company_id,
    candidate: CompanyCandidate,
    *,
    confidence: float,
) -> CompanySource | None:
    if not candidate.source_id:
        return None
    source = await session.scalar(
        select(CompanySource).where(
            CompanySource.provider == candidate.source_provider,
            CompanySource.provider_entity_id == candidate.source_id,
        )
    )
    if source:
        source.last_seen_at = utcnow()
        source.raw_payload = candidate.raw_payload
        return source
    source = create_company_source(company_id, candidate, confidence=confidence)
    session.add(source)
    await session.flush()
    return source


async def ensure_company_category(session, company_id, category: str) -> CompanyCategory:
    existing = await session.scalar(
        select(CompanyCategory).where(
            CompanyCategory.company_id == company_id,
            CompanyCategory.category == category,
            CompanyCategory.source == "query",
        )
    )
    if existing:
        return existing
    row = CompanyCategory(
        company_id=company_id,
        category=category,
        source="query",
        confidence=1.0,
    )
    session.add(row)
    await session.flush()
    return row


def merge_candidate_into_company(company: Company, candidate: CompanyCandidate) -> None:
    company.canonical_name = company.canonical_name or candidate.name
    company.normalized_name = company.normalized_name or normalize_name(candidate.name)
    company.canonical_address = company.canonical_address or candidate.address
    company.city = company.city or candidate.city
    company.district = company.district or candidate.district
    company.osb = company.osb or candidate.osb
    company.lat = company.lat or candidate.lat
    company.lng = company.lng or candidate.lng
    company.phone = company.phone or candidate.phone
    company.normalized_phone = company.normalized_phone or normalize_phone(candidate.phone)
    company.website = company.website or normalize_website(candidate.website)
    company.rating = company.rating or candidate.rating
    company.review_count = company.review_count or candidate.review_count


async def update_batch_after_job(
    session,
    job: ScanJob,
    *,
    found_count: int,
    created_count: int,
    deduped_count: int,
    error: bool,
) -> None:
    batch = await session.get(ScanBatch, job.batch_id)
    if not batch:
        return
    if error and job.status == "error":
        batch.error_jobs += 1
    elif not error:
        batch.done_jobs += 1
        batch.companies_found += found_count
        batch.companies_created += created_count
        batch.companies_deduped += deduped_count

    if batch.done_jobs + batch.error_jobs >= batch.total_jobs:
        batch.status = "error" if batch.error_jobs else "done"
        batch.finished_at = utcnow()
        if batch.started_at:
            batch.duration_ms = duration_ms(batch.started_at, batch.finished_at)


if __name__ == "__main__":
    asyncio.run(main())
