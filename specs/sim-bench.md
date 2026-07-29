# Software bench — virtual ECU + virtual Aether + orchestrator

**Rev 0.2 · July 2026**  
**Status:** Implemented host sim (`sim/`) + portable C ECU client + ESPREC1 on
V-AETHER + QEMU **identity knock** CI job (not boot-print alone).  
**Related:** issue #4 (calibration R/W + burn), #5 (serial session),
[tig/esprec](https://github.com/tig/esprec) (framebuffer capture).

## 1. Purpose

Before metal firmware talks to a real ECU, Aether needs a **software-only**
loop that can prove:

1. Calibration pages live in **RAM** and **flash** with an explicit **burn**.
2. Unburned RAM is lost on **power-cycle**; burned data survives.
3. Backup → golden → mutate → burn → verify → **restore** (§17-shaped).
4. The Aether **host link** answers `identity` like metal.
5. A **synthetic framebuffer** is capturable via **ESPREC1** (`esprec shot`)
   without a panel — same wire as esprec / future QEMU eyes.
6. A **portable C ECU client** (metal-bound) talks AESP over an injected
   transport (host TCP today, UART later).

Real USB and a real FOME are **not** required for this gate.

## 2. Components

| ID | Name | Implementation | Listens / connects |
|----|------|----------------|--------------------|
| **V-ECU** | Virtual ECU | `sim/ecu` | TCP AESP server |
| **V-AETHER** | Virtual Aether device | `sim/aether` | TCP host-link; AESP client → V-ECU; ESPREC1 |
| **C-CLIENT** | Portable ECU client | `src/ecu_client.c` | Transport vtable; `host/ecu_tcp_bench` |
| **ORCH** | Orchestrator | `sim/orch` | In-process bench + scenarios |
| **QEMU-FW** | Real firmware image | `firmware/` + `sim/qemu` | Espressif QEMU serial log |

```text
  pytest / human / CI
           │
           ▼
     ┌─────────────┐   host link (TCP)   ┌──────────────┐   AESP (TCP)   ┌─────────┐
     │  ORCH/host  │ ──────────────────► │  V-AETHER    │ ─────────────► │  V-ECU  │
     │  C-CLIENT   │ ──────────────────► │  identity    │                │ RAM+flash│
     │  esprec*    │ ── esprec shot ───► │  ESPREC1 FB  │                │ burn     │
     └─────────────┘                     └──────────────┘                └─────────┘

  QEMU (CI): firmware/ boot → serial log must contain fw_name=AETHER
```

\* esprec library optional; sim ships a compatible ESPREC1 emit + verifier.

## 3. Named gates

| Gate | Command | When |
|------|---------|------|
| **host_test** | `cmake --build build/host --target host_test` | Every PR (includes `test_ecu_client`) |
| **sim-bench** | `python -m pytest sim/tests -q` | Every PR |
| **sim-orch** | `python -m sim.orch all --out sim/out` | CI smoke |
| **qemu-identity** | CI job: build firmware → QEMU UART TCP → `identity_knock.py` | Every PR (after host-gate) |

## 4. What is proven vs not

### Proven

- Burn mechanics + power-cycle persistence (Python V-ECU + C client TCP).
- Multi-aspect mutation (scalar + curve + table regions) via orch burn soak.
- Operator backup/restore leave the ECU as found.
- Aether identity boot-print + knock (V-AETHER).
- ESPREC1 integrity (meta+raster CRC) + shot over TCP.
- Real plate `firmware/` boots under QEMU and prints identity.

### Not proven yet

| Claim | Needs |
|-------|--------|
| FOME signature / INI / real page map | Live FOME or captured goldens |
| Firmware ECU client on UART → V-ECU/FOME | Metal + transport |
| esprec capture from QEMU serial (product FB) | Metal esprec + virtual FB backend |
| “Burn supported” release language | issue #4 §17.5 on pilot hardware |

## 5. §17 mapping (burn soak)

`sim.orch.bench.burn_soak` exercises a **shaped** B0–B9 through V-AETHER
(`ecu.sign` … `ecu.restore`). See `sim/orch/bench.py`.

## 6. ESPREC / esprec

V-AETHER answers `esprec shot` / `shot` with:

```text
ESPREC1 w=… h=… fmt=rgb565be pack=spi_be enc=b64 nbytes=N crc=0x…
<base64 lines>
ESPREC1_END crc=0x…
```

CRC matches tig/esprec (canonical meta prefix + raster). Host can use
`sim.aether.esprec_port.AetherTcpPort` as a BytePort, or install esprec and
call `grab_frame` / `snapshot`.

## 7. Portable C client

```text
include/gcu/ecu_client.h   — transport vtable + SIGN/R/W/B/POWERCYCLE/CRC
src/ecu_client.c           — no freertos / esp_* (HAL-safe for metal later)
host/test_ecu_client.c     — mock transport unit test
host/ecu_tcp_bench.c       — live TCP against V-ECU (pytest sim/tests)
```

## 8. Acceptance (this rev)

- [x] V-ECU with RAM/flash/burn/power-cycle
- [x] V-AETHER with identity + ECU client + synthetic FB
- [x] ORCH burn-soak green under pytest
- [x] ESPREC1 shot on V-AETHER + verify
- [x] Portable C ECU client + host unit + TCP bench vs V-ECU
- [x] QEMU CI job for firmware identity
- [ ] Firmware-side UART transport for C client
- [ ] esprec snapshot from QEMU serial in product CI
