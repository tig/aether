# Software-only Aether bench

Three components so calibration and device paths can be exercised **without
USB metal and without a real FOME**:

| Component | Package | Role |
|-----------|---------|------|
| **Virtual ECU** | `sim/ecu` | RAM + flash pages, burn, power-cycle, AESP wire protocol |
| **Virtual Aether** | `sim/aether` | Host-link serial (identity + cal verbs + synthetic FB) talking to the ECU |
| **Orchestrator** | `sim/orch` | Wires both, runs scenarios (burn soak, identity, FB capture) |

Normative contract: [`specs/sim-bench.md`](../specs/sim-bench.md).

This is **not** a FOME substitute for pilot signature correctness. It is the
**approved software HIL** for protocol mechanics, burn persistence, Aether
host verbs, and CI. Real FOME remains required before claiming “burn supported
on pilot hardware” (issue #4 §17.5).

## Quick start

From the repo root (so `sim` imports resolve):

```bash
# Full orchestrated scenarios
python -m sim.orch all --out sim/out

# Individual processes (desk layout)
python -m sim.ecu --port 8765 --flash-file sim/out/ecu_flash.json
python -m sim.aether --port 8766 --ecu-port 8765
# then:  nc 127.0.0.1 8766   or a host client
#        identity
#        ecu.sign
#        ecu.backup
```

## Tests (CI gate)

```bash
python -m pytest sim/tests -q
```

## Layout

```text
sim/
  ecu/          # CalibrationStore, AESP protocol, TCP server, client
  aether/       # Device + synthetic RGB565 framebuffer + host TCP
  orch/         # SimBench + burn_soak (§17-shaped) + CLI
  tests/        # pytest
  out/          # local artifacts (gitignored)
```

## C ECU client (metal-bound)

```text
include/gcu/ecu_client.h
src/ecu_client.c
host/test_ecu_client.c      # mock transport (ctest)
host/ecu_tcp_bench.c         # live TCP vs V-ECU (pytest)
```

```bash
cmake -S host -B build/host
cmake --build build/host --target host_test
cmake --build build/host --target ecu_tcp_bench
# pytest starts V-ECU and runs ecu_tcp_bench automatically when built
```

## ESPREC1 (esprec-compatible eyes)

```text
# against V-AETHER host link
esprec shot\n
→ ESPREC1 … / base64 / ESPREC1_END
```

Local verifier: `sim.aether.esprec_emit.verify_esprec1_lines`.  
Optional: install [tig/esprec](https://github.com/tig/esprec) and use
`AetherTcpPort` as a `BytePort`.

## Fidelity ladder

```text
host unit + sim-bench  →  QEMU firmware identity  →  real USB FOME
     always on CI              CI qemu-identity         release claim
```

- **Host sim:** pure Python V-ECU/V-AETHER + C client TCP; green on every PR.
- **QEMU:** real `firmware/` under Espressif QEMU; identity in serial log
  (`sim/qemu/run_identity_check.py`, `tobozo/esp32-qemu-sim`).
- **Metal:** real board + real FOME for product burn claims.

## Wire protocols (summary)

**AESP (ECU):** line commands `SIGN`, `R`, `W`, `B`, `RAMCRC`, `FLASHCRC`,
`POWERCYCLE`, `GOLDEN`, `MUTATE`, … — see `sim/ecu/protocol.py`.

**Aether host link:** boot-prints `fw_name=AETHER fw_version=0.0.1`; answers
`identity`; cal verbs `ecu.*`; framebuffer `fb.meta` / `fb.ppm`.
