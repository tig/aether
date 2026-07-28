# Research notes — serial-class ECU realtime protocols

**Date:** 2026-07-28  
**Purpose:** Non-normative survey backing [specs/inputs.md](../../specs/inputs.md) / issue [#5](https://github.com/tig/aether/issues/5).  
**Not product contract** — prefer the spec for decisions.

---

## 1. Naming: FOAM vs FOME

Issue #5 says **FOAM**. Public project is **FOME** — Free Open Motorsports ECU ([fome.tech](https://www.fome.tech/), [FOME-Tech/fome-fw](https://github.com/FOME-Tech/fome-fw)). Wiki and USB/TS workflows match a rusEFI-lineage open ECU. Spec treats FOAM as **FOME**.

---

## 2. MegaSquirt / TunerStudio “newserial”

**Primary doc:** *Megasquirt serial protocol*, 2014-10-28 (msextra.com PDF).

Key facts:

- **Poll only** on serial — no unsolicited realtime stream.
- Half-duplex: do not write while ECU is transmitting.
- **Wrapper:** big-endian size + payload + big-endian CRC32 (public-domain crc32).
- Response adds **flag** (0x00 OK, 0x01 realtime, 0x80 underrun, 0x82 CRC failure, 0x85 busy, …).
- Realtime: **`A`** → full outpc; selective **`g`** on some MS3; **`r`** for table/offset reads.
- Identity: **`Q`** format string, **`S`** version/copyright string.
- **Compatibility mode:** naked single-byte `A`/`Q`/`S` without CRC for older dashes.
- Doc encourages **CAN broadcast** for dash-only devices — out of scope for #5 but relevant later.

INI files remain the authority for och field layout and `ochBlockSize`.

---

## 3. Speeduino

Sources: Speeduino secondary serial wiki; community `comms` notes; [speeduino-serial-sim](https://github.com/askrejans/speeduino-serial-sim) (full protocol sim).

| Item | Notes |
|------|--------|
| Baud | Commonly **115200 8N1** |
| Legacy | Single-byte `A` → full status blob |
| Framed v2 | Size + payload + CRC32; `r` with offset/length for och |
| Handshake (TS-like) | `F`→`002`, `Q`/`S` signatures, then continuous `r` ~20 Hz |
| Layout | Firmware-year packed struct (sim documents **130 bytes** for 202501-class) |
| Secondary serial | Dash/logger can use second port while TS uses primary |
| Wi-Fi | Sims/tools use TCP serial (example port **5000** on one sim) |

Good **P0 pilot** because of fixed layouts + simulators on ESP32.

---

## 4. rusEFI

Sources: wiki TunerStudio Connectivity, Bluetooth; `firmware/console/binary/tunerstudio.cpp` comments and command set.

| Item | Notes |
|------|--------|
| Protocol | TS binary; gauges need **query + och get** (`O`/output channels) |
| USB | **STM Virtual COM** micro-USB; primary TS path; power via USB common on bench |
| TTL UART | Parallel path (e.g. PC10/PC11 notes historically); 38400 often used for TTL tests; can run **USB + UART clients together** |
| Test | Plain `t`/`T` alive text; not TS och |
| BT | JDY-33 / HC-05/06 style **SPP** on binary UART; documented **slow/limited**; init via console `bluetooth_*` commands |
| Wi-Fi | Prefer external UART–TCP or CAN–WiFi; simulator uses TCP (e.g. port **29002** in virtual sim docs) |
| INI | Auto-detect download path over USB/serial/BT for official boards |
| Scatter | Optional high-speed sparse och reads — useful model for face-minimal channel sets |
| Errors | underrun / overrun / CRC counters; ~1 s idle may drop BT software link |

---

## 5. FOME

Sources: fome.tech, wiki.fome.tech (USB + TunerStudio setup, Miata quick start).

- Day-one path: **USB cable**, select COM port in TunerStudio, load matching **INI** (sometimes from mass-storage image when ECU is plugged in).
- Live path: **TS-compatible** with FOME signatures — not a separate framing invention.
- Treat as **rusEFI-family decoder + definition pack**.

---

## 6. USB on ESP32-S3 (Aether hardware class)

Sources: ESP-IDF USB device docs; USB host CDC-ACM examples; community OTG notes.

| Fact | Implication |
|------|-------------|
| USB-OTG + USB-Serial-JTAG share **one PHY** on many S3 modules | Device console and host-to-ECU may be **mutually exclusive** without external PHY/mux |
| **Device CDC** | Aether appears as COM to PC — host bridge (#1), PC simulators, capture |
| **Host CDC-ACM** | Aether enumerates ECU native CDC or needs **VCP quirks** (CH340, CP210x, FTDI) |
| Hot-plug | Host stack must handle disconnect semaphores / re-open; face must go invalid |
| Baud on CDC | Often ignored by device; still set line coding for USB–UART bridges |

**Do not** document USB as “UART at 115200” without role language.

---

## 7. Bluetooth / Wi-Fi summary

| Transport | Typical ECU use | Aether stance |
|-----------|-----------------|---------------|
| BT Classic SPP | HC-05 / JDY modules, phone TS apps | P2; rate-cap polls |
| BLE UART | Phones / modern modules | Later if needed |
| Wi-Fi TCP serial | Sims, UART–TCP proxies, shop | P3; great for CI sim |
| Wi-Fi UDP | Rare proprietary | Not assumed |

---

## 8. Wideband serial (secondary)

| Brand | Pattern | Relevance |
|-------|---------|-----------|
| Innovate LC-1/2 | Push packets ~12 Hz class | λ only; merge as sensor source |
| AEM UEGO / X-series | RS-232 serial out (often 9600) | λ only; optional dual-channel |

Not sufficient alone for AFR face (needs RPM + load per product mission).

---

## 9. Display vs log rates (practice)

| Consumer | Practical rate | Mechanism |
|----------|----------------|-----------|
| Pocket face | 10–20 Hz | Subsample + optional smooth |
| Logger | 20–50+ Hz | Full och or max stable poll |
| TS gauges | ~15–50 Hz depending on och size and link | Poll loop |

USB and wired UART usually win headroom; BT needs lower caps.

---

## 10. Decision snapshot (see inputs.md for normative text)

1. **Family:** TunerStudio-compatible MS serial (CRC + legacy).  
2. **P0 dialect:** Speeduino fixed layout.  
3. **P1:** rusEFI + FOME layouts.  
4. **Transports:** USB P0 (device and/or host) → UART → BT → Wi-Fi.  
5. **Internal model:** λ-centric channels + quality + int64 ms timestamps.  
6. **CAN:** deferred to reserved section in inputs.md.

---

## 11. Useful links

- https://wiki.rusefi.com/Tunerstudio-Connectivity/
- https://wiki.rusefi.com/Bluetooth/
- https://github.com/rusefi/rusefi/blob/master/firmware/console/binary/tunerstudio.cpp
- http://www.msextra.com/doc/pdf/Megasquirt_Serial_Protocol-2014-10-28.pdf
- https://wiki.speeduino.com/en/Secondary_Serial_IO_interface
- https://github.com/askrejans/speeduino-serial-sim
- https://www.fome.tech/ / https://wiki.fome.tech
- https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-reference/peripherals/usb_device.html
- ESP-IDF examples: `peripherals/usb/host/cdc/cdc_acm_host`, `cdc_acm_vcp`
