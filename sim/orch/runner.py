"""CLI entry: run software bench scenarios."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .bench import SimBench, burn_soak


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Aether software bench orchestrator")
    p.add_argument(
        "scenario",
        choices=("burn-soak", "identity", "fb", "all"),
        help="Scenario to run",
    )
    p.add_argument(
        "--out",
        default="sim/out",
        help="Artifact directory (fb ppm, result json)",
    )
    args = p.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    scenarios = (
        ["identity", "fb", "burn-soak"] if args.scenario == "all" else [args.scenario]
    )
    failed = 0
    results: dict[str, object] = {}

    with SimBench(out_dir=out) as bench:
        for name in scenarios:
            if name == "identity":
                boot = bench.boot_identity or ""
                knock = bench.cmd("identity")
                ok = boot.startswith("fw_name=AETHER") and knock == boot
                results["identity"] = {"ok": ok, "boot": boot, "knock": knock}
                print(f"[identity] ok={ok} boot={boot!r} knock={knock!r}")
                if not ok:
                    failed += 1

            elif name == "fb":
                ppm = out / "aether_fb.ppm"
                meta = bench.cmd("fb.meta")
                written = bench.cmd(f"fb.ppm {ppm.as_posix()}")
                ok = (
                    meta.startswith("OK FB ")
                    and written.startswith("OK wrote")
                    and ppm.is_file()
                    and ppm.stat().st_size > 64
                )
                results["fb"] = {
                    "ok": ok,
                    "meta": meta,
                    "written": written,
                    "path": str(ppm),
                    "bytes": ppm.stat().st_size if ppm.is_file() else 0,
                }
                print(f"[fb] ok={ok} {meta}")
                if not ok:
                    failed += 1

            elif name == "burn-soak":
                result = burn_soak(bench)
                results["burn-soak"] = result.as_dict()
                print(f"[burn-soak] ok={result.ok}")
                for s in result.steps:
                    print(f"  {s}")
                if result.error:
                    print(f"  ERROR: {result.error}", file=sys.stderr)
                if not result.ok:
                    failed += 1

    report = out / "bench_result.json"
    report.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {report}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
