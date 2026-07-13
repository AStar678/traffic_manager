#!/usr/bin/env bash
set -euo pipefail

VISIONDRIVE_ROOT="${VISIONDRIVE_ROOT:-/home/aoxiang/visiondrive}"
ARCHIVE="${NVGESTURE_ARCHIVE:-${VISIONDRIVE_ROOT}/data/nvgesture_mirror/nvGesture_v1.1.7z}"
RAW_ROOT="${NVGESTURE_RAW_ROOT:-${VISIONDRIVE_ROOT}/data/nvgesture_raw}"
PREPARED_ROOT="${NVGESTURE_PREPARED_ROOT:-${VISIONDRIVE_ROOT}/data/nvgesture_prepared}"
OUTPUT_ROOT="${GESTURE_TRAIN_OUTPUT:-${VISIONDRIVE_ROOT}/output/gesture_dinov2_tcn_proto}"
PYTHON="${GESTURE_TRAIN_PYTHON:-/home/aoxiang/miniconda3/envs/gesture_train/bin/python}"
DOWNLOAD_PID="${NVGESTURE_DOWNLOAD_PID:-19222}"
EXPECTED_ARCHIVE_SIZE=41095268802

while kill -0 "${DOWNLOAD_PID}" 2>/dev/null; do
  current_size="$(stat -c %s "${ARCHIVE}" 2>/dev/null || echo 0)"
  echo "download_wait bytes=${current_size}/${EXPECTED_ARCHIVE_SIZE}"
  sleep 30
done

actual_size="$(stat -c %s "${ARCHIVE}")"
if [[ "${actual_size}" != "${EXPECTED_ARCHIVE_SIZE}" ]]; then
  echo "download_incomplete bytes=${actual_size} expected=${EXPECTED_ARCHIVE_SIZE}" >&2
  exit 20
fi

mkdir -p "${RAW_ROOT}" "${PREPARED_ROOT}" "${OUTPUT_ROOT}"
echo "extract_rgb archive=${ARCHIVE} output=${RAW_ROOT}"
7z x -y "${ARCHIVE}" "-o${RAW_ROOT}" \
  "-ir!*.lst" \
  "-ir!*sk_color.avi" \
  "-ir!*sk_color/*.jpg"

DATASET_ROOT="${RAW_ROOT}/nvGesture_v1.1/nvGesture_v1"
cd "${VISIONDRIVE_ROOT}/app/algorithm"

echo "prepare_nvgesture dataset=${DATASET_ROOT} output=${PREPARED_ROOT}"
"${PYTHON}" -m gesture.training.prepare_nvgesture \
  --dataset-root "${DATASET_ROOT}" \
  --output-dir "${PREPARED_ROOT}" \
  --gesture-model "${VISIONDRIVE_ROOT}/app/algorithm/gesture/app/public/models/gesture_recognizer.task" \
  --samples-per-video 24 \
  --crop-size 256 \
  --crop-expansion 1.70

export HF_ENDPOINT="${HF_ENDPOINT:-https://hf-mirror.com}"
export PYTHONUNBUFFERED=1

echo "training_smoke_test"
"${PYTHON}" -m gesture.training.train \
  --config gesture/training/config.nvgesture.yaml \
  --output-dir "${OUTPUT_ROOT}/smoke" \
  --smoke-test

echo "training_full"
"${PYTHON}" -m gesture.training.train \
  --config gesture/training/config.nvgesture.yaml \
  --output-dir "${OUTPUT_ROOT}/full"

echo "pipeline_complete output=${OUTPUT_ROOT}/full"
