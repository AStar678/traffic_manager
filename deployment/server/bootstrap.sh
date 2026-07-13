#!/usr/bin/env bash
set -euo pipefail

DEPLOY_ROOT="${VISIONDRIVE_SERVER_DIR:-${HOME}/visiondrive}"
CONDA_BIN="${CONDA_BIN:-${HOME}/miniconda3/bin/conda}"
ENV_NAME="${VISIONDRIVE_CONDA_ENV:-visiondrive}"
ENV_DIR="${HOME}/miniconda3/envs/${ENV_NAME}"
VEHICLE_ENV_NAME="${VISIONDRIVE_VEHICLE_CONDA_ENV:-visiondrive-vehicle}"
VEHICLE_ENV_DIR="${HOME}/miniconda3/envs/${VEHICLE_ENV_NAME}"

command -v java >/dev/null || { echo "缺少 Java 17，请先安装 openjdk-17-jre-headless" >&2; exit 1; }
command -v ffmpeg >/dev/null || { echo "缺少 FFmpeg，请先安装 ffmpeg" >&2; exit 1; }
command -v turnserver >/dev/null || { echo "缺少 coturn，请先执行 sudo apt install coturn" >&2; exit 1; }
[[ -x "${CONDA_BIN}" ]] || { echo "未找到 Conda：${CONDA_BIN}" >&2; exit 1; }

mkdir -p \
  "${DEPLOY_ROOT}/app/backend" \
  "${DEPLOY_ROOT}/app/algorithm" \
  "${DEPLOY_ROOT}/config" \
  "${DEPLOY_ROOT}/data" \
  "${DEPLOY_ROOT}/logs" \
  "${DEPLOY_ROOT}/models/license" \
  "${DEPLOY_ROOT}/models/ppvehicle" \
  "${DEPLOY_ROOT}/models/police" \
  "${DEPLOY_ROOT}/vendor" \
  "${DEPLOY_ROOT}/shared/camera-sources" \
  "${DEPLOY_ROOT}/shared/camera-frames"

if [[ ! -x "${ENV_DIR}/bin/python" ]]; then
  "${CONDA_BIN}" create --name "${ENV_NAME}" --clone pytorch_base --yes
fi
if [[ ! -x "${VEHICLE_ENV_DIR}/bin/python" ]]; then
  "${CONDA_BIN}" create --name "${VEHICLE_ENV_NAME}" --clone "${ENV_NAME}" --yes
fi

for requirements in \
  "${DEPLOY_ROOT}/app/algorithm/license/requirements.txt" \
  "${DEPLOY_ROOT}/app/algorithm/police/requirements.txt" \
  "${DEPLOY_ROOT}/app/algorithm/gesture/requirements.txt" \
  "${DEPLOY_ROOT}/app/algorithm/webrtc/requirements.txt"; do
  "${ENV_DIR}/bin/python" -m pip install --disable-pip-version-check -r "${requirements}"
done
"${VEHICLE_ENV_DIR}/bin/python" -m pip install --disable-pip-version-check \
  -r "${DEPLOY_ROOT}/app/algorithm/vehicle/requirements.txt"

if [[ ! -f "${DEPLOY_ROOT}/vendor/PaddleDetection/deploy/pipeline/pipeline.py" ]]; then
  git clone --depth 1 --branch release/2.9 \
    https://github.com/PaddlePaddle/PaddleDetection.git \
    "${DEPLOY_ROOT}/vendor/PaddleDetection"
fi
"${VEHICLE_ENV_DIR}/bin/python" -m pip install --disable-pip-version-check \
  -r "${DEPLOY_ROOT}/vendor/PaddleDetection/requirements.txt"

if ! "${VEHICLE_ENV_DIR}/bin/python" -c "import paddle; assert paddle.device.is_compiled_with_cuda()" >/dev/null 2>&1; then
  "${VEHICLE_ENV_DIR}/bin/python" -m pip uninstall -y paddlepaddle paddlepaddle-gpu || true
  "${VEHICLE_ENV_DIR}/bin/python" -m pip install paddlepaddle-gpu==3.3.0 \
    -i https://www.paddlepaddle.org.cn/packages/stable/cu118/
fi

"${ENV_DIR}/bin/python" -c \
  "import torch; assert torch.cuda.is_available(), 'CUDA 不可用'; print('CUDA ready:', torch.cuda.get_device_name(0), torch.__version__, torch.version.cuda)"
"${VEHICLE_ENV_DIR}/bin/python" -c \
  "import paddle; assert paddle.device.is_compiled_with_cuda(), 'Paddle CUDA 不可用'; paddle.set_device('gpu:0'); print('Paddle GPU ready:', paddle.__version__, paddle.device.cuda.get_device_name())"
