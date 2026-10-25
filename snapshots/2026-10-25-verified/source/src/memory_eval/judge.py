from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .types import CallResult
from .writer import MemoryWriter
from .runner import configured_writers


JUDGE_PROMPT = """You judge one memory-store checkpoint against explicit ground truth. Return only JSON with integer fields: expected_facts, recalled_facts, hallucinated_entries, duplicate_entries, stale_entries, and an errors array of short strings. Count semantic equivalents as matches. Hallucinations are entries not supported by the expected facts. Duplicates restate the same fact. Stale entries conflict with a replacement fact. Judge only this checkpoint: a fact that is correct at this checkpoint must not be treated as stale because it changes in a later session."""

JUDGE_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "memory_score",
        "schema": {
            "type": "object",
            "properties": {
                "expected_facts": {"type": "integer", "minimum": 0},
                "recalled_facts": {"type": "integer", "minimum": 0},
                "hallucinated_entries": {"type": "integer", "minimum": 0},
                "duplicate_entries": {"type": "integer", "minimum": 0},
                "stale_entries": {"type": "integer", "minimum": 0},
                "errors": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["expected_facts", "recalled_facts", "hallucinated_entries", "duplicate_entries", "stale_entries", "errors"],
            "additionalProperties": False,
        },
    },
}


def score_synthetic(run_dir: str | Path, config: dict[str, Any], synthetic_dir: str | Path = "data/synthetic", retry_errors: bool = False) -> Path:
    run_path = Path(run_dir)
    results = json.loads((run_path / "results.json").read_text())
    ground_truths = {p.stem.removesuffix("__ground_truth"): json.loads(p.read_text()) for p in Path(synthetic_dir).glob("*__ground_truth.json")}
    expected_by_checkpoint = {
        (thread_id, checkpoint["session_id"]): checkpoint["ideal_memory"]
        for thread_id, truth in ground_truths.items()
        for checkpoint in truth["after_each_session"]
    }
    writer_settings = dict(configured_writers(config))
    judge_name = f"openrouter:{config['judge']['name']}"
    if judge_name not in writer_settings:
        raise ValueError("judge.name must match an entry under openrouter.models")
    judge_runtime = {**config["runtime"], "max_output_tokens": config["judge"].get("max_output_tokens", config["runtime"].get("max_output_tokens", 1000)), "reasoning_effort": config["judge"].get("reasoning_effort", "low")}
    judge = MemoryWriter(judge_name, writer_settings[judge_name], judge_runtime)
    destination = run_path / "synthetic_scores.json"
    previous = {}
    if retry_errors and destination.exists():
        previous = {(row["model"], row["thread_id"], row.get("session_id")): row for row in json.loads(destination.read_text())}
    scores = []
    for row in sorted(results, key=lambda item: (item["model"], item["thread_id"], item["session_id"])):
        model = row["model"]
        thread_id = row["thread_id"]
        session_id = row["session_id"]
        expected = expected_by_checkpoint.get((thread_id, session_id))
        if expected is None:
            raise ValueError(f"Missing synthetic ground truth for {thread_id}/{session_id}")
        prior = previous.get((model, thread_id, session_id))
        if not row["call"].get("json_valid"):
            scores.append({"model": model, "thread_id": thread_id, "session_id": session_id, "writer_json_valid": False, "judge_model": judge.model, "score": {"error": "Writer JSON invalid; store unchanged"}, "call": None})
            continue
        if prior and "error" not in prior["score"]:
            prior["writer_json_valid"] = True
            scores.append(prior)
            continue
        messages = [{"role": "system", "content": JUDGE_PROMPT}, {"role": "user", "content": json.dumps({"expected_facts": expected, "actual_memory": [e["content"] for e in row["memory_after"]]})}]
        try:
            call: CallResult = judge._stream(messages, json_mode=True, response_format=JUDGE_RESPONSE_FORMAT)
            score = json.loads(call.raw_content)
            required = {"expected_facts", "recalled_facts", "hallucinated_entries", "duplicate_entries", "stale_entries", "errors"}
            if not required.issubset(score):
                raise ValueError("judge schema mismatch")
            metric_names = required - {"errors"}
            if any(type(score[name]) is not int or score[name] < 0 for name in metric_names):
                raise ValueError("judge metrics must be non-negative integers")
            if score["recalled_facts"] > len(expected):
                raise ValueError("judge recalled more facts than exist at this checkpoint")
            if not isinstance(score["errors"], list) or not all(isinstance(error, str) for error in score["errors"]):
                raise ValueError("judge errors must be an array of strings")
            # Ground truth, not the judge's self-reported count, is authoritative
            # for the recall denominator.
            score["expected_facts"] = len(expected)
            call.json_valid = True
        except Exception as exc:
            score = {"error": f"{type(exc).__name__}: {exc}"}
            call = CallResult("", "", None, 0, None, None, 0, False, score["error"])
        scores.append({"model": model, "thread_id": thread_id, "session_id": session_id, "writer_json_valid": True, "judge_model": judge.model, "score": score, "call": call.as_dict()})
        destination.write_text(json.dumps(scores + [other for other in previous.values() if (other["model"], other["thread_id"], other.get("session_id")) not in {(done["model"], done["thread_id"], done.get("session_id")) for done in scores}], indent=2) + "\n")
    destination.write_text(json.dumps(scores, indent=2) + "\n")
    write_score_summary(run_path, scores)
    return destination


def write_score_summary(run_path: Path, scores: list[dict[str, Any]]) -> None:
    checkpoint_scoring = bool(scores) and all("session_id" in row for row in scores)
    unit = "checkpoints" if checkpoint_scoring else "final-thread stores"
    totals: dict[str, dict[str, int]] = {}
    for row in scores:
        score = row["score"]
        total = totals.setdefault(row["model"], {"expected_facts": 0, "recalled_facts": 0, "hallucinated_entries": 0, "duplicate_entries": 0, "stale_entries": 0, "checkpoints_scored": 0, "checkpoints_total": 0, "writer_valid": 0})
        total["checkpoints_total"] += 1
        if row.get("writer_json_valid", True):
            total["writer_valid"] += 1
        if "error" in score:
            continue
        total["checkpoints_scored"] += 1
        for key in ("expected_facts", "recalled_facts", "hallucinated_entries", "duplicate_entries", "stale_entries"):
            total[key] += int(score.get(key, 0))
    scope = "Each valid model output is judged at every session checkpoint against the memory expected at that point in the thread." if checkpoint_scoring else "This is a legacy final-thread score artifact; rerun `score-synthetic` to score every session checkpoint."
    lines = ["", "## Synthetic automatic scoring", "", f"{scope} GLM is judging outputs generated by GLM, so treat this as a useful but non-independent signal. Recall uses the ground-truth fact count, not the judge's reported denominator. Writer validity and judge coverage are reported separately; an invalid writer response is not a judge failure.", "", f"| Model | Writer valid | Judge coverage | Recall on scored {unit} | Hallucinations | Duplicates | Stale |", "|---|---:|---:|---:|---:|---:|---:|"]
    for model, total in sorted(totals.items()):
        recall = total["recalled_facts"] / total["expected_facts"] if total["expected_facts"] else 0
        lines.append(f"| {model} | {total['writer_valid']}/{total['checkpoints_total']} | {total['checkpoints_scored']}/{total['writer_valid']} | {recall:.1%} ({total['recalled_facts']}/{total['expected_facts']}) | {total['hallucinated_entries']} | {total['duplicate_entries']} | {total['stale_entries']} |")
    lines.append("\nSee `synthetic_scores.json` for checkpoint-level verdicts.\n")
    report_path = run_path / "report.md"
    original = report_path.read_text()
    marker = "\n## Synthetic automatic scoring"
    report_path.write_text(original.split(marker, 1)[0].rstrip() + "\n" + "\n".join(lines))


def refresh_score_summary(run_dir: str | Path, synthetic_dir: str | Path = "data/synthetic") -> None:
    """Normalize an already-created judge artifact without making API calls."""
    run_path = Path(run_dir)
    scores_path = run_path / "synthetic_scores.json"
    scores = json.loads(scores_path.read_text())
    truth = {path.stem.removesuffix("__ground_truth"): json.loads(path.read_text()) for path in Path(synthetic_dir).glob("*__ground_truth.json")}
    expected_by_checkpoint = {
        (thread_id, checkpoint["session_id"]): checkpoint["ideal_memory"]
        for thread_id, thread_truth in truth.items()
        for checkpoint in thread_truth["after_each_session"]
    }
    for row in scores:
        if "error" not in row["score"]:
            # Older score artifacts did not include a session id and can only
            # be normalized as final-checkpoint scores.
            session_id = row.get("session_id")
            if session_id:
                row["score"]["expected_facts"] = len(expected_by_checkpoint[(row["thread_id"], session_id)])
            else:
                row["score"]["expected_facts"] = len(truth[row["thread_id"]]["after_each_session"][-1]["ideal_memory"])
    scores_path.write_text(json.dumps(scores, indent=2) + "\n")
    write_score_summary(run_path, scores)
