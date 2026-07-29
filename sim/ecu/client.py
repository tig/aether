"""Client for AESP (software ECU)."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..line_socket import LineSocket


@dataclass
class EcuClient:
    host: str
    port: int
    timeout_s: float = 2.0
    _ls: LineSocket = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._ls = LineSocket(self.host, self.port, timeout_s=self.timeout_s)

    def connect(self) -> None:
        self._ls.connect()
        greeting = self._ls.readline_str()
        if not greeting.startswith("AESP"):
            raise RuntimeError(f"unexpected ECU greeting: {greeting!r}")

    def close(self) -> None:
        self._ls.close()

    def __enter__(self) -> "EcuClient":
        self.connect()
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def cmd(self, line: str) -> str:
        self._ls.write_line(line)
        return self._ls.readline_str()

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
