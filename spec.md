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
| Display | 1.8″ AMOLED touch; treat **product face as square** (layout for equal width/height; crop/letterbox if panel is slightly taller) |
| Panel | SH8601 (QSPI) |
| Touch | FT3168 (I2C) |
| Link | USB Type-C (CDC) |
| Listing | [Amazon B0F242GFHK](https://www.amazon.com/dp/B0F242GFHK) |

## Product face (AFR gauge) — mockup learnings

Reference visual: commercial 52 mm digital wideband (arc LEDs + 7-segment-style digits). Host mockup captures:

| Trait | Choice (mockup → refine) |
|-------|---------------------------|
| Scale | **8.0 – 20.0** AFR (gasoline lambda framing) |
| Stoich reference | ~**14.7** |
| Arc | Discrete **LED-style segments** around the dial |
| Color bands | **Green** near stoich / slightly rich-good; **amber** transition; **red** at rich and lean extremes |
| Center | Large **one-decimal** numeric AFR |
| Label | **AIR/FUEL RATIO** |
| Face shape | **Square** panel; LED outer **flush to display L/T/R**; **rounded-square** inner aperture (~71% half — band ~30% thinner than first full-flush ring) for a large AFR readout; outer longer toward corners |
| Caption | **AIR/FUEL RATIO** bottom-justified just above MODE/SEL |
| Stoich mark | Segment at **~14.7** stays slightly highlighted even when not fill-lit |
| Scale labels | Large readable ticks: **8 · 11 · 13 · 15 · 17 · 20** |
| MODE / SEL | Large bottom bar (~18% height), two equal hit targets flush L/R/B; labels **MODE** / **SEL** only (no LIVE/TAP subtext) |

### Color band map (shipped mockup logic)

| AFR range | Band | Meaning (operator) |
|-----------|------|---------------------|
| `< 11.5` | red | Rich |
| `11.5 – 15.0` | green | Good / stoich / slightly rich |
| `15.0 – 15.8` | amber | Lean of stoich |
| `> 15.8` | red | Lean |
| out of `[8, 20]` | invalid (clamped display, marked invalid) | Sensor/sim fault |

Segment count and exact thresholds are **mockup defaults** — refine after bench feel.

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
