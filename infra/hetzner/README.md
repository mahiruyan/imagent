# Hetzner Deployment

This setup runs PostgreSQL, the FastAPI web service, and the scan worker on the Hetzner server with Docker Compose.

## 1. Server packages

On a fresh Ubuntu server:

```bash
sudo apt update
sudo apt install -y ca-certificates curl git
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo tee /etc/apt/keyrings/docker.asc >/dev/null
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo ${UBUNTU_CODENAME:-$VERSION_CODENAME}) stable" | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER
```

Log out and back in after adding the Docker group.

## 2. Project setup

Clone/copy this project to the server, then:

```bash
cp .env.production.example .env.production
```

Edit `.env.production`:

```text
POSTGRES_PASSWORD=<strong-db-password>
DATABASE_URL=postgresql+asyncpg://imagent:<same-db-password>@db:5432/imagent
SECRET_KEY=<long-random-secret>
YANDEX_JS_API_KEY=<yandex-js-key>
YANDEX_PLACES_API_KEY=<yandex-places-key>
WEB_PORT=8000
```

Generate a secret:

```bash
openssl rand -hex 32
```

## 3. Start database

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production up -d db
```

## 4. Run migrations

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production run --rm web alembic upgrade head
```

## 5. Create admin

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production run --rm web \
  python scripts/create_admin.py --username admin --password '<admin-password>'
```

## 6. Seed query catalog

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production run --rm web \
  python scripts/seed_query_catalog.py
```

## 7. Start app and worker

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
```

Check health:

```bash
curl http://127.0.0.1:8000/healthz
```

## 8. Smoke-test Yandex provider

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production run --rm web \
  python scripts/smoke_yandex_provider.py --query "CNC" --city "Izmir" --limit 5
```

## 9. Backups

Run from project root on the server:

```bash
bash scripts/backup_postgres.sh
```

Recommended cron:

```cron
15 3 * * * cd /opt/imagent && bash scripts/backup_postgres.sh
```
