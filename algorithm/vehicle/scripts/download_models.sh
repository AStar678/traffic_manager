#!/usr/bin/env sh
set -eu

target_dir="${1:-$(pwd)/models/ppvehicle}"
work_dir="$(mktemp -d)"
trap 'rm -rf "$work_dir"' EXIT

mkdir -p "$target_dir"

curl -fL \
  https://bj.bcebos.com/v1/paddledet/models/pipeline/mot_ppyoloe_s_36e_ppvehicle.zip \
  -o "$work_dir/mot.zip"
curl -fL \
  https://bj.bcebos.com/v1/paddledet/models/pipeline/vehicle_attribute_model.zip \
  -o "$work_dir/attr.zip"

unzip -q "$work_dir/mot.zip" -d "$work_dir/mot"
unzip -q "$work_dir/attr.zip" -d "$work_dir/attr"

mot_model="$(find "$work_dir/mot" -name infer_cfg.yml -print -quit | xargs dirname)"
attr_model="$(find "$work_dir/attr" -name infer_cfg.yml -print -quit | xargs dirname)"

test -n "$mot_model"
test -n "$attr_model"
rm -rf "$target_dir/mot" "$target_dir/attr"
cp -R "$mot_model" "$target_dir/mot"
cp -R "$attr_model" "$target_dir/attr"

echo "PP-Vehicle models are ready in $target_dir"
