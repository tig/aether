#!/usr/bin/env python3
"""Capture one named face scene via esprec (element harness skeleton).

Framework only — not a full visual regression suite.
  python tools/esprec_elements/capture_element.py --port COM11 --scene banner_afr
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

try:
    import tomllib
except ImportError:  # py<3.11
    import tomli as tomllib  # type: ignore

ROOT = Path(__file__).resolve().parents[2]
REG = Path(__file__).resolve().parent / "elements.toml"
DEFAULT_OUT = ROOT / "docs" / "esprec-captures"


def load_registry() -> dict:
    with REG.open("rb") as f:
        return tomllib.load(f)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", required=True, help="Serial port (e.g. COM11)")
    ap.add_argument("--scene", required=True, help="Scene id from elements.toml")
    ap.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="PNG path (default docs/esprec-captures/<scene>.png)",
    )
    ap.add_argument(
        "--settle",
        type=float,
        default=None,
        help="Seconds after face scene before shot (default: registry settle_s)",
    )
    ap.add_argument(
        "--list",
        action="store_true",
        help="List scenes and exit",
    )
    args = ap.parse_args()

    reg = load_registry()
    scenes = {s["id"]: s for s in reg.get("scenes", [])}
    elements = {e["id"]: e for e in reg.get("elements", [])}

    if args.list:
        for s in reg.get("scenes", []):
            el = s.get("element", "?")
            print(f"{s['id']:24} element={el:10} {s.get('note', '')}")
        return 0

    if args.scene not in scenes:
        print(f"error: unknown scene {args.scene!r}", file=sys.stderr)
        print("known:", ", ".join(sorted(scenes)), file=sys.stderr)
        return 2

    scene = scenes[args.scene]
    el_id = scene.get("element", "")
    el = elements.get(el_id, {})
    settle = args.settle if args.settle is not None else float(reg.get("meta", {}).get("settle_s", 0.25))
    out = args.output or (DEFAULT_OUT / f"{args.scene}.png")
    out.parent.mkdir(parents=True, exist_ok=True)

    try:
        from esprec.serial_port import open_port
        from esprec.capture import snapshot
    except ImportError:
        print(
            "error: esprec not installed. pip install -e <path-to-tig/esprec>",
            file=sys.stderr,
        )
        return 3

    shot_cmd = reg.get("meta", {}).get("shot_command", "esprec shot")
    if not str(shot_cmd).endswith("\n"):
        shot_cmd = str(shot_cmd) + "\n"

    print(f"scene={args.scene} element={el_id} settle={settle}s → {out}")
    if el.get("checklist"):
        print("checklist (manual for now):")
        for line in el["checklist"]:
            print(f"  - {line}")

    ser = open_port(args.port)
    try:
        # Named scene freeze (device must implement face scene).
        cmd = f"face scene {args.scene}\n".encode()
        ser.write(cmd)
        ser.flush()
        time.sleep(settle)
        meta = snapshot(ser, out, command=shot_cmd.encode() if isinstance(shot_cmd, str) else shot_cmd)
        print(f"OK {out} {meta.w}x{meta.h} ver={meta.version} crc=0x{meta.crc:08x}")
    finally:
        ser.close()

    print(f"next: open PNG; judge only element '{el_id}'; then fix face_{el_id}.c")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
