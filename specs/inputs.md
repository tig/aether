# Aether inputs — live serial-class streams (display & logging)

**Rev 0.3 · July 2026**  
**Status:** Contract for planning and implementation handoff. Not firmware.  
**Addresses:** [#5](https://github.com/tig/aether/issues/5) — real-time ECU data formats & serial protocols (display/logging mode).

| Related | Role |
|---------|------|
| [#1](https://github.com/tig/aether/issues/1) | Host wireless bridge — *carries* this ECU-facing layer; does not redefine it |
| [#2](https://github.com/tig/aether/issues/2) | Always-on logging — consumes **canonical live channels** defined here |
| [#3](https://github.com/tig/aether/issues/3) | On-disk log file formats — *downstream* of the live channel model |
| [#4](https://github.com/tig/aether/issues/4) | Map / tune R/W — shares **transport + session** later; not live decode |
| [spec.md](spec.md) | Product mission; display rate vs log rate; readiness |
| [afr-face.md](afr-face.md) | Face needs **λ/AFR + RPM + load (TPS/MAP)** from this path |
| [lexicon.md](lexicon.md) | Face phrasing only |

**Survey notes (non-normative):** [docs/research/serial-protocols.md](../docs/research/serial-protocols.md)

### Operator context (drives P0)

| Fact | Value |
|------|--------|
| **Prototype device** | Current Aether product board — ESP32-S3 1.8″ AMOLED (Type-C USB), as in [spec.md](spec.md) §2 |
| **Pilot ECU** | **[FOME](https://www.fome.tech/)**-based (issue “FOAM” → FOME; rusEFI-lineage TS serial) |
| **P0 product outcome** | **Plug Aether into the FOME ECU via USB** and get live display + logging channels (RPM, load, λ/AFR) without a PC in the middle |

Speeduino remains a valuable **simulator / secondary** target (fixed och layouts, public sims). It is **not** the operator’s P0 metal path.

---

## 1. Scope

### 1.1 Goals

1. Define how Aether **consumes** real-time ECU data over **serial-class** links for **display and logging mode** (read-mostly).
2. Treat **USB** as a first-class transport — not “serial with a different connector.”
3. Survey the protocols popular open ECUs already speak; **prefer speaking those** over inventing a new ECU protocol.
4. Specify an **internal canonical live channel model** so the AFR face and logger do not care which ECU framing produced a sample.
5. Give a **phased pilot** that **starts with USB + FOME on the Aether prototype**, then UART / BT / Wi-Fi, then a second dialect (Speeduino sim / broader rusEFI).
6. Leave a clean slot for **CANbus** later without rewriting this document’s structure.

### 1.2 Non-goals

| Out | Why / where |
|-----|-------------|
| **CANbus** (OBD ISO-TP, OEM CAN, MS 11-bit broadcast, rusEFI CAN dash) | Explicitly deferred — product supports CAN later; §13 reserves the slot |
| Map / table **read-write**, burn, page CRC for tuning | [#4](https://github.com/tig/aether/issues/4) |
| On-disk log **file** formats, export codecs | [#3](https://github.com/tig/aether/issues/3) |
| Host/LLM wireless product UX | [#1](https://github.com/tig/aether/issues/1) — only the ECU-facing contract is shared |
| Full TunerStudio replacement (dialogs, auto-tune, project UI) | Display + logger only |
| Wideband **controller** control loops (heater drive, free-air cal) | Separate sensor identity; may share serial transport later |
| Physical pinouts for every ECU harness | Board / setup docs when hardware freezes |

### 1.3 Document shape (CAN later)

```text
specs/inputs.md
├── Serial-class live inputs          ← this rev (USB / UART / BT / Wi-Fi)
├── §13 Reserved: CANbus live inputs  ← future section, same channel model
└── (optional later) Sensor identity  ← dedicated wideband modules, etc.
```

Live samples always end as **canonical channels** (§6). Transport and decoder plug in underneath. CAN decoders will publish to the same bus.

---

## 2. Principles

1. **Speak the ECU’s protocol** — Aether is a client of existing serial dialects (TunerStudio-compatible, Speeduino, rusEFI/FOME, …).
2. **USB is mandatory in survey, architecture, and early phases** — same logical byte stream as UART once past the bridge; **roles, enumeration, and hot-plug differ**.
3. **One live bus, many adapters** — transport → framing → decoder → **canonical channels** → face + logger.
4. **Display rate and log rate may differ** — already product intent in [spec.md](spec.md) §3.4.
5. **Read path first** — continuous stream, low latency, integrity flags; map R/W (#4) reuses session later.
6. **No silent bad data on the face** — disconnect, CRC fail, and “not valid yet” must be visible (dashed primary, quality flags).

---

## 3. Protocol survey (serial-class realtime)

Family names below are **decoder families**. One family can cover multiple hardware brands when the wire protocol matches.

### 3.1 Comparison table

| Family | Platforms | Session / identity | Realtime model | Framing / integrity | Definition need | USB notes | Priority |
|--------|-----------|--------------------|----------------|---------------------|-----------------|-----------|----------|
| **TS newserial (MS-style)** | MegaSquirt 2/3 Extra, many “TS-compatible” ECUs | `Q` / `S` / signature; plain `Q` for port scan | **Poll** only (no unsolicited broadcast on serial) | Size + payload + **CRC32** (BE); response flag | **INI** defines `ochBlockSize` + field layout | Usually RS-232 or USB–UART (FTDI/CP210x/CH340) as **device** to host | P1 full |
| **FOME** (issue “FOAM”) | FOME (rusEFI-lineage; [fome.tech](https://www.fome.tech/)) | Same TS + console pattern; USB mass-storage for INI on some boards | Same TS och poll family | Same as rusEFI lineage | FOME-specific INI / signature | **USB cable first-class** for TS; COM port + bundled INI | **P0 pilot** |
| **rusEFI TS binary** | rusEFI boards | Signature / auto-detect INI over USB/serial/BT; plain `Q`/`t`/`T` | Poll: `O` / och get (offset+count); optional **scatter** high-speed | CRC-wrapped TS packets; multi-channel `TsChannel` | **INI** required for full field map; signature selects file | **Native USB CDC** (STM VCP) + optional TTL UART **simultaneously**; baud often irrelevant on pure CDC | **P0 family** (shared decoder with FOME) |
| **Speeduino TS subset** | Speeduino | `F`→`002`, `Q`/`S` signature strings | Poll: legacy `A` (full dump) or framed `r` offset/len (~20 Hz typical) | Legacy raw **or** framed CRC32 | Fixed **~130 B** layout for a given firmware year; INI for TS | MCU USB-serial or external USB–UART; Wi-Fi TCP serial common in tools/sims | **P1** sim / secondary metal |
| **Legacy MS plain** | Old MS / simple dashes | Single-byte `A`/`Q`/`S` | Poll `A` → raw och, **no CRC** | None | INI or hard-coded layout | Same physical transports | Fallback only |
| **Wideband serial modules** | Innovate LC-1/2, AEM UEGO serial, etc. | Vendor stream ID / push packets | Often **push** ~10–12 Hz | Vendor packets / checksums | Fixed vendor docs | USB–serial adapters common | P2+ (sensor, not full ECU) |

**Note on naming:** GitHub issue #5 says **FOAM**. The active open project is **[FOME](https://www.fome.tech/)** (Free Open Motorsports ECU). This spec treats FOAM as **FOME** and documents that lineage.

### 3.2 Family detail (normative summary)

#### 3.2.1 TunerStudio / MegaSquirt “newserial”

- **Half-duplex request/response.** ECU does **not** push realtime on serial unless polled.
- Request frame layout: `[u16 size][payload…][u32 CRC32]` (big-endian fields).
- **`size` = payload length only** — the number of bytes in `payload…`. It **excludes** the 2-byte length prefix and the trailing 4-byte CRC32 (MegaSquirt **newserial** / MS protocol family; 2014-era doc and current TS-compatible firmwares). Advertising `len(payload)+6` is a **spec bug** and will desync the ECU.
- CRC32 is computed over the **payload** (confirm exact coverage against the MS newserial reference during implementation golden tests; do not invent a second CRC domain).
- Response adds a **flag** byte (OK, realtime data, underrun, CRC fail, busy, …) ahead of response payload as defined by the same family.
- Wire total bytes for a request = `2 + size + 4`.
- Realtime: **`A`** (full outpc) or table/`r` style reads; layout from **INI** (`ochBlockSize`, `[OutputChannels]`).
- Identity: **`Q`** → format/signature string; **`S`** → title/version string.
- Baud on true UART: commonly **115200 8N1** (product-dependent); on USB-CDC the “baud” is often ignored by the device stack.
- **Implication for Aether:** must own a poll scheduler, CRC validation, and an INI- or table-driven field extractor.

#### 3.2.2 FOME (FOAM) — **P0 pilot**

- Open ECU fork/lineage of the rusEFI stack; **TunerStudio + USB** are the documented day-one path ([fome.tech](https://www.fome.tech/), [wiki.fome.tech](https://wiki.fome.tech/), [FOME-Tech/fome-fw](https://github.com/FOME-Tech/fome-fw)).
- Live data = **same TS och family** with FOME signatures and INI.
- Treat as **rusEFI-family decoder + FOME definition pack**, not a third wire protocol.
- **Why P0:** operator’s vehicle is FOME-based; **P0 bar is plug current Aether prototype into FOME via USB** and get face + log channels.

#### 3.2.3 rusEFI

- Implements EFI Analytics / TS binary: minimal gauges need **query + och get**; comments in firmware stress that pair for live gauges.
- **Native USB serial** (STM Virtual COM) is the primary bench path; **TTL UART** can run **in parallel** (e.g. TS on USB + console on UART).
- Bluetooth: **SPP serial module** (JDY-33 / HC-05 class) on the binary UART — documented as limited/slow; Wi-Fi via external UART–TCP bridges preferred for bandwidth.
- Auto-detect of definition files when connected via USB, serial, or BT (TS project path).
- Optional **scatter** read for sparse high-rate subsets (good model for “face channels only”).
- **Why same family as FOME:** shared poll/CRC machinery; additional signature packs after FOME is green.

#### 3.2.4 Speeduino — secondary / sim

- Speaks the same **TS-compatible** world: legacy single-byte commands **and** framed v2 CRC.
- Realtime:
  - Legacy **`A`**: full status blob (firmware-year layout; e.g. ~**130 bytes** for recent public layouts).
  - Framed **`r`**: offset + length into output channels (TunerStudio’s preferred continuous path).
- Typical tool rates ~**15–20 Hz** gauges; Aether may poll higher if the ECU keeps up (product-configurable caps).
- Secondary serial / dash ports exist on many boards for a second client without stealing the TS port.
- **Why not operator P0:** public simulators and fixed layouts are excellent for **CI goldens** and lab bring-up; they do not replace FOME-on-USB acceptance.

#### 3.2.5 Wideband-only serial (brief)

- Innovate-style **push** packets and AEM-style RS-232 streams supply **λ/AFR** without RPM/load.
- Useful as **sensor sources** that merge into the same canonical bus when the ECU does not provide wideband, or as dual-channel add-ons.
- Not the v1 ECU pilot (face requires RPM + load per product mission).

---

## 4. Transport survey

Logical serial bytes are transport-agnostic **after** the link is up. USB still needs its own role, power, and hot-plug model.

### 4.1 USB (required)

#### 4.1.1 Why USB is not “just serial”

| Concern | UART/TTL | USB |
|---------|----------|-----|
| Link bring-up | Baud + levels | **Enumerate**, descriptors, class drivers |
| Roles | Point-to-point peers | **Host vs device** (asymmetric) |
| Hot-plug | Cable in/out ≈ line idle | Disconnect/reset/re-enumerate cycles |
| Multi-function | Rare | CDC + MSC + DFU composites common on ECUs |
| Baud | Meaningful | Often **ignored** on pure CDC; still set for USB–UART bridges |
| Power | Separate | VBUS can power bench ECU/Aether (careful with car installs) |

#### 4.1.2 Classes and bridge chips

| Path | What Aether sees | Notes |
|------|------------------|-------|
| **CDC-ACM** | Virtual COM | rusEFI/FOME native USB; many MCU boards |
| **USB–UART** | CDC or vendor VCP | **CP210x**, **CH340/CH341**, **FTDI FT232**, Prolific — need host VID/PID quirks on ESP USB host |
| **USB-Serial-JTAG** | Debug + CDC on ESP itself | Aether’s own flash/console path on ESP32-S3 — **do not steal** from ECU host without explicit mux policy |

#### 4.1.3 Roles on the ESP32-S3 product

The SoC has **USB-OTG** and **USB-Serial-JTAG** sharing one PHY on many modules — **only one controller active at a time** without an external PHY. Board wiring (single Type-C vs OTG host port) is an open hardware fact; this spec states **behaviors**, not an unproven schematic claim.

| Mode | Aether role | Peer | Use |
|------|-------------|------|-----|
| **USB device (CDC)** | Device | PC / host app | Bench bring-up, **host bridge** (#1), PC-side ECU **simulator** → Aether as gauge |
| **USB host (CDC-ACM / VCP)** | Host | ECU native USB **or** USB–UART adapter on ECU | Direct cable ECU↔Aether in car/bench |
| **Neither (UART path)** | N/A | TTL | Field harness when USB host not wired |

**Cable scenarios (product stories):**

1. **ECU ↔ Aether (USB host):** Aether enumerates ECU/adapter; poll och; face + log.  
2. **ECU ↔ PC with Aether as CDC device:** Host app or #1 bridge injects live frames / relays TS; Aether displays/logs.  
3. **Dual:** USB device to PC for capture/debug while UART talks to ECU (when hardware allows).  
4. **Bench power:** USB power for Aether and/or ECU — never assume VBUS is present in-vehicle.

#### 4.1.4 Enumeration, hot-plug, failure

| Event | Transport layer | Session layer | Face |
|-------|-----------------|---------------|------|
| Plug in | Enumerate; open ACM; set line coding if required | Re-run identity (`Q`/`S`/signature) | “Linking…” then live or fail |
| Unplug | Disconnect IRQ / port gone | Session → `NO_LINK`; stop poll | **Invalid** mixture (dashed); aux freeze or dash; log gap flagged |
| Re-plug | New enumeration (COM path may change on host OS; on Aether host stack, new device handle) | Full re-handshake | Resume only after good och + CRC |
| Enumerate OK, protocol fail | Port open | CRC/signature errors accumulate | Show link but **bad quality**; do not paint trust colors |
| Composite device | Pick CDC interface by policy | Ignore MSC/DFU for live mode | — |

#### 4.1.5 USB in the phase plan

USB is **P0**, not deferred behind wireless-only demos. Minimum P0 bar on the **current Aether prototype**:

- **Must:** **USB link to a real FOME ECU** such that Aether receives live och/channels for face + logger (host CDC-ACM toward ECU as **device**, or documented adapter path if FOME exposes USB–UART).
- **Must:** Hot-unplug recovery → face shows invalid / `NO_LINK` within ~1 s.
- **Should:** USB device CDC path for PC sim / host bridge (#1) using the **same decoder**.
- **Should:** UART twin with the same decoder when harness allows.
- Prefer landing both device and host roles before declaring USB “done,” if the SKU PHY allows — **but do not block P0 on dual-role if host-to-FOME already works.**

### 4.2 UART / TTL

- Levels: **3.3 V TTL** preferred (ESP32-S3); 5 V ECU UART needs level shift.
- Framing: **8N1**, no flow control for TS-class (unless a specific ECU requires RTS/CTS).
- Baud: try **115200** first; also **38400 / 57600** for some rusEFI TTL notes; store last-good per profile.
- Same **decoder** as USB-CDC once bytes arrive.
- Best **in-car** hardwire path when USB host is unavailable on the SKU.

### 4.3 Bluetooth

| Profile | Role | Notes |
|---------|------|-------|
| **Classic SPP** | Serial port emulation | What most MS/rusEFI **ECU-side** BT modules (HC-05 / JDY-33 class) expose to phones/TS |
| **BLE UART** (NUS-like) | Phone-centric / future | Possible later; **not** a drop-in for Classic SPP ECU modules |

**Hardware dependency (must):** the **ESP32-S3R8** (Aether prototype / target class) has **Bluetooth LE only** — **no** Classic BR/EDR controller. Therefore:

| Path | Status |
|------|--------|
| **On-SoC Classic SPP** | **Not available** on S3 — do not schedule as a software-only phase |
| **P2 wireless serial** | Requires an **external Classic BT SPP module** on **UART** (or a future SoC with Classic), **or** skip Classic and use **Wi-Fi TCP serial (P3)** / USB for wireless-ish shop use |
| **BLE-only SPP substitute** | Only if the **ECU** also speaks BLE UART — uncommon for HC-05-style stacks; treat as research, not P2 default |

- Pairing PINs often `1234` / `0000` on HC modules — product UX must not assume secure pairing.
- Bandwidth and duty cycle: treat as **lower priority / lower rate** than USB or wired UART; cap poll rate (e.g. 10–15 Hz face) to reduce drops.
- rusEFI documents BT as limited; prefer USB or Wi-Fi bridges for logging density.

### 4.4 Wi-Fi

| Pattern | Ports / discovery | Notes |
|---------|-------------------|-------|
| **TCP serial bridge** | Common: ECU or ESP proxy listens (examples: simulators on **:5000**, TS TCP drivers, UART–TCP proxies) | Byte-identical TS protocol over TCP |
| **UDP** | Occasional proprietary | Not assumed for v1 |
| **AP vs STA** | ECU/sim as AP, or car Wi-Fi STA | Profile stores SSID/password/IP/port |
| **mDNS** | Nice-to-have | Optional discovery; manual IP always required as fallback |

Wi-Fi is excellent for **bench simulators** and shop tools; in-car RF and latency make it **after** USB/UART for the pocket gauge pilot.

### 4.5 Transport priority (decision)

| Rank | Transport | Phase | Rationale |
|------|-----------|-------|-----------|
| 1 | **USB** (device and/or host CDC) | **P0** | Product Type-C story; bench + tethered logging; #1 host bridge |
| 2 | **UART / TTL** | **P0–P1** | Same framing; field install; always-on power domain |
| 3 | **Wi-Fi TCP serial** | **P2** (was P3) | Shop/bench wireless without Classic BT hardware; simulators |
| 4 | **Bluetooth Classic SPP** | **P3** | **Only if** SKU includes **external Classic SPP UART module** (or non-S3 radio); not on bare ESP32-S3 |

---

## 5. Decisions (v1)

### 5.1 Pilot protocol family

**Primary family: TunerStudio-compatible rusEFI / FOME / MS serial (newserial CRC + legacy plain).**

| Choice | Detail |
|--------|--------|
| **P0 pilot ECU dialect** | **FOME** (operator vehicle; signature → FOME INI/layout pack) |
| **P0 transport** | **USB** on the **current Aether prototype** (Type-C) ↔ FOME USB CDC or USB–UART |
| **P0 hardware** | ESP32-S3 AMOLED board **as built today** — do not wait for a future SKU |
| **P0 wire protocol** | TS-family CRC och poll (`O` / framed read as implemented by FOME/rusEFI lineage); plain signature/`Q`/`S` for identity |
| **P1 same family** | Broader **rusEFI** packs; optional scatter; dual USB/UART |
| **P1 secondary dialect** | **Speeduino** fixed och (`A` / `r`) for simulators and CI goldens |
| **Not pilot** | Innovate/AEM-only streams as sole source (no RPM/load); proprietary closed ECUs |

**Why FOME first:** it is the ECU on the car; USB is how the operator will plug the prototype in; same family as rusEFI so framing investment carries forward.

**Why Speeduino next (not instead):** fixed layouts and public sims accelerate CI; they do **not** replace FOME USB P0 acceptance.

### 5.2 Adapter strategy

```text
┌──────────── transports ────────────┐
│ USB host │ USB device │ UART │ BT │ Wi-Fi TCP │
└─────────────────┬──────────────────┘
                  ▼
           link_bytes I/O
                  ▼
         framing (plain | CRC packet)
                  ▼
     session (identity, keepalive, reconnect)
                  ▼
   decoder_family (fome_rusefi | speeduino | ms_ini | …)
                  ▼
        canonical live channel bus
           ┌──────┴──────┐
           ▼             ▼
     face subscribers  logger subscribers
```

- **One decoder module per protocol family**, not per transport.
- Transports implement a narrow **`serial_link`** API: open/close, read/write, link-state events (including USB attach/detach).
- Map R/W (#4) will add **commands on the same session**, not a second USB stack.

### 5.3 Definition handling

| Phase | Strategy |
|-------|----------|
| P0 Speeduino | **Ship** compiled layout tables for supported firmware signatures (`Q`/`S` match) |
| P1 rusEFI/FOME | Ship **signature → layout pack**; optional pull of INI-derived tables from host (#1) later |
| Later | Full INI subset parser on host; edge keeps compact binary layouts only |

Aether **does not** require TunerStudio installed on the car. Definitions are product assets or host-pushed blobs.

### 5.4 What we explicitly will not invent

- A new ECU-side binary dialect for v1.
- A custom USB vendor class for live data (use CDC).
- Assuming USB baud equals UART baud semantics without testing the bridge chip.

---

## 6. Internal canonical live channel model

After decode, **everything** is a time-stamped sample on a single bus. Face, logger, alarms, and future CAN publishers/consumers share this model.

### 6.1 Time

| Field | Type | Meaning |
|-------|------|---------|
| `t_mono_ms` | `int64` | Aether monotonic ms (HAL clock) when sample was **accepted** |
| `t_ecu_ms` | `int64` optional | ECU time if protocol provides it |
| `seq` | `uint32` | Monotonic sample sequence per session |

Use **`int64` milliseconds** end-to-end (ESP32 `long` is 32-bit — see plate AGENTS).

### 6.2 Quality

| `quality` | Face behavior | Logger |
|-----------|---------------|--------|
| `OK` | Normal paint | Store value |
| `STALE` | Hold last with aged indicator if UI has one; else treat as soft invalid after timeout | Store last + quality |
| `CRC_FAIL` | Do not update primary from bad frame | Gap / error counter |
| `NO_LINK` | Dashed primary; aux dashed or frozen per face rules | Session gap |
| `HEATING` / `SENSOR_INVALID` | Dashed or “not ready” mixture | Flag channel |
| `PARTIAL` | Update only channels marked present | Per-channel validity |

### 6.3 Channel IDs (v1 set)

Stable string IDs (and fixed numeric enums in C). Units are **SI / unambiguous**; display converts.

| ID | Unit | Face | Log default | Notes |
|----|------|------|-------------|-------|
| `rpm` | rev/min | **yes** | yes | Integer |
| `tps` | % | **yes** | yes | 0–100; 100 → WOT label on face |
| `map` | kPa | aux/load | yes | Absolute |
| `lambda` | — | **primary internal** | yes | Prefer λ internally |
| `afr` | — | derived display | optional | Using user stoich factor |
| `afr_target` | — | optional | yes | If ECU provides |
| `clt` | °C | optional page | yes | |
| `iat` | °C | optional page | yes | |
| `batt` | V | optional | yes | |
| `ego_corr` | % | optional | yes | Short-term fuel trim / ego correction when present |
| `engine_sync` | bool/enum | status | yes | |
| `secl` | s | debug | yes | ECU seconds counter if present |

**Primary mixture truth:** store **`lambda`** when the ECU provides it or when AFR + known stoich allows conversion. Face units mode (AFR vs λ) is a **view** ([afr-face.md](afr-face.md)).

### 6.4 Sample record (logical)

```text
LiveSample {
  t_mono_ms: int64
  t_ecu_ms:  int64? 
  seq:       uint32
  source:    { family, transport, profile_id }
  quality:   enum
  present:   bitset of channel IDs
  values:    float or scaled int per present channel
}
```

Decoders must set **`present`** bits — missing wideband must not pretend 14.7.

### 6.5 Subscriptions

| Consumer | Channels | Rate target | Filtering |
|----------|----------|-------------|-----------|
| **AFR face** | `lambda`/`afr`, `rpm`, `tps` (or `map` if TPS absent) | **10–20 Hz** display | Optional smoothing ([spec.md](spec.md) §3.4) |
| **Logger** | Full configured set | **20–50+ Hz** or max stable poll | Prefer raw |
| **Alarms** | Condition set | Same as log or face max | Raw preferred |

Poll scheduler may request **full och** at log rate and **downsample / smooth** for the face, **or** use scatter/partial reads for face and full reads for log when the ECU supports it (rusEFI scatter; Speeduino `r` length).

---

## 7. Architecture

### 7.1 Layers

| Layer | Responsibility | Non-responsibility |
|-------|----------------|--------------------|
| **Transport** | Bytes, link up/down, USB enum, BT connect, TCP connect | Protocol meaning |
| **Framing** | Packet reassembly, CRC, legacy single-byte mode | Field names |
| **Session** | Identity, profile, reconnect backoff, exclusive poll lock | UI |
| **Decoder** | Bytes → physical values + present bits | Drawing |
| **Live bus** | Fan-out samples, rate stats | Persistence format |
| **Face / logger** | Subscribe | Wire protocols |

### 7.2 Display-mode vs log-mode

Aligned with [spec.md](spec.md) §3.4:

1. **Independent rates:** face update interval and log sample interval are separate config values.
2. **Shared decode:** one och response can feed both (log stores full; face takes subset).
3. **Back-pressure:** if logging media is slow, **drop log samples with counters** — never block the face poll task beyond a bounded wait.
4. **Always-on logging (#2):** when enabled, logger subscribes at session start; face subscribe is independent.
5. **Export (#3):** log writers read **canonical samples** (or an intermediate ring), not Speeduino bytes.

### 7.3 Failure modes → face

| Failure | Face (AFR screen) |
|---------|-------------------|
| USB unplug / BT drop / TCP loss | Primary **dashed**; quality `NO_LINK`; logging LED policy per logging spec (do not claim logging healthy) |
| CRC errors burst | Hold last **briefly**, then invalid; do not flash random AFR |
| Partial frame / underrun | Ignore frame; count error |
| ECU reboot (signature change / timeout) | Re-handshake; invalid until first good och |
| Wideband heating / ECU flags invalid | `HEATING` / `SENSOR_INVALID` — never green-band a known-bad λ |
| Wrong INI/layout (plausible CRC, wrong fields) | Sanity checks (RPM range, λ range); fail safe to invalid + “profile mismatch” in setup later |

### 7.4 Shared session notes for map R/W (#4)

Session object should eventually expose:

- `link` + `family` + `signature` + `layout_id`
- `poll_lock` so map chunk R/W does not interleave mid-frame with och poll
- `burn` / page commands **not** implemented here — only the lock and identity

USB host mode is the preferred **safe bench write** path later (#4); this live spec only requires that session not be protocol-hardcoded to och-only forever.

---

## 8. Capability matrix

| Platform | USB | UART/TTL | BT SPP | Wi-Fi TCP | Live channels for face | Aether priority |
|----------|-----|----------|--------|-----------|------------------------|-----------------|
| **FOME** | **Native USB** first-class | Yes (lineage) | Lineage-dependent | External | Same family as rusEFI | **P0 pilot** |
| **rusEFI** | **Native CDC** (strong) | Yes, parallel to USB | Module on UART (limited) | External bridges | Full och via INI; scatter optional | **P0 family / P1 packs** |
| **Speeduino** | Via USB–UART or MCU CDC | Yes (primary + often secondary) | Via BT serial adapters | Common in tools/sims | RPM, TPS, MAP, AFR/λ, CLT, IAT, batt, … | **P1** sim / secondary |
| **MegaSquirt / MS3** | USB–serial adapters typical | RS-232 / TTL adapters | Common BT adapters | Third-party bridges | INI och | P1–P2 |
| **Innovate / AEM WB** | USB–serial | RS-232 | Rare | Rare | λ/AFR only | P2 sensor merge |

---

## 9. Phased implementation

| Phase | Deliverable | Exit criteria |
|-------|-------------|---------------|
| **P0 — USB + FOME on Aether prototype** | `serial_link` for **USB host CDC-ACM** (and/or device CDC) on **current Aether board**; TS framing; **FOME** signature/layout pack; canonical bus; face shows live RPM/TPS/λ from **real FOME ECU over USB** | Plug cable → live face; 10+ min soak; hot-unplug recovery; host unit tests with recorded **FOME** frames |
| **P1 — Speeduino goldens + rusEFI packs + field UART** | Speeduino fixed och for CI/sim; broader rusEFI layouts; hardened TTL path; dual-rate face/log | Simulator CI green; second metal ECU optional |
| **P2 — Wi-Fi TCP serial** | STA/AP profile; TCP client; optional mDNS; same TS framing as USB | Bench sim + shop wireless path (no Classic BT required) |
| **P3 — Bluetooth Classic SPP** | **External** SPP module on UART (HC-05/JDY class) **or** explicit future SKU radio; pairing; rate-capped poll | In-car wireless **only when hardware exists** — **blocked** on bare S3 SoC radio |
| **P4 — MS INI subset / scatter** | Broader MS layouts; rusEFI scatter for face-minimal reads | More ECUs without per-board C tables |
| **Later — CAN** | §13 | Same canonical bus |

**P0 USB acceptance (must not slip):**

- **Real FOME ECU** on USB with the **current Aether prototype** shows live RPM + load + λ/AFR on the face (not sim-only).
- Document which USB role(s) the prototype uses for that path (host / device / adapter).
- Capture at least one **.bin/.pcap-style** FOME USB or serial trace used in CI replay.
- Face invalid on unplug within **≤ 1 s** of link loss detection.

---

## 10. Test plan ideas

| Kind | What |
|------|------|
| **Golden frames** | Record **FOME** och responses first; Speeduino `A`/`r` and rusEFI as secondary; replay on host tests |
| **Simulator** | rusEFI/FOME virtual / TS TCP where available; [speeduino-serial-sim](https://github.com/askrejans/speeduino-serial-sim)-class for CI |
| **USB device path** | PC runs simulator → Aether CDC device receives (or host PC tool feeds) |
| **USB host path** | Aether hosts FOME CDC / CP210x/CH340 adapter |
| **Fault injection** | Truncate frames, flip CRC, mid-stream unplug, baud mismatch |
| **Rate tests** | Face @ 15 Hz + log @ 50 Hz without face stall |
| **Soak** | 1 h continuous poll; sequence gaps = 0 under clean link |
| **HIL (P0)** | **Real FOME ECU + current Aether prototype over USB** |

No production firmware is required to close **this** issue — but implementation tickets should inherit these tests.

---

## 11. Open questions

1. **Prototype USB topology:** On the **current** Aether Type-C board, is USB-OTG host available, device-only, or muxed with USB-Serial-JTAG? (Blocks host-vs-device default for FOME cable.)
2. ~~First physical ECU?~~ **Resolved:** **FOME** + Aether prototype over **USB**.
3. **INI on device:** How large a FOME layout pack fits flash before host-pushed defs (#1) are mandatory?
4. **Secondary serial:** Prefer a second port so a laptop can keep TunerStudio while Aether logs?
5. **Security / pairing:** Any requirement beyond default BT PINs for v1?
6. **Power:** Is USB VBUS-powered bench mode a supported product mode for ECU+Aether?
7. **Wideband priority:** ECU och AFR vs dedicated Innovate/AEM serial as dual-channel source for bank-to-bank ([spec.md](spec.md) §3.7)?

---

## 12. Acceptance criteria (this spec / issue #5)

- [x] Written comparison of realtime serial protocols for **rusEFI**, **FOME (FOAM)**, and **Speeduino/MS TS-compatible** family  
- [x] **USB** addressed: roles, CDC/UART bridges, enumeration, hot-plug, phase plan — not assumed identical to bare UART  
- [x] Chosen **internal live channel model** and **pilot = FOME over USB on current Aether prototype**
- [x] Explicit **display vs log** channel/rate strategy  
- [x] **CANbus** excluded; map formats (#4) and log files (#3) only at interfaces  
- [x] Clear handoff: phases P0–P4, architecture, tests, open questions  

**Close #5** when this document (and research notes) land on `main` via PR. Implementation is follow-on issues.

---

## 13. Reserved — CANbus live inputs (future)

*Placeholder — do not expand in #5 work.*

Future content will cover:

- Physical CAN (transceiver, bitrate, termination)
- OBD-II ISO-TP vs manufacturer dash CAN vs rusEFI/MS broadcast
- Decoders that publish to the **same** §6 canonical bus
- Coexistence: serial + CAN fusion (e.g. λ from CAN, RPM from serial)

Until then, product language may say “serial & CANbus” at mission level; **this file’s normative live path is serial-class only.**

---

## 14. References (selected)

| Source | Use |
|--------|-----|
| MegaSquirt Serial Protocol (2014-10-28), msextra.com | newserial wrapper, flags, `A`/`Q`/`r` |
| rusEFI `tunerstudio.cpp` + wiki (USB, Bluetooth, TS connectivity) | TS binary, dual USB/UART, BT limits |
| FOME wiki / fome.tech | USB + TunerStudio workflow (FOAM → FOME) |
| Speeduino secondary serial wiki + community protocol notes | `A` / `r` / secondary port |
| ESP-IDF USB device + USB host CDC-ACM examples | ESP32-S3 roles |
| EFI Analytics ECU definition / INI docs | och layout authority |
| [docs/research/serial-protocols.md](../docs/research/serial-protocols.md) §12 | **OSS leverage map** (licenses, adopt vs ref-only) |

---

## 15. Implementation leverage (OSS)

Normative **product** choices remain in §5 and §9. This section freezes the **recommended open-source stack** for implementation tickets. Full candidate table: research notes §12.

### 15.1 License policy (normative for implementers)

| Rule | Detail |
|------|--------|
| **Metal static link** | Prefer **MIT / Apache-2.0 / BSD / Zlib**. Ship Aether framing as **original** portable C. |
| **GPL ECU firmware** (rusEFI, FOME, Speeduino) | **Reference-only.** Study wire behavior and comments; **do not copy** `tunerstudio.cpp` / comms sources into Aether. |
| **GPL host apps** (LibreTune GPL-2, MegaTunix, …) | May run as **separate processes** for bench smoke; **do not** link into firmware or proprietary-hostile host core without counsel. |
| **Host CI tools** | Prefer **BSD/MIT** (pyserial, speeduino-serial-sim); MPL/LGPL OK for host-only if process boundaries are clean. |

### 15.2 Recommended metal stack (P0 USB + FOME)

| Layer | Component | SPDX | How used |
|-------|-----------|------|----------|
| Platform | **ESP-IDF** (UART, USB Host Library, FreeRTOS) | Apache-2.0 | Existing Aether plate |
| USB host (native CDC) | **espressif/usb_host_cdc_acm** | Apache-2.0 | Enumerate FOME STM VCP / CDC; TX/RX bytes into `serial_link` |
| USB host (UART dongles) | **espressif/usb_host_vcp** + CP210x/FTDI/CH34x drivers | Apache-2.0 | Only if path is USB–UART adapter, not native CDC |
| USB device (bench / #1) | **esp_tinyusb** CDC (TinyUSB **MIT**) | Apache-2.0 + MIT | Aether as COM to PC sim / host bridge |
| Framing / CRC / och poll | **Aether-owned** TS newserial + CRC32 | product | Per MS 2014 PDF; CRC via IDF ROM/`esp_crc` or small Zlib-compatible table |
| Dialect pack | **FOME signature → compiled layout** | data | Derived from public FOME INI; not GPL C |
| Decoder → bus | Canonical channels (§6) | product | Face 10–20 Hz; log 20–50+ Hz |

```text
USB host CDC-ACM (or VCP)  ──►  serial_link  ──►  TS frame + CRC
                                                      │
                                                      ▼
                                            FOME layout pack
                                                      │
                                                      ▼
                                            live channel bus ──► face + logger
```

**Explicit non-dependencies on metal:** rusEFI/FOME firmware trees, LibreTune crates, Speeduino firmware sources.

### 15.3 Recommended host stack (goldens / sim)

| Purpose | Component | SPDX | Notes |
|---------|-----------|------|-------|
| Capture live FOME frames | **pyserial** | BSD-3-Clause | Record USB-CDC sessions → `.bin` goldens for CTest |
| Optional Rust harness | **serialport** (serialport-rs) | MPL-2.0 | Host-only |
| Speeduino CI peer | **speeduino-serial-sim** | MIT | UART or TCP `:5000`; P1 dialect + poll-loop soak |
| Speeduino client reference | **speeduino-to-mqtt** | MIT | Study layout parse; do not require in gate |
| FOME/rusEFI behavioral oracle | Real FOME HIL; LibreTune/TS as external tools | GPL apps OK as external | Not a CI binary dependency |
| Wi-Fi bridge patterns (P3) | ESP32-Serial-Bridge class (MIT) | MIT | External accessory / knowledge only |

**P0 CI minimum:** host unit tests of framing + CRC + FOME layout extract against **recorded FOME frames**. Speeduino sim is **P1** for second dialect, not a substitute for FOME goldens.

### 15.4 Transport-specific OSS notes

| Transport | Leverage | Caution |
|-----------|----------|---------|
| **USB host** | ESP-IDF examples `cdc_acm_host`, `cdc_acm_vcp` | Prototype may share PHY with USB-Serial-JTAG — document active controller |
| **USB device** | TinyUSB / esp_tinyusb CDC | Same PHY contention as host |
| **UART** | IDF UART driver | Same decoder as USB once bytes arrive |
| **BT SPP (P2)** | — | **ESP32-S3 has no Classic BT.** SPP needs **external module** on UART (or future SoC). NimBLE/Bluedroid on S3 = **BLE only**. |
| **Wi-Fi TCP (P3)** | MIT serial bridges; sim ports 5000 / 29002 | Aether TCP client; reuse TS framing |

### 15.5 Gaps implementers must fill (no drop-in OSS)

1. **TS newserial client in C** (size + CRC32 + response flags + och poll) — write in Aether portable domain.  
2. **FOME och layout pack** — generate from INI; no permissive published pack for face channels.  
3. **FOME protocol simulator** — none under MIT; rely on capture + HIL.  
4. **Board USB role default** — still open (§11 Q1); stack supports host and device once topology freezes.

---

## 16. Handoff checklist (implementation issues)

Suggested follow-on tickets (not this PR):

1. `serial_link` + **USB host CDC-ACM** (`usb_host_cdc_acm`) on prototype; document PHY/role  
2. USB **VCP** quirk path (CP210x/CH340) if FOME is not native CDC on the car install  
3. USB device CDC (`esp_tinyusb`) for PC sim / host bridge (#1)  
4. **Aether TS framing + CRC32** + host golden tests from **real FOME** captures (pyserial)  
5. **FOME** signature/layout pack + och → canonical bus  
6. Canonical bus + face subscription wiring (RPM / load / λ)  
7. P1: Speeduino fixed och + **speeduino-serial-sim** CI peer  
8. Field UART twin of the same decoder  
9. P2: external BT SPP module transport (not S3 Classic radio)  
10. P3: Wi-Fi TCP client transport  
11. (Later) CAN section in this file  

End of `specs/inputs.md`.
