# FOME protocol spike results (HIL)

**Date:** 2026-07-30  
**Branch:** `spec/serial-live-protocols`  
**ECU:** Classic Daily / FOME USB CDC (`COM13`, `VID_0483`/`PID_5740`)  
**Normative:** [`specs/comms.md`](../specs/comms.md) rev 0.3

## Wire dialect (validated)

| Direction | Layout | CRC covers |
|-----------|--------|------------|
| Request | BE u16 size \| payload \| BE u32 CRC | **payload only** |
| Response | BE u16 size \| flag \| payload \| BE u32 CRC | **flag \|\| payload** |

| Command | Result |
|---------|--------|
| `S` | `rusEFI (FOME) .2026.06.03.proteus_f7.3416487136` |
| `V` | `FOME proteus_f7 20260424@343fb8` |
| `O` och 1260 | ~20–40 Hz clean poll |
| `R`/`k`/`C`/`B` | Full page 26552; burn flag **0x04**; post-burn match |

Goldens: `goldens/fome_envelope.json` (unit-tested).

## Runs

Local only (gitignored): page backups under `fome-backup-*`, soaks under `run-*`.

Re-run HIL after tooling changes; keep **goldens + tests** as the durable proof for CRC scope.
