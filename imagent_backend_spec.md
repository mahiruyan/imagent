# imagent - Backend Implementation Spec v1

## 1. Purpose

imagent is an internal supplier discovery and enrichment tool. It scans commercial businesses from map providers, deduplicates them, stores them in PostgreSQL, lets operators review/filter them, and exports supplier lists to Excel.

This document is the backend implementation reference. It turns the planning PDF into code-level decisions.

## 2. Core Decisions

| Area | Decision |
| --- | --- |
| Primary map provider | Yandex Maps |
| Yandex APIs | JavaScript API for map UI, Places/Organization HTTP API for backend search |
| Future provider support | Google Maps-compatible provider abstraction |
| Data store | PostgreSQL |
| Deployment | Existing Hetzner server |
| UI | FastAPI + Jinja2 + HTMX/Vanilla JS |
| Export | Excel via openpyxl |
| Auth | Internal login/session, no OAuth |
| Monitoring | Logs + lightweight admin views, no Sentry for MVP |
| Data resale | No. Internal business development tool only |

## 3. Scope

### MVP includes

- Operator login.
- Query catalog by city, district/OSB, category, and keyword.
- Manual scan batch creation.
- Yandex organization search provider.
- Provider-agnostic normalized candidate format.
- Deduplication before insert.
- PostgreSQL persistence.
- Company list, filter, map JSON feed, and detail view.
- Operator notes/status/category edits.
- Export latest scan, selected companies, or full supplier pool to Excel.
- Basic audit trail.
- Hetzner deployment with Docker Compose.

### MVP excludes

- Public SaaS/multi-tenant mode.
- OAuth.
- Sentry.
- Automated email outreach.
- Complex CRM pipeline.
- Heavy LLM workflow. Simple local classification can come later.

## 4. Architecture

```text
Browser
  |
  | HTTP
  v
FastAPI app
  |-- auth/session
  |-- pages and API routes
  |-- scan orchestration
  |-- company review/edit
  |-- Excel export
  |
  | writes jobs
  v
PostgreSQL
  ^
  | pulls pending jobs
  |
Scan worker
  |-- MapProvider interface
  |-- YandexMapsProvider
  |-- GoogleMapsProvider later
  |-- dedupe service
  |-- enrichment service later
```

## 5. Provider Abstraction

All provider-specific logic must stay behind a provider interface. The rest of the app should never depend directly on Yandex response shapes.

### Provider interface

```python
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

    async def get_organization_details(
        self,
        provider_entity_id: str,
    ) -> CompanyCandidate:
        ...
```

### Normalized candidate

```python
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
    categories: list[str] = []
    rating: float | None = None
    review_count: int | None = None
    raw_payload: dict
```

### Google compatibility rule

Yandex IDs, Google `place_id`, and future provider IDs must not be stored as the main company ID. They belong in `company_sources`.

The canonical company record is provider-independent. Multiple provider records can point to the same company.

## 6. Data Model

Use UUID primary keys internally. Use `supplier_code` only as an external display/export identifier.

### users

Internal operators.

| Column | Type | Notes |
| --- | --- | --- |
| id | UUID PK | |
| username | TEXT UNIQUE NOT NULL | |
| password_hash | TEXT NOT NULL | |
| role | TEXT NOT NULL | `admin`, `operator` |
| is_active | BOOLEAN NOT NULL DEFAULT TRUE | |
| created_at | TIMESTAMPTZ NOT NULL | |
| updated_at | TIMESTAMPTZ NOT NULL | |

### companies

Canonical supplier records.

| Column | Type | Notes |
| --- | --- | --- |
| id | UUID PK | |
| supplier_code | TEXT UNIQUE | Example: `SUP-00052` |
| canonical_name | TEXT NOT NULL | Display name |
| normalized_name | TEXT NOT NULL | Dedupe/search |
| canonical_address | TEXT | Display address |
| city | TEXT | |
| district | TEXT | |
| osb | TEXT | Optional industrial zone |
| lat | DOUBLE PRECISION | |
| lng | DOUBLE PRECISION | |
| phone | TEXT | Display phone |
| normalized_phone | TEXT | Dedupe/search |
| website | TEXT | |
| email | TEXT | Usually enrichment/scrape, not maps |
| rating | NUMERIC(2,1) | Optional provider value |
| review_count | INT | Optional provider value |
| business_status | TEXT | Optional provider value |
| status | TEXT NOT NULL | `new`, `reviewed`, `selected`, `exported`, `contacted`, `rejected`, `duplicate`, `archived` |
| quality_score | NUMERIC(5,2) | Internal ranking |
| notes | TEXT | Operator notes |
| created_by | UUID FK users.id | |
| updated_by | UUID FK users.id | |
| created_at | TIMESTAMPTZ NOT NULL | |
| updated_at | TIMESTAMPTZ NOT NULL | |

Recommended indexes:

- `companies(normalized_name)`
- `companies(normalized_phone)`
- `companies(city, district)`
- `companies(status)`
- `companies(lat, lng)` or PostGIS geography later

### company_sources

Provider-specific source records.

| Column | Type | Notes |
| --- | --- | --- |
| id | UUID PK | |
| company_id | UUID FK companies.id | |
| provider | TEXT NOT NULL | `yandex`, `google`, `manual`, `scrape` |
| provider_entity_id | TEXT | Yandex org id/uri or Google place_id |
| provider_url | TEXT | Source URL if available |
| source_name | TEXT | Name as returned by provider |
| source_address | TEXT | Address as returned by provider |
| raw_payload | JSONB NOT NULL | Original response for debugging |
| confidence | NUMERIC(5,2) | Match confidence |
| first_seen_at | TIMESTAMPTZ NOT NULL | |
| last_seen_at | TIMESTAMPTZ NOT NULL | |
| created_at | TIMESTAMPTZ NOT NULL | |
| updated_at | TIMESTAMPTZ NOT NULL | |

Constraints:

- `UNIQUE(provider, provider_entity_id)` when `provider_entity_id IS NOT NULL`
- `UNIQUE(company_id, provider, provider_entity_id)` when `provider_entity_id IS NOT NULL`

### company_categories

A company can belong to more than one category.

| Column | Type | Notes |
| --- | --- | --- |
| id | UUID PK | |
| company_id | UUID FK companies.id | |
| category | TEXT NOT NULL | `cnc`, `3d_printing`, `plastic_injection`, `sheet_laser`, etc. |
| source | TEXT NOT NULL | `query`, `operator`, `provider`, `llm` |
| confidence | NUMERIC(5,2) | |
| created_at | TIMESTAMPTZ NOT NULL | |

Constraint:

- `UNIQUE(company_id, category, source)`

### query_catalog

Reusable query definitions.

| Column | Type | Notes |
| --- | --- | --- |
| id | UUID PK | |
| city | TEXT NOT NULL | |
| district | TEXT | |
| osb | TEXT | |
| category | TEXT NOT NULL | |
| keyword | TEXT NOT NULL | Example: `CNC torna`, `plastic injection` |
| query_text | TEXT NOT NULL | Final provider query |
| language | TEXT | `tr`, `en`, `mixed` |
| is_active | BOOLEAN NOT NULL DEFAULT TRUE | |
| priority | INT NOT NULL DEFAULT 100 | Lower runs first |
| created_at | TIMESTAMPTZ NOT NULL | |
| updated_at | TIMESTAMPTZ NOT NULL | |

### scan_batches

A batch groups many provider search jobs.

| Column | Type | Notes |
| --- | --- | --- |
| id | UUID PK | |
| provider | TEXT NOT NULL | `yandex` initially |
| trigger_type | TEXT NOT NULL | `manual`, `scheduled` |
| city | TEXT | |
| category | TEXT | |
| status | TEXT NOT NULL | `pending`, `running`, `done`, `error`, `cancelled` |
| total_jobs | INT NOT NULL DEFAULT 0 | |
| done_jobs | INT NOT NULL DEFAULT 0 | |
| error_jobs | INT NOT NULL DEFAULT 0 | |
| companies_found | INT NOT NULL DEFAULT 0 | Raw candidates |
| companies_created | INT NOT NULL DEFAULT 0 | New canonical records |
| companies_updated | INT NOT NULL DEFAULT 0 | Existing records touched |
| companies_deduped | INT NOT NULL DEFAULT 0 | Existing records matched |
| created_by | UUID FK users.id | Null for scheduled |
| started_at | TIMESTAMPTZ | |
| finished_at | TIMESTAMPTZ | |
| duration_ms | INT | |
| created_at | TIMESTAMPTZ NOT NULL | |
| updated_at | TIMESTAMPTZ NOT NULL | |

### scan_jobs

One provider query or details fetch.

| Column | Type | Notes |
| --- | --- | --- |
| id | UUID PK | |
| batch_id | UUID FK scan_batches.id | |
| provider | TEXT NOT NULL | |
| type | TEXT NOT NULL | `organization_search`, `details_fetch`, `enrichment` |
| query_text | TEXT | |
| payload | JSONB NOT NULL | Provider params |
| status | TEXT NOT NULL | `pending`, `running`, `done`, `error`, `cancelled` |
| attempt_count | INT NOT NULL DEFAULT 0 | |
| max_attempts | INT NOT NULL DEFAULT 3 | |
| error_message | TEXT | |
| locked_by | TEXT | Worker instance id |
| locked_at | TIMESTAMPTZ | |
| started_at | TIMESTAMPTZ | |
| finished_at | TIMESTAMPTZ | |
| duration_ms | INT | |
| created_at | TIMESTAMPTZ NOT NULL | |
| updated_at | TIMESTAMPTZ NOT NULL | |

Indexes:

- `scan_jobs(status, created_at)`
- `scan_jobs(batch_id)`

Worker pickup should use `FOR UPDATE SKIP LOCKED`.

### scan_results

Links a batch/job to canonical companies.

| Column | Type | Notes |
| --- | --- | --- |
| id | UUID PK | |
| batch_id | UUID FK scan_batches.id | |
| job_id | UUID FK scan_jobs.id | |
| company_id | UUID FK companies.id | |
| company_source_id | UUID FK company_sources.id | |
| result_type | TEXT NOT NULL | `created`, `updated`, `deduped`, `ignored` |
| match_reason | TEXT | `provider_id`, `phone`, `name_address`, `manual` |
| score | NUMERIC(5,2) | |
| created_at | TIMESTAMPTZ NOT NULL | |

### export_batches

Tracks Excel exports.

| Column | Type | Notes |
| --- | --- | --- |
| id | UUID PK | |
| export_type | TEXT NOT NULL | `latest_scan`, `selected`, `all`, `filtered` |
| source_batch_id | UUID FK scan_batches.id | Nullable |
| filters | JSONB NOT NULL DEFAULT '{}' | |
| file_name | TEXT NOT NULL | |
| row_count | INT NOT NULL | |
| created_by | UUID FK users.id | |
| created_at | TIMESTAMPTZ NOT NULL | |

### export_items

| Column | Type | Notes |
| --- | --- | --- |
| id | UUID PK | |
| export_batch_id | UUID FK export_batches.id | |
| company_id | UUID FK companies.id | |
| row_number | INT NOT NULL | |
| created_at | TIMESTAMPTZ NOT NULL | |

Constraint:

- `UNIQUE(export_batch_id, company_id)`

### audit_events

IP and user agent should be stored here instead of duplicating them across every table.

| Column | Type | Notes |
| --- | --- | --- |
| id | UUID PK | |
| actor_id | UUID FK users.id | Nullable for system |
| action | TEXT NOT NULL | `login`, `scan.create`, `company.update`, `export.create`, etc. |
| entity_type | TEXT | |
| entity_id | UUID | |
| ip_address | INET | |
| user_agent | TEXT | |
| metadata | JSONB NOT NULL DEFAULT '{}' | |
| created_at | TIMESTAMPTZ NOT NULL | |

## 7. Deduplication

Deduplication runs before inserting a new company.

### Matching order

1. Exact provider match: `company_sources(provider, provider_entity_id)`.
2. Exact normalized phone match.
3. Strong normalized name + same city/district.
4. Strong normalized name + close coordinates.
5. Manual review queue if confidence is medium.

### Dedupe service output

```python
class DedupeDecision(BaseModel):
    action: Literal["create", "update_existing", "needs_review", "ignore"]
    company_id: UUID | None
    confidence: float
    reason: str
```

### Normalization rules

- Lowercase.
- Turkish character normalization for matching only.
- Remove company suffix noise: `ltd`, `şti`, `san`, `tic`, `a.ş`, `limited`, `anonim`.
- Normalize phone to E.164-like Turkish format when possible.
- Normalize website domain by stripping protocol, `www`, tracking params, and trailing slash.

## 8. Job System

### Manual scan flow

1. Operator selects city/category/query set.
2. Backend creates `scan_batches`.
3. Backend creates one `scan_jobs` row per query.
4. Worker pulls pending jobs.
5. Provider returns candidates.
6. Candidates are normalized.
7. Dedupe service creates/updates/skips companies.
8. `scan_results` records batch membership.
9. Batch counters update.
10. UI shows latest batch summary.

### Scheduled scan flow

Same as manual scan, but `trigger_type = scheduled` and `created_by = NULL`.

Recommended MVP schedules:

- Weekly full scan per target city/category.
- Optional daily scan for priority query sets.

### Retry rules

- Retry transient provider/network errors up to 3 times.
- Do not retry validation errors.
- Mark job `error` with `error_message`.
- Always record `duration_ms`.

## 9. Export Logic

There are three first-class export modes.

### Latest scan export

Exports only companies discovered or matched in a selected `scan_batch`.

Input:

- `batch_id`

### Selected export

Exports manually selected companies from current filters. Selection must not be a global boolean on `companies`; it should be request/filter driven or represented through a saved export.

Input:

- `company_ids`

### Full supplier pool export

Exports all active companies.

Input:

- optional filters: city, category, status, min_rating, has_phone, has_website.

### Excel columns

Initial columns:

- Supplier ID
- Company Name
- City
- District / OSB
- Category
- Address
- Website
- Phone
- Email
- Rating
- Review Count
- Source Providers
- Notes
- Status
- Added Date

## 10. API and Pages

### Pages

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/login` | Login page |
| POST | `/login` | Create session |
| POST | `/logout` | End session |
| GET | `/` | Dashboard |
| GET | `/companies` | Main list/map page |
| GET | `/companies/{id}` | Detail page |
| GET | `/scans` | Scan history |
| GET | `/scans/{id}` | Scan batch detail |
| GET | `/exports` | Export history |

### API endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/companies` | Filtered list JSON |
| GET | `/api/companies/map` | Marker JSON |
| PATCH | `/api/companies/{id}` | Update notes/status/category/basic fields |
| POST | `/api/scans` | Create scan batch |
| GET | `/api/scans/{id}` | Scan status |
| POST | `/api/exports` | Create Excel export |
| GET | `/api/exports/{id}/download` | Download Excel |
| GET | `/api/query-catalog` | Query catalog list |
| POST | `/api/query-catalog` | Create query |
| PATCH | `/api/query-catalog/{id}` | Update query |

## 11. Security

MVP security is simple but explicit.

- Session cookie auth.
- Passwords stored with strong hash.
- CSRF protection on POST/PATCH/DELETE.
- Rate limiting on login and write endpoints.
- Audit event for login, scan creation, company update, and export.
- Environment variables for secrets.
- Provider API keys are split by runtime.
- `YANDEX_JS_API_KEY` is used only by browser-rendered map pages.
- `YANDEX_PLACES_API_KEY` is used only by backend search/provider calls.
- Backend keys must never be rendered into templates or sent to the browser.
- If a frontend map key is needed, restrict it by domain/referrer where supported.

## 12. Deployment on Hetzner

### Runtime

- Docker Compose.
- App container: FastAPI.
- Worker container: same image, worker command.
- PostgreSQL: existing server/database.
- Reverse proxy: Caddy or Nginx.
- TLS: existing proxy certificate or Let's Encrypt.

### Services

```yaml
services:
  web:
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000
  worker:
    command: python -m app.workers.scan_worker
```

### Required env vars

```text
DATABASE_URL=
SECRET_KEY=
ENVIRONMENT=production
LOG_LEVEL=INFO
YANDEX_JS_API_KEY=
YANDEX_PLACES_API_KEY=
MAP_PROVIDER=yandex
EXPORT_TEMPLATE_PATH=
```

Future:

```text
GOOGLE_MAPS_API_KEY=
GOOGLE_MAPS_BACKEND_KEY=
```

### Operations

- Daily Postgres backup.
- Log rotation.
- Health endpoint: `/healthz`.
- Admin-only job status page.
- Deployment script or Makefile target.

## 13. Enrichment Roadmap

MVP can store fields from Yandex and operator edits. Later enrichment can add:

- Website scraping.
- Email extraction.
- Sector/capability detection.
- Certificate detection.
- Company scale estimation.
- Local Ollama classification.

These should be separate `enrichment_jobs`, not mixed into map scan jobs.

## 14. Implementation Order

1. Project scaffold.
2. Config, database connection, Alembic.
3. Models and migrations.
4. Auth/session.
5. Provider interface and Yandex provider.
6. Query catalog.
7. Scan batch/job creation.
8. Worker and dedupe.
9. Company list/detail APIs.
10. Jinja/HTMX pages.
11. Excel export.
12. Audit events.
13. Hetzner Docker Compose.

## 15. Open Technical Questions

- Exact Yandex organization identifier field to use as `provider_entity_id`.
- Whether Yandex details call is needed after search or search response is enough.
- Excel master template file path and exact column mapping.
- Initial query catalog contents for each city/OSB/category.
- Whether PostGIS is already enabled in the existing PostgreSQL database.
- Whether scheduled jobs should run inside the worker loop or via host cron.
