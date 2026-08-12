# Aether AFR screen — drive demo specification

**Rev 0.2 · August 2026**  
**Scope:** The **scripted drive demo** that exercises the AFR face with simulated drive data (RPM, throttle, mixture, logging). Applies to **host mockup** and **metal** when a demo loop is claimed.  
**Not in scope:** live ECU protocols; capture tooling internals; page/Wi‑Fi config ([pages.md](pages.md)).

**Status:** Any build that claims a “demo” of this face must meet **this** contract. The face look itself is [afr-face.md](afr-face.md). Phrase book: [lexicon.md](lexicon.md).

---

## Why this exists

Operators and agents judge the face by **watching it move**. A static stoich frame is not a demo. A short triangle sweep of AFR alone is not a demo. The demo must feel like a **short drive story** so you can see:

1. Car off / invalid mixture  
2. Idle and light load  
3. Pull and shifts  
4. **WOT** and redline stress on aux + band color  
5. Cruise back toward stoich  
6. Logging LED activity  

---

## Hard requirements (not inventable)

| Rule | Detail |
|------|--------|
| **Loop length** | Exactly **30 seconds**, then **seamless loop** (no stop, no blank). |
| **What moves** | At least **AFR** (or invalid), **RPM**, **TPS** (incl. **WOT**), **logging LED**. |
| **Face paint** | Same draw path as live harness — demo only feeds **state**, it does not own a second layout. |
| **Auto-run** | Host: opening the page starts the demo unless paused. Metal: demo may run on boot for prototype. |
| **Units are operator-owned** | Demo **must not** auto-toggle AFR ↔ lambda. Banner tap (or host scene) owns units. |
| **Multitask** | While the operator is on SETTINGS or ABOUT, sensor demo **must** keep advancing (instrument does not freeze). |
| **Harness only** | Demo chrome (host buttons, t= readout) is **not** product UI and must not appear on the device face. |

Exact sample equations are **allow-list invent** as long as the **phases and acceptance** below hold.

---

## Drive story (phases)

Times are **seconds into the 30 s loop** (t ∈ [0, 30)). Intent is fixed; edges may ease ±0.3 s.

| Phase | t (s) | Operator should notice |
|-------|-------|------------------------|
| **Off** | 0 → ~2 | RPM **0**, TPS **0**, mixture **invalid** (dashed / empty needle — not a fake 14.7 “good”). Logging **off**. |
| **Crank / fire** | ~2 → ~3.2 | RPM climbs from 0; AFR appears and moves richward from lean-ish crank. Logging **on** from ~2 s onward for the rest of the loop. |
| **Idle settle** | ~3.2 → ~5.5 | RPM settles near **idle (~750)**; AFR near stoich with small wander. |
| **Pull 1→2** | ~5.5 → ~8 | TPS rises; RPM builds then dips on a shift; AFR goes **richer** under load. |
| **2nd WOT to redline** | ~8 → ~11.2 | TPS = **WOT**; RPM runs to **redline (~6200)** with limiter chatter at the top; AFR rich. |
| **Shift 2→3** | ~11.2 → ~12 | Still WOT; RPM drops for the gear. |
| **3rd WOT hold** | ~12 → ~17 | Full throttle held ~**5 s**; RPM climbs in gear; rich AFR. |
| **Cruise** | ~17 → 30 | TPS falls toward light cruise; RPM ~**2400**; AFR returns toward **~14.7** stoich; loop restarts. |

**Redline / warn:** RPM near or over redline should use the face’s warn/flash treatment (see face aux rules). **WOT** label (not `100%`) when throttle is pegged.

---

## Units (not demo-owned)

- Default language at cold start may be **AFR**.  
- Demo **must not** change units during the loop.  
- Operator (or host `face scene`) owns AFR ↔ lambda.  
- Banner units control stays **inverse** of the dial language.

---

## Acceptance (demo)

- [ ] Loop is **30 s** and **repeats** without manual restart  
- [ ] Off phase shows **invalid** mixture, not a confident stoich reading  
- [ ] Idle, pull, **WOT**, redline, cruise are all **visibly distinct** in RPM/TPS/AFR  
- [ ] Logging LED is off only in the early off window, then on  
- [ ] Units stay operator-owned (no forced mid-loop flip)  
- [ ] Sensors keep updating if the operator is on SETTINGS/ABOUT  
- [ ] Dual host views (if present) both track the same demo state  

---

## Where it lives

| Concern | Owner |
|---------|--------|
| Demo story + hard rules (this file) | `specs/afr-demo.md` |
| Face look / type / silhouette | `specs/afr-face.md` |
| Pages / multitask | `specs/pages.md` |
| Core host reference | `mockup/gauge.html` |
| Metal board demo | Same phase table on prototype firmware |

---

## What you may invent

| Allowed invent | Guidance |
|----------------|----------|
| Sample math / easing | Smoothsteps, sines for wander, exact lerp edges |
| Redline number | ~**6200** unless product config says otherwise |
| Tick rate | ~**20–180 ms** paint is fine; feel continuous |
| Extra demo buttons | Pause, restart, scrub — optional harness |

**Not inventable:** **30 s** loop length, full drive **story** (off → idle → pull → WOT/redline → cruise), invalid when off, logging story, auto-run (or equivalent full loop), operator-owned units.
