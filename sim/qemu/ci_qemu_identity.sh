#!/usr/bin/env bash
# CI helper: build is assumed already run OR we build here from firmware/.
# Invoked from gcu/firmware with IDF exported (espressif/esp-idf-ci-action).
set -euo pipefail

echo "== idf.py build =="
idf.py build

echo "== merge flash image =="
esptool.py --chip esp32s3 merge_bin --fill-flash-size 4MB \
  -o build/qemu_flash.bin @build/flash_args
ls -la build/qemu_flash.bin

echo "== ensure qemu-xtensa on PATH =="
# Container image usually already has qemu; install is cheap/no-op if present.
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
