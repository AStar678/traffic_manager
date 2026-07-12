#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SMS_ENV_FILE:-${SCRIPT_DIR}/.env.local}"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "未找到短信配置文件：${ENV_FILE}" >&2
  echo "请复制 .env.example 为 .env.local，并填写阿里云号码认证配置。" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

required_variables=(
  ALIYUN_ACCESS_KEY_ID
  ALIYUN_ACCESS_KEY_SECRET
  ALIYUN_SMS_SIGN_NAME
  ALIYUN_SMS_TEMPLATE_CODE
)

for variable_name in "${required_variables[@]}"; do
  if [[ -z "${!variable_name:-}" ]]; then
    echo "短信配置缺失：${variable_name}" >&2
    exit 1
  fi
done

export SMS_PROVIDER=aliyun
export SMS_EXPOSE_MOCK_CODE=false

cd "${SCRIPT_DIR}"
exec mvn spring-boot:run
