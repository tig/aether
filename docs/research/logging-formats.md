# Research notes — ECU / tuner log formats

**Date:** July 2026  
**Purpose:** Survey backing for [specs/logging.md](../../specs/logging.md). **Non-normative** — the contract is the spec.  
**Issue:** [tig/aether#3](https://github.com/tig/aether/issues/3)

---

## 1. EFI Analytics MLVLG (`.mlg`)

### Sources

- Public format PDF: [MLG_Binary_LogFormat_2.0.pdf](http://www.efianalytics.com/TunerStudio/docs/MLG_Binary_LogFormat_2.0.pdf) (Phil Tobin / EFI Analytics; v2 notes Aug 2022: 4-byte info start, field groups/categories).
- Community parser/writer reference: [karniv00l/mlg-converter](https://github.com/karniv00l/mlg-converter) (parse v1/v2; export CSV/MSL/JSON).

### Structure (v2 highlights)

- **File = one session.** Extension `.mlg` / `.MLG`.
- **Endianness:** big-endian throughout.
- **Header**
  - Magic: `MLVLG\0` (6 bytes)
  - Format version: `0x0002`
  - Unix time (u32 seconds), optional zeros
  - Info Data start (u32), Data begin index (u32)
  - Record length (u16), num logger fields (u16)
  - Logger Field array: **89 bytes × N** in v2 (55 bytes in v1 — no category)
  - Optional bit-field name blob
  - Optional Info Data: unstructured ASCII (firmware string, capture date, …)
- **Logger Field (scalar)**
  - Type: U08/S08/U16/S16/U32/S32/S64/F32
  - Name (34), Units (10), display style, scale (f32), transform (f32), digits, category (34)
  - `display = (raw + transform) * scale`
- **Data blocks (type-data pairs)**
  - **Type 0 — field data:** counter (u8), timestamp (u16 @ **10 µs/bit**), packed raw fields, **CRC u8** = sum of raw field bytes
  - **Type 1 — marker:** counter, timestamp, **50-byte** NUL-terminated message (vertical red line in MLV)

### Strengths

- Designed for **viewer-direct** open with no ECU definition file required for basic graphing.
- Dense binary; good for SD continuous logging (rusEFI, Speeduino-class usage).
- **Markers first-class** — rare among simple CSV loggers.
- Rich enough metadata (units, scale, categories) for serious multi-channel work.

### Weaknesses

- Big-endian on ESP32 (swap cost — small).
- Header implies **channel set fixed for the session** (rotation = new file if set changes).
- 16-bit 10 µs timestamp wraps ~0.655 s — need external full-range time reconstruction.
- Spec is “open PDF from vendor,” not an IETF/ISO standard; still the de facto DIY EFI log binary.

### Ecosystem

- **MegaLogViewer** / MLV HD native.
- **TunerStudio** can log/export MLG; MS3 SD paths convert into MLV-viewable forms.
- **rusEFI:** both TS logging and onboard SD produce `.mlg` for MLV ([Logging Guide](https://wiki.rusefi.com/Logging-Guide/)); ~20 MB/h cited at 20 Hz default SD period.
- Speeduino community: SD logging and tools often target MLV (CSV and/or MLG depending on path/age).

### Import vs export for Aether

- **Write (export from device):** primary.
- **Read:** useful for host tools / tests; not required on-device.

---

## 2. TunerStudio / MegaLogViewer ASCII (`.msl`)

### Structure (observed / converter-aligned)

- Leading **info lines** (firmware, “Capture Date: …”) — free text.
- **Header row:** channel names, **tab-separated**.
- **Units row:** units, tab-separated (TS added units to log files historically; MLV expected them).
- **Data rows:** engineering values (or scaled), tab-separated.
- **Markers:** special lines (not full sample rows); MLG→MSL converters emit marker message lines; CSV converters often **strip** markers.

### Strengths

- Human-readable; diff-friendly; easy for scripts and support email.
- Default mental model for many MegaSquirt tuners (“the .msl log”).

### Weaknesses

- Larger and slower to write at high rate on MCU flash.
- Parsing edge cases (quotes, locales) if not careful.
- Less ideal as always-on internal format on ESP32.

### Aether role

- **P0 export** twin of `.mlg`.

---

## 3. Generic CSV / semicolon CSV

### Structure

- Delimiter `,` or `;` (European / Virtual Dyno often `;`).
- Optional units row.
- No single standard for markers or bitfields.

### Strengths

- Universal: Excel, Google Sheets, Python, Virtual Dyno, many “almost any log” loaders in MLV HD.

### Weaknesses

- Metadata loss; marker loss; type ambiguity.
- Easy to produce incompatible dialects.

### Aether role

- **P0 export** with documented dialect; optional `;` preset as P1.

---

## 4. Innovate LogWorks

### Sources

- LogWorks 2/3 user manuals (Innovate Motorsports / MTS).
- Formats described:
  - **`.log`** — native compact; keeps measurement points, filters, input settings; version skew between LW2/LW3.
  - **`.dif`** — spreadsheet interchange; **engineering values already applied**; re-import can lose manipulation flexibility (manual warns DIF is for Excel, not full fidelity round-trip).

### Strengths

- Mature wideband + MTS log-chain UX; lambda stored ~10-bit over 0.5–1.523 λ in stream descriptions; good AFR-centric analysis.

### Weaknesses

- **Native `.log` not openly specified** for third-party embedded writers.
- Ecosystem narrower than MLV for full standalone ECU channel sets.
- DIF is not a great canonical store.

### Aether role

- Do **not** use as internal format.
- Users who need LogWorks can use CSV/DIF-like export later (**P2**); P0 success does not depend on LogWorks.

---

## 5. rusEFI

- Documents **TS logging** and **SD card logging**, both aimed at **`.mlg` + MegaLogViewer**.
- SD: configurable period (default 50 ms / 20 Hz); USB mass-storage style access vs logging mode arbitration when powered by USB.
- Validates “write MLG on embedded ECU-class hardware” as production practice, not theory.

---

## 6. Speeduino / MegaSquirt family

- **PC path:** TunerStudio → `.msl` / `.mlg` depending on settings and product generation.
- **SD path:** historically CSV and binary approaches; TS “Convert Binary Log (MS3, FRD)” exists for MS SD formats.
- Community loggers (e.g. SpeedyLogger) emit **`.msl`** sequences (`dl000001.msl` style).
- Interop lesson: **MLV + MSL/MLG** is the lingua franca; Aether should speak it rather than invent FRD-like SD binaries.

---

## 7. FOAM and other open ECUs

- Issue #3 asks to survey FOAM. At research time, **no durable public FOAM-native log format** was found that is widely used as an interchange standard comparable to MLG/MSL.
- Practical approach: if FOAM (or peers) already export CSV/MLG-compatible streams, **consume via live protocol (#5)** and still **store MLG**. If a FOAM-native file appears later, add an import adapter — do not block the canonical choice.
- Recorded as **open question** in the contract.

---

## 8. HP Tuners / closed commercial scanners

- Typically proprietary session formats plus **CSV export** for sharing.
- For Aether (open/serial-first pocket logger), CSV export covers the “send me a log” social path; reverse-engineering VCM Scanner binary is out of scope.

---

## 9. ASAM MDF / MF4

### Notes

- Industry standard for measurement/calibration data; multi-rate, bus logging, large tool ecosystem (Vector, asammdf, CAN loggers writing MF4).
- Excellent for high-volume CAN capture and OEM workflows.
- **Heavy** relative to a pocket AFR logger’s P0 needs; DIY tuners graph AFR pulls in **MLV**, not primarily MDF studios.

### Aether role

- Mentioned for honesty; **P2+** host export only if product grows a serious CAN archive story.

---

## 10. Decision matrix (why MLVLG wins)

| Criterion | MLG | MSL | CSV | LogWorks .log | MDF4 | Proprietary Aether |
|-----------|-----|-----|-----|---------------|------|--------------------|
| Open enough to implement | Yes (PDF) | Yes (observe) | Yes | No | Yes (ASAM, complex) | N/A |
| Efficient continuous write | **Best** | Weak | Weak | Unknown closed | Medium | Custom |
| Markers / events | **Yes** | Partial | Poor | App-specific | Yes (events) | Custom |
| MLV / tuner first-class | **Yes** | Yes | Via loader | No | No | No |
| LLM/host parse | Via convert | Easy | Easy | Hard | Libraries | Easy if we invent |
| Matches #2 always-on | **Yes** | OK small | OK small | N/A | Overkill | Tempting but wrong |

**Conclusion:** implement **MLVLG v2 on-device**, export **MSL + CSV (+ JSON for agents)**. Same philosophy as issue #3: best existing format internal, multi-format export.

---

## 11. Follow-up implementation handoff

1. Host-side MLG writer + golden file opened in MLV (manual QA) and parsed by automated test.
2. Port writer to firmware behind a thin `log_write_sample` / `log_write_marker` API fed by canonical channels from inputs (#5).
3. Rotation, media drivers, USB list/get for #1.
4. Do not start on LogWorks or MDF until P0 acceptance in [specs/logging.md](../../specs/logging.md) §15 is green.
