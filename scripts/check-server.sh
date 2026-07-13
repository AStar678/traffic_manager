#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC1091
source "${PROJECT_ROOT}/deployment/server/server.env"

base="http://${VISIONDRIVE_SERVER_HOST}"

wait_for_url() {
  local name="$1"
  local url="$2"
  local attempts="${3:-45}"

  for ((attempt = 1; attempt <= attempts; attempt++)); do
    if curl --noproxy '*' --fail --silent --show-error \
      --connect-timeout 2 --max-time 5 "${url}" >/dev/null 2>&1; then
      echo "${name} 已就绪"
      return 0
    fi
    sleep 2
  done

  echo "等待 ${name} 超时：${url}" >&2
  return 1
}

wait_for_url "手势算法服务" "${base}:8002/health"
wait_for_url "WebRTC 视频网关" "${base}:8003/health"
wait_for_url "主服务" "${base}:8080/api/v1/cameras/slots"
nc -z -w 5 "${VISIONDRIVE_SERVER_HOST}" 3478 || { echo "TURN TCP 3478 不可达" >&2; exit 1; }
echo "TURN TCP 中继已就绪"

ssh -i "${VISIONDRIVE_SSH_KEY}" -o BatchMode=yes \
  "${VISIONDRIVE_SERVER_USER}@${VISIONDRIVE_SERVER_HOST}" \
  "curl --noproxy '*' --fail --silent http://127.0.0.1:8000/health >/dev/null; curl --noproxy '*' --fail --silent http://127.0.0.1:8001/health >/dev/null; systemctl is-active coturn.service; systemctl --user --no-pager --full status visiondrive-license.service visiondrive-police.service visiondrive-gesture.service visiondrive-webrtc.service visiondrive-backend.service | sed -n '1,100p'; nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader"

echo "VisionDrive 服务器检查通过：${VISIONDRIVE_SERVER_HOST}"
