"""Host-process Aether device: metal-shaped wire surface without ESP silicon.

Speaks:
  - host serial protocol (identity knock, cal commands, fb meta)
  - ESPREC1 shot (esprec-compatible framebuffer capture)
  - AESP client to the software ECU

This is the *always-on* software Aether. Real ``firmware/`` under Espressif
QEMU is the higher-fidelity twin (same identity line, later same cal verbs);
see ``specs/sim-bench.md``.
"""

from __future__ import annotations

import argparse
import socket
import socketserver
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Union

from ..ecu.client import EcuClient
from .esprec_emit import build_esprec1_lines
from .framebuffer import SyntheticFramebuffer

FW_NAME = "AETHER"
FW_VERSION = "0.0.1"

Response = Union[str, list[str]]


def identity_line(fw_name: str = FW_NAME, fw_version: str = FW_VERSION) -> str:
    """Match metal / silico inspect: fw_name=… fw_version=…"""
    return f"fw_name={fw_name} fw_version={fw_version}"


@dataclass
class AetherDevice:
    """In-process device state + command dispatch."""

    ecu_host: str = "127.0.0.1"
    ecu_port: int = 8765
    fw_name: str = FW_NAME
    fw_version: str = FW_VERSION
    fb: SyntheticFramebuffer = field(default_factory=SyntheticFramebuffer)
    _ecu: EcuClient | None = field(default=None, repr=False)
    _backup_flash: list[bytes] | None = field(default=None, repr=False)
    audit: list[str] = field(default_factory=list)

    def identity(self) -> str:
        return identity_line(self.fw_name, self.fw_version)

    def connect_ecu(self) -> None:
        if self._ecu is None:
            self._ecu = EcuClient(self.ecu_host, self.ecu_port)
        self._ecu.connect()
        self.audit.append(f"ecu_connect {self.ecu_host}:{self.ecu_port}")

    def close_ecu(self) -> None:
        if self._ecu is not None:
            self._ecu.close()
            self._ecu = None

    def _require_ecu(self) -> EcuClient:
        if self._ecu is None:
            self.connect_ecu()
        assert self._ecu is not None
        return self._ecu

    def esprec_shot_lines(self) -> list[str]:
        raster = self.fb.rgb565_spi_be()
        lines = build_esprec1_lines(self.fb.width, self.fb.height, raster)
        self.audit.append(
            f"esprec.shot {self.fb.width}x{self.fb.height} pattern={self.fb.pattern_id}"
        )
        return lines

    def handle_line(self, line: str) -> Response:
        raw = line.strip()
        if not raw:
            return "ERR empty"

        # Case-sensitive identity knock (metal compares exact word).
        if raw == "identity":
            return self.identity()

        low = raw.lower()
        # esprec host CLI sends "esprec shot" or "shot"
        if low in ("esprec shot", "shot", "frame", "esprec", "esprec.shot"):
            return self.esprec_shot_lines()

        parts = raw.split()
        cmd = parts[0].lower()

        try:
            if cmd == "ping":
                return "PONG aether-sim"

            if cmd == "help":
                return (
                    "OK cmds: identity ping help ecu.sign ecu.backup ecu.restore "
                    "ecu.golden ecu.mutate ecu.burn ecu.powercycle ecu.ramcrc "
                    "ecu.flashcrc ecu.read ecu.write fb.meta fb.ppm fb.pattern "
                    "esprec shot"
                )

            if cmd == "ecu.sign":
                sig = self._require_ecu().signature()
                self.audit.append(f"ecu.sign {sig}")
                return f"OK {sig}"

            if cmd == "ecu.backup":
                pages = self._require_ecu().dump_flash_pages()
                self._backup_flash = pages
                crc = self._require_ecu().flash_crc_all()
                self.audit.append(f"ecu.backup pages={len(pages)} flash_crc={crc}")
                return f"OK backup pages={len(pages)} flash_crc={crc}"

            if cmd == "ecu.restore":
                if self._backup_flash is None:
                    return "ERR no_backup"
                ecu = self._require_ecu()
                for i, data in enumerate(self._backup_flash):
                    ecu.write_ram(i, 0, data)
                ecu.burn()
                crc = ecu.flash_crc_all()
                self.audit.append(f"ecu.restore flash_crc={crc}")
                return f"OK restored flash_crc={crc}"

            if cmd == "ecu.golden":
                crc = self._require_ecu().install_golden()
                self.audit.append(f"ecu.golden flash_crc={crc}")
                return f"OK golden flash_crc={crc}"

            if cmd == "ecu.mutate":
                detail = self._require_ecu().mutate()
                self.audit.append(f"ecu.mutate {detail}")
                return f"OK {detail}"

            if cmd == "ecu.burn":
                self._require_ecu().burn()
                crc = self._require_ecu().flash_crc_all()
                self.audit.append(f"ecu.burn flash_crc={crc}")
                return f"OK burned flash_crc={crc}"

            if cmd == "ecu.powercycle":
                self._require_ecu().power_cycle()
                self.audit.append("ecu.powercycle")
                return "OK powercycle"

            if cmd == "ecu.ramcrc":
                return f"OK {self._require_ecu().ram_crc_all()}"

            if cmd == "ecu.flashcrc":
                return f"OK {self._require_ecu().flash_crc_all()}"

            if cmd == "ecu.read":
                if len(parts) != 4:
                    return "ERR usage ecu.read <page> <off> <len>"
                page, off, length = int(parts[1]), int(parts[2]), int(parts[3])
                data = self._require_ecu().read_ram(page, off, length)
                return f"OK {data.hex()}"

            if cmd == "ecu.write":
                if len(parts) != 4:
                    return "ERR usage ecu.write <page> <off> <hex>"
                page, off = int(parts[1]), int(parts[2])
                data = bytes.fromhex(parts[3])
                self._require_ecu().write_ram(page, off, data)
                return f"OK wrote {len(data)}"

            if cmd == "fb.meta":
                return f"OK {self.fb.meta_line()}"

            if cmd == "fb.pattern":
                if len(parts) != 2:
                    return "ERR usage fb.pattern <id>"
                self.fb.set_pattern(int(parts[1]))
                return f"OK {self.fb.meta_line()}"

            if cmd == "fb.ppm":
                if len(parts) != 2:
                    return "ERR usage fb.ppm <path>"
                path = Path(parts[1])
                self.fb.to_ppm(path)
                return f"OK wrote {path.as_posix()} {self.fb.meta_line()}"

            if cmd == "audit":
                return "OK " + (" | ".join(self.audit) if self.audit else "(empty)")

            return f"ERR unknown {cmd}"

        except Exception as exc:  # noqa: BLE001 — wire-facing
            return f"ERR {type(exc).__name__}:{exc}"[:200]


class _AetherHandler(socketserver.StreamRequestHandler):
    device: AetherDevice

    def handle(self) -> None:
        # Boot identity print (metal does this once at boot).
        self.wfile.write((self.device.identity() + "\n").encode("utf-8"))
        self.wfile.flush()
        while True:
            raw = self.rfile.readline()
            if not raw:
                break
            text = raw.decode("utf-8", errors="replace")
            resp = self.device.handle_line(text)
            if isinstance(resp, list):
                for line in resp:
                    self.wfile.write((line + "\n").encode("utf-8"))
            else:
                self.wfile.write((resp + "\n").encode("utf-8"))
            self.wfile.flush()


class AetherServer:
    """TCP stand-in for Aether USB-serial host link."""

    def __init__(
        self,
        device: AetherDevice | None = None,
        host: str = "127.0.0.1",
        port: int = 0,
    ) -> None:
        self.device = device or AetherDevice()
        self.host = host

        class _Server(socketserver.ThreadingTCPServer):
            allow_reuse_address = True
            daemon_threads = True

        handler = type(
            "BoundAetherHandler",
            (_AetherHandler,),
            {"device": self.device},
        )
        self._server = _Server((host, port), handler)
        self.port: int = int(self._server.server_address[1])
        self._thread: threading.Thread | None = None

    @property
    def endpoint(self) -> str:
        return f"{self.host}:{self.port}"

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name="aether-sim",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self.device.close_ecu()
        self._server.shutdown()
        self._server.server_close()
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

    def __enter__(self) -> "AetherServer":
        self.start()
        return self

    def __exit__(self, *args: object) -> None:
        self.stop()


class AetherHostClient:
    """Host-side client talking to AetherServer (or later QEMU serial TCP)."""

    def __init__(self, host: str, port: int, timeout_s: float = 2.0) -> None:
        self.host = host
        self.port = port
        self.timeout_s = timeout_s
        self._sock: socket.socket | None = None
        self._rfile: Any = None
        self._wfile: Any = None

    def connect(self) -> str:
        self.close()
        sock = socket.create_connection((self.host, self.port), timeout=self.timeout_s)
        sock.settimeout(self.timeout_s)
        self._sock = sock
        self._rfile = sock.makefile("rb")
        self._wfile = sock.makefile("wb")
        boot = self._readline()
        return boot

    def close(self) -> None:
        for f in (self._rfile, self._wfile):
            if f is not None:
                try:
                    f.close()
                except Exception:
                    pass
        self._rfile = self._wfile = None
        if self._sock is not None:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None

    def __enter__(self) -> "AetherHostClient":
        self.connect()
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _readline(self) -> str:
        assert self._rfile is not None
        line = self._rfile.readline()
        if not line:
            raise RuntimeError("Aether connection closed")
        return line.decode("utf-8", errors="replace").rstrip("\r\n")

    def cmd(self, line: str) -> str:
        """Single-line request → single-line response."""
        if self._sock is None:
            self.connect()
        assert self._wfile is not None
        self._wfile.write((line.rstrip("\r\n") + "\n").encode("utf-8"))
        self._wfile.flush()
        return self._readline()

    def esprec_shot(self) -> list[str]:
        """Request ESPREC1 shot; return all response lines including header/end."""
        if self._sock is None:
            self.connect()
        assert self._wfile is not None
        self._wfile.write(b"esprec shot\n")
        self._wfile.flush()
        lines: list[str] = []
        while True:
            line = self._readline()
            lines.append(line)
            if line.startswith("ESPREC1_END") or line.startswith("ERR"):
                break
            # safety: huge frames
            if len(lines) > 10000:
                raise RuntimeError("esprec shot runaway")
        return lines


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Aether software-only device sim")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8766, help="Host-link listen port")
    p.add_argument("--ecu-host", default="127.0.0.1")
    p.add_argument("--ecu-port", type=int, default=8765)
    args = p.parse_args(argv)

    device = AetherDevice(ecu_host=args.ecu_host, ecu_port=args.ecu_port)

    class _Server(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        daemon_threads = True

    handler = type("BoundAetherHandler", (_AetherHandler,), {"device": device})
    server = _Server((args.host, args.port), handler)
    port = int(server.server_address[1])
    print(
        f"aether-sim listening on {args.host}:{port} "
        f"ecu={args.ecu_host}:{args.ecu_port} {device.identity()}",
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("aether-sim stopping", flush=True)
    finally:
        device.close_ecu()
        server.shutdown()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
