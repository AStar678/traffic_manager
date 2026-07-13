#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-${ROOT_DIR}/backend/.env.local}"
ACTION="${1:-status}"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "未找到数据库配置：${ENV_FILE}" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

required=(DB_SSH_HOST DB_SSH_USER DB_SSH_LOCAL_PORT DB_USERNAME DB_PASSWORD)
for name in "${required[@]}"; do
  [[ -n "${!name:-}" ]] || { echo "数据库隧道配置缺失：${name}" >&2; exit 1; }
done

DB_SSH_REMOTE_HOST="${DB_SSH_REMOTE_HOST:-127.0.0.1}"
DB_SSH_REMOTE_PORT="${DB_SSH_REMOTE_PORT:-3306}"
DB_NAME="${DB_NAME:-visiondrive}"
CONTROL_SOCKET="/tmp/visiondrive-db-%C.sock"
SSH_TARGET="${DB_SSH_USER}@${DB_SSH_HOST}"
SSH_OPTIONS=(
  -o BatchMode=yes
  -o ConnectTimeout=10
  -o ExitOnForwardFailure=yes
  -o ServerAliveInterval=30
  -o ServerAliveCountMax=3
)

if [[ -n "${DB_SSH_IDENTITY_FILE:-}" ]]; then
  SSH_OPTIONS+=(-i "${DB_SSH_IDENTITY_FILE}")
fi

port_ready() {
  nc -z 127.0.0.1 "${DB_SSH_LOCAL_PORT}" >/dev/null 2>&1
}

wait_for_port() {
  for _ in {1..40}; do
    port_ready && return 0
    sleep 0.25
  done
  return 1
}

start_tunnel() {
  if port_ready; then
    echo "数据库隧道已可用：127.0.0.1:${DB_SSH_LOCAL_PORT}"
    return 0
  fi

  ssh -fN -M -S "${CONTROL_SOCKET}" \
    -L "${DB_SSH_LOCAL_PORT}:${DB_SSH_REMOTE_HOST}:${DB_SSH_REMOTE_PORT}" \
    "${SSH_OPTIONS[@]}" \
    "${SSH_TARGET}"

  if ! wait_for_port; then
    echo "数据库隧道启动失败" >&2
    exit 1
  fi
  echo "数据库隧道已启动：127.0.0.1:${DB_SSH_LOCAL_PORT} -> ${DB_SSH_HOST}:${DB_SSH_REMOTE_PORT}"
}

case "${ACTION}" in
  start)
    start_tunnel
    ;;
  stop)
    if ssh -S "${CONTROL_SOCKET}" -O exit "${SSH_TARGET}" >/dev/null 2>&1; then
      echo "数据库隧道已停止"
    elif port_ready; then
      echo "端口 ${DB_SSH_LOCAL_PORT} 由其他进程占用，未强制终止" >&2
      exit 1
    else
      echo "数据库隧道未运行"
    fi
    ;;
  restart)
    ssh -S "${CONTROL_SOCKET}" -O exit "${SSH_TARGET}" >/dev/null 2>&1 || true
    start_tunnel
    ;;
  status)
    if port_ready; then
      echo "数据库隧道正常：127.0.0.1:${DB_SSH_LOCAL_PORT}"
    else
      echo "数据库隧道未运行" >&2
      exit 1
    fi
    ;;
  test)
    start_tunnel
    if command -v mysql >/dev/null 2>&1; then
      MYSQL_PWD="${DB_PASSWORD}" mysql \
        --protocol=TCP \
        -h 127.0.0.1 \
        -P "${DB_SSH_LOCAL_PORT}" \
        -u "${DB_USERNAME}" \
        "${DB_NAME}" \
        -NBe 'SELECT CONCAT("database=", DATABASE(), ", user=", CURRENT_USER(), ", status=ok");'
    else
      echo "隧道端口正常；本机未安装 mysql 客户端，跳过 SQL 查询"
    fi
    ;;
  *)
    echo "用法：$0 {start|stop|restart|status|test}" >&2
    exit 2
    ;;
esac
