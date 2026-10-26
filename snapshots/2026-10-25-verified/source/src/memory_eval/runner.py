from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from .io import load_threads, write_json
from .memory import apply_operations
from .types import MemoryEntry, SessionResult
from .writer import MemoryWriter, prompt_text


def configured_writers(config: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    writers = [("local", config["local"])]
    router = config.get("openrouter", {})
    for model in router.get("models", []):
        if not model.get("enabled", True):
            continue
        settings = {k: v for k, v in router.items() if k != "models"}
        settings.update(model)
        writers.append((f"openrouter:{model['name']}", settings))
    return writers


def run_models(config: dict[str, Any], input_dir: str, limit_threads: int | None = None, limit_sessions: int | None = None, output_root: str = "runs", resume_dir: str | None = None, model_names: set[str] | None = None, retry_errors: bool = False) -> Path:
    if resume_dir:
        run_dir = Path(resume_dir)
        if not run_dir.is_dir():
            raise ValueError(f"Resume directory does not exist: {run_dir}")
    else:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        run_dir = Path(output_root) / stamp
        run_dir.mkdir(parents=True)
    prompt = prompt_text()
    threads = load_threads(input_dir)
    if limit_threads:
        threads = dict(list(threads.items())[:limit_threads])
    if limit_sessions:
        threads = {thread_id: sessions[:limit_sessions] for thread_id, sessions in threads.items()}
    all_results: list[dict[str, Any]] = []
    for name, settings in configured_writers(config):
        selected = model_names is None or name in model_names
        writer = MemoryWriter(name, settings, config["runtime"])
        for thread_id, sessions in threads.items():
            store: list[MemoryEntry] = []
            recompute_downstream = False
            for session in sessions:
                raw_path = run_dir / "raw" / name / f"{thread_id}__{session['session_id']}.json"
                if raw_path.exists():
                    prior = json.loads(raw_path.read_text())
                    should_retry = selected and retry_errors and (recompute_downstream or bool(prior.get("call", {}).get("error")))
                    if not should_retry:
                        store = [MemoryEntry(**entry) for entry in prior["memory_after"]]
                        all_results.append(prior)
                        continue
                    recompute_downstream = True
                elif not selected:
                    continue
                elif retry_errors:
                    # A missing checkpoint in a resumed thread also invalidates
                    # any cached stores that follow it.
                    recompute_downstream = True
                before = [entry.__dict__ for entry in store]
                ops, call = writer.write(prompt, json.dumps(before, ensure_ascii=False), session["transcript"])
                store = apply_operations(store, ops, session["session_id"])
                record = SessionResult(
                    model=name,
                    thread_id=thread_id,
                    session_id=session["session_id"],
                    memory_before=before,
                    memory_after=[entry.__dict__ for entry in store],
                    operations=[op.__dict__ for op in ops],
                    call=call.as_dict(),
                )
                record_dict = {**record.__dict__, "transcript_excerpt": session["transcript"][:240]}
                all_results.append(record_dict)
                write_json(raw_path, record_dict)
    write_json(run_dir / "results.json", all_results)
    write_report(run_dir, all_results, config)
    return run_dir


def _cost(call: dict[str, Any], pricing: dict[str, Any]) -> float | None:
    if pricing.get("input") is None or pricing.get("output") is None:
        return None
    return ((call.get("input_tokens") or 0) * pricing["input"] + (call.get("output_tokens") or 0) * pricing["output"]) / 1_000_000


def write_report(run_dir: Path, results: list[dict[str, Any]], config: dict[str, Any]) -> None:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in results:
        grouped[result["model"]].append(result)
    lines = ["# Memory writer evaluation report", "", "## Per-model metrics", "", "| Model | Sessions | Valid JSON | Invalid JSON rate | Retried | Median TTFT | Median total | Decode tok/s | Estimated API cost |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for name, rows in grouped.items():
        calls = [row["call"] for row in rows]
        valid = sum(bool(call.get("json_valid")) for call in calls)
        retried = sum((call.get("retries") or 0) > 0 for call in calls)
        ttfts = sorted(c["latency_ttft_s"] for c in calls if c.get("latency_ttft_s") is not None)
        totals = sorted(c["latency_total_s"] for c in calls)
        rates = sorted((c["output_tokens"] / c["latency_total_s"]) for c in calls if c.get("output_tokens") and c.get("latency_total_s"))
        median = lambda values: values[len(values)//2] if values else None
        settings = dict(configured_writers(config)).get(name, {})
        costs = [_cost(c, settings.get("pricing_usd_per_million_tokens", {})) for c in calls] if name.startswith("openrouter:") else []
        cost_text = "N/A (prices unset)" if name.startswith("openrouter:") and any(c is None for c in costs) else (f"${sum(costs):.6f}" if costs else "N/A")
        fmt = lambda value: f"{value:.3f}s" if value is not None else "N/A"
        rate = median(rates)
        rate_text = f"{rate:.1f}" if rate is not None else "N/A"
        invalid_rate = 1 - valid / len(rows) if rows else 0
        lines.append(f"| {name} | {len(rows)} | {valid}/{len(rows)} | {invalid_rate:.1%} | {retried} | {fmt(median(ttfts))} | {fmt(median(totals))} | {rate_text} | {cost_text} |")
    failures = [(row["model"], row["thread_id"], row["session_id"], row["call"].get("error")) for row in results if row["call"].get("error")]
    lines += ["", "## Worst errors", ""]
    if failures:
        lines.extend(f"- {model}, {thread}/{session}: {error}" for model, thread, session, error in failures[:6])
    else:
        lines.append("- No transport or invalid-JSON failures. Run `score-synthetic` to add semantic error examples.")
    lines += ["", "## Verdict", "", "_Fill this in after reviewing quality, latency, and cost._", ""]
    (run_dir / "report.md").write_text("\n".join(lines))


def export_blind_sheet(run_dir: str | Path, output: str | Path = "scoring/blind_sheet.csv", input_dir: str | Path = "data/synthetic") -> tuple[Path, Path]:
    """Export only final stores, with a distinct opaque code per model.

    Earlier versions mixed entries from intermediate stores and grouped every
    remote model under one code. That could both penalize corrected facts and
    make a multi-model blind review impossible.
    """
    rows = json.loads((Path(run_dir) / "results.json").read_text())
    items = []
    threads = load_threads(input_dir)
    histories: dict[tuple[str, str], str] = {}
    for thread_id, sessions in threads.items():
        history = []
        for session in sessions:
            history.append(session["transcript"])
            histories[(thread_id, session["session_id"])] = "\n\n".join(history)
    excerpts = {(row["model"], row["thread_id"], row["session_id"]): row.get("transcript_excerpt", "") for row in rows}
    final_rows: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        # Results are emitted in session order, so later rows are the final
        # checkpoint for a model/thread pair.
        final_rows[(row["model"], row["thread_id"])] = row
    for result in final_rows.values():
        history = histories.get((result["thread_id"], result["session_id"]))
        if history is None:
            raise ValueError(f"Missing transcript history for {result['thread_id']}/{result['session_id']} in {input_dir}")
        for entry in result["memory_after"]:
            excerpt = excerpts.get((result["model"], result["thread_id"], entry["source_session"]), "")
            items.append({
                "entry": entry["content"],
                "source_session_excerpt": excerpt,
                "checkpoint_session": result["session_id"],
                "transcript_history": history,
                "model": result["model"],
            })
    import random
    rng = random.SystemRandom()
    rng.shuffle(items)
    models = sorted({item["model"] for item in items})
    codes = {model: f"M{index:02d}" for index, model in enumerate(rng.sample(models, len(models)), 1)}
    output_path = Path(output)
    key_path = output_path.with_name(output_path.stem + "_key.csv")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["row_id", "entry", "source_session_excerpt", "checkpoint_session", "transcript_history", "correct?(1-5)", "should_be_stored?(y/n)", "notes"])
        writer.writeheader()
        for index, item in enumerate(items, 1):
            writer.writerow({"row_id": index, "entry": item["entry"], "source_session_excerpt": item["source_session_excerpt"], "checkpoint_session": item["checkpoint_session"], "transcript_history": item["transcript_history"]})
    with key_path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["row_id", "random_code", "model"])
        writer.writeheader()
        for index, item in enumerate(items, 1):
            writer.writerow({"row_id": index, "random_code": codes[item["model"]], "model": item["model"]})
    return output_path, key_path
