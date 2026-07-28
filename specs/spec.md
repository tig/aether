# Aether — product requirements

**Rev 0.1 · July 2026**

Aether is a **serial & CANbus ECU monitor, logger, and real-time AFR gauge** for a pocket edge device. This document is the **product-level** contract: mission, target hardware, what makes the system *useful* (not just a raw oxygen number), and how other specs fit together.

Screen-specific layout lives elsewhere (see [Spec map](#spec-map)). Do not dump face geometry into this file.

---

## Spec map

| Spec | Scope |
|------|--------|
| **[specs/spec.md](spec.md)** (this file) | Product mission, hardware target, value requirements (HW + SW) |
| **[specs/afr-face.md](afr-face.md)** | **AFR screen only** — layout, dial, type, RPM/TPS on that face |
| **[specs/lexicon.md](lexicon.md)** | Face and product phrase book |
| *future* `specs/logging.md` | Logging, review, export, analysis |
| *future* `specs/setup.md` | First-run, profiles, fuels, alarms config |
| *future* `specs/inputs.md` | Serial / CAN / sensor wiring and identity |

Root [spec.md](../spec.md) is a short seed pointer into this tree (for silico-style “product truth at HEAD”).

---

## 1. Mission

On the workbench and in the vehicle, Aether should:

1. **Talk** to the ECU and related sensors over **serial** and/or **CANbus** (and dedicated wideband inputs where fitted).
2. **Log** time-aligned streams for later review.
3. Show **glanceable, high-value** mixture and context on a tiny AMOLED — not a naked AFR digit with no context.

A raw AFR number is **low-value**. High-value systems turn continuous oxygen measurement into **actionable insight** for diagnosis and tuning. The requirements below separate a mediocre gauge from a tool people actually rely on.

**Honest status of this repo:** host mockup + plate bootstrap prove the AFR **screen** and simulated context (RPM/TPS). Live protocols, dual wideband metal, and full logger analysis are product intent; track readiness honestly by layer.

---

## 2. Target hardware (chosen device)

| Fact | Value |
|------|--------|
| Role | General Contact Unit (GCU) — one shippable edge product |
| Board class | ESP32-S3 1.8″ AMOLED (Amazon ASIN [B0F242GFHK](https://www.amazon.com/dp/B0F242GFHK) / ESP32-S3-Touch-AMOLED-1.8) |
| MCU | ESP32-S3R8 (typical of class) |
| Display | 1.8″ AMOLED capacitive touch, native **368 × 448** |
| Panel / touch | SH8601 (QSPI), FT3168 (I2C) |
| USB | Type-C (CDC / flash / power) |
| Hard controls | Physical buttons beside USB (PWR/BOOT-class) — product UI is **landscape** with those keys on the **top** edge; on-screen MODE/SEL are **labels**, not soft buttons |
| Runtime (v1 path) | **C / ESP-IDF** via silico `gcu-c` plate |
| Host spine | [Silico](https://github.com/tig/silico); sibling layout with local clone pin |

### Product UI orientation

- **Logical face:** **448 × 368** landscape (native panel rotated so USB + hard buttons are on top).
- Host mockup and metal UI should match that orientation unless a later setup mode explicitly allows portrait.

### Open hardware questions (do not invent answers)

- On-board vs external CAN transceiver for this SKU.
- Wideband controller: external module(s) over serial/CAN vs analog only.
- Logger media: internal flash, SD, host pull, or combination.
- Dual-channel wideband: one device vs two inputs.

---

## 3. Making the display useful and valuable

### 3.1 Contextual data (highest priority)

**Hardware**

- Must accept or generate **synchronized** inputs for at least: **engine speed (RPM)**, **load** (MAP, **TPS**, or calculated load), and preferably **fuel pressure** (or differential fuel pressure on boosted engines).
- **Dual (or more) wideband channels** strongly preferred for bank-to-bank or cylinder-group comparison.
- Clean, low-latency outputs where Aether is a source: analog 0–5 V (or 0–1 V), **CAN**, or **serial** so the signal can be logged alongside ECU data.

**Software / display logic**

- Real-time AFR/λ presented **with** corresponding **RPM** and **load** (TPS/MAP/load) — or mapped onto fuel-table axes when reviewing logs.
- Logged data **time-aligned** so AFR can be overlaid on RPM, load, TPS, fuel pressure, knock, EGT, etc.
- Ability to show **short-term fuel trims** (or closed-loop correction %) when available — measured λ can look perfect while the base table is wrong.

**Current mockup slice:** AFR face shows live **RPM** and **TPS** under the dial (simulated). Full multi-channel sync is still product intent.

### 3.2 Units and scaling flexibility

**Hardware / controller**

- Native support for both **Lambda** and **AFR**.
- User-selectable stoichiometric factor (14.7, 14.1, 9.8, custom, …) so the same sensor works across gasoline, E10, E85, methanol, race fuels.
- Prefer outputting **raw lambda** (or one consistent scale) so downstream tools do not invent conversion errors.

**Software**

- Instant switch between Lambda and AFR views.
- Ability to lock the **display** to gasoline-scale AFR even on ethanol blends (tuner familiarity) while computing internally in λ.
- Configurable display range (e.g. 10–18 AFR or 0.70–1.30 λ) so the useful window fills the dial.

### 3.3 Visual design and glanceability

**Hardware (screen)**

- High-contrast AMOLED readable in sun and night (auto-dimming or user brightness).
- Prefer **large digital value + analog-style arc/bar** over pure digits alone.
- Configurable color coding: green ≈ on target, yellow ≈ approaching limits, red ≈ dangerous lean under load (or rich under defined conditions).
- Mounting / orientation that keeps the face in primary or secondary FOV without head gymnastics.

**Software**

- Configurable color thresholds by **operating condition** (idle vs WOT lean limits differ).
- Optional **target band** visualization (how far from desired for current load/RPM).
- Minimal clutter — critical info (current value + safety status) readable in **&lt; 0.5 s**.

**Screen layout detail** for the main AFR page: [afr-face.md](afr-face.md).

### 3.3.1 Legibility floors (hard rules on this device)

This is a **~1.8″** face. Text that looks fine when zoomed on a desktop can be unusable in the car.

**Label floor**

- The font size used for **banner button labels** (MODE / SEL) is the base floor for face chrome text.
- **Legends** (value legend, dial legend, RPM/TPS captions, and any similar captions) must be **at least 25% larger** than that banner size. That larger size is the **legend minimum** — do not shrink legends below it.
- If a string cannot fit at its required floor without clipping, overlapping, or abbreviating into gibberish, **it does not belong on the face** — redesign the layout or drop the label.

**Value floors (do not regress)**

- **Primary value** (the dominant live number on a screen — on the AFR screen, the AFR **value**) must **never be smaller** than the current shipping primary size. Reference at 448×368: **≥ 82 device pixels** high (mockup-tuned). Later screens with a different primary number (e.g. a dedicated RPM page) must keep their primary at least this large unless the product explicitly re-baselines.
- **Secondary values** (supporting live numbers on the same face — on the AFR screen, **RPM** and **TPS**/WOT) must **never be smaller** than the current shipping secondary size. Reference at 448×368: **≥ 48 device pixels** high.
- Primary must remain **clearly larger** than secondary; both must remain **clearly larger** than the label floor.
- Always judge legibility at **physical size** (mockup ~1.8″ diagonal), not only at full-screen browser zoom.
- Shrinking primary/secondary to “make room” for more chrome is a **spec violation**, not a fix.

### 3.4 Temporal features (response, history, statistics)

**Hardware / controller**

- Sensor + path fast enough for tip-in and gear-change transients (ideally &lt;30–50 ms end-to-end where possible).
- User-adjustable **filtering / smoothing** on the displayed stream (raw for diagnosis, filtered while driving).

**Software**

- Peak-hold and valley-hold with manual or automatic reset.
- Rolling min / max / average over selectable windows (1 s, 5 s, full pull, …).
- Ability to mark or flag events (lean spike, tip-in, shift cut) for later review.
- Configurable **display** update rate independent of **log** rate (driver sees a usable number; logger keeps high resolution).

### 3.5 Warning and safety systems

**Hardware**

- Configurable visual (and preferably audible) alarm for lean under load.
- Clear **sensor validity / heater / error** indication so a bad reading is never trusted.

**Software**

- Multi-condition alarms (e.g. λ &gt; 0.92 while MAP &gt; 90 kPa and RPM &gt; 3500).
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

*Detail for this area belongs in a future `specs/logging.md`.*

### 3.7 Multi-sensor and system integration

**Hardware**

- At least **two** independent wideband channels with independent calibration and display (preferred).
- Clean integration with standalone ECUs, loggers, and phone apps (**CAN preferred** over analog where possible).

**Software**

- Bank-to-bank difference display and alerting.
- Average multiple sensors or show side-by-side.
- Optional closed-loop trim overlay when the ECU is correcting live.

### 3.8 Usability and reliability

- Startup that does not require special driver rituals under normal use.
- Clear “heating / not valid yet” state.
- Robustness to automotive electrical noise and voltage swing.
- Saved/restored **profiles** (fuel, car, tuning goal).
- Minimal driver workload once configured.

---

## 4. Priority summary

### Must-have for any serious system

- Contextual data (**RPM + load** alongside AFR)
- Lambda + configurable AFR
- Fast response with adjustable filtering
- Peak/min/max and basic logging
- Configurable lean-under-load warning
- Readable, color-coded display

### Highly valuable

- Dual-channel support
- Full synchronized logging + graphing against fuel-table axes
- Condition-based alarms
- Fuel pressure correlation
- Easy export and correction-factor tools

### Nice-to-have / differentiating

- Advanced analytics, automatic lean-spike detection, multi-session comparison, companion apps, cloud sync, pressure-compensated readings, etc.

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
| Product requirements (this doc) | **In progress** |
| Host AFR face mockup + unit tests | **In scope / present** |
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
| [README.md](../README.md) | Human entry |
