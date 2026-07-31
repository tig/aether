# Aether — product requirements

**Rev 0.3 · July 2026**  
**Writing mode:** Technical (STE bias). See machine guide *writing-in-tigs-voice.md*.

Aether is a CANbus and serial monitor, logger, and real-time AFR gauge for cars that run an **open-source or standalone ECU**.

This file is the product-level contract. It states mission, target ECU class, target hardware, and value requirements.

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
| [docs/research/canbus-ecu.md](../docs/research/canbus-ecu.md) | **Non-normative** — how open ECUs implement CAN; evidence behind §1.1 and §2 |

Root [spec.md](../spec.md) is a short pointer into this tree.

---

## 1. Mission

Aether must:

1. Exchange data with an **open-source or standalone ECU** over CANbus and/or serial.
2. Log time-aligned channel streams for later review.
3. Show mixture and context on a display so the operator can read them at a glance.
4. Hand a host LLM the logs and the full calibration, and apply reviewed, human-confirmed edits back to the ECU.

A bare AFR digit without context has low value. Aether must present AFR with engine context and keep logs that support diagnosis and tuning.

**Status of this checkout:** The host mockup and plate bootstrap prove the AFR screen and simulated RPM/TPS. Live protocols and full logger analysis are product intent. Track each layer in §6.

### 1.1 Target ECU class (normative)

Aether targets ECUs whose calibration and live data are **openly documented and openly addressable**. That property, not the vehicle, defines the product.

| Class | Examples | Support |
|-------|----------|---------|
| **Primary** | **FOME**, **rusEFI** | Full: face, logger, calibration read/write, burn |
| **Secondary** | Speeduino, MegaSquirt-class | Face and logger. Calibration support follows the ECU's own capability |
| **Out of scope** | OEM ECUs (Siemens MSS5x, Bosch ME/MS, and similar) | None |

Rationale, with wire-level evidence, is in [docs/research/canbus-ecu.md](../docs/research/canbus-ecu.md). In summary:

- Open ECUs **broadcast** every face channel — RPM, load, **λ**, and fuel trims — on CAN with a published definition file, so the face and logger need no polling and no proprietary front end.
- Open ECUs expose the **same command set on CAN as on serial**, so calibration read, write, and burn work over either transport with one protocol stack.
- OEM ECUs offer neither. They broadcast a thin fixed channel set with no λ, and their calibration lives behind a vendor-specific, engine-off, whole-image reflash. Supporting them would require a second transport, a second calibration model, and a second definition format, and would still not deliver the acceptance narrative.

### 1.2 Non-goals (normative)

Aether **must not**:

1. Read or write OEM ECU calibrations, or implement OEM diagnostic protocols to do so.
2. Update ECU **firmware**. Calibration burn is in scope; bootloaders are not.
3. Originate any CAN frame that requests or controls a vehicle function. Aether observes; it does not actuate.
4. Write to an ECU without an explicit human confirmation for that write.

---

## 2. Target hardware

### 2.1 Integration rule (normative)

A shippable Aether **must** be assembled from **off-the-shelf hardware with no soldering and no custom PCB**. Wiring to the car must be limited to screw terminals or keyed connectors: 12 V, ground, CAN HIGH, CAN LOW.

Therefore the target board **must** provide, on one part:

| Requirement | Reason |
|-------------|--------|
| Display + capacitive touch | §3.3 face |
| **CAN transceiver on board**, with **selectable termination, off by default** | §1.1 primary transport. A third terminator on a healthy two-node bus degrades it |
| **SD card** slot | §3.6. At 30 channels × 4 bytes × 50 Hz a log consumes ≈ 21 MB/h; 16 MB of internal flash holds under an hour |
| **Wide DC input (12 V nominal)** with automotive tolerance | The device is powered by the car, not by a bench USB port |
| Enclosure available | §3.8 |
| ESP32-S3 class or better | §2.4 performance floor |

An external wideband front end is **not** required, because primary-class ECUs already publish λ (§1.1). Aether may add one later; it must not be a condition of v1.

### 2.2 Development board (present)

| Fact | Value |
|------|--------|
| Board | ESP32-S3-Touch-AMOLED-1.8 (Waveshare; also sold as UeeKKoo, ASIN [B0F242GFHK](https://www.amazon.com/dp/B0F242GFHK)) |
| Display | 1.8″ AMOLED capacitive touch, native **368 × 448**, SH8601 (QSPI) + FT3168 (I2C) |
| Role | Face development and firmware bring-up **only** |
| Limit | Exposes 7 GPIO + I2C + UART + USB pads. CAN, SD, and a 12 V front end together exceed that budget, and none are on board. **Not a shipping candidate** |

### 2.3 Integrated candidate (on the bench — evaluation)

| Fact | Value |
|------|--------|
| Board | **Waveshare ESP32-S3-Touch-LCD-4.3B**, cased (Waveshare SKU `ESP32-S3-Touch-LCD-4.3B-BOX`; also sold as ASIN [B0DD6VLH1Y](https://www.amazon.com/dp/B0DD6VLH1Y)) |
| MCU | ESP32-S3, 16 MB flash, 8 MB PSRAM, Wi-Fi 4 + BLE 5 |
| Display | 4.3″ IPS 800 × 480, 5-point capacitive touch |
| CAN | On board, CAN 2.0. **GPIO15 = TX, GPIO16 = RX.** Screw terminal. **Termination switch fitted, off by default** |
| Storage | TF card slot, SPI — GPIO11 MOSI, GPIO12 SCK, GPIO13 MISO, **CS via the CH422G expander (EXIO4)** |
| Power | **7–36 V DC** terminal, plus Type-C 5 V and a LiPo header with charging |
| Spare I/O | RS485 terminal (GPIO43/44); optoisolated 5–36 V digital in and out |
| Car wiring | 12 V (ignition-switched), ground, CAN HIGH, CAN LOW. **Four screw terminals, no soldering** |

This board satisfies every line of §2.1 as shipped. Two constraints follow from the silicon and the panel:

- **One CAN bus.** The ESP32-S3 has a single TWAI controller. Adding a second transceiver does not add a second bus. Where an ECU runs two buses, this board must tap one.
- **The termination switch is the node-role control.** It **must** be off when the bus already has two terminated nodes, and on only when the ECU is the sole other node. Measure before deciding (60 Ω / 120 Ω / open).

Status stays **evaluation** until both of these pass:

1. **Sun legibility.** IPS is not AMOLED. The face must be judged in a car, in daylight, at physical size. This is the single largest risk to adoption.
2. **Face portability.** The AFR face is tuned to 448 × 368. Legibility floors in §3.3.1 are stated in device pixels at that geometry and **must** be re-derived for 800 × 480, not scaled blindly.

Adoption is an [issue #12](https://github.com/tig/aether/issues/12) decision, not a §2 assertion. Boards that also satisfy §2.1 — for example an M5Stack controller with a Grove CANBus Unit and a 12 V supply — remain valid alternatives if evaluation fails.

### 2.4 Runtime

| Fact | Value |
|------|--------|
| Role | General Contact Unit (GCU); one shippable edge product |
| Runtime (v1 path) | C / ESP-IDF via silico `gcu-c` plate |
| Host spine | [Silico](https://github.com/tig/silico); sibling layout with local clone pin |
| Hard controls | Physical buttons. On-screen MODE/SEL are labels, not soft buttons |

### 2.5 Product UI orientation

- Logical face: **448 × 368** landscape on the §2.2 development board (native panel rotated so USB and hard buttons are on top).
- Host mockup and metal UI must use landscape unless a later setup mode allows portrait.
- Face layout code must not hard-code one panel geometry. §2.1 permits any qualifying board, and §2.3 changes the aspect ratio.

### 2.6 Performance floor

Dual-core 240 MHz, 8 MB PSRAM, 16 MB flash, Wi-Fi + BLE, no graphics accelerator beyond DMA. Any board that matches or beats this profile **and** satisfies §2.1 is a legitimate target. Neither ESP32-S3 nor ESP32-P4 supports CAN FD; no ECU in §1.1 requires it.

### 2.7 Open hardware questions (do not invent answers)

- Sun legibility of an IPS panel on the face (§2.3).
- Whether one CAN controller is enough, or a second bus is needed where the ECU runs two.
- Clock source for drive tagging: RTC module, host sync, or ECU uptime.
- Graceful log close on power loss: supercap, LiPo header, or filesystem strategy.
- Mounting and enclosure for a 4.3″ device in a car interior.

---

## 3. Making the display useful and valuable

### 3.1 Contextual data (highest priority)

**Hardware**

- Aether must accept synchronized inputs for at least: engine speed (**RPM**), **load** (MAP, **TPS**, or calculated load), and **λ**.
- On a primary-class ECU (§1.1) all of these arrive on one CAN broadcast, already time-aligned by the ECU. Aether must consume that broadcast rather than duplicate the sensors.
- Dual wideband channels are preferred where the ECU publishes both.
- Aether must not require an external wideband front end for v1 (§2.1).

**Software / display logic**

- Aether must present real-time AFR/λ with corresponding **RPM** and **load** (TPS/MAP/load), or map them onto fuel-table axes when the operator reviews logs.
- Logged data must be time-aligned so AFR can overlay RPM, load, TPS, fuel pressure, knock, EGT, and similar channels.
- Aether must show **short-term fuel trims** (or closed-loop correction %). Measured λ can look correct while the base table is wrong. Primary-class ECUs publish trims in the same broadcast as λ, so this is a decode requirement, not a sensing one.

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

- Two wideband channels where the ECU publishes both (λ1 / λ2).
- Clean integration with standalone ECUs, loggers, and phone apps. **CAN is the preferred transport**; serial is the fallback where an ECU does not carry the needed service on CAN.

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
| CAN broadcast decode (face + logger) | Not done — [#12](https://github.com/tig/aether/issues/12) hardware, [#5](https://github.com/tig/aether/issues/5) decode |
| Calibration read/write + burn over CAN or serial | Not done — [#4](https://github.com/tig/aether/issues/4) |
| Serial ECU path (USB / UART) | Not done — [#5](https://github.com/tig/aether/issues/5) |
| Integrated hardware selection (§2.1) | Not done — [#12](https://github.com/tig/aether/issues/12) |
| Metal product face | Not done |
| Durable multi-channel logger + review UI | Not done |

---

## 7. Open questions

Answered since rev 0.2, with the reasoning in [docs/research/canbus-ecu.md](../docs/research/canbus-ecu.md): first protocol slice (**CAN broadcast, then TS-over-ISO-TP for calibration**); wideband front end (**none for v1 — λ comes from the ECU**); logger media (**SD, per §2.1**); on-board vs external CAN transceiver (**on-board, per §2.1**).

Still open:

- Hard-button semantics for MODE / SEL beyond banner labels?
- Default fuel scale and display range for first ship?
- Face geometry on a 4.3″ 800 × 480 panel (§2.3) — re-derive the §3.3.1 floors.
- Does the operator's pilot car expose CAN on an accessible connector, and on which bus?
- Export path for logs: SD removal, USB pull, or wireless only?

---

## 8. Related artifacts

| Path | Role |
|------|------|
| `mockup/` | Host-runnable AFR face (simulated AFR, RPM, TPS) |
| `docs/images/afr-face-mockup.gif` | Visual target for the AFR screen |
| `firmware/`, `host/` | C plate (identity, host tests) |
| [README.md](../README.md) | Human entry (Narrative vision + Technical setup) |
