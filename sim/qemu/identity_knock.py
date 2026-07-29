#!/usr/bin/env python3
"""Boot real firmware under Espressif QEMU and exercise the identity knock.

AGENTS.md: boot-print alone is not enough for silico inspect after the banner
scrolls past. This gate:

1. Starts ``qemu-system-xtensa -machine <chip>`` with UART on TCP.
2. Waits for the boot ``fw_name=AETHER`` line (optional but expected).
3. Sends CR/LF-framed ``identity`` and requires the exact response line.
4. Exits non-zero on any failure; kills QEMU on the way out.

Usage (from an IDF environment with qemu-xtensa on PATH)::

    python sim/qemu/identity_knock.py \\
        --flash firmware/build/qemu_flash.bin \\
        --machine esp32s3
"""

from __future__ import annotations

import argparse
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

EXPECTED = "fw_name=AETHER fw_version=0.0.1"
BOOT_NEEDLE = "fw_name=AETHER"


def find_qemu() -> str:
    for name in ("qemu-system-xtensa", "qemu-system-xtensa.exe"):
        path = shutil.which(name)
        if path:
            return path
    raise FileNotFoundError(
        "qemu-system-xtensa not on PATH (install via idf_tools.py install qemu-xtensa)"
    )


def wait_port(host: str, port: int, timeout_s: float) -> None:
    deadline = time.monotonic() + timeout_s
    last_err: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1.0):
                return
        except OSError as exc:
            last_err = exc
            time.sleep(0.1)
    raise TimeoutError(f"QEMU serial port {host}:{port} not open: {last_err}")


def read_line(sock: socket.socket, timeout_s: float) -> str:
    sock.settimeout(timeout_s)
    buf = bytearray()
    while True:
        try:
            chunk = sock.recv(1)
        except socket.timeout as exc:
            raise TimeoutError("UART readline timeout") from exc
        if not chunk:
            raise ConnectionError("UART closed")
        if chunk in (b"\n", b"\r"):
            if buf:
                return buf.decode("utf-8", errors="replace")
            continue
        buf.extend(chunk)
        if len(buf) > 4096:
            raise RuntimeError("UART line too long")


def drain_until(
    sock: socket.socket, needle: str, timeout_s: float, log: list[str]
) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        remaining = max(0.05, deadline - time.monotonic())
        try:
            line = read_line(sock, remaining)
        except TimeoutError:
            break
        log.append(line)
        if needle in line:
            return True
    return False


def knock(sock: socket.socket, timeout_s: float) -> str:
    sock.sendall(b"identity\r\n")
    # Some firmwares also accept LF-only; metal accepts either framing char.
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        remaining = max(0.05, deadline - time.monotonic())
        line = read_line(sock, remaining)
        # Ignore empty / noise; accept exact identity line.
        if line.strip() == EXPECTED:
            return line.strip()
        if line.strip().startswith("fw_name="):
            return line.strip()
    raise TimeoutError("no identity response after knock")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--flash", required=True, type=Path, help="Merged flash image")
    p.add_argument("--machine", default="esp32s3", help="QEMU -machine value")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=5555)
    p.add_argument("--boot-timeout", type=float, default=30.0)
    p.add_argument("--knock-timeout", type=float, default=10.0)
    p.add_argument(
        "--qemu-bin",
        default=None,
        help="Path to qemu-system-xtensa (default: PATH)",
    )
    args = p.parse_args(argv)

    flash = args.flash.resolve()
    if not flash.is_file():
        print(f"FAIL: flash image missing: {flash}", file=sys.stderr)
        return 1

    qemu = args.qemu_bin or find_qemu()
    serial = f"tcp:{args.host}:{args.port},server=on,wait=off"
    cmd = [
        qemu,
        "-nographic",
        "-machine",
        args.machine,
        "-drive",
        f"file={flash},if=mtd,format=raw",
        "-serial",
        serial,
    ]
    print("starting:", " ".join(cmd), flush=True)
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=os.environ.copy(),
    )
    log: list[str] = []
    try:
        wait_port(args.host, args.port, timeout_s=15.0)
        sock = socket.create_connection((args.host, args.port), timeout=5.0)
        try:
            saw_boot = drain_until(sock, BOOT_NEEDLE, args.boot_timeout, log)
            if not saw_boot:
                print(
                    "WARN: boot identity not seen before knock; "
                    "still exercising knock (AGENTS.md)",
                    flush=True,
                )
            else:
                print(f"boot: {[ln for ln in log if BOOT_NEEDLE in ln][-1]!r}", flush=True)

            # Extra drain window so the banner is "past" before we knock.
            time.sleep(0.3)
            reply = knock(sock, args.knock_timeout)
            print(f"knock reply: {reply!r}", flush=True)
            if reply != EXPECTED:
                print(
                    f"FAIL: identity knock mismatch want={EXPECTED!r} got={reply!r}",
                    file=sys.stderr,
                )
                return 1
            print("OK: identity knock exact match", flush=True)
            return 0
        finally:
            sock.close()
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: {exc}", file=sys.stderr)
        if log:
            print("--- uart lines ---", file=sys.stderr)
            for ln in log[-40:]:
                print(ln, file=sys.stderr)
        # dump qemu stdout if any
        try:
            if proc.stdout:
                out = proc.stdout.read()
                if out:
                    print("--- qemu stdout ---", file=sys.stderr)
                    print(out[-2000:], file=sys.stderr)
        except Exception:
            pass
        return 1
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
