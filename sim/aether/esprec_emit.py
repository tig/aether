"""ESPREC1 frame emit matching tig/esprec wire protocol (host-side twin).

CRC32 (IEEE) over canonical meta prefix + raster:
  w=W|h=H|fmt=F|pack=P|nbytes=N| + raster_bytes

Raster packing: rgb565be + spi_be (LE memory words as sent to SPI —
byte-swapped logical 565 with R in high bits of the logical word).
"""

from __future__ import annotations

import base64
import binascii
import struct
from typing import Iterable


FMT = "rgb565be"
PACK = "spi_be"


def canonical_meta_prefix(w: int, h: int, fmt: str, pack: str, nbytes: int) -> bytes:
    return f"w={w}|h={h}|fmt={fmt}|pack={pack}|nbytes={nbytes}|".encode("ascii")


def crc_esprec1(w: int, h: int, fmt: str, pack: str, nbytes: int, raster: bytes) -> int:
    return binascii.crc32(canonical_meta_prefix(w, h, fmt, pack, nbytes) + raster) & 0xFFFFFFFF


def logical_rgb565_le_to_spi_be(raster_le: bytes) -> bytes:
    """Convert LE logical RGB565 words → spi_be packing used by esprec."""
    if len(raster_le) % 2 != 0:
        raise ValueError("odd raster length")
    out = bytearray(len(raster_le))
    for i in range(0, len(raster_le), 2):
        logical = raster_le[i] | (raster_le[i + 1] << 8)
        wire = ((logical & 0xFF) << 8) | ((logical >> 8) & 0xFF)
        out[i] = wire & 0xFF
        out[i + 1] = (wire >> 8) & 0xFF
    return bytes(out)


def encode_b64_lines(data: bytes, cols: int = 76) -> list[str]:
    b64 = base64.b64encode(data).decode("ascii")
    return [b64[i : i + cols] for i in range(0, len(b64), cols)]


def build_esprec1_lines(
    w: int,
    h: int,
    raster_spi_be: bytes,
    *,
    seq: int | None = None,
    ts_ms: int | None = None,
) -> list[str]:
    nbytes = len(raster_spi_be)
    expected = w * h * 2
    if nbytes != expected:
        raise ValueError(f"raster {nbytes} != {w}x{h}*2={expected}")
    crc = crc_esprec1(w, h, FMT, PACK, nbytes, raster_spi_be)
    header = (
        f"ESPREC1 w={w} h={h} fmt={FMT} pack={PACK} enc=b64 "
        f"nbytes={nbytes} crc=0x{crc:08x}"
    )
    if seq is not None:
        header += f" seq={seq}"
    if ts_ms is not None:
        header += f" ts_ms={ts_ms}"
    end = f"ESPREC1_END crc=0x{crc:08x}"
    return [header, *encode_b64_lines(raster_spi_be), end]


def verify_esprec1_lines(lines: Iterable[str]) -> tuple[int, int, bytes]:
    """Parse/verify a shot response; return (w, h, raster). Fail closed."""
    lines = list(lines)
    if not lines:
        raise ValueError("empty frame")
    header = lines[0].strip()
    if not header.startswith("ESPREC1 "):
        raise ValueError(f"not ESPREC1 header: {header[:60]!r}")
    # light parse
    fields = dict(part.split("=", 1) for part in header.split()[1:] if "=" in part)
    w = int(fields["w"])
    h = int(fields["h"])
    fmt = fields["fmt"]
    pack = fields["pack"]
    nbytes = int(fields["nbytes"])
    crc = int(fields["crc"], 16)
    if lines[-1].strip() != f"ESPREC1_END crc=0x{crc:08x}":
        # allow case variations on hex
        if not lines[-1].strip().upper().startswith("ESPREC1_END CRC=0X"):
            raise ValueError(f"bad end: {lines[-1]!r}")
    b64_parts = [ln.strip() for ln in lines[1:-1] if ln.strip()]
    s = "".join(b64_parts)
    s += "=" * ((4 - (len(s) % 4)) % 4)
    raster = base64.b64decode(s, validate=False)
    if len(raster) != nbytes:
        raise ValueError(f"raster len {len(raster)} != nbytes {nbytes}")
    calc = crc_esprec1(w, h, fmt, pack, nbytes, raster)
    if calc != crc:
        raise ValueError(f"crc mismatch header=0x{crc:08x} calc=0x{calc:08x}")
    return w, h, raster


def solid_spi_be(w: int, h: int, r: int, g: int, b: int) -> bytes:
    r5 = (r >> 3) & 0x1F
    g6 = (g >> 2) & 0x3F
    b5 = (b >> 3) & 0x1F
    logical = (r5 << 11) | (g6 << 5) | b5
    wire = ((logical & 0xFF) << 8) | ((logical >> 8) & 0xFF)
    pixel = struct.pack("<H", wire)
    return pixel * (w * h)
