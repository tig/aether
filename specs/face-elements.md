# Aether AFR face — element map (build + capture)

**Rev 0.1 · July 2026**  
**Scope:** How to **build and verify** the AFR face **one element at a time**, with host **esprec** as agent eyes.  
**Parents:** [afr-face.md](afr-face.md) (look), [afr-demo.md](afr-demo.md) (motion).  
**Not in scope:** full pytest suite yet — this doc + `tools/esprec_elements/` are the **framework** those tests will inherit.

---

## Why element-by-element

Bulk UI rewrites failed esprec checks (ghosted aux, messy marks) and buried which layer broke.  
**Rule:** nail **one** element to esprec “good,” freeze its contract, then open the next.

| Principle | Detail |
|-----------|--------|
| **Modular firmware** | One module (or clear API) per element; root only orchestrates |
| **Known scene** | Device can enter a **named scene** so captures are comparable |
| **esprec evidence** | PNG of the logical face (or ROI later); agent reads pixels, not source folklore |
| **Silico inheritance** | Scene registry + capture recipe shape is reusable; product owns ROIs and “good” |

---

## Element order (build sequence)

Work **in this order**. Do not polish later elements until earlier ones pass their scene capture.

| # | Element id | Owns | Freeze scene (examples) |
|---|------------|------|-------------------------|
| 1 | `banner` | Top strip: MODE, log LED, inverse LAMBDA/AFR | `banner_afr`, `banner_lambda`, `banner_log_on` |
| 2 | `dial` | LED bezel L→top→R, open bottom, scale marks 8…20 | `dial_off`, `dial_stoich`, `dial_rich` |
| 3 | `primary` | Mixture digits + unit (AFR / λ) | `primary_stoich_afr`, `primary_lambda`, `primary_invalid` |
| 4 | `aux` | RPM + TPS/WOT numbers | `aux_idle`, `aux_wot`, `aux_redline` |
| 5 | `chrome` | Captions RPM/TPS + swipe dots flush bottom | `chrome_page0` |
| 6 | `compose` | Full AFR face + 30 s demo | `demo_loop` (afr-demo.md) |
| 7 | `pages` | Multi-page shell: SETTINGS, ABOUT, nav | metal stills `docs/images/page-*.png` ([pages.md](pages.md)) |

**Done for an element:** modular code path exists + at least one esprec PNG under a known scene looks right for that element (others may be stub/minimal).

---

## Device API (scenes)

Host may inject (serial, CR/LF framed), same path as `identity` / `esprec shot`:

```text
face scene <scene_id>
face element <element_id>     # optional: dim non-focus layers (future)
face live                     # resume afr-demo loop
```

`face scene` **stops the demo clock** and applies a fixed `afr_face_state_t` (and any element flags).  
Then: `esprec shot` / host `esprec snapshot`.

Exact scene table: `tools/esprec_elements/elements.toml`.

---

## Capture contract (framework; tests later)

| Step | Who | Action |
|------|-----|--------|
| 1 | Host | Open serial **once** (DTR/RTS low — esprec default) |
| 2 | Host | `face scene <id>\n` |
| 3 | Host | Settle ≥1 frame (~100–200 ms product tick) |
| 4 | Host | `esprec snapshot --port … -o <path>` |
| 5 | Agent | Read PNG; check element checklist only |

**Later tests** (not required yet) will assert ROI hashes / SSIM / structural probes against golden stills. The **registry + scene + path layout** must already match what those tests will use.

```text
tools/esprec_elements/
  elements.toml          # element + scene registry (normative for harness)
  capture_element.py     # one-shot: scene → PNG (skeleton OK)
  README.md              # agent recipe
docs/esprec-captures/    # gitignored or product stills; scene-named files
  banner_afr.png
  …
```

---

## Firmware module map

```text
firmware/main/
  afr_face.h / afr_face.c     # thin public API (init / update / handler / scene)
  face/
    face_state.h              # shared state + scene ids
    face_root.c               # layout + call order
    face_banner.c/.h
    face_dial.c/.h
    face_primary.c/.h
    face_aux.c/.h
    face_chrome.c/.h
  afr_map.*                   # pure mixture → segments / colors
  afr_demo.*                  # 30 s drive (compose only)
```

Root draw order (afr-face.md): face black → dial → primary → aux → banner → chrome (captions/dots).

---

## Relationship to host mockup

`mockup/spec-from-prose/` remains the **prose clean-room** host twin.  
Metal elements should **match the same element ids and scenes** so host and metal evidence share names. Pixel-perfect parity is not required; **genre + floors + no-overlap** are.

---

## Spec gaps to clarify (running list)

See [friction-and-spec-notes.md](../docs/friction-and-spec-notes.md) (compound log). High-signal candidates:

- Explicit **element freeze / scene** as first-class acceptance for metal UI work  
- esprec **ROI** vs full-face in afr-face acceptance  
- Lambda glyph (**λ** vs **L**) when default fonts lack Greek  
- LVGL: ban `transform_scale` on frequently updated labels (or require opaque clip box)
