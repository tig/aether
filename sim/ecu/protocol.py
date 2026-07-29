"""Aether ECU Sim Protocol (AESP) v0 — line-oriented text over a byte stream.

This is intentionally *not* MegaSquirt newserial binary. It models the same
*operations* (identity/signature, page read, page write to RAM, burn to flash,
CRC, soft power-cycle) so the calibration reader/burner and §17 burn soak can
be validated in pure software. A future TS-class binary bridge can speak the
same store without changing ATM/burn logic.

Framing: one command per line, CR and/or LF terminated. Responses are one line
unless noted. Hex payloads are lowercase hex without spaces.
"""

from __future__ import annotations

from .pages import CalibrationStore


class EcuProtocolError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def _ok(kind: str, *parts: str) -> str:
    if parts:
        return kind + " " + " ".join(parts)
    return kind


def _err(msg: str) -> str:
    return f"ERR {msg}"


def handle_line(store: CalibrationStore, line: str) -> str:
    """Dispatch one command line; return a single response line (no trailing NL)."""
    raw = line.strip()
    if not raw:
        return _err("empty")

    parts = raw.split()
    cmd = parts[0].upper()

    try:
        if cmd == "PING":
            return "PONG"

        if cmd in ("SIGN", "SIGNATURE", "Q"):
            return _ok("SIGN", store.signature)

        if cmd == "PAGES":
            sizes = " ".join(str(p.size) for p in store.pages)
            names = ",".join(p.name for p in store.pages)
            return _ok("PAGES", str(store.page_count), sizes, names)

        if cmd == "R":
            if len(parts) != 4:
                return _err("usage R <page> <off> <len>")
            page_i, off, length = int(parts[1]), int(parts[2]), int(parts[3])
            data = store.page(page_i).read_ram(off, length)
            return _ok("R", "OK", data.hex())

        if cmd == "W":
            if len(parts) != 4:
                return _err("usage W <page> <off> <hex>")
            page_i, off = int(parts[1]), int(parts[2])
            data = bytes.fromhex(parts[3])
            store.page(page_i).write_ram(off, data)
            return _ok("W", "OK", str(len(data)))

        if cmd == "B":
            if len(parts) == 1 or (len(parts) == 2 and parts[1].upper() == "ALL"):
                store.burn(None)
                return _ok("B", "OK", "ALL")
            if len(parts) != 2:
                return _err("usage B [<page>|ALL]")
            page_i = int(parts[1])
            store.burn(page_i)
            return _ok("B", "OK", str(page_i))

        if cmd == "RAMCRC":
            if len(parts) == 1 or (len(parts) == 2 and parts[1].upper() == "ALL"):
                return _ok("RAMCRC", f"{store.all_ram_crc():08x}")
            page_i = int(parts[1])
            return _ok("RAMCRC", str(page_i), f"{store.page(page_i).ram_crc32():08x}")

        if cmd == "FLASHCRC":
            if len(parts) == 1 or (len(parts) == 2 and parts[1].upper() == "ALL"):
                return _ok("FLASHCRC", f"{store.all_flash_crc():08x}")
            page_i = int(parts[1])
            return _ok("FLASHCRC", str(page_i), f"{store.page(page_i).flash_crc32():08x}")

        if cmd in ("POWERCYCLE", "RESET"):
            store.power_cycle()
            return _ok("POWERCYCLE", "OK")

        if cmd == "GOLDEN":
            # Test harness: install known image into RAM and burn.
            store.install_golden()
            return _ok("GOLDEN", "OK", f"{store.all_flash_crc():08x}")

        if cmd == "MUTATE":
            patches = store.apply_mutation_aspects()
            summary = ";".join(
                f"{name}:{page}:{off}:{data.hex()}"
                for name, (page, off, data) in patches.items()
            )
            return _ok("MUTATE", "OK", summary)

        if cmd == "DUMPFLASH":
            # Full flash hex per page, joined with | for one-line response.
            chunks = [bytes(p.flash).hex() for p in store.pages]
            return _ok("DUMPFLASH", "|".join(chunks))

        if cmd == "DUMPRAM":
            chunks = [bytes(p.ram).hex() for p in store.pages]
            return _ok("DUMPRAM", "|".join(chunks))

        return _err(f"unknown {cmd}")

    except (ValueError, IndexError, TypeError) as exc:
        return _err(str(exc).replace(" ", "_")[:120])
