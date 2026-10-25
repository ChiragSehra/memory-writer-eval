import csv
import json
import tempfile
import unittest
from pathlib import Path

from memory_eval.checkpoint_review import _indices, export_checkpoint_sheet


class CheckpointReviewTests(unittest.TestCase):
    def test_export_includes_each_checkpoint_and_empty_store(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            source = root / "sessions"
            source.mkdir()
            for index in (1, 2):
                (source / f"thread__s{index}.json").write_text(json.dumps({"thread_id": "thread", "session_id": f"s{index}", "sequence": index, "transcript": f"User: session {index}"}))
            (source / "thread__ground_truth.json").write_text(json.dumps({"after_each_session": [
                {"session_id": "s1", "ideal_memory": ["fact 1"]},
                {"session_id": "s2", "ideal_memory": ["fact 1", "fact 2"]},
            ]}))
            run = root / "run"
            run.mkdir()
            (run / "results.json").write_text(json.dumps([
                {"model": "writer", "thread_id": "thread", "session_id": "s1", "memory_after": [], "call": {"json_valid": False}},
                {"model": "writer", "thread_id": "thread", "session_id": "s2", "memory_after": [{"content": "fact 1"}], "call": {"json_valid": True}},
            ]))
            sheet, key = export_checkpoint_sheet(run, source, root / "checkpoints.csv")
            with sheet.open(newline="") as file:
                rows = list(csv.DictReader(file))
            with key.open(newline="") as file:
                identities = list(csv.DictReader(file))
            self.assertEqual(len(rows), 2)
            self.assertEqual({row["actual_memory"] for row in rows}, {"[]", '["fact 1"]'})
            self.assertEqual({row["writer_json_valid"] for row in identities}, {"True", "False"})
            self.assertTrue(all("model" not in row for row in rows))

    def test_rejects_invalid_judge_indices(self):
        for invalid in ([2], [-1], [0, 0], [True], "0"):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                _indices(invalid, 2, "matched")
        self.assertEqual(_indices([1, 0], 2, "matched"), [0, 1])


if __name__ == "__main__":
    unittest.main()
