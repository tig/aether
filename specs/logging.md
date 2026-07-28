# Aether logging — format & storage contract

**Rev 0.4 · July 2026**  
**Status:** Contract for implementation planning (not shipped firmware).  
**Scope:** On-device log representation, channel/time/marker model, export matrix, session & naming conventions, interfaces to live bus and host pull.  
**Not in scope:** Live serial/CAN framing ([#5](https://github.com/tig/aether/issues/5) → [inputs.md](inputs.md) when merged), map R/W ([#4](https://github.com/tig/aether/issues/4)), full on-device graphing UI, cloud sync product.

| Related | Link |
|---------|------|
| Product requirements | [spec.md](spec.md) §3.6 |
| Always-on logging + marks | [#2](https://github.com/tig/aether/issues/2) |
| Format strategy issue | [#3](https://github.com/tig/aether/issues/3) |
| Host / LLM log pull | [#1](https://github.com/tig/aether/issues/1) |
| Live serial protocols | [#5](https://github.com/tig/aether/issues/5) |
| Map R/W formats | [#4](https://github.com/tig/aether/issues/4) |
| Survey notes (non-normative) | [docs/research/logging-formats.md](../docs/research/logging-formats.md) |

Phrase book additions that appear on the face stay in [lexicon.md](lexicon.md); this file owns **file-format** terms.

### Operator context (drives P0 export)

| Fact | Value |
|------|--------|
| **Pilot ECU** | **[FOME](https://www.fome.tech/)** (Free Open Motorsports ECU; issue prose “FOAM” → FOME) |
| **Tuner workflow** | Remote / shop tuner works primarily in **Innovate LogWorks** |
| **P0 product outcome** | Operator can pull a session from Aether and **send a file the tuner opens in LogWorks** without a third proprietary tool chain |

Internal store may still be MLVLG (MLV-native). **LogWorks handoff is P0**, not a later “if demand” item.

---

## 1. Goals & non-goals

### Goals

1. **Always log** useful multi-channel time series without operator ritual ([#2](https://github.com/tig/aether/issues/2)).
2. Use a **battle-tested ecosystem format** as the **internal/canonical** on-disk representation — not an Aether-only orphan binary.
3. Open natively in **MegaLogViewer** (and TunerStudio’s log path) with full channel names, units, and **event markers**.
4. **P0: LogWorks handoff** — host **must** produce a file openable in **Innovate LogWorks** so the operator can email/AirDrop/USB a session to a LogWorks-using tuner (FOME-based vehicle context).
5. Support **multi-format export** for spreadsheets, LLM/host tools, and MLV/TS (MSL/CSV/JSON).
6. Fit **ESP32-S3** continuous write: fixed-width records, append-friendly, rotation, recoverable partial files.
7. Align **sequence / user marks** with MLV marker semantics so “the lean spike I marked” is findable in standard tools and by host agents ([#1](https://github.com/tig/aether/issues/1)).

### Non-goals

| Non-goal | Notes |
|----------|--------|
| Inventing a closed proprietary-only log with “converter later” | Forbidden for v1 design |
| Full on-device analysis suite | Export into existing tools is the win |
| On-device write of closed LogWorks-native **`.log`** as canonical store | Spec not open; **export** to LogWorks-openable form is P0 instead |
| Forcing ASAM MDF/MF4 as primary | OEM measurement stack; not the DIY tuner default for AFR review |
| CAN bus framing | Later; logs may **contain** CAN-sourced channels once inputs exist |
| Logger **face** layout | Separate UI work; face only needs logging LED + mark affordance ([afr-face.md](afr-face.md)) |
| Map/table file formats | [#4](https://github.com/tig/aether/issues/4) |

---

## 2. Decision (canonical internal format)

### Recommendation

| Role | Format | Extension |
|------|--------|-----------|
| **Internal / on-device canonical** | **EFI Analytics MLVLG v2** (Binary MLG Logging) | **`.mlg`** |
| **Tuner handoff (LogWorks)** | **LogWorks-openable DIF** (primary) and/or **documented CSV import layout** | **`.dif`** / **`.csv`** |
| Primary MLV/TS interchange | TunerStudio / MLV ASCII datalog | **`.msl`** |
| Universal spreadsheet / scripts | Delimited text (CSV family) | **`.csv`** |
| Host / LLM structured pull | JSON projection of the same channel model | **`.json`** (export / API, not primary store) |

**Rationale (must hold for the choice to remain valid):**

1. **Documented.** MLVLG v2 is published by EFI Analytics as *Binary MLG Logging (MLVLG) file format specification* ([public PDF](http://www.efianalytics.com/TunerStudio/docs/MLG_Binary_LogFormat_2.0.pdf)): magic `MLVLG`, big-endian, header + typed data blocks.
2. **Tuner-first tooling.** `.mlg` opens directly in **MegaLogViewer** / MLV HD; the same ecosystem already dominates MegaSquirt, Speeduino, and **rusEFI** SD/TS logging.
3. **Embedded-friendly.** Fixed field layout, compact raw integers with scale/transform, appendable type-data pairs, **1-byte CRC** per field record — suitable for continuous SD/flash write without a full DB.
4. **Markers are first-class.** Block type `1` carries a per-event **null-terminated comment (50 bytes)** at a 10 µs-resolution timestamp — maps cleanly to user marks and start/end sequence ([#2](https://github.com/tig/aether/issues/2)).
5. **Open converters exist.** Community tools (e.g. [mlg-converter](https://github.com/karniv00l/mlg-converter)) already project MLG → MSL / CSV / JSON; Aether must not depend on them at runtime but they prove the interchange path.
6. **No orphan format.** Identity export is “copy the `.mlg`”; other formats are **projections**, not a second truth store.

### Alternatives rejected as primary (summary)

| Format | Why not canonical on-device |
|--------|----------------------------|
| **`.msl` (ASCII)** | Excellent export; larger, slower, harder to stream at high rate on constrained flash |
| **CSV / TSV only** | Ubiquitous but weak typed metadata; markers usually stripped; units row is convention not guarantee |
| **Innovate LogWorks `.log`** | Compact but **closed** native format; ecosystem is wideband-centric; not open for clean ESP32 writer |
| **LogWorks DIF** | Spreadsheet bridge only; lossy re-import story in LogWorks docs |
| **ASAM MDF4 / MF4** | Strong OEM/measurement standard; heavy for pocket logger + not what tuners open first for AFR pulls |
| **Aether-proprietary binary** | Violates product principle unless every critical path has lossless export (still inferior to writing MLG natively) |

Detail comparison: [docs/research/logging-formats.md](../docs/research/logging-formats.md).

### Conformance rule

- On-device durable logs **must** be valid **MLVLG version 2** files (or a documented subset that MLV accepts — see §5.3).
- Host code **may** re-encode the same session to other formats; re-encode **must not** be required to open the primary file in MLV.
- If a future MLVLG version is required by tooling, bump this rev and document migration; do not silently diverge.

---

## 3. Survey summary (formats compared)

| Format | Structure (short) | Strengths | Weaknesses | Ecosystem | Aether use |
|--------|-------------------|-----------|------------|-----------|------------|
| **MLVLG `.mlg` v2** | BE binary; header (fields, units, scale/transform); type-data blocks: field records + markers | Size, markers, MLV-native, published field layout | BE on little-endian MCU; header fixed at session start; 50-char marker text | MLV, TS, rusEFI SD, Speeduino-class, converters | **Canonical store** |
| **MSL `.msl`** | Text header lines + tab columns: **name row**, **units row**, then samples; markers as special lines | Debuggable, MLV/TS friendly, easy host parse | Larger; slower write; less dense on flash | TS default PC logs, MLV, SpeedyLogger-class tools | **P0 export** |
| **CSV / `;` CSV** | Delimited rows; optional units row | Excel, Virtual Dyno, scripts | Markers often lost; weak schema | Everywhere | **P0 export** |
| **JSON** | Object: fields + records + markers | LLM/host (#1), APIs | Verbose; not tuner-native graph | Host tools | **P0 host pull / P1 file export** |
| **LogWorks `.log`** | Proprietary compact + settings | Native LogWorks UX | Spec not open; reverse-engineer tax — **not** on-device canonical | Innovate LogWorks | **Not** on-device writer; optional host research only |
| **LogWorks DIF** | LogWorks dual open/save format; engineering quantities; also Excel path | **Tuner can open in LogWorks** without Innovate hardware chain | Some loss vs native `.log` (filters/settings); channel naming must match LogWorks expectations | Innovate LogWorks, Excel | **P0 export** (tuner handoff) |
| **MS3/FRD SD proprietary** | ECU-specific binary, TS converts | Existing MS installs | Not general; TS conversion step | MegaSquirt SD | Out of scope as Aether writer |
| **Speeduino SD** | CSV and/or MLG-class per firmware path | Open ECU precedent | Varies by board/firmware age | Speeduino + MLV | Validate interop; do not fork |
| **MDF4 / MF4** | ASAM blocks, multi-rate, bus logging | Industry measurement exchange | Complexity, tooling outside DIY AFR | Vector, asammdf, CAN loggers | **P2+** only if CAN bulk archive needs it |

---

## 4. Channel model

### 4.1 Canonical channel object (logical)

Every logged quantity is a **channel**:

| Field | Requirement | Notes |
|-------|-------------|--------|
| `name` | **Must** | Stable ASCII identifier ≤ 33 chars payload (MLG name field is 34 including NUL) |
| `units` | **Must** | ≤ 9 chars payload (MLG units field 10 with NUL); empty only if dimensionless flag/bitfield |
| `storage_type` | **Must** | One of MLG scalar types: U08, S08, U16, S16, U32, S32, S64, F32 (prefer integer + scale) |
| `scale`, `transform` | **Must** | `display = (raw + transform) * scale` (MLG formula) |
| `digits` | **Should** | Display decimals for float style |
| `category` | **Should** | MLG v2 category (e.g. `Mixture`, `Engine`, `Aether`) for MLV grouping |
| `source` | **Should** (metadata) | `wideband`, `ecu`, `derived`, `user` — may live in Info Data if not a column |
| `quality` | **Should** | Separate channel or bitfield: sensor valid / heating / fault |

**Internal mixture truth:** store and prefer **lambda** as the physics channel; AFR is `λ × stoich` for a declared fuel scale. Display/export may present AFR; do not store two disagreeing mixture truths without documenting which is primary.

### 4.2 Required channels (P0 session)

A valid Aether P0 log **must** include:

| Channel name (canonical) | Units | Intent |
|--------------------------|-------|--------|
| `Time` | `s` | Session-relative time (also carried by MLG record timestamp; keep column for MSL/CSV parity with TS logs) |
| `RPM` | `rpm` | Engine speed |
| `TPS` | `%` | Throttle / load proxy (0–100); use `WOT` display rules only on face, not as log name |
| `Lambda` **or** `AFR` | `λ` / `AFR` | At least one mixture channel; **prefer `Lambda`** + optional `AFR` derived |

**Should** include when the input exists:

| Channel | Units | Notes |
|---------|-------|--------|
| `MAP` | `kPa` | Preferred load axis for table work with [#4](https://github.com/tig/aether/issues/4) |
| `AFR` | `AFR` | If `Lambda` is primary, still export AFR for tuner familiarity |
| `Lambda2` / `AFR2` | | Dual wideband ([spec.md](spec.md) §3.7) |
| `FuelPress` | `kPa` or `psi` | Document unit in field metadata |
| `CLT`, `IAT` | `°C` (prefer) | Convert on export if user wants °F |
| `Battery` | `V` | |
| `AetherMark` | bit/enum | Optional parallel to marker blocks for tools that ignore markers |

### 4.3 Naming rules

- **Must** use stable names across firmware revs for the same physical signal (breaking renames require export aliases).
- **Must not** use spaces in **canonical** names if avoidable; if ecosystem logs use spaces (`Accel Enrich`), prefer underscore form in Aether (`AccelEnrich`) and document MLV display name if needed.
- Prefix Aether-only derived channels with `Ae` or category `Aether` (e.g. `AeLeanAlarm`) so they are obvious next to ECU fields.
- When logging ECU-native names from a protocol ([#5](https://github.com/tig/aether/issues/5)), **prefer the ECU/TS name** for that channel so side-by-side comparison with TS logs stays sane.

### 4.4 Units policy

- Prefer **SI-ish tuner norms**: `kPa`, `°C`, `s`, `rpm`, `%`, `V`, lambda dimensionless as `λ` or `Lambda`.
- Stoich factor used for AFR conversion **must** be recorded in **Info Data** (and setup profile when that exists).
- Display filtering on the face **must not** alter logged raw values; log rate and display rate are independent ([spec.md](spec.md) §3.4).

---

## 5. Time base

| Concern | Contract |
|---------|----------|
| **Session epoch** | MLG header Unix timestamp (32-bit UTC seconds) when RTC/NTP/host time known; **0** if unknown (allowed by MLG). |
| **Internal clock** | Writer **must** keep a full-width monotonic clock (`int64_t` ms domain — see plate HAL notes) for all channel alignment and the `Time` channel (session-relative seconds, float or scaled int). |
| **MLG u16 field meaning** | Per **MLVLG v2**, each data/marker block’s 16-bit timestamp is the **interval since the previous block**, in units of **10 µs/tick** — **not** the low 16 bits of an absolute clock and **not** a free-running counter that “wraps.” MegaLogViewer **accumulates** these deltas to place samples. |
| **Encode rule (must)** | `delta_ticks = (t_now − t_prev) / 10µs` (integer), where `t_*` are from the full-width monotonic clock. Emit that value in the u16 field. First block after the header: use **0** or the interval from session start — document choice; MLV still builds a timeline by accumulation. |
| **Overflow (must)** | Max representable interval is **65535 × 10 µs ≈ 0.65535 s**. If the real gap is larger (pause, sleep, long marker gap), the writer **must not** store `gap mod 65536`. Instead **split**: emit one or more intermediate field or marker blocks (e.g. hold last sample, or a `NOTE gap` marker) so each on-wire delta ≤ 65535 ticks, **or** end the session and start a new `.mlg`. Silent modulo is a **spec violation** (causes MLV timeline jumps). |
| **Clock domain** | Device monotonic for alignment of channels; wall clock only for file metadata and host correlation. |
| **Sync across sources** | All channels in one record share one sample instant (nearest-sample or interpolated — **document per input** in inputs spec; default nearest). |
| **Dropped samples** | Prefer gap in `Time` over fake flat-hold; optional `AeDrop` counter channel; still encode honest MLG deltas (including split blocks for long gaps). |

---

## 6. Markers & events ([#2](https://github.com/tig/aether/issues/2))

### 6.1 Transport in the file

Use **MLG block type 1 (Marker)**:

- Rolling counter + 16-bit timestamp + **50-byte NUL-terminated message**.
- Rendered in MegaLogViewer as vertical marks with comment text.

ASCII **`.msl` export** **must** preserve markers as distinct lines (not as fake samples). **CSV export** **should** either:

- emit a parallel `markers.csv` / sidecar, or  
- include a `Marker` column (empty on normal rows),  

and **must document** which approach shipped (markers are easy to lose in naive CSV).

### 6.2 Message grammar (Aether conventions)

Marker text is freeform in MLG; Aether **should** use a small prefix grammar so hosts/LLMs can parse:

| Prefix | Meaning | Example |
|--------|---------|---------|
| `MARK ` | User mark (default button / voice) | `MARK lean tip-in` |
| `SEQ_START ` | Start of operator sequence | `SEQ_START cold start` |
| `SEQ_END ` | End of sequence | `SEQ_END cold start` |
| `DRIVE ` | Drive / session tag (optional inline) | `DRIVE street` |
| `ALARM ` | Auto mark from safety logic | `ALARM lean under load` |
| `NOTE ` | Longer note (truncated to 50) | `NOTE fuel pressure dip` |

Rules:

- **Must** truncate safely to 49 characters + NUL; prefer keeping the prefix.
- **Must** support mark without text → `MARK` alone.
- **Should** support speech-to-text fill when hardware/host provides it ([#2](https://github.com/tig/aether/issues/2)); offline device may only store `MARK`.
- Nested sequences: **should** allow stack or reject with UI feedback — pick one in implementation and document; default recommendation: **single open sequence** (second `SEQ_START` auto-closes previous with `SEQ_END auto`).

### 6.3 Drive tagging

Two complementary mechanisms (both allowed):

1. **File / directory convention** (§8) — primary for “this whole file is street vs track.”
2. **`DRIVE` marker** and/or Info Data line `DriveTag: …` — for mid-session retag.

### 6.4 Always-on vs mark UX

- Logging **on** by default when media available and inputs configured ([#2](https://github.com/tig/aether/issues/2)).
- Face **logging LED** remains the only required on-face logging chrome ([afr-face.md](afr-face.md)).
- Mark control: hard key long-press, touch affordance on a later page, or host command — **not** specified as face geometry here.

---

## 7. On-device storage model

### 7.1 Session = one `.mlg` file

MLVLG associates **one file ↔ one datalog session** (begin → end). Aether maps:

| Concept | Behavior |
|---------|----------|
| **Session start** | Write header (field defs + Info Data), then append blocks |
| **Session end** | Flush; close file; optional final `NOTE session end` marker |
| **Always-on** | Auto-start session on boot when logging enabled; rotate per §7.3 |
| **Crash / power loss** | Last durable flash/SD sync wins; reader **must** tolerate truncated final record (stop at last good CRC) |

### 7.2 Write path requirements

- **Must** buffer in RAM and flush in whole records (field block or marker block).
- **Must** use big-endian field packing per MLG (byte-swap on ESP32-S3).
- **Should** fsync/commit policy balance wear vs loss window (open question: media type).
- **Must not** rewrite the entire file each sample.

### 7.3 Rotation

Rotate to a new file when **any** configured limit hits:

| Trigger | Default intent (tunable) |
|---------|---------------------------|
| Max size | e.g. 8–16 MiB per file (open: final numbers with media) |
| Max duration | e.g. 30–60 min continuous |
| Wall-clock day boundary | Optional |
| User “new session” | Explicit |
| Media nearly full | Stop gracefully + face/host warning |

Rotation **must** finalize field definitions consistently (same channel set across a drive unless profile changes mid-day — if profile changes, new session **must** start).

### 7.4 Media (open where unknown)

Product hardware leaves media open ([spec.md](spec.md) §2). This contract requires **one durable store** at ship; candidates:

| Media | Notes |
|-------|--------|
| **microSD** | Preferred for always-on capacity (rusEFI/Speeduino precedent) |
| **Internal flash / littlefs** | Short ring or few sessions; wear-aware |
| **Host-only stream** | USB/BT/Wi-Fi live mirror without local retain — allowed as mode, not a substitute for durable always-on when media exists |

**Open questions:** which SKU has SD; max flash budget for logs; USB MSC expose vs pull API only.

### 7.5 Capacity sketch (planning, not acceptance)

Order-of-magnitude: ~20–40 channels of mostly U16 @ 20–50 Hz is a few MB/hour (rusEFI cites ~20 MB/h @ 20 Hz for rich SD logs). Aether P0 channel counts are smaller; treat **hours per GB** as design comfort, not a hard KPI until channel set freezes.

---

## 8. File naming & folder conventions

### 8.1 Default file name

```text
AETHER_YYYYMMDD_HHMMSS[_TAG].mlg
```

| Part | Rule |
|------|------|
| `AETHER_` | Constant prefix |
| `YYYYMMDD_HHMMSS` | Session start wall time if known; else monotonic `boot` time like `B00012345` |
| `_TAG` | Optional drive/profile tag: `STREET`, `TRACK`, `DYNO`, `COLD`, custom ≤ 16 chars `[A-Za-z0-9_-]` |

Export twins:

```text
AETHER_YYYYMMDD_HHMMSS[_TAG].msl
AETHER_YYYYMMDD_HHMMSS[_TAG].csv
AETHER_YYYYMMDD_HHMMSS[_TAG].json
```

### 8.2 Folder layout (when filesystem present)

```text
/AETHER/
  logs/
    2026/
      07/
        AETHER_20260728_183045_STREET.mlg
  export/          # host-created or on-device export output
  meta/
    last_session.json   # optional pointer for host pull
```

**Should** keep path depth FAT-friendly. Exact mount root depends on SD vs flash (open).

### 8.3 Info Data content (MLG unstructured string)

**Should** include newline-separated lines such as:

```text
Aether <firmware-version>
Capture Date: <local or UTC>
FuelStoich: 14.70
DriveTag: STREET
Profile: <name>
ECU: <identity if known>
```

---

## 9. Export matrix

| Target | Priority | Producer | Fidelity notes |
|--------|----------|----------|----------------|
| **`.mlg` MLVLG v2** | **P0** | Device (canonical) + host re-pack if needed | Identity; markers retained; MLV open |
| **LogWorks DIF (`.dif`)** | **P0 — tuner handoff** | Host **must** | File **opens in Innovate LogWorks** with Time + λ/AFR + RPM + load (+ other P0 channels). Prefer DIF because LogWorks documents `.log` **or** `.dif` as first-class log files ([LogWorks 3 manual](https://www.racedom.com/media/catalog/down/LogWorks3_Manual.pdf)). Engineering units; document any marker loss. |
| **LogWorks CSV import layout** | **P0 alternate** | Host **must** if DIF blocked | Documented row layout that LogWorks (or common LogWorks import recipes) accepts; golden sample verified in LogWorks. Use when DIF writer is incomplete — **must not** ship “CSV only for Excel” as the sole tuner path. |
| **`.msl`** | **P0** | Host **must**; device **should** if CPU/media allow | Tab-separated; name + units rows; markers as lines; scaled engineering values |
| **`.csv`** (generic) | **P0** | Host **must**; device optional | Comma or semicolon selectable; document delimiter; markers via column or sidecar |
| **JSON** (file or HTTP/BT payload) | **P0** for **host pull API**; **P1** as on-disk export | Host / bridge | Fields, records, markers, info — for [#1](https://github.com/tig/aether/issues/1) LLM tools |
| Virtual Dyno–style `;` CSV | **P1** | Host | Same as CSV with `;` and required column aliases if documented |
| LogWorks native **`.log`** | **P2** research only | Host | Closed format; only if DIF/CSV handoff fails real tuners |
| MDF4 | **P2+** | Host | Only if CAN archive / OEM toolchain appears |
| Parquet / DB | Out of scope | — | |

### 9.1 LogWorks handoff (normative P0)

**Operator story:** FOME-based car → Aether always-on log → pull session → send file to tuner → tuner opens in **LogWorks** and graphs mixture vs RPM/load.

| Requirement | Rule |
|-------------|------|
| **Must** | One host action produces a **LogWorks-openable** artifact (`.dif` preferred, or documented CSV layout). |
| **Must** | Include at least `Time`, mixture (`Lambda` and/or `AFR`), `RPM`, and load (`TPS` and/or `MAP`) in engineering units. |
| **Must** | Golden acceptance: open the export in LogWorks (manual QA or CI screenshot/note) without third-party converters. |
| **Should** | Preserve user/`SEQ_*` marks as channels or annotations LogWorks can show; if not, emit a sidecar mark list with the same time base and label the export **lossy for marks**. |
| **Must not** | Claim P0 complete if the only exports are `.mlg`/`.msl` that the LogWorks-using tuner cannot open. |
| **Must not** | Require the tuner to install MegaLogViewer solely to read Aether logs (MLV remains first-class for the operator; LogWorks is first-class for the **tuner handoff**). |

Native LogWorks **`.log`** remains non-canonical (closed). Reverse-engineering it is **not** P0 if DIF/CSV handoff works.

### Export rules

- **Must** apply scale/transform so exported numeric values are engineering units unless the format stores raw+scale (MLG).
- **Must** preserve marker timestamps relative to the same time base (MLG/MSL); LogWorks exports follow §9.1.
- **Should** keep channel order stable: `Time`, mixture, `RPM`, load, then others.
- Lossy exports **must** be labeled (e.g. CSV without markers → warn in host UI).

---

## 10. Host pull path ([#1](https://github.com/tig/aether/issues/1))

High level only (transport detail lives with wireless/host specs):

| Path | Behavior |
|------|----------|
| **USB** | CDC or MSC: list sessions, download `.mlg`, optional on-the-fly `.msl`/`.csv`/`.dif`/JSON |
| **Bluetooth / Wi-Fi** | Same logical **log store API**: list → get metadata → get bytes / stream convert |
| **SD physical pull** | User removes card; files already MLV-ready |
| **LLM / agent** | Prefer JSON summary + deep-link to full `.mlg`, or full JSON for short sessions; use marker grammar to answer “at the mark…” |

**Must** expose per-session: filename, start time, duration, size, drive tag, marker index (time + text).

---

## 11. Interfaces to live bus (#5) and maps (#4)

### 11.1 Live bus ([#5](https://github.com/tig/aether/issues/5) / future `inputs.md`)

```text
  transport (USB/UART/BT/Wi-Fi/CAN later)
       → decoder
       → canonical live channels (name, value, quality, timestamp)
            ├→ AFR face (decimated / filtered)
            └→ logger writer (full log rate) → .mlg
```

- Face and logger **share** the canonical channel model; they **must not** each re-parse ECU protocols.
- Log rate **may** exceed display rate.
- Logger **must** tolerate missing optional channels (NaN/sentinel + quality) without stopping the session.

### 11.2 Maps ([#4](https://github.com/tig/aether/issues/4))

- Logs do **not** embed full tunes.
- Markers + RPM/load/mixture streams are the **evidence** input to “enrich this region” workflows.
- Export of correction hints (measured ÷ target) is a **host/analysis** feature layered on this format, not a second log format.

---

## 12. MLVLG implementation notes (normative subset)

Implementers **must** follow the published MLVLG v2 layout. Critical constants:

| Item | Value |
|------|--------|
| Magic | `MLVLG` + NUL (6 bytes) |
| Version | `0x0002` |
| Endianness | **Big-endian** |
| Logger field size (v2) | **89 bytes** per field (includes 34-byte category) |
| Data block type 0 | Field record: type, counter, **u16 inter-record delta (10 µs/tick)**, packed raw fields, **u8 CRC** (sum of raw field bytes) |
| Data block type 1 | Marker: type, counter, **u16 inter-record delta (10 µs/tick)**, **50-byte** message |
| Display formula | `(raw + transform) * scale` |

**Bitfields:** supported by MLG; Aether **may** defer bitfield channels to P1 if unused.

**Validation:** host tests **should** round-trip a fixture through a known-good parser (e.g. community MLG parser or MLV manual open in QA).

---

## 13. Phased implementation outline

| Phase | Deliverable | Exit criteria |
|-------|-------------|---------------|
| **P0a** | Channel model + MLG writer library (host-first or firmware unit-testable) | Writes v2 file openable in MLV; markers visible |
| **P0b** | Always-on session + rotation on available media | Boot → file grows; power-loss leaves openable prefix |
| **P0c** | User mark + `SEQ_START`/`SEQ_END` | Markers in MLV; grammar stable |
| **P0d** | Host export: **LogWorks DIF (or CSV layout)** + MSL + generic CSV; pull list/download over USB | **Tuner opens export in LogWorks**; operator opens `.mlg`/`.msl` in MLV |
| **P0e** | FOME-sourced channel naming aliases for LogWorks-friendly labels | Documented alias table; golden LogWorks session from FOME live path (#5) |
| **P1** | JSON pull for agents; drive tags; dual AFR channels; alarm auto-markers | [#1](https://github.com/tig/aether/issues/1) can fetch + cite marks |
| **P1b** | Device-side MSL/CSV/DIF if media/CPU allow | Optional convenience |
| **P2** | Extra exports (Virtual Dyno presets; native `.log` only if DIF fails field tuners) | Data-driven |
| **P2+** | On-device review/playback UI | Separate UX spec |

---

## 14. Implementation leverage (OSS)

**Normative-ish for implementers.** Prefer existing **permissive** code over reimplementation. Full survey: [docs/research/logging-formats.md](../docs/research/logging-formats.md) §11.  
**License rule:** **do not** link GPL/LGPL/AGPL into Aether **firmware**. Copyleft is allowed only as **standalone host CLIs** (subprocess / separate install), not as a linked product library.

### 14.1 Recommended stack by phase

| Phase | Metal (ESP-IDF / C) | Host (Python gate + optional Node) | Do not reimplement if… |
|-------|---------------------|------------------------------------|------------------------|
| **P0a** MLG writer | **Write** Aether `log_mlg` (C) from [MLVLG v2 PDF](http://www.efianalytics.com/TunerStudio/docs/MLG_Binary_LogFormat_2.0.pdf): header, field defs, type-0 sample, type-1 marker, CRC | Host twin writer (`struct` packing) **or** unit-test the C lib on host; **verify** with [mlg-converter](https://github.com/karniv00l/mlg-converter) (**MIT**, parse v1/v2 → MSL/CSV/JSON) + MLV manual open | …mlg-converter already **parses** your golden file; do not invent a second MLG **parser** for CI |
| **P0b** session/media | **ESP-IDF FatFs + SDMMC** (SD) and/or **littlefs** (**BSD-3-Clause**) for internal flash; append whole records; rotation | Host fixtures only | …ESP-IDF already mounts SD/FAT and littlefs; do not invent a filesystem |
| **P0c** markers | Type-1 blocks + Aether grammar (§6) in the same C writer | Assert markers via mlg-converter / MLV | …MLG already has markers |
| **P0d** exports | Optional later (P1b) | **Must:** MSL + generic CSV + **LogWorks DIF or CSV layout** via **Python stdlib** (+ small DIF writer). Optional: SheetJS CE (**Apache-2.0**) `dif` book type if host is Node | …stdlib CSV/JSON suffice; do not pull GPL **racing-data-converter** into the product tree |
| **P0e** FOME names | N/A (channel aliases) | Document aliases from FOME/TS logs; live path is [#5](https://github.com/tig/aether/issues/5) | …do not fork FOME (**GPL-3.0**) for naming tables |
| **P1** JSON pull | Optional device JSON | stdlib `json` for [#1](https://github.com/tig/aether/issues/1) | …no third-party JSON log format lib required |
| **P2+** MDF | No | [asammdf](https://pypi.org/project/asammdf/) (**LGPL-3.0+**, host careful) or [mdflib](https://github.com/ihedvall/mdflib) (**MIT**) only if product needs MF4 | …not P0 |

### 14.2 On-device: what we write vs vendor

| Piece | Source |
|-------|--------|
| MLVLG v2 binary packing, markers, CRC, 10 µs time wrap | **Aether-owned C** (no permissive embedded MLG library found) |
| Byte-swap helpers, ring buffer, rotation | Aether |
| SD / flash FS, VFS, SDMMC | **ESP-IDF** components (Apache-2.0 / BSD-style FatFs) |
| littlefs (if flash SKU) | **littlefs** BSD-3-Clause via ESP component registry |
| rusEFI / FOME / Speeduino / Speeduino-Copilot log writers | **Study only** — all **GPL**; **must not** copy into firmware |

### 14.3 Host: depend / vendor for gates

| Need | Recommended | Notes |
|------|-------------|-------|
| MLG **read** / golden regression | **mlg-converter** (MIT) as CI tool or `npm` devDep | Optional secondary: [hyper-tuner/mlg-cli](https://github.com/hyper-tuner/mlg-cli) (MIT, Rust) |
| MLG **write** (fixtures) | Aether Python or shared C | Do not vendor [racing-data-converter](https://github.com/BenergyRacing/racing-data-converter) (**GPL-2.0**) into product; algorithm reference only |
| MSL / CSV / JSON export | Python stdlib | Match §9 dialects; preserve markers in MSL |
| LogWorks handoff | Spreadsheet **DIF** writer (Python) or documented CSV; optional SheetJS CE Apache-2.0 | LogWorks manuals treat DIF as Excel-friendly engineering dump — validate open in real LogWorks (§9.1) |
| Manual QA | MegaLogViewer (operator), LogWorks (tuner) | Proprietary viewers; not libraries |

### 14.4 Explicit non-leverage (reject for product link)

- **GPL-3.0 / GPL-2.0 firmware:** rusEFI, FOME, Speeduino, Speeduino-Copilot — no static or dynamic link into Aether metal.
- **AGPL-3.0:** UltraLog — external viewer only, not a dependency.
- **Unknown license:** SpeedyLogger — do not copy.
- **Closed:** LogWorks native `.log` writer, MegaLogViewer internals — export **to** them, do not embed.

### 14.5 Gaps Aether must invent

1. Permissive **continuous MLG appender** for ESP32-S3 (RAM buffer, flush policy, truncated-file recovery).
2. **Host MLG writer** under project license for golden fixtures (community writers are parse-only MIT or write under GPL).
3. **LogWorks-validated** DIF/CSV column layout for P0 channels.
4. Marker-preserving **MSL** and marker policy for CSV (column or sidecar).

---

## 15. Open questions

Do **not** invent hardware answers in firmware PRs until product decides:

1. Logger media for v1 SKU: SD vs internal flash vs host-only?
2. Default sample rate (face vs log): e.g. display 10–20 Hz, log 20–50 Hz?
3. Max channels in P0 profile?
4. RTC source (none / ECU / host sync / GPS later)?
5. USB MSC vs explicit pull API as primary offline path?
6. Whether speech mark transcription runs on-device or only via host ([#2](https://github.com/tig/aether/issues/2))?
7. Exact FAT mount layout and wear-leveling budget?
8. ~~FOAM pilot?~~ **Resolved for product:** pilot ECU is **FOME**; live path is [#5](https://github.com/tig/aether/issues/5) / `inputs.md`.
9. Exact LogWorks DIF channel header strings that match the tuner’s LogWorks version (validate with real LogWorks install)?
10. Prefer email-sized compressed export vs full-rate DIF for long always-on sessions?

---

## 16. Acceptance criteria (future implementation)

A logging implementation claim is **done** for P0 when:

1. [ ] Device or host writer produces **MLVLG v2** `.mlg` with at least `Time`, mixture (`Lambda` or `AFR`), `RPM`, and `TPS` (or `MAP`).
2. [ ] File opens in **MegaLogViewer** without a custom loader plugin.
3. [ ] User marker appears at correct relative time with readable text.
4. [ ] `SEQ_START` / `SEQ_END` markers round-trip in `.mlg` and `.msl` export.
5. [ ] Continuous logging survives ≥ 10 minutes without drop-to-zero timebase; rotation creates a new valid file.
6. [ ] Host export produces `.msl` and generic `.csv` with engineering units.
7. [ ] **LogWorks handoff:** host produces `.dif` (preferred) or documented CSV layout; file **opens in Innovate LogWorks** with Time + mixture + RPM + load visible.
8. [ ] Operator can send that LogWorks file to a third party without requiring them to install MegaLogViewer.
9. [ ] Truncated final record does not prevent opening prior samples.
10. [ ] No reliance on an undocumented Aether-only binary as the only durable form.
11. [ ] Documented channel list and marker grammar match this spec rev.
12. [ ] Face logging indicator still matches [afr-face.md](afr-face.md) (no extra face chrome required by this spec).

---

## 17. Lexicon (logging)

| Term | Meaning |
|------|---------|
| **Session** | One MLG file from open to close/rotate |
| **Channel** | Named time series field with units and scale |
| **Marker** | MLG type-1 event with text; not a sample row |
| **Sequence** | Operator-bounded interval (`SEQ_START`…`SEQ_END`) |
| **Drive tag** | Label for duty (street/track/…) via name and/or marker/Info |
| **Canonical log** | On-device `.mlg` MLVLG v2 |
| **Projection** | Export (MSL/CSV/JSON/DIF) derived from canonical |
| **Tuner handoff** | LogWorks-openable export for a remote/shop tuner |

---

## 18. References (research anchors)

- EFI Analytics, *Binary MLG Logging (MLVLG) file format specification* v2 — http://www.efianalytics.com/TunerStudio/docs/MLG_Binary_LogFormat_2.0.pdf  
- MegaLogViewer / TunerStudio product pages (EFI Analytics)  
- rusEFI Logging Guide (TS + SD → `.mlg`) — https://wiki.rusefi.com/Logging-Guide/  
- Speeduino SD logging docs / community MLG+CSV practice  
- Innovate LogWorks manuals (`.log` native, DIF for Excel / spreadsheet path)  
- mlg-converter (MIT; MLG → MSL/CSV/JSON parse) — https://github.com/karniv00l/mlg-converter  
- mlg-cli (MIT; Rust convert) — https://github.com/hyper-tuner/mlg-cli  
- racing-data-converter (GPL-2.0; host-only reference writer) — https://github.com/BenergyRacing/racing-data-converter  
- littlefs (BSD-3-Clause) — https://github.com/littlefs-project/littlefs  
- ASAM MDF overview (secondary) — https://www.asam.net/standards/detail/mdf/  

Non-normative narrative + OSS tables: [docs/research/logging-formats.md](../docs/research/logging-formats.md).
