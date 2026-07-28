"""Aether host AFR gauge mockup package."""

from .afr_gauge import (
    AFR_MAX,
    AFR_MIN,
    AFR_STOICH,
    SEGMENT_COUNT,
    AfrSimulator,
    ColorBand,
    GaugeState,
    map_afr,
    simulate_stream,
)

__all__ = [
    "AFR_MAX",
    "AFR_MIN",
    "AFR_STOICH",
    "SEGMENT_COUNT",
    "AfrSimulator",
    "ColorBand",
    "GaugeState",
    "map_afr",
    "simulate_stream",
]
