# Aether AFR product face — reimplementation spec

**Rev 0.2 · July 2026**  
**Status:** Host mockup is the source of truth for this face. Implement on metal later; do not invent a second layout.

This document is written so an agent with no prior session can rebuild the face.  
Phrase book: [lexicon.md](lexicon.md). Product seed: [../spec.md](../spec.md).  
Reference implementation: `mockup/` (Python mapper + SVG + HTML canvas).

---

## 1. Goal (what “good” looks like)

A landscape **wideband-style AFR face** on a tiny AMOLED:

- Operator reads **value** at a glance (large red digits, one decimal).
- **Dial** segments fill low→high with green / amber / red bands; **dial legend** marks 8–20.
- **Banner** names physical **MODE** / **SEL** and shows **logging** via a **status indicator** (no text on the LED).
- **Swipe indicator** hints at more pages; page 0 is the AFR face.

Not a pixel clone of a commercial 52 mm gauge. Not live OBD/CAN in this pass — simulated AFR is fine for host mockups.

---

## 2. Hardware orientation

| Item | Spec |
|------|------|
| Board class | ESP32-S3 1.8″ AMOLED (ASIN B0F242GFHK / ESP32-S3-Touch-AMOLED-1.8) |
| Native panel pixels | **368 × 448** (portrait sensor orientation) |
| Product UI pixels | **448 × 368** landscape |
| Rotation rule | Hold so **USB + two hard buttons** are on the **top** edge (former “right tall side” becomes top) |
| Hard buttons | Physical keys beside USB (PWR/BOOT-class). On-screen **MODE** / **SEL** are **labels only**, not touch targets |

Host prototype: render at ~**true physical size** of the 1.8″ panel (≈ **1.391 in × 1.143 in** landscape at CSS 96 px/in), not full-window scale.

---

## 3. Lexicon (mandatory names)

Use these exact multi-word terms. Do not invent short forms.

| Term | Role |
|------|------|
| **banner** | Top strip: button labels + status indicators; distinct background |
| **dial** | Multi-segment LED ring + rounded-rect aperture |
| **button labels** | MODE (left), SEL (right) |
| **dial legend** | 8, 11, 13, 15, 17, 20 inside the aperture |
| **value** | Large AFR numeric (e.g. `14.7`) |
| **value legend** | `AIR/FUEL RATIO` under the value |
| **swipe indicator** | Page dots at bottom of face |
| **status indicators** | Logging LED (and future LEDs) |

---

## 4. Face layout (device pixels, 448×368)

Coordinate origin: **top-left**. +X right, +Y down.

```
Y=0  ┌────────────────────────────────────────────┐
     │  MODE          ● (log LED)           SEL   │  ← banner (H = 60)
     ├────────────────────────────────────────────┤
     │ ████████  dial segments (full width) █████ │
     │ ██                                    ██  │
     │ ██     dial legend   value            ██  │
     │ ██                 value legend       ██  │
     │ ██  8                          20     ██  │
     │ ████████ (to face bottom)         █████ │
     │              ● ○ ○  swipe indicator       │  ← overlay, not a dead strip
Y=H  └────────────────────────────────────────────┘
```

### 4.1 Regions

| Region | Geometry (px) |
|--------|----------------|
| Face | `W=448`, `H=368` |
| **Banner** | `y ∈ [0, BANNER_H)`, `BANNER_H = 60` |
| **Dial outer** | Rectangle filling **full width** and **all height under banner to bottom**: `x ∈ [0,W]`, `y ∈ [BANNER_H, H]` |
| **Swipe indicator** | Overlay near bottom: center y ≈ `H - 14` (does **not** shrink the dial) |

### 4.2 Dial outer / inner geometry

Center of dial content band:

```
cx = W / 2
cy = BANNER_H + (H - BANNER_H) / 2
outer_half_w = W / 2                    # 224
outer_half_h = (H - BANNER_H) / 2       # 154
```

**Constant band thickness** (mid-side width equals mid-top height):

```
BAND_FRAC = 0.154                       # 0.14 × 1.1
band = min(outer_half_w, outer_half_h) * BAND_FRAC
inner_half_w = outer_half_w - band
inner_half_h = outer_half_h - band
inner_corner = min(inner_half_w, inner_half_h) * 0.253   # 0.22 × 1.15
```

- **Outer edge:** sharp axis-aligned rectangle (flush L/R of face; flush top of dial under banner; flush bottom of face).
- **Inner edge:** **rounded rectangle** aperture with half-sizes above and corner radius `inner_corner`.
- Raycast each angle from `(cx,cy)` to outer and inner boundaries to build segment polygons.

Angle convention for rays (screen space):

```
x = cx + r * cos(a)
y = cy - r * sin(a)     # a = 0 → right; a = π/2 → up
```

Outer ray length to rectangle:  
`r = min( outer_half_w/|cos a| , outer_half_h/|sin a| )` (with care at axis zeros).  
Inner: ray to rounded rect (flat sides + far arc of corner circles).

### 4.3 Dial arc (segments)

| Parameter | Value |
|-----------|--------|
| **Segment count** | **35** (not 36) |
| **Start** | Bottom-left **corner** of outer rect |
| **End** | Bottom-right **corner** of outer rect |
| **Path** | Via the **top** (long way around) |

Corner angles (same convention as rays):

```
start_deg = degrees(atan2(-outer_half_h, -outer_half_w))   # normalize to [0,360) if needed → ~214.5°
end_deg   = degrees(atan2(-outer_half_h,  outer_half_w))   # ~-34.5°
sweep_deg = start_deg - end_deg                            # ~249°
```

Segment `i` (`i = 0 .. 34`) spans:

```
a0 = radians(start_deg - (i / n) * sweep_deg)
a1 = radians(start_deg - ((i + 1) / n) * sweep_deg)
```

Small angular gaps between segments (~0.012 rad) for LED separation.

**Fill (needle):** light segments `0 .. lit_count-1` for rising AFR (low left → high right).  
**Unlit segments:** still drawn — dim but **visible** on black (`#2e2e36`), not black-on-black.

### 4.4 Stoich mark

Segment whose range contains **14.7** stays **softly highlighted** when not fill-lit (fill `#2a4a32`, optional edge `#3d6b48`).

---

## 5. AFR mapping (pure logic, no display)

Portable rules (see `mockup/afr_gauge.py`):

| Symbol | Value |
|--------|--------|
| `AFR_MIN` | 8.0 |
| `AFR_MAX` | 20.0 |
| `AFR_STOICH` | 14.7 |
| `SEGMENT_COUNT` | 35 |

### 5.1 Color band of an AFR sample

| Condition | Band |
|-----------|------|
| `afr < 8` or `afr > 20` | **invalid** |
| `afr < 11.5` | **red** (rich) |
| `11.5 ≤ afr < 15.0` | **green** (good / stoich) |
| `15.0 ≤ afr < 15.8` | **amber** |
| `afr ≥ 15.8` | **red** (lean) |

### 5.2 Fixed segment colors

Each segment index `i` has a **fixed** band from its midpoint AFR:

```
mid = AFR_MIN + (i + 0.5) * (AFR_MAX - AFR_MIN) / n
band = band_for_afr(mid)   # always in-range for mids
```

Lit color by band:

| Band | Lit hex | Unlit |
|------|---------|--------|
| green | `#22c55e` | `#2e2e36` |
| amber | `#f59e0b` | `#2e2e36` |
| red | `#ef4444` | `#2e2e36` |

### 5.3 Lit count

```
display = clamp(afr, AFR_MIN, AFR_MAX)
t = (display - AFR_MIN) / (AFR_MAX - AFR_MIN)
lit_count = floor(t * n) + 1     # in 1..n
lit_indices = 0 .. lit_count-1
```

### 5.4 Value string

- Valid: one decimal, e.g. `14.7`
- Invalid: `--.-`
- Out-of-range samples: still clamp for needle; mark invalid for readout/band

---

## 6. Typography and placement (device px)

Let `half = min(inner_half_w, inner_half_h)`.

| Element | Size rule | Color | Placement |
|---------|-----------|--------|-----------|
| **Button labels** | `0.42 * BANNER_H` (min ~16) | `#e8eef8` | Banner: MODE left (~x=22), SEL right (~x=W−22), vertically centered in banner |
| **Status LED** | radius ~9 | See §7 | Banner center |
| **Dial legend** | `0.24 * half` (min ~14) | `#d0d0d8` | **Inside** aperture: `r = inner_r(a) − ~0.85*label_px` (not on LED band) |
| **Value** | `min(1.148*half, 0.95*half_aperture)` ≈ large red | `#ff2a2a` | See block layout below |
| **Value legend** | `0.18 * half` (min ~12) | `#c0c0c8` | Under value |

### 6.1 Value + value legend block

Treat value + gap + value legend as one vertical block:

```
value_gap ≈ 0.18 * digit_px
block_h = digit_px + value_gap + caption_px
center_nudge = 0.18 * min(inner_half_h, half)   # push block downward in aperture
digit_y = cy - block_h/2 + digit_px/2 + center_nudge
caption_y = digit_y + digit_px/2 + value_gap
```

Font: bold monospace for **value**; semibold sans for legends/labels.

Dial legend marks: **8, 11, 13, 15, 17, 20** at AFR-proportional angles along the same arc as segments.

---

## 7. Banner and status indicators

### 7.1 Banner chrome

| Property | Value |
|----------|--------|
| Height | 60 px |
| Background | `#1a2433` (visually distinct from dial black `#050508`) |
| Bottom edge | 1 px line `#2a3a52` |
| Label ink | `#e8eef8` (must stay legible on banner) |

### 7.2 Logging LED (status indicator)

| State | Look |
|-------|------|
| **On** | Bright red `#ff3232`, soft glow/pulse |
| **Off** | **Dim red** still (not gray): fill `#5a1818`, soft dark red halo — readable as “red LED off” |

Centered in banner between button labels. **No text** next to the LED on the device face.

Host prototype demo: start **off**, turn **on** after ~2 s of sim loop (optional).

---

## 8. Swipe indicator

- **3** dots (page 0 = AFR face; 1–2 placeholders OK for now)
- Active: larger light fill `#e8e8ee`
- Idle: smaller `#3a3a44`
- Horizontal center; y ≈ `H - 14`
- Drawn **on top of** the dial (no reserved dead band that shrinks the dial)

Touch (host mockup): horizontal swipe changes page. Physical device: same intent later.

---

## 9. Interaction map

| Input | Behavior |
|-------|----------|
| Physical MODE | Product-defined later (banner label only on mockup) |
| Physical SEL | Product-defined later (banner label only on mockup) |
| Logging | Status LED only; no “LOG” text on face |
| Swipe L/R | Next/prev page via swipe indicator |

Do **not** implement MODE/SEL as on-screen touch buttons in the product face.

---

## 10. Layers / z-order

1. Face black background  
2. Dial segments (outer→inner polygons)  
3. Dial legend, value, value legend  
4. Banner rectangle + edge  
5. Button labels + status LED  
6. Swipe indicator  

---

## 11. Host verification (agents)

After any layout change:

```text
python -m pytest mockup/tests -q
python -m mockup.capture          # needs ImageMagick `magick`
# Open mockup/out/preview_stoich.png (and rich/lean/log_off) and inspect visually
```

Do **not** claim the face is correct from code alone.  
HTML prototype: `mockup/gauge.html` (physical CSS size).  
SVG twin: `python -m mockup` → `mockup/out/afr_gauge.svg`.

### Acceptance checklist

- [ ] Landscape 448×368; banner distinct color; MODE / LED / SEL legible  
- [ ] Dial fills width and height under banner to bottom  
- [ ] 35 segments; 8 and 20 at bottom corners  
- [ ] Mid-side band thickness equals mid-top band thickness  
- [ ] Unlit segments visible; stoich soft-highlight when not lit  
- [ ] Dial legend inside aperture; value large; value legend under value  
- [ ] Value + value legend sit low/centered in aperture (not stuck under top legend)  
- [ ] Logging LED bright vs dim red  
- [ ] Swipe dots overlaid at bottom  
- [ ] Unit tests pass for pure AFR→segment mapping  

---

## 12. Out of scope (this face rev)

- Live CANbus / OBD / sensor input  
- Durable trip log storage UI  
- Full multi-page product domains (MONITOR/LOGGER are placeholders)  
- Pixel-perfect commercial gauge chrome (MODE/SEL knobs, packaging art)  

---

## 13. Implementation map (this repo)

| Concern | Owner |
|---------|--------|
| Pure AFR → lit segments / bands | `mockup/afr_gauge.py` |
| Layout constants + SVG | `mockup/run.py` |
| Interactive HTML prototype | `mockup/gauge.html` |
| PNG capture for agents | `mockup/capture.py` |
| Unit tests | `mockup/tests/test_afr_gauge.py` |
| Lexicon | `specs/lexicon.md` |
| This face contract | `specs/afr-face.md` |

When porting to C / AMOLED: keep this geometry and lexicon; replace host canvas with the panel framebuffer. Do not soft-fork a second face design in chat-only recovery.
