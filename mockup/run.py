"""Launchable host entry for the Aether AFR gauge mockup.

Usage (from aether product root)::

    python -m mockup
    python mockup/run.py
    python mockup/run.py --ticks 20 --out mockup/out
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

from .afr_gauge import (
    AFR_MAX,
    AFR_MIN,
    SEGMENT_COUNT,
    SimulatorConfig,
    map_afr,
    simulate_stream,
    states_change,
)

# Square device-class canvas (matches mockup/gauge.html logical size).
FACE_SIZE = 368
BTN_STRIP_FRAC = 0.18
BTN_GAP = 6


def _segment_svg_color(band: str, lit: bool) -> str:
    if not lit:
        return "#1a1a1e"
    return {
        "green": "#22c55e",
        "amber": "#f59e0b",
        "red": "#ef4444",
        "invalid": "#444444",
    }.get(band, "#666666")


def _layout(size: int = FACE_SIZE) -> dict:
    strip_h = round(size * BTN_STRIP_FRAC)
    btn_y = size - strip_h
    btn_h = strip_h
    btn_w = (size - BTN_GAP) / 2
    outer_r = size / 2.0
    return {
        "size": size,
        "strip_h": strip_h,
        "cx": size / 2.0,
        "cy": outer_r,  # top of circle flush with y=0
        "outer_r": outer_r,
        "mode": {
            "x": 0.0,
            "y": float(btn_y),
            "w": btn_w,
            "h": float(btn_h),
            "label": "MODE",
        },
        "sel": {
            "x": btn_w + BTN_GAP,
            "y": float(btn_y),
            "w": btn_w,
            "h": float(btn_h),
            "label": "SEL",
        },
    }


def render_gauge_svg(state, size: int = FACE_SIZE) -> str:
    """Square face: circular arc flush L/T/R; MODE/SEL flush bottom (no sublabels)."""
    L = _layout(size)
    w = h = size
    cx = L["cx"]
    cy = L["cy"]
    outer_r = L["outer_r"]
    inner_r = outer_r * 0.78
    n = len(state.segment_bands)
    start_deg = 225.0
    sweep_deg = 270.0

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}">',
        f'<rect width="100%" height="100%" fill="#050508"/>',
    ]

    lit_set = set(state.lit_indices)
    for i, band in enumerate(state.segment_bands):
        a0 = math.radians(start_deg - (i / n) * sweep_deg)
        a1 = math.radians(start_deg - ((i + 1) / n) * sweep_deg)
        gap = 0.01
        a0 -= gap
        a1 += gap
        x0o, y0o = cx + outer_r * math.cos(a0), cy - outer_r * math.sin(a0)
        x1o, y1o = cx + outer_r * math.cos(a1), cy - outer_r * math.sin(a1)
        x1i, y1i = cx + inner_r * math.cos(a1), cy - inner_r * math.sin(a1)
        x0i, y0i = cx + inner_r * math.cos(a0), cy - inner_r * math.sin(a0)
        color = _segment_svg_color(band.value, i in lit_set)
        d = (
            f"M {x0o:.2f} {y0o:.2f} A {outer_r:.2f} {outer_r:.2f} 0 0 1 {x1o:.2f} {y1o:.2f} "
            f"L {x1i:.2f} {y1i:.2f} A {inner_r:.2f} {inner_r:.2f} 0 0 0 {x0i:.2f} {y0i:.2f} Z"
        )
        parts.append(f'<path d="{d}" fill="{color}"/>')

    for mark, label in ((8, "8"), (11, "11"), (13, "13"), (15, "15"), (17, "17"), (20, "20")):
        t = (mark - AFR_MIN) / (AFR_MAX - AFR_MIN)
        ang = math.radians(start_deg - t * sweep_deg)
        r = inner_r - w * 0.055
        x = cx + r * math.cos(ang)
        y = cy - r * math.sin(ang)
        parts.append(
            f'<text x="{x:.1f}" y="{y:.1f}" fill="#888" font-size="{max(12, round(w * 0.038))}" '
            f'font-family="Segoe UI, Arial, sans-serif" text-anchor="middle" '
            f'dominant-baseline="middle">{label}</text>'
        )

    digit_px = round(w * 0.20)
    readout = state.readout()
    parts.append(
        f'<text x="{cx}" y="{cy * 0.95:.1f}" fill="#ff2a2a" '
        f'font-size="{digit_px}" font-weight="700" '
        f'font-family="Consolas, monospace" text-anchor="middle" '
        f'dominant-baseline="middle">{readout}</text>'
    )
    parts.append(
        f'<text x="{cx}" y="{cy * 0.95 + digit_px * 0.55:.1f}" fill="#b8b8c0" '
        f'font-size="{max(12, round(w * 0.042))}" font-weight="600" '
        f'font-family="Segoe UI, Arial, sans-serif" text-anchor="middle">'
        f"AIR/FUEL RATIO</text>"
    )

    # Bottom strip + flush MODE / SEL (title only)
    parts.append(
        f'<rect x="0" y="{L["mode"]["y"]}" width="{w}" height="{L["strip_h"]}" fill="#0a0a0c"/>'
    )
    for key in ("mode", "sel"):
        b = L[key]
        title_px = max(18, round(b["h"] * 0.42))
        parts.append(
            f'<rect x="{b["x"]:.1f}" y="{b["y"]:.1f}" width="{b["w"]:.1f}" height="{b["h"]:.1f}" '
            f'fill="#141418" stroke="#2e2e36" stroke-width="2"/>'
        )
        parts.append(
            f'<text x="{b["x"] + b["w"] / 2:.1f}" y="{b["y"] + b["h"] / 2:.1f}" '
            f'fill="#eee" font-size="{title_px}" font-weight="700" '
            f'font-family="Segoe UI, Arial, sans-serif" text-anchor="middle" '
            f'dominant-baseline="middle">{b["label"]}</text>'
        )

    parts.append("</svg>")
    return "\n".join(parts)


def format_state_line(i: int, state) -> str:
    lit = ",".join(str(x) for x in state.lit_indices[:8])
    if state.lit_count > 8:
        lit += ",…"
    return (
        f"[{i:03d}] AFR={state.afr:6.2f}  display={state.display_afr:5.1f}  "
        f"band={state.band.value:7s}  valid={str(state.valid):5s}  "
        f"lit={state.lit_count:2d}/{SEGMENT_COUNT}  indices=[{lit}]  "
        f"readout={state.readout()}"
    )


def run(ticks: int = 24, out_dir: Path | None = None, seed: int = 42) -> int:
    out = out_dir or Path(__file__).resolve().parent / "out"
    out.mkdir(parents=True, exist_ok=True)

    cfg = SimulatorConfig(seed=seed)
    states = simulate_stream(ticks, config=cfg)
    lines = [format_state_line(i, s) for i, s in enumerate(states)]
    report = "\n".join(lines) + "\n"

    print("Aether AFR gauge mockup (simulated data, square face / circular gauge)")
    print(
        f"scale={AFR_MIN}–{AFR_MAX}  segments={SEGMENT_COUNT}  "
        f"face={FACE_SIZE}×{FACE_SIZE}  ticks={ticks}  seed={seed}"
    )
    print("-" * 72)
    print(report, end="")
    print("-" * 72)
    print(f"stream_changes={states_change(states)}")

    last = states[-1]
    svg_path = out / "afr_gauge.svg"
    svg_path.write_text(render_gauge_svg(last), encoding="utf-8")

    for name, afr in (("rich", 10.5), ("stoich", 14.7), ("lean", 17.0)):
        (out / f"afr_{name}.svg").write_text(
            render_gauge_svg(map_afr(afr)), encoding="utf-8"
        )

    json_path = out / "afr_stream.json"
    payload = [
        {
            "afr": s.afr,
            "display_afr": s.display_afr,
            "valid": s.valid,
            "band": s.band.value,
            "lit_count": s.lit_count,
            "lit_indices": list(s.lit_indices),
            "readout": s.readout(),
        }
        for s in states
    ]
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    report_path = out / "afr_stream.txt"
    report_path.write_text(report, encoding="utf-8")

    print(f"wrote {svg_path}")
    print(f"wrote {json_path}")
    print(f"wrote {report_path}")
    print("graphical UI: open mockup/gauge.html (flush L/T/R circle + MODE/SEL)")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Aether AFR gauge mockup (simulated AFR)")
    p.add_argument("--ticks", type=int, default=24, help="simulated samples to emit")
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="directory for SVG/JSON snapshots (default: mockup/out)",
    )
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args(argv)
    return run(ticks=args.ticks, out_dir=args.out, seed=args.seed)


if __name__ == "__main__":
    sys.exit(main())
