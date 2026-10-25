from __future__ import annotations

import csv
import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Any

from .blind_judge import _digest
from .io import load_threads
from .memory import apply_operations
from .types import MemoryEntry, Operation


def export_write_sheet(run_dir: str | Path, input_dir: str | Path, output: str | Path) -> tuple[Path, Path]:
    """Blind every applied add/update operation, including later deleted writes."""
    threads = load_threads(input_dir)
    histories: dict[tuple[str, str], str] = {}
    for thread_id, sessions in threads.items():
        history = []
        for session in sessions:
            history.append(session["transcript"])
            histories[(thread_id, session["session_id"])] = "\n\n".join(history)

    results = json.loads((Path(run_dir) / "results.json").read_text())
    events: list[dict[str, Any]] = []
    for result in results:
        store = [MemoryEntry(**entry) for entry in result["memory_before"]]
        history = histories.get((result["thread_id"], result["session_id"]))
        if history is None:
            raise ValueError(f"Missing transcript history for {result['thread_id']}/{result['session_id']} in {input_dir}")
        for operation_index, raw in enumerate(result["operations"]):
            op = Operation(**raw)
            has_content = bool(op.content and op.content.strip())
            applied = (op.op == "add" and has_content) or (op.op == "update" and op.id in {entry.id for entry in store} and has_content)
            store = apply_operations(store, [op], result["session_id"])
            if applied:
                entry = store[-1] if op.op == "add" else next(entry for entry in store if entry.id == op.id)
                events.append({
                    "entry": entry.content,
                    "operation_kind": op.op,
                    "checkpoint_session": result["session_id"],
                    "transcript_history": history,
                    "model": result["model"],
                    "thread_id": result["thread_id"],
                    "operation_index": operation_index,
                })
        if [entry.__dict__ for entry in store] != result["memory_after"]:
            raise ValueError(f"Operation replay disagrees with stored result for {result['model']}/{result['thread_id']}/{result['session_id']}")

    rng = random.SystemRandom()
    rng.shuffle(events)
    destination = Path(output)
    key_path = destination.with_name(destination.stem + "_key.csv")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["row_id", "entry", "operation_kind", "checkpoint_session", "transcript_history"])
        writer.writeheader()
        for index, event in enumerate(events, 1):
            writer.writerow({"row_id": index, **{key: event[key] for key in ("entry", "operation_kind", "checkpoint_session", "transcript_history")}})
    with key_path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["row_id", "model", "thread_id", "checkpoint_session", "operation_index"])
        writer.writeheader()
        for index, event in enumerate(events, 1):
            writer.writerow({"row_id": index, **{key: event[key] for key in ("model", "thread_id", "checkpoint_session", "operation_index")}})
    return destination, key_path


def report_write_support(sheet: str | Path, key: str | Path, scores: str | Path, output: str | Path) -> Path:
    with Path(sheet).open(newline="") as file:
        writes = {row["row_id"]: row for row in csv.DictReader(file)}
    with Path(key).open(newline="") as file:
        identities = {row["row_id"]: row for row in csv.DictReader(file)}
    with Path(scores).open(newline="") as file:
        judgments = {row["row_id"]: row for row in csv.DictReader(file)}
    if writes.keys() != identities.keys() or not set(judgments).issubset(writes):
        raise ValueError("Write sheet, identity key, and judge scores disagree on row IDs")
    if any(score.get("input_sha256") != _digest(writes[row_id]) for row_id, score in judgments.items()):
        raise ValueError("Judge scores do not match the write sheet content")
    totals: dict[str, dict[str, int]] = defaultdict(lambda: {"writes": 0, "scored": 0, "invented": 0, "uncertain": 0, "supported": 0, "supported_low_value": 0})
    for row_id in writes:
        model = identities[row_id]["model"]
        total = totals[model]
        total["writes"] += 1
        score = judgments.get(row_id)
        if not score or score["error"]:
            continue
        total["scored"] += 1
        if score["support"] == "unsupported":
            total["invented"] += 1
        elif score["support"] == "uncertain":
            total["uncertain"] += 1
        elif score["support"] == "supported":
            total["supported"] += 1
            if score["should_be_stored"] == "no":
                total["supported_low_value"] += 1
    lines = [
        "# Invented facts as a share of writes",
        "",
        "A write is an applied `add` or `update` operation. Deletes, noops, invalid references, and empty-content operations are excluded. Every applied write is counted even if later changed or deleted. A write with any unsupported detail is labeled unsupported. `Supported but not worth storing` counts facts the judge found grounded in user statements but transient, redundant, or otherwise low-value for long-term memory. These are automated second-judge labels; review ambiguous cases before treating the rates as ground truth.",
        "",
        "| Model | Writes | Judge coverage | Unsupported / writes | Supported but not worth storing / writes | Uncertain / writes |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for model, total in sorted(totals.items()):
        denominator = total["writes"]
        lines.append(f"| {model} | {denominator} | {total['scored']}/{denominator} | {total['invented']}/{denominator} ({total['invented']/denominator:.1%}) | {total['supported_low_value']}/{denominator} ({total['supported_low_value']/denominator:.1%}) | {total['uncertain']}/{denominator} ({total['uncertain']/denominator:.1%}) |")
    overall = {key: sum(total[key] for total in totals.values()) for key in ("writes", "scored", "invented", "uncertain", "supported_low_value")}
    if overall["writes"]:
        denominator = overall["writes"]
        lines.append(f"| **All models** | {denominator} | {overall['scored']}/{denominator} | {overall['invented']}/{denominator} ({overall['invented']/denominator:.1%}) | {overall['supported_low_value']}/{denominator} ({overall['supported_low_value']/denominator:.1%}) | {overall['uncertain']}/{denominator} ({overall['uncertain']/denominator:.1%}) |")
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(lines) + "\n")
    return destination
