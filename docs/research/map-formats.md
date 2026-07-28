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
| **LibreTune** (open TS-class host) | [LibreTune project / sources](https://github.com/LibreTune) (INI + MSQ + serial for Speeduino/rusEFI/FOME class) |
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

Relevant ideas (not requirements):

- INI parse → ECU memory model → table editor  
- Burn to ECU, restore points, Git tune versioning  
- CSV import/export  
- AutoTune against AFR targets  

Validates that **INI + page protocol + structured tables** is implementable outside EFI Analytics’ closed app. Aether should remain a **monitor/logger/bridge + safe patch path**, not a LibreTune clone on a 1.8″ screen.

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
| Pilot | **Speeduino** |
| Next families | rusEFI / FOME |

---

## 13. References (non-exhaustive)

- EFI Analytics — ECU Definition files PDF (TunerStudio docs site)  
- Megasquirt serial protocol PDF (msextra.com / megasquirt.co.uk doc tree)  
- Speeduino wiki — VE table / tuning  
- rusEFI wiki — TunerStudio project, tuning, bundles  
- FOME wiki — fome.tech  
- LibreTune — github.com/RallyPat/LibreTune  
- MS TS Lite references — burn UX and project/MSQ behavior  
