#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="/etc/trading-pro/trading-pro.env"
BACKUP_DIR="/srv/trading-pro/backups"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this script as root." >&2
  exit 1
fi

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Env file ${ENV_FILE} not found." >&2
  exit 1
fi

mkdir -p "${BACKUP_DIR}"

set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

: "${DB_NAME:?DB_NAME must be set}"
: "${DB_USER:?DB_USER must be set}"

BACKUP_FILE="${BACKUP_DIR}/${DB_NAME}-${TIMESTAMP}.sql.gz"

export PGPASSWORD="${DB_PASSWORD:-}"
pg_dump \
  --host="${DB_HOST:-127.0.0.1}" \
  --port="${DB_PORT:-5432}" \
  --username="${DB_USER}" \
  --dbname="${DB_NAME}" \
  --no-owner \
  --no-privileges | gzip > "${BACKUP_FILE}"
unset PGPASSWORD

find "${BACKUP_DIR}" -type f -name "*.sql.gz" -mtime +14 -delete

echo "Database backup written to ${BACKUP_FILE}"
