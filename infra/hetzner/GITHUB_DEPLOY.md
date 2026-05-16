# GitHub Deploy

This project should be pushed to GitHub without real `.env` files. Production secrets live in GitHub Actions Secrets and are written to `/opt/imagent/.env.production` during deployment.

## 1. Create GitHub repository

Create an empty repository named `imagent`.

From this local folder:

```bash
cd /Users/mahiruyan/imagent
git init
git add .
git commit -m "Initial imagent backend"
git branch -M main
git remote add origin git@github.com:<owner>/imagent.git
git push -u origin main
```

## 2. Add GitHub Actions secrets

In GitHub:

```text
Settings -> Secrets and variables -> Actions -> New repository secret
```

Required secrets:

```text
HETZNER_HOST
HETZNER_USER
HETZNER_SSH_KEY
POSTGRES_PASSWORD
SECRET_KEY
YANDEX_JS_API_KEY
YANDEX_PLACES_API_KEY
```

Generate `SECRET_KEY`:

```bash
openssl rand -hex 32
```

`HETZNER_SSH_KEY` must be a private key that can SSH into the server. Its public key must be in the server user's `~/.ssh/authorized_keys`.

## 3. Prepare Hetzner server once

Install Docker on the server by following:

```text
infra/hetzner/README.md
```

The GitHub workflow creates `/opt/imagent`, uploads the project, writes `.env.production`, runs migrations, and starts `db`, `web`, and `worker`.

## 4. Deploy

Deployment runs automatically on push to `main`.

Manual deploy:

```text
GitHub -> Actions -> Deploy to Hetzner -> Run workflow
```

## 5. First admin user

After first deploy, SSH into Hetzner:

```bash
cd /opt/imagent
docker compose -f docker-compose.prod.yml --env-file .env.production run --rm web \
  python scripts/create_admin.py --username admin --password '<admin-password>'
```

Then seed starter queries:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production run --rm web \
  python scripts/seed_query_catalog.py
```

