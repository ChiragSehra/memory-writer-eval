import csv
import json
import unittest
from collections import Counter
from pathlib import Path

from memory_eval.blind_judge import _digest as entry_digest
from memory_eval.checkpoint_review import _digest as checkpoint_digest
from memory_eval.io import load_threads
from memory_eval.memory import apply_operations
from memory_eval.snapshot import verify_snapshot
from memory_eval.types import MemoryEntry, Operation


SNAPSHOT = Path(__file__).resolve().parents[1] / "snapshots/2026-10-25-verified"


def read_rows(name):
    with (SNAPSHOT / name).open(newline="") as file:
        rows = list(csv.DictReader(file))
    ids = [row["row_id"] for row in rows]
    if len(ids) != len(set(ids)) or any(not row_id for row_id in ids):
        raise ValueError(f"Missing or duplicate row ID in {name}")
    return {row["row_id"]: row for row in rows}


class FrozenSnapshotEvidenceTests(unittest.TestCase):
    def test_reported_coverage_and_row_level_joins(self):
        manifest = verify_snapshot(SNAPSHOT)
        threads = load_threads(SNAPSHOT / "source/data/synthetic")
        labels = {model["label"] for model in manifest["models"]}
        expected_keys = {(model, thread_id, session["session_id"]) for model in labels for thread_id, sessions in threads.items() for session in sessions}
        self.assertEqual((len(labels), len(threads), sum(map(len, threads.values()))), (9, 4, 14))

        results = json.loads((SNAPSHOT / "results.json").read_text())
        result_by_key = {(row["model"], row["thread_id"], row["session_id"]): row for row in results}
        self.assertEqual(len(results), len(result_by_key))
        self.assertEqual(set(result_by_key), expected_keys)
        self.assertEqual(sum(bool(row["call"]["json_valid"]) for row in results), 124)

        histories = {}
        writes = {}
        final_entries = Counter()
        final_entries_with_history = Counter()
        expected_facts = {
            (path.stem.removesuffix("__ground_truth"), checkpoint["session_id"]): checkpoint["ideal_memory"]
            for path in (SNAPSHOT / "source/data/synthetic").glob("*__ground_truth.json")
            for checkpoint in json.loads(path.read_text())["after_each_session"]
        }
        for model in labels:
            for thread_id, sessions in threads.items():
                previous = []
                history = []
                for session in sessions:
                    session_id = session["session_id"]
                    history.append(session["transcript"])
                    histories[(thread_id, session_id)] = "\n\n".join(history)
                    row = result_by_key[(model, thread_id, session_id)]
                    self.assertEqual(row["memory_before"], previous)
                    store = [MemoryEntry(**entry) for entry in previous]
                    for index, raw in enumerate(row["operations"]):
                        op = Operation(**raw)
                        applied = bool(op.content and op.content.strip()) and (op.op == "add" or (op.op == "update" and op.id in {entry.id for entry in store}))
                        store = apply_operations(store, [op], session_id)
                        if applied:
                            entry = store[-1] if op.op == "add" else next(entry for entry in store if entry.id == op.id)
                            writes[(model, thread_id, session_id, index)] = (entry.content, op.op)
                    previous = [entry.__dict__ for entry in store]
                    self.assertEqual(row["memory_after"], previous)
                final_entries.update((model, entry["content"]) for entry in previous)
                final_entries_with_history.update((model, entry["content"], "\n\n".join(history)) for entry in previous)
        self.assertEqual(sum(final_entries.values()), 186)
        self.assertEqual(len(writes), 240)

        primary = json.loads((SNAPSHOT / "synthetic_scores.json").read_text())
        primary_by_key = {(row["model"], row["thread_id"], row["session_id"]): row for row in primary}
        self.assertEqual(len(primary), len(primary_by_key))
        self.assertEqual(set(primary_by_key), expected_keys)
        self.assertEqual(sum(bool(row["writer_json_valid"]) and row["call"] is not None and row["call"]["json_valid"] and isinstance(row["score"], dict) and "error" not in row["score"] for row in primary), 124)
        for key, row in primary_by_key.items():
            self.assertEqual(bool(row["writer_json_valid"]), bool(result_by_key[key]["call"]["json_valid"]))

        blind = read_rows("snapshot_blind_sheet.csv")
        blind_key = read_rows("snapshot_blind_sheet_key.csv")
        blind_scores = read_rows("snapshot_blind_scores.csv")
        self.assertEqual(blind.keys(), blind_key.keys())
        self.assertEqual(blind.keys(), blind_scores.keys())
        self.assertEqual(Counter((blind_key[row_id]["model"], row["entry"]) for row_id, row in blind.items()), final_entries)
        self.assertEqual(Counter((blind_key[row_id]["model"], row["entry"], row["transcript_history"]) for row_id, row in blind.items()), final_entries_with_history)
        for row_id, row in blind.items():
            score = blind_scores[row_id]
            self.assertFalse(score["error"])
            self.assertEqual(score["input_sha256"], entry_digest(row))
            self.assertIn(score["support"], {"supported", "unsupported", "uncertain"})
            self.assertTrue(not score["evidence_quote"] or score["evidence_quote"] in row["transcript_history"])

        write_sheet = read_rows("snapshot_write_sheet.csv")
        write_key = read_rows("snapshot_write_sheet_key.csv")
        write_scores = read_rows("snapshot_write_scores.csv")
        self.assertEqual(write_sheet.keys(), write_key.keys())
        self.assertEqual(write_sheet.keys(), write_scores.keys())
        seen_writes = set()
        for row_id, row in write_sheet.items():
            key = write_key[row_id]
            identity = (key["model"], key["thread_id"], key["checkpoint_session"], int(key["operation_index"]))
            self.assertNotIn(identity, seen_writes)
            seen_writes.add(identity)
            self.assertEqual((row["entry"], row["operation_kind"]), writes[identity])
            self.assertEqual(row["transcript_history"], histories[(key["thread_id"], key["checkpoint_session"])])
            score = write_scores[row_id]
            self.assertFalse(score["error"])
            self.assertEqual(score["input_sha256"], entry_digest(row))
            self.assertTrue(not score["evidence_quote"] or score["evidence_quote"] in row["transcript_history"])
        self.assertEqual(seen_writes, set(writes))
        self.assertEqual(Counter(row["support"] for row in write_scores.values()), Counter({"supported": 226, "unsupported": 13, "uncertain": 1}))
        self.assertEqual(sum(row["support"] == "supported" and row["should_be_stored"] == "no" for row in write_scores.values()), 9)

        checkpoints = read_rows("snapshot_checkpoint_sheet.csv")
        checkpoint_key = read_rows("snapshot_checkpoint_sheet_key.csv")
        checkpoint_scores = read_rows("snapshot_checkpoint_scores.csv")
        self.assertEqual(checkpoints.keys(), checkpoint_key.keys())
        self.assertEqual(checkpoints.keys(), checkpoint_scores.keys())
        self.assertEqual(len(checkpoints), 126)
        for row_id, row in checkpoints.items():
            key = checkpoint_key[row_id]
            result = result_by_key[(key["model"], key["thread_id"], key["checkpoint_session"])]
            self.assertEqual(json.loads(row["actual_memory"]), [entry["content"] for entry in result["memory_after"]])
            self.assertEqual(json.loads(row["expected_facts"]), expected_facts[(key["thread_id"], key["checkpoint_session"])])
            self.assertEqual(key["writer_json_valid"], str(bool(result["call"]["json_valid"])))
            self.assertEqual(row["transcript_history"], histories[(key["thread_id"], key["checkpoint_session"])])
            score = checkpoint_scores[row_id]
            self.assertFalse(score["error"])
            self.assertEqual(score["input_sha256"], checkpoint_digest(row))
            for field, size in (("matched_expected_indices", len(json.loads(row["expected_facts"]))), ("unsupported_actual_indices", len(json.loads(row["actual_memory"]))), ("duplicate_actual_indices", len(json.loads(row["actual_memory"]))), ("stale_actual_indices", len(json.loads(row["actual_memory"])))):
                indices = json.loads(score[field])
                self.assertEqual(len(indices), len(set(indices)))
                self.assertTrue(all(type(index) is int and 0 <= index < size for index in indices))

        failures = read_rows("snapshot_failure_types.csv")
        unsupported_ids = {row_id for row_id, score in write_scores.items() if score["support"] == "unsupported"}
        self.assertEqual(failures.keys(), unsupported_ids)
        self.assertEqual(Counter(row["failure_type"] for row in failures.values()), Counter({"non_user_source": 11, "unsupported_inference": 2}))
        for row_id, row in failures.items():
            self.assertFalse(row["error"])
            self.assertEqual(row["input_sha256"], entry_digest(write_sheet[row_id]))


if __name__ == "__main__":
    unittest.main()
