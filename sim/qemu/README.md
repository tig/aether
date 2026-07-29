# QEMU twin — real Aether firmware image

The **default software Aether** is `sim/aether` (always on CI, no IDF). This
directory is the **higher-fidelity twin**: real `firmware/` under Espressif QEMU.

## CI gate (this PR)

Job **`qemu-identity`** in `.github/workflows/ci.yml`:

1. Build `firmware/` for `esp32s3` with ESP-IDF.
2. Merge a full flash image.
3. Install Espressif `qemu-xtensa`.
4. Run `identity_knock.py`:
   - start QEMU with UART on TCP
   - observe boot `fw_name=AETHER` when present
   - **send CR/LF-framed `identity`** and require exact
     `fw_name=AETHER fw_version=0.0.1` (AGENTS.md / silico inspect)

Boot-print alone is **not** sufficient for a green gate.

## Local (when IDF + QEMU installed)

```bash
cd firmware
idf.py set-target esp32s3
idf.py build
esptool.py --chip esp32s3 merge_bin --fill-flash-size 4MB \
  -o build/qemu_flash.bin @build/flash_args

python $IDF_PATH/tools/idf_tools.py install qemu-xtensa
. $IDF_PATH/export.sh

python ../sim/qemu/identity_knock.py \
  --flash build/qemu_flash.bin --machine esp32s3
```

## esprec on QEMU

Until metal links esprec and a software/virtual FB backend:

- Use **V-AETHER** `esprec shot` (host sim) for capture CI.
- When firmware emits ESPREC1 on UART under QEMU, point `esprec snapshot`
  at the UART TCP port the same way (`identity_knock` already proves UART TCP).

## V-ECU from QEMU firmware

Firmware ECU client (portable `gcu_ecu_client` + UART transport) can target
host V-ECU once QEMU has a path to the host (OpenETH or a host-side bridge).
Until then, the **C client is proven on host TCP** (`ecu_tcp_bench` + pytest).
