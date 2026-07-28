"""Capture mockup frames so agents can *see* the gauge (not only ship code).

Writes PNG evidence under mockup/out/ (and optional --out dir):

  python -m mockup.capture
  python -m mockup.capture --html   # also Edge headless of gauge.html

Requires ImageMagick `magick` on PATH for SVG→PNG. Optional Edge for HTML.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from .afr_gauge import map_afr
from .run import FACE_H, FACE_W, render_gauge_svg

ROOT = Path(__file__).resolve().parent
DEFAULT_OUT = ROOT / "out"

EDGE_CANDIDATES = [
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
]


def _magick() -> str | None:
    return shutil.which("magick")


def svg_to_png(svg_path: Path, png_path: Path, *, density: int = 192) -> None:
    magick = _magick()
    if not magick:
        raise RuntimeError("ImageMagick `magick` not on PATH — cannot rasterize SVG")
    png_path.parent.mkdir(parents=True, exist_ok=True)
    # Transparent-free black background; density for readable agent inspection
    subprocess.run(
        [
            magick,
            "-density",
            str(density),
            str(svg_path),
            "-background",
            "#050508",
            "-alpha",
            "remove",
            "-alpha",
            "off",
            str(png_path),
        ],
        check=True,
    )


def capture_svg_frames(out: Path) -> list[Path]:
    out.mkdir(parents=True, exist_ok=True)
    frames = [
        ("preview_stoich", map_afr(14.7), True, 0, 3200, 28.0),
        ("preview_rich", map_afr(10.5), True, 0, 4800, 72.0),
        ("preview_lean", map_afr(17.0), True, 0, 2100, 12.0),
        ("preview_log_off", map_afr(14.7), False, 0, 900, 0.0),
        ("preview_wot", map_afr(12.8), True, 0, 6500, 100.0),
    ]
    paths: list[Path] = []
    for name, state, logging, page, rpm, tps in frames:
        svg = out / f"{name}.svg"
        png = out / f"{name}.png"
        svg.write_text(
            render_gauge_svg(
                state, logging=logging, page=page, rpm=rpm, tps=tps
            ),
            encoding="utf-8",
        )
        svg_to_png(svg, png)
        paths.append(png)
        print(f"wrote {png}  ({FACE_W}x{FACE_H} @ density 192)")
    return paths


def capture_html(out: Path) -> Path | None:
    edge = next((p for p in EDGE_CANDIDATES if p.is_file()), None)
    if edge is None:
        print("no Edge/Chrome found — skip HTML screenshot")
        return None
    html = ROOT / "gauge.html"
    # Scale window so 1.8" CSS face is readable in the PNG (not 1:1 physical).
    # The page still draws the tiny device; we zoom via device scale factor.
    png = out / "preview_html.png"
    out.mkdir(parents=True, exist_ok=True)
    uri = html.resolve().as_uri()
    cmd = [
        str(edge),
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        f"--screenshot={png}",
        "--window-size=900,700",
        "--force-device-scale-factor=2",
        uri,
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"wrote {png}")
    return png


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Capture AFR mockup PNG evidence")
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    p.add_argument(
        "--html",
        action="store_true",
        help="also screenshot gauge.html via Edge/Chrome headless",
    )
    args = p.parse_args(argv)

    if not _magick():
        print("ERROR: ImageMagick `magick` required for SVG capture", file=sys.stderr)
        return 2

    paths = capture_svg_frames(args.out)
    if args.html:
        capture_html(args.out)

    # Quick structural sanity: PNGs exist and are non-trivial
    for path in paths:
        if path.stat().st_size < 2000:
            print(f"ERROR: capture looks empty: {path}", file=sys.stderr)
            return 3
    print(f"capture ok: {len(paths)} SVG frames")
    print("Agent: open preview_*.png with the image reader to inspect the face.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
