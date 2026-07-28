# Research notes — ECU map / tune formats

**Date:** July 2026  
**For:** [#4](https://github.com/tig/aether/issues/4) → product contract [`specs/maps.md`](../../specs/maps.md)  
**Nature:** Survey notes, not product requirements. Prefer `specs/maps.md` for decisions.  
**Pilot context:** Operator ECU is **FOME**; Speeduino is secondary/sim.

## Canonical sources (bookmark this)

| Topic | Canonical / primary source |
|-------|----------------------------|
| **INI definition language** | EFI Analytics *ECU Definition File Specification* — [TunerStudio docs index](https://www.efianalytics.com/TunerStudio/docs/) (search “ECU Definition” / iniSpec PDF on that site) |
| **MSQ (XML tune)** | TunerStudio project/tune files; format behavior described in TS help and definition docs above — MSQ is **not** self-describing without matching INI |
| **MegaSquirt serial (“newserial”)** | *Megasquirt serial protocol* (2014-10-28 and successors) — CRC envelope + `r`/`w`/`b` page commands; historically mirrored in MSExtra / community archives and Speeduino/rusEFI implementations |
| **Speeduino** | [Speeduino wiki](https://wiki.speeduino.com/) + firmware INI in [speeduino/speeduino](https://github.com/speeduino/speeduino) |
| **rusEFI TS binary / tunes** | [rusEFI wiki](https://wiki.rusefi.com/) + firmware `tunerstudio` sources [rusefi/rusefi](https://github.com/rusefi/rusefi) |
| **FOME** | [https://www.fome.tech/](https://www.fome.tech/) · [wiki.fome.tech](https://wiki.fome.tech/) · [FOME-Tech/fome-fw](https://github.com/FOME-Tech/fome-fw) (TS integration, USB, INI) |
| **LibreTune** (open TS-class host) | [RallyPat/LibreTune](https://github.com/RallyPat/LibreTune) (GPL-2.0; INI + MSQ + serial for Speeduino/rusEFI/FOME) — see §13 |
| **MLVLG logs** (context for #3, not maps) | [MLG Binary Log Format 2.0 PDF](http://www.efianalytics.com/TunerStudio/docs/MLG_Binary_LogFormat_2.0.pdf) |

---

## 1. TunerStudio / EFI Analytics definition (INI)

### What it is

ECU **definition files** (`.ini` / historically `.ecu`) describe everything a tuning app needs to talk to a controller and present settings: memory map, protocol commands, constants, table editors, gauges, datalog fields, menus.

Authoritative public documentation: EFI Analytics *ECU Definition files* PDF (iniSpec through ~3.80 as of early 2026 revisions) via [TunerStudio docs](https://www.efianalytics.com/TunerStudio/docs/).

### Key mechanisms

| Mechanism | Role |
|-----------|------|
| `signature` | Required string; matched to firmware query — **definition ↔ firmware lock** |
| `iniVersion` | Optional definition revision independent of firmware signature |
| `queryCommand` / version info | Protocol hooks to read signature/version from controller |
| `[Constants]` | Typed scalars, bitfields, arrays with **page, offset, scale, translate, min, max, digits, units** |
| Pages | Memory banking; constants live at offsets within pages |
| `[TableEditor]` | Binds UI tables: `xBins` / `yBins` (axes) + `zBins` (2-D array constant) |
| `[OutputChannels]` | Live gauge/log channels (runtime — see #5) |
| `[Datalog]` | Log field list for MSL-class logs (see #3) |

### Table definition example pattern

```text
table = veTable1Tbl, veTable1Map, "VE Table 1", …
  xBins = frpm_table, rpm
  yBins = fmap_table, fuelLoad
  zBins = veTable1
```

Resizable tables use dimension constants and expression-sized arrays (modern firmwares).

### LLM fitness

**Low without projection.** INI is a domain-specific language for tools, not a clean agent context. Once parsed into named tables with units, fitness becomes high.

---

## 2. MSQ tune files

### What it is

**`.msq`** = TunerStudio **tune / calibration snapshot** for a project. Since ~2005 (MegaTune 4 / TS era) MSQs are **XML** (human-openable in a text editor). Older MegaTune 3.x styles exist in the wild; treat as legacy.

**Canonical understanding:** there is no separate “ISO MSQ standard” independent of TunerStudio — the file is the **TS project tune export**, always interpreted with a **matching INI**. Primary product docs: [EFI Analytics TunerStudio](https://www.tunerstudio.com/) / [docs index](https://www.efianalytics.com/TunerStudio/docs/). Open implementations that round-trip MSQ (e.g. LibreTune) are useful secondary sources.

### Contents (conceptual)

- Metadata: firmware / signature association, comments, project hints  
- **Constant values** in engineering (or stored) form as interpreted by the **project’s INI**  
- Not self-describing for layout: **same MSQ + wrong INI = wrong meaning**

### Related

| Artifact | Role |
|----------|------|
| `CurrentTune.msq` | Common working name in TS projects |
| `.msqpart` | Partial save (single dialog / subset) |
| Project folder | INI + dashboards + tunes + logs |

### Tooling

- **TunerStudio** — primary create/edit/connect  
- **LibreTune** — open-source INI-compatible app; MSQ / TS project import, CSV, Git versioning  
- Web viewers (e.g. historical msqur.com) — view-only experiments  

### LLM fitness

XML MSQ is **semi-structured** but verbose and INI-coupled. Better as **interop/backup** than as agent scratchpad. Round-trip: MSQ → ATM → agent patch → MSQ.

---

## 3. MegaSquirt serial protocol (map path)

Reference: *Megasquirt serial protocol* (2014-10-28) — “newserial” with size + CRC32 wrapper.

### Map-relevant commands

| Cmd | Role |
|-----|------|
| `r` | Read page/table data at offset/size |
| `w` | Write page data (RAM tuning image) |
| `b` | **Burn** table/page to flash |
| `Q` / signature tables | Identity (with INI queryCommand) |
| `f` | Blocking factors for safe chunk sizes |
| `A` / `g` | Realtime — **display/logging (#5)**, not maps |

### Properties

- Request/response, half-duplex  
- Big-endian multi-byte fields  
- Response **flag** distinguishes OK, page data, burn ok, CRC failure, etc.  
- Tables numbered; tuning pages are firmware-specific — **INI is authority**  
- Writes affect RAM working set; **burn** makes permanent (flash endurance considerations)

### Safety lessons for Aether

1. Chunk writes to write-blocking factor.  
2. Always CRC-check responses.  
3. Separate **write** from **burn**.  
4. Signature mismatch ⇒ stop.

---

## 4. Speeduino

### Tables

Primary tuning tables (TS):

- **VE** — 3-D interpolated, RPM × fuel load (MAP or TPS-derived depending on algorithm)  
- **Spark** — ignition advance  
- **AFR** — target mixture  

Typical educational size **16×16** (firmware-dependent; not assumed fixed in ATM).

### Protocol / files

- Speaks **TunerStudio-compatible** page protocol (framed commands; page read `p`, burn `b`/`B`, CRC checks in field reports).  
- Tunes saved as **MSQ** with Speeduino INI.  
- Secondary serial exists for realtime dash-style IO (logging/display — #5).

### Why pilot-friendly

Open firmware, simple mental model, large community, same definition/data split as MS without MS3’s huge page map.

---

## 5. rusEFI

### Tune / definition

- Ships **bundle**: firmware + **`.ini`** for TS + console tools.  
- USB device often exposes mass-storage with the correct INI — strong **definition delivery** story.  
- Auto-detect INI over USB/serial/BT when supported.  
- Field tunes exchanged as **MSQ** (including rusEFI online MSQ library).  
- Tuning workflow documentation centers on **VE table** + **target AFR** + TS VE Analyze / autotune (registered TS).

### Protocol

- Implements **TunerStudio binary protocol** (see rusEFI `tunerstudio` sources).  
- Additional **rusEFI console** for diagnostics beyond TS.

### LLM fitness

Same as other INI ECUs after projection; richer config surface ⇒ **narrow allowlists** more important.

---

## 6. FOME (issue “FOAM”)

**Naming:** Issue text says “FOAM”; the open project in this ecosystem is **FOME** — *Free Open Motorsports ECU* ([fome.tech](https://www.fome.tech/), [FOME-Tech/fome-fw](https://github.com/FOME-Tech/fome-fw)). Treat FOAM as **FOME** unless a distinct FOAM product appears.

### Characteristics

- Open firmware/hardware lineage related to modern STM32 open ECU stack.  
- **TunerStudio** is a first-class tuning host; firmware releases include INI path.  
- Feature set (VE, spark, multi-dimensional mapping, ETB, etc.) documented in FOME wiki — tables are still TS-style constants under the hood.  
- LibreTune lists **FOME** alongside Speeduino/rusEFI as INI + serial compatible.

### Implication for Aether

Do **not** invent a separate “FOME binary format” — model as **TS-class INI family** peer to rusEFI.

---

## 7. LibreTune (ecosystem proof)

Open-source TS-compatible tuner (Rust/Tauri): Speeduino, rusEFI, FOME, epicEFI, partial MS2/MS3.  
**License: GPL-2.0** — excellent **reference / gold-test peer**, **not** a linkable dependency for non-GPL Aether code. Source: [RallyPat/LibreTune](https://github.com/RallyPat/LibreTune). Modular core (`libretune-core`: `ini/`, `tune/`, `protocol/`, `ecu/`, `table_ops/`) is the best extractable *design* for a clean-room host binder.

Relevant ideas (not requirements):

- INI parse → ECU memory model → table editor  
- Burn to ECU, restore points, Git tune versioning  
- CSV import/export  
- AutoTune against AFR targets  

Validates that **INI + page protocol + structured tables** is implementable outside EFI Analytics’ closed app. Aether should remain a **monitor/logger/bridge + safe patch path**, not a LibreTune clone on a 1.8″ screen. Full OSS inventory: §13.

---

## 8. Intermediate / exchange conventions

| Convention | Use | Caveat |
|------------|-----|--------|
| CSV grids | Share one table with axis headers | Loses definition hash, scalars, multi-table consistency |
| Page hex dumps | Forensic / factory restore | Opaque to agents |
| JSON structured tables | Agent tools, web UIs | Must version schema (AMP) |
| Git of MSQ/AMP | Human version control | Good host practice; optional |

---

## 9. Closed OEM (out of scope)

RomRaider / EcuFlash / WinOLS / HP Tuners-class workflows use **ROM definitions** and often **encrypted or checksummed** binaries. Different stack (flash tools, not TS pages). Aether notes them as **out of scope** for serial map R/W v1.

---

## 10. Safety practices observed in the field

| Practice | Source |
|----------|--------|
| Signature / INI match before connect | TS, rusEFI docs |
| Burn separate from live edit | MS TS Lite reference; flash wear notes (~100k burns class) |
| Save MSQ before experiments | Universal tuner advice |
| CRC on serial frames | MS newserial; Speeduino CRC failure reports |
| VE analyze authority limits / cell locks | TS autotune UX — maps to agent `max_abs_delta` / allowlists |
| Prefer rich-safe when unsure | rusEFI tuning guidance |

---

## 11. LLM structured representation — design takeaway

What works for agents:

1. **Named** tables (`ve_table_1`) not page numbers.  
2. **Engineering units** on axes and cells.  
3. **Region ops** (scale/add/set) with clamps.  
4. **Provenance** (definition_hash, signature, document_hash).  
5. **Rationale + log context** attached to the patch, not embedded as fake ECU constants.  
6. **Small surface** — subset tables for context window.  

What fails:

- Raw EEPROM images  
- Unversioned CSV without axes  
- MSQ XML dumped whole into a prompt without summarization  

---

## 12. Decision pointers (see product spec)

| Decision | Choice in `specs/maps.md` |
|----------|---------------------------|
| Internal model | **ATM** (structured) |
| Agent format | **AMP JSON + MapPatch** |
| Ecosystem file | **MSQ + INI** |
| On-wire | Native TS-class pages |
| Pilot | **FOME** |
| Secondary / sim | Speeduino |
| Peer family | rusEFI |

---

## 13. OSS leverage map (host + metal)

Survey of **existing open-source** code Aether should **use hard** for prove/HIL, plus notes for later ship hygiene. Normative stance: [`specs/maps.md` §16](../../specs/maps.md) — **prove first, don’t be pedantic about GPL in the lab.**

### 13.1 Stance (prove vs hygiene)

| Mode | Practice |
|------|----------|
| **Prove / lab / gh ship-vehicle (now)** | Run **LibreTune**, talk **FOME/rusEFI**, capture goldens, CI against open ECU tools. Gray areas (“is this repo the ship vehicle?”) are **documented**, not blocking. |
| **Redistribute hygiene (later)** | Before polished public binaries, revisit static-link and redistributed trees. See §13.5 and maps.md §16.5. |

**Working preference:** permissive for *new* Aether modules when easy; **GPL ecosystem is first-class for validation**. Avoid license theater that slows HIL.

| Layer | Preference (now) | Later if shipping widely |
|-------|------------------|---------------------------|
| **Test / HIL / goldens** | **FOME, rusEFI, LibreTune, Speeduino — use them** | Keep as external/dev deps if counsel wants a cleaner product tree |
| **Metal USB/FS/JSON** | ESP-IDF / MIT/Apache when available | Same |
| **Aether ATM/AMP/MapPatch** | Build under product license | Unchanged |
| **Temporary GPL spike** | OK if labeled; gets the demo working | Replace or isolate before “real” release |
| **TunerStudio closed code** | **No** decompile / proprietary algorithm lift | Unchanged hard line |

### 13.2 Candidate inventory

Each row: **name · URL · SPDX · language · host/metal fit · maturity · integration cost · gaps**.

#### A. Full TS-class host apps (reference / peer, not link)

| Name | URL | SPDX | Lang | Fit | Maturity | Cost | Gaps / notes |
|------|-----|------|------|-----|----------|------|--------------|
| **LibreTune** | [github.com/RallyPat/LibreTune](https://github.com/RallyPat/LibreTune) | **GPL-2.0** | Rust + TS (Tauri) | **Primary validation host** — modular `libretune-core`: `ini/`, `tune/` (MSQ), `protocol/`, `ecu/`, `table_ops/` | Early but active (2026 nightlies); Speeduino/rusEFI/**FOME**/epicEFI | **Low for goldens** (clone and run); high only if forked as Aether UI | **Use for MSQ open/save + serial smoke.** Not a crates.io lib; no AMP/MapPatch. Full desktop tuner — out of Aether device scope. GPL: fine as test sidecar / local clone; flag if vendored into product binary later. |
| **MegaTunix** | [github.com/djandruczyk/MegaTunix](https://github.com/djandruczyk/MegaTunix) · SF | **GPL-2.0** | C (GTK) | Historical host reference for MS serial | **Legacy / stalled**; modern MS firmware support incomplete | High (old GTK, incomplete modern INI) | Do not base new work; useful only for archaeology of page R/W |
| **msqur** | [github.com/nearwood/msqur](https://github.com/nearwood/msqur) · [msqur.com](https://msqur.com) | **GPL-3.0** | PHP + JS | **Host reference** for MSQ XML + INI display | Mature enough for MS1–MS3 / Speeduino / rusEFI **viewing** | Med as read-path study | View-only web app; not a library; GPL-3; write path weak |
| **TunerStudio** | [tunerstudio.com](https://www.tunerstudio.com/) | **Proprietary** | Java | Interop **target** only | Dominant commercial host | N/A — **cannot reuse** | Closed: UI, autotune algorithms, cloud SOAP, binary. **Public** piece: *ECU Definition File Specification* (INI). MSQ is TS project XML — document behavior, don’t copy closed code. |

#### B. ECU firmwares / protocol sources (metal + definition packs)

| Name | URL | SPDX | Lang | Fit | Maturity | Cost | Gaps / notes |
|------|-----|------|------|-----|----------|------|--------------|
| **FOME** (`fome-fw`) | [github.com/FOME-Tech/fome-fw](https://github.com/FOME-Tech/fome-fw) | **GPL-3.0 + additional terms** (rusEFI-lineage; GitHub `NOASSERTION`) | C++ firmware + Java console/tools | **Pilot ECU / HIL #1** — live USB-serial, INI packs, page R/W behavior | Production open ECU; active | **Low for HIL** (plug in and talk) | **Use as the vehicle ECU.** Capture INI/MSQ goldens. Study `tunerstudio` path. Static-link of firmware into Aether is the later hygiene question — not a reason to skip HIL. Additional terms: document for product disclaimers. |
| **rusEFI** | [github.com/rusefi/rusefi](https://github.com/rusefi/rusefi) | **GPL-3.0 + additional terms** (off-road / non-aircraft caveats; GitHub `NOASSERTION`) | C++ + Java (`java_console`, `java_tools`) | Peer HIL + protocol study; USB mass-storage INI story | Very mature | Low for black-box HIL | Same family as FOME. Excellent **definition delivery** patterns. Use freely for lab; note additional terms for later marketing/docs. |
| **Speeduino** | [github.com/speeduino/speeduino](https://github.com/speeduino/speeduino) | **GPL-2.0** | C++ (Arduino) | **Sim / secondary metal** | Mature community ECU | Low as sim | Secondary after FOME pilot; great when the car is not available. |
| **TS_lib** | [github.com/filipporaciti/TS_lib](https://github.com/filipporaciti/TS_lib) | **MIT** | C++ (Arduino) | **Metal-adjacent** — ECU-side TS protocol helper | Small / niche | Low to read | Helps **ECU implementers**, not host INI/MSQ. May inform framing only; not FOME/rusEFI complete. |
| **speeduino-serial-sim** | [github.com/askrejans/speeduino-serial-sim](https://github.com/askrejans/speeduino-serial-sim) | **MIT** | (see repo) | **Host/metal test harness** — Speeduino protocol v2 (framed CRC32 + legacy) | Useful for CI sim | Low | Speeduino-only; not FOME. Great for #5 protocol tests on secondary path. |

#### C. INI / MSQ “libraries” (extractability reality)

| Name | URL | SPDX | Lang | Fit | Maturity | Cost | Gaps / notes |
|------|-----|------|------|-----|----------|------|--------------|
| **LibreTune `ini` + `tune` modules** | inside LibreTune | **GPL-2.0** | Rust | **Best structured OSS INI/MSQ engine** in the wild | Coupled to LibreTune app | Low as **oracle** (run LibreTune); high to **extract as product lib** | **Not** a standalone crate. Prove mode: use whole app as gold. Product path: clean-room binder *or* deliberate GPL product strategy — decide later; don’t block goldens. |
| **msqur PHP MSQ/INI parse** | nearwood/msqur `src/` | **GPL-3.0** | PHP | Reference for XML constant trees | Web-app quality | High to port | Not embeddable in ESP or preferred host lang without rewrite |
| **Python `configparser`** | stdlib | PSF | Python | **Unsuitable** as ECU INI engine | N/A | — | ECU definitions are a **domain language** (typed constants, pages, TableEditor, expressions) — not Windows INI. Use only for trivial key dumps, never as the binder. |
| **General XML (lxml / ElementTree)** | various | MIT / PSF | Python | **Host plumbing** for MSQ XML DOM | Mature | Low | Need Aether schema of MSQ elements; XML libs don’t know “constant meaning” |
| **RomRaider** | [github.com/RomRaider/RomRaider](https://github.com/RomRaider/RomRaider) | **GPL-2.0** | Java | **Out of ecosystem** (Subaru/OEM ROM defs) | Mature for OEM | High / wrong stack | Different problem (ROM tables, checksums). Note only; not TS page path. |

**Finding:** there is **no permissive, production-grade, standalone “ECU INI + MSQ” library**. Aether will **build** ATM/AMP and likely its own binder over time. **LibreTune + live FOME are the primary behavioral oracles today** — use them, don’t wait for a perfect MIT library.

#### D. Patch / schema / serialization (host + optional metal)

| Name | URL | SPDX | Lang | Fit | Maturity | Cost | Gaps / notes |
|------|-----|------|------|-----|----------|------|--------------|
| **python-json-patch** (RFC 6902) | [github.com/stefankoegl/python-json-patch](https://github.com/stefankoegl/python-json-patch) | **BSD-3-Clause** | Python | Host **structural** AMP document patch / test diffs | Mature | Low | **Not a substitute for MapPatch.** MapPatch ops are table-region/domain (`scale_region`, `set_cells`). Use RFC6902 for whole-AMP merge tests or host tool internals only. |
| **jsonschema** | [github.com/python-jsonschema/jsonschema](https://github.com/python-jsonschema/jsonschema) | **MIT** | Python | **AMP / MapPatch schema validation** on host | Mature | Low | Ship `amp.schema.json`; CI validate fixtures |
| **Strategic merge / JSON Merge Patch (RFC 7396)** | various | usually permissive | multi | Weak fit | — | — | Merge patch lacks region math; agents need explicit ops + clamps |
| **cJSON** | [github.com/DaveGamble/cJSON](https://github.com/DaveGamble/cJSON) · ESP component `espressif/cjson` | **MIT** | C | **Metal** AMP subset parse if JSON over USB/Wi-Fi | Mature; ESP-IDF registry | Low | Prefer host-heavy AMP; metal holds compact tables + hashes |
| **nanopb** | [github.com/nanopb/nanopb](https://github.com/nanopb/nanopb) | **Zlib** | C | Metal binary schema if AMP ever goes binary | Mature embedded | Med | **Not justified for P0–P2.** ATM/AMP stay JSON on host; metal uses definition-bound page bytes |
| **FlatBuffers** | [github.com/google/flatbuffers](https://github.com/google/flatbuffers) | **Apache-2.0** | multi | Same as nanopb — optional later | Mature | Med–High | Overkill until wireless AMP bandwidth proves painful |

#### E. Protocol / serial helpers

| Name | URL | SPDX | Notes |
|------|-----|------|-------|
| **MS newserial docs** | Megasquirt serial protocol PDF (community mirrors) | Documentation | Canonical command set `r`/`w`/`b` + CRC envelope — **implement clean-room** |
| **Speeduino / FOME / rusEFI sources** | respective firmwares | GPL-* | **HIL + behavior reference**; implement client against live ECU; avoid unreviewed wholesale paste into metal if a small clean client works |
| **LibreTune `protocol`** | RallyPat/LibreTune | GPL-2.0 | Best host-side multi-family client — **run it** for multi-family checks |
| **ESP-IDF UART / USB-Serial-JTAG** | Espressif | Apache-2.0 | Transport substrate for #5 |

### 13.3 What TunerStudio cannot contribute

| Item | Status |
|------|--------|
| Source code, UI, registered autotune algorithms | **Proprietary — no reuse** |
| Cloud definition/registration SOAP | **Proprietary — no reuse** |
| Published **ECU Definition File Specification** (INI) | **Use as the grammar authority** |
| Observed MSQ XML shape via open tools | **Interop via open implementations + fixtures**, not decompilation |
| “TS-compatible” claim | Means **speak the open protocol + INI**, not “contains TS code” |

### 13.4 Host vs metal leverage summary

```text
HOST (P0 first) — prove with ecosystem tools
  ├── LibreTune / TS ......... RUN as gold (open MSQ, serial smoke)
  ├── FOME INI + MSQ samples . CAPTURE from real ECU / tuner project
  ├── INI binder ............. BUILD over time (bootstrap vs LibreTune)
  ├── MSQ XML R/W ............ BUILD; acceptance = LibreTune/TS opens file
  ├── ATM / AMP / MapPatch ... BUILD (Aether IP; jsonschema)
  └── CI ..................... May depend on GPL tools / recorded fixtures

METAL (with #5) — HIL first
  ├── FOME over USB .......... REQUIRED pilot path
  ├── TS page r/w/burn ....... BUILD against live FOME (docs + HIL)
  ├── rusEFI ................. Optional peer HIL
  ├── Structured table cache . BUILD thin
  ├── cJSON .................. OPTIONAL
  └── nanopb / FlatBuffers ... DEFER
```

### 13.5 License gray areas (document; don’t stall)

| Topic | Note |
|-------|------|
| **GPL in monorepo / CI** | Dev/test use of LibreTune/FOME is expected. Whether a public release tarball is a “combined work” is a **later** packaging question. |
| **Static link into firmware** | Prefer not to paste GPL `tunerstudio.cpp` wholesale; a short Aether client is usually faster *and* cleaner. Spikes that vendor code should be labeled. |
| **FOME/rusEFI additional terms** | Beyond bare GPL; fine for HIL; product disclaimers when marketing hardens. |
| **INI redistribution** | Record provenance; pilot fixtures OK. |
| **gh as ship vehicle** | Spec/code may live in the same org as experiments — optimize for **proof**, not perfect SPDX theater. |

### 13.6 Must-build list (product path; goldens can lead)

1. **ECU-definition-aware INI parser** (or deliberate long-term LibreTune dependency strategy).  
2. **MSQ XML import/export** bound to a loaded definition.  
3. **ATM ↔ pages ↔ MSQ** with `definition_hash` / `document_hash`.  
4. **MapPatch** validate + dry-run + apply (domain ops).  
5. **TS-class serial client** — shared with #5; prove on **live FOME**.  
6. **FOME fixtures** — capture from car/HIL + LibreTune.  
7. **Safety gates** — backup, readback, burn, agent confirm.

### 13.7 Recommended stack by phase (pointer)

| Phase | Leverage |
|-------|----------|
| **P0** | Host INI+MSQ+ATM; **LibreTune gold**; real FOME MSQ samples |
| **P1** | Live FOME USB read; rusEFI peer; speeduino-serial-sim for CI when car offline |
| **P2** | MapPatch write path; validate with LibreTune re-read + FOME |
| **P3** | LLM loop; same HIL stack |

Detail: [`specs/maps.md` §16](../../specs/maps.md).

---

## 14. References (non-exhaustive)

- EFI Analytics — ECU Definition files PDF (TunerStudio docs site)  
- Megasquirt serial protocol PDF (msextra.com / megasquirt.co.uk doc tree)  
- Speeduino wiki — VE table / tuning · [speeduino/speeduino](https://github.com/speeduino/speeduino) (GPL-2.0)  
- rusEFI wiki — TunerStudio project, tuning, bundles · [rusefi/rusefi](https://github.com/rusefi/rusefi) (GPL-3.0 + additional terms)  
- FOME wiki — [fome.tech](https://www.fome.tech/) · [FOME-Tech/fome-fw](https://github.com/FOME-Tech/fome-fw) (GPL-3.0 + additional terms)  
- LibreTune — [github.com/RallyPat/LibreTune](https://github.com/RallyPat/LibreTune) (GPL-2.0); architecture: `docs/architecture.md`  
- msqur — [github.com/nearwood/msqur](https://github.com/nearwood/msqur) (GPL-3.0)  
- MegaTunix — [github.com/djandruczyk/MegaTunix](https://github.com/djandruczyk/MegaTunix) (GPL-2.0)  
- TS_lib — [github.com/filipporaciti/TS_lib](https://github.com/filipporaciti/TS_lib) (MIT)  
- speeduino-serial-sim — [github.com/askrejans/speeduino-serial-sim](https://github.com/askrejans/speeduino-serial-sim) (MIT)  
- python-json-patch — [stefankoegl/python-json-patch](https://github.com/stefankoegl/python-json-patch) (BSD-3-Clause)  
- jsonschema — [python-jsonschema/jsonschema](https://github.com/python-jsonschema/jsonschema) (MIT)  
- cJSON — [DaveGamble/cJSON](https://github.com/DaveGamble/cJSON) (MIT)  
- nanopb — [nanopb/nanopb](https://github.com/nanopb/nanopb) (Zlib)  
- FlatBuffers — [google/flatbuffers](https://github.com/google/flatbuffers) (Apache-2.0)  
- RomRaider — [RomRaider/RomRaider](https://github.com/RomRaider/RomRaider) (GPL-2.0; OEM ROM stack — out of scope)  
- MS TS Lite references — burn UX and project/MSQ behavior  
