"""Shared TCP line socket helpers for V-ECU / V-AETHER host clients."""

from __future__ import annotations

import socket
from typing import Optional


class LineSocket:
    """CR/LF line client over TCP (boot greeting optional)."""

    def __init__(self, host: str, port: int, timeout_s: float = 2.0) -> None:
        self.host = host
        self.port = port
        self.timeout_s = timeout_s
        self._sock: Optional[socket.socket] = None
        self._rfile = None

    def connect(self) -> None:
        self.close()
        sock = socket.create_connection((self.host, self.port), timeout=self.timeout_s)
        sock.settimeout(self.timeout_s)
        self._sock = sock
        self._rfile = sock.makefile("rb")

    def close(self) -> None:
        if self._rfile is not None:
            try:
                self._rfile.close()
            except Exception:
                pass
            self._rfile = None
        if self._sock is not None:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None

    def ensure(self) -> None:
        if self._sock is None:
            self.connect()

    def write_bytes(self, data: bytes) -> int:
        self.ensure()
        assert self._sock is not None
        self._sock.sendall(data)
        return len(data)

    def write_line(self, line: str) -> None:
        self.write_bytes((line.rstrip("\r\n") + "\n").encode("utf-8"))

    def readline_bytes(self, *, empty_on_timeout: bool = False) -> bytes:
        self.ensure()
        assert self._rfile is not None
        try:
            line = self._rfile.readline()
        except (TimeoutError, socket.timeout, OSError):
            if empty_on_timeout:
                return b""
            raise
        if not line and empty_on_timeout:
            return b""
        if not line:
            raise RuntimeError("connection closed")
        return line

    def readline_str(self, *, empty_on_timeout: bool = False) -> str:
        raw = self.readline_bytes(empty_on_timeout=empty_on_timeout)
        if not raw:
            return ""
        return raw.decode("utf-8", errors="replace").rstrip("\r\n")
