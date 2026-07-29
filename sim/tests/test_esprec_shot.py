"""ESPREC1 shot from V-AETHER (esprec-compatible software eyes)."""

from __future__ import annotations

from pathlib import Path

from sim.aether.device import AetherDevice, AetherServer
from sim.aether.esprec_emit import verify_esprec1_lines
from sim.aether.esprec_port import AetherTcpPort
from sim.aether.framebuffer import SyntheticFramebuffer
from sim.orch.bench import SimBench


def test_esprec_emit_roundtrip_crc() -> None:
    fb = SyntheticFramebuffer(width=16, height=8, pattern_id=2)
    from sim.aether.esprec_emit import build_esprec1_lines

    lines = build_esprec1_lines(fb.width, fb.height, fb.rgb565_spi_be())
    w, h, raster = verify_esprec1_lines(lines)
    assert (w, h) == (16, 8)
    assert raster == fb.rgb565_spi_be()


def test_device_esprec_shot_in_process() -> None:
    dev = AetherDevice()
    lines = dev.handle_line("esprec shot")
    assert isinstance(lines, list)
    w, h, raster = verify_esprec1_lines(lines)
    assert w == dev.fb.width and h == dev.fb.height
    assert len(raster) == dev.fb.nbytes


def test_esprec_shot_over_tcp_and_optional_esprec_lib(tmp_path: Path) -> None:
    with AetherServer() as srv:
        port = AetherTcpPort("127.0.0.1", srv.port, timeout_s=3.0)
        boot = port.connect()
        assert boot.startswith("fw_name=AETHER")

        # Local grab via host client multi-line shot
        lines = port.esprec_shot()
        w, h, raster = verify_esprec1_lines(lines)
        assert w * h * 2 == len(raster)

        # If tig/esprec is installed, use its grab_frame + PNG path.
        try:
            from esprec.capture import snapshot  # type: ignore
            from esprec.transport import grab_frame  # type: ignore
        except ImportError:
            port.close()
            return

        meta, _raster = grab_frame(port, timeout_s=5.0, command=b"esprec shot\n")
        assert meta.w == w and meta.h == h
        png = tmp_path / "face.png"
        snapshot(port, png, timeout_s=5.0)
        assert png.is_file() and png.stat().st_size > 32
        port.close()


def test_bench_esprec_shot() -> None:
    with SimBench() as bench:
        lines = bench.host.esprec_shot()  # type: ignore[union-attr]
        w, h, raster = verify_esprec1_lines(lines)
        assert len(raster) == w * h * 2
