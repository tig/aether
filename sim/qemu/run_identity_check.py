#!/usr/bin/env python3
"""Assert QEMU serial log contains Aether identity (boot print).

Used by CI after tobozo/esp32-qemu-sim (or idf.py qemu) dumps logs.txt.
Also accepts a path to any captured UART log.

Exit 0 if fw_name=AETHER is present; 1 otherwise.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


NEEDLE = "fw_name=AETHER"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "log",
        nargs="?",
        default="logs.txt",
        help="Path to QEMU / UART capture log (default: logs.txt)",
    )
    p.add_argument(
        "--also",
        action="append",
        default=[],
        help="Additional needles that must appear (repeatable)",
    )
    args = p.parse_args(argv)
    path = Path(args.log)
    if not path.is_file():
        print(f"FAIL: log not found: {path}", file=sys.stderr)
        return 1
    text = path.read_text(encoding="utf-8", errors="replace")
    needles = [NEEDLE, *args.also]
    missing = [n for n in needles if n not in text]
    if missing:
        print(f"FAIL: missing {missing!r} in {path} ({len(text)} bytes)", file=sys.stderr)
        # show a short tail for agents
        tail = text[-800:] if len(text) > 800 else text
        print("--- log tail ---", file=sys.stderr)
        print(tail, file=sys.stderr)
        return 1
    print(f"OK: identity found in {path}")
    # Prefer full version line when present
    for line in text.splitlines():
        if "fw_name=AETHER" in line:
            print(f"  {line.strip()}")
            break
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
