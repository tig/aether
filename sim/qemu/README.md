# QEMU twin — real Aether firmware image

The **default software Aether** is `sim/aether` (always on CI, no IDF). This
directory is the **higher-fidelity twin**: real `firmware/` under Espressif QEMU.

## CI gate (this PR)

Job **`qemu-identity`** in `.github/workflows/ci.yml`:

1. Build `firmware/` for `esp32s3` with ESP-IDF.
2. Merge a full flash image.
3. Run under [tobozo/esp32-qemu-sim](https://github.com/tobozo/esp32-qemu-sim).
4. Assert serial log contains `fw_name=AETHER` via `run_identity_check.py`.

Boot-print identity is enough for this gate (metal also answers an `identity`
knock; interactive UART knock over the action’s log capture is follow-up).

## Local (when IDF + QEMU installed)

```bash
cd firmware
idf.py set-target esp32s3
idf.py build
# merge flash (size must match sdkconfig flash size; default often 4MB/8MB)
esptool.py --chip esp32s3 merge_bin --fill-flash-size 8MB -o ../build/qemu_flash.bin @build/flash_args

# idf tools path, or:
idf.py qemu monitor
# stop when you see fw_name=AETHER … then:
python ../sim/qemu/run_identity_check.py /path/to/capture.txt
```

## esprec on QEMU

Until metal links esprec and a software/virtual FB backend:

- Use **V-AETHER** `esprec shot` (host sim) for capture CI.
- When firmware emits ESPREC1 on UART under QEMU, point `esprec snapshot`
  at the UART TCP port (`socket://` / serial bridge) the same way.

## V-ECU from QEMU firmware

Firmware ECU client (portable `gcu_ecu_client` + UART transport) can target
host V-ECU once QEMU has a path to the host (OpenETH or a host-side bridge).
Until then, the **C client is proven on host TCP** (`ecu_tcp_bench` + pytest).
