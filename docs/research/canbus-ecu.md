# Research notes — CANbus on open-source ECUs

**Date:** 2026-07-31
**Purpose:** Answer one question — *can an Aether device with CAN support use CANbus as the **primary** comms channel for real-time display, logging, and calibration burn?*
**Status:** **Non-normative survey.** Product contract for the comms layer is [specs/comms.md](https://github.com/tig/aether/blob/spec/serial-live-protocols/specs/comms.md) (issue [#5](https://github.com/tig/aether/issues/5), branch `spec/serial-live-protocols` at time of writing). Where this note disagrees with that file on wire facts, **comms.md wins**.
**Method:** Source-of-truth reading of FOME and rusEFI firmware trees (shallow clones, `master`, 2026-07-31), the MegaSquirt 29-bit CAN protocol PDF, Speeduino wiki/firmware docs, and Espressif TWAI documentation. Forum and wiki claims are marked as such.

---

## 1. Short answer

**Yes for FOME/rusEFI-class ECUs — with a split-service design, and only on a new hardware SKU.**

| Aether layer | CAN mechanism | Verdict |
|--------------|---------------|---------|
| Real-time face (AFR, RPM, TPS, MAP) | Broadcast frames (`0x200`+, 20 Hz default) | **Yes** — cheaper and lower-latency than polling; works **listen-only** |
| Logging (wide channel set) | Broadcast + partial `O` och poll over ISO-TP | **Yes** |
| Full calibration read/write + **burn** | TunerStudio binary protocol tunneled over **ISO-TP** (`0x100`/`0x102`) | **Yes** — same `R`/`C`/`k`/`B` command set as USB |
| ECU **firmware** update | OpenBLT over CAN (jump via `0x667`) | Exists; **out of scope** for Aether |

Two qualifications that decide the product shape:

1. **Not portable across the ECU family.** FOME and rusEFI implement TS-over-CAN. **Speeduino does not** (broadcast + OBD-II only; tuning over CAN is "under development"). MegaSquirt does, but through a completely different, chattier protocol (§5).
2. **Not free hardware.** No board in [README Hardware](../../README.md#hardware) has a CAN transceiver. ESP32-S3 and ESP32-P4 both need an external one, and neither supports CAN FD (§7).

The interesting result is architectural, not protocol trivia: **CAN is the only transport that lets Aether hold a full tuning session while TunerStudio stays connected on USB.** That removes the single-pipe conflict that forces `comms.md` §2.2 / Appendix A to pause the face during passthrough.

---

## 2. Four distinct CAN services (do not conflate them)

Every project below implements some subset of the same four service classes. Aether needs different ones for different layers.

| Class | Direction | Payload shape | Use |
|-------|-----------|---------------|-----|
| **A. Broadcast** ("verbose", dash packs) | ECU → bus, unsolicited, periodic | Fixed 8-byte packed structs, one channel-group per ID | Gauges, dashes, loggers |
| **B. Diagnostic request/response** (OBD-II) | Peer → ECU → peer | Mode/PID, ISO-TP where >7 bytes | Generic tools, non-native ECUs |
| **C. Tunneled tuning protocol** | Peer ↔ ECU, session | TS binary over ISO-TP (rusEFI/FOME) or MS 29-bit addressing (MegaSquirt) | Full calibration R/W + burn |
| **D. Bootloader** | Host → ECU | OpenBLT / STM DFU-class | Firmware update |

Class A alone is what most "CAN gauge" products use. It cannot read a calibration. Class C is what makes Aether's remote-programmer story possible over CAN.

---

## 3. FOME

Read from `FOME-Tech/fome-fw` `master`, 2026-07-31.

### 3.1 Class A — verbose broadcast

`firmware/controllers/can/can_verbose.cpp`, scheduled from `can_tx.cpp`.

| Fact | Value |
|------|-------|
| Enable | `enableVerboseCanTx` (TS: `can_broadcast`) |
| Base ID | `verboseCanBaseAddress`, default `CAN_DEFAULT_BASE` = **0x200** (`integration/fome_config.txt:180`) |
| Period | `canSleepPeriodMs`, default **50 ms** (`engine_configuration.cpp:358`), rounded to the 200 Hz CAN cycle |
| ID width | 11-bit; `rusefiVerbose29b` switches to 29-bit |
| Bus | `canBroadcast_e` selects bus 0, bus 1, or both |
| Machine-readable definition | `firmware/controllers/can/FOME_CAN_verbose.dbc` ships in-tree |

Frames are little-endian packed C structs, base + offset:

| Offset | Struct | Channels Aether cares about |
|-------:|--------|------------------------------|
| +0 | `Status` | warning counter, last error code, rev-limit / CEL / pump / fan bits, gear |
| +1 | `Speeds` | **RPM** `u16` @0 (1 rpm/bit), timing, inj/coil duty, VSS, ethanol % |
| +2 | `PedalAndTps` | pedal, **TPS1** `s16` @2 (0.01 %/bit), TPS2, wastegate |
| +3 | `Sensors1` | **MAP** `u16` @0 (1/30 kPa/bit), CLT, IAT, aux, MCU temp, fuel level |
| +4 | `Sensors2` | oil pressure/temp, fuel temp, battery volts |
| +5..+6 | `Fueling`, `Fueling2` | air mass, fuel pulse, knock count, fuel used/flow, **trims** |
| +7 | `Fueling3` | **λ1** `u16` @0 (1e-4/bit), λ2, fuel pressures |
| +8..+9 | `Cams`, `Egts` | opt-in via `canBroadcastCams` / `canBroadcastEgt` |

Scaling constants come from `util/efi_scaled_channel.h` (`scaled_percent` = 0.01 %, `scaled_pressure` = 1/30 kPa, `scaled_lambda` = 1e-4). These match the och scalings already recorded in `comms.md` §8.1 — **the same dialect pack serves both transports**.

Every face channel the AFR screen needs (RPM, TPS, MAP, λ) is in frames +1, +2, +3, +7. Short-term trims — a `spec.md` §3.1 requirement — are in +6.

### 3.2 Class C — TunerStudio over ISO-TP

`firmware/console/binary/serial_can.cpp` + `ts_can_channel.cpp`. This is the load-bearing finding.

| Fact | Value |
|------|-------|
| ECU RX ID (host → ECU) | **0x100** (`CAN_ECU_SERIAL_RX_ID`) |
| ECU TX ID (ECU → host) | **0x102** (`CAN_ECU_SERIAL_TX_ID`) |
| Compiled in | `EFI_CAN_SERIAL`, `TRUE` in `stm32f4/efifeatures.h`, which `stm32f7/efifeatures.h` includes — so the **proteus_f7 pilot class ECU has it** |
| Runtime prerequisites | CAN enabled, `canReadEnabled` **and** `canWriteEnabled` (otherwise a warning is raised) |
| Bus | **Bus 0 only** — hardcoded `CanBusIndex::Bus0` in `sendFrame()` |
| ID configurability | **None.** Compile-time `#define` |
| Transport | ISO 15765-2 single / first / consecutive / flow-control frames, DLC fixed at 8 |
| Flow control emitted by ECU | `BS = 0`, `STmin = 0` ("send everything, no delay") |
| Flow control accepted by ECU | Only `BS = 0`, `STmin = 0`; anything else logs "CAN Flow Control fields not supported" |
| Chunking | TS byte stream is cut into ISO-TP messages of **≤ 76 bytes** (`CAN_FIFO_BUF_SIZE`), chosen as `6 + 10×7` so each message is exactly 11 full frames |
| Short-packet optimization | `TS_CAN_DEVICE_SHORT_PACKETS_IN_ONE_FRAME` (drops size+CRC for ≤7-byte payloads) is **not defined** in either tree — standard size/CRC framing applies over CAN |

Architecturally, `CanTsChannel` is a `TsChannelBase` — the ECU treats CAN as *a byte stream like any other TS channel*, running in **its own thread alongside the USB channel**. Consequences:

- The TS command set is unchanged: `S`, `V`, `O`, `R`, `k`, `C`, `B`. **Burn over CAN is the same `B` command with the same response flags** — no new session semantics, no new backup rules.
- Aether's existing layer stack (`ts_frame` → session → dialect → live bus, `comms.md` §4.2) is untouched. CAN adds **one new `serial_link` implementation**, not a second protocol stack.
- Because chunking is per-76-bytes and not per-TS-packet, the Aether side must treat ISO-TP as a **stream** (reassemble each message, append to a byte buffer), not as one message per TS packet. Implementing strict "one ISO-TP message = one PDU" will break on any response over 76 bytes.
- **One ISO-TP master per bus.** IDs are fixed, so an Aether device and a PCAN/rusEFI WiFi bridge cannot both tune the same ECU concurrently. An Aether on CAN plus a laptop on USB *is* fine — different channels.

### 3.3 Class B and D

- **OBD-II** (`obd2.cpp`): mode 01 responses on the standard `0x7DF`/`0x7E8` pair include `PID_RPM`, `PID_INTAKE_MAP`, `PID_THROTTLE`, `PID_ENGINE_LOAD`, `PID_FUEL_AIR_RATIO_1` (λ), `PID_STFT_BANK1/2`, plus ethanol, oil temp, fuel rate and control-unit voltage in the 0x41-0x60 range. Enough for a degraded but functional AFR face on any rusEFI-lineage ECU whose broadcast is off, and the only realistic path to non-open ECUs.
- **OpenBLT**: `can_rx.cpp` jumps to the bootloader on SID `0x667` with DLC 2, gated by `canOpenBLT` / `can2OpenBLT`. `bootloader/readme.md` documents the older UART/DFU path and explicitly asks whether it should be merged into OpenBLT. Firmware update over CAN is real but is **not** the "burn" in Aether's tuning sense.

---

## 4. rusEFI

FOME is a rusEFI fork; the CAN stack is common ancestry with divergence.

| Area | rusEFI vs FOME |
|------|----------------|
| ISO-TP | Refactored into `firmware/controllers/can/isotp/` with a general `IsoTpBase` — parameterized RX/TX IDs, bus index, padding byte (`0x0A`, chosen to avoid stuff bits), and a vendor "ISO header byte" offset. FOME keeps the older inline `serial_can.cpp`. |
| TS-over-CAN IDs | Same `0x100`/`0x102`, same bus-0 hardcoding |
| **Discovery** | `announceCanConsole()` broadcasts a `{txId, rxId}` struct every **250 ms** on an extended ID under the bench-test base `0x770000`. A client can **auto-detect** that an ECU speaks TS-over-CAN, and on which IDs. FOME has no equivalent. |
| Dash packs | Separate `can_dash_honda/nissan/haltech/ms` files + `can_dash_haltech.dbc`; FOME keeps one `can_dash.cpp` |
| WBO | Documented two-way wideband on `0x190` |
| Host tooling | `java_console/io/.../can/` ships PCAN and SocketCAN ISO-TP bridges that present TunerStudio a **TCP socket on `localhost:29001`** |

The rusEFI wiki states the design intent plainly: TS over CAN is *"much slower than USB, but should be much more noise tolerant"*, and CAN *"provides a level of reliability above RS232 and USB physical layers"*. rusEFI also sells a **CAN-to-WiFi adapter that translates TunerStudio TCP to ISO-TP over CAN** — which is, minus the display and the LLM bridge, the exact product Aether-over-CAN would be. The precedent is shipping hardware, not a proposal.

---

## 5. MegaSquirt (MS2/MS3 class)

Primary source: *Megasquirt 29bit CAN protocol*, 2014-10-28, James Murray.

Two separate protocols:

- **11-bit broadcast** (separate spec, `Megasquirt_CAN_Broadcast.pdf`): 500 kbit/s, big-endian, sequential IDs from an operator-selected base, default **1520** (0x5F0). The doc *"strongly encourages"* dashes and dataloggers to use this instead of the 29-bit protocol. DBC files are published.
- **29-bit request/response**, used device-to-device and for **passthrough tuning** (a tuning PC connected to one device tunes a remote device over CAN).

29-bit addressing packs everything into the identifier: 11-bit **offset**, 4-bit **message type**, 4-bit **from ID**, 4-bit **to ID**, 5-bit **table**. Master ECU is always CANid 0.

| Type | Value | Function |
|------|------:|----------|
| `MSG_CMD` | 0 | Poke data into `table`+`offset` — **no validation**, if the address is valid the write happens |
| `MSG_REQ` | 1 | Request data; DLC 3; reply size (`varbyt`) is **≤ 8 bytes** |
| `MSG_RSP` | 2 | Reply (same format as `MSG_CMD`) |
| `MSG_BURN` | 4 | **Burn tuning table to flash** (not calibration tables) |
| `MSG_XTND` | 7 | Extended type in first data byte |
| `MSG_FWD` | 8 | Forward data out the serial port (passthrough) |
| `MSG_CRC` | 9 | CRC of a data table — a page-verify primitive |
| `MSG_REQX` | 12 | Request for tables 16-31 |
| `MSG_PROT` | 0x80 | Protocol version + **table/write blocking factors** (MS2 = 256, MS3 = 2048) |
| `MSG_SPND` | 0x82 | Suspend/resume CAN polling (broadcast to CANid 15) |

MS3 holds all tuning pages in RAM concurrently, so arbitrary table/offset writes then `MSG_BURN` is the documented flow — a complete RAM-write → burn → CRC-verify cycle over CAN, mapping cleanly onto `comms.md` §5.2/§5.3. MS2 holds **one page in RAM at a time** and silently loses uncommitted edits to another page — a real hazard for any tool that walks pages.

The cost is throughput: **8 bytes per request/response round trip**, versus 2048 for MS3 over serial. A full MS3 tuning set (~18 KB across the `flash*` tables) is ~2,300 round trips. Bus time is only ~1 s at 500 kbit/s, but it is **latency-bound**, so a naive stop-and-wait client will take tens of seconds. Requests must be pipelined.

---

## 6. Speeduino

Sources: Speeduino wiki `Canbus_Support2`, Secondary Serial IO interface, firmware comms docs.

| Item | State |
|------|-------|
| Hardware | Mega2560 needs a CAN coprocessor board; Teensy 3.5 / STM32F4 have native controllers |
| CAN0 | **OBD-II only** — 11-bit, 500 kbit/s, modes 01 and 22, responds `0x7DF` → `0x7E8` range. No readiness monitors |
| Broadcast | Dash packs (BMW, VAG, Haltech) at 10/15/30/50 Hz depending on protocol and message |
| Wideband in | rusEFI and AEM wideband frames consumed over CAN |
| **Tuning over CAN** | **Not available.** "TunerStudio programming over CAN remains under development"; the CAN1 interface that would carry it is unimplemented |
| Reading other devices' data | "Coming soon" |

The wiki names the reason directly: a CAN frame carries 8 bytes, and Speeduino's realtime block is 30+ bytes, so the serial-shaped protocol needs a segmentation layer that Speeduino has not adopted. Speeduino's answer is a **secondary serial port** (protocols: generic fixed/INI, CAN forwarding, MSdroid, RealDash, TS routing) — i.e. Speeduino solves the "dash + tuner at once" problem with a second UART instead of with CAN.

**Consequence for Aether:** on Speeduino, CAN is a display/log transport only. `comms.md` already scopes Speeduino as a P1 CI/sim dialect, so this costs nothing today — but it forbids "CAN replaces serial" as a product-wide statement.

---

## 7. Aether hardware reality

| Fact | ESP32-S3 (current floor) | ESP32-P4 (higher tier) |
|------|--------------------------|------------------------|
| Controllers | **1** TWAI | **3** TWAI |
| Frame formats | 11-bit and 29-bit | 11-bit and 29-bit |
| **CAN FD** | **Not supported** — FD frames are treated as errors | **Not supported** |
| Transceiver | **Not integrated** — external part required (TJA105x class) | **Not integrated** |
| Filtering | 1 mask filter (single 29-bit or dual 16-bit), plus range filtering | same family |
| Bus-off | Software-initiated recovery; hardware reconnects only after 129 consecutive recessive bits | same |
| Listen-only | Supported (no ACK, no TX) | supported |

Board-level notes:

- The Waveshare ESP32-S3-Touch-AMOLED-1.8 exposes **7 GPIO + 1 I2C + 1 UART + 1 USB pad**. TWAI TX/RX route through the GPIO matrix, so any two free pins work. A transceiver daughterboard is feasible; **no current SKU ships one**.
- The Waveshare ESP32-P4-WIFI6-Touch-LCD-7 already breaks out RS-485/CAN headers — already flagged in [README Hardware](../../README.md#hardware) as the board to watch.
- Only one TWAI controller on S3 means **one bus at a time**. FOME/rusEFI ECUs commonly run two, and TS-over-CAN lives on bus 0 — so an S3 Aether must tap bus 0 and cannot simultaneously watch a vehicle bus.
- **Termination:** most cheap transceiver modules carry a fixed 120 Ω resistor. Tapping mid-bus with a third terminator degrades or kills the bus. The module must have termination removable.
- 12 V automotive supply, load-dump protection, and ground strategy are separate hardware problems that USB-powered bench operation currently hides.

---

## 8. Bandwidth and latency

Classic CAN, 11-bit ID, 8 data bytes ≈ 111 bits nominal, ~135 bits worst case with stuffing, plus IFS. At 500 kbit/s that is **~0.22-0.27 ms per frame**; halve at 1 Mbit/s. FOME supports 100k / 250k / 500k / 1M.

Using FOME's ISO-TP shape (76-byte messages = 1 FF + 1 FC + 10 CF = 12 frames per message):

| Operation | Bytes | ISO-TP msgs | Frames | Bus time @500k | Notes |
|-----------|------:|------------:|-------:|---------------:|-------|
| Verbose broadcast, 8 frames @ 20 Hz | — | — | 160/s | **~4 % load** | No polling, no TX from Aether |
| Partial `O` och poll (~32 B of face channels) | 39 | 1 | ~9 | ~2.3 ms | 20 Hz ≈ 4.5 % load |
| **Full och block** (`ochBlockSize` 1260) | 1267 | 17 | ~204 | **~51 ms** | 10 Hz would be **~51 % load** — not viable |
| Full calibration read (`pageSize` 26552 @ `blockingFactor` 1320) | ~26.7 k | ~363 | ~4,400 | **~1.1 s** | plus ~363 flow-control turnarounds |
| Burn (`B`) | ~10 | 1 | ~3 | negligible | latency is ECU flash time, not CAN |

Three conclusions fall out:

1. **Do not poll the full och block over CAN.** It is the one thing that does not fit. Broadcast already carries the same channels for free.
2. Partial och polling (`O` + offset/count, the "scatter" model already noted in [`docs/research/serial-protocols.md`](https://github.com/tig/aether/blob/spec/serial-live-protocols/docs/research/serial-protocols.md) §4) is the right escape hatch for channels the broadcast omits.
3. **Full calibration read/write is entirely practical** — 1-3 s wall clock including flow-control turnaround, against a workflow where the operator is already waiting for an LLM. CAN's disadvantage versus USB is real but lands on the operation that tolerates it.

---

## 9. Proposed architecture (input to `comms.md` Appendix B)

Non-normative. Offered as the shape a CAN rev of the contract should take.

```text
                       ┌──────────── ECU (FOME/rusEFI) ────────────┐
                       │  broadcast 0x200+     TS ch. 0x100/0x102  │
                       └──────┬──────────────────────┬─────────────┘
                              │ (A) listen-only      │ (C) ISO-TP session
                              ▼                      ▼
   face + logger  ◄──── can_broadcast decoder    can_isotp serial_link
                              │                      │
                              └──────► live bus ◄────┴─ ts_frame → session → dialect
```

| Layer | Change |
|-------|--------|
| `serial_link` | Add a `can_isotp` transport. ISO-TP is a byte stream — this is the FOME `CanTsChannel : TsChannelBase` pattern, mirrored |
| `ts_frame` / session / dialect | **No change.** Same envelope, same CRC scope, same `S`/`V`/`O`/`R`/`k`/`C`/`B` |
| Live bus | Add a broadcast decoder publishing the same sample shape and `present` bitset; generate it from `FOME_CAN_verbose.dbc` rather than hand-transcribing |
| Session master rule | Unchanged in spirit, but **per-service**: broadcast consumption never requires master; only ISO-TP does. `BRIDGED` quality stops being necessary in the CAN topology |
| Quality | Add `LISTEN_ONLY` (no TX permitted) and a bus-off / error-passive state distinct from `NO_LINK` |

Default policy proposal:

1. Boot **listen-only**. Face and logger run from broadcast. Aether transmits nothing.
2. Leave listen-only only when a calibration read or write is requested, and return to it when the session ends.
3. Keep the ISO-TP session single-instance; refuse to open a second one.
4. Keep USB/UART as a peer transport, not a legacy one — Speeduino and any ECU without `EFI_CAN_SERIAL` need it.

---

## 10. Risks

| Risk | Note |
|------|------|
| **Writes on a live vehicle bus** | TS-over-CAN is unauthenticated. Anything on the bus can RAM-write and burn. Aether's human-gated burn rule ([#4](https://github.com/tig/aether/issues/4)) is the only gate that exists — it must not be relaxed because "CAN is just a transport" |
| **ID collisions** | `0x100`/`0x102` are low IDs, i.e. **high priority**, and are not configurable. On a swapped car with OEM traffic, collisions are an availability problem for the *engine* bus, not just for Aether |
| Broadcast base overlap | `0x200`-`0x209` at default base can collide with OEM dash traffic; operator-configurable on the ECU side only |
| Bus-off | An Aether fault that drives TEC ≥ 256 removes Aether from the bus and can disturb others first. Bus-off recovery and a hard TX kill-switch are requirements, not polish |
| Termination | A third 120 Ω terminator degrades the bus (§7) |
| Single controller on S3 | Cannot watch a second bus; forces the tap onto ECU bus 0 |
| ECU config drift | `canReadEnabled` / `canWriteEnabled` / baud must match; a silent mismatch looks identical to a dead ECU. Identity probe must distinguish them |
| Partial ISO-TP | Neither tree honors peer `BS`/`STmin`. Aether must send `BS=0, STmin=0` flow control and must not rely on throttling the ECU |

---

## 11. Open questions

1. Which SKU carries the transceiver — daughterboard on the S3 bootstrap board, or move to a P4 board with CAN broken out?
2. Does the operator's pilot ECU have CAN wired to an accessible connector at all, and on bus 0?
3. Auto-detect strategy: rusEFI's `0x770000`-class ISO-TP announcement does not exist on FOME. Probe by sending a framed `S` to `0x100` and waiting on `0x102`?
4. Does the pilot FOME build have `enableVerboseCanTx` on, and at what `canSleepPeriodMs`?
5. Generate the broadcast decoder from `FOME_CAN_verbose.dbc` at build time, or transcribe once and golden-test it?
6. λ source priority when broadcast λ1, och λ1, and a CAN wideband on `0x190` are all present.
7. Is a CAN-only SKU (no USB host) worth shipping, or is CAN always additive?

---

## 12. Sources

| Source | Use |
|--------|-----|
| `FOME-Tech/fome-fw` `master` — `controllers/can/*`, `console/binary/serial_can.*`, `ts_can_channel.cpp`, `integration/fome_config.txt`, `controllers/algo/engine_configuration.cpp` | FOME wire facts, IDs, defaults, frame layouts |
| `rusefi/rusefi` `master` — `controllers/can/isotp/*`, `console/binary/serial_can.cpp`, `ts_can_channel.cpp`, `can_bench_test.cpp` | rusEFI ISO-TP generalization, announcement mechanism |
| [rusEFI CAN documentation](https://github.com/rusefi/rusefi_documentation/blob/master/CAN.md), [TS over CAN wiki](https://github.com/rusefi/rusefi/wiki/TS-over-CAN), [calibration via CAN wiki](https://github.com/rusefi/rusefi/wiki/rusEFI-calibration-via-CAN) | ID map, host bridge design, "slower than USB but noise tolerant" |
| [Megasquirt 29bit CAN protocol, 2014-10-28](https://www.megasquirt.co.uk/doc/pdf/Megasquirt_29bit_CAN_Protocol-2014-10-28.pdf) (also [2015-01-20](https://www.msextra.com/doc/pdf/Megasquirt_29bit_CAN_Protocol-2015-01-20.pdf)) | MS message types, addressing, blocking factors |
| [Megasquirt CAN broadcast spec](https://www.msextra.com/doc/pdf/Megasquirt_CAN_Broadcast.pdf) | 11-bit dash/logger broadcast, base 1520 |
| [Speeduino CANbus support](https://wiki.speeduino.com/en/Canbus_Support2), [secondary serial](https://wiki.speeduino.com/en/Secondary_Serial_IO_interface), [comms overview](https://deepwiki.com/speeduino/speeduino/4-communications) | Speeduino OBD-II-only CAN, tuning-over-CAN status |
| [ESP-IDF TWAI — ESP32-S3](https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-reference/peripherals/twai.html), [ESP32-P4](https://docs.espressif.com/projects/esp-idf/en/stable/esp32p4/api-reference/peripherals/twai.html) | Controller count, no FD, transceiver requirement, bus-off |
| [Waveshare ESP32-S3-Touch-AMOLED-1.8 wiki](https://www.waveshare.com/wiki/ESP32-S3-Touch-AMOLED-1.8) | Exposed GPIO/I2C/UART pads |
| [specs/comms.md](https://github.com/tig/aether/blob/spec/serial-live-protocols/specs/comms.md), [docs/research/serial-protocols.md](https://github.com/tig/aether/blob/spec/serial-live-protocols/docs/research/serial-protocols.md) | Existing contract and survey this note extends |
