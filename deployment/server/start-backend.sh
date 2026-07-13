#!/usr/bin/env bash
set -euo pipefail

DEPLOY_ROOT="${VISIONDRIVE_SERVER_DIR:-${HOME}/visiondrive}"
BACKEND_ENV="${BACKEND_ENV:-${DEPLOY_ROOT}/config/backend.env}"
RUNTIME_ENV="${RUNTIME_ENV:-${DEPLOY_ROOT}/config/runtime.env}"

[[ -f "${BACKEND_ENV}" ]] || { echo "缺少后端配置：${BACKEND_ENV}" >&2; exit 1; }

set -a
# shellcheck disable=SC1090
source "${BACKEND_ENV}"
# shellcheck disable=SC1090
source "${RUNTIME_ENV}"
set +a

if [[ -n "${JPA_DDL_AUTO_OVERRIDE:-}" ]]; then
  export JPA_DDL_AUTO="${JPA_DDL_AUTO_OVERRIDE}"
fi

required=(DB_URL DB_USERNAME DB_PASSWORD JWT_SECRET)
for name in "${required[@]}"; do
  [[ -n "${!name:-}" ]] || { echo "后端配置缺失：${name}" >&2; exit 1; }
done

if [[ "${DB_SSH_DISABLED:-false}" != "true" ]]; then
  required_ssh=(DB_SSH_HOST DB_SSH_USER DB_SSH_LOCAL_PORT)
  for name in "${required_ssh[@]}"; do
    [[ -n "${!name:-}" ]] || { echo "数据库隧道配置缺失：${name}" >&2; exit 1; }
  done
  ssh_args=(
    -N
    -L "${DB_SSH_LOCAL_PORT}:127.0.0.1:3306"
    -o ExitOnForwardFailure=yes
    -o ServerAliveInterval=30
    -o ServerAliveCountMax=3
    -o StrictHostKeyChecking=accept-new
  )
  if [[ -n "${DB_SSH_IDENTITY_FILE:-}" ]]; then
    ssh_args+=( -i "${DB_SSH_IDENTITY_FILE}" -o IdentitiesOnly=yes )
  fi
  ssh "${ssh_args[@]}" "${DB_SSH_USER}@${DB_SSH_HOST}" &
  tunnel_pid=$!
  java_pid=""
  cleanup() {
    [[ -z "${java_pid}" ]] || kill "${java_pid}" 2>/dev/null || true
    kill "${tunnel_pid}" 2>/dev/null || true
  }
  trap cleanup EXIT INT TERM
  for _ in {1..40}; do
    timeout 1 bash -c "</dev/tcp/127.0.0.1/${DB_SSH_LOCAL_PORT}" 2>/dev/null && break
    sleep 0.25
  done
  timeout 1 bash -c "</dev/tcp/127.0.0.1/${DB_SSH_LOCAL_PORT}" 2>/dev/null || {
    echo "数据库 SSH 隧道建立失败" >&2
    exit 1
  }
fi

if [[ "${DB_SSH_DISABLED:-false}" == "true" ]]; then
  exec java ${JAVA_OPTS:--Xms512m -Xmx2048m} -jar "${DEPLOY_ROOT}/app/backend/vision-drive-backend.jar"
fi

java ${JAVA_OPTS:--Xms512m -Xmx2048m} -jar "${DEPLOY_ROOT}/app/backend/vision-drive-backend.jar" &
java_pid=$!

set +e
wait -n "${tunnel_pid}" "${java_pid}"
child_status=$?
set -e

if ! kill -0 "${tunnel_pid}" 2>/dev/null; then
  echo "数据库 SSH 隧道意外退出，触发主服务自动重启" >&2
  exit 1
fi

exit "${child_status}"
