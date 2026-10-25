import csv
import json
import tempfile
import unittest
from pathlib import Path

from memory_eval.write_metrics import export_write_sheet, report_write_support
from memory_eval.blind_judge import _digest


class WriteMetricsTests(unittest.TestCase):
    def test_counts_applied_writes_even_if_later_deleted(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            source = root / "sessions"
            source.mkdir()
            (source / "thread__s1.json").write_text(json.dumps({"thread_id": "thread", "session_id": "s1", "sequence": 1, "transcript": "User: use Friday"}))
            run = root / "run"
            run.mkdir()
            (run / "results.json").write_text(json.dumps([{
                "model": "writer", "thread_id": "thread", "session_id": "s1", "memory_before": [],
                "operations": [
                    {"op": "add", "id": None, "content": "Friday", "reason": ""},
                    {"op": "update", "id": "mem_1", "content": "Saturday", "reason": ""},
                    {"op": "update", "id": "mem_1", "content": "   ", "reason": ""},
                    {"op": "add", "id": None, "content": "   ", "reason": ""},
                    {"op": "delete", "id": "mem_1", "content": None, "reason": ""},
                    {"op": "update", "id": "mem_1", "content": "Sunday", "reason": ""},
                    {"op": "add", "id": None, "content": "", "reason": ""},
                ],
                "memory_after": [],
            }]))
            sheet, key = export_write_sheet(run, source, root / "writes.csv")
            with sheet.open(newline="") as file:
                rows = list(csv.DictReader(file))
            self.assertEqual({row["entry"] for row in rows}, {"Friday", "Saturday"})
            self.assertEqual(len(rows), 2)
            with (root / "scores.csv").open("w", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=["row_id", "input_sha256", "support", "should_be_stored", "error"])
                writer.writeheader()
                for row in rows:
                    writer.writerow({"row_id": row["row_id"], "input_sha256": _digest(row), "support": "unsupported" if row["entry"] == "Saturday" else "supported", "should_be_stored": "no", "error": ""})
            report = report_write_support(sheet, key, root / "scores.csv", root / "report.md")
            self.assertIn("1/2 (50.0%)", report.read_text())
            self.assertIn("Supported but not worth storing", report.read_text())

    def test_replay_mismatch_fails_before_export(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            source = root / "sessions"
            source.mkdir()
            (source / "thread__s1.json").write_text(json.dumps({"thread_id": "thread", "session_id": "s1", "sequence": 1, "transcript": "User: test"}))
            run = root / "run"
            run.mkdir()
            (run / "results.json").write_text(json.dumps([{"model": "writer", "thread_id": "thread", "session_id": "s1", "memory_before": [], "operations": [], "memory_after": [{"id": "mem_1", "content": "impossible", "source_session": "s1"}]}]))
            with self.assertRaisesRegex(ValueError, "replay disagrees"):
                export_write_sheet(run, source, root / "writes.csv")


if __name__ == "__main__":
    unittest.main()
