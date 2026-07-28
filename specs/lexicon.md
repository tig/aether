# Aether lexicon

**Rev 0.2 · July 2026** (draft — product + face + live/log/calibration)

Canonical terms for **user-facing copy**, **specs**, and **agent/implementer prose**. Prefer these over synonyms. Prefer **industry wording** (TunerStudio / MegaLogViewer / MegaSquirt-family, FOME/rusEFI, Innovate LogWorks) over invented product slang.

| Doc | Role |
|-----|------|
| [spec.md](spec.md) | Product requirements |
| [afr-face.md](afr-face.md) | AFR screen layout |
| Issues #3 / #4 / #5 | Planning specs for log / calibration / live serial (until `specs/*.md` lands with impl) |

**How to use this file:** pick one term per concept and stick to it. If a synonym appears in UI or docs, treat it as an alias and migrate toward the **Preferred** term. Do not grow this into a glossary of every INI constant name.

---

## 1. Product and roles

| Preferred | Meaning | Source / note | Avoid |
|-----------|---------|---------------|--------|
| **Aether** | This product (device + software). | Product name | “the gauge” alone when product identity matters |
| **ECU** | Engine control unit that holds calibration and streams live data. | Universal | “computer,” “box” in specs |
| **operator** | Person using Aether in car or on bench. | Product | “user” OK in casual prose; prefer **operator** in specs |
| **tuner** | Person or shop that analyzes logs / changes calibration (may not hold the device). | Field usage | — |
| **host** | PC/phone/agent machine talking to Aether (USB/BT/Wi‑Fi). | Common embedded | “server” for the phone/PC side |
| **session** | One continuous link to an ECU *or* one continuous log file period (qualify: **link session** vs **log session** if both appear). | TS / MLV “datalog session” | “connection” alone for logs |

---

## 2. Mixture and engine context (face + live)

| Preferred | Meaning | Source / note | Avoid |
|-----------|---------|---------------|--------|
| **lambda** (λ) | Excess-air ratio; **internal mixture truth** when both exist. AFR = λ × stoich. | Wideband controllers, TS, Innovate | Storing disagreeing AFR and λ as dual truths |
| **AFR** | Air–fuel ratio for **display** (often gasoline-scale even on other fuels). | Tuners, LogWorks, gauges | Using “AFR” when you mean λ in protocols |
| **stoich** | Stoichiometric AFR for the fuel scale in use (e.g. 14.7 gasoline). | Universal | Hard-coding 14.7 with no fuel context |
| **wideband** | Sensor/controller path that reports true λ/AFR (vs narrowband). | Industry | “O2” alone when wideband is meant |
| **RPM** | Engine speed. | Universal | “revs” in specs |
| **TPS** | Throttle position (%). | TS / ECUs | “throttle” alone when the channel is TPS |
| **MAP** | Manifold absolute pressure (prefer **kPa** in data). | TS / ECUs | PSI in internal channels without conversion note |
| **load** | Generic axis: TPS, MAP, or calculated load — say which when known. | Fuel tables | Assuming load always means MAP |
| **CLT** / **IAT** | Coolant / intake air temperature. | TS channel names | “water temp” / “air temp” in channel IDs |
| **WOT** | Wide-open throttle (display label when TPS ≈ 100%). | Universal | Replacing the TPS channel name with WOT in logs |

Face UI chrome terms (**value**, **dial**, **banner**, …) stay in [§6](#6-afr-face-chrome).

---

## 3. Live link and protocols

| Preferred | Meaning | Source / note | Avoid |
|-----------|---------|---------------|--------|
| **live data** | Real-time channels while linked (gauges / face). | TS “realtime” | “stream” alone |
| **output channels** / **och** | ECU realtime block layout (TS INI `[OutputChannels]`). | TunerStudio / MS family | Inventing a second name for the same bytes |
| **signature** | Firmware identity string used to select the correct definition. | TS / MS `signature` | “version” when you mean signature match |
| **definition** | ECU description file (**.ini** / historically **.ecu**) — pages, constants, scales, realtime. | EFI Analytics INI | “config file” for the INI |
| **poll** | Host/Aether requests realtime (TS-class serial is request/response). | MS serial | Assuming unsolicited push on TS serial |
| **framing** | Packet envelope (e.g. newserial size + payload + CRC). | MS serial protocol | “packet” for both envelope and och payload without distinction |
| **transport** | Pipe under the protocol: **USB**, **UART**, **Bluetooth**, **Wi‑Fi**. | Product + #5 | Calling USB “just serial” without roles |
| **USB CDC** | USB virtual COM (device or host CDC-ACM). | USB-IF / ESP-IDF | “COM port” as the only abstraction on-device |

---

## 4. Calibration (what gets burned)

Industry “tune” is **broader than fuel maps**. Aether models the full burnable set.

| Preferred | Meaning | Source / note | Avoid |
|-----------|---------|---------------|--------|
| **calibration** | Full set of burnable settings on the ECU (tables + curves + scalars + flags). | Calibration culture; MSQ content | Using **map** for the whole tune |
| **tune** | Casual synonym for calibration / MSQ project; OK in operator copy. | TS “tune” | Specs should prefer **calibration** when precision matters |
| **map** / **table** | **2-D** table (e.g. VE vs RPM×load). | TS TableEditor | “map” for a scalar setting |
| **curve** | **1-D** table (e.g. WUE vs CLT, ASE taper). | TS | Calling curves “maps” |
| **scalar** / **setting** | Single constant (cranking fuel, fan temp, …). | INI constants | Burying settings only under “maps” |
| **VE** | Volumetric efficiency fuel table (when that is the fuel model). | TS / speed-density | “fuel map” when VE is the precise term |
| **burn** | Commit RAM calibration to non-volatile storage on the ECU. | TS “Burn” | “save,” “flash” for calibration burn |
| **RAM** (calibration) | Working image after write, before burn. | TS | “temporary tune” |
| **backup** | Full calibration snapshot before mutate (pages and/or MSQ/ATM). | Tuner practice | “export” when you mean restore-point |
| **MSQ** | TunerStudio tune file (XML) — values + metadata; needs matching **definition**. | TS | “the binary” for MSQ |
| **page** | ECU memory bank holding constants. | TS / MS protocol | Exposing raw pages to LLMs instead of named constants |

**Implementer models (Aether):** **ATM** (structured calibration), **AMP** (JSON projection), **TunePatch** (structured edits). Keep these in agent/API docs; do not put them on the face.

---

## 5. Logging and export

| Preferred | Meaning | Source / note | Avoid |
|-----------|---------|---------------|--------|
| **log** / **datalog** | Time-series recording of channels. | TS / MLV / LogWorks | “trace” for operator copy |
| **channel** | One named signal in a log or live bus (name + units). | MLV / TS | “field” in user copy (OK in binary format docs) |
| **marker** | Timed event annotation in a log (MLV marker / comment). | MLVLG / MLV | “bookmark” only |
| **sequence** | Operator-bounded interval (`SEQ_START` … `SEQ_END`). | Aether grammar on MLV markers | Overloaded “session” |
| **MLG** / **MLVLG** | EFI Analytics binary log (Aether **on-device** store when adopted). | EFI Analytics MLVLG spec | Proprietary-only primary store |
| **MSL** | TunerStudio / MLV ASCII datalog. | TS | — |
| **LogWorks** | Innovate analysis app; **handoff** format for the remote tuner (DIF/CSV as planned). | Innovate | Assuming MLV-only consumers |
| **export** | Projection of a log or calibration to another format/file. | Universal | “convert” when the operator action is export |

---

## 6. AFR face chrome

UI structure only (layout detail: [afr-face.md](afr-face.md)).

| Term | Meaning |
|------|---------|
| **banner** | Top strip: **button labels** + **status indicators**. |
| **dial** | Multi-segment LED gauge ring + aperture. |
| **button labels** | On-screen **MODE** / **SEL** naming physical hard keys (not touch targets). |
| **dial legend** | Scale marks **8 · 11 · 13 · 15 · 17 · 20** inside the aperture. |
| **value** | Large primary number on this screen (**AFR** when in AFR mode). |
| **lambda** | λ companion to the right of the value (~75% size), same color. |
| **aux readouts** | Secondary numbers under the dial: **RPM** (left), **TPS** (right). |
| **swipe indicator** | Page dots at the bottom. |
| **status indicators** | Non-text chrome (e.g. logging **LED**). |

Layout: logical face **448×368** landscape; native panel **368×448**; hard buttons + USB on the **top** edge.

---

## 7. Consistency rules (short)

1. **λ inside, AFR for eyes** — protocols and storage prefer **lambda** when both exist; face may show AFR.  
2. **Calibration ≠ map** — say **map/table** only for 2-D; say **setting/scalar/curve** otherwise.  
3. **Burn ≠ log save** — **burn** is ECU non-volatile calibration; **export** is files for humans/tools.  
4. **Definition binds meaning** — never describe page bytes without a **definition** / signature.  
5. **One channel name** — live bus, logger, and export use the same canonical **channel** id where possible (TS-style names when from the ECU).  
6. **Don’t mint product jargon** when TS/MLV/LogWorks/FOME already name it.

---

## 8. Out of scope for this lexicon

- Full FOME/rusEFI constant name lists (live in the **definition** / allowlists).  
- Pixel sizes and color tokens (face specs / mockup).  
- Legal product disclaimers.
