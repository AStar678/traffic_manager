#!/usr/bin/env bash
set -euo pipefail

DEPLOY_ROOT="${VISIONDRIVE_SERVER_DIR:-${HOME}/visiondrive}"
UNIT_SOURCE="${DEPLOY_ROOT}/deployment/server/systemd"
UNIT_TARGET="${HOME}/.config/systemd/user"

mkdir -p "${UNIT_TARGET}"
cp "${UNIT_SOURCE}"/visiondrive-*.service "${UNIT_TARGET}/"
cp "${UNIT_SOURCE}"/visiondrive.target "${UNIT_TARGET}/"
systemctl --user daemon-reload
systemctl --user enable visiondrive.target
systemctl --user restart visiondrive-license.service visiondrive-police.service visiondrive-gesture.service visiondrive-webrtc.service
systemctl --user restart visiondrive-backend.service
systemctl --user start visiondrive.target
