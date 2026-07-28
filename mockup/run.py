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
    AFR_STOICH,
    SEGMENT_COUNT,
    SimulatorConfig,
    map_afr,
    simulate_stream,
    states_change,
)

# ESP32-S3-Touch-AMOLED-1.8 class panel (matches mockup/gauge.html).
FACE_W = 368
FACE_H = 448
BTN_STRIP_H = 72
BTN_GAP = 6
# Band 25% thinner than prior 0.706-inner: thickness 0.294→0.2205 → inner 0.7795
INNER_SCALE = 0.7795


def _stoich_segment_index(n: int = SEGMENT_COUNT) -> int:
    span = AFR_MAX - AFR_MIN
    i = int(math.floor(((AFR_STOICH - AFR_MIN) / span) * n))
    return min(n - 1, max(0, i))


def _segment_svg_color(band: str, lit: bool, *, stoich: bool = False) -> str:
    if lit:
        return {
            "green": "#22c55e",
            "amber": "#f59e0b",
            "red": "#ef4444",
            "invalid": "#444444",
        }.get(band, "#666666")
    if stoich:
        return "#2a4a32"
    return "#1a1a1e"


def _layout(w: int = FACE_W, h: int = FACE_H) -> dict:
    strip_h = BTN_STRIP_H
    btn_y = h - strip_h
    btn_h = strip_h
    btn_w = (w - BTN_GAP) / 2
    half = w / 2.0
    cx = w / 2.0
    cy = half
    inner_half = half * INNER_SCALE
    status_y = min(btn_y - 4.0, cy + half * 0.92)
    return {
        "w": w,
        "h": h,
        "size": w,  # half-span for horizontal
        "strip_h": strip_h,
        "btn_y": float(btn_y),
        "cx": cx,
        "cy": cy,
        "half": half,
        "status_y": status_y,
        "inner_half": inner_half,
        "inner_corner": inner_half * 0.28,
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


def _radius_to_rounded_square(ux: float, uy: float, half: float, corner: float) -> float:
    ax, ay = abs(ux), abs(uy)
    flat = half - corner
    if flat <= 0:
        return half
    if ax > 1e-12:
        t = half / ax
        if abs(t * uy) <= flat + 1e-9:
            return t
    if ay > 1e-12:
        t = half / ay
        if abs(t * ux) <= flat + 1e-9:
            return t
    ccx = (1.0 if ux >= 0 else -1.0) * flat
    ccy = (1.0 if uy >= 0 else -1.0) * flat
    b = ux * ccx + uy * ccy
    c0 = ccx * ccx + ccy * ccy - corner * corner
    disc = b * b - c0
    if disc < 0:
        return half
    t2 = b + math.sqrt(disc)
    if t2 > 1e-9:
        return t2
    return half


def _outer_radius_at(a: float, L: dict) -> float:
    dx = math.cos(a)
    dy = -math.sin(a)
    w, cx, cy = L["w"], L["cx"], L["cy"]
    r_max = float("inf")
    if dx > 1e-9:
        r_max = min(r_max, (w - cx) / dx)
    if dx < -1e-9:
        r_max = min(r_max, (0.0 - cx) / dx)
    if dy > 1e-9:
        r_max = min(r_max, (L["btn_y"] - cy) / dy)
    if dy < -1e-9:
        r_max = min(r_max, (0.0 - cy) / dy)
    return max(L["inner_half"] + 4.0, r_max - 0.5)


def _inner_radius_at(a: float, L: dict) -> float:
    ux = math.cos(a)
    uy = -math.sin(a)
    return _radius_to_rounded_square(ux, uy, L["inner_half"], L["inner_corner"])


def render_gauge_svg(
    state,
    w: int = FACE_W,
    h: int = FACE_H,
    *,
    logging: bool = True,
) -> str:
    """Device-sized face (368×448): flush segments, log LED, MODE/SEL."""
    L = _layout(w, h)
    cx, cy = L["cx"], L["cy"]
    n = len(state.segment_bands)
    start_deg = 225.0
    sweep_deg = 270.0
    stoich_i = _stoich_segment_index(n)

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}">',
        f'<rect width="100%" height="100%" fill="#050508"/>',
    ]

    lit_set = set(state.lit_indices)
    steps = 10
    for i, band in enumerate(state.segment_bands):
        a0 = math.radians(start_deg - (i / n) * sweep_deg)
        a1 = math.radians(start_deg - ((i + 1) / n) * sweep_deg)
        gap = 0.012
        aa0, aa1 = a0 - gap, a1 + gap
        pts: list[str] = []
        for s in range(steps + 1):
            t = s / steps
            a = aa0 + (aa1 - aa0) * t
            r = _outer_radius_at(a, L)
            pts.append(f"{cx + r * math.cos(a):.2f},{cy - r * math.sin(a):.2f}")
        for s in range(steps, -1, -1):
            t = s / steps
            a = aa0 + (aa1 - aa0) * t
            r = _inner_radius_at(a, L)
            pts.append(f"{cx + r * math.cos(a):.2f},{cy - r * math.sin(a):.2f}")
        lit = i in lit_set
        color = _segment_svg_color(band.value, lit, stoich=(i == stoich_i))
        stroke = (
            f' stroke="#3d6b48" stroke-width="1.5"'
            if (i == stoich_i and not lit)
            else ""
        )
        parts.append(f'<polygon points="{" ".join(pts)}" fill="{color}"{stroke}/>')

    label_px = max(18, round(w * 0.062))
    for mark, label in ((8, "8"), (11, "11"), (13, "13"), (15, "15"), (17, "17"), (20, "20")):
        t = (mark - AFR_MIN) / (AFR_MAX - AFR_MIN)
        ang = math.radians(start_deg - t * sweep_deg)
        r = max(8.0, _inner_radius_at(ang, L) - label_px * 0.72)
        x = cx + r * math.cos(ang)
        y = cy - r * math.sin(ang)
        parts.append(
            f'<text x="{x:.1f}" y="{y:.1f}" fill="#d0d0d8" font-size="{label_px}" '
            f'font-weight="600" font-family="Segoe UI, Arial, sans-serif" '
            f'text-anchor="middle" dominant-baseline="middle">{label}</text>'
        )

    digit_px = round(w * 0.30)
    digit_y = cy - L["inner_half"] * 0.08
    readout = state.readout()
    parts.append(
        f'<text x="{cx}" y="{digit_y:.1f}" fill="#ff2a2a" '
        f'font-size="{digit_px}" font-weight="700" '
        f'font-family="Consolas, monospace" text-anchor="middle" '
        f'dominant-baseline="middle">{readout}</text>'
    )
    caption_px = max(12, round(w * 0.042))
    parts.append(
        f'<text x="{cx}" y="{digit_y + digit_px * 0.48:.1f}" fill="#b8b8c0" '
        f'font-size="{caption_px}" font-weight="600" '
        f'font-family="Segoe UI, Arial, sans-serif" text-anchor="middle" '
        f'dominant-baseline="hanging">AIR/FUEL RATIO</text>'
    )

    # Logging LED (no text) in rail above buttons
    led_y = (L["status_y"] + L["btn_y"]) / 2
    led_r = 9
    if logging:
        parts.append(
            f'<circle cx="{cx}" cy="{led_y:.1f}" r="{led_r + 5}" fill="#ff2828" opacity="0.2"/>'
        )
        parts.append(
            f'<circle cx="{cx}" cy="{led_y:.1f}" r="{led_r}" fill="#ff3232"/>'
        )
    else:
        parts.append(
            f'<circle cx="{cx}" cy="{led_y:.1f}" r="{led_r}" fill="#121216" '
            f'stroke="#33333a" stroke-width="2"/>'
        )

    parts.append(
        f'<rect x="0" y="{L["mode"]["y"]}" width="{w}" height="{L["strip_h"]}" fill="#0a0a0c"/>'
    )
    for key in ("mode", "sel"):
        b = L[key]
        title_px = max(18, round(b["h"] * 0.38))
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

    print("Aether AFR gauge mockup (simulated data, 368×448 device face)")
    print(
        f"scale={AFR_MIN}–{AFR_MAX}  segments={SEGMENT_COUNT}  "
        f"face={FACE_W}×{FACE_H}  ticks={ticks}  seed={seed}"
    )
    print("-" * 72)
    print(report, end="")
    print("-" * 72)
    print(f"stream_changes={states_change(states)}")

    last = states[-1]
    svg_path = out / "afr_gauge.svg"
    svg_path.write_text(render_gauge_svg(last, logging=True), encoding="utf-8")
    (out / "afr_gauge_log_off.svg").write_text(
        render_gauge_svg(last, logging=False), encoding="utf-8"
    )

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
    print("graphical UI: open mockup/gauge.html (368×448 + log LED)")
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
