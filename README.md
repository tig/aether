# Aether

**Aether** is a complete open source solution for tuning cars with open source ECUs (FOME / rusEFI / Speeduino / MegaSquirt-class). It turns off-the-shelf **ESP32** hardware into an AFR gauge and logger that, once plugged into the ECU's USB port, is also a **remote programmer** — a calibration reader/writer built so an AI can read the logs and the full calibration and figure out the optimal way to fix a tuning problem or find real performance, not just display a number.

This repository is a product GCU (General Contact Unit) used with [Silico](https://github.com/tig/silico). Runtime target is **C / ESP-IDF** (same plate shape as [tig/xuss-c](https://github.com/tig/xuss-c)).

## Vision

A naked AFR digit is low-value. The product Aether is converging on, one layer at a time:

1. **Glanceable AFR gauge on cheap, off-the-shelf hardware** — dial + value + lambda + RPM/TPS on a small touch AMOLED, legible in a car at a glance ([specs/afr-face.md](specs/afr-face.md)). The **current bootstrap target** is one specific pocket ESP32-S3 1.8″ AMOLED board (below); the product intent is to run on a **wide range of ESP32 dev kits**, not lock to a single SKU. **This layer is the part that exists today**, as a host-runnable mockup on the bootstrap board.
2. **Live ECU link** — Aether as a client of the protocols open ECUs already speak (TunerStudio-compatible newserial: rusEFI / **FOME** / MegaSquirt / Speeduino), over **USB first**, then UART, then wireless. Pilot target is the operator's own **FOME**-based car, plugged into Aether over USB with no PC in the middle. Design: [issue #5](https://github.com/tig/aether/issues/5).
3. **Always-on logging** — logging starts by default, tags drives, and lets the operator drop voice/button **event marks** ("mark that lean spike") without ritual. Canonical on-device format is **MLVLG (`.mlg`)** so sessions open natively in MegaLogViewer, with **first-class export to Innovate LogWorks** so a remote tuner can open the file without installing Aether's own tools. Design: [issue #2](https://github.com/tig/aether/issues/2), [issue #3](https://github.com/tig/aether/issues/3).
4. **Remote programmer: full calibration read/write** — not just fuel maps: cold-start/cranking/ASE/WUE curves, idle, protections, every burnable scalar, table, and curve the ECU's definition exposes, modeled as a structured **Aether Tune Model (ATM)** with definition-pinned, backup-before-write, readback-verified, human-gated burns. Design: [issue #4](https://github.com/tig/aether/issues/4).
5. **Bridge the car to AIs** — Aether as a BT/Wi-Fi bridge so an operator can hand a host LLM the logs, marks, and full calibration — the complete picture an AI needs to reason about a tuning problem — and get back a proposed, reviewable, human-confirmed edit rather than a raw number to interpret themselves. Design: [issue #1](https://github.com/tig/aether/issues/1).

The acceptance narrative these converge on: **log a bad cold start on the FOME car → hand an LLM the log + full calibration → it proposes a scoped patch to cranking/ASE/WUE (not just the VE table) → human applies, verifies, and burns → next cold start confirms the fix** ([issue #4](https://github.com/tig/aether/issues/4) §18).

## Status

**Spec-learning mockup (this pass).** Host-runnable AFR screen with **simulated** AFR, RPM, and TPS — not live OBD/CAN, not full metal product acceptance. Layers 2–5 above are **planning specs only** (linked issues), not implemented; track readiness honestly by layer rather than assuming the roadmap is shipped.

| Layer | Status |
|-------|--------|
| AFR face (host mockup) | **In scope / present** |
| Live serial/USB ECU link ([#5](https://github.com/tig/aether/issues/5)) | Planning spec only |
| Always-on multi-channel logging ([#2](https://github.com/tig/aether/issues/2), [#3](https://github.com/tig/aether/issues/3)) | Planning spec only |
| Full calibration R/W + burn validation ([#4](https://github.com/tig/aether/issues/4)) | Planning spec only |
| Wireless LLM host bridge ([#1](https://github.com/tig/aether/issues/1)) | Idea / not designed in a spec yet |
| Metal AMOLED product face | Not done |

## Specs

| Document | Scope |
|----------|--------|
| **[specs/spec.md](specs/spec.md)** | Product requirements: mission, device, what makes AFR **useful** (context, units, logging, alarms, …) |
| **[specs/afr-face.md](specs/afr-face.md)** | **AFR screen only** — layout, dial, type, on-screen RPM/TPS |
| **[specs/lexicon.md](specs/lexicon.md)** | Face phrase book |
| [spec.md](spec.md) | Short seed pointer → `specs/` |
| *planned* `specs/inputs.md` | Live serial/USB ECU channel model — spec lives in [issue #5](https://github.com/tig/aether/issues/5) until implementation ships it |
| *planned* `specs/logging.md` | Log format, markers, LogWorks/MLV export — spec lives in [issue #3](https://github.com/tig/aether/issues/3) until implementation ships it |
| *planned* `specs/maps.md` (or `tune.md`) | Full calibration R/W, ATM/AMP/TunePatch, burn validation — spec lives in [issue #4](https://github.com/tig/aether/issues/4) until implementation ships it |

Host path: [install/README.md](install/README.md).

## Roadmap (open issues)

Each issue below carries a full planning spec in its body — that spec becomes the matching `specs/*.md` file (and this table can shrink) once an implementation PR actually ships the behavior. Until then, the issue is the product truth for that layer, not code.

| Issue | Title | Feeds |
|-------|-------|-------|
| [#1](https://github.com/tig/aether/issues/1) | Direct wireless bridge to a host LLM (logs + marks + calibration in, reviewed edits out) | Wireless host bridge |
| [#2](https://github.com/tig/aether/issues/2) | Always be logging, with drive tagging and voice/button event marks | → `specs/logging.md` |
| [#3](https://github.com/tig/aether/issues/3) | Log format strategy: MLVLG canonical, LogWorks/MLV/CSV/JSON export | → `specs/logging.md` |
| [#4](https://github.com/tig/aether/issues/4) | Full ECU calibration read/write (tables, curves, scalars) + burn validation | → `specs/maps.md` |
| [#5](https://github.com/tig/aether/issues/5) | Real-time ECU data formats & serial protocols (USB-first, FOME pilot) | → `specs/inputs.md` |

## Hardware

**Current bootstrap board** — first target while the software is still being learned/built; not the only board Aether intends to support (see [Vision](#vision) #1):

| Item | Detail |
|------|--------|
| Board | ESP32-S3R8, 1.8″ AMOLED 368×448, SH8601 (QSPI), FT3168 (I2C touch), Type-C USB |
| Class | ESP32-S3-Touch-AMOLED-1.8 (Amazon ASIN [B0F242GFHK](https://www.amazon.com/dp/B0F242GFHK)) |
| Product role | ECU monitor, logger, and calibration tool over serial/USB (CANbus reserved for later); real-time AFR gauge face |
| UI orientation | Landscape **448×368** (hard buttons + USB on top) |

**Longer term:** a wide range of off-the-shelf ESP32 kits (display shapes/sizes vary) rather than a single locked SKU — display layout code should stay portable rather than hard-baked to this one panel's geometry.

## AFR gauge mockup (host)

![Aether AFR face host mockup](docs/images/afr-face-mockup.gif)

Simulated landscape face: **dial**, large AFR **value** with **lambda** to the right, **RPM** / **TPS** (to **WOT**) below, **banner** with MODE/SEL labels and logging LED, **swipe** dots. Rebuild from [specs/afr-face.md](specs/afr-face.md).

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
