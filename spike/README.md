# FOME protocol spike (HIL)

Host-side validation of TunerStudio-compatible framing against a live FOME ECU.

**Normative product contract:** [`../specs/comms.md`](../specs/comms.md).

## Layout

| Path | Role |
|------|------|
| `ts_frame.py` | Pure encode/decode + CRC (no serial) |
| `fome_client.py` | pyserial client |
| `fome_protocol_spike.py` | CLI HIL phases |
| `goldens/fome_envelope.json` | Hex frames for unit tests |
| `tests/test_ts_frame.py` | CRC/scope goldens |
| `SPIKE_RESULTS.md` | HIL session notes |

Bulk capture trees (`run-*`, `fome-backup-*`) are **gitignored**. Keep goldens small.

## Tests (no ECU)

```text
cd spike
python -m pytest tests/ -q
```

## HIL (ECU on COM port)

```text
python fome_protocol_spike.py --port COM13
python fome_protocol_spike.py --port COM13 --write-back --burn
```

Close TunerStudio first. Always backs up the page before write/burn.
