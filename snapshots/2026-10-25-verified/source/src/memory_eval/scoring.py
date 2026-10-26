from __future__ import annotations

import csv
from pathlib import Path


def merge_human_scores(sheet: str | Path, key: str | Path, output: str | Path) -> Path:
    with Path(sheet).open(newline="") as file:
        scores = {row["row_id"]: row for row in csv.DictReader(file)}
    with Path(key).open(newline="") as file:
        keys = list(csv.DictReader(file))
    fields = list(scores[next(iter(scores))].keys()) + ["random_code", "model"] if scores else ["row_id", "random_code", "model"]
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for row in keys:
            writer.writerow({**scores.get(row["row_id"], {}), **row})
    return destination
