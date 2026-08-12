# Aether AFR screen — face specification

**Rev 1.5 · August 2026**  
**Scope:** The main mixture **page** — experience, **instrument genre**, silhouette, LED brick grammar, **absolute type floors (mm)**, no-overlap layout, and host dual views.  
**Not in scope:** multi-page navigation, SETTINGS/ABOUT, Wi‑Fi — see [pages.md](pages.md); product-wide logging — see [spec.md](spec.md).

**Status:** Implement to match **this experience**. After face changes, prove by *looking* (host dual view, metal capture, or the board) — not by code-only claims.

**Build order / metal capture:** nail **one element at a time** — [face-elements.md](face-elements.md) + `tools/esprec_elements/`. Do not bulk-rewrite the whole face without esprec evidence per element.

Phrase book: [lexicon.md](lexicon.md).

---

## One-line pitch

A pocket wideband face: thick mixture **LED bezel**, one big number with clear units, RPM and throttle under it, and a banner that names what a press does next — built for a glance in the car.

---

## Visual reference

### Metal (prototype 4.3″ — primary truth for this board)

Logical face **800 × 480**. Capture after a stable stoich scene:

![AFR page metal](../docs/images/page-afr.png)

| Fact | Detail |
|------|--------|
| **What this PNG is** | Device framebuffer (esprec) of the **AFR page** on the ship prototype board. |
| **How to use it** | Genre/silhouette and chrome placement must match this *kind* of instrument. |
| **After layout changes** | Re-capture `docs/images/page-afr.png` and update this section. |

Multi-page stills (SETTINGS, ABOUT): [pages.md](pages.md).

### Host mockup (legacy / motion)

**Canonical host motion GIF** (may still show older smaller-panel proportions):

![Aether AFR face host mockup](../docs/images/afr-face-mockup.gif)

| Fact | Detail |
|------|--------|
| **What this GIF is** | Capture from the **core host mockup** — motion and dial genre. |
| **What it is not** | Not a substitute for metal 800×480 layout on the 4.3B board. |
| **After host visual changes** | Re-capture the GIF from the core mockup path. |

Clean-room / alternate mockups are **eval harnesses**. They do not replace metal stills or the core mockup.

### Word-picture of the GIF (when you cannot open the image)

Clean-room and text-only agents: treat this as the silhouette you must hit.

- Full-bleed **black landscape** face; **banner strip on top** (dark blue-slate), not floating chrome in empty space.  
- Under the banner, a **dial zone that owns almost all remaining height until aux** — not a small gauge in a dark room.  
- LED ring **hugs the outer rectangle** of that zone: flush **left and right**, top under the banner, ends at the **bottom-left and bottom-right corners**.  
- LEDs run **up and over only** (left → top → right). **No LEDs across the bottom** between 8 and 20; that bottom span is open so the center and aux can breathe.  
- Center is a **large rounded-rectangular black window** with a huge mixture number (and unit).  
- Below the dial: a clear **aux band** with two **large** numbers (RPM left, TPS right).  
- **Bottom row:** captions **RPM** / **TPS** left and right, and **swipe dots dead-center**, all **flush to the face bottom** with only a **small gap** from the edge — never floating mid-aux.  
- Logging = **red LED** in the banner middle only.

If what you drew is a **semicircle tach floating in black**, you missed this section.

---

## What this screen is for

You’re building a **tiny automotive instrument**, not a phone UI and not a generic round tach widget.

At a glance the operator should know:

1. **How rich or lean** the mixture is — from the dial band *before* they fully parse the digits.  
2. **Which language** the number is in — AFR or lambda, never both at once.  
3. **Engine context** — RPM and throttle — without leaving the page.  
4. **Whether logging is on** — a status light, not a word.  
5. That **this is one page** in a larger product — swipe dots, not full nav chrome ([pages.md](pages.md)).

Simulated data is fine on host and for metal demo; live sources are product-level.

---

## Instrument genre (read before drawing)

### Silhouette checklist (pass/fail in ~10 seconds)

| Must pass | Fail if… |
|-----------|----------|
| Dial zone is a **landscape rectangle** under the banner | Gauge is a circle/semicircle floating mid-face |
| LEDs follow the **outer path L → top → R** of that rectangle | Half-disk sitting on a baseline / open-bottom speedo |
| Inner hole is a **soft-cornered rectangle** | Perfect circle porthole only |
| Segments are **countable thick bricks** with hairline gaps | Smooth pie / continuous paint / sparse ticks |
| Aux is a **second horizontal band** under the dial | Aux floating inside the arc or missing |
| Banner is a **full-width top strip** | Labels floating with no distinct banner field |

**Correct units toggle + wrong silhouette = still fail.**

### What it *is*

- A **landscape full-width LED bezel** that owns the dial region under the banner.  
- The LED channel is a **constant-thickness band** following the dial zone:  
  - **Outer wall = sharp rectangle** of the dial zone (flush L/R, top under banner, bottom at aux).  
  - **Inner wall = rounded rectangle** (generous soft corners) — that is where “radius” lives.  
- **Why this matters (do not miss):** If you round the **outer** wall the same way as the inner, the first and last LEDs pull **away from the geometric corners** and leave empty black triangles at BL/BR. That fails.  
- **Corner fill rule:** The **first** segment (rich / scale **8**) must **include the bottom-left geometric corner** of the dial zone. The **last** segment (lean / scale **20**) must **include the bottom-right geometric corner**. Mid-side and mid-top bricks still **touch** the outer L/R/top edges.  
- **Test:** Zoom the bottom-left corner — you should see **LED paint in the corner pixel region**, not a dark gap between the red brick and the face edge.  
- Softness of the bezel is read from the **inner hole** (and slightly from brick shape), not from floating the whole ring inward.
- Arc is **corner-to-corner via the top**: rich at **bottom-left** corner, lean at **bottom-right**; LEDs climb up and over.  
- **No LED row across the bottom** between the two corners — open under the number.  
- LEDs are **radial wedge bricks**: each segment is a short **arc-shaped bar** whose sides follow rays from the dial center — **not** axis-aligned screen rectangles pasted on a frame.  
- Bricks are solid and **evenly thick** at mid-left, mid-top, and mid-right (constant channel width).  
- **Thin dark hairline** between bricks; unlit bricks stay **visible**.  
- Color first: green healthy mid, amber lean transition, red at rich and lean extremes.

### What it is *not* (wrong genre — reject on sight)

| Wrong | Why it fails |
|-------|----------------|
| **Semicircle / half-disk speedo** in a dark field | Wrong silhouette; wastes the landscape face |
| **Continuous painted pie** or rainbow wedge | Loses LED segment grammar |
| **Round porthole** only, tiny gauge in empty black | Phone-widget energy |
| **Sparse thin ticks** with huge gaps | Looks broken, not hardware |
| **Blurred solid ring** with no segment separation | Loses LED character |
| **Ring inset from the face edges** (empty margin at corners/sides) | Outer wall flush; no floating gutter |
| **Outer path rounded so BL/BR corners are empty black** | Outer wall stays **sharp rect**; only **inner** wall is rounded; first/last bricks own the geometric corners |
| **Sharp-cornered rectangular picture frame** with boxy LED tiles | Outer/inner must feel **rounded**; bricks must be **radial wedges**, not axis-aligned blocks |
| **Dual mixture numbers** (big AFR + companion λ) | Violates one primary truth |
| Right key labeled **SEL** when it means units | Right key is **inverse units** (LAMBDA / AFR) |

### “Wrong successful” (from real clean-room fails)

These looked “done” but were **not this product**:

1. **Dual AFR + λ** companion numbers — hierarchy/interaction wrong.  
2. **Semicircle rainbow tach + round hole** — genre wrong even with a units toggle.  
3. **Pretty dual physical/review host chrome** with the wrong dial shape — still fail acceptance.  
4. **Full-width frame but sharp box + axis-aligned LED tiles** — almost right genre, wrong LED grammar and corner softness (pass-1 clean-room gap vs GIF).  
5. **Rounded LED ring with every segment permanently band-colored (full rainbow strip)** — wrong needle model; must be progressive fill with dim unlit remainder (pass-2 clean-room gap vs GIF).  
6. **Outer channel rounded so corner bricks stop short of BL/BR** — empty black at corners; outer wall must stay a **sharp rect** (pass-5 clean-room gap vs GIF).  
7. **Primary digits drawn over dial scale marks** (e.g. 11/13/15/17 through the mixture number) — **no-overlap rule** fails (pass-6b field gap).  
8. **Swipe dots floating mid-aux** between numbers and captions — dots must sit on the **bottom row** with captions (pass-6b field gap).

### Needle / fill model (how mixture moves)

- Mixture is shown by **how many contiguous LEDs are lit**, starting at the **rich end** (bottom-left) and progressing toward lean (a **progressing arc**, not a random subset).  
- **Critical:** Only the lit prefix is painted in band color (green / amber / red by that segment’s mixture zone).  
- **All remaining segments stay dim-unlit** (same dark gray as “hardware present but off”) — do **not** paint the whole ring as a permanent rainbow of band colors.  
- At stoich (~14.7), roughly the **mid arc** is lit and the lean side is still dim.  
- Stoich neighborhood may keep a **soft highlight** on the relevant segment when not fully lit.  
- Do **not** invent a solid pie fill, a continuous gradient wedge, or a “always-on multicolored LED strip.”

### Relative proportions (intent only — not a pixel recipe)

| Part | Relative intent |
|------|-----------------|
| Banner | Distinct top strip; full width; dark blue-slate vs dial black — tall enough for **readable** MODE / units labels on the ship panel |
| Dial | **Majority** of the face under the banner |
| Aux | About the **lower third** of the face |
| LED channel thickness | **Substantial and even** — about a fifth of the shorter dial half at mid-side **and** mid-top (not thinner on top) |
| LED edge contact | Outer wall = **sharp rect** of dial zone; first/last bricks **own** BL/BR geometric corners |
| Outer corner radius | **None on the outer wall** (sharp zone rectangle). Soft look comes from **inner** rounded-rect. |
| Inner corner radius | **Obviously rounded** — about a third to two-fifths of the aperture’s shorter half |

### Physical scale + absolute type floors (required)

**Prototype ship panel:** 4.3″ IPS, logical face **800 × 480** landscape.  
**mm floors** are the contract (not inventable). Pixel counts scale with the panel; verify on glass.

| Class | What | Min height |
|-------|------|------------|
| **Any text** | Banner labels, dial legends, unit word AFR, aux captions, any other on-face type | **≥ 2.75 mm** |
| **Secondary values** | RPM, TPS / WOT numbers | **≥ 6 mm** |
| **Primary value** | Mixture number (AFR or λ digits) | **≥ 10 mm** |

**Notes**

- “Height” = rendered capital / digit body height; verify on the physical panel.  
- **λ** unit is ~¾ of primary digits and still **≥ 2.75 mm**.  
- Prefer **larger** than floors when space allows; floors are the **minimum**, not the design target.  
- Segment gaps stay **hairline** (thinner than a brick).  
- Primary digits as large as the aperture allows once the floor is met **and** the no-overlap rule holds; monospaced bold.  
- Aux captions **flush bottom** (same bottom row as swipe dots).

### No visual overlap (required)

**No text of any element may overlap visually with any other text or with non-text face chrome that is meant to stay readable.**

| Must not overlap | Examples that fail |
|------------------|--------------------|
| Primary digits × dial scale marks | `16.4` painted through `11` / `13` / `15` / `17` |
| Primary digits × unit tag | Number and **AFR** / **λ** stacked or colliding |
| Dial scale marks × LED bricks | Marks sitting on the bezel paint |
| Secondary numbers × captions | RPM digits through the **RPM** word |
| Captions × swipe dots | **RPM** / **TPS** glyphs through the page dots |
| Banner labels × logging LED | MODE / LAMBDA through the red LED |

**How to pass:** reserve exclusive layout boxes; shrink or re-place the **lesser** element (scale marks sit outside the primary block; unit sits clear of digits; primary may not grow past the free aperture). Changing layout is correct; shrinking below type floors is not.

### Dial scale and non-linearity (intent only)

- Scale marks live **inside** the aperture, never on the LED bricks.  
- They must not kiss the ring — especially side marks.  
- They must not collide with the primary number or unit (see **No visual overlap**).  
- **Language matches units mode**, and **placement follows the LED fill path** (not fixed AFR slots relabeled):  
  - **AFR mode:** marks **8 · 11 · 13 · 15 · 17 · 20** at their fill positions  
  - **Lambda mode:** a λ-native scale (e.g. **0.70 · 0.85 · 1.00 · 1.10 · 1.20 · 1.35**), two decimals; **1.00 must sit on the stoich segment** (same path position as AFR 14.7)  
- Primary mixture digits: AFR **one** decimal (`14.7`); lambda **two** decimals (`1.00`).  
- Arc is **not linear in AFR**: expand the useful midrange; don’t let far rich/lean dominate. Exact control points live in code.

### Logical face size (required, not inventable)

| Item | Value |
|------|--------|
| Prototype logical face | **800 × 480** landscape (4.3B RGB native) |
| Composition | Landscape instrument: banner / dial / aux — not a panoramic strip |

The face **scales** with the panel. Composition and hierarchy are the contract; mm floors always win.

### What you may invent (bounded allow-list)

If implementation needs numbers the prose omits, invent **only** from this list:

| Allowed invent | Guidance |
|----------------|----------|
| Segment count | **Dense** LED ring — about **30–40** segments (not ~12, not ~80) |
| Non-linear map | Compress far rich/lean; expand midrange (e.g. 11 and 17 near bottom corners) |
| Gasoline stoich for display | **14.7** AFR unless product config says otherwise |
| Band thresholds / paint hex | Reasonable green / amber / red; document in code |

**Not inventable:** **mm type floors** (2.75 / 6 / 10), **no visual overlap**, **swipe dots flush bottom**, silhouette, LED path (L–top–R, open bottom, sharp outer wall / soft inner), fill model (progressive lit prefix only), inverse units control, one-number rule, aux placement, operator-owned units.

---

## Orientation and controls

- Product UI is **landscape**.  
- On this prototype, **units control** is a **touch target** (banner right). MODE may remain label-only.  
- Physical hard keys (if present on a future SKU) may mirror MODE / units — do not invent semantics here.  
- Rounded glass **clips** flush edge text. Banner labels sit **inboard** of the corners.

---

## How the face is read (top → bottom)

### Regions (ASCII — structural, not pixel art)

```text
┌────────────────────────────────────────────┐
│  MODE          ● (log)           LAMBDA    │  banner (full width)
├────────────────────────────────────────────┤
│█                                    █      │
│█   dial LEDs: L ── top ── R only    █      │  dial zone (majority height)
│█   8/20 at bottom corners           █      │
│█         [ rounded-rect hole ]      █      │
│█            14.7 AFR                █      │
├────────────────────────────────────────────┤
│     2400                   18% / WOT       │  aux (~ lower third)
│                                            │
│     RPM        ● ○ ○              TPS      │  bottom row: captions + dots flush bottom
└────────────────────────────────────────────┘
```

LEDs do **not** close across the bottom edge under the number.

### Banner — chrome, not content

- **Left:** MODE (reserved).  
- **Center:** logging **LED** — bright red on, dim red off; never gray; no “LOG” word.  
- **Right:** **inverse units** — what a press switches *to*.

| Dial shows | Right label | Press does |
|------------|-------------|------------|
| AFR | **LAMBDA** | Switch to lambda |
| lambda | **AFR** | Switch back to AFR |

### Dial — the hero

See **Instrument genre**. Summary: full-width LED bezel, thick discrete segments, L–top–R path, open bottom, rounded-rect aperture, band color before digits.

### Center — one primary truth

Exactly **one** live mixture number and **one** unit tag beside it.

- Never two mixture numbers at once.  
- Never “AIR/FUEL RATIO” under-text.  
- Under half a second: **band color + that number**.

| Mode | Example | Unit mark |
|------|---------|-----------|
| **AFR** (default) | `14.7` | Word **AFR** (legend class) |
| **Lambda** | `1.0` | Greek **λ** (~¾ digit height) |

Number and unit share the **band color**. Invalid: dashed digits, same layout.

Units switch feels **intentional** (short transition). Right banner label updates to the new inverse.

### Aux — context without leaving

- **RPM** left, **TPS** right — large secondary numbers (glanceable on-device).  
- Captions **RPM** / **TPS** sit on the **bottom row** of the face (left / right), not mid-air under the numbers alone.  
- Secondary numbers sit **above** that bottom row with clear air — **no** digit-through-caption overlap.  
- Partial throttle: percent. Full throttle: **WOT** (distinct blue), not `100%`.  
- High RPM may warn red / flash past redline.

### Swipe (bottom row with captions)

- Three page dots, **always flush to the face bottom** with only a **small gap** from the edge (same bottom band as captions).  
- Dots sit **dead center** on that bottom row; captions stay left / right — **no** caption-through-dot overlap.  
- Page zero = this screen. Hint only — don’t float dots mid-aux between numbers and captions.

---

## Host mockup presentation (required)

Any HTML host mockup that claims this face **must** show **two views of the same logical face**:

| View | Job |
|------|-----|
| **Physical panel size** | Legibility truth — “can I read this in the car?” |
| **Review canvas** | Craft truth — layout, type, gaps, interaction |

Rules:

1. **Same buffer / same draw path** for both — not two divergent layouts.  
2. Physical = **legibility bar**; review = craft inspection.  
3. **Harness chrome** under the canvases (demo, sliders, toggle buttons) is allowed. It is **not** product UI and must not appear on the device face.  
4. Showing only one view = **incomplete** for host acceptance.  
5. Core path: `mockup/gauge.html` (+ SVG twin as needed). Keep **`docs/images/afr-face-mockup.gif`** regenerated from that core path after meaningful visual changes.

Eval mockups should use the same dual presentation when practical.

---

## Type hierarchy (physical size, not zoom)

Judge at **true physical size** (physical host view). **Absolute mm floors above are mandatory.** Hierarchy (largest → smallest intent) once floors are met **and no overlap remains**:

1. **Mixture value** — **≥ 10 mm**; grow further only while scale marks + unit stay clear.  
2. **λ unit** — ~¾ of primary, **≥ 2.75 mm**.  
3. **RPM / TPS numbers** — **≥ 6 mm**.  
4. **Legends / captions / banner labels / word AFR** — **≥ 2.75 mm**; captions on the **flush-bottom** row with swipe dots.  

Fonts: bold digits for live numbers; clean sans for units, legends, banner.  
If product-wide floors in [spec.md](spec.md) are lower, **these mm floors win** on this face.

---

## Interaction

| Input | Behavior |
|-------|----------|
| **Units control (banner)** | Tap toggles AFR ↔ lambda; inverse label names the *next* language. Operator-owned — demo **must not** force a toggle that fights the operator. |
| MODE label | Reserved / label only on this board unless hard keys exist |
| Swipe L/R | Change page; dots update ([pages.md](pages.md)) |
| Tap swipe dots | Jump to page |

**Touch reliability (requirements):**

- Units control **must** respond to a normal finger tap on glass.  
- Page swipe **must** be reliable; prefer a **proven toolkit** page/gesture path over bespoke swipe code.  
- Taps on units and dots **must not** require perfect stillness; short moves **must not** always become a page change.

**Scripted drive demo** (30 s story): [afr-demo.md](afr-demo.md) — host and metal.

---

## Draw order

Face black → dial segments → dial legend + value + unit → aux → banner → labels + LED → swipe dots.

---

## Acceptance (this screen)

**Genre first:** wrong silhouette fails even if toggle works.

- [ ] **Word-picture / silhouette checklist** pass (full-width bezel, L–top–R LEDs, open bottom, rounded-rect hole, aux band)  
- [ ] Discrete thick segments + hairline gaps; unlit visible; contiguous fill from rich end  
- [ ] LED channel **reaches** L/R/top edges and bottom **corners** (no corner gutters)  
- [ ] Scale marks inside aperture, clear of ring; extremes at bottom corners  
- [ ] Banner: log LED only; MODE + inverse LAMBDA/AFR **≥ 2.75 mm**, clear of rounded glass  
- [ ] Primary mixture digits **≥ 10 mm** + unit (**≥ 2.75 mm**); no dual numbers; no AIR/FUEL under-text  
- [ ] **No visual overlap** — primary vs scale marks, primary vs unit, captions vs dots, etc.  
- [ ] Right units control inverse; tap switches language; dial legends + primary precision match mode (AFR 1 dp / λ 2 dp)  
- [ ] RPM/TPS **≥ 6 mm**; captions **≥ 2.75 mm** on bottom row; WOT at full throttle  
- [ ] Swipe dots **flush bottom** (small gap), center, same row as captions — not mid-aux  
- [ ] **No on-face text under 2.75 mm**; judge at physical panel size  
- [ ] Metal still matches genre of `docs/images/page-afr.png`  

- [ ] **Host:** dual physical + review when host claims this face; GIF optional if metal stills are current  
- [ ] Mapper/unit tests green where they exist; visual capture or board inspect done  

---

## Where numbers and code live

This document is **UX + genre contract**. Geometry constants, arc control points, segment counts, and paint hex live in:

| Concern | Owner |
|---------|--------|
| Experience + genre (this file) | `specs/afr-face.md` |
| Phrase book | `specs/lexicon.md` |
| Product mission / HW | `specs/spec.md` |
| AFR → segments / bands | `mockup/afr_gauge.py` + metal twin |
| **Metal still (AFR)** | `docs/images/page-afr.png` |
| Multi-page / SETTINGS | `specs/pages.md`, `docs/images/page-settings.png` |
| **Core host visual** | `mockup/gauge.html` / capture → `docs/images/afr-face-mockup.gif` |
| Eval / clean-room | e.g. `mockup/spec-from-prose/` — not product truth |

When intent and implementation disagree: fix the implementation, re-capture **metal stills** (and host GIF if host still claims the face) — do not redefine the product from a wrong-genre experiment.
