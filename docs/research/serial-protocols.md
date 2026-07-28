# Research notes — serial-class ECU realtime protocols

**Date:** 2026-07-28 (OSS leverage map §12 added same day)  
**Purpose:** Non-normative survey backing [specs/inputs.md](../../specs/inputs.md) / issue [#5](https://github.com/tig/aether/issues/5).  
**Not product contract** — prefer the spec for decisions (including §15 Implementation leverage).

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

Good **CI / secondary** target because of fixed layouts + simulators on ESP32. **Operator P0 is FOME over USB** on the current Aether prototype (see `specs/inputs.md` rev 0.2).

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

1. **Family:** TunerStudio-compatible MS / rusEFI / FOME serial (CRC + legacy).  
2. **P0 dialect:** **FOME** over **USB** on the **current Aether prototype**.  
3. **P1:** Speeduino fixed och (CI/sim) + broader rusEFI packs + field UART.  
4. **Transports:** USB P0 (FOME cable) → UART → BT → Wi-Fi.  
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

---

## 12. OSS leverage map (host + metal)

Survey of **existing open-source** that Aether can use for P0 USB+FOME live channels, CI goldens, and later transports.  
**Policy:** metal static-link prefers **MIT / Apache-2.0 / BSD / Zlib**. **GPL** ECU firmware and tuning apps are **reference-only** for protocol behavior — **do not copy or link** into Aether firmware. Host tools may be separate processes even if GPL.

**Captured:** 2026-07-28. Licenses are SPDX as reported by project metadata / LICENSE files at time of survey; re-check before shipping.

### 12.1 Legend

| Field | Meaning |
|-------|---------|
| **Role** | `metal` = on-device ESP32-S3 firmware; `host` = PC CI/tools; `both` |
| **Leverage** | `adopt` = link/use; `pattern` = learn API shape; `ref` = protocol docs only; `out` = not useful for P0 |
| **Maturity** | rough: production / maintained / early / abandoned |

### 12.2 Metal — USB / UART / framing (P0 stack candidates)

| Name | URL | SPDX | Lang | Role | Maturity | Size / deps | Integration notes | Gaps |
|------|-----|------|------|------|----------|-------------|-------------------|------|
| **ESP-IDF** (USB Host Library, UART, device stack) | https://github.com/espressif/esp-idf | **Apache-2.0** | C | metal | production | Full IDF | Baseline: already Aether plate. Host lib + device USB + UART drivers. | S3 single PHY: OTG host vs USB-Serial-JTAG mux |
| **usb_host_cdc_acm** | https://components.espressif.com/components/espressif/usb_host_cdc_acm · src in [espressif/esp-usb](https://github.com/espressif/esp-usb) | **Apache-2.0** | C | metal | production (~370k downloads) | ~85 KB archive; deps: USB Host Library | **P0 path:** `cdc_acm_host_install` / `open` / TX blocking / RX callback. Examples: `peripherals/usb/host/cdc/cdc_acm_host` | Native CDC only; FOME STM VCP should match; composite MSC+CDC need interface pick policy |
| **usb_host_vcp** (+ chip drivers) | https://components.espressif.com/components/espressif/usb_host_vcp · esp-usb `host/class/cdc/` | **Apache-2.0** | C | metal | maintained | small service + per-chip drivers (CP210x, FTDI, CH34x) | Example `cdc_acm_vcp`: register VCP drivers then open generically — needed if FOME path is **USB–UART dongle** not native CDC | Not every clone chip; VID/PID quirks table still product work |
| **TinyUSB** | https://github.com/hathach/tinyusb | **MIT** | C | metal | production | mid-size stack | Via **esp_tinyusb** component for **USB device CDC** (Aether as COM to PC for sim/host bridge #1) | Host CDC on TinyUSB is secondary to Espressif host class drivers for S3 product path |
| **esp_tinyusb** | https://components.espressif.com/components/espressif/esp_tinyusb | Apache-2.0 (Espressif wrapper; upstream TinyUSB MIT) | C | metal | production | wraps TinyUSB | `tusb_cdc_acm_init` for device-mode COM; console redirect helpers | Device role only in typical Aether use |
| **ESP-IDF `esp_crc` / zlib CRC32** | IDF `esp_rom_crc32` / [zlib](https://github.com/madler/zlib) `crc32` | Apache-2.0 (IDF) / **Zlib** | C | metal | production | tiny | MS **newserial** uses CRC32 over size+payload (BE). Prefer IDF ROM CRC or a **tiny public-domain table** (MS protocol doc references public-domain style CRC32) | Must match MS big-endian CRC placement exactly; unit-test against goldens |
| **ESP-IDF UART driver** | IDF `driver/uart` | Apache-2.0 | C | metal | production | built-in | Same `serial_link` under UART as under CDC for field harness (P0–P1) | Level shift / baud profile not in OSS |

### 12.3 Metal / protocol source — **GPL reference-only** (do not port code)

| Name | URL | SPDX | Lang | Role | Maturity | Size / deps | Integration notes | Gaps |
|------|-----|------|------|------|----------|-------------|-------------------|------|
| **rusEFI** (`tunerstudio.cpp`, TsChannel) | https://github.com/rusefi/rusefi | **GPL-3.0** + project vehicle-use terms | C/C++ | **ref** | production | huge monorepo | **Learn:** query + och get, CRC flags, dual USB/UART, scatter, BT limits. **Do not copy** framing or command handlers into Aether. | No permissive extract of TS client; protocol also in MS 2014 PDF |
| **FOME-Tech/fome-fw** | https://github.com/FOME-Tech/fome-fw | **GPL-3.0** (rusEFI lineage LICENSE) | C | **ref** | production | huge | **P0 ECU peer:** signatures, INI packs, USB CDC behavior. Treat as **documentation + live HIL target**, not a library. | Same GPL trap as rusEFI; layout still needs FOME INI → compact pack |
| **Speeduino firmware** | https://github.com/speeduino/speeduino | **GPL-2.0** | C++ | **ref** | production | large Arduino-class | Fixed och layout / `A`/`r` semantics for **secondary** dialect; do not link | Not operator P0 metal |
| **LibreTune** (RallyPat) | https://github.com/RallyPat/LibreTune | **GPL-2.0** | Rust + TS | host **ref** | early / active | large Tauri app | Modern TS-compatible client with **claimed FOME/rusEFI/Speeduino** serial + INI. Excellent **behavioral reference** and optional **separate-process** bench tool. **Cannot** static-link `libretune-core` into Aether metal. | Early project; GPL-2 whole app; not a small framing crate |
| **LibreTuner** (archived Mazda) | https://github.com/LibreTuner/LibreTuner | **GPL-3.0** | C++ | out | abandoned | medium | OBD/J2534 Mazda — **not** TS serial | Wrong problem |
| **MegaTunix** | https://github.com/djandruczyk/MegaTunix | **GPL-2.0** | C | host **ref** | abandoned | large GTK app | Historical MS serial/INI client; outdated for modern MS/rusEFI | Stale defs; GPL |
| **arduino-megasquirt** | https://github.com/irvined1982/arduino-megasquirt | *no SPDX* (2014, unlicensed) | C++ | out | abandoned | tiny | Pre-modern MS serial; license unclear | Avoid |

**Rule of thumb:** Wire protocol for P0 is defined by **MegaSquirt Serial Protocol PDF (newserial)** + **FOME/rusEFI command set observed on the wire**. Implement **original** Aether framing/CRC/och poll in portable C under `include/` + `src/`. Use GPL sources only as **oracle** when goldens disagree.

### 12.4 Host — simulators, clients, serial I/O (CI / goldens)

| Name | URL | SPDX | Lang | Role | Maturity | Size / deps | Integration notes | Gaps |
|------|-----|------|------|------|----------|-------------|-------------------|------|
| **speeduino-serial-sim** | https://github.com/askrejans/speeduino-serial-sim | **MIT** | C++ (Arduino/ESP) | host + lab metal | maintained | small | Full Speeduino protocol (legacy + CRC v2), engine model, UART + **Wi-Fi TCP :5000**. **Best CI ECU peer** for Speeduino dialect and TS-shaped poll loops. | Speeduino layout ≠ FOME och; not FOME HIL |
| **speeduino-to-mqtt** | https://github.com/askrejans/speeduino-to-mqtt | **MIT** | Rust | host | maintained | mid | Real Speeduino **client**: serial + TCP, `A` parse, TUI. Study och layout extraction; optional external process. | Speeduino-only; not FOME/rusEFI CRC och |
| **pyserial** | https://github.com/pyserial/pyserial | **BSD-3-Clause** | Python | host | production | small | Capture/replay COM ports; golden frame acquisition from real FOME over USB-CDC | No TS framing built-in — Aether host tests own codec |
| **serialport** (serialport-rs) | https://github.com/serialport/serialport-rs | **MPL-2.0** | Rust | host | production | mid | Cross-platform serial for host harnesses written in Rust | MPL file-level copyleft; fine for separate host tools |
| **libusb** | https://github.com/libusb/libusb | **LGPL-2.1** | C | host | production | mid | Raw USB capture if OS VCP is opaque; rare for P0 | Prefer OS CDC + pyserial first; LGPL dynamic link if needed |
| **rusEFI virtual simulator** | wiki Virtual-simulator; TCP **29002** | GPL (with rusEFI) | Java/C | host **ref**/sim | production | large | TS over TCP for family testing; **separate process** OK | GPL; not MIT sim |
| **AlphaLima / yuri-rage ESP32-Serial-Bridge** | https://github.com/AlphaLima/ESP32-Serial-Bridge · https://github.com/yuri-rage/ESP-Serial-Bridge | **MIT** | Arduino C++ | host/lab | mature forks | small | Pattern for **P3 Wi-Fi TCP serial** bridges | Not in Aether image by default; external accessory |
| **esphome-uart-link** | https://github.com/nebulous/esphome-uart-link | **MIT** | YAML/C++ | host/lab | maintained | ESPHome component | UART↔TCP for shop benches | ESPHome ecosystem dependency |
| **MS Serial Protocol (2014)** | http://www.msextra.com/doc/pdf/Megasquirt_Serial_Protocol-2014-10-28.pdf | doc (not code) | — | both **spec** | authoritative | 26 pp | Size BE + payload + CRC32 BE; flags; `A`/`Q`/`r` | Not a library — Aether implements |

### 12.5 Bluetooth / Wi-Fi (P2 / P3) — ESP32-S3 constraints

| Topic | Finding | Implication for Aether |
|-------|---------|------------------------|
| **ESP32-S3 BT** | Hardware is **BLE only**. ESP-IDF Bluedroid **and** NimBLE on S3: **no Classic Bluetooth**. | **Classic SPP (HC-05 / JDY-33 class)** cannot be implemented in S3 radio. P2 SPP needs **external UART BT module** (Aether UART → module SPP) or a different SoC. |
| **NimBLE** | Apache-2.0 (Mynewt); lightweight BLE host | Use for BLE UART / NUS-like phone path later — **not** drop-in for existing ECU BT modules |
| **Bluedroid** | Espressif stack; Classic+BLE on original ESP32 only | Irrelevant for S3 Classic SPP |
| **Wi-Fi TCP serial** | Many MIT bridges (ESP32-Serial-Bridge, etc.); sims use fixed ports (Speeduino sim **:5000**, rusEFI sim **:29002**) | P3: Aether as TCP **client** to bridge/sim; reuse same TS framing over sockets |

### 12.6 CRC32 options (metal)

| Option | SPDX | Notes |
|--------|------|--------|
| ESP-IDF / ROM CRC32 | Apache-2.0 | Prefer on metal; verify vs MS vector |
| zlib `crc32` | Zlib | Host tests; optional small copy if needed |
| MS protocol “public domain” table | public domain (as described in MS doc) | Match bit order / init with goldens — do not assume zip CRC without tests |

### 12.7 Recommended stacks (research recommendation)

#### Metal P0 (USB + FOME on current Aether prototype)

```text
ESP-IDF UART / USB Host Library (Apache-2.0)
  └─ usb_host_cdc_acm  (+ usb_host_vcp if adapter)  [Apache-2.0]
  └─ (optional device) esp_tinyusb CDC  [MIT/Apache]
  └─ Aether-original TS newserial framing + CRC32  [our code]
  └─ FOME signature → layout pack (compiled tables)  [data from FOME INI, not GPL C]
  └─ canonical live channel bus → face + logger
```

- **Do not** vendor rusEFI/FOME `tunerstudio.cpp`.
- **Do** capture real FOME USB frames with pyserial for CI replay.

#### Host goldens / sim P0–P1

```text
pyserial (BSD-3) or serialport-rs (MPL-2.0)
  └─ Aether host unit tests: framing encode/decode + och extract
  └─ golden .bin from real FOME (P0) + Speeduino (P1)
speeduino-serial-sim (MIT)  — live peer for Speeduino dialect / TCP :5000
(optional) LibreTune or TunerStudio  — separate process smoke vs same ECU
(optional) rusEFI/FOME sim / real ECU HIL  — acceptance, not CI dependency
```

### 12.8 Biggest gaps (OSS)

1. **No permissive, production C library** for TS newserial + FOME/rusEFI och as a drop-in client. Must **write** framing + poll in Aether.
2. **No MIT FOME protocol simulator** comparable to speeduino-serial-sim — FOME goldens require **real ECU** or reverse-engineered host mock.
3. **ESP32-S3 cannot do Classic SPP** — P2 wireless story is external module or BLE redesign.
4. **Prototype USB topology still open** (host OTG vs device-only vs mux) — OSS stack exists for both roles, but board wiring chooses default.
5. **INI → compact layout** tooling: LibreTune has GPL INI parser (reference); Aether needs **own** pack generator (host Python OK under product license).

### 12.9 License traps (checklist)

| Trap | Action |
|------|--------|
| rusEFI / FOME **GPL-3** firmware | Reference-only; reimplement; no copy-paste of framing |
| Speeduino **GPL-2** | Same for metal; sim (MIT) is fine for CI peer |
| LibreTune **GPL-2** | Separate process / learn algorithms; no metal link |
| libusb **LGPL-2.1** | Prefer OS serial; if used, dynamic link on host |
| serialport-rs **MPL-2.0** | OK for host tools; not for ESP firmware |
| TinyUSB **MIT** + esp-usb **Apache-2.0** | Safe for metal |

---

## 13. Link index (OSS-focused)

| Area | Links |
|------|-------|
| USB host CDC | https://components.espressif.com/components/espressif/usb_host_cdc_acm |
| USB host VCP | https://components.espressif.com/components/espressif/usb_host_vcp |
| esp-usb monorepo | https://github.com/espressif/esp-usb |
| TinyUSB | https://github.com/hathach/tinyusb |
| MS newserial PDF | http://www.msextra.com/doc/pdf/Megasquirt_Serial_Protocol-2014-10-28.pdf |
| rusEFI TS source (ref) | https://github.com/rusefi/rusefi/blob/master/firmware/console/binary/tunerstudio.cpp |
| FOME fw (ref) | https://github.com/FOME-Tech/fome-fw |
| Speeduino sim (MIT) | https://github.com/askrejans/speeduino-serial-sim |
| Speeduino client (MIT) | https://github.com/askrejans/speeduino-to-mqtt |
| LibreTune (GPL host ref) | https://github.com/RallyPat/LibreTune |
| pyserial | https://github.com/pyserial/pyserial |
| serialport-rs | https://github.com/serialport/serialport-rs |
