# Aether lexicon

Canonical names for product and face UI. Use these in agent prose, specs, and mockup
code comments — do not invent nicknames.

Product requirements: [spec.md](spec.md). AFR screen: [afr-face.md](afr-face.md).

| Term | Meaning |
|------|---------|
| **banner** | Top strip above the dial: holds **button labels** and **status indicators**; visually distinct background from the dial face. |
| **dial** | The multi-segmented LED gauge ring (outer segments + rounded inner aperture). Segments run **corner-to-corner** (scale **8** and **20** at the bottom corners). |
| **button labels** | On-screen **MODE** / **SEL** text naming the physical hard keys (not touch targets). |
| **dial legend** | Scale marks on the dial: **8 · 11 · 13 · 15 · 17 · 20** (inside the aperture, not on the LED segments). |
| **value** | The large numeric **AFR** readout (e.g. `14.7`). |
| **lambda** | Companion **λ** number to the right of the value (AFR ÷ stoich, e.g. `1.00`), about **75%** of the value size. Same color as the value. |
| **value legend** | *(removed from AFR face)* Formerly `AIR/FUEL RATIO` under the value — do not restore as small under-text; use **lambda** instead. |
| **aux readouts** | Secondary live numbers below the dial: **RPM** (left) and **TPS** (right), each with its own small legend under the number. |
| **swipe indicator** | Page dots at the bottom of the face (swipe left/right between pages). |
| **status indicators** | Non-text status chrome (e.g. the logging red LED). |

Related layout: landscape **448×368** product UI; native panel **368×448**; hard buttons on the top edge with USB.
