# AGENTS.md - C / ESP-IDF GCU

Guidance for AI coding agents in **this product repo** (language=c plate).

## FIRST ACTION (first ship / getting started) — do this before any status dump

When the human says *follow silico getting started* (or first ship / Day 1):

0. **Open the silico spine AGENTS** (local `../silico/AGENTS.md` or raw `https://raw.githubusercontent.com/tig/silico/main/AGENTS.md`). The GitHub README/homepage alone is **not** the agent playbook.
1. **Do not** open with tooling narration, `bedside init`, vendoring `third_party/`, PR strategy, or a start-gate chooser.

```text
# TURN 1 — 0a only: silico welcome, paste skeleton + "reply ok/go", END TURN (no picker)
# TURN 2 — after any short reply: open chooser FIRST (not free-text "shall I open the gate?")
bedside ask --id start-first-ship --prompt "Start first ship on this machine?" --choices yes,adjust --default yes
# host picker: same id/prompt/choices only — never invent Go / Host-only / Look around
```

2. **0b** = structured chooser on the turn after 0a. Do not leave a free-text cliff after orientation. Full silico AGENTS (not a fetch digest). One short question; **yes** / **adjust** only.
3. **Decline / exit 10:** halt writes; short re-gate or stop.
4. **After go:** plate / sibling silico paths for manners pin — not pre-go vendor.

Full playbook: silico root `AGENTS.md` FIRST ACTION.

## Spine

Host path comes from **silico** (https://github.com/tig/silico). Pin as host-only.
Device `firmware/` never imports silico.

This plate uses **ESP-IDF** deploy (`silico deploy` → `idf.py build` + flash), not mpremote file copy.
Host gate is **CMake + CTest**, not pytest (unless you add Python tests separately).

Operator manners: **Bedside** via `bedside.toml` (sibling silico vendor paths). Domain notes: `BEDSIDE.md`.

## Spec quality

If product `spec.md` is way under-specified or contradictory, follow silico root **Spec interview mode** (`silico/knowledge/spec-interview.md`). Interactive path (build while the spec improves; re-run later) is valid. Do not invent domain moat. Product truth is **this** checkout + the operator.

### Writing mode

- **`specs/**`, `install/**`, procedures, acceptance checklists:** Technical literature (STE bias). See machine guide `writing-in-tigs-voice.md` → *Technical literature (STE bias)*. Prefer lexicon Preferred terms. Short active sentences. **must** / **must not**. No first-person story in requirement bodies.
- **README vision / product story:** Narrative (Tig voice). Do not rewrite vision into STE.

## Host gate

```text
cmake -S host -B build/host
cmake --build build/host --target host_test
silico gate
silico product-path
```

Plate ships `.github/workflows/ci.yml` that on `push` / `pull_request`:
checks out this GCU and **sibling** `tig/silico`, runs **cmake host_test**, then
**`silico gate`** (include hygiene + `[host].gate`). Still run
`silico product-path` locally when claiming a full host path.

## Metal

```text
silico doctor
silico wait-device
silico inspect --port COMx
# confirm board, then:
silico deploy --port COMx
# after operator yes:
silico deploy --port COMx --yes --verify
```

ESP-IDF must be installed (`idf.py` or `IDF_PATH`). First flash and update flash are the same image path.

## HAL seam

Portable domain under `include/` + `src/` must not include freertos / esp_* / driver headers.
Only stems listed in `[hal].allow_device_headers` (default `hal_board`) may touch device headers.

### Time is int64_t milliseconds

The HAL clock hook is `int64_t now_ms` (see `include/gcu/hal.h`). On ESP32
(ILP32) `long` is **32 bits**: millisecond math in `long`/`int` overflows in
under 10 hours and wraps at ~24.8 days. Host `long` is 64-bit, so host tests
only catch this if they seed the clock past 2^31 — `host/test_time.c` does
exactly that; keep that seed when you extend the domain.

## ESP-IDF environment gotchas

- If the agent/GCU **venv is on PATH ahead of the IDF python env**, `idf.py`
  resolves the wrong interpreter and fails on missing packages. Deactivate or
  strip the venv from PATH before `. $IDF_PATH/export.sh`.
- An existing install is usually recorded in `~/.espressif/idf-env.json` —
  `silico doctor` reads it; check before installing another IDF.
- More: `silico/knowledge/macos-codex-esp-idf.md`.

## Identity (required on the link)

**Boot-print alone is not enough** for `silico inspect` after a greeting or banner scrolls past (#78 / #79). The image **must answer** the host word `identity` (CR/LF framed) with:

```text
fw_name=AETHER fw_version=0.0.1
```

Plate `main.c` shows the pattern: print once at boot **and** respond when the host knocks. A boot-print-only app is invisible to inspect as soon as the banner is gone.

Escape hatch (`repl` / `reboot`) is a product requirement for reclaim without hard reset when possible.

## Cursor Cloud specific instructions

Scope of the cloud dev environment is the **host path** only: C host gate, the AFR mockup, the software sim bench, and `silico gate`. The **metal / ESP-IDF** path (`firmware/`, QEMU twin, `silico deploy`) is not provisioned. There is no `idf.py`, no board, and no serial device, so device flash and QEMU steps do not run here.

Python lives in a repo-root virtualenv at `.venv` (gitignored). The VM ships `python3` but no `python`, so run tools through the venv: `.venv/bin/python`, `.venv/bin/pytest`, `.venv/bin/silico`. The README/`install/` docs write `python`; substitute `.venv/bin/python`. The venv is recreated by the startup update script, so a plain `pip install` outside it does not stick.

`silico` (and `bedside`) are installed editable into `.venv` from a clone at `~/silico` (there is no writable sibling `../silico` here, `/` is read-only). `silico gate` and `silico product-path` work from the repo root as-is and do **not** need the `bedside.toml` sibling paths in this layout.

Host commands (already documented in `README.md` "Host gate" / "Software bench" and `install/README.md`), run from the repo root:

- C gate: `cmake -S host -B build/host` then `cmake --build build/host --target host_test` (3 ctest cases). `silico gate` runs include-hygiene plus this same build.
- AFR mockup: `.venv/bin/python -m mockup` (writes `mockup/out/`), tests `.venv/bin/pytest mockup/tests -q`.
- Sim bench: `.venv/bin/pytest sim/tests -q` and `.venv/bin/python -m sim.orch all --out sim/out`. The `test_c_ecu_tcp_bench` case auto-builds/uses `build/host/ecu_tcp_bench`, so keep the C build configured.

Visual gauge check: `python -m mockup.capture` needs ImageMagick `magick`, which is **not** installed, and its `--html` path only knows Windows browser locations. To eyeball the face, render `mockup/gauge.html` with the VM's headless Chrome: `google-chrome-stable --headless=new --disable-gpu --no-sandbox --screenshot=out.png --window-size=900,700 file:///workspace/mockup/gauge.html`. The page runs a ~30s scripted drive demo, so a single screenshot at load time shows the idle `AFR --.-` frame, use a video/live view to see it animate.
