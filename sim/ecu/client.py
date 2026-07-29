"""Client for AESP (software ECU)."""

from __future__ import annotations

import socket
from dataclasses import dataclass


@dataclass
class EcuClient:
    host: str
    port: int
    timeout_s: float = 2.0

    def __post_init__(self) -> None:
        self._sock: socket.socket | None = None
        self._rfile = None
        self._wfile = None

    def connect(self) -> None:
        self.close()
        sock = socket.create_connection((self.host, self.port), timeout=self.timeout_s)
        sock.settimeout(self.timeout_s)
        self._sock = sock
        self._rfile = sock.makefile("rb")
        self._wfile = sock.makefile("wb")
        greeting = self._readline()
        if not greeting.startswith("AESP"):
            raise RuntimeError(f"unexpected ECU greeting: {greeting!r}")

    def close(self) -> None:
        for f in (self._rfile, self._wfile):
            if f is not None:
                try:
                    f.close()
                except Exception:
                    pass
        self._rfile = None
        self._wfile = None
        if self._sock is not None:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None

    def __enter__(self) -> "EcuClient":
        self.connect()
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _readline(self) -> str:
        assert self._rfile is not None
        line = self._rfile.readline()
        if not line:
            raise RuntimeError("ECU connection closed")
        return line.decode("utf-8", errors="replace").rstrip("\r\n")

    def cmd(self, line: str) -> str:
        if self._sock is None:
            self.connect()
        assert self._wfile is not None
        self._wfile.write((line.rstrip("\r\n") + "\n").encode("utf-8"))
        self._wfile.flush()
        return self._readline()

    def signature(self) -> str:
        resp = self.cmd("SIGN")
        parts = resp.split(maxsplit=1)
        if parts[0] != "SIGN" or len(parts) < 2:
            raise RuntimeError(resp)
        return parts[1]

    def read_ram(self, page: int, off: int, length: int) -> bytes:
        resp = self.cmd(f"R {page} {off} {length}")
        parts = resp.split()
        if len(parts) < 3 or parts[0] != "R" or parts[1] != "OK":
            raise RuntimeError(resp)
        return bytes.fromhex(parts[2])

    def write_ram(self, page: int, off: int, data: bytes) -> None:
        resp = self.cmd(f"W {page} {off} {data.hex()}")
        if not resp.startswith("W OK"):
            raise RuntimeError(resp)

    def burn(self, page: int | None = None) -> None:
        resp = self.cmd("B ALL" if page is None else f"B {page}")
        if not resp.startswith("B OK"):
            raise RuntimeError(resp)

    def power_cycle(self) -> None:
        resp = self.cmd("POWERCYCLE")
        if not resp.startswith("POWERCYCLE OK"):
            raise RuntimeError(resp)

    def ram_crc_all(self) -> str:
        resp = self.cmd("RAMCRC ALL")
        parts = resp.split()
        if parts[0] != "RAMCRC" or len(parts) < 2:
            raise RuntimeError(resp)
        return parts[1]

    def flash_crc_all(self) -> str:
        resp = self.cmd("FLASHCRC ALL")
        parts = resp.split()
        if parts[0] != "FLASHCRC" or len(parts) < 2:
            raise RuntimeError(resp)
        return parts[1]

    def dump_flash_pages(self) -> list[bytes]:
        resp = self.cmd("DUMPFLASH")
        if not resp.startswith("DUMPFLASH "):
            raise RuntimeError(resp)
        body = resp[len("DUMPFLASH ") :]
        return [bytes.fromhex(chunk) for chunk in body.split("|") if chunk != ""]

    def dump_ram_pages(self) -> list[bytes]:
        resp = self.cmd("DUMPRAM")
        if not resp.startswith("DUMPRAM "):
            raise RuntimeError(resp)
        body = resp[len("DUMPRAM ") :]
        return [bytes.fromhex(chunk) for chunk in body.split("|") if chunk != ""]

    def install_golden(self) -> str:
        resp = self.cmd("GOLDEN")
        parts = resp.split()
        if parts[0] != "GOLDEN" or parts[1] != "OK":
            raise RuntimeError(resp)
        return parts[2]

    def mutate(self) -> str:
        resp = self.cmd("MUTATE")
        if not resp.startswith("MUTATE OK"):
            raise RuntimeError(resp)
        return resp
