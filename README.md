# imagent Backend

Internal supplier discovery backend. Primary map provider is Yandex Maps, with a provider interface that keeps a later Google Maps migration contained.

## Local Setup

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
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

Smoke-test Yandex provider:

```bash
python scripts/smoke_yandex_provider.py --query "CNC" --city "Izmir" --limit 5
```

Run the worker in a second terminal:

```bash
python -m app.workers.scan_worker
```

Do not commit real API keys. Use `.env`.

## Hetzner

Production setup lives in [infra/hetzner/README.md](infra/hetzner/README.md).

GitHub-based deployment lives in [infra/hetzner/GITHUB_DEPLOY.md](infra/hetzner/GITHUB_DEPLOY.md).
