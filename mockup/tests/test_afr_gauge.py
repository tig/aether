"""Unit tests for shipped AFR→segment/color mapping and simulated stream.

Drives mockup.afr_gauge functions only — no GUI, no reimplemented tables.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Allow `pytest mockup/tests` from product root without install.
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from mockup.afr_gauge import (
    AFR_MAX,
    AFR_MIN,
    AFR_STOICH,
    SEGMENT_COUNT,
    AfrSimulator,
    ColorBand,
    SimulatorConfig,
    afr_to_arc_t,
    arc_t_to_afr,
    band_for_afr,
    clamp_afr,
    lit_count_for_afr,
    lit_indices_for_afr,
    map_afr,
    segment_band,
    segment_midpoint_afr,
    simulate_stream,
    states_change,
)


class TestClampAndRange:
    def test_clamp_below_min(self):
        assert clamp_afr(AFR_MIN - 2.0) == AFR_MIN

    def test_clamp_above_max(self):
        assert clamp_afr(AFR_MAX + 3.0) == AFR_MAX

    def test_clamp_in_range_identity(self):
        assert clamp_afr(14.7) == pytest.approx(14.7)


class TestColorBands:
    def test_rich_is_red(self):
        assert band_for_afr(10.0) is ColorBand.RED

    def test_green_zone(self):
        assert band_for_afr(12.5) is ColorBand.GREEN
        assert band_for_afr(13.5) is ColorBand.GREEN
        assert band_for_afr(14.7) is ColorBand.GREEN

    def test_amber_zone(self):
        assert band_for_afr(15.2) is ColorBand.AMBER
        assert band_for_afr(15.5) is ColorBand.AMBER

    def test_lean_is_red(self):
        assert band_for_afr(16.5) is ColorBand.RED
        assert band_for_afr(19.0) is ColorBand.RED

    def test_out_of_range_invalid(self):
        assert band_for_afr(7.9) is ColorBand.INVALID
        assert band_for_afr(20.1) is ColorBand.INVALID

    def test_endpoints_in_range(self):
        assert band_for_afr(AFR_MIN) is not ColorBand.INVALID
        assert band_for_afr(AFR_MAX) is not ColorBand.INVALID


class TestSegments:
    def test_segment_count_matches_indices(self):
        state = map_afr(14.7)
        assert len(state.segment_bands) == SEGMENT_COUNT
        assert state.lit_count == len(state.lit_indices)
        assert state.lit_indices == tuple(range(state.lit_count))

    def test_higher_afr_lights_more_or_equal_segments(self):
        low = lit_count_for_afr(9.0)
        mid = lit_count_for_afr(14.7)
        high = lit_count_for_afr(19.0)
        assert low < mid < high

    def test_min_lights_first_segment(self):
        assert lit_indices_for_afr(AFR_MIN) == (0,)
        assert lit_count_for_afr(AFR_MIN) == 1

    def test_max_lights_all_segments(self):
        assert lit_count_for_afr(AFR_MAX) == SEGMENT_COUNT
        assert lit_indices_for_afr(AFR_MAX) == tuple(range(SEGMENT_COUNT))

    def test_segment_midpoints_span_scale(self):
        mids = [segment_midpoint_afr(i) for i in range(SEGMENT_COUNT)]
        assert mids[0] > AFR_MIN
        assert mids[-1] < AFR_MAX
        assert mids == sorted(mids)

    def test_segment_bands_include_green_and_red(self):
        bands = {segment_band(i) for i in range(SEGMENT_COUNT)}
        assert ColorBand.GREEN in bands
        assert ColorBand.RED in bands

    def test_midrange_gets_more_arc_than_ends(self):
        # 11 and 17 sit near corners; 11–17 owns most of the dial.
        t11 = afr_to_arc_t(11.0)
        t17 = afr_to_arc_t(17.0)
        assert t11 < 0.20
        assert t17 > 0.80
        assert (t17 - t11) > 0.60
        # Inverse is consistent at control points
        assert arc_t_to_afr(0.0) == pytest.approx(8.0)
        assert arc_t_to_afr(1.0) == pytest.approx(20.0)
        assert arc_t_to_afr(t11) == pytest.approx(11.0)
        assert arc_t_to_afr(t17) == pytest.approx(17.0)


class TestMapAfr:
    def test_stoich_valid_green(self):
        s = map_afr(AFR_STOICH)
        assert s.valid is True
        assert s.band is ColorBand.GREEN
        assert s.readout() == f"{AFR_STOICH:.1f}"
        assert s.display_afr == pytest.approx(AFR_STOICH)

    def test_out_of_range_marks_invalid_and_clamps_display(self):
        low = map_afr(5.0)
        assert low.valid is False
        assert low.band is ColorBand.INVALID
        assert low.display_afr == AFR_MIN
        assert low.readout() == "--.-"
        # Still produces a clamped lit set for display continuity
        assert low.lit_count >= 1

        high = map_afr(25.0)
        assert high.valid is False
        assert high.display_afr == AFR_MAX
        assert high.lit_count == SEGMENT_COUNT

    def test_in_range_readout_one_decimal(self):
        s = map_afr(15.42)
        assert s.readout() == "15.4"
        assert s.valid is True

    def test_sample_grid_maps_without_crash(self):
        for afr in [8.0, 10.0, 11.5, 12.0, 14.2, 14.7, 15.5, 17.0, 20.0]:
            s = map_afr(afr)
            assert 1 <= s.lit_count <= SEGMENT_COUNT
            assert s.band is not None


class TestSimulator:
    def test_stream_length_and_types(self):
        states = simulate_stream(12, config=SimulatorConfig(seed=1))
        assert len(states) == 12
        assert all(hasattr(s, "lit_indices") for s in states)

    def test_stream_changes_over_time(self):
        # Force excursions so band/lit must move.
        cfg = SimulatorConfig(
            seed=7,
            noise_sigma=0.4,
            excursion_prob=0.35,
            rich_excursion=10.5,
            lean_excursion=17.5,
        )
        states = simulate_stream(40, config=cfg)
        assert states_change(states) is True

    def test_deterministic_with_seed(self):
        a = [s.afr for s in simulate_stream(8, config=SimulatorConfig(seed=99))]
        b = [s.afr for s in simulate_stream(8, config=SimulatorConfig(seed=99))]
        assert a == b

    def test_simulator_next_state_uses_mapper(self):
        sim = AfrSimulator(SimulatorConfig(seed=3))
        afr = sim.next_afr()
        # Re-map the last generated value path: next_state is map_afr(next_afr)
        sim2 = AfrSimulator(SimulatorConfig(seed=3))
        s = sim2.next_state()
        assert s.afr == pytest.approx(afr)
        assert s.lit_indices == lit_indices_for_afr(s.display_afr)
        assert s.band == band_for_afr(s.afr) if s.valid else ColorBand.INVALID
