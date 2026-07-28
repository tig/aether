"""Launchable host entry for the Aether AFR gauge mockup.

Usage (from aether product root)::

    python -m mockup
    python mockup/run.py
    python mockup/run.py --ticks 20 --out mockup/out
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .afr_gauge import (
    AFR_MAX,
    AFR_MIN,
    SEGMENT_COUNT,
    AfrSimulator,
    SimulatorConfig,
    map_afr,
    simulate_stream,
    states_change,
)


def _segment_svg_color(band: str, lit: bool) -> str:
    if not lit:
        return "#1a1a1a"
    return {
        "green": "#22c55e",
        "amber": "#f59e0b",
        "red": "#ef4444",
        "invalid": "#444444",
    }.get(band, "#666666")


def render_gauge_svg(state, width: int = 480, height: int = 480) -> str:
    """Render one gauge state as SVG (stdlib-only visual artifact)."""
    cx, cy = width / 2, height / 2
    outer_r = min(width, height) * 0.42
    inner_r = outer_r * 0.78
    n = len(state.segment_bands)
    # Arc from ~225° (bottom-left / AFR 8) clockwise-ish via top to ~-45° (AFR 20)
    # Use math angles: 0° = east, CCW. Map segment 0 → start_angle.
    start_deg = 225.0
    sweep_deg = 270.0  # leaves a gap at the bottom for label
    import math

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        f'<rect width="100%" height="100%" fill="#0a0a0a"/>',
        f'<circle cx="{cx}" cy="{cy}" r="{outer_r + 18}" fill="#111" stroke="#222" stroke-width="14"/>',
        f'<circle cx="{cx}" cy="{cy}" r="{outer_r + 4}" fill="#0d0d0d"/>',
    ]

    lit_set = set(state.lit_indices)
    for i, band in enumerate(state.segment_bands):
        a0 = math.radians(start_deg - (i / n) * sweep_deg)
        a1 = math.radians(start_deg - ((i + 1) / n) * sweep_deg)
        # pad a little gap between segments
        gap = 0.012
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

    # Scale marks
    for mark, label in ((8, "8"), (11, "11"), (13, "13"), (15, "15"), (17, "17"), (20, "20")):
        t = (mark - AFR_MIN) / (AFR_MAX - AFR_MIN)
        ang = math.radians(start_deg - t * sweep_deg)
        r = inner_r - 18
        x = cx + r * math.cos(ang)
        y = cy - r * math.sin(ang)
        parts.append(
            f'<text x="{x:.1f}" y="{y:.1f}" fill="#888" font-size="14" '
            f'font-family="Segoe UI, Arial, sans-serif" text-anchor="middle" '
            f'dominant-baseline="middle">{label}</text>'
        )

    readout = state.readout()
    parts.append(
        f'<text x="{cx}" y="{cy + 8}" fill="#ff2a2a" font-size="72" font-weight="700" '
        f'font-family="Consolas, monospace" text-anchor="middle" '
        f'dominant-baseline="middle">{readout}</text>'
    )
    parts.append(
        f'<text x="{cx}" y="{cy + 70}" fill="#ccc" font-size="16" letter-spacing="2" '
        f'font-family="Segoe UI, Arial, sans-serif" text-anchor="middle">'
        f"AIR/FUEL RATIO</text>"
    )
    band_label = state.band.value.upper()
    parts.append(
        f'<text x="{cx}" y="{cy + outer_r + 8}" fill="#555" font-size="12" '
        f'font-family="Segoe UI, Arial, sans-serif" text-anchor="middle">'
        f"band={band_label}  lit={state.lit_count}/{SEGMENT_COUNT}</text>"
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

    print("Aether AFR gauge mockup (simulated data)")
    print(f"scale={AFR_MIN}–{AFR_MAX}  segments={SEGMENT_COUNT}  ticks={ticks}  seed={seed}")
    print("-" * 72)
    print(report, end="")
    print("-" * 72)
    print(f"stream_changes={states_change(states)}")

    # Snapshot last state as SVG + JSON trail
    last = states[-1]
    svg_path = out / "afr_gauge.svg"
    svg_path.write_text(render_gauge_svg(last), encoding="utf-8")

    # Also map a few fixed demos into SVGs for visual comparison
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
    print(f"graphical UI: open mockup/gauge.html in a browser")
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
