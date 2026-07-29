"""Generate Aether brand assets from Bergman classical-element geometry.

Symbol geometry from Wikimedia File:Aether_symbol.svg
(https://commons.wikimedia.org/wiki/File:Aether_symbol.svg) — Torbern Bergman ~1775.
"""
from __future__ import annotations

import os
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = Path(__file__).resolve().parent

# viewBox 0 0 12 12 centers from the SVG paths
CENTERS = [
    (6.0, 2.697),  # top
    (6.0, 6.962),  # mid
    (2.251, 9.303),  # bottom-left
    (9.749, 9.303),  # bottom-right
]
RADIUS = 1.25
VB = 12.0

BG_TOP = (8, 10, 22)
BG_BOT = (18, 14, 36)
GOLD = (232, 196, 96, 255)
GOLD_HI = (255, 236, 170, 255)
GLOW = (180, 140, 255, 90)
GLOW2 = (255, 210, 120, 70)
TEXT = (245, 240, 230, 255)
MUTED = (170, 175, 195, 255)
ACCENT_LINE = (232, 196, 96, 180)


def draw_aether_symbol(draw: ImageDraw.ImageDraw, cx: float, cy: float, scale: float, color, width_ratio: float = 0.28) -> None:
    sw = max(1, int(RADIUS * scale * width_ratio))
    for x, y in CENTERS:
        px = cx + (x - VB / 2) * scale
        py = cy + (y - VB / 2) * scale
        r = RADIUS * scale
        draw.ellipse([px - r, py - r, px + r, py + r], outline=color, width=sw)


def glow_layer(size, cx, cy, scale, glow_color, width_ratio=0.28, blur=18, glow_expand=1.35):
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    sw = max(2, int(RADIUS * scale * width_ratio * glow_expand))
    for x, y in CENTERS:
        px = cx + (x - VB / 2) * scale
        py = cy + (y - VB / 2) * scale
        r = RADIUS * scale * 1.02
        d.ellipse([px - r, py - r, px + r, py + r], outline=glow_color, width=sw)
    return layer.filter(ImageFilter.GaussianBlur(blur))


def find_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates: list[str] = []
    if bold:
        candidates += [
            r"C:\Windows\Fonts\segoeuib.ttf",
            r"C:\Windows\Fonts\arialbd.ttf",
            r"C:\Windows\Fonts\calibrib.ttf",
        ]
    candidates += [
        r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\calibri.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def vertical_gradient(w: int, h: int, c0, c1) -> Image.Image:
    im = Image.new("RGB", (w, h))
    px = im.load()
    for y in range(h):
        t = y / max(1, h - 1)
        r = int(c0[0] + (c1[0] - c0[0]) * t)
        g = int(c0[1] + (c1[1] - c0[1]) * t)
        b = int(c0[2] + (c1[2] - c0[2]) * t)
        for x in range(w):
            nx = (x / w - 0.5) * 2
            ny = (y / h - 0.5) * 2
            v = min(1.0, (nx * nx + ny * ny) ** 0.5)
            dark = 1.0 - 0.28 * v
            px[x, y] = (int(r * dark), int(g * dark), int(b * dark))
    return im.convert("RGBA")


def starfield(im: Image.Image, n: int = 120, seed: int = 42) -> Image.Image:
    rng = random.Random(seed)
    d = ImageDraw.Draw(im)
    w, h = im.size
    for _ in range(n):
        x = rng.randint(0, w - 1)
        y = rng.randint(0, h - 1)
        a = rng.randint(40, 160)
        s = rng.choice([1, 1, 1, 2])
        d.ellipse([x, y, x + s, y + s], fill=(220, 225, 255, a))
    return im


def make_icon(size: int = 1024) -> Image.Image:
    icon = vertical_gradient(size, size, BG_TOP, BG_BOT)
    icon = starfield(icon, n=80, seed=7)
    cx = cy = size / 2
    scale = size * 0.62 / 9.1
    g1 = glow_layer((size, size), cx, cy, scale, GLOW, width_ratio=0.30, blur=28, glow_expand=1.6)
    g2 = glow_layer((size, size), cx, cy, scale, GLOW2, width_ratio=0.28, blur=14, glow_expand=1.2)
    icon = Image.alpha_composite(icon, g1)
    icon = Image.alpha_composite(icon, g2)
    d = ImageDraw.Draw(icon)
    draw_aether_symbol(d, cx, cy, scale, GOLD, width_ratio=0.30)
    draw_aether_symbol(d, cx, cy, scale, GOLD_HI, width_ratio=0.14)
    return icon


def make_social(w: int = 1280, h: int = 640) -> Image.Image:
    social = vertical_gradient(w, h, BG_TOP, BG_BOT)
    social = starfield(social, n=140, seed=11)

    sym_cx = w * 0.28
    sym_cy = h * 0.50
    scale_s = h * 0.72 / 9.1

    g1 = glow_layer((w, h), sym_cx, sym_cy, scale_s, GLOW, width_ratio=0.28, blur=26, glow_expand=1.5)
    g2 = glow_layer((w, h), sym_cx, sym_cy, scale_s, GLOW2, width_ratio=0.26, blur=12, glow_expand=1.15)
    social = Image.alpha_composite(social, g1)
    social = Image.alpha_composite(social, g2)
    d = ImageDraw.Draw(social)
    draw_aether_symbol(d, sym_cx, sym_cy, scale_s, GOLD, width_ratio=0.28)
    draw_aether_symbol(d, sym_cx, sym_cy, scale_s, GOLD_HI, width_ratio=0.12)

    title_font = find_font(108, bold=True)
    tag_font = find_font(34, bold=False)
    sub_font = find_font(26, bold=False)

    title = "Aether"
    tx = int(w * 0.52)
    ty = int(h * 0.34)
    d.text((tx, ty), title, font=title_font, fill=TEXT)
    bbox = d.textbbox((tx, ty), title, font=title_font)
    tw = bbox[2] - bbox[0]
    line_y = bbox[3] + 18
    d.line([(tx, line_y), (tx + min(tw, 280), line_y)], fill=ACCENT_LINE, width=3)

    tag = "ECU gauge · logger · remote programmer"
    d.text((tx, line_y + 28), tag, font=tag_font, fill=MUTED)
    sub = "Open-source · ESP32 · FOME / rusEFI / Speeduino"
    d.text((tx, line_y + 78), sub, font=sub_font, fill=(130, 135, 160, 255))

    flat = Image.new("RGBA", (w, h), (*BG_TOP, 255))
    return Image.alpha_composite(flat, social)


def main() -> None:
    icon = make_icon(1024)
    icon_path = OUT / "aether-icon.png"
    icon.save(icon_path, "PNG", optimize=True)
    print("icon", icon_path, icon.size, icon_path.stat().st_size)

    icon512 = icon.resize((512, 512), Image.Resampling.LANCZOS)
    icon512_path = OUT / "aether-icon-512.png"
    icon512.save(icon512_path, "PNG", optimize=True)
    print("icon512", icon512_path, icon512.size)

    social = make_social(1280, 640)
    social_path = OUT / "aether-social-preview.png"
    social.convert("RGB").save(social_path, "PNG", optimize=True)
    print("social", social_path, social.size, social_path.stat().st_size)

    assert social_path.stat().st_size < 1_000_000
    print("done")


if __name__ == "__main__":
    main()
