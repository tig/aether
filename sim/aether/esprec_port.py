"""BytePort adapter so tig/esprec (or local grab) can talk to V-AETHER TCP."""

from __future__ import annotations

import socket
from typing import Optional


class AetherTcpPort:
    """Minimal serial-like port over TCP to AetherServer / QEMU UART bridge.

    Compatible with esprec.transport.BytePort (write / readline / read /
    reset_input_buffer / flush).
    """

    def __init__(self, host: str, port: int, timeout_s: float = 5.0) -> None:
        self.host = host
        self.port = port
        self.timeout_s = timeout_s
        self._sock: Optional[socket.socket] = None
        self._rfile = None
        self._boot: Optional[str] = None

    def connect(self) -> str:
        self.close()
        sock = socket.create_connection((self.host, self.port), timeout=self.timeout_s)
        sock.settimeout(self.timeout_s)
        self._sock = sock
        self._rfile = sock.makefile("rb")
        # Drain boot identity line
        boot = self.readline()
        self._boot = boot.decode("utf-8", errors="replace").rstrip("\r\n") if boot else ""
        return self._boot

    @property
    def boot_identity(self) -> str:
        return self._boot or ""

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

    def write(self, data: bytes) -> int:
        if self._sock is None:
            self.connect()
        assert self._sock is not None
        self._sock.sendall(data)
        return len(data)

    def readline(self) -> bytes:
        if self._sock is None:
            return b""
        assert self._rfile is not None
        try:
            line = self._rfile.readline()
        except (TimeoutError, socket.timeout, OSError):
            return b""
        return line if line else b""

    def read(self, n: int) -> bytes:
        if self._sock is None or n <= 0:
            return b""
        try:
            return self._sock.recv(n)
        except (TimeoutError, socket.timeout, OSError):
            return b""

    def reset_input_buffer(self) -> None:
        # best-effort: nothing buffered beyond makefile
        pass

    def flush(self) -> None:
        pass
