#!/usr/bin/env python3
"""
FOME HIL CLI — identity, realtime, logging soak, flash backup / write-back / burn.

Pure framing: ts_frame.py (unit-tested against goldens/).
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
import time
import zlib
from datetime import datetime, timezone
from pathlib import Path

import serial

from fome_client import (
    BLOCKING_FACTOR,
    DEFAULT_BAUD,
    PAGE_SIZE,
    FomeClient,
    ProtocolError,
    poll_for,
)

ROOT = Path(__file__).resolve().parent


def phase_identity(cli: FomeClient) -> dict:
    print("\n=== 1. Identity ===")
    sig = cli.query_signature()
    print(f"  S (signature): {sig!r}")
    try:
        ver = cli.version_info()
        print(f"  V (version):   {ver!r}")
    except Exception as e:
        ver = None
        print(f"  V (version):   FAILED: {e}")
    return {"signature": sig, "version": ver}


def phase_realtime(cli: FomeClient, seconds: float, hz: float) -> dict:
    print(f"\n=== 2. Realtime och poll ({seconds}s @ ~{hz} Hz) ===")
    t0 = time.monotonic()
    try:
        samples = poll_for(cli, seconds, hz)
    except Exception as e:
        print(f"  FAILED: {e}")
        return {"n": 0, "errors": 1, "error": str(e)}
    for i, row in enumerate(samples):
        if i < 3 or (i + 1) % 10 == 0:
            print(
                f"  t={row['t_ms']:5d}ms  RPM={row['RPM']:5d}  "
                f"TPS={row['TPS_pct']:6.2f}%  MAP={row['MAP_kPa']:6.1f}  "
                f"λ={row['lambda1']:.3f}  needBurn={row['needBurn']}"
            )
    rate = len(samples) / max(1e-6, time.monotonic() - t0)
    print(f"  samples={len(samples)} effective_hz={rate:.1f}")
    return {"n": len(samples), "head": samples[:2], "tail": samples[-3:]}


def phase_logging(
    cli: FomeClient, out_dir: Path, seconds: float, hz: float
) -> dict:
    print(f"\n=== 3. Logging soak ({seconds}s @ ~{hz} Hz) ===")
    bin_path = out_dir / "och_log.bin"
    jsonl_path = out_dir / "och_log.jsonl"
    t0 = time.monotonic()

    with bin_path.open("wb") as bf, jsonl_path.open("w", encoding="utf-8") as jf:

        def on_sample(row: dict, och: bytes) -> None:
            ts = time.time()
            bf.write(struct.pack("<d", ts) + och)
            out = dict(row)
            out["ts"] = ts
            jf.write(json.dumps(out) + "\n")

        samples = poll_for(cli, seconds, hz, on_sample=on_sample)

    elapsed = time.monotonic() - t0
    meta = {
        "samples": len(samples),
        "errors": 0,
        "elapsed_s": elapsed,
        "effective_hz": len(samples) / max(1e-6, elapsed),
        "bin": str(bin_path),
        "jsonl": str(jsonl_path),
    }
    print(
        f"  wrote {meta['samples']} samples @ {meta['effective_hz']:.1f} Hz"
    )
    return meta


def phase_flash(
    cli: FomeClient,
    out_dir: Path,
    do_write_back: bool,
    do_burn: bool,
) -> dict:
    print("\n=== 4. Flash page backup / CRC / write+burn ===")
    print(f"  reading full page ({PAGE_SIZE} B) chunks of {BLOCKING_FACTOR}...")
    t0 = time.monotonic()
    page = cli.page_read_all()
    read_s = time.monotonic() - t0
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    page_path = out_dir / f"flash_page_{stamp}.bin"
    page_path.write_bytes(page)
    local_crc = zlib.crc32(page) & 0xFFFFFFFF
    print(f"  saved {page_path.name} ({len(page)} B in {read_s:.2f}s)")
    print(f"  local IEEE CRC32: 0x{local_crc:08x}")

    result: dict = {
        "page_path": str(page_path),
        "page_size": len(page),
        "local_crc32": f"0x{local_crc:08x}",
        "read_seconds": read_s,
    }

    try:
        ecu_crc = cli.page_crc32(0, PAGE_SIZE)
        result["ecu_crc32_cmd"] = f"0x{ecu_crc:08x}"
        result["crc_matches_local"] = ecu_crc == local_crc
        print(f"  ECU k-command CRC32: 0x{ecu_crc:08x}")
    except Exception as e:
        result["ecu_crc32_cmd"] = None
        result["crc_error"] = str(e)
        print(f"  k-command CRC failed: {e}")

    if not do_write_back:
        print("  write-back/burn SKIPPED (pass --write-back / --burn).")
        result["write_back"] = False
        result["burn"] = False
        return result

    print("  write-back: identical page bytes...")
    t1 = time.monotonic()
    cli.page_write_all(page)
    result["write_back"] = True
    result["write_seconds"] = time.monotonic() - t1
    head = cli.page_read_chunk(0, min(256, PAGE_SIZE))
    if head != page[: len(head)]:
        raise ProtocolError("post-write head mismatch — abort burn")
    print("  post-write head verify OK")

    if not do_burn:
        print("  burn SKIPPED (pass --burn).")
        result["burn"] = False
        return result

    print("  burn B ...")
    br = cli.burn()
    result["burn"] = True
    result["burn_flag"] = f"0x{br.flag:02x}"
    print(f"  burn flag=0x{br.flag:02x}")
    time.sleep(0.5)
    page2 = cli.page_read_all()
    result["post_burn_match"] = page2 == page
    print(f"  post-burn match: {result['post_burn_match']}")
    if page2 != page:
        mismatch = out_dir / f"flash_page_post_burn_MISMATCH_{stamp}.bin"
        mismatch.write_bytes(page2)
        print(f"  WARNING: {mismatch}")
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description="FOME TS HIL spike")
    ap.add_argument("--port", default="COM13")
    ap.add_argument("--baud", type=int, default=DEFAULT_BAUD)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--rt-seconds", type=float, default=3.0)
    ap.add_argument("--log-seconds", type=float, default=5.0)
    ap.add_argument("--rt-hz", type=float, default=20.0)
    ap.add_argument("--log-hz", type=float, default=50.0)
    ap.add_argument("--write-back", action="store_true")
    ap.add_argument("--burn", action="store_true")
    ap.add_argument("--skip-flash", action="store_true")
    args = ap.parse_args()
    if args.burn and not args.write_back:
        print("--burn requires --write-back", file=sys.stderr)
        return 2

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = args.out or (ROOT / f"run-{stamp}")
    out_dir.mkdir(parents=True, exist_ok=True)

    summary: dict = {
        "port": args.port,
        "started": datetime.now(timezone.utc).isoformat(),
        "out_dir": str(out_dir),
    }
    print(f"FOME HIL spike → {args.port}  out={out_dir}")

    try:
        with FomeClient(args.port, args.baud) as cli:
            summary["identity"] = phase_identity(cli)
            summary["realtime"] = phase_realtime(
                cli, args.rt_seconds, args.rt_hz
            )
            summary["logging"] = phase_logging(
                cli, out_dir, args.log_seconds, args.log_hz
            )
            if not args.skip_flash:
                summary["flash"] = phase_flash(
                    cli,
                    out_dir,
                    do_write_back=args.write_back,
                    do_burn=args.burn,
                )
            else:
                summary["flash"] = {"skipped": True}
    except serial.SerialException as e:
        print(f"\nSERIAL ERROR: {e}", file=sys.stderr)
        summary["error"] = str(e)
        (out_dir / "summary.json").write_text(
            json.dumps(summary, indent=2), encoding="utf-8"
        )
        return 1
    except Exception as e:
        print(f"\nFAILED: {e}", file=sys.stderr)
        summary["error"] = str(e)
        (out_dir / "summary.json").write_text(
            json.dumps(summary, indent=2), encoding="utf-8"
        )
        return 1

    summary["finished"] = datetime.now(timezone.utc).isoformat()
    path = out_dir / "summary.json"
    path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\n=== DONE === {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
