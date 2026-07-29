"""§17-shaped burn soak through the full software bench."""

from __future__ import annotations

from pathlib import Path

from sim.orch.bench import SimBench, burn_soak


def test_identity_over_host_link() -> None:
    with SimBench() as bench:
        assert bench.boot_identity == "fw_name=AETHER fw_version=0.0.1"
        assert bench.cmd("identity") == bench.boot_identity


def test_burn_soak_through_aether() -> None:
    with SimBench() as bench:
        result = burn_soak(bench)
        assert result.ok, result.as_dict()
        assert result.operator_flash_crc
        assert result.golden_flash_crc
        assert result.mutated_flash_crc
        assert result.final_flash_crc == result.operator_flash_crc
        assert result.mutated_flash_crc != result.golden_flash_crc


def test_fb_ppm_artifact(tmp_path: Path) -> None:
    with SimBench(out_dir=tmp_path) as bench:
        ppm = tmp_path / "face.ppm"
        resp = bench.cmd(f"fb.ppm {ppm.as_posix()}")
        assert resp.startswith("OK wrote")
        assert ppm.is_file()
        assert ppm.stat().st_size > 100
