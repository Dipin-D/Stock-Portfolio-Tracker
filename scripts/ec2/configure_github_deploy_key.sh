#!/usr/bin/env bash
set -euo pipefail

APP_USER="tradingpro"
APP_HOME="/home/${APP_USER}"
SSH_DIR="${APP_HOME}/.ssh"
KEY_DEST="${SSH_DIR}/id_ed25519"
KEY_SOURCE="${1:-${GITHUB_DEPLOY_KEY_FILE:-}}"
REPO_SSH_URL="${GITHUB_REPO_SSH_URL:-}"
APP_DIR="/srv/trading-pro/app"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this script as root." >&2
  exit 1
fi

if [[ -z "${KEY_SOURCE}" ]]; then
  echo "Provide the deploy key path as the first argument or GITHUB_DEPLOY_KEY_FILE." >&2
  exit 1
fi

if [[ ! -f "${KEY_SOURCE}" ]]; then
  echo "Deploy key file ${KEY_SOURCE} not found." >&2
  exit 1
fi

if ! id -u "${APP_USER}" >/dev/null 2>&1; then
  echo "App user ${APP_USER} does not exist yet. Run bootstrap_ec2.sh first." >&2
  exit 1
fi

mkdir -p "${SSH_DIR}"
install -m 600 "${KEY_SOURCE}" "${KEY_DEST}"
ssh-keyscan github.com > "${SSH_DIR}/known_hosts"
cat > "${SSH_DIR}/config" <<'EOF'
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes
    StrictHostKeyChecking yes
EOF

chown -R "${APP_USER}:${APP_USER}" "${SSH_DIR}"
chmod 700 "${SSH_DIR}"
chmod 600 "${SSH_DIR}/config" "${SSH_DIR}/known_hosts"

if [[ -n "${REPO_SSH_URL}" && ! -d "${APP_DIR}/.git" ]]; then
  mkdir -p /srv/trading-pro
  chown -R "${APP_USER}:www-data" /srv/trading-pro
  runuser -u "${APP_USER}" -- git clone "${REPO_SSH_URL}" "${APP_DIR}"
fi

echo "GitHub deploy key installed for ${APP_USER}."
echo "Test with:"
echo "  sudo -u ${APP_USER} ssh -T git@github.com"
