# Aether

**Aether** is a serial & CANbus ECU monitor, logger, and real-time **AFR gauge** for a pocket **ESP32-S3 1.8″ AMOLED** touch board (Amazon ASIN [B0F242GFHK](https://www.amazon.com/dp/B0F242GFHK) / ESP32-S3-Touch-AMOLED-1.8 class: 368×448 AMOLED, SH8601 QSPI, FT3168 touch).

This repository is a product GCU (General Contact Unit) used with [Silico](https://github.com/tig/silico). Runtime target is **C / ESP-IDF** (same plate shape as [tig/xuss-c](https://github.com/tig/xuss-c)).

## Status

**Spec-learning mockup (this pass).** Host-runnable AFR gauge mockup with **simulated** AFR data — not live OBD/CAN, not full metal product acceptance. Use what the mockup teaches (square face, fat MODE/SEL, scale, color bands, refresh feel) to refine [spec.md](spec.md).

Contract seed: [spec.md](spec.md). Host path: [install/README.md](install/README.md).

## Hardware

| Item | Detail |
|------|--------|
| Board | ESP32-S3R8, 1.8″ AMOLED 368×448, SH8601 (QSPI), FT3168 (I2C touch), Type-C USB |
| Class | ESP32-S3-Touch-AMOLED-1.8 (B0F242GFHK) |
| Product role | ECU monitor / logger over serial & CANbus; real-time AFR gauge face |

## AFR gauge mockup (host)

Simulated air–fuel ratio on a **368×448** device face (real panel size): LED arc flush to edges, scale **8–20**, large center readout with **AIR/FUEL RATIO** under the value, a **red logging LED** (no text) above the buttons, and fat **MODE** / **SEL** targets. **SEL** toggles logging in the mockup.

```text
# From the aether product root (Python 3.11+)
python -m mockup
# or:
python mockup/run.py

# Unit tests (pure mapping + simulator — no display required)
python -m pytest mockup/tests -q

# Open the graphical mockup in a browser (double-click also works)
# mockup/gauge.html
```

`python -m mockup` prints a short simulated stream (AFR, band, lit segments) and writes a snapshot under `mockup/out/` when run with defaults. Pure mapping lives in `mockup/afr_gauge.py` and is the unit under test.

## Host gate (C plate)

```text
cmake -S host -B build/host
cmake --build build/host --target host_test
silico gate
```

Plus mockup tests above for the AFR face learning path.

## Deploy (later metal — not this pass)

```text
silico inspect --port COMx
silico deploy --port COMx --yes --verify --reset
```

Requires ESP-IDF. Metal product face on the AMOLED is **out of gate** for this bootstrap.

## Layout

| Path | Role |
|------|------|
| `spec.md` | Product contract seed |
| `silico.toml` | C / ESP-IDF pin, product identity |
| `firmware/` | ESP-IDF app (plate) |
| `host/` | C host tests |
| `mockup/` | Host AFR gauge mockup + unit tests |
| `install/` | Update-path notes |
