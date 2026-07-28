"""Launchable host entry for the Aether AFR gauge mockup.

Usage (from aether product root)::

    python -m mockup
    python mockup/run.py
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

# Landscape product face: native panel 368×448 rotated so USB + hard buttons
# are on the TOP edge → logical UI size 448×368.
FACE_W = 448
FACE_H = 368
TOP_CHROME = 60
BOTTOM_DOTS = 28
DIAL_SCALE = 0.75  # graph 25% shorter
INNER_SCALE = 0.72
PAGE_COUNT = 3
# Type as fractions of dial *half* (face-relative sizing caused overflow).
AFR_DIGIT_OF_HALF = 0.58
TICK_OF_HALF = 0.16
CAPTION_OF_HALF = 0.12
HARD_LABEL_OF_CHROME = 0.42


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
    return "#2e2e36"  # visible unlit ring on black


def _layout(w: int = FACE_W, h: int = FACE_H) -> dict:
    content_top = TOP_CHROME
    content_bot = h - BOTTOM_DOTS
    content_h = content_bot - content_top
    half = min(w / 2.0, content_h / 2.0) * DIAL_SCALE
    cx = w / 2.0
    cy = content_top + content_h / 2.0
    outer_half = half  # mid-side thickness == mid-top thickness
    inner_half = half * INNER_SCALE
    return {
        "w": w,
        "h": h,
        "content_top": float(content_top),
        "content_bot": float(content_bot),
        "half": half,
        "outer_half": outer_half,
        "cx": cx,
        "cy": cy,
        "inner_half": inner_half,
        "inner_corner": inner_half * 0.28,
        "mode_x": 22.0,
        "sel_x": w - 22.0,
        "chrome_y": TOP_CHROME / 2.0,
        "log_r": 9.0,
        "dots_y": h - BOTTOM_DOTS / 2.0,
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
    """Square outer envelope: equal mid-side and mid-top radial thickness."""
    dx = math.cos(a)
    dy = -math.sin(a)
    oh = L["outer_half"]
    r_max = float("inf")
    if dx > 1e-9:
        r_max = min(r_max, oh / dx)
    if dx < -1e-9:
        r_max = min(r_max, oh / -dx)
    if dy > 1e-9:
        r_max = min(r_max, oh / dy)
    if dy < -1e-9:
        r_max = min(r_max, oh / -dy)
    return max(L["inner_half"] + 4.0, r_max - 0.5)


def _inner_radius_at(a: float, L: dict) -> float:
    return _radius_to_rounded_square(
        math.cos(a), -math.sin(a), L["inner_half"], L["inner_corner"]
    )


def render_gauge_svg(
    state,
    w: int = FACE_W,
    h: int = FACE_H,
    *,
    logging: bool = True,
    page: int = 0,
) -> str:
    """Landscape 448×368 face: hard-button labels, log LED, gauge, swipe dots."""
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
        f'<rect x="0" y="0" width="{w}" height="{TOP_CHROME}" fill="#08080c"/>',
    ]

    # Hard-button labels (not touch targets)
    label_px = max(16, round(TOP_CHROME * HARD_LABEL_OF_CHROME))
    parts.append(
        f'<text x="{L["mode_x"]}" y="{L["chrome_y"]}" fill="#e0e0e6" '
        f'font-size="{label_px}" font-weight="700" '
        f'font-family="Segoe UI, Arial, sans-serif" text-anchor="start" '
        f'dominant-baseline="middle">MODE</text>'
    )
    parts.append(
        f'<text x="{L["sel_x"]}" y="{L["chrome_y"]}" fill="#e0e0e6" '
        f'font-size="{label_px}" font-weight="700" '
        f'font-family="Segoe UI, Arial, sans-serif" text-anchor="end" '
        f'dominant-baseline="middle">SEL</text>'
    )

    # Logging LED centered between labels
    led_y = L["chrome_y"]
    led_r = L["log_r"]
    if logging:
        parts.append(
            f'<circle cx="{cx}" cy="{led_y}" r="{led_r + 4}" fill="#ff2828" opacity="0.2"/>'
        )
        parts.append(f'<circle cx="{cx}" cy="{led_y}" r="{led_r}" fill="#ff3232"/>')
    else:
        parts.append(
            f'<circle cx="{cx}" cy="{led_y}" r="{led_r}" fill="#121216" '
            f'stroke="#33333a" stroke-width="2"/>'
        )

    if page == 0:
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

        half = L["half"]
        label_tick = max(11, round(half * TICK_OF_HALF))
        for mark, label in ((8, "8"), (11, "11"), (13, "13"), (15, "15"), (17, "17"), (20, "20")):
            t = (mark - AFR_MIN) / (AFR_MAX - AFR_MIN)
            ang = math.radians(start_deg - t * sweep_deg)
            # Tick labels sit in the ring band, not the digit hole.
            ri = _inner_radius_at(ang, L)
            ro = _outer_radius_at(ang, L)
            r = (ri + ro) / 2.0
            x = cx + r * math.cos(ang)
            y = cy - r * math.sin(ang)
            parts.append(
                f'<text x="{x:.1f}" y="{y:.1f}" fill="#d0d0d8" font-size="{label_tick}" '
                f'font-weight="600" font-family="Segoe UI, Arial, sans-serif" '
                f'text-anchor="middle" dominant-baseline="middle">{label}</text>'
            )

        digit_px = min(round(half * AFR_DIGIT_OF_HALF), round(L["inner_half"] * 0.95))
        digit_y = cy - digit_px * 0.08
        parts.append(
            f'<text x="{cx}" y="{digit_y:.1f}" fill="#ff2a2a" '
            f'font-size="{digit_px}" font-weight="700" '
            f'font-family="Consolas, monospace" text-anchor="middle" '
            f'dominant-baseline="middle">{state.readout()}</text>'
        )
        caption_px = max(9, round(half * CAPTION_OF_HALF))
        parts.append(
            f'<text x="{cx}" y="{digit_y + digit_px * 0.52:.1f}" fill="#c0c0c8" '
            f'font-size="{caption_px}" font-weight="600" '
            f'font-family="Segoe UI, Arial, sans-serif" text-anchor="middle" '
            f'dominant-baseline="hanging">AIR/FUEL RATIO</text>'
        )
    else:
        title = "MONITOR" if page == 1 else "LOGGER"
        parts.append(
            f'<text x="{cx}" y="{cy}" fill="#888" font-size="{round(w * 0.045)}" '
            f'font-weight="600" font-family="Segoe UI, Arial, sans-serif" '
            f'text-anchor="middle" dominant-baseline="middle">{title}</text>'
        )

    # Bottom swipe dots
    parts.append(
        f'<rect x="0" y="{h - BOTTOM_DOTS}" width="{w}" height="{BOTTOM_DOTS}" fill="#08080c"/>'
    )
    gap = 14
    total_w = (PAGE_COUNT - 1) * gap
    x0 = cx - total_w / 2
    dots_y = L["dots_y"]
    for i in range(PAGE_COUNT):
        x = x0 + i * gap
        r = 4.5 if i == page else 3.5
        fill = "#e8e8ee" if i == page else "#3a3a44"
        parts.append(f'<circle cx="{x:.1f}" cy="{dots_y}" r="{r}" fill="{fill}"/>')

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

    print("Aether AFR gauge mockup (simulated data, landscape 448×368)")
    print(
        f"scale={AFR_MIN}–{AFR_MAX}  segments={SEGMENT_COUNT}  "
        f"face={FACE_W}×{FACE_H} (native 368×448 landscape)  ticks={ticks}  seed={seed}"
    )
    print("-" * 72)
    print(report, end="")
    print("-" * 72)
    print(f"stream_changes={states_change(states)}")

    last = states[-1]
    svg_path = out / "afr_gauge.svg"
    svg_path.write_text(render_gauge_svg(last, logging=True, page=0), encoding="utf-8")
    (out / "afr_gauge_log_off.svg").write_text(
        render_gauge_svg(last, logging=False, page=0), encoding="utf-8"
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
    print("graphical UI: open mockup/gauge.html (landscape 448×368)")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Aether AFR gauge mockup (simulated AFR)")
    p.add_argument("--ticks", type=int, default=24)
    p.add_argument("--out", type=Path, default=None)
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args(argv)
    return run(ticks=args.ticks, out_dir=args.out, seed=args.seed)


if __name__ == "__main__":
    sys.exit(main())
