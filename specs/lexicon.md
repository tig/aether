# Aether lexicon

**Rev 0.3 · July 2026** (draft — product + face + live/log/calibration)

Canonical terms for **user-facing copy**, **specs**, and **agent/implementer prose**. Prefer industry wording (TunerStudio / MegaLogViewer / MegaSquirt-family, FOME/rusEFI, Innovate LogWorks) over invented slang.

| Doc | Role |
|-----|------|
| [spec.md](spec.md) | Product requirements |
| [afr-face.md](afr-face.md) | AFR screen layout |
| Issues #3 / #4 / #5 | Planning notes only (non-canonical until matching `specs/*.md` ships with impl) |

**Schema for every term row:** one **Preferred** name; optional **Alias** (OK in operator copy); **Meaning**; **Avoid**. Do not list two Preferreds for one concept. Do not grow this into a glossary of every INI constant name.

---

## 1. Product and roles

| Preferred | Alias | Meaning | Avoid |
|-----------|-------|---------|--------|
| **Aether** | — | This product (device + software). | “the gauge” alone when product identity matters |
| **ECU** | — | Engine control unit that holds calibration and streams live data. | “computer,” “box” in specs |
| **operator** | user | Person using Aether in car or on bench. | — |
| **tuner** | — | Person or shop that analyzes logs / changes calibration (may not hold the device). | — |
| **host** | — | PC/phone/agent machine talking to Aether (USB/BT/Wi‑Fi). | “server” for the phone/PC side |
| **link session** | — | One continuous link to an ECU (transport + protocol session). | bare **session** in specs |
| **log session** | — | One continuous log file period (one MLG/MSL file from open to close/rotate). | bare **session** in specs |

Bare **session** is **Avoid** in specs unless the sentence has already fixed link vs log.

---

## 2. Mixture and engine context (face + live)

| Preferred | Alias | Meaning | Avoid |
|-----------|-------|---------|--------|
| **lambda** | λ | Excess-air ratio; **internal mixture truth** when both exist. AFR = λ × stoich. Channel / physics only — not face chrome. | Storing disagreeing AFR and λ as dual truths; using **lambda** for the face widget (use **lambda readout**) |
| **AFR** | — | Air–fuel ratio for **display** (often gasoline-scale even on other fuels). | Using “AFR” when you mean λ in protocols / storage |
| **stoich** | — | Stoichiometric AFR for the fuel scale in use (e.g. 14.7 gasoline). | Hard-coding 14.7 with no fuel context |
| **wideband** | — | Sensor/controller path that reports true λ/AFR (vs narrowband). | “O2” alone when wideband is meant |
| **RPM** | — | Engine speed. | “revs” in specs |
| **TPS** | — | Throttle position (%). | “throttle” alone when the channel is TPS |
| **MAP** | — | Manifold absolute pressure (prefer **kPa** in data). | PSI in internal channels without conversion note |
| **load** | — | Generic axis: TPS, MAP, or calculated load — say which when known. | Assuming load always means MAP |
| **CLT** | — | Coolant temperature. | “water temp” in channel IDs |
| **IAT** | — | Intake air temperature. | “air temp” in channel IDs |
| **WOT** | — | Wide-open throttle (**display label** when TPS ≈ 100%). | Replacing the TPS **channel** name with WOT in logs |

Face chrome: [§6](#6-afr-face-chrome). Chrome terms never name live **channels**.

---

## 3. Live link and protocols

| Preferred | Alias | Meaning | Avoid |
|-----------|-------|---------|--------|
| **live data** | realtime | Real-time channels while linked (gauges / face). | “stream” alone |
| **och** | output channels | ECU realtime block (TS INI `[OutputChannels]`). Prefer **och** in impl/code; long form OK in prose once. | Inventing a second name for the same bytes |
| **signature** | — | Firmware identity string used to select the correct definition. | “version” when you mean signature match |
| **definition** | INI, .ini, .ecu | ECU description file — pages, constants, scales, realtime. | “config file” for the INI |
| **pin** | — | Operator/trust binding: this **definition** is approved for live write on this **signature**. | Treating first-seen host INI as trusted without pin |
| **poll** | — | Host/Aether requests realtime (TS-class serial is request/response). | Assuming unsolicited push on TS serial |
| **framing** | — | Packet envelope (e.g. newserial size + payload + CRC). | “packet” for both envelope and och payload without distinction |
| **transport** | — | Pipe under the protocol: **USB**, **UART**, **Bluetooth**, **Wi‑Fi**. | Calling USB “just serial” without roles |
| **USB CDC** | — | USB virtual COM (device or host CDC-ACM). | “COM port” as the only on-device abstraction |

---

## 4. Calibration (what gets burned)

Industry “tune” is **broader than fuel maps**. Aether models the full burnable set.

| Preferred | Alias | Meaning | Avoid |
|-----------|-------|---------|--------|
| **calibration** | tune (operator copy) | Full set of burnable settings on the ECU (tables + curves + scalars + flags). | Using **map** for the whole tune |
| **table** | map (operator) | **2-D** calibration grid (e.g. VE vs RPM×load). | “map”/“table” for a scalar or curve |
| **curve** | — | **1-D** calibration vs one axis (e.g. WUE vs CLT, ASE taper). Not a table. | Calling curves “maps” or “tables” |
| **scalar** | setting (operator) | Single constant (cranking fuel, fan temp, …). | Burying settings only under “maps” |
| **VE** | — | Volumetric efficiency fuel **table** (when that is the fuel model). | “fuel map” when VE is the precise term |
| **RAM write** | — | Push calibration into the ECU **working image** (page write). Live effect. Not durable across power loss until **burn**. | bare “write,” “save,” “soft write,” “temp write” |
| **burn** | — | Commit RAM calibration to non-volatile storage on the ECU (TS “Burn”). | “save,” “flash” for calibration burn |
| **readback** | — | Re-read the same raw bytes after a **RAM write** or **burn**; compare to expected encoding. | Using display `digits` as a tolerance |
| **RAM** | working image | Calibration state in ECU working memory after **RAM write**, before **burn**. | “temporary tune” |
| **backup** | — | Full calibration snapshot before mutate (pages and/or MSQ/ATM). | “export” when you mean restore-point |
| **MSQ** | — | TunerStudio tune file (XML) — values + metadata; needs matching **definition**. | “the binary” for MSQ |
| **page** | — | ECU memory bank holding constants. | Exposing raw pages to LLMs instead of named constants |
| **firmware** | — | ECU application/boot image (code). Not calibration. | “flash the tune,” using **burn** for firmware update |

### Implementer models (not face copy)

| Preferred | Alias | Meaning | Avoid |
|-----------|-------|---------|--------|
| **ATM** | — | Aether Tune Model — structured calibration (all burnable constants). | Putting ATM on the face |
| **AMP** | — | JSON projection of ATM for host/LLM. | — |
| **TunePatch** | — | Structured edit ops (scalar/curve/table); agent write language. | **MapPatch** (retired alias); opaque page blobs from agents |

---

## 5. Logging and export

| Preferred | Alias | Meaning | Avoid |
|-----------|-------|---------|--------|
| **log** | datalog | Time-series recording of channels. | “trace” for operator copy |
| **channel** | — | One named signal in a log or live bus (name + units). | “field” in user copy (OK in binary format docs) |
| **marker** | — | Timed event annotation in a log (MLV marker / comment). | “bookmark” only |
| **sequence** | — | Operator-bounded interval (`SEQ_START` … `SEQ_END`). | Overloading **log session** |
| **MLG** | MLVLG (format-spec cite only) | EFI Analytics binary log file / on-device store when adopted. | Proprietary-only primary store |
| **MSL** | — | TunerStudio / MLV ASCII datalog. | — |
| **LogWorks** | — | Innovate analysis app; tuner **handoff** target (DIF/CSV as planned). | Assuming MLV-only consumers |
| **export** | — | Projection of a log or calibration to another format/file off-device. | “convert” when the operator action is export; “export” for ECU **backup** |

---

## 6. AFR face chrome

UI structure only (layout detail: [afr-face.md](afr-face.md)). These names are **chrome**, not **channels**.

| Preferred | Alias | Meaning | Avoid |
|-----------|-------|---------|--------|
| **banner** | — | Top strip: **button labels** + **status indicators**. | — |
| **dial** | — | Multi-segment LED gauge ring + aperture. | — |
| **button labels** | — | On-screen **MODE** / **SEL** naming physical hard keys (not touch targets). | Treating labels as soft buttons |
| **dial legend** | — | Scale marks **8 · 11 · 13 · 15 · 17 · 20** inside the aperture. | Putting legend on the LED segments |
| **value** | — | Large primary number on this screen (**AFR** when in AFR mode). | — |
| **lambda readout** | — | λ companion **widget** to the right of the value (~75% size), same color. Shows **lambda**. | Calling the widget plain **lambda** in layout/spec prose |
| **value legend** | — | **Removed.** Formerly `AIR/FUEL RATIO` under the value. | Restoring under-value legend text; use **lambda readout** instead |
| **aux readouts** | — | Secondary numbers under the dial: **RPM** (left), **TPS** (right). | — |
| **swipe indicator** | — | Page dots at the bottom. | — |
| **status indicators** | — | Non-text chrome (e.g. logging **LED**). | — |

Layout: logical face **448×368** landscape; native panel **368×448**; hard buttons + USB on the **top** edge.

---

## 7. Consistency rules

1. **λ inside, AFR for eyes** — protocols and storage prefer **lambda**; face may show **AFR**; the face widget is **lambda readout**.  
2. **Calibration ≠ table** — **table** (alias map) only for 2-D; **curve** for 1-D; **scalar** (alias setting) for singles.  
3. **Three verbs, never “save”**  
   - **RAM write** — working image on ECU  
   - **burn** — non-volatile calibration on ECU  
   - **export** — files for humans/tools  
   **flash** is not a calibration verb (firmware only, or avoid).  
4. **Definition binds meaning** — never describe **page** bytes without a **definition** / **signature** (and **pin** before live write).  
5. **One channel name** — live bus, logger, and export share the same **channel** id where possible.  
6. **Don’t mint product jargon** when TS/MLV/LogWorks/FOME already name it.  
7. **Chrome ≠ channel** — face terms do not replace **RPM** / **TPS** / **lambda** channel ids in logs or APIs.

---

## 8. Out of scope for this lexicon

- Full FOME/rusEFI constant name lists (live in the **definition** / allowlists).  
- Pixel sizes and color tokens (face specs / mockup).  
- Legal product disclaimers.
