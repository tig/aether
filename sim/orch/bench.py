"""In-process software bench: ECU + Aether + host client.

Preferred path for CI: no subprocesses, no QEMU, no USB — pure Python with
the same wire protocols the multi-process desk layout uses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..aether.device import AetherDevice, AetherHostClient, AetherServer
from ..ecu.client import EcuClient
from ..ecu.pages import CalibrationStore
from ..ecu.server import EcuServer


@dataclass
class BurnSoakResult:
    ok: bool
    steps: list[str] = field(default_factory=list)
    error: str | None = None
    operator_flash_crc: str | None = None
    golden_flash_crc: str | None = None
    mutated_flash_crc: str | None = None
    final_flash_crc: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "steps": self.steps,
            "error": self.error,
            "operator_flash_crc": self.operator_flash_crc,
            "golden_flash_crc": self.golden_flash_crc,
            "mutated_flash_crc": self.mutated_flash_crc,
            "final_flash_crc": self.final_flash_crc,
        }


class SimBench:
    """Context manager wiring ECU sim ← Aether sim ← host client."""

    def __init__(self, out_dir: Path | str | None = None) -> None:
        self.out_dir = Path(out_dir) if out_dir else Path("sim/out")
        self.ecu_server: EcuServer | None = None
        self.aether_server: AetherServer | None = None
        self.host: AetherHostClient | None = None
        self.boot_identity: str | None = None

    def __enter__(self) -> "SimBench":
        self.out_dir.mkdir(parents=True, exist_ok=True)
        store = CalibrationStore()
        # Leave a non-golden "operator" image so restore is meaningful.
        for p in store.pages:
            for i in range(p.size):
                p.ram[i] = (0x10 + i) & 0xFF
            p.burn()

        self.ecu_server = EcuServer(store=store)
        self.ecu_server.start()

        device = AetherDevice(
            ecu_host="127.0.0.1",
            ecu_port=self.ecu_server.port,
        )
        self.aether_server = AetherServer(device=device)
        self.aether_server.start()

        self.host = AetherHostClient("127.0.0.1", self.aether_server.port)
        self.boot_identity = self.host.connect()
        return self

    def __exit__(self, *args: object) -> None:
        if self.host:
            self.host.close()
        if self.aether_server:
            self.aether_server.stop()
        if self.ecu_server:
            self.ecu_server.stop()

    def cmd(self, line: str) -> str:
        assert self.host is not None
        return self.host.cmd(line)

    def direct_ecu(self) -> EcuClient:
        assert self.ecu_server is not None
        return EcuClient("127.0.0.1", self.ecu_server.port)


def burn_soak(bench: SimBench) -> BurnSoakResult:
    """Issue #4 §17.2-shaped sequence through the Aether device (software).

    B0 bind → B1 backup → B2 golden+burn → B3 power-cycle → B4 mutate →
    B5 burn → B6 verify aspects → B8 restore → B9 final.
    """
    result = BurnSoakResult(ok=False)
    h = bench.cmd

    def step(name: str, resp: str, predicate: bool) -> None:
        result.steps.append(f"{name}: {resp}")
        if not predicate:
            raise AssertionError(f"{name} failed: {resp}")

    try:
        # B0 — bind / signature
        resp = h("ecu.sign")
        step("B0", resp, resp.startswith("OK AETHER_ECU_SIM"))

        # B1 — operator backup
        resp = h("ecu.backup")
        step("B1", resp, resp.startswith("OK backup"))
        result.operator_flash_crc = resp.split("flash_crc=")[-1].strip()

        # B2 — golden clean image + burn (GOLDEN does both)
        resp = h("ecu.golden")
        step("B2", resp, resp.startswith("OK golden"))
        result.golden_flash_crc = resp.split("flash_crc=")[-1].strip()
        # Raw-equals: RAM CRC == FLASH CRC
        ram = h("ecu.ramcrc")
        flash = h("ecu.flashcrc")
        step(
            "B2-readback",
            f"{ram} / {flash}",
            ram.startswith("OK ")
            and flash.startswith("OK ")
            and ram.split()[1] == flash.split()[1]
            and ram.split()[1] == result.golden_flash_crc,
        )

        # B3 — power-cycle; image must still equal golden
        resp = h("ecu.powercycle")
        step("B3", resp, resp.startswith("OK powercycle"))
        flash = h("ecu.flashcrc")
        ram = h("ecu.ramcrc")
        step(
            "B3-persist",
            f"{ram} / {flash}",
            ram.split()[1] == result.golden_flash_crc
            and flash.split()[1] == result.golden_flash_crc,
        )

        # B4 — mutate scalar + curve + table in RAM + raw readback of one aspect
        resp = h("ecu.mutate")
        step("B4", resp, "MUTATE OK" in resp or resp.startswith("OK MUTATE"))
        # Scalar at page0 off0: little-endian 0xBEEF → hex efbe
        scalar = h("ecu.read 0 0 2")
        step("B4-scalar", scalar, scalar.lower().startswith("ok efbe"))

        # B5 — burn mutated
        resp = h("ecu.burn")
        step("B5", resp, resp.startswith("OK burned"))
        result.mutated_flash_crc = resp.split("flash_crc=")[-1].strip()
        if result.mutated_flash_crc == result.golden_flash_crc:
            raise AssertionError("mutated CRC unexpectedly equals golden")

        # B6 — re-read aspects differ from golden as intended
        scalar = h("ecu.read 0 0 2")
        curve = h("ecu.read 1 4 4")
        table = h("ecu.read 2 16 2")
        step("B6-scalar", scalar, scalar.lower().startswith("ok efbe"))
        step("B6-curve", curve, curve.lower().startswith("ok c1c2c3c4"))
        step("B6-table", table, table.lower().startswith("ok d1d2"))

        # B7 — optional second power-cycle
        resp = h("ecu.powercycle")
        step("B7", resp, resp.startswith("OK powercycle"))
        scalar = h("ecu.read 0 0 2")
        step("B7-persist", scalar, scalar.lower().startswith("ok efbe"))

        # B8 — restore operator backup
        resp = h("ecu.restore")
        step("B8", resp, resp.startswith("OK restored"))
        result.final_flash_crc = resp.split("flash_crc=")[-1].strip()
        if result.final_flash_crc != result.operator_flash_crc:
            raise AssertionError(
                f"restore CRC {result.final_flash_crc} != "
                f"operator {result.operator_flash_crc}"
            )

        # B9 — final re-read matches operator
        flash = h("ecu.flashcrc")
        step(
            "B9",
            flash,
            flash.startswith("OK ") and flash.split()[1] == result.operator_flash_crc,
        )

        result.ok = True
        return result

    except Exception as exc:  # noqa: BLE001
        result.error = str(exc)
        result.ok = False
        # Best-effort restore so the sim is left clean for following tests.
        try:
            h("ecu.restore")
            result.steps.append("teardown: restore attempted")
        except Exception as restore_exc:  # noqa: BLE001
            result.steps.append(f"teardown: restore failed: {restore_exc}")
        return result
