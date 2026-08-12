"""
TS newserial / msEnvelope helpers (pure).

FOME HIL scope (proteus_f7 class):
  request  CRC = IEEE CRC32 over payload only
  response CRC = IEEE CRC32 over flag || payload
  size BE = bytes after size field and before CRC
"""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass


def crc32_ieee(data: bytes) -> int:
    return zlib.crc32(data) & 0xFFFFFFFF


def frame_request(payload: bytes) -> bytes:
    """BE size | payload | BE CRC32(payload)."""
    return (
        struct.pack(">H", len(payload))
        + payload
        + struct.pack(">I", crc32_ieee(payload))
    )


@dataclass(frozen=True)
class FrameResponse:
    flag: int
    payload: bytes
    raw: bytes


class FrameError(ValueError):
    pass


def parse_response(raw: bytes) -> FrameResponse:
    """Parse one complete response buffer (size + flag+payload + crc)."""
    if len(raw) < 2 + 1 + 4:
        raise FrameError(f"response too short: {len(raw)} bytes")
    (size,) = struct.unpack(">H", raw[:2])
    if size < 1:
        raise FrameError(f"invalid size {size}")
    need = 2 + size + 4
    if len(raw) < need:
        raise FrameError(f"truncated response: have {len(raw)} need {need}")
    if len(raw) > need:
        # allow exact only for goldens; callers may slice
        raw = raw[:need]
    flag_and_payload = raw[2 : 2 + size]
    crc_rx = struct.unpack(">I", raw[2 + size : need])[0]
    crc_calc = crc32_ieee(flag_and_payload)
    if crc_rx != crc_calc:
        raise FrameError(
            f"CRC mismatch rx=0x{crc_rx:08x} calc=0x{crc_calc:08x}"
        )
    return FrameResponse(
        flag=flag_and_payload[0],
        payload=flag_and_payload[1:],
        raw=raw,
    )


def response_success_identity(flag: int) -> bool:
    """Signature/version style success flags (MS 0x00 / 0x01)."""
    return flag in (0x00, 0x01)


def response_success_burn(flag: int) -> bool:
    """
    FOME pilot HIL: burn completed with flag 0x04 (and post-condition match).
    Also accept classic 0x00/0x01 if a firmware uses them.
    """
    return flag in (0x00, 0x01, 0x04)


def och_get_payload(offset: int, count: int) -> bytes:
    return b"O" + struct.pack("<HH", offset, count)


def page_read_payload(offset: int, count: int) -> bytes:
    return b"R" + struct.pack("<HH", offset, count)


def page_crc_payload(offset: int, count: int) -> bytes:
    return b"k" + struct.pack("<HH", offset, count)


def page_write_payload(offset: int, data: bytes) -> bytes:
    return b"C" + struct.pack("<HH", offset, len(data)) + data
