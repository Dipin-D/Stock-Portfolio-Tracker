#!/usr/bin/env bash
set -euo pipefail

APP_USER="tradingpro"
APP_DIR="/srv/trading-pro/app"
VENV_DIR="/srv/trading-pro/venv"
ENV_FILE="/etc/trading-pro/trading-pro.env"
PYTHON_BIN="${VENV_DIR}/bin/python"
PIP_BIN="${VENV_DIR}/bin/pip"
SYSTEMD_TEMPLATE="${APP_DIR}/deploy/ec2/systemd/trading-pro.service"
SYSTEMD_UNIT="/etc/systemd/system/trading-pro.service"
NGINX_TEMPLATE="${APP_DIR}/deploy/ec2/nginx/trading-pro.conf.template"
NGINX_SITE="/etc/nginx/sites-available/trading-pro"
NGINX_SITE_LINK="/etc/nginx/sites-enabled/trading-pro"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this script as root." >&2
  exit 1
fi

if [[ ! -d "${APP_DIR}" ]]; then
  echo "App directory ${APP_DIR} does not exist." >&2
  exit 1
fi

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Env file ${ENV_FILE} does not exist." >&2
  exit 1
fi

if [[ ! -d "${VENV_DIR}" ]]; then
  runuser -u "${APP_USER}" -- python3 -m venv "${VENV_DIR}"
fi

run_as_app() {
  local command="$1"
  runuser -u "${APP_USER}" -- /bin/bash -lc "cd '${APP_DIR}' && ${command}"
}

render_server_names() {
  python3 - <<'PY'
import os
hosts = [item.strip() for item in os.getenv("DJANGO_ALLOWED_HOSTS", "").split(",") if item.strip()]
filtered = [host for host in hosts if host not in {"127.0.0.1", "localhost"}]
print(" ".join(filtered or ["localhost"]))
PY
}

sync_runtime_configs() {
  local systemd_changed=0

  if [[ -f "${SYSTEMD_TEMPLATE}" ]]; then
    if [[ ! -f "${SYSTEMD_UNIT}" ]] || ! cmp -s "${SYSTEMD_TEMPLATE}" "${SYSTEMD_UNIT}"; then
      install -m 0644 "${SYSTEMD_TEMPLATE}" "${SYSTEMD_UNIT}"
      systemd_changed=1
    fi
  fi

  if [[ "${systemd_changed}" -eq 1 ]]; then
    systemctl daemon-reload
  fi

  if [[ -f "${NGINX_TEMPLATE}" ]]; then
    local rendered_nginx
    local server_names
    rendered_nginx="$(mktemp)"
    server_names="$(render_server_names)"
    sed "s/__SERVER_NAMES__/${server_names//\//\\/}/g" "${NGINX_TEMPLATE}" > "${rendered_nginx}"
    install -m 0644 "${rendered_nginx}" "${NGINX_SITE}"
    ln -sf "${NGINX_SITE}" "${NGINX_SITE_LINK}"
    rm -f /etc/nginx/sites-enabled/default
    rm -f "${rendered_nginx}"
  fi
}

set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

if run_as_app "git rev-parse --is-inside-work-tree >/dev/null 2>&1"; then
  run_as_app "git pull --ff-only"
else
  echo "Skipping git pull because ${APP_DIR} is not a git checkout."
fi

sync_runtime_configs

run_as_app "'${PIP_BIN}' install --upgrade pip"
run_as_app "'${PIP_BIN}' install -r requirements/production.txt"
/bin/bash -lc "set -a && source '${ENV_FILE}' && set +a && cd '${APP_DIR}' && sudo -E -u '${APP_USER}' '${PYTHON_BIN}' manage.py migrate --noinput"
/bin/bash -lc "set -a && source '${ENV_FILE}' && set +a && cd '${APP_DIR}' && sudo -E -u '${APP_USER}' '${PYTHON_BIN}' manage.py collectstatic --noinput"

systemctl restart trading-pro
nginx -t
systemctl reload nginx
sleep 3

HEALTH_HOST="$(python3 - <<'PY'
import os
hosts = [item.strip() for item in os.getenv("DJANGO_ALLOWED_HOSTS", "").split(",") if item.strip()]
for host in hosts:
    if host not in {"127.0.0.1", "localhost"}:
        print(host)
        break
else:
    print("localhost")
PY
)"

curl --fail --silent --show-error \
  --unix-socket /run/trading-pro/gunicorn.sock \
  -H "Host: ${HEALTH_HOST}" \
  -H 'X-Forwarded-Proto: https' \
  http://localhost/health/ | grep -q '"status": "ok"'
systemctl --no-pager --full status trading-pro

echo "Deploy completed successfully."
