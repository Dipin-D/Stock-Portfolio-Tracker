#!/usr/bin/env bash
set -euo pipefail

APP_USER="tradingpro"
APP_GROUP="www-data"
APP_DIR="/srv/trading-pro/app"
VENV_DIR="/srv/trading-pro/venv"
ENV_FILE="/etc/trading-pro/trading-pro.env"
STATIC_DIR="/srv/trading-pro/static"
BACKUP_DIR="/srv/trading-pro/backups"
RUNTIME_DIR="/run/trading-pro"
NGINX_TEMPLATE="$APP_DIR/deploy/ec2/nginx/trading-pro.conf.template"
SYSTEMD_TEMPLATE="$APP_DIR/deploy/ec2/systemd/trading-pro.service"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this script as root." >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y \
  python3 \
  python3-venv \
  python3-pip \
  git \
  curl \
  build-essential \
  libpq-dev \
  postgresql \
  postgresql-contrib \
  nginx \
  certbot \
  python3-certbot-nginx

if ! id -u "${APP_USER}" >/dev/null 2>&1; then
  useradd --system --create-home --home-dir /home/${APP_USER} --shell /bin/bash "${APP_USER}"
fi

mkdir -p /srv/trading-pro /etc/trading-pro "${STATIC_DIR}" "${BACKUP_DIR}" "${RUNTIME_DIR}" /var/www/certbot
chown -R "${APP_USER}:${APP_GROUP}" /srv/trading-pro
chmod 750 /srv/trading-pro
chmod 750 "${STATIC_DIR}" "${BACKUP_DIR}"
chmod 755 "${RUNTIME_DIR}"

if [[ -d "${APP_DIR}" && ! -d "${VENV_DIR}" ]]; then
  runuser -u "${APP_USER}" -- python3 -m venv "${VENV_DIR}"
fi

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Expected env file at ${ENV_FILE}. Copy deploy/ec2/trading-pro.env.example there before bootstrap." >&2
fi

if [[ -f "${ENV_FILE}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a

  DB_NAME_VALUE="${DB_NAME:-tradingpro}"
  DB_USER_VALUE="${DB_USER:-tradingpro}"
  DB_PASSWORD_VALUE="${DB_PASSWORD:-}"

  if [[ -n "${DB_PASSWORD_VALUE}" ]]; then
    sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname = '${DB_USER_VALUE}'" | grep -q 1 || \
      sudo -u postgres psql -c "CREATE ROLE ${DB_USER_VALUE} WITH LOGIN PASSWORD '${DB_PASSWORD_VALUE}';"
    sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname = '${DB_NAME_VALUE}'" | grep -q 1 || \
      sudo -u postgres createdb -O "${DB_USER_VALUE}" "${DB_NAME_VALUE}"
  fi

  if [[ -f "${NGINX_TEMPLATE}" ]]; then
    SERVER_NAMES="$(python3 - <<'PY'
import os
hosts = [item.strip() for item in os.getenv("DJANGO_ALLOWED_HOSTS", "").split(",") if item.strip()]
filtered = [host for host in hosts if host not in {"127.0.0.1", "localhost"}]
print(" ".join(filtered or ["example.com", "www.example.com"]))
PY
)"
    sed "s/__SERVER_NAMES__/${SERVER_NAMES//\//\\/}/g" "${NGINX_TEMPLATE}" > /etc/nginx/sites-available/trading-pro
    ln -sf /etc/nginx/sites-available/trading-pro /etc/nginx/sites-enabled/trading-pro
    rm -f /etc/nginx/sites-enabled/default
  fi
fi

if [[ -f "${SYSTEMD_TEMPLATE}" ]]; then
  cp "${SYSTEMD_TEMPLATE}" /etc/systemd/system/trading-pro.service
fi

systemctl daemon-reload
systemctl enable postgresql
systemctl enable nginx
if [[ -f "/etc/systemd/system/trading-pro.service" ]]; then
  systemctl enable trading-pro
fi

nginx -t
systemctl restart nginx

echo "Bootstrap complete."
echo "Next steps:"
echo "  1. Ensure ${ENV_FILE} is populated with real secrets and domains."
echo "  2. Run: sudo bash ${APP_DIR}/scripts/ec2/deploy_ec2.sh"
echo "  3. Run Certbot once DNS is live."
