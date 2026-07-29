"""Deterministic software framebuffer for esprec-style capture without a panel.

QEMU / metal will eventually serve a real (or QEMU virtual RGB) buffer through
esprec. Until then, this synthetic pattern is the honest sim surface: known
pixels, stable CRC, exportable as PPM for host-side eyes.
"""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SyntheticFramebuffer:
    """RGB565 little-endian raster with a fixed test pattern."""

    width: int = 128
    height: int = 64
    pattern_id: int = 1

    def __post_init__(self) -> None:
        self._pixels = self._render()

    @property
    def nbytes(self) -> int:
        return self.width * self.height * 2

    def _render(self) -> bytearray:
        buf = bytearray(self.nbytes)
        for y in range(self.height):
            for x in range(self.width):
                # Banded pattern + pattern_id so captures are distinguishable.
                r5 = (x * 31) // max(self.width - 1, 1)
                g6 = (y * 63) // max(self.height - 1, 1)
                b5 = (self.pattern_id * 7) & 0x1F
                rgb565 = ((r5 & 0x1F) << 11) | ((g6 & 0x3F) << 5) | (b5 & 0x1F)
                off = (y * self.width + x) * 2
                struct.pack_into("<H", buf, off, rgb565)
        return buf

    def set_pattern(self, pattern_id: int) -> None:
        self.pattern_id = int(pattern_id)
        self._pixels = self._render()

    def rgb565(self) -> bytes:
        """Logical RGB565 little-endian words (R in high bits of each word)."""
        return bytes(self._pixels)

    def rgb565_spi_be(self) -> bytes:
        """esprec pack=spi_be: LE memory words as sent to SPI (byte-swapped logical)."""
        raw = self.rgb565()
        out = bytearray(len(raw))
        for i in range(0, len(raw), 2):
            logical = raw[i] | (raw[i + 1] << 8)
            wire = ((logical & 0xFF) << 8) | ((logical >> 8) & 0xFF)
            out[i] = wire & 0xFF
            out[i + 1] = (wire >> 8) & 0xFF
        return bytes(out)

    def crc32(self) -> int:
        return zlib.crc32(self.rgb565()) & 0xFFFFFFFF

    def to_ppm(self, path: Path | str) -> None:
        """Write 8-bit RGB PPM (P6) expanded from RGB565."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = self.rgb565()
        rgb = bytearray(self.width * self.height * 3)
        for i in range(self.width * self.height):
            (v,) = struct.unpack_from("<H", raw, i * 2)
            r = ((v >> 11) & 0x1F) * 255 // 31
            g = ((v >> 5) & 0x3F) * 255 // 63
            b = (v & 0x1F) * 255 // 31
            rgb[i * 3 : i * 3 + 3] = bytes((r, g, b))
        header = f"P6\n{self.width} {self.height}\n255\n".encode("ascii")
        path.write_bytes(header + bytes(rgb))

    def meta_line(self) -> str:
        return (
            f"FB {self.width}x{self.height} rgb565le "
            f"pattern={self.pattern_id} crc32={self.crc32():08x} "
            f"bytes={self.nbytes}"
        )
