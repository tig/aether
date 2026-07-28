"""Pure AFR gauge mapping and simulated stream (no display I/O).

Canonical product-face learning logic for Aether's host mockup.
Scale 8–20, LED-style arc segments, green/amber/red bands.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum
from typing import Iterator, List, Optional, Sequence

# --- Shipped scale / geometry defaults (also documented in spec.md) ---

AFR_MIN = 8.0
AFR_MAX = 20.0
AFR_STOICH = 14.7
SEGMENT_COUNT = 36

# Band thresholds (AFR). Inclusive lower bound for each named band check.
BAND_RICH_RED_LT = 11.5
BAND_GREEN_LT = 15.0  # includes stoich ~14.7
BAND_AMBER_LT = 15.8
# >= BAND_AMBER_LT → lean red


class ColorBand(str, Enum):
    GREEN = "green"
    AMBER = "amber"
    RED = "red"
    INVALID = "invalid"


@dataclass(frozen=True)
class GaugeState:
    """Renderable state produced from one AFR sample."""

    afr: float
    display_afr: float
    valid: bool
    band: ColorBand
    lit_count: int
    lit_indices: tuple[int, ...]
    segment_bands: tuple[ColorBand, ...]

    def readout(self) -> str:
        """Center numeric string (one decimal), or dashes when invalid."""
        if not self.valid:
            return "--.-"
        return f"{self.display_afr:.1f}"


def clamp_afr(afr: float) -> float:
    """Clamp AFR into the displayable scale [AFR_MIN, AFR_MAX]."""
    if afr < AFR_MIN:
        return AFR_MIN
    if afr > AFR_MAX:
        return AFR_MAX
    return float(afr)


def is_in_range(afr: float) -> bool:
    return AFR_MIN <= afr <= AFR_MAX


def band_for_afr(afr: float) -> ColorBand:
    """Map a single AFR value to a color band (invalid if out of scale)."""
    if not is_in_range(afr):
        return ColorBand.INVALID
    if afr < BAND_RICH_RED_LT:
        return ColorBand.RED
    if afr < BAND_GREEN_LT:
        return ColorBand.GREEN
    if afr < BAND_AMBER_LT:
        return ColorBand.AMBER
    return ColorBand.RED


def segment_midpoint_afr(index: int, n: int = SEGMENT_COUNT) -> float:
    """AFR value at the midpoint of segment *index* (0 .. n-1)."""
    if n < 1:
        raise ValueError("segment count must be >= 1")
    if index < 0 or index >= n:
        raise ValueError(f"segment index {index} out of range for n={n}")
    # Segment i covers [min + i*span/n, min + (i+1)*span/n)
    span = AFR_MAX - AFR_MIN
    return AFR_MIN + (index + 0.5) * span / n


def segment_band(index: int, n: int = SEGMENT_COUNT) -> ColorBand:
    """Fixed color of segment *index* by its midpoint AFR (never invalid)."""
    mid = segment_midpoint_afr(index, n)
    # Midpoints are always in range; fold invalid away.
    b = band_for_afr(mid)
    return ColorBand.RED if b is ColorBand.INVALID else b


def lit_count_for_afr(afr: float, n: int = SEGMENT_COUNT) -> int:
    """How many arc segments light for this AFR (needle fills low→high).

    Out-of-range samples clamp for fill level but callers should check valid.
    """
    display = clamp_afr(afr)
    span = AFR_MAX - AFR_MIN
    if span <= 0:
        return 0
    # Map [min, max] → [1, n] so min still lights the first tick.
    t = (display - AFR_MIN) / span
    count = int(math.floor(t * n + 1e-9)) + 1
    if count < 1:
        return 1
    if count > n:
        return n
    return count


def lit_indices_for_afr(afr: float, n: int = SEGMENT_COUNT) -> tuple[int, ...]:
    """Indices 0..lit_count-1 that are lit for this AFR."""
    c = lit_count_for_afr(afr, n)
    return tuple(range(c))


def map_afr(afr: float, n: int = SEGMENT_COUNT) -> GaugeState:
    """Primary mapper: AFR sample → full gauge state (shipped entry)."""
    valid = is_in_range(afr)
    display = clamp_afr(afr)
    band = band_for_afr(afr) if valid else ColorBand.INVALID
    indices = lit_indices_for_afr(display, n)
    segs = tuple(segment_band(i, n) for i in range(n))
    return GaugeState(
        afr=float(afr),
        display_afr=display,
        valid=valid,
        band=band,
        lit_count=len(indices),
        lit_indices=indices,
        segment_bands=segs,
    )


# --- Simulated stream -------------------------------------------------------


@dataclass
class SimulatorConfig:
    """Noise around stoich with occasional rich/lean excursions."""

    center: float = AFR_STOICH
    noise_sigma: float = 0.25
    rich_excursion: float = 11.0
    lean_excursion: float = 17.5
    excursion_prob: float = 0.08
    seed: Optional[int] = 42


class AfrSimulator:
    """Time-varying simulated AFR (not live OBD/CAN)."""

    def __init__(self, config: Optional[SimulatorConfig] = None) -> None:
        self.config = config or SimulatorConfig()
        self._rng = random.Random(self.config.seed)
        self._tick = 0
        self._hold_target: Optional[float] = None
        self._hold_remaining = 0

    def next_afr(self) -> float:
        cfg = self.config
        self._tick += 1
        if self._hold_remaining > 0:
            self._hold_remaining -= 1
            base = self._hold_target if self._hold_target is not None else cfg.center
        else:
            self._hold_target = None
            if self._rng.random() < cfg.excursion_prob:
                if self._rng.random() < 0.5:
                    self._hold_target = cfg.rich_excursion
                else:
                    self._hold_target = cfg.lean_excursion
                self._hold_remaining = self._rng.randint(3, 8)
                base = self._hold_target
            else:
                base = cfg.center
        afr = base + self._rng.gauss(0.0, cfg.noise_sigma)
        # Keep sim mostly on-scale so the gauge is useful; rare overshoot allowed.
        return afr

    def next_state(self, n: int = SEGMENT_COUNT) -> GaugeState:
        return map_afr(self.next_afr(), n)

    def stream(self, count: int, n: int = SEGMENT_COUNT) -> Iterator[GaugeState]:
        for _ in range(count):
            yield self.next_state(n)


def simulate_stream(
    count: int,
    config: Optional[SimulatorConfig] = None,
    n: int = SEGMENT_COUNT,
) -> List[GaugeState]:
    """Produce *count* simulated gauge states (shipped helper for tests/UI)."""
    return list(AfrSimulator(config).stream(count, n))


def states_change(states: Sequence[GaugeState]) -> bool:
    """True if readout or lit set is not constant across the stream."""
    if len(states) < 2:
        return False
    keys = {(s.readout(), s.lit_indices, s.band) for s in states}
    return len(keys) > 1
