#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC1091
source "${PROJECT_ROOT}/deployment/server/server.env"

remote="${VISIONDRIVE_SERVER_USER}@${VISIONDRIVE_SERVER_HOST}"
ssh_cmd=(ssh -i "${VISIONDRIVE_SSH_KEY}" -o BatchMode=yes)
rsync_ssh="ssh -i ${VISIONDRIVE_SSH_KEY} -o BatchMode=yes"

if [[ "${SKIP_TESTS:-0}" != "1" ]]; then
  echo "[1/6] 本机前端构建"
  (cd "${PROJECT_ROOT}/frontend" && npm run build)
  echo "[2/6] 本机后端测试与打包"
  (cd "${PROJECT_ROOT}/backend" && mvn test -q && mvn package -DskipTests -q)
  echo "[3/6] 本机算法测试"
  (cd "${PROJECT_ROOT}/algorithm" && .venv/bin/python -m pytest -q license/tests police/tests gesture/tests webrtc/tests)
else
  echo "[1-3/6] 已按 SKIP_TESTS=1 跳过本机测试"
fi

jar_path="$(find "${PROJECT_ROOT}/backend/target" -maxdepth 1 -name 'vision-drive-backend-*.jar' -type f | head -1)"
[[ -n "${jar_path}" ]] || { echo "未找到后端 JAR" >&2; exit 1; }
[[ -f "${PROJECT_ROOT}/backend/.env.local" ]] || { echo "缺少 backend/.env.local" >&2; exit 1; }
[[ -f "${PROJECT_ROOT}/deployment/server/turn.env" ]] || { echo "缺少 deployment/server/turn.env（TURN 运行密钥）" >&2; exit 1; }

echo "[4/6] 同步应用代码"
"${ssh_cmd[@]}" "${remote}" "mkdir -p '${VISIONDRIVE_SERVER_DIR}/app/backend' '${VISIONDRIVE_SERVER_DIR}/app/algorithm' '${VISIONDRIVE_SERVER_DIR}/config' '${VISIONDRIVE_SERVER_DIR}/deployment' '${VISIONDRIVE_SERVER_DIR}/models/license' '${VISIONDRIVE_SERVER_DIR}/models/police' '${VISIONDRIVE_SERVER_DIR}/shared/camera-sources' '${VISIONDRIVE_SERVER_DIR}/shared/camera-frames'"
rsync -az --delete -e "${rsync_ssh}" \
  --exclude '.venv/' --exclude '__pycache__/' --exclude '*.pyc' --exclude '.env' \
  "${PROJECT_ROOT}/algorithm/" \
  "${remote}:${VISIONDRIVE_SERVER_DIR}/app/algorithm/"
rsync -az -e "${rsync_ssh}" "${jar_path}" "${remote}:${VISIONDRIVE_SERVER_DIR}/app/backend/vision-drive-backend.jar"
rsync -az --delete -e "${rsync_ssh}" \
  --exclude 'turn.env' --exclude 'coturn.runtime.conf' \
  "${PROJECT_ROOT}/deployment/server/" "${remote}:${VISIONDRIVE_SERVER_DIR}/deployment/server/"
rsync -az -e "${rsync_ssh}" "${PROJECT_ROOT}/backend/.env.local" "${remote}:${VISIONDRIVE_SERVER_DIR}/config/backend.env"
rsync -az -e "${rsync_ssh}" "${PROJECT_ROOT}/deployment/server/runtime.env" "${remote}:${VISIONDRIVE_SERVER_DIR}/config/runtime.env"
rsync -az -e "${rsync_ssh}" "${PROJECT_ROOT}/deployment/server/turn.env" "${remote}:${VISIONDRIVE_SERVER_DIR}/config/turn.env"
"${ssh_cmd[@]}" "${remote}" "chmod 600 '${VISIONDRIVE_SERVER_DIR}/config/backend.env' '${VISIONDRIVE_SERVER_DIR}/config/turn.env'"

if [[ "${SYNC_MODELS:-0}" == "1" ]]; then
  echo "[5/6] 同步模型文件"
  rsync -az --delete -e "${rsync_ssh}" \
    "/Users/aoxiang/Desktop/软件工程学期实训/车牌识别/" \
    "${remote}:${VISIONDRIVE_SERVER_DIR}/models/license/"
  "${ssh_cmd[@]}" "${remote}" "mkdir -p '${VISIONDRIVE_SERVER_DIR}/models/police'"
  for directory in ctpgr-pytorch-master checkpoints generated; do
    rsync -az --delete -e "${rsync_ssh}" \
      "/Users/aoxiang/Desktop/软件工程学期实训/交警指令识别/${directory}/" \
      "${remote}:${VISIONDRIVE_SERVER_DIR}/models/police/${directory}/"
  done
else
  echo "[5/6] 未同步模型（首次部署请设置 SYNC_MODELS=1）"
fi

echo "[6/6] 安装依赖并重启远端服务"
"${ssh_cmd[@]}" "${remote}" \
  "chmod +x '${VISIONDRIVE_SERVER_DIR}'/deployment/server/*.sh && VISIONDRIVE_SERVER_DIR='${VISIONDRIVE_SERVER_DIR}' '${VISIONDRIVE_SERVER_DIR}/deployment/server/bootstrap.sh' && VISIONDRIVE_SERVER_DIR='${VISIONDRIVE_SERVER_DIR}' '${VISIONDRIVE_SERVER_DIR}/deployment/server/install-services.sh'"

"${PROJECT_ROOT}/scripts/check-server.sh"
