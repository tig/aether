# esprec element harness (Aether)

Framework for **element-by-element** metal UI work.  
**Not** a full pytest suite yet — same layout future tests (and silico/esprec product helpers) should reuse.

## Specs

- Element order + device scene API: [`specs/face-elements.md`](../../specs/face-elements.md)
- Look: [`specs/afr-face.md`](../../specs/afr-face.md)
- Motion: [`specs/afr-demo.md`](../../specs/afr-demo.md)
- Registry: [`elements.toml`](elements.toml)

## Agent recipe (nail one element)

```text
# Worktree: aether-afr-face; board on COMx; image with face scene + esprec shot
pip install -e ../../esprec

python tools/esprec_elements/capture_element.py --port COM11 --scene banner_afr
# → docs/esprec-captures/banner_afr.png

# Read the PNG. Check only the element checklist in elements.toml.
# Fix face_<element>.c only. Re-capture until good. Then next element order.
```

## Device commands

| Command | Effect |
|---------|--------|
| `face scene <id>` | Freeze demo; apply registry state |
| `face live` | Resume 30 s demo |
| `esprec shot` / `shot` | Emit full-face RGB565 shadow |

## Silico inheritance (intent)

When extracted:

| Piece | Stays product | Moves toward silico/esprec |
|-------|---------------|----------------------------|
| Scene state / ROI / checklist | GCU `elements.toml` | Schema + CLI “run scene → PNG” |
| `face scene` wire | GCU command names | Optional generic `ui scene` pattern |
| Capture integrity | — | esprec protocol / CLI |

Do **not** put Aether AFR ROIs into silico. Put the **harness shape** there later.

## Output paths

Default: `docs/esprec-captures/<scene_id>.png` (local evidence; do not treat as operator product-face accept alone).
