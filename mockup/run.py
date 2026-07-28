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
BANNER_H = 60  # top strip: button labels + status indicators
TOP_CHROME = BANNER_H
BANNER_BG = "#1a2433"
BANNER_EDGE = "#2a3a52"
# Bottom ~30% of face for RPM / TPS aux readouts; dial ends above that.
AUX_FRAC = 0.30
SWIPE_DOTS_Y_FROM_BOTTOM = 12
BAND_FRAC = 0.14 * 1.1
PAGE_COUNT = 3
AFR_DIGIT_OF_HALF = 0.58 * 1.5 * 1.1 * 1.2 * 1.2 * 1.2 * 1.2  # value +20%
TICK_OF_HALF = 0.16 * 1.5 * 1.35  # dial legend restored larger
CAPTION_OF_HALF = 0.12 * 1.5 * 1.35  # value legend restored larger
HARD_LABEL_OF_CHROME = 0.42  # banner size = absolute min face text


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
    aux_h = round(h * AUX_FRAC)
    aux_top = h - aux_h
    content_bot = aux_top  # dial ends at aux top (value legend bottoms here)
    content_h = content_bot - content_top
    cx = w / 2.0
    cy = content_top + content_h / 2.0
    outer_half_w = w / 2.0
    outer_half_h = content_h / 2.0
    band = min(outer_half_w, outer_half_h) * BAND_FRAC
    inner_half_w = max(8.0, outer_half_w - band)
    inner_half_h = max(8.0, outer_half_h - band)
    inner_corner = min(inner_half_w, inner_half_h) * 0.22 * 1.15
    half = min(inner_half_w, inner_half_h)
    return {
        "w": w,
        "h": h,
        "content_top": float(content_top),
        "content_bot": float(content_bot),
        "aux_top": float(aux_top),
        "aux_h": float(aux_h),
        "half": half,
        "cx": cx,
        "cy": cy,
        "outer_half_w": outer_half_w,
        "outer_half_h": outer_half_h,
        "inner_half_w": inner_half_w,
        "inner_half_h": inner_half_h,
        "inner_corner": inner_corner,
        "band": band,
        "mode_x": 22.0,
        "sel_x": w - 22.0,
        "chrome_y": TOP_CHROME / 2.0,
        "log_r": 9.0,
        "dots_y": h - SWIPE_DOTS_Y_FROM_BOTTOM,
    }


def format_tps(tps: float) -> str:
    """Throttle position: 0% … 99%, WOT near full."""
    if tps >= 98:
        return "WOT"
    return f"{int(round(tps))}%"


def _radius_to_rounded_rect(
    ux: float, uy: float, half_w: float, half_h: float, corner: float
) -> float:
    ax, ay = abs(ux), abs(uy)
    flat_w = half_w - corner
    flat_h = half_h - corner
    if flat_w <= 0 or flat_h <= 0:
        if ax < 1e-12:
            return half_h
        if ay < 1e-12:
            return half_w
        return 1.0 / math.sqrt((ax * ax) / (half_w * half_w) + (ay * ay) / (half_h * half_h))
    if ax > 1e-12:
        t = half_w / ax
        if abs(t * uy) <= flat_h + 1e-9:
            return t
    if ay > 1e-12:
        t = half_h / ay
        if abs(t * ux) <= flat_w + 1e-9:
            return t
    ccx = (1.0 if ux >= 0 else -1.0) * flat_w
    ccy = (1.0 if uy >= 0 else -1.0) * flat_h
    b = ux * ccx + uy * ccy
    c0 = ccx * ccx + ccy * ccy - corner * corner
    disc = b * b - c0
    if disc < 0:
        return min(half_w, half_h)
    t2 = b + math.sqrt(disc)
    if t2 > 1e-9:
        return t2
    return min(half_w, half_h)


def _outer_radius_at(a: float, L: dict) -> float:
    """Rect outer: full content width × height (constant mid band thickness)."""
    dx = math.cos(a)
    dy = -math.sin(a)
    r_max = float("inf")
    if dx > 1e-9:
        r_max = min(r_max, L["outer_half_w"] / dx)
    if dx < -1e-9:
        r_max = min(r_max, L["outer_half_w"] / -dx)
    if dy > 1e-9:
        r_max = min(r_max, L["outer_half_h"] / dy)
    if dy < -1e-9:
        r_max = min(r_max, L["outer_half_h"] / -dy)
    return max(L["band"] + 2.0, r_max - 0.5)


def _inner_radius_at(a: float, L: dict) -> float:
    return _radius_to_rounded_rect(
        math.cos(a),
        -math.sin(a),
        L["inner_half_w"],
        L["inner_half_h"],
        L["inner_corner"],
    )


def render_gauge_svg(
    state,
    w: int = FACE_W,
    h: int = FACE_H,
    *,
    logging: bool = True,
    page: int = 0,
    rpm: int = 3200,
    tps: float = 35.0,
) -> str:
    """Landscape 448×368 face: banner, dial, AFR value, RPM/TPS aux, swipe dots."""
    L = _layout(w, h)
    cx, cy = L["cx"], L["cy"]
    n = len(state.segment_bands)
    # Arc from bottom-left corner → bottom-right corner via top (8 and 20 on corners).
    start_deg = math.degrees(math.atan2(-L["outer_half_h"], -L["outer_half_w"]))
    end_deg = math.degrees(math.atan2(-L["outer_half_h"], L["outer_half_w"]))
    if start_deg < 0:
        start_deg += 360.0
    sweep_deg = start_deg - end_deg
    stoich_i = _stoich_segment_index(n)

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}">',
        f'<rect width="100%" height="100%" fill="#050508"/>',
        # Banner (lexicon): distinct from dial face; light labels stay legible.
        f'<rect x="0" y="0" width="{w}" height="{TOP_CHROME}" fill="{BANNER_BG}"/>',
        f'<line x1="0" y1="{TOP_CHROME - 0.5}" x2="{w}" y2="{TOP_CHROME - 0.5}" '
        f'stroke="{BANNER_EDGE}" stroke-width="1"/>',
    ]

    # Hard-button labels (not touch targets)
    label_px = max(16, round(TOP_CHROME * HARD_LABEL_OF_CHROME))
    parts.append(
        f'<text x="{L["mode_x"]}" y="{L["chrome_y"]}" fill="#e8eef8" '
        f'font-size="{label_px}" font-weight="700" '
        f'font-family="Segoe UI, Arial, sans-serif" text-anchor="start" '
        f'dominant-baseline="middle">MODE</text>'
    )
    parts.append(
        f'<text x="{L["sel_x"]}" y="{L["chrome_y"]}" fill="#e8eef8" '
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
        # Dim red LED (still red) for logging-off state.
        parts.append(
            f'<circle cx="{cx}" cy="{led_y}" r="{led_r + 2}" fill="#781414" opacity="0.25"/>'
        )
        parts.append(
            f'<circle cx="{cx}" cy="{led_y}" r="{led_r}" fill="#5a1818" '
            f'stroke="#3a1010" stroke-width="1.5"/>'
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
        # Banner label size = absolute minimum for any face text.
        min_text_px = max(16, round(TOP_CHROME * HARD_LABEL_OF_CHROME))
        # Dial legend inside aperture (not on LED segments).
        label_tick = max(min_text_px, round(half * TICK_OF_HALF))
        for mark, label in ((8, "8"), (11, "11"), (13, "13"), (15, "15"), (17, "17"), (20, "20")):
            t = (mark - AFR_MIN) / (AFR_MAX - AFR_MIN)
            ang = math.radians(start_deg - t * sweep_deg)
            ri = _inner_radius_at(ang, L)
            r = max(float(label_tick), ri - label_tick * 0.85)
            x = cx + r * math.cos(ang)
            y = cy - r * math.sin(ang)
            parts.append(
                f'<text x="{x:.1f}" y="{y:.1f}" fill="#d0d0d8" font-size="{label_tick}" '
                f'font-weight="600" font-family="Segoe UI, Arial, sans-serif" '
                f'text-anchor="middle" dominant-baseline="middle">{label}</text>'
            )

        # Value (+20%); tight value legend; bottoms near dial content_bot.
        digit_px = min(
            round(half * AFR_DIGIT_OF_HALF),
            round(min(L["inner_half_w"], L["inner_half_h"]) * 0.98),
        )
        caption_px = max(min_text_px, round(half * CAPTION_OF_HALF))
        value_gap = max(2, round(digit_px * 0.08))
        caption_bottom = L["content_bot"] - max(4.0, L["band"] * 0.35)
        caption_y = caption_bottom - caption_px
        digit_y = caption_y - value_gap - digit_px / 2.0
        up = min(L["inner_half_h"], half) * 0.05
        digit_y -= up
        caption_y -= up
        parts.append(
            f'<text x="{cx}" y="{digit_y:.1f}" fill="#ff2a2a" '
            f'font-size="{digit_px}" font-weight="700" '
            f'font-family="Consolas, monospace" text-anchor="middle" '
            f'dominant-baseline="middle">{state.readout()}</text>'
        )
        parts.append(
            f'<text x="{cx}" y="{caption_y:.1f}" fill="#c0c0c8" '
            f'font-size="{caption_px}" font-weight="600" '
            f'font-family="Segoe UI, Arial, sans-serif" text-anchor="middle" '
            f'dominant-baseline="hanging">AIR/FUEL RATIO</text>'
        )

        # Aux: RPM left, TPS right; legends flush to bottom; numbers +20%.
        left_x = w * 0.28
        right_x = w * 0.72
        leg_px = min_text_px
        num_px = max(min_text_px, round(L["aux_h"] * 0.36 * 1.2))
        leg_baseline = h - 4
        mid_y = L["aux_top"] + (leg_baseline - leg_px - L["aux_top"]) * 0.48
        parts.append(
            f'<text x="{left_x:.1f}" y="{mid_y:.1f}" fill="#f0f0f4" '
            f'font-size="{num_px}" font-weight="700" '
            f'font-family="Consolas, monospace" text-anchor="middle" '
            f'dominant-baseline="middle">{rpm}</text>'
        )
        parts.append(
            f'<text x="{right_x:.1f}" y="{mid_y:.1f}" fill="#f0f0f4" '
            f'font-size="{num_px}" font-weight="700" '
            f'font-family="Consolas, monospace" text-anchor="middle" '
            f'dominant-baseline="middle">{format_tps(tps)}</text>'
        )
        parts.append(
            f'<text x="{left_x:.1f}" y="{leg_baseline}" fill="#b0b0bc" '
            f'font-size="{leg_px}" font-weight="600" '
            f'font-family="Segoe UI, Arial, sans-serif" text-anchor="middle" '
            f'dominant-baseline="auto">RPM</text>'
        )
        parts.append(
            f'<text x="{right_x:.1f}" y="{leg_baseline}" fill="#b0b0bc" '
            f'font-size="{leg_px}" font-weight="600" '
            f'font-family="Segoe UI, Arial, sans-serif" text-anchor="middle" '
            f'dominant-baseline="auto">TPS</text>'
        )
    else:
        title = "MONITOR" if page == 1 else "LOGGER"
        parts.append(
            f'<text x="{cx}" y="{cy}" fill="#888" font-size="{round(w * 0.045)}" '
            f'font-weight="600" font-family="Segoe UI, Arial, sans-serif" '
            f'text-anchor="middle" dominant-baseline="middle">{title}</text>'
        )

    # Swipe indicator overlay
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
