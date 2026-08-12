"""Live FOME serial client over pyserial (uses pure ts_frame)."""

from __future__ import annotations

import struct
import time
from typing import Callable

import serial

from ts_frame import (
    FrameError,
    FrameResponse,
    frame_request,
    och_get_payload,
    page_crc_payload,
    page_read_payload,
    page_write_payload,
    parse_response,
    response_success_burn,
    response_success_identity,
)

# Pilot pack constants (INI)
OCH_BLOCK_SIZE = 1260
PAGE_SIZE = 26552
BLOCKING_FACTOR = 1320
DEFAULT_BAUD = 115200

OFF_FLAGS = 0
OFF_RPM = 4
OFF_COOLANT = 8
OFF_INTAKE = 10
OFF_TPS = 24
OFF_LAMBDA1 = 92
OFF_MAP = 136

FLAG_SD_LOGGING = 1 << 1
FLAG_NEED_BURN = 1 << 6
FLAG_USB_CONNECTED = 1 << 22


class ProtocolError(RuntimeError):
    pass


class FomeClient:
    def __init__(self, port: str, baud: int = DEFAULT_BAUD, timeout: float = 1.5):
        self.port = port
        self.ser = serial.Serial(port=port, baudrate=baud, timeout=timeout)
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()

    def close(self) -> None:
        self.ser.close()

    def __enter__(self) -> "FomeClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def _read_exact(self, n: int, deadline: float) -> bytes:
        buf = bytearray()
        while len(buf) < n:
            if time.monotonic() > deadline:
                raise ProtocolError(
                    f"timeout reading {n} bytes (got {len(buf)}): {buf.hex()}"
                )
            chunk = self.ser.read(n - len(buf))
            if chunk:
                buf.extend(chunk)
        return bytes(buf)

    def transact(self, payload: bytes, timeout: float = 3.0) -> FrameResponse:
        frame = frame_request(payload)
        # Bench isolation only — do not copy into multi-master metal paths.
        self.ser.reset_input_buffer()
        self.ser.write(frame)
        self.ser.flush()
        deadline = time.monotonic() + timeout
        hdr = self._read_exact(2, deadline)
        (size,) = struct.unpack(">H", hdr)
        if size < 1 or size > 65530:
            raise ProtocolError(f"insane response size {size}")
        rest = self._read_exact(size + 4, deadline)
        try:
            return parse_response(hdr + rest)
        except FrameError as e:
            raise ProtocolError(str(e)) from e

    def query_signature(self) -> str:
        r = self.transact(b"S")
        if not response_success_identity(r.flag):
            raise ProtocolError(f"signature flag=0x{r.flag:02x}")
        return r.payload.split(b"\x00", 1)[0].decode("ascii", errors="replace")

    def version_info(self) -> str:
        r = self.transact(b"V")
        if not response_success_identity(r.flag):
            raise ProtocolError(f"version flag=0x{r.flag:02x}")
        return r.payload.split(b"\x00", 1)[0].decode("ascii", errors="replace")

    def och_get(self, offset: int = 0, count: int = OCH_BLOCK_SIZE) -> bytes:
        r = self.transact(och_get_payload(offset, count), timeout=3.0)
        if not response_success_identity(r.flag):
            raise ProtocolError(f"och flag=0x{r.flag:02x}")
        if len(r.payload) != count:
            raise ProtocolError(
                f"och length {len(r.payload)} != requested {count}"
            )
        return r.payload

    def page_read_chunk(self, offset: int, count: int) -> bytes:
        r = self.transact(page_read_payload(offset, count), timeout=5.0)
        if not response_success_identity(r.flag):
            raise ProtocolError(f"page read flag=0x{r.flag:02x}")
        if len(r.payload) != count:
            raise ProtocolError(
                f"page read len {len(r.payload)} != {count}"
            )
        return r.payload

    def page_read_all(
        self, page_size: int = PAGE_SIZE, chunk: int = BLOCKING_FACTOR
    ) -> bytes:
        out = bytearray()
        off = 0
        while off < page_size:
            n = min(chunk, page_size - off)
            out.extend(self.page_read_chunk(off, n))
            off += n
            time.sleep(0.01)
        return bytes(out)

    def page_crc32(self, offset: int = 0, count: int = PAGE_SIZE) -> int:
        r = self.transact(page_crc_payload(offset, count), timeout=5.0)
        if len(r.payload) < 4:
            raise ProtocolError(f"CRC payload unexpected: {r.payload.hex()}")
        return struct.unpack(">I", r.payload[:4])[0]

    def page_write_chunk(self, offset: int, data: bytes) -> FrameResponse:
        return self.transact(page_write_payload(offset, data), timeout=5.0)

    def page_write_all(
        self, data: bytes, chunk: int = BLOCKING_FACTOR
    ) -> None:
        if len(data) != PAGE_SIZE:
            raise ValueError(f"expected page size {PAGE_SIZE}, got {len(data)}")
        off = 0
        while off < len(data):
            n = min(chunk, len(data) - off)
            r = self.page_write_chunk(off, data[off : off + n])
            if not response_success_identity(r.flag):
                raise ProtocolError(
                    f"chunk write fail offset={off} flag=0x{r.flag:02x}"
                )
            off += n
            time.sleep(0.01)

    def burn(self) -> FrameResponse:
        r = self.transact(b"B", timeout=10.0)
        if not response_success_burn(r.flag):
            raise ProtocolError(f"burn flag=0x{r.flag:02x} not accepted")
        return r


def u16(buf: bytes, off: int) -> int:
    return struct.unpack_from("<H", buf, off)[0]


def s16(buf: bytes, off: int) -> int:
    return struct.unpack_from("<h", buf, off)[0]


def u32(buf: bytes, off: int) -> int:
    return struct.unpack_from("<I", buf, off)[0]


def decode_och(och: bytes) -> dict:
    flags = u32(och, OFF_FLAGS)
    return {
        "flags": flags,
        "sd_logging_internal": bool(flags & FLAG_SD_LOGGING),
        "needBurn": bool(flags & FLAG_NEED_BURN),
        "isUsbConnected": bool(flags & FLAG_USB_CONNECTED),
        "RPM": u16(och, OFF_RPM),
        "coolant_C": s16(och, OFF_COOLANT) * 0.01,
        "intake_C": s16(och, OFF_INTAKE) * 0.01,
        "TPS_pct": s16(och, OFF_TPS) * 0.01,
        "lambda1": u16(och, OFF_LAMBDA1) * 1e-4,
        "MAP_kPa": u16(och, OFF_MAP) * (1.0 / 30.0),
    }


def poll_for(
    cli: FomeClient,
    seconds: float,
    hz: float,
    on_sample: Callable[[dict, bytes], None] | None = None,
) -> list[dict]:
    """Shared timed och poll loop for realtime + logging phases."""
    period = 1.0 / hz if hz > 0 else 0.0
    end = time.monotonic() + seconds
    samples: list[dict] = []
    t0 = time.monotonic()
    while time.monotonic() < end:
        loop_start = time.monotonic()
        och = cli.och_get(0, OCH_BLOCK_SIZE)
        row = decode_och(och)
        row["t_ms"] = int((time.monotonic() - t0) * 1000)
        samples.append(row)
        if on_sample:
            on_sample(row, och)
        elapsed = time.monotonic() - loop_start
        if period > 0:
            time.sleep(max(0.0, period - elapsed))
    return samples
