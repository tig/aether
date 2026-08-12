# Research notes — ECU / tuner log formats

**Date:** July 2026 (OSS map expanded same month)  
**Purpose:** Survey backing for [specs/logging.md](../../specs/logging.md). **Non-normative** — the contract is the spec.  
**Issue:** [tig/aether#3](https://github.com/tig/aether/issues/3) · PR [#6](https://github.com/tig/aether/pull/6)

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
- **Product update (rev 0.2):** operator’s tuner uses LogWorks; **LogWorks-openable DIF (or documented CSV) is P0 export**, not P2. Native `.log` write remains non-canonical (closed). See [specs/logging.md](../../specs/logging.md) §9.1.

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

## 7. FOME (issue prose “FOAM”) and other open ECUs

- **Product resolution:** pilot ECU is **[FOME](https://www.fome.tech/)** ([FOME-Tech/fome-fw](https://github.com/FOME-Tech/fome-fw), **GPL-3.0**).
- FOME wiki documents **MLG** as the typical datalog format (TunerStudio path); no separate FOME-only file format for interchange.
- **Do not link** FOME firmware into Aether; use live protocol (#5) and still **store MLG** on device.
- GPL code is **reference / interop only** (channel naming for P0e), not a reusable library.

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

## 11. OSS leverage map (host + metal)

**Date of survey:** July 2026 · **Goal:** do not reinvent parsers/writers when a **permissive** library already fits.  
**License policy (Aether product):**

| Layer | Prefer | Copyleft (GPL/LGPL/AGPL) |
|-------|--------|---------------------------|
| **Metal (firmware link)** | MIT / Apache-2.0 / BSD / ISC / Unlicense / BSL / Zlib | **Reject** for static/dynamic link into Aether firmware |
| **Host tools / CLI converters** | MIT / Apache preferred | OK as **standalone** CLI (no firmware link); quarantine in docs; do not vendor into product binary without legal review |
| **Reference study only** | Any open source | May **read** algorithms; **do not copy** GPL source into Aether trees |

**Closed / non-OSS (for honesty):** MegaLogViewer, TunerStudio, LogWorks UI — use as **QA consumers**, not as libraries.

### 11.1 Candidate inventory (verified)

| Name | URL | License (SPDX) | Lang / platform | What it does | Maturity | Fit for Aether | Integration cost | Gaps |
|------|-----|----------------|-----------------|--------------|----------|----------------|------------------|------|
| **mlg-converter** | https://github.com/karniv00l/mlg-converter | **MIT** (LICENSE verified) | TypeScript / Node ≥14 | **Parse** MLVLG v1/v2; export **CSV (`;`)**, **MSL**, **JSON**; npm + CLI | ~27★; last push ~2023-05; tests present; topics include FOME/Speeduino | **Host:** golden-test **reader** + optional export path | `npm i mlg-converter` or CLI; no metal | **No writer**; markers stripped from CSV; not Python |
| **mlg-cli** (HyperTuner) | https://github.com/hyper-tuner/mlg-cli | **MIT** | Rust CLI | Convert MLG → other formats (CSV/JSON family) | ~6★; last push ~2023-03; 5 commits | **Host** secondary verifier | Cargo binary / releases | Small project; not a library for Python gate |
| **racing-data-converter** | https://github.com/BenergyRacing/racing-data-converter | **GPL-2.0** | TypeScript / Node | **`MlgWriter`** + **`MslWriter`** (MLVLG v2 header/blocks), Motec CSV, etc. | ~27★; last push ~2024-05; jest tests | **Host-only** reference / optional standalone CLI — **not** product link | npm; streams API | **GPL** → quarantine for product; Node not Python; metal N/A |
| **Speeduino-Copilot** | https://github.com/minceheid/Speeduino-Copilot | **GPL-3.0** | C++ (Teensy) | Embedded **MGVLG writer** (`mgvlg.h` / `mgvlg.ino`) + Speeduino serial | ~6★; last push ~2021-01; incomplete | **Reference only** for embedded field packing | Copy forbidden under GPL into Aether | GPL; Speeduino-specific; incomplete; not ESP-IDF |
| **rusEFI firmware** | https://github.com/rusefi/rusefi | **GPL-3.0** + extra terms (license.txt) | C/C++ STM32 | Production **onboard SD MLG** logging (see Logging Guide) | Large mature ECU project | **Reference** (how production MLG writers behave) — **no link** | N/A (GPL metal) | Entire ECU stack; cannot ship inside Aether |
| **FOME firmware** | https://github.com/FOME-Tech/fome-fw | **GPL-3.0** (+ rusEFI-lineage terms in LICENSE) | C | Pilot ECU; **MLG via TS / SD** (wiki: default MLG naming) | ~129★; active 2026 | **Interop** + channel-name study for P0e — **not** a library | Protocol (#5), not file code | GPL; not a reusable log lib |
| **Speeduino** | https://github.com/speeduino/speeduino | **GPL-2.0** | C++ Arduino | SD / TS logging paths | ~1.8k★ | Interop precedent only | GPL | Not a library |
| **UltraLog** | https://github.com/ClassicMiniDIY/UltraLog | **AGPL-3.0** | Rust (desktop viewer) | MLG/CSV viewer; **FORMAT_SPECIFICATIONS.md** documents MLG | ~34★; active 2026 | Host QA viewer optional; **do not link** AGPL | External tool | AGPL; not a writer; not embeddable |
| **SpeedyLogger** | https://github.com/ric355/SpeedyLogger | **Unknown** (no LICENSE on repo) | Pascal / bare-metal RPi | Writes sequential **`dl######.msl`** from Speeduino | ~23★; last push ~2021 | Quarantine (license) | High port cost | Unknown license; MSL only; not ESP32 |
| **SheetJS Community (xlsx)** | https://github.com/SheetJS/sheetjs · docs.sheetjs.com | **Apache-2.0** (CE) | JS/TS | Read/write many spreadsheets including **spreadsheet DIF** | Very mature ecosystem | **Host:** candidate for **LogWorks DIF** if LogWorks accepts classic spreadsheet DIF | npm package | **Not** LogWorks-native `.log`; Node-centric; validate in real LogWorks |
| **Python `csv` / `struct` / `json`** | stdlib | PSF (permissive) | Python | Host MSL/CSV/JSON/binary packing | Universal | **Host gate default** (matches aether mockup Python) | Zero deps | Still write format logic ourselves |
| **asammdf** | https://pypi.org/project/asammdf/ | **LGPL-3.0+** | Python | MDF/MF4 R/W | Mature | **P2+ host only** if MDF export appears; LGPL dynamic-link care | pip | Overkill for P0; not MLG/MSL |
| **mdflib** | https://github.com/ihedvall/mdflib | **MIT** | C++ | MDF3/4 R/W | Active | P2+ host/native if needed | CMake | Not P0 |
| **littlefs** | https://github.com/littlefs-project/littlefs | **BSD-3-Clause** | C | Fail-safe FS for MCU flash | Very mature | **Metal media** for internal flash ring/sessions | ESP-IDF component (`joltwallet/littlefs`) | Not a log **format**; append perf caveats on large files |
| **ESP-IDF FatFs + SDMMC** | https://docs.espressif.com/…/fatfs.html · sdmmc | Apache-2.0 (IDF); FatFs BSD-style; SDMMC BSD-derived | C | SD card mount, append files, VFS | Production Espressif | **Metal media** for microSD continuous log | Built into ESP-IDF | Not format-specific |
| **Innovate OT-2 SDK** | https://github.com/Innovate/OT-2-SDK | Vendor / not a file-format OSS stack | — | OT-1b/OT-2 OBD adapter SDK | Vendor | **Neither** for Aether log files | N/A | Does **not** implement LogWorks `.log`/DIF writers for third-party loggers |
| **MegaLogViewer** | EFI Analytics (commercial) | Proprietary | Desktop | Canonical MLG **viewer** | Dominant DIY | **QA open** of golden `.mlg` / `.msl` | Manual QA | Closed; not a library |

### 11.2 LogWorks DIF vs spreadsheet DIF

LogWorks documentation (LogWorks 2/3 manuals) states:

- Logs are stored as **native `.log`** **or** **`.dif`**.
- **`.log`:** compact native; keeps measurement points, filters, input settings — **spec not openly published** for third-party writers.
- **`.dif`:** used to move log data into **spreadsheet programs (e.g. Excel)**; stores **already-converted engineering quantities**; re-import into LogWorks is **lossy** for filters/settings.

Classic **Data Interchange Format** (Software Arts / VisiCalc era; Wikipedia: `TABLE` / `VECTORS` / `TUPLES` / `DATA` / `BOT` / `EOD` chunks) is what spreadsheet tools call `.dif`. LogWorks marketing of “DIF” aligns with that **spreadsheet interchange** path, **not** a separate published binary LogWorks schema.

**Implications for Aether P0:**

1. Prefer generating **classic spreadsheet DIF** (or a documented CSV layout LogWorks can import) with columns Time, Lambda/AFR, RPM, load.
2. **Validate with a real LogWorks install** before claiming handoff (open question already in the contract).
3. Do **not** reverse-engineer native `.log` for P0 if DIF/CSV opens.
4. SheetJS `bookType: 'dif'` (Apache-2.0) or a **~50-line Python DIF writer** are both viable; pure Python preferred for aether’s host gate.

### 11.3 Leverage vs invent (summary)

| Artifact | Leverage | Invent (Aether owns) |
|----------|----------|----------------------|
| On-device **MLVLG v2 writer** | Format PDF; *algorithm* hints from GPL writers (no copy) | **C writer** (no permissive C library found) |
| Host **MLG golden tests** | **mlg-converter** parse (MIT) + MLV manual open | Host **writer** (Python/`struct` or small C shared with metal) |
| **MSL export** | Pattern from mlg-converter / racing-data-converter (GPL = don’t copy) | Trivial tab writer in Python/C — **do not pull GPL** |
| **CSV export** | stdlib / no library | Dialect docs only |
| **LogWorks DIF** | Spreadsheet DIF spec + optional SheetJS | Channel layout + **LogWorks open validation** |
| **JSON pull** | stdlib | Schema for #1 |
| **Media** | ESP-IDF FatFs/SDMMC, littlefs | Session rotation, flush policy, naming |
| **Native LogWorks `.log`** | None open | **P2 research only** if DIF fails |

### 11.4 Reject / quarantine list

| Item | Reason |
|------|--------|
| rusEFI / FOME / Speeduino **firmware source** linked into Aether | **GPL** metal |
| racing-data-converter **vendored** into product | **GPL-2.0** |
| Speeduino-Copilot code into firmware | **GPL-3.0** |
| UltraLog linked or server-side | **AGPL-3.0** |
| SpeedyLogger source | **Unknown license** |
| Innovate native `.log` RE as P0 | Closed; product chose DIF/CSV handoff |
| MegaLogViewer as dependency | Proprietary binary |
| asammdf / MDF for P0 | Wrong ecosystem; LGPL careful use only if P2+ |

### 11.5 Recommended stack (non-normative; contract in `specs/logging.md`)

**Metal (ESP32-S3 / ESP-IDF):**

- Media: ESP-IDF **SDMMC + FatFs** (SD SKU) and/or **littlefs** (internal flash SKU).
- Format: **Aether-owned** small C MLVLG v2 writer (header + type-0 records + type-1 markers). Implement from EFI Analytics PDF; host/firmware **share** the same packing rules.
- Do **not** depend on GPL ECU trees for code.

**Host (Python mockup / CI / pull tools):**

- **Write** MLG: Aether Python (or shared C unit-tested via host plate) — **must** pass `mlg-converter` parse + MLV open.
- **Read/verify:** `mlg-converter` (MIT) in CI optional gate; manual MLV QA remains gold.
- **MSL/CSV/JSON:** Python stdlib writers following §9 of the contract.
- **LogWorks:** spreadsheet DIF writer (Python preferred) **or** documented CSV; golden open in LogWorks.

**Do not reimplement if X works:**

- Do not write a second MLG **parser** if `mlg-converter` covers CI readback.
- Do not invent a proprietary on-device binary when MLG writer exists in-tree.
- Do not reverse-engineer LogWorks `.log` while DIF/CSV handoff is green.
- Do not vendor GPL “because it already writes MLG.”

### 11.6 Gaps we still invent (honest)

1. **Permissive C continuous MLG appender** suitable for ESP32 (RAM buffer, CRC, 10 µs wrap, markers) — **no OSS package**.
2. **Host MLG writer** under MIT/Apache that is first-class (existing writers are GPL or TS-only).
3. **LogWorks-proven DIF column layout** for Aether channels (empirical QA).
4. **Marker-preserving MSL** export (mlg-converter is a reference for read→MSL; writer is ours).
5. **Session rotation / wear / power-loss** policy on Aether media stack.

---

## 12. Follow-up implementation handoff

1. Host-side MLG writer + golden file opened in MLV (manual QA) and parsed by **mlg-converter** (or equivalent) automated test.
2. Port writer to firmware behind a thin `log_write_sample` / `log_write_marker` API fed by canonical channels from inputs (#5).
3. Rotation, media drivers (FatFs/SDMMC and/or littlefs), USB list/get for #1.
4. **LogWorks DIF/CSV handoff is P0** (tuner workflow). Defer native `.log` reverse-engineering and MDF until DIF handoff is green in the contract acceptance list.
5. Wire host export matrix using stdlib + DIF writer; keep GPL tools as external optional CLIs only.
