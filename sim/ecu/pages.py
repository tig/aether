"""RAM + flash calibration pages for the software ECU.

Burn copies RAM → flash. Soft power-cycle reloads flash → RAM (unburned
RAM writes are lost). Hard persistence is a flash image file on disk.
"""

from __future__ import annotations

import json
import struct
import zlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


# Fixture definition — small but multi-aspect (scalar / curve / table).
# Layout is sim-native (AESP), not a real FOME map; enough for burn soak.
DEFAULT_SIGNATURE = "AETHER_ECU_SIM_v1"
DEFAULT_PAGES: tuple[tuple[str, int], ...] = (
    ("scalars", 64),  # page 0 — scalars / bitfields
    ("curves", 128),  # page 1 — 1-D curves
    ("tables", 256),  # page 2 — 2-D table cells
)


@dataclass
class Page:
    name: str
    size: int
    ram: bytearray = field(repr=False)
    flash: bytearray = field(repr=False)

    def __init__(self, name: str, size: int, fill: int = 0) -> None:
        self.name = name
        self.size = size
        self.ram = bytearray([fill & 0xFF] * size)
        self.flash = bytearray([fill & 0xFF] * size)

    def read_ram(self, offset: int, length: int) -> bytes:
        self._check_range(offset, length)
        return bytes(self.ram[offset : offset + length])

    def write_ram(self, offset: int, data: bytes) -> None:
        self._check_range(offset, len(data))
        self.ram[offset : offset + len(data)] = data

    def burn(self) -> None:
        self.flash[:] = self.ram

    def reload_from_flash(self) -> None:
        self.ram[:] = self.flash

    def ram_crc32(self) -> int:
        return zlib.crc32(bytes(self.ram)) & 0xFFFFFFFF

    def flash_crc32(self) -> int:
        return zlib.crc32(bytes(self.flash)) & 0xFFFFFFFF

    def raw_equal_flash(self) -> bool:
        return self.ram == self.flash

    def _check_range(self, offset: int, length: int) -> None:
        if offset < 0 or length < 0 or offset + length > self.size:
            raise ValueError(
                f"range out of bounds page={self.name!r} "
                f"off={offset} len={length} size={self.size}"
            )


class CalibrationStore:
    """Full calibration image: definition signature + ordered pages."""

    def __init__(
        self,
        signature: str = DEFAULT_SIGNATURE,
        page_specs: Iterable[tuple[str, int]] | None = None,
        fill: int = 0x00,
    ) -> None:
        self.signature = signature
        specs = list(page_specs) if page_specs is not None else list(DEFAULT_PAGES)
        self.pages: list[Page] = [Page(name, size, fill=fill) for name, size in specs]

    @property
    def page_count(self) -> int:
        return len(self.pages)

    def page(self, index: int) -> Page:
        if index < 0 or index >= len(self.pages):
            raise IndexError(f"page {index} out of range 0..{len(self.pages) - 1}")
        return self.pages[index]

    def burn(self, page_index: int | None = None) -> None:
        if page_index is None:
            for p in self.pages:
                p.burn()
        else:
            self.page(page_index).burn()

    def power_cycle(self) -> None:
        """Soft power-cycle: discard unburned RAM, reload flash → RAM."""
        for p in self.pages:
            p.reload_from_flash()

    def all_ram_crc(self) -> int:
        blob = b"".join(bytes(p.ram) for p in self.pages)
        return zlib.crc32(blob) & 0xFFFFFFFF

    def all_flash_crc(self) -> int:
        blob = b"".join(bytes(p.flash) for p in self.pages)
        return zlib.crc32(blob) & 0xFFFFFFFF

    def snapshot_flash(self) -> dict:
        return {
            "signature": self.signature,
            "pages": [
                {
                    "name": p.name,
                    "size": p.size,
                    "flash_hex": bytes(p.flash).hex(),
                    "flash_crc32": f"{p.flash_crc32():08x}",
                }
                for p in self.pages
            ],
            "all_flash_crc32": f"{self.all_flash_crc():08x}",
        }

    def snapshot_ram(self) -> dict:
        return {
            "signature": self.signature,
            "pages": [
                {
                    "name": p.name,
                    "size": p.size,
                    "ram_hex": bytes(p.ram).hex(),
                    "ram_crc32": f"{p.ram_crc32():08x}",
                }
                for p in self.pages
            ],
            "all_ram_crc32": f"{self.all_ram_crc():08x}",
        }

    def load_flash_from_snapshot(self, snap: dict) -> None:
        if snap.get("signature") != self.signature:
            raise ValueError(
                f"signature mismatch: store={self.signature!r} snap={snap.get('signature')!r}"
            )
        pages = snap["pages"]
        if len(pages) != len(self.pages):
            raise ValueError("page count mismatch")
        for p, raw in zip(self.pages, pages):
            data = bytes.fromhex(raw["flash_hex"])
            if len(data) != p.size:
                raise ValueError(f"page {p.name} size mismatch")
            p.flash[:] = data
            p.ram[:] = data

    def save_flash_file(self, path: Path | str) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.snapshot_flash(), indent=2) + "\n", encoding="utf-8")

    def load_flash_file(self, path: Path | str) -> None:
        path = Path(path)
        snap = json.loads(path.read_text(encoding="utf-8"))
        self.load_flash_from_snapshot(snap)

    def install_golden(self, pattern: bytes | None = None) -> None:
        """Fill RAM with a known golden image and burn it."""
        if pattern is None:
            # Deterministic multi-byte pattern so scalar/curve/table regions differ.
            for i, p in enumerate(self.pages):
                for off in range(p.size):
                    p.ram[off] = (0xA0 + i * 0x10 + (off % 0x10)) & 0xFF
        else:
            for p in self.pages:
                for off in range(p.size):
                    p.ram[off] = pattern[off % len(pattern)]
        self.burn()

    def apply_mutation_aspects(self) -> dict[str, tuple[int, int, bytes]]:
        """Mutate ≥1 scalar, ≥1 curve point, ≥1 table cell. Returns expected patches.

        Each value is (page, offset, data).
        """
        patches: dict[str, tuple[int, int, bytes]] = {
            "scalar": (0, 0, struct.pack("<H", 0xBEEF)),
            "curve": (1, 4, bytes([0xC1, 0xC2, 0xC3, 0xC4])),
            "table": (2, 16, bytes([0xD1, 0xD2])),
        }
        for _name, (page_i, off, data) in patches.items():
            self.page(page_i).write_ram(off, data)
        return patches
