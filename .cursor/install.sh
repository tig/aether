#!/usr/bin/env bash
# Cloud Agent install for Aether (tig/aether) — host development gate.
#
# Idempotent: safe to re-run. Prepares the C host gate, the silico host spine,
# the AFR face mockup (SVG -> PNG capture), and the pure-software bench
# (V-ECU + V-AETHER + orchestrator). It does not install ESP-IDF and does not
# touch metal; flashing the ESP32-S3 firmware is a separate, hardware-only path.
set -euo pipefail

# Repo root is the parent of this .cursor/ dir. tig/silico is pinned host-only
# as a sibling clone (`-e ../silico`); firmware/ never imports it.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PARENT="$(dirname "$REPO_ROOT")"

# 1) System toolchain + SVG rasterizer for the AFR face capture.
export DEBIAN_FRONTEND=noninteractive
sudo apt-get update -qq
sudo apt-get install -y \
  build-essential cmake git ca-certificates \
  imagemagick librsvg2-bin

# Ubuntu ships ImageMagick 6 (`convert`); the mockup capture invokes `magick`.
# The IM6 CLI accepts the same argument order, so a thin shim keeps
# `python -m mockup.capture` working unchanged.
if ! command -v magick >/dev/null 2>&1; then
  printf '#!/usr/bin/env bash\nexec convert "$@"\n' | sudo tee /usr/local/bin/magick >/dev/null
  sudo chmod +x /usr/local/bin/magick
fi

# 2) Host spine: sibling tig/silico clone (skipped when already present, e.g.
#    restored from the environment snapshot).
if [ ! -d "$PARENT/silico/.git" ]; then
  git clone --depth 1 https://github.com/tig/silico "$PARENT/silico"
fi

# 3) Editable install of silico + vendored bedside + pytest, system-wide so the
#    `silico` / `bedside` / `pytest` console scripts are on PATH for every shell.
sudo python3 -m pip install \
  -e "$PARENT/silico" \
  -e "$PARENT/silico/third_party/bedside" \
  pytest

# 4) Configure the C host build so `silico gate` and the host_test target are
#    ready to run without a separate configure step.
cd "$REPO_ROOT"
cmake -S host -B build/host

echo "aether cloud install: done"
