"""Unit tests for ECU calibration store (no sockets)."""

from __future__ import annotations

from pathlib import Path

from sim.ecu.pages import CalibrationStore
from sim.ecu.protocol import handle_line


def test_burn_persists_across_power_cycle() -> None:
    store = CalibrationStore()
    store.page(0).write_ram(0, b"\x11\x22")
    store.power_cycle()
    assert store.page(0).read_ram(0, 2) != b"\x11\x22"

    store.page(0).write_ram(0, b"\x11\x22")
    store.burn(0)
    store.power_cycle()
    assert store.page(0).read_ram(0, 2) == b"\x11\x22"


def test_flash_file_roundtrip(tmp_path: Path) -> None:
    store = CalibrationStore()
    store.install_golden()
    path = tmp_path / "flash.json"
    store.save_flash_file(path)

    other = CalibrationStore()
    other.load_flash_file(path)
    assert other.all_flash_crc() == store.all_flash_crc()
    assert bytes(other.page(1).flash) == bytes(store.page(1).flash)


def test_mutate_touches_three_aspects() -> None:
    store = CalibrationStore()
    store.install_golden()
    before = [bytes(p.flash) for p in store.pages]
    patches = store.apply_mutation_aspects()
    assert set(patches) == {"scalar", "curve", "table"}
    store.burn()
    after = [bytes(p.flash) for p in store.pages]
    assert after[0] != before[0]
    assert after[1] != before[1]
    assert after[2] != before[2]


def test_protocol_sign_and_rw() -> None:
    store = CalibrationStore()
    assert handle_line(store, "SIGN").startswith("SIGN AETHER_ECU_SIM")
    assert handle_line(store, "W 0 0 aabb") == "W OK 2"
    assert handle_line(store, "R 0 0 2") == "R OK aabb"
    assert handle_line(store, "B 0").startswith("B OK")
    assert handle_line(store, "POWERCYCLE") == "POWERCYCLE OK"
    assert handle_line(store, "R 0 0 2") == "R OK aabb"
