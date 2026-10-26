from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from .io import load_threads, write_json
from .runner import configured_writers


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def create_snapshot(run_dir: str | Path, output_dir: str | Path, config: dict[str, Any], artifacts: dict[str, str | Path]) -> Path:
    run_path = Path(run_dir)
    results = json.loads((run_path / "results.json").read_text())
    threads = load_threads("data/synthetic")
    expected = len(configured_writers(config)) * sum(len(sessions) for sessions in threads.values())
    if len(results) != expected:
        raise ValueError(f"Incomplete run: {len(results)} results, expected {expected}")
    destination = Path(output_dir)
    if destination.exists():
        raise FileExistsError(f"Snapshot already exists: {destination}")
    source_files = sorted(Path("src/memory_eval").glob("*.py")) + sorted(Path("data/synthetic").glob("*.json")) + [Path("prompts/memory_writer.md"), Path("config.yaml"), Path("pyproject.toml")]
    source_hashes = {str(path): _sha256(path) for path in source_files}
    source_artifacts = {"results.json": run_path / "results.json", "report.md": run_path / "report.md", "synthetic_scores.json": run_path / "synthetic_scores.json"}
    source_artifacts.update({name: Path(path) for name, path in artifacts.items()})
    if any(not path.is_file() for path in source_artifacts.values()):
        raise ValueError("Snapshot artifact is missing")
    destination.mkdir(parents=True)
    for source in source_files:
        bundled = destination / "source" / source
        bundled.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, bundled)
    artifact_hashes = {}
    for name, source in source_artifacts.items():
        if Path(name).name != name:
            raise ValueError(f"Snapshot artifact name must be a basename: {name}")
        shutil.copy2(source, destination / name)
        artifact_hashes[name] = _sha256(destination / name)
    git_head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    manifest = {
        "created_at_ist": datetime.now(ZoneInfo("Asia/Kolkata")).isoformat(),
        "run_dir": str(run_path),
        "git_head": git_head,
        "source_hashes": source_hashes,
        "artifact_hashes": artifact_hashes,
        "corpus": {"threads": len(threads), "sessions": sum(len(sessions) for sessions in threads.values())},
        "models": [{"label": name, "model_id": settings["model"]} for name, settings in configured_writers(config)],
        "runtime": config["runtime"],
        "judge": config["judge"],
        "writer_valid": sum(bool(row["call"].get("json_valid")) for row in results),
        "writer_total": len(results),
    }
    write_json(destination / "manifest.json", manifest)
    return destination / "manifest.json"


def verify_snapshot(snapshot_dir: str | Path) -> dict[str, Any]:
    root = Path(snapshot_dir)
    manifest = json.loads((root / "manifest.json").read_text())
    for name, expected in manifest["artifact_hashes"].items():
        if _sha256(root / name) != expected:
            raise ValueError(f"Snapshot artifact changed: {name}")
    for name, expected in manifest["source_hashes"].items():
        if _sha256(root / "source" / name) != expected:
            raise ValueError(f"Snapshot bundled source changed: {name}")
        if _sha256(Path(name)) != expected:
            raise ValueError(f"Snapshot source changed: {name}")
    results = json.loads((root / "results.json").read_text())
    if len(results) != manifest["writer_total"] or sum(bool(row["call"].get("json_valid")) for row in results) != manifest["writer_valid"]:
        raise ValueError("Snapshot result coverage changed")
    return manifest
