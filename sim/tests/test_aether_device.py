"""Aether device unit tests (in-process, ECU optional)."""

from __future__ import annotations

from pathlib import Path

from sim.aether.device import AetherDevice, identity_line
from sim.aether.framebuffer import SyntheticFramebuffer
from sim.ecu.server import EcuServer


def test_identity_matches_metal_shape() -> None:
    line = identity_line()
    assert line == "fw_name=AETHER fw_version=0.0.1"
    dev = AetherDevice()
    assert dev.handle_line("identity") == line


def test_framebuffer_stable_crc_and_ppm(tmp_path: Path) -> None:
    fb = SyntheticFramebuffer(width=32, height=16, pattern_id=3)
    crc1 = fb.crc32()
    fb2 = SyntheticFramebuffer(width=32, height=16, pattern_id=3)
    assert fb2.crc32() == crc1
    fb.set_pattern(4)
    assert fb.crc32() != crc1
    path = tmp_path / "t.ppm"
    fb.to_ppm(path)
    data = path.read_bytes()
    assert data.startswith(b"P6\n")
    assert b"32 16" in data.split(b"\n", 2)[1] or b"32 16" in data


def test_device_cal_path_against_ecu() -> None:
    with EcuServer() as ecu:
        dev = AetherDevice(ecu_host="127.0.0.1", ecu_port=ecu.port)
        assert dev.handle_line("ecu.sign").startswith("OK AETHER_ECU_SIM")
        assert dev.handle_line("ecu.golden").startswith("OK golden")
        golden = dev.handle_line("ecu.flashcrc")
        assert golden.startswith("OK ")
        assert dev.handle_line("ecu.mutate").startswith("OK ")
        assert dev.handle_line("ecu.burn").startswith("OK burned")
        mutated = dev.handle_line("ecu.flashcrc")
        assert mutated != golden
        dev.close_ecu()
