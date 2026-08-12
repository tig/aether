# Aether — product requirements

**Rev 0.2 · July 2026**  
**Writing mode:** Technical (STE bias). See machine guide *writing-in-tigs-voice.md*.

Aether is a serial and CANbus ECU monitor, logger, and real-time AFR gauge on a pocket edge device.

This file is the product-level contract. It states mission, target hardware, and value requirements.

Screen layout lives in [afr-face.md](afr-face.md). Do not put face geometry in this file.

---

## Spec map

| Spec | Scope |
|------|--------|
| **[specs/spec.md](spec.md)** (this file) | Product mission, hardware target, value requirements (HW + SW) |
| **[specs/afr-face.md](afr-face.md)** | AFR screen only: layout, dial, type, RPM/TPS on that face |
| **[specs/lexicon.md](lexicon.md)** | Face and product phrase book |
| **[specs/comms.md](comms.md)** | ECU + host comms: client path, agent bridge, tool passthrough, built-in topology |
| *future* `specs/logging.md` | Logging, review, export, analysis |
| *future* `specs/setup.md` | First-run, profiles, fuels, alarms config |

Root [spec.md](../spec.md) is a short pointer into this tree.

---

## 1. Mission

Aether must:

1. Exchange data with the ECU and related sensors over serial and/or CANbus (and dedicated wideband inputs when fitted).
2. Log time-aligned channel streams for later review.
3. Show mixture and context on a small AMOLED so the operator can read them at a glance.

A bare AFR digit without context has low value. Aether must present AFR with engine context and keep logs that support diagnosis and tuning.

**Status of this checkout:** The host mockup and plate bootstrap prove the AFR screen and simulated RPM/TPS. Live protocols, dual wideband on metal, and full logger analysis are product intent. Track each layer in §6.

---

## 2. Target hardware (chosen device)

| Fact | Value |
|------|--------|
| Role | General Contact Unit (GCU); one shippable edge product |
| Board class | ESP32-S3 1.8″ AMOLED (Amazon ASIN [B0F242GFHK](https://www.amazon.com/dp/B0F242GFHK) / ESP32-S3-Touch-AMOLED-1.8) |
| MCU | ESP32-S3R8 (typical of class) |
| Display | 1.8″ AMOLED capacitive touch, native **368 × 448** |
| Panel / touch | SH8601 (QSPI), FT3168 (I2C) |
| USB | Type-C (CDC / flash / power) |
| Hard controls | Physical buttons beside USB (PWR/BOOT-class). Product UI is landscape with those keys on the top edge. On-screen MODE/SEL are labels, not soft buttons. |
| Runtime (v1 path) | C / ESP-IDF via silico `gcu-c` plate |
| Host spine | [Silico](https://github.com/tig/silico); sibling layout with local clone pin |

### Product UI orientation

- Logical face: **448 × 368** landscape (native panel rotated so USB and hard buttons are on top).
- Host mockup and metal UI must use that orientation unless a later setup mode allows portrait.

### Open hardware questions (do not invent answers)

- On-board vs external CAN transceiver for this SKU.
- Wideband controller: external module(s) over serial/CAN vs analog only.
- Logger media: internal flash, SD, host pull, or combination.
- Dual-channel wideband: one device vs two inputs.

---

## 3. Making the display useful and valuable

### 3.1 Contextual data (highest priority)

**Hardware**

- Aether must accept or generate synchronized inputs for at least: engine speed (**RPM**), **load** (MAP, **TPS**, or calculated load), and preferably fuel pressure (or differential fuel pressure on boosted engines).
- Dual (or more) wideband channels are strongly preferred for bank-to-bank or cylinder-group comparison.
- When Aether is a source, it must offer clean, low-latency outputs: analog 0–5 V (or 0–1 V), **CAN**, or **serial**, so the signal can log with ECU data.

**Software / display logic**

- Aether must present real-time AFR/λ with corresponding **RPM** and **load** (TPS/MAP/load), or map them onto fuel-table axes when the operator reviews logs.
- Logged data must be time-aligned so AFR can overlay RPM, load, TPS, fuel pressure, knock, EGT, and similar channels.
- When the ECU exposes them, Aether must be able to show short-term fuel trims (or closed-loop correction %). Measured λ can look correct while the base table is wrong.

**Current mockup slice:** The AFR face shows live **RPM** and **TPS** under the dial (simulated). Full multi-channel sync is product intent.

### 3.2 Units and scaling flexibility

**Hardware / controller**

- Native support for both **lambda** and **AFR**.
- Operator-selectable stoichiometric factor (14.7, 14.1, 9.8, custom, …) so the same sensor works across gasoline, E10, E85, methanol, and race fuels.
- Prefer output of raw lambda (or one consistent scale) so downstream tools do not invent conversion errors.

**Software**

- Instant switch between lambda and AFR views.
- Ability to lock the **display** to gasoline-scale AFR even on ethanol blends (tuner familiarity) while computing internally in λ.
- Configurable display range (e.g. 10–18 AFR or 0.70–1.30 λ) so the useful window fills the dial.

### 3.3 Visual design and glanceability

**Hardware (screen)**

- High-contrast AMOLED readable in sun and night (auto-dimming or operator brightness).
- Prefer a large digital value plus an analog-style arc/bar over digits alone.
- Configurable color coding: green ≈ on target, yellow ≈ approaching limits, red ≈ dangerous lean under load (or rich under defined conditions).
- Mounting and orientation that keep the face in primary or secondary FOV.

**Software**

- Configurable color thresholds by operating condition (idle vs WOT lean limits differ).
- Optional target-band visualization (distance from desired mixture for current load/RPM).
- Minimal clutter. Critical info (current value + safety status) must be readable in under 0.5 s.

Screen layout for the main AFR page: [afr-face.md](afr-face.md).

### 3.3.1 Legibility floors (hard rules on this device)

This face is about 1.8″. Text that looks fine when zoomed on a desktop can be unusable in the car.

**Label floor**

- The font size for **banner button labels** (MODE / SEL) is the base floor for face chrome text.
- **Legends** (value legend, dial legend, RPM/TPS captions, and similar captions) must be at least 25% larger than that banner size. That larger size is the legend minimum. Do not shrink legends below it.
- If a string cannot fit at its required floor without clipping, overlapping, or abbreviating into gibberish, it must not stay on the face. Redesign the layout or drop the label.

**Value floors (do not regress)**

- **Primary value** (dominant live number on a screen; on the AFR screen, the AFR **value**) must never be smaller than the current shipping primary size. Reference at 448×368: ≥ 82 device pixels high (mockup-tuned). Later screens with a different primary number must keep their primary at least this large unless the product explicitly re-baselines.
- **Secondary values** (supporting live numbers on the same face; on the AFR screen, **RPM** and **TPS**/WOT) must never be smaller than the current shipping secondary size. Reference at 448×368: ≥ 53 device pixels high.
- **Legends** must stay at least 25% larger than banner label size. That is the legend floor.
- Primary must remain clearly larger than secondary. Both must remain clearly larger than the label floor.
- Always judge legibility at physical size (mockup ~1.8″ diagonal), not only at full-screen browser zoom.
- Shrinking primary or secondary to make room for more chrome is a **spec violation**.

### 3.4 Temporal features (response, history, statistics)

**Hardware / controller**

- Sensor plus path must be fast enough for tip-in and gear-change transients. Target end-to-end latency under 30–50 ms where the path allows.
- Operator-adjustable filtering / smoothing on the displayed stream (raw for diagnosis, filtered while driving).

**Software**

- Peak-hold and valley-hold with manual or automatic reset.
- Rolling min / max / average over selectable windows (1 s, 5 s, full pull, …).
- Ability to mark or flag events (lean spike, tip-in, shift cut) for later review.
- Configurable display update rate independent of log rate (operator sees a usable number; logger keeps high resolution).

### 3.5 Warning and safety systems

**Hardware**

- Configurable visual (and preferably audible) alarm for lean under load.
- Clear sensor validity / heater / error indication so a bad reading is never trusted.

**Software**

- Multi-condition alarms (e.g. λ > 0.92 while MAP > 90 kPa and RPM > 3500).
- Persistent or latching warnings that require acknowledgment.
- Optional soft limits (color / flash) before hard alarms.

### 3.6 Logging, review, and analysis

**Hardware**

- Enough buffering or continuous high-rate output that aggressive driving does not drop samples.
- Easy export path (SD, USB, Bluetooth, Wi-Fi, or direct ECU logging).

**Software**

- Time-synchronized multi-channel logging (AFR/λ + RPM + load + other sensors).
- Graphing with overlay of AFR against fuel-table axes.
- Correction factors (measured ÷ target) and export of adjusted tables or notes.
- Session management: multiple runs, notes, weather/conditions metadata.
- Simple playback with cursors for scrubbing a pull.

Detail for this area belongs in a future `specs/logging.md`.

### 3.7 Multi-sensor and system integration

**Hardware**

- At least two independent wideband channels with independent calibration and display (preferred).
- Clean integration with standalone ECUs, loggers, and phone apps (**CAN preferred** over analog where possible).

**Software**

- Bank-to-bank difference display and alerting.
- Average multiple sensors or show side-by-side.
- Optional closed-loop trim overlay when the ECU is correcting live.

### 3.8 Usability and reliability

- Startup must not require special driver rituals under normal use.
- Clear “heating / not valid yet” state.
- Robustness to automotive electrical noise and voltage swing.
- Saved/restored profiles (fuel, car, tuning goal).
- Minimal operator workload once configured.

---

## 4. Priority summary

### Must-have for any serious system

- Contextual data (**RPM + load** alongside AFR).
- Lambda + configurable AFR.
- Fast response with adjustable filtering.
- Peak/min/max and basic logging.
- Configurable lean-under-load warning.
- Readable, color-coded display.

### Highly valuable

- Dual-channel support.
- Full synchronized logging + graphing against fuel-table axes.
- Condition-based alarms.
- Fuel pressure correlation.
- Easy export and correction-factor tools.

### Nice-to-have / differentiating

- Advanced analytics, automatic lean-spike detection, multi-session comparison, companion apps, cloud sync, pressure-compensated readings, and similar features.

Systems that meet **must-have** and **highly valuable** items turn oxygen measurement into a diagnostic and tuning instrument. Everything else is secondary.

---

## 5. Runtime and delivery shape

| Layer | Choice |
|-------|--------|
| Language / toolchain | C, ESP-IDF |
| Plate | silico `gcu-c` |
| Host gate | cmake host tests + `silico gate` |
| Product face (AFR) | [afr-face.md](afr-face.md) + `mockup/` |

---

## 6. Honest readiness (this checkout)

| Layer | Status |
|-------|--------|
| Product requirements (this doc) | In progress |
| Host AFR face mockup + unit tests | In scope / present |
| Live CAN / serial ECU path | Not done |
| Metal AMOLED product face | Not done |
| Durable multi-channel logger + review UI | Not done |

---

## 7. Open questions

- First ECU protocol slice (OBD ISO-TP, manufacturer CAN, …)?
- Wideband front-end: which modules and how many channels on day one?
- Logger media and export path for v1?
- Hard-button semantics for MODE / SEL beyond banner labels?
- Default fuel scale and display range for first ship?

---

## 8. Related artifacts

| Path | Role |
|------|------|
| `mockup/` | Host-runnable AFR face (simulated AFR, RPM, TPS) |
| `docs/images/afr-face-mockup.gif` | Visual target for the AFR screen |
| `firmware/`, `host/` | C plate (identity, host tests) |
| [README.md](../README.md) | Human entry (Narrative vision + Technical setup) |
