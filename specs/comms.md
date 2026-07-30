# Aether comms — ECU and host links

**Rev 0.3 · July 2026**  
**Writing mode:** Technical (STE bias).  
**Status:** **Normative product contract** for this layer. Implementation may lag.  
**Addresses:** [#5](https://github.com/tig/aether/issues/5).  
**Related:** [#1](https://github.com/tig/aether/issues/1) agent UX; [#2](https://github.com/tig/aether/issues/2) logging; [#3](https://github.com/tig/aether/issues/3) log files; [#4](https://github.com/tig/aether/issues/4) map/tune R/W.

| Related doc | Role |
|-------------|------|
| [spec.md](spec.md) | Product mission |
| [afr-face.md](afr-face.md) | Face channels from the live bus |
| [lexicon.md](lexicon.md) | Preferred terms |
| [docs/research/serial-protocols.md](../docs/research/serial-protocols.md) | **Non-normative** survey only |
| `spike/` | HIL harness + goldens; not product truth alone |

**Single source of truth:** This file is the product contract for ECU/host comms. Issue #5 tracks work; it must not hold a second full spec. Research must not contradict this file on wire facts.

**Filename history:** Drafted as `inputs.md`, renamed to `comms.md` (both sides of the device).

Preferred terms: **transport**, **framing**, **och**, **signature**, **definition**, **poll**, **calibration**, **RAM write**, **burn**, **backup**.

---

## 1. Scope

### 1.1 In scope

1. **ecu_link** — serial-class path to ECU firmware (USB, UART/RS-232, internal pipe when co-located).
2. **host_link** — path to a host PC (USB device, Wi‑Fi, BT) when present.
3. Two host scenarios (§2): **agent** (primary) and **tool passthrough** (secondary).
4. External GCU and built-in (integrated with FOME-class ECU) topologies (§3).
5. TunerStudio-compatible **client** protocol when Aether is ecu_link master.
6. Canonical live samples for face + logger; shared session for #4 / agent writes.

### 1.2 Out of scope

| Out | Where |
|-----|--------|
| Log file formats | #3 |
| TunePatch / pin policy | #4 |
| Agent chat / LLM UX | #1 (reuses host_link + session here) |
| CANbus decode | Appendix B |
| TunerStudio replacement UI | Not a goal |

### 1.3 Client family ownership (normative)

| Path | Protocol | Role |
|------|----------|------|
| **Vehicle ECU (FOME / rusEFI / Speeduino / MS-class)** | TunerStudio-compatible **binary** (this file) | **P0 product path** |
| **AESP line client** (`ecu_client` / TCP sim bench, if present in tree) | Line-oriented AESP | **Sim / software V-ECU only** — not the car USB/FOME path |

Do not implement two competing vehicle ECU clients for P0. AESP must not be the metal FOME path.

### 1.4 Pilot (P0)

| Fact | Value |
|------|--------|
| Device | External Aether prototype (ESP32-S3 1.8″ AMOLED, Type-C) |
| ECU | FOME-based (Classic Daily / Polygonus class) |
| Outcome | Live RPM, load (TPS and/or MAP), λ/AFR on face without a PC (**Aether master**) |
| Wire family | TS binary, FOME/rusEFI lineage |

Speeduino = P1 CI/sim dialect only.

---

## 2. Host scenarios

Both use **host_link**. They differ by **who masters ecu_link**, not by a third protocol stack.

### 2.1 Primary — agent (Aether master)

```text
ECU ◄── ecu_link ──► Aether ◄── host_link ──► Host PC (agent / host app)
                       ├── face + logger
                       └── session APIs (logs, cal R/W per #4)
```

- Aether is sole **protocol master** on ecu_link.
- Host uses Aether APIs / host protocol (#1) — not raw TS as the only interface.
- Face **must** keep working while agent is connected (poll-lock fairness).
- Agent writes **must** use session + backup rules. Unsupervised burn **must not** occur.

### 2.2 Secondary — tool passthrough (host-tool master)

```text
ECU ◄── ecu_link ──► Aether (byte relay) ◄── host_link ──► TunerStudio / log tools
```

- Host tool is protocol master; Aether **must not** inject client TX on that ecu_link while relay is active.
- Default face policy on single-pipe external units: **pause** live client (quality `BRIDGED` / invalid). Second ECU channel or built-in sample bus may keep face alive (Appendix A).

### 2.3 Selection

- No host attached → Aether master for face/logger.
- Operator/policy selects agent service vs tool passthrough when host attaches.
- Entering passthrough **must** stop Aether client TX on that pipe first.
- Leaving passthrough **must** re-identity before client poll resumes.

---

## 3. Topologies

| Topology | ecu_link | host_link |
|----------|----------|-----------|
| **External GCU** | USB host CDC/VCP or UART to ECU | USB device and/or Wi‑Fi/BT to PC |
| **Built-in** (Aether co-located with FOME-class ECU) | Internal pipe (UART/RPC/…) still exposed as `serial_link` | Same host scenarios |

Upper layers **must not** special-case built-in except via the link adapter. GPL ECU sources **must not** be linked into Aether.

---

## 4. Architecture (normative core)

### 4.1 Master rule (invariant)

On a given **ecu_link**, exactly one protocol master:

| Master | Meaning |
|--------|---------|
| **AETHER** | Framing + session + dialect; face/logger/agent/#4 |
| **HOST_TOOL** | Pass-through relay only; no Aether TS TX |

There is **no** third master mode. “Agent bridge” = **AETHER master** + host_link service. Do not add `AGENT_BRIDGE` as a separate wire mode in code.

```text
  Face · Logger · Agent(#1) · Tune(#4)
              │
              ▼
       live channel bus
              │
              ▼
       dialect decoder
              │
              ▼
     session (master = AETHER | HOST_TOOL)
         │                    │
   framing (AETHER)     bridge relay (HOST_TOOL)
         │                    │
         └────────┬───────────┘
                  ▼
         serial_link × 2
         · ecu_link
         · host_link
```

### 4.2 Layers

| Layer | Must | Must not |
|-------|------|----------|
| **serial_link** | open/close/rw; link events; baud if needed | Parse TS; know och |
| **Framing** | Envelope + CRC when AETHER master | Run as rewriter in pure passthrough |
| **Bridge relay** | Bounded bidirectional byte copy | Dual master TX |
| **Session** | Master selection; identity; poll lock; reconnect | Draw UI; own log files |
| **Dialect** | Pack → physical values + present bits | Own sockets |
| **Live bus** | Samples, quality, rates | On-disk format |

### 4.3 Principles

1. Speak ECU TS protocol when Aether is master.  
2. One stack; many transports.  
3. Never two masters on one pipe.  
4. One client poll feeds face + logger (dual rate).  
5. No silent bad face data.  
6. Portable freestanding C for framing/session/dialect/bus.  
7. GPL ECU trees reference-only.

### 4.4 Module map

| Concern | Home |
|---------|------|
| `serial_link` | `include/gcu/serial_link.h` + adapters |
| TS frame + CRC | `include/gcu/ts_frame.h` + `src/` |
| Bridge relay | `include/gcu/bridge_relay.h` + `src/` |
| Session | `include/gcu/ecu_session.h` + `src/` |
| FOME pack | tables from INI + goldens |
| Live bus | `include/gcu/live_bus.h` + `src/` |
| Board | `firmware/main/hal_board.*` only |

Language: **C** (`silico.toml`).

---

## 5. Session (AETHER master)

1. Identity: FOME `S` (signature), `V` (version) when available.  
2. Bind dialect pack from signature.  
3. Och poll, or yield **poll lock** to map/agent write.  
4. Link down / frame burst → invalidate bus; reconnect with backoff.

### 5.1 Poll lock

Exclusive for och and page R/W/burn. Face, logger, and agent must not bypass session on ecu_link.

### 5.2 FOME commands (pilot)

| Purpose | Shape |
|---------|--------|
| Signature | `S` |
| Version | `V` |
| Och | `O` + LE u16 offset + count |
| Page read | `R` + offset + count (≤ blockingFactor) |
| Page CRC | `k` + offset + count → BE IEEE CRC of page bytes |
| Page write | `C` + offset + count + data (**RAM write**) |
| Burn | `B` — verify **post-condition** (readback/CRC), not flag alone |

Pilot HIL: burn response flag **`0x04`** with post-burn page match. Treat as success only with match.

### 5.3 Backup before mutate

Before RAM write or burn: full page (or full cal) **backup** + CRC when supported. Live-only paths must not write pages.

---

## 6. Framing (AETHER master)

### 6.1 Envelope — FOME P0 (wire-validated)

| Direction | Layout | CRC32 covers |
|-----------|--------|--------------|
| Request | BE u16 size \| payload \| BE u32 CRC | **payload only** |
| Response | BE u16 size \| flag \| payload \| BE u32 CRC | **flag \|\| payload** |

- size = bytes after size field, before CRC (response size includes flag).  
- CRC = IEEE / zlib-compatible.  
- **Do not** use size-inclusive CRC for this FOME family unless a golden proves it.  
- Support bare `Q`/`S` identity where ECU answers without envelope.

Half-duplex: no new client request until response complete. CRC/timeout → session error; never publish corrupt och as OK.

Passthrough: do not mutate tool bytes.

---

## 7. Transports

### 7.1 serial_link API

open, close, write, read (or RX callback), link-state events.

### 7.2 ecu_link

| Transport | Phase |
|-----------|-------|
| USB host CDC-ACM (composite → ACM) | **P0** external |
| USB host VCP (CP210x/FTDI/CH34x) | P0–P1 |
| UART / RS-232 | P1 / built-in |
| Internal pipe | Built-in |

### 7.3 host_link

| Transport | Phase |
|-----------|-------|
| USB device CDC | P0+ |
| Wi‑Fi TCP **server** | P2 (agent + optional passthrough) |
| BT Classic SPP | P3 external module / SKU — **not** S3 on-die Classic |

Document USB host vs device per path. Hot-unplug updates master and quality. Open wireless passthrough needs explicit operator enable (not always-on).

---

## 8. Dialect and live bus

### 8.1 Packs

Signature rule; och size; field map; endianness; page size; blocking factor. Present bitset required.

**Minimum face channels:** RPM; load (TPS and/or MAP); λ or AFR.

**P0 FOME facts:**

| Item | Value |
|------|--------|
| Signature example | `rusEFI (FOME) .2026.06.03.proteus_f7.3416487136` |
| ochBlockSize | 1260 |
| RPM | U16 @ 4 |
| TPS | S16 @ 24 × 0.01 % |
| MAP | U16 @ 136 × 1/30 kPa |
| lambda1 | U16 @ 92 × 1e-4 |
| pageSize | 26552 |
| blockingFactor | 1320 |

### 8.2 Sample

`ts_ms` (int64), source (family, links, pack, **master**), quality, present, physical values.

Dual rate: face ~10–20 Hz; log ~20–50+ Hz; logger drops under back-pressure without stalling face.

### 8.3 Quality

| Value | Meaning |
|-------|---------|
| `OK` | Fresh decode |
| `NO_LINK` | ecu_link down |
| `FRAME_ERROR` | CRC/timeout burst |
| `STALE` | No good poll within budget (default ≤ 500 ms) |
| `SENSOR_INVALID` | ECU/sensor flags |
| `PROFILE_MISMATCH` | Pack/signature failure |
| `BRIDGED` | HOST_TOOL master; local client stopped |

Face: unplug → invalid primary ≤ **1 s**. No green-band on known-bad λ.

---

## 9. Bridge relay (HOST_TOOL master)

- Bounded buffers; no reorder within a direction; count overflows.  
- Either link down → stop relay; session notified.  
- PC presentation: USB CDC COM, Wi‑Fi TCP serial, or BT SPP.  
- Do not run host-tool master and Aether TS TX on the same ecu_link together.

---

## 10. Map / agent write path

Page R/W/CRC/burn via AETHER master session + lock + §5.3 backup. Pin/TunePatch = #4. Agent UX = #1.

---

## 11. Delivery phases (summary)

| Phase | Deliverable |
|-------|-------------|
| **P0** | External GCU; ecu_link USB host; AETHER master; FOME pack; face live |
| **P0b** | host_link USB device; master switch API |
| **P1** | UART; Speeduino pack/sim CI |
| **P1b** | HOST_TOOL passthrough over USB |
| **P2** | Wi‑Fi host_link server; agent host MVP |
| **P3** | BT SPP host_link (external/SKU) |
| **P4** | Built-in internal ecu_link adapters |

P0 exit: real FOME; soak; unplug ≤1 s; host tests on recorded frames.

---

## 12. Tests

- Unit: frame encode/decode; CRC accept/reject; och extract (RPM, TPS/MAP, λ) from **goldens**.  
- Page `k` CRC vs IEEE over page blob.  
- Master switch: AETHER → HOST_TOOL stops poll; reverse re-identifies.  
- HIL: CLIENT soak; passthrough TS identity; agent pull without killing face; unplug.  
- Faults: truncate, bad CRC, unplug, dual-master attempt fails safe.

---

## 13. Acceptance (this document)

- [x] Single normative file (`comms.md`); research non-normative  
- [x] Two masters only (AETHER | HOST_TOOL); agent = AETHER + host service  
- [x] Dual links; external + built-in topologies  
- [x] FOME framing CRC scope from HIL  
- [x] AESP vs TS ownership stated  
- [x] Live bus, quality, backup-before-mutate  
- [ ] Implementation matches at HEAD  

---

## Appendix A — Face during passthrough (non-blocking detail)

| Policy | Use |
|--------|-----|
| **Pause** (default external single pipe) | Face invalid / BRIDGED |
| **Second channel** | Client on secondary ECU port; tools on primary |
| **Integrated bus** (built-in) | Internal samples without TS poll on tool port |

Sniffing tool traffic for face is out of P0.

## Appendix B — CANbus (reserved)

Future CAN decoders publish to the same live bus. No requirements in this rev.

## Appendix C — Open questions

1. External Type-C USB host vs Serial-JTAG PHY.  
2. Agent host wire format (#1).  
3. Built-in preferred internal pipe.  
4. Wireless passthrough auth UX.  
5. Pack size on device vs host-pushed definitions.  
6. λ priority: ECU och vs external wideband serial.

## Appendix D — References

| Source | Use |
|--------|-----|
| FOME HIL (COM13, 2026-07-30) + `spike/goldens/` | Wire CRC and command facts |
| FOME / rusEFI INI | Pack authority |
| MegaSquirt serial PDF (2014) | Vocabulary only — **CRC scope follows HIL for FOME** |
| Issue #5 | Work tracker; superseded as full-text home of this contract |
