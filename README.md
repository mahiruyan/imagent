# imagent Backend

Internal supplier discovery backend. Primary map provider is Google Maps, with Yandex kept behind the same provider interface as a fallback.

## Local Setup

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
```

Docker-based local preview:

```bash
cp .env.example .env
docker compose up -d db
docker compose run --rm web alembic upgrade head
docker compose run --rm web python scripts/create_admin.py --username admin --password change-me
docker compose up -d --build web worker
```

Create the first admin after migrations:

```bash
python scripts/create_admin.py --username admin --password 'change-me'
```

Validate environment and database connectivity:

```bash
python scripts/check_setup.py
```

Seed starter search queries:

```bash
python scripts/seed_query_catalog.py
```

Smoke-test Google provider:

```bash
python scripts/smoke_google_provider.py --query "CNC" --city "Izmir" --limit 5
```

Run the worker in a second terminal:

```bash
python -m app.workers.scan_worker
```

Do not commit real API keys. Use `.env`.

## Hetzner

Production setup lives in [infra/hetzner/README.md](infra/hetzner/README.md).

GitHub-based deployment lives in [infra/hetzner/GITHUB_DEPLOY.md](infra/hetzner/GITHUB_DEPLOY.md).
