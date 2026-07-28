# Aether Software Specification (seed)

**Rev 0.1, July 2026 — spec-learning mockup**

Aether is a **serial & CANbus ECU monitor, logger, and real-time AFR gauge** for the **ESP32-S3 1.8″ AMOLED** touch board (Amazon ASIN **B0F242GFHK** / ESP32-S3-Touch-AMOLED-1.8 class).

This pass is intentionally thin: bootstrap the GCU after the [tig/xuss-c](https://github.com/tig/xuss-c) C/ESP-IDF plate model, and learn the **AFR product face** on the host with simulated data before locking full ECU/CAN domain moat.

## Mission (plain language)

On the workbench and in the vehicle, Aether should eventually:

1. **Talk** to the ECU over **serial** and/or **CANbus**.
2. **Log** streams for later review.
3. Show a **real-time air–fuel ratio (AFR)** gauge that a driver can read at a glance — circular arc of colored segments, numeric readout, familiar wideband scale.

**This revision does not implement live OBD/CAN or durable trip logging.** Those are product intent, not shipped behavior yet.

## Hardware (target)

| Fact | Value |
|------|--------|
| MCU | ESP32-S3R8 |
| Display | 1.8″ AMOLED touch, native **368×448**; product UI runs **landscape 448×368** with hard buttons on the top edge |
| Panel | SH8601 (QSPI) |
| Touch | FT3168 (I2C) |
| Link | USB Type-C (CDC) |
| Listing | [Amazon B0F242GFHK](https://www.amazon.com/dp/B0F242GFHK) |

## Product face (AFR gauge)

**Normative reimplementation contract:** [specs/afr-face.md](specs/afr-face.md)  
**Lexicon:** [specs/lexicon.md](specs/lexicon.md)

![Aether AFR face host mockup](docs/images/afr-face-mockup.gif)

Host mockup (`mockup/`) is the working reference for landscape 448×368 face layout, dial geometry, colors, and type. Agents rebuilding the face must follow **afr-face.md** and prove the result with `python -m mockup.capture` + visual inspect — not code-only claims.

Summary (see afr-face for numbers):

| Trait | Contract |
|-------|----------|
| Panel UI | Landscape **448×368**; native panel 368×448; hard buttons on **top** |
| Regions | **Banner** (MODE · log LED · SEL) + **dial** full width/height under banner + **swipe indicator** overlay |
| Dial | 35 segments, corner-to-corner (8 / 20 at bottom corners); constant band thickness |
| Value | Large one-decimal AFR + **AIR/FUEL RATIO** value legend |
| Bands | Red rich / green stoich / amber / red lean (thresholds in afr-face) |

## Runtime

- **Language:** C
- **Toolchain:** ESP-IDF
- **Plate:** silico `gcu-c` (host cmake tests + idf-flash deploy)

## Readiness layers (honest)

| Layer | This rev |
|-------|----------|
| Host plate / identity stubs | Scaffold present |
| Host AFR mockup + unit tests | **In scope** |
| Live CAN / serial ECU protocol | Out of scope |
| Metal AMOLED AFR face | Out of scope (learning only) |
| Trip logger storage | Out of scope |

## Acceptance (mockup)

1. Simulated AFR values map to lit arc segments + color band without a display (unit tests).
2. Graphical mockup shows arc, 8–20 scale marks, large center digits, AIR/FUEL RATIO label.
3. Changing simulated stream changes segment/readout state.

## Open questions (for later spec refinement)

- CAN bus transceiver hardware on this board or external?
- Which ECU protocols first (ISO-TP OBD, manufacturer CAN)?
- Logger media (SPIFFS / SD / host pull)?
- MODE cycles (LIVE / PEAK / AVG mockup) vs real product modes; SEL hold/freeze vs menu?
- Exact panel pixel size if not 1:1 square (letterbox vs stretch)?
- Lambda units toggle (AFR vs λ)?
