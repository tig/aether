"""CLI orchestrator smoke."""

from __future__ import annotations

import json
from pathlib import Path

from sim.orch.runner import main


def test_runner_all(tmp_path: Path) -> None:
    code = main(["all", "--out", str(tmp_path)])
    assert code == 0
    report = tmp_path / "bench_result.json"
    assert report.is_file()
    data = json.loads(report.read_text(encoding="utf-8"))
    assert data["identity"]["ok"] is True
    assert data["fb"]["ok"] is True
    assert data["burn-soak"]["ok"] is True
    assert (tmp_path / "aether_fb.ppm").is_file()
