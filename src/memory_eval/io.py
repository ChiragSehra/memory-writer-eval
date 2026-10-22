from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_session(path: Path) -> dict[str, Any]:
    if path.suffix == ".json":
        return json.loads(path.read_text())
    return {"session_id": path.stem, "transcript": path.read_text()}


def load_threads(directory: str | Path) -> dict[str, list[dict[str, Any]]]:
    threads: dict[str, list[dict[str, Any]]] = {}
    for path in sorted(Path(directory).glob("*")):
        if path.suffix not in {".json", ".md", ".markdown"}:
            continue
        if path.stem.endswith("__ground_truth"):
            continue
        session = read_session(path)
        thread_id = session.get("thread_id", path.stem.split("__")[0])
        session["session_id"] = session.get("session_id", path.stem)
        threads.setdefault(thread_id, []).append(session)
    for sessions in threads.values():
        sessions.sort(key=lambda item: (item.get("sequence", 0), item["session_id"]))
    return threads


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
