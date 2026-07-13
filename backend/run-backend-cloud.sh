#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ENV_FILE:-${SCRIPT_DIR}/.env.local}"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "未找到云端配置文件：${ENV_FILE}" >&2
  echo "请复制 .env.example 为 .env.local 并填写数据库、JWT 和短信配置。" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

if [[ -n "${SMS_PROVIDER_OVERRIDE:-}" ]]; then
  export SMS_PROVIDER="${SMS_PROVIDER_OVERRIDE}"
fi
if [[ -n "${SMS_EXPOSE_MOCK_CODE_OVERRIDE:-}" ]]; then
  export SMS_EXPOSE_MOCK_CODE="${SMS_EXPOSE_MOCK_CODE_OVERRIDE}"
fi
if [[ -n "${JPA_DDL_AUTO_OVERRIDE:-}" ]]; then
  export JPA_DDL_AUTO="${JPA_DDL_AUTO_OVERRIDE}"
fi

required_variables=(
  DB_URL DB_USERNAME DB_PASSWORD JWT_SECRET
  DB_SSH_HOST DB_SSH_USER DB_SSH_LOCAL_PORT
)
for variable_name in "${required_variables[@]}"; do
  if [[ -z "${!variable_name:-}" ]]; then
    echo "云端配置缺失：${variable_name}" >&2
    exit 1
  fi
done

TUNNEL_PID=""
if ! nc -z 127.0.0.1 "${DB_SSH_LOCAL_PORT}" 2>/dev/null; then
  ssh_options=(
    -o BatchMode=yes
    -o ConnectTimeout=10
    -o ExitOnForwardFailure=yes
    -o ServerAliveInterval=30
    -o ServerAliveCountMax=3
  )
  if [[ -n "${DB_SSH_IDENTITY_FILE:-}" ]]; then
    ssh_options+=(-i "${DB_SSH_IDENTITY_FILE}")
  fi

  ssh -N \
    -L "${DB_SSH_LOCAL_PORT}:${DB_SSH_REMOTE_HOST:-127.0.0.1}:${DB_SSH_REMOTE_PORT:-3306}" \
    "${ssh_options[@]}" \
    "${DB_SSH_USER}@${DB_SSH_HOST}" &
  TUNNEL_PID=$!
else
  echo "复用已有数据库隧道：127.0.0.1:${DB_SSH_LOCAL_PORT}"
fi

cleanup() {
  if [[ -n "${TUNNEL_PID}" ]]; then
    kill "${TUNNEL_PID}" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

for _ in {1..30}; do
  if nc -z 127.0.0.1 "${DB_SSH_LOCAL_PORT}" 2>/dev/null; then
    break
  fi
  sleep 0.2
done

if ! nc -z 127.0.0.1 "${DB_SSH_LOCAL_PORT}" 2>/dev/null; then
  echo "无法建立 MySQL SSH 隧道" >&2
  exit 1
fi

cd "${SCRIPT_DIR}"
mvn spring-boot:run
