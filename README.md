# Aether

**Aether** is a serial & CANbus ECU monitor, logger, and real-time **AFR gauge** for a pocket **ESP32-S3 1.8″ AMOLED** touch board (Amazon ASIN [B0F242GFHK](https://www.amazon.com/dp/B0F242GFHK) / ESP32-S3-Touch-AMOLED-1.8 class: 368×448 AMOLED, SH8601 QSPI, FT3168 touch).

This repository is a product GCU (General Contact Unit) used with [Silico](https://github.com/tig/silico). Runtime target is **C / ESP-IDF** (same plate shape as [tig/xuss-c](https://github.com/tig/xuss-c)).

## Status

**Spec-learning mockup (this pass).** Host-runnable AFR screen with **simulated** AFR, RPM, and TPS — not live OBD/CAN, not full metal product acceptance.

## Specs

| Document | Scope |
|----------|--------|
| **[specs/spec.md](specs/spec.md)** | Product requirements: mission, device, what makes AFR **useful** (context, units, logging, alarms, …) |
| **[specs/afr-face.md](specs/afr-face.md)** | **AFR screen only** — layout, dial, type, on-screen RPM/TPS |
| **[specs/lexicon.md](specs/lexicon.md)** | Face phrase book |
| [spec.md](spec.md) | Short seed pointer → `specs/` |

Host path: [install/README.md](install/README.md).

## Hardware

| Item | Detail |
|------|--------|
| Board | ESP32-S3R8, 1.8″ AMOLED 368×448, SH8601 (QSPI), FT3168 (I2C touch), Type-C USB |
| Class | ESP32-S3-Touch-AMOLED-1.8 (B0F242GFHK) |
| Product role | ECU monitor / logger over serial & CANbus; real-time AFR gauge face |
| UI orientation | Landscape **448×368** (hard buttons + USB on top) |

## AFR gauge mockup (host)

![Aether AFR face host mockup](docs/images/afr-face-mockup.gif)

Simulated landscape face: **dial**, large AFR **value**, **RPM** / **TPS** (to **WOT**) below, **banner** with MODE/SEL labels and logging LED, **swipe** dots. Rebuild from [specs/afr-face.md](specs/afr-face.md).

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
| `specs/spec.md` | Product requirements |
| `specs/afr-face.md` | AFR screen contract |
| `specs/lexicon.md` | Phrase book |
| `mockup/` | Host AFR face mockup + unit tests |
| `firmware/` | ESP-IDF app (plate) |
| `host/` | C host tests |
| `install/` | Update-path notes |
