#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${ROOT_DIR}/backups"
STAMP="$(date +%Y%m%d_%H%M%S)"

mkdir -p "${BACKUP_DIR}"

docker compose \
  -f "${ROOT_DIR}/docker-compose.prod.yml" \
  --env-file "${ROOT_DIR}/.env.production" \
  exec -T db \
  pg_dump -U "${POSTGRES_USER:-imagent}" -d "${POSTGRES_DB:-imagent}" \
  > "${BACKUP_DIR}/imagent_${STAMP}.sql"

find "${BACKUP_DIR}" -type f -name "imagent_*.sql" -mtime +14 -delete

echo "Backup written: ${BACKUP_DIR}/imagent_${STAMP}.sql"
