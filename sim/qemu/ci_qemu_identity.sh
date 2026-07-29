#!/usr/bin/env bash
# CI helper: build firmware, merge flash from build/, identity knock under QEMU.
# Invoked from gcu/firmware with IDF exported (espressif/esp-idf-ci-action).
set -euo pipefail

echo "== idf.py build =="
idf.py build

echo "== merge flash image (cwd=build; flash_args paths are relative) =="
# Project default flash_size is often 2MB; match it so QEMU accepts the image.
FLASH_SIZE=2MB
if grep -q 'CONFIG_ESPTOOLPY_FLASHSIZE_4MB=y' sdkconfig 2>/dev/null; then
  FLASH_SIZE=4MB
elif grep -q 'CONFIG_ESPTOOLPY_FLASHSIZE_8MB=y' sdkconfig 2>/dev/null; then
  FLASH_SIZE=8MB
elif grep -q 'CONFIG_ESPTOOLPY_FLASHSIZE_16MB=y' sdkconfig 2>/dev/null; then
  FLASH_SIZE=16MB
fi
echo "flash size: ${FLASH_SIZE}"

(
  cd build
  esptool.py --chip esp32s3 merge_bin --fill-flash-size "${FLASH_SIZE}" \
    -o qemu_flash.bin @flash_args
  ls -la qemu_flash.bin
)

echo "== ensure qemu-xtensa on PATH =="
python "${IDF_PATH}/tools/idf_tools.py" install qemu-xtensa || true
# shellcheck disable=SC1091
. "${IDF_PATH}/export.sh"
command -v qemu-system-xtensa

echo "== identity knock under QEMU =="
python ../sim/qemu/identity_knock.py \
  --flash build/qemu_flash.bin \
  --machine esp32s3 \
  --port 5555 \
  --boot-timeout 40 \
  --knock-timeout 15

echo "OK: qemu identity knock green"
