import csv
import json
import tempfile
import unittest
from pathlib import Path

from memory_eval.failure_types import TYPES, _classify, report_failure_types
from memory_eval.types import CallResult


class FakeJudge:
    model = "independent-judge"

    def _stream(self, messages, json_mode, response_format):
        self.messages = messages
        return CallResult(json.dumps({"failure_type": "non_user_source", "evidence_quote": "Tool: ticket 7", "reason": "Only the tool supplied the number."}), "", None, 0, None, None, 0, True)


class FailureTypesTests(unittest.TestCase):
    def test_classifier_uses_closed_taxonomy_and_no_model_identity(self):
        row = {"row_id": "1", "entry": "ticket 7", "checkpoint_session": "s1", "transcript_history": "Tool: ticket 7"}
        judge = FakeJudge()
        result = _classify(row, judge)
        self.assertEqual(result["failure_type"], "non_user_source")
        self.assertIn(result["failure_type"], TYPES)
        self.assertEqual(result["evidence_quote"], "Tool: ticket 7")
        self.assertNotIn("model", judge.messages[1]["content"])

    def test_report_counts_one_primary_type_per_row(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            with (root / "key.csv").open("w", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=["row_id", "model"])
                writer.writeheader()
                writer.writerows([{"row_id": "1", "model": "writer"}, {"row_id": "2", "model": "writer"}])
            with (root / "types.csv").open("w", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=["row_id", "failure_type", "error"])
                writer.writeheader()
                writer.writerows([{"row_id": "1", "failure_type": "non_user_source", "error": ""}, {"row_id": "2", "failure_type": "stale_replacement", "error": ""}])
            report = report_failure_types(root / "key.csv", root / "types.csv", root / "report.md")
            self.assertIn("**All models** | 1 | 1", report.read_text())


if __name__ == "__main__":
    unittest.main()
