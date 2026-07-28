# Aether ECU map (tune table) read/write

**Rev 0.3 · July 2026**  
**Status:** Contract / decision record — **not** an implementation.  
**Issue:** [#4](https://github.com/tig/aether/issues/4)  
**Related:** [#1](https://github.com/tig/aether/issues/1) (wireless host / LLM), [#2](https://github.com/tig/aether/issues/2) (event marks), [#3](https://github.com/tig/aether/issues/3) (logging), [#5](https://github.com/tig/aether/issues/5) (serial transport / session)  
**Rev 0.4:** OSS leverage — **prove fast** with FOME/rusEFI/LibreTune for test/validation; license risks documented, not blocking — §16 + research §13.

### Operator context

| Fact | Value |
|------|--------|
| **Pilot ECU** | **[FOME](https://www.fome.tech/)** (rusEFI-lineage; issue “FOAM” → FOME) |
| **North star** | LLM-assisted map edit via structured patches (with [#1](https://github.com/tig/aether/issues/1)) |

Product mission: [spec.md](spec.md). Raw survey notes: [docs/research/map-formats.md](../docs/research/map-formats.md).

---

## One-line pitch

Aether must **read, backup, project, and (later) safely write** ECU tune tables in a form that **humans, TunerStudio-class tools, and LLM agents** can share — definition-bound, unit-aware, partial-update capable, and never a silent full flash.

---

## 1. Goals and non-goals

### 1.1 Goals (must)

| # | Goal |
|---|------|
| G1 | **Canonical internal model** for tables (VE / AFR-target / ignition / axes / scalars) with units, provenance, and definition binding. |
| G2 | **Multi-format interop** — import/export or bridge for ecosystem formats that matter in the field (MSQ + INI first). |
| G3 | **Partial update** — single table, axis band, or cell region — for interactive **and** agent-driven tuning. |
| G4 | **Safety gates** designed for automated writers: definition hash match, backup-before-write, dry-run, readback, explicit burn, human confirm for commit. |
| G5 | **LLM edit fitness** — structured, named, unit-aware, **diffable region patches** an agent can propose and Aether can validate/apply. |
| G6 | Share **session/transport** with live display/logging ([#5](https://github.com/tig/aether/issues/5)); map R/W is not a second wire stack. |
| G7 | Align with host bridge ([#1](https://github.com/tig/aether/issues/1)): Aether can forward structured maps and patches over wireless without becoming a full TunerStudio clone. |

### 1.2 Non-goals (this plan)

| # | Non-goal |
|---|----------|
| N1 | Shipping the LLM agent, autotune product, or wireless UX in this ticket. |
| N2 | Implementing firmware map R/W in this PR — **spec only**. |
| N3 | Closed OEM encrypted tunes (HP Tuners locked, proprietary flash, etc.) — note only. |
| N4 | CAN map protocols as primary path (prefer serial/USB story; CAN later if needed). |
| N5 | Replacing TunerStudio / LibreTune as a full calibration workstation on-device. |
| N6 | Inventing a closed Aether-only binary with no export story. |

### 1.3 Principles

1. Prefer **existing ecosystem formats** for on-disk interop (MSQ + matching INI).  
2. Separate **definition** (what the ECU *is*) from **data** (current values).  
3. On-wire stays **ECU-native** (TS page/offset/size); agent-facing stays **structured projection**.  
4. Every write path assumes an **automated agent** might call it: provenance, constraints, rollback, no silent burn.  
5. **Best existing where possible**; invent only the thin projection/patch layer the ecosystem lacks for LLM tools.

---

## 2. Survey summary

Full notes: [docs/research/map-formats.md](../docs/research/map-formats.md).

| Platform / tool | Definition | On-disk tune | Live R/W model | LLM-native? | Aether priority |
|-----------------|------------|--------------|----------------|-------------|-----------------|
| **TunerStudio + EFI Analytics INI** | `.ini` / `.ecu` definition (signature, pages, constants, TableEditor, scales) | **`.msq`** (XML since ~2005) full tune; `.msqpart` partial dialog saves | Page/offset R/W + **burn** to flash; RAM first | No — needs projection | **P0 interop** |
| **MegaSquirt MS2/MS3** | Firmware-shipped INI | MSQ | “Newserial” envelope + `r`/`w`/`b` (read/write/burn) + CRC32 | Opaque pages without INI | Pilot-adjacent |
| **FOME** (“FOAM” in issue prose = **FOME**, Free Open Motorsports ECU) | TS INI (rusEFI-lineage); [fome.tech](https://www.fome.tech/), [FOME-Tech/fome-fw](https://github.com/FOME-Tech/fome-fw) | MSQ | TS-compatible serial/USB + console | Same after projection | **P0 pilot ECU family** |
| **rusEFI** | Bundle `.ini` (USB mass-storage / auto-detect); signature-bound | MSQ via TS; online MSQ exchange | TS binary protocol + rusEFI console extensions | Same after projection | **P0 family / P1 depth** (peer of FOME) |
| **Speeduino** | Speeduino INI in TS | MSQ | TS-compatible pages; VE/spark/AFR tables (typically **16×16**, RPM × load) | Same as MS family after projection | **P1** (simulators / second metal) |
| **LibreTune** (open TS-class app) | Same INI ecosystem | TS project / MSQ / CSV / Git tune versioning | Speeduino, rusEFI, FOME, epicEFI, partial MS | Proves INI family is implementable outside TS | Interop peer / reference |
| **CSV / table dumps** | None | Axis + cell grids | N/A | High readability, weak provenance | **P1 export**; not sole backup |
| **OEM encrypted / closed** | Vendor only | Proprietary | Flash tools | Poor | **Out of scope** |

### 2.1 Structural common ground (TS-class)

Almost all open standalone ECUs Aether will meet first share this stack:

1. **Definition (INI)** — maps firmware **signature** → memory **pages**, **constants** (scalars, 1-D axes, 2-D tables), scales/units/min/max, UI table editors (`xBins` / `yBins` / `zBins`).  
2. **Data (pages)** — raw bytes in ECU RAM; constants are typed views over offsets.  
3. **File (MSQ)** — XML snapshot of constant **engineering values** + metadata (firmware/signature, notes), interpreted only with a matching INI.  
4. **Protocol** — read/write page ranges; **burn** commits RAM → non-volatile; realtime is separate (`A` / och) and is **#5**, not this doc’s primary payload.

### 2.2 Table axes in the field

| Table class | Typical X | Typical Y | Z units | Notes |
|-------------|-----------|-----------|---------|--------|
| **VE (fuel)** | RPM | Load (MAP kPa, TPS %, or blended) | % VE | Primary fuel map for speed-density / Alpha-N |
| **AFR / lambda target** | RPM | Load | AFR or λ | Target for closed-loop / VE analyze |
| **Ignition advance** | RPM | Load | ° BTDC | Safety-critical; leaner limits differ under load |
| **Boost / idle / trims** | Various | Various | Domain-specific | Phase later; same ATM primitives |

---

## 3. Decision record

### 3.1 Internal / canonical model — **Aether Tune Model (ATM)**

**Decision:** Aether’s internal representation is the **Aether Tune Model (ATM)** — a structured, definition-bound object graph of **tables, curves, scalars, and axes** in engineering units, plus provenance.

ATM is **not** a closed binary dump of pages. Page bytes may be retained as an optional `raw_pages` attachment for lossless round-trip, but agents and product logic **must** use the structured view.

#### 3.1.1 Core entities (normative shape)

```text
TuneDocument
  identity:
    ecu_family          # e.g. speeduino | rusefi | fome | ms3 | unknown
    firmware_signature  # string from ECU / INI signature=
    firmware_version    # optional human version string
    definition_id       # stable id for the INI (name + version)
    definition_hash     # SHA-256 of definition file bytes (see D6)
    captured_at         # UTC
    source              # ecu_live | msq_file | host_import | simulated
  constraints:          # from definition + product policy
    write_allowed       # bool
    burn_allowed        # bool
    stoich_afr          # optional fuel scale context
  tables[]: Table
  curves[]: Curve       # 1-D (e.g. WUE, dwell vs voltage)
  scalars[]: Scalar
  raw_pages?:           # optional lossless attachment
    page_id → bytes + page_crc32
  backup_of?:           # if this doc is a pre-write backup
    parent_id, reason

Table
  id                    # stable product id, e.g. ve_table_1
  definition_name       # INI constant name, e.g. veTable1
  title                 # human title from INI TableEditor
  axes:
    x: Axis             # usually RPM
    y: Axis             # usually load
  values: number[][]    # engineering units, row-major y then x (document endian in schema)
  unit                  # e.g. "%", "AFR", "deg"
  value_kind            # ve | afr_target | lambda_target | ignition_deg | other
  bounds: { min, max, digits }
  editable              # from definition + policy
  region_hints[]        # optional: idle, cruise, wot bands for agents

Axis
  id, definition_name
  unit                  # "rpm", "kPa", "%", …
  values: number[]      # bin edges / centers as defined by firmware (document which)
  length

Scalar / Curve — analogous (name, unit, value(s), bounds, definition_name)
```

#### 3.1.2 Why ATM (including LLM fitness)

| Criterion | Why ATM wins |
|-----------|--------------|
| **Named tables** | Agent says “enrich VE around marked pull” → map to `ve_table_1`, not page 4 offset 0x80. |
| **Units** | Patches in AFR/λ/°/%; no silent raw U08 scale mistakes. |
| **Diffable** | Region patches are JSON-merge style; human and agent review the same object. |
| **Definition-bound** | `definition_hash` mismatch → **no write**. |
| **Partial** | Patch ops target cells/regions without rewriting whole flash image. |
| **Round-trip** | Project from INI+pages/MSQ; re-serialize to MSQ / page writes for ecosystem tools. |
| **On-device cost** | Device may hold only active tables + hash; full ATM on host is fine. |

### 3.2 Primary exchange formats

| Role | Format | Rationale |
|------|--------|-----------|
| **Canonical in-process** | **ATM** (language structs; schema-versioned) | Product truth |
| **Agent / host API** | **AMP** — Aether Map Projection (JSON over ATM + **MapPatch**) | LLM- and tool-friendly |
| **Ecosystem on-disk backup** | **MSQ (XML) + definition reference** (INI id/hash) | Opens in TunerStudio / LibreTune |
| **On-wire to ECU** | **Native TS-class page protocol** (family-specific; see #5) | Speak the ECU’s language |
| **Human quick export** | CSV per table (axes + grid) | Spreadsheets; not authoritative backup |
| **Optional lossless** | Page dump + CRCs + definition hash | Forensic restore when projection is lossy |

**Decision:** Do **not** invent a new closed “`.aether-tune` binary” as the only interop. If a single file container is needed later, it **must** be a documented envelope (e.g. zip/json) that includes MSQ **or** ATM JSON + definition hash, not an orphan blob.

### 3.3 Pilot target

| Choice | Value |
|--------|--------|
| **Pilot ECU family** | **FOME** (TunerStudio INI + MSQ + page R/W/burn over **USB/serial**) |
| **Why** | Operator’s vehicle ECU is FOME-based; same TS/INI/MSQ stack as rusEFI; USB-first bench path matches Aether Type-C prototype ([#5](https://github.com/tig/aether/issues/5)). |
| **Architecture generality** | ATM + AMP + INI binder must not hard-code FOME table sizes; Speeduino remains a **simulator / secondary** metal target (fixed och layouts). |
| **Explicit second** | **Speeduino** (sim + simpler surface) and broader **rusEFI** packs — P1 after FOME path is proven. |

### 3.4 What Aether is *not* claiming

- Bit-perfect reimplementation of every TunerStudio proprietary UI section.  
- Ability to open every historical MegaTune pre-XML MSQ without conversion.  
- Safe automated ignition timing increases without human policy (default: **fuel/VE and AFR-target first** for LLM apply).

---

## 4. Definition layer vs data layer

```text
┌─────────────────────────────────────────────────────────┐
│  DEFINITION LAYER (what the ECU is)                     │
│  • INI / ECU definition file                            │
│  • signature, page layout, constant types               │
│  • scales, units, min/max, TableEditor bindings         │
│  • definition_hash = SHA-256(exact definition file bytes) │
└───────────────────────────┬─────────────────────────────┘
                            │ binds
┌───────────────────────────▼─────────────────────────────┐
│  DATA LAYER (current values)                            │
│  • ECU RAM pages (live)                                 │
│  • MSQ constant values (file)                           │
│  • ATM structured tables/scalars (product)              │
└───────────────────────────┬─────────────────────────────┘
                            │ projects
┌───────────────────────────▼─────────────────────────────┐
│  AGENT LAYER (AMP + MapPatch)                           │
│  • named tables, axes, units                            │
│  • region/cell patches, rationale, constraints          │
└─────────────────────────────────────────────────────────┘
```

### 4.1 Definition rules (must)

| Rule | Requirement |
|------|-------------|
| D1 | **No write** without a loaded definition that matches live `firmware_signature` (or explicit offline-edit mode that cannot burn). |
| D2 | Store **`definition_hash`** with every TuneDocument and every backup. |
| D3 | On connect: query signature → select definition → recompute hash → compare to last session; mismatch → reconnect flow, refuse cached writes. |
| D4 | Definitions may ship with Aether (known FOME/Speeduino INIs), come from host (#1), or (later) from ECU mass-storage (rusEFI-style). Source recorded in provenance. |
| D4a | **Host-supplied definitions are untrusted for live write until pinned.** A first-seen INI that merely *claims* the live `firmware_signature` **must not** alone enable RAM write or burn. Require one of: (1) **shipped trust list** `signature → definition_hash` (or equivalent pack id), (2) **operator pin** (“trust this definition for this ECU” → stored pin: signature + hash + source), or (3) **read-only mode** until pin. After pin, D1–D3 apply as usual. |
| D5 | Product **must not** invent constant layouts by guessing page dumps. |
| D6 | **`definition_hash` input bytes (canonicalization):** default **SHA-256 over the exact byte sequence of the definition file as distributed/stored** (no line-ending rewrite, no comment strip, no conditional expansion before hash). If the product later supports “logically equivalent” INIs, it **must** publish a separate normative canonicalization algorithm and a schema version; until then, **bit-identical file bytes** are the only portable authority. Host and device **must** hash the same stored blob. |

### 4.2 Data rules (must)

| Rule | Requirement |
|------|-------------|
| V1 | Live values are **RAM** until **burn**; product UI and agents must distinguish **pending**, **RAM-active**, **burned**. |
| V2 | Full backup = full page set (or full MSQ export) **before** first write in a session that will mutate. |
| V3 | Partial table write maps ATM region → byte ranges via definition offsets; never hand-written magic offsets in call sites. |

---

## 5. Read path / write path / verify / burn

Shared transport/session is **#5**. This section is the **map-layer contract** on top of a live session.

### 5.1 Read path (must)

```text
Session up (#5)
  → query signature / version
  → bind definition (hash)
  → read pages (or subset for known tables)
  → decode constants → ATM
  → optional: project AMP for host/agent
  → optional: export MSQ / CSV
```

| Step | Must / should |
|------|----------------|
| Signature match | **Must** before treating data as writable |
| Page CRC where ECU supports | **Should** verify; record in TuneDocument |
| Structured decode | **Must** for any product-facing table |
| Full backup export | **Must** before first write in a mutating session |

### 5.2 Write path (must)

Writes are staged:

| Stage | Meaning | Default for LLM |
|-------|---------|-----------------|
| **1. Patch propose** | MapPatch only (no ECU I/O) | Yes |
| **2. Validate** | Bounds, units, definition_hash, policy allowlist | Yes |
| **3. Dry-run** | Apply patch to **local ATM copy**; show diff | Yes |
| **4. RAM commit** | Page `w` (or family equivalent); **no burn** | Human confirm **must** for agent |
| **5. Readback** | Re-read affected ranges; compare | **Must** after RAM commit |
| **6. Burn** | `b` / family burn to non-volatile | **Human-only invoke** (see S5); never bundled with step 4; never callable as an agent-owned RPC |
| **7. Post-burn verify** | Re-read or page CRC | **Should** |

### 5.3 Burn vs RAM (must document in UX and API)

| Mode | Behavior | Use |
|------|----------|-----|
| **RAM only** | Live effect until power cycle / page reload | Interactive tuning, agent trials with easy revert |
| **Burn** | Permanent until next burn | End of session / known-good snapshot |
| **Restore backup** | Write backup pages + optional burn | Rollback |

Flash wear: TS-class docs note finite burn cycles (~100k class on classic MS). Aether **must not** burn on every cell edit; batch burns under human control.

### 5.4 Verify (must)

After any RAM commit of a table region:

1. Readback the **same raw byte range** that was written (page/offset/length).  
2. **Primary compare: raw octets** — expected encoded bytes (after Aether’s scale/pack toward the ECU) vs re-read bytes. **Pass only on exact match**, unless the ECU family documents a normalization (e.g. forced alignment) — then compare against the **post-normalize expected raw**, not against display rounding.  
3. **Do not** use INI `digits` as a readback tolerance. `digits` is **display** decimal precision only; using it as ε can accept multi-count raw corruption or reject valid quantized values.  
4. Optional secondary: decode to engineering units for UX diff only — **not** the safety gate.  
5. On raw mismatch → mark session **write_fault**, refuse further writes until operator resolves, retain backup.

### 5.5 Capability matrix (map R/W)

| Platform | Read pages | Write RAM | Burn | Verify | ATM projection | Phase |
|----------|------------|-----------|------|--------|----------------|-------|
| FOME | Yes | Yes | Yes | Yes | Yes | **P0–P3** (pilot) |
| rusEFI | Yes | Yes | Yes | Yes | Yes | **P0 family / P1–P3** |
| Speeduino | Yes | Yes | Yes | Yes | Yes | **P1–P2** (sim / secondary) |
| MS2/MS3 | Yes | Yes | Yes | Yes | Yes | P2+ |
| MSQ file only | N/A | Offline ATM edit | N/A (file save) | Diff | Yes | **P0** |
| OEM closed | No | No | No | No | No | Out |

---

## 6. Structured projection for agents (AMP)

### 6.1 AMP = ATM as JSON for tools

**Aether Map Projection (AMP)** is the versioned JSON serialization of ATM used on host APIs, wireless bridge (#1), and LLM tool I/O.

Requirements:

| # | Requirement |
|---|-------------|
| A1 | Schema version field (`amp_schema`: `1`). |
| A2 | Every table includes **axes with units** and **values in engineering units**. |
| A3 | Includes `definition_hash`, `firmware_signature`, `ecu_family`. |
| A4 | Optional **context block** (not part of the tune): log summary, mark timestamps, measured AFR stats for a region — supplied by #3/#2, not stored as ECU data. |
| A5 | Size-conscious: host may request **table subset** (`ve_table_1` only) for LLM context windows. |

### 6.2 MapPatch (normative ops)

Patches are the **only** agent write language. Opaque full-page blobs from an agent are **rejected**.

```json
{
  "amp_schema": 1,
  "patch_id": "uuid",
  "base": {
    "definition_hash": "…",
    "firmware_signature": "…",
    "document_hash": "…"
  },
  "rationale": "Marked pull at 4500 rpm / 90 kPa showed AFR 15.2 vs target 12.8; enrich VE.",
  "ops": [
    {
      "op": "scale_region",
      "table": "ve_table_1",
      "x_range": [4000, 5000],
      "y_range": [80, 100],
      "factor": 1.08,
      "clamp": true
    },
    {
      "op": "set_cells",
      "table": "afr_table_1",
      "cells": [
        {"x": 4500, "y": 90, "value": 12.5}
      ],
      "interp": "nearest_bin"
    }
  ],
  "constraints": {
    "max_abs_delta_pct": 15,
    "tables_allow": ["ve_table_1", "afr_table_1"],
    "disallow": ["ignition_table_1"],
    "require_human_confirm": true
  }
}
```

#### Supported ops (v1)

| Op | Meaning |
|----|---------|
| `set_cells` | Set absolute engineering values at axis coordinates (nearest-bin or exact index). |
| `add_cells` | Add delta to cells. |
| `scale_region` | Multiply region by factor; optional clamp to bounds. |
| `smooth_region` | Light local smooth (optional P2+; may be host-only). |
| `set_scalar` | Scalar constant change (guarded allowlist). |

#### Rejected ops (v1)

- Raw page overwrite without definition decode.  
- Whole-firmware flash.  
- Ignition advance **increase** unless product policy explicitly enables (default **deny** for agents).  
- Definition mutation.

### 6.3 Validation gates (must, before any ECU I/O)

1. `base.definition_hash` == live session definition hash.  
2. `base.firmware_signature` == live signature.  
3. `base.document_hash` == hash of current ATM (detect mid-air collision).  
4. Every op’s table in allowlist; values within definition min/max.  
5. Max cell delta / max region factor within policy.  
6. No NaN / Inf; axis ranges map to real bins.  
7. Agent identity + human confirm token for commit (see §8).

---

## 7. LLM edit architecture (end state)

**North star:** Natural-language intent → safe table change, with Aether (and/or host LLM via #1) never skipping safety.

This section is **in scope for the plan**; **out of scope for implementation** on this ticket.

### 7.1 End-state flow

```text
┌────────────┐   wireless/USB    ┌──────────────┐
│ Host LLM   │ ←───────────────→ │ Aether GCU   │ ←── serial/USB ──→ ECU
│ (#1)       │   AMP + logs      │ bridge/store │
└─────┬──────┘                   └──────┬───────┘
      │                                 │
      │ 1. Intent: "high AFR at mark"   │
      │ 2. Pull: AMP subset + log slice │
      │    + marks (#2) + session meta  │
      ▼                                 │
 propose MapPatch + rationale           │
      │                                 │
      │ 3. validate (host and/or device)│
      │ 4. dry-run diff (ATM')          │
      │ 5. human confirm (device and/or │
      │    host policy)                 │
      │ 6. RAM commit + readback        │
      │ 7. optional burn (separate)     │
      └─────────────────────────────────┘
```

### 7.2 Context packaging (why change *this* cell)

| Input | Source issue | Role |
|-------|--------------|------|
| Current ATM/AMP tables | #4 | What to edit |
| Time-aligned log slice | #3 | Measured AFR/λ, RPM, load |
| Event marks | #2 | “the marked pull” time anchors |
| Target AFR table / stoich | ATM | Expected mixture |
| Operating notes | host | Fuel, altitude, goal (richer for race, etc.) |

**Derived features for the agent (should):**

- Cells visited during mark window (RPM×load histogram on table bins).  
- Mean / min measured λ vs target per visited cell.  
- Suggested region bounds (convex hull of visited bins + 1-cell padding).

### 7.3 Human vs agent policy

| Actor | Propose patch | RAM write | Burn | Ignition enrich | VE enrich | AFR target change |
|-------|---------------|-----------|------|-----------------|-----------|-------------------|
| Human (on-device later) | Yes | Confirm | Confirm | Policy | Yes | Yes |
| Human (host tool) | Yes | Confirm | Confirm | Policy | Yes | Yes |
| LLM agent | Yes | **Only via human-minted RAM token** (agent never self-confirms) | **Forbidden** — agent **must not** call burn; may **request** burn text for a human to invoke separately | **Default deny** | Allowlist | Allowlist |

**S5 consistency:** the LLM **cannot burn at all** (not even with a token the agent holds). Burn is always a **human-initiated** operation after the human has reviewed RAM state (and typically after agent RAM work used a human-minted, single-use RAM token). “Confirm” for RAM may be: physical button on Aether, host UI checkbox, or high-assurance token — product UX later; **API must require a scoped confirm handle** (§11).

### 7.4 Failure and rollback

| Event | Response |
|-------|----------|
| Validate fail | Return structured errors; no I/O |
| Readback mismatch | Restore last backup to RAM (if safe); alert |
| Link drop mid-write | Resume only after full re-read + hash check |
| User abort | Discard pending patch; ECU unchanged if pre-commit |
| Post-burn regret | Restore backup MSQ/pages + burn (explicit) |

### 7.5 Host story (#1)

| Mode | Map storage | Who validates | Who talks to ECU |
|------|-------------|---------------|------------------|
| **Bridge** | Host holds ATM; Aether is serial/USB/BT/Wi-Fi pipe + optional confirm UI | Host primary; device re-validates before write | Aether session |
| **Edge-assist** | Aether holds last backup + active AMP subset | Device gates always | Aether |
| **Offline file** | MSQ/AMP on host | Host only; no burn until live match | None |

Device **must** re-check definition_hash and confirm token even if host already validated (malicious or buggy agent).

---

## 8. Safety and versioning model

### 8.1 Hard rules (must)

| ID | Rule |
|----|------|
| S1 | **No-write-if-mismatch** — definition_hash or firmware_signature mismatch ⇒ refuse mutate. |
| S2 | **Backup-before-write** — full tune backup stored (device and/or host) before first RAM write in a mutating session. |
| S3 | **Readback-after-write** — required for automated and human paths. |
| S4 | **Burn is explicit** — never implied by “apply patch”. |
| S5 | **Agent boundaries** — LLM **cannot burn** (no agent-callable burn path). LLM cannot RAM-write without a **human-minted, single-use** confirm token scoped to that patch (§11). Agent may only *propose* that a human burn. |
| S6 | **Allowlists** — first LLM apply surface is fuel-related tables only (VE, AFR/λ target); ignition advance increases denied by default. |
| S7 | **Audit log** — patch_id, actor, timestamps, diff summary, success/fail retained with session. |
| S8 | **No silent full-flash** — full page image write only as restore-from-backup with confirm. |

### 8.2 Versioning

| Object | Version field | Notes |
|--------|---------------|-------|
| ATM / AMP schema | `amp_schema` integer | Breaking changes increment; old readers fail closed |
| MapPatch | same schema family | Forward-compatible additive ops preferred |
| Definition | `definition_hash` + iniVersion if present | Hash is authority |
| Document | `document_hash` over structured ATM (exclude raw_pages optional) | Optimistic concurrency |

### 8.3 Safety copy locations (should)

1. Host project folder (primary for #1 workflows).  
2. On-device flash/SD if present (last-known-good).  
3. Optional: export MSQ named with timestamp + signature slug.

---

## 9. Import / export / bridge matrix

| Format | Direction | Priority | Fidelity notes |
|--------|-----------|----------|----------------|
| **ATM in-memory** | — | P0 | Canonical |
| **AMP JSON** | import/export | P0 | Agent/host |
| **MSQ XML** | import/export | P0 | Needs matching INI; TS/LibreTune open |
| **INI definition** | import (bind) | P0 | Not “tune data”; required companion |
| **CSV table** | export (import optional) | P1 | Weak metadata; good for spreadsheets |
| **Page dump + CRC** | export/import | P1 | Lossless device restore |
| **msqpart** | import later | P2 | Partial TS dialog saves |
| **OEM binary** | — | Out | Encrypted/closed |

**Bridge-through:** When Aether cannot decode a family, it may still **pass through** serial to a host tuner (#1) without claiming ATM fidelity — but must not label pass-through bytes as a validated TuneDocument.

---

## 10. Phased implementation

| Phase | Deliverable | Success signal |
|-------|-------------|----------------|
| **P0 — Backup / export** | Offline MSQ import → ATM; ATM → MSQ/CSV export; **FOME** INI bind on host; no live write | Open exported MSQ in TS or LibreTune; definition_hash stable |
| **P1 — Structured live read** | Session (#5) + **FOME** page read over USB → ATM/AMP; table subset API; backup snapshot on connect | Live VE/AFR/spark visible as AMP; matches TS within scale digits |
| **P2 — Guarded human write** | MapPatch validate + dry-run + RAM write + readback + explicit burn; backup-before-write; audit | Human enriches one VE region safely; restore backup works |
| **P3 — LLM-assisted propose/apply** | Host agent (#1) consumes AMP + log marks (#2/#3); proposes MapPatch; human confirm on host/device; **FOME pilot only** first | “Fix lean at mark” produces validated patch and confirmed RAM apply |

### 10.1 Dependencies

| Dep | Issue | Need |
|-----|-------|------|
| Transport/session | #5 | Signature query, page r/w/burn, USB-first |
| Log format + pull | #3 | Context for agent |
| Event marks | #2 | Time anchors for “the pull I marked” |
| Wireless host | #1 | LLM runtime off-device; AMP transport |
| Face / product | spec.md | Confirm UX; not full table editor on 1.8″ |

### 10.2 Explicit non-claims per phase

- P0 does **not** require metal ECU.  
- P2 does **not** require LLM.  
- P3 does **not** auto-burn or edit ignition by default.

---

## 11. API sketch (contract-level)

Not binding code — shapes for future `specs/inputs.md` / host IPC.

```text
tune.get_identity() -> { signature, definition_hash, ecu_family, definition_pin_state }
tune.pin_definition(operator_confirm) -> { definition_hash, signature }   # human only
tune.backup() -> TuneDocument id
tune.read_tables([ids]) -> AMP
tune.diff(doc_a, doc_b) -> structured diff
tune.validate_patch(MapPatch) -> { ok, errors[], dry_run_diff }
tune.apply_patch(MapPatch, confirm_token, mode=ram|dry_run) -> result
  # dry_run: no token. ram: token required; actor may be agent *holding* a human-minted token
tune.burn(confirm_token, pages?) -> result
  # human actor only — reject if actor=agent even with a token
tune.restore(backup_id, confirm_token, burn:bool) -> result
  # burn=true requires human + burn-scoped token; never agent
```

#### Confirm token rules (must)

| Rule | Requirement |
|------|-------------|
| T1 | Token is **minted only by a human path** (device UI, host UI, or out-of-band operator). Agents **request**; they **do not mint**. |
| T2 | Each token is bound to **all** of: `session_id`, `operation` ∈ {`ram_apply`,`burn`,`restore_ram`,`restore_burn`}, `patch_id` and/or `document_hash`, **affected page set**, `definition_hash`. |
| T3 | **Single use** — successful consume invalidates the token; failed attempt **should** invalidate or decrement a tight attempt budget. |
| T4 | **Expiry** — short TTL (recommend ≤ 5 minutes idle; exact value product policy). |
| T5 | A token minted for **`ram_apply` must not** authorize **`burn`**, restore, or a different patch/document hash. Burn requires a **separately minted** `burn` token after human review of post-RAM state. |
| T6 | Device **must** re-validate token binding server-side (or on-GCU); host-supplied “trust me” flags are ignored. |

---

## 12. Open questions

| # | Question | Impact |
|---|----------|--------|
| Q1 | ~~First metal pilot?~~ **Resolved:** **FOME** on operator vehicle + Aether USB prototype | — |
| Q2 | On-device table editor vs host-only edits for P2? | UX scope on 1.8″ |
| Q3 | Where do INIs live long-term — ship set, host library, ECU-provided? | Offline robustness |
| Q4 | Exact AMP JSON Schema file location and CI validation? | Host tooling |
| Q5 | Should Aether ever auto-burn after N successful RAM readbacks? (**Recommend: no**) | Safety |
| Q6 | Multi-table fuel (dual VE banks) — project as separate ATM tables from day one? | Schema |
| Q7 | rusEFI pack depth vs Speeduino sim after FOME P0–P2 | Lab bandwidth |
| Q8 | Legal/licensing note for bundling third-party INIs | Distribution |

---

## 13. Acceptance criteria (for closing #4)

- [x] Comparison of TS/MSQ-class, Speeduino, rusEFI, FOME, and peers (this doc + research notes).  
- [x] Chosen internal representation (**ATM**) with rationale including **LLM edit**.  
- [x] Primary exchange (**AMP** + **MSQ+INI**) and import/export matrix.  
- [x] Safety/versioning rules for human and agent writers.  
- [x] End-state LLM flow and phases **P0–P3**.  
- [x] Handoff to #5 (transport), #3/#2 (context), #1 (host LLM).  
- [ ] Follow-up **implementation** issues filed (post-merge, not this PR).  

Closing #4 means **spec accepted**, not product map R/W shipping.

---

## 14. Handoff checklist

| To | Deliver |
|----|---------|
| **#5 serial** | Page read/write/burn + signature query for **FOME** over USB; shared session with map layer |
| **#3 logging** | Channel set sufficient to bin RPM×load×AFR against tables; export that host agent can join to marks |
| **#2 marks** | Stable timestamps/IDs in logs for region suggestion |
| **#1 wireless** | AMP + MapPatch + confirm token transport; never raw unauthenticated burn RPC |
| **Implementation epics** | P0 host MSQ/INI/ATM + **LibreTune/FOME goldens** → P1 live FOME read → P2 write gates → P3 agent loop; see §16 (prove first) |

---

## 15. Related artifacts

| Path | Role |
|------|------|
| [spec.md](spec.md) | Product mission; links here |
| [docs/research/map-formats.md](../docs/research/map-formats.md) | Survey detail + **OSS leverage map** |
| [afr-face.md](afr-face.md) | Face stays display; not a full map editor |
| [lexicon.md](lexicon.md) | UI phrases (extend when map UI appears) |

---

## 16. Implementation leverage (OSS)

**Status:** Decision record for implementers (still **spec**, not code).  
**Full candidate tables:** [docs/research/map-formats.md §13](../docs/research/map-formats.md).

### 16.0 Stance: prove first, hygiene later

**Default for this phase of Aether:** move fast and **use the real ecosystem** — FOME, rusEFI, LibreTune, Speeduino tools, TS as closed peer — for **testing, validation, HIL, goldens, and operator workflows**. Do **not** block proof work on perfect GPL isolation.

| Mode | What it means |
|------|----------------|
| **Prove / lab / gh ship-vehicle** | Clone, run, compare against, shell out to, capture fixtures from, and instrument **FOME / rusEFI / LibreTune** freely. CI may depend on them. Gray areas around “is this repo the ship vehicle?” are **accepted for now** — document, don’t stall. |
| **Product / redistribute hygiene** | Before a **wider public binary release** (or if counsel asks), revisit static-link and redistributed source trees. Issues live in §16.5 as a **checklist**, not a gate on P0–P3 demos. |

**Do not be pedantic in PRs:** “we used LibreTune to validate MSQ” is a **success**. “we cannot open LibreTune because GPL” is the wrong optimization target right now.

### 16.1 Policy (working rules)

| Rule | Requirement |
|------|-------------|
| L1 | **Use GPL ecosystem tools hard** for test/validation: LibreTune open/save, FOME/rusEFI as live ECU, Speeduino sim, msqur view — **expected and encouraged**. |
| L2 | **Prefer permissive** for greenfield Aether code (ATM/AMP/MapPatch, face, logger) when building new modules — not as a reason to avoid GPL oracles. |
| L3 | **Metal should still prefer ESP-IDF / MIT/Apache** for USB/FS/JSON plumbing; if a temporary GPL experiment accelerates a spike, **label the branch/spike** and plan a clean path — don’t invent license theater mid-demo. |
| L4 | **TunerStudio proprietary code / closed algorithms: no reuse.** Public INI docs + observed wire/file behavior + open peers (LibreTune, FOME) are fair game. |
| L5 | **Long-term product code** for INI/MSQ/ATM should end up Aether-owned (clean-room or clearly licensed). Getting there via GPL goldens and side-by-side is fine. |
| L6 | **Document known license friction** (§16.5) so a later pass can clean up; do not invent process that slows HIL. |

### 16.2 Top OSS picks (use these)

| Pick | Role | SPDX | How Aether uses it **now** |
|------|------|------|----------------------------|
| **LibreTune** ([RallyPat/LibreTune](https://github.com/RallyPat/LibreTune)) | Best open TS-class host (INI + MSQ + serial + **FOME**) | **GPL-2.0** | **Primary validation host:** open Aether-exported MSQ, compare tables, serial smoke. Sidecar, submodule, or local clone — all OK for prove mode. |
| **FOME** ([FOME-Tech/fome-fw](https://github.com/FOME-Tech/fome-fw)) | Pilot vehicle ECU + INI + TS behavior | **GPL-3.0 + additional terms** | **HIL target #1.** Talk USB/serial; pull INI; capture pages/MSQ goldens; burn only under safety gates. |
| **rusEFI** ([rusefi/rusefi](https://github.com/rusefi/rusefi)) | Peer family; console + TS sources | **GPL-3.0 + additional terms** | Second metal / protocol study / USB INI delivery patterns. |
| **Speeduino** + **speeduino-serial-sim** (MIT) | Sim / secondary | GPL-2.0 · **MIT** sim | CI without the car; not a substitute for FOME HIL. |
| **jsonschema** (MIT) + **python-json-patch** (BSD-3-Clause) | Host AMP validate / structural tests | Permissive | Schema CI; MapPatch domain ops stay Aether-owned. |
| **cJSON** (MIT) | Optional metal/host JSON | MIT | AMP subset on wire if needed. |
| **msqur** (GPL-3.0), **MegaTunix** (GPL-2.0) | Viewers / archaeology | GPL | Quick MSQ inspect when useful. |
| **TS_lib** (MIT) | Arduino TS helper | MIT | Framing study. |
| **nanopb** / **FlatBuffers** | Binary schemas | Permissive | **Defer** until prove needs them. |

### 16.3 Must-build (product path — can lag goldens)

| Component | Layer | Note |
|-----------|-------|------|
| ECU-aware **INI binder** | Host | No permissive standalone lib; may **bootstrap** by comparing to LibreTune until Aether binder is good enough |
| **MSQ XML** import/export | Host | Gold = “LibreTune / TS opens our MSQ” |
| **ATM / AMP / MapPatch** | Host (+ thin metal) | Aether IP; LLM north star — build even while goldens come from GPL tools |
| **TS-class page client** | Metal + host | Shared with #5; implement against **live FOME**, not only paper protocol |
| Safety gates + audit | Both | Spec §8 — product requirement regardless of OSS |
| FOME fixture pack | Host CI | Capture from real ECU + LibreTune; commit fixtures (data), not necessarily full firmware trees |

### 16.4 Recommended stack by phase (P0–P3)

| Phase | Build | **Use for proof** | Hygiene note (later, not a gate) |
|-------|-------|-------------------|----------------------------------|
| **P0 — Backup / export** | Host INI binder; MSQ↔ATM; AMP; FOME INI pack | **LibreTune + TS** open round-trip; real FOME MSQ samples | Prefer not to *ship* LibreTune inside Aether binary; CI sidecar is fine |
| **P1 — Live read** | Session (#5) page read → ATM | **FOME USB HIL**; rusEFI peer; speeduino-serial-sim for CI | Avoid pasting GPL `tunerstudio.cpp` into metal if a short clean client works; if you vendor temporarily, flag it |
| **P2 — Guarded write** | MapPatch → RAM → readback → burn | Validate with LibreTune re-read + FOME live | Safety over license pedantry |
| **P3 — LLM propose/apply** | Agent + confirm + logs/marks | Same HIL stack | Don’t disable gates for agents |

**Order:** host MSQ/INI/ATM + **real FOME validation** first → metal page R/W. Device is not a full TunerStudio clone.

### 16.5 License / ship risks (documented, not blocking)

These are **known issues to revisit** before a polished public redistributable — **not** reasons to skip LibreTune/FOME in the lab.

| Topic | What’s the gray area? | Prove-mode practice | Later cleanup |
|-------|----------------------|---------------------|---------------|
| **GPL tools in CI / gh repo** | Is the monorepo / release artifact a “combined work”? | Use LibreTune/FOME as **dev/test deps**, submodules, or external paths; note in README | Separate product license notice; optional non-GPL CI path |
| **Static link of GPL into metal/host** | Classic viral-link concern | Prefer not to; if a spike links something, **label the spike** | Replace with Aether-owned client before wide ship |
| **FOME/rusEFI additional terms** | Off-road / non-aircraft style caveats beyond bare GPL | Use for HIL; product docs stay honest about vehicle use | Counsel + disclaimers when marketing solidifies |
| **Bundling third-party INI** | Definition files live next to GPL firmwares | Record source URL + firmware rev; commit what we need for pilot | Prefer user-supplied INI when possible (Q8) |
| **“TS compatible” wording** | Interop vs affiliation | Fine for engineering | Marketing review |
| **TunerStudio closed code** | Still no decompile / no proprietary algorithm lift | Observe file/wire; use open peers | Unchanged hard line |
| **RomRaider / OEM ROM** | Wrong stack | Ignore | Out of scope |

### 16.6 Acceptance add-on (OSS research)

- [x] Candidate inventory with SPDX, host vs metal fit (research §13).  
- [x] P0–P3 stack: **prove with FOME/LibreTune/rusEFI**, build Aether ATM/AMP.  
- [x] License risks **documented without blocking** proof work.  
- [x] Must-build list for product path; goldens may come from GPL ecosystem first.  
