"""Integration: portable C ecu_tcp_bench against V-ECU."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from sim.ecu.server import EcuServer

REPO = Path(__file__).resolve().parents[2]
BUILD = REPO / "build" / "host"


def _find_bench() -> Path | None:
    candidates = [
        BUILD / "ecu_tcp_bench",
        BUILD / "ecu_tcp_bench.exe",
        BUILD / "Debug" / "ecu_tcp_bench.exe",
        BUILD / "Release" / "ecu_tcp_bench.exe",
    ]
    for c in candidates:
        if c.is_file():
            return c
    return None


def _ensure_built() -> Path | None:
    existing = _find_bench()
    if existing:
        return existing
    if not shutil.which("cmake"):
        return None
    BUILD.mkdir(parents=True, exist_ok=True)
    conf = subprocess.run(
        ["cmake", "-S", str(REPO / "host"), "-B", str(BUILD)],
        capture_output=True,
        text=True,
    )
    if conf.returncode != 0:
        return None
    build = subprocess.run(
        ["cmake", "--build", str(BUILD), "--target", "ecu_tcp_bench"],
        capture_output=True,
        text=True,
    )
    if build.returncode != 0:
        return None
    return _find_bench()


def test_c_client_tcp_against_vecu() -> None:
    bench = _ensure_built()
    if bench is None:
        pytest.skip("ecu_tcp_bench not built (cmake missing or build failed)")

    with EcuServer() as ecu:
        env = os.environ.copy()
        proc = subprocess.run(
            [str(bench), "127.0.0.1", str(ecu.port)],
            capture_output=True,
            text=True,
            env=env,
            timeout=15,
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert "ecu_tcp_bench: OK" in proc.stdout
