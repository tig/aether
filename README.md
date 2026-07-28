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

Simulated air–fuel ratio in **landscape** (logical **448×368**; native panel 368×448 rotated so USB + hard buttons are on top): LED arc, scale **8–20**, large center readout with **AIR/FUEL RATIO** under the value. **MODE** / **SEL** are **labels** for the physical keys (not on-screen buttons). Logging is a **red LED** between those labels. **Page dots** at the bottom mean swipe left/right.

```text
# From the aether product root (Python 3.11+)
python -m mockup
python -m mockup.capture          # PNG frames (needs ImageMagick magick)
python -m mockup.capture --html   # + Edge/Chrome headless of gauge.html

# Unit tests (pure mapping + simulator — no display required)
python -m pytest mockup/tests -q

# Open the graphical mockup in a browser
# mockup/gauge.html
```

`python -m mockup` prints a short simulated stream and writes SVG under `mockup/out/`.
**Agents must run `python -m mockup.capture` and open the PNGs** after visual layout changes — do not claim the face looks right from code alone. Pure mapping lives in `mockup/afr_gauge.py`.

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
