import csv
import json
import tempfile
import unittest
from pathlib import Path

from memory_eval.io import load_threads
from memory_eval.real_tracing import _digest, _trace, export_trace_sheet, report_traces
from memory_eval.types import CallResult


class FakeJudge:
    model = "trace-judge"

    def __init__(self, message_id, quote):
        self.message_id = message_id
        self.quote = quote

    def _stream(self, messages, json_mode, response_format):
        self.messages = messages
        return CallResult(json.dumps({"support": "supported", "evidence": [{"message_id": self.message_id, "quote": self.quote}], "reason": "User stated it."}), "", None, 0, None, None, 0, True)


class RealTracingTests(unittest.TestCase):
    def test_structured_messages_keep_stable_ids_and_quote_validation(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            (root / "thread__s1.json").write_text(json.dumps({"thread_id": "thread", "session_id": "s1", "sequence": 1, "messages": [
                {"message_id": "u-1", "role": "user", "content": "Remember Friday delivery."},
                {"message_id": "t-1", "role": "tool", "content": "Ticket ABC-1."},
            ]}))
            session = load_threads(root)["thread"][0]
            self.assertIn("[u-1] user: Remember Friday delivery.", session["transcript"])
            row = {"row_id": "1", "entry": "Friday delivery", "checkpoint_session": "s1", "messages_json": json.dumps(session["messages"])}
            good = _trace(row, FakeJudge("u-1", "Friday delivery"))
            self.assertEqual(good["support"], "supported")
            self.assertEqual(good["error"], "")
            bad = _trace(row, FakeJudge("t-1", "Ticket ABC-1"))
            self.assertIn("not an exact substring of its user message", bad["error"])

    def test_export_keeps_identity_out_of_trace_sheet(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            source = root / "sessions"
            source.mkdir()
            (source / "thread__s1.json").write_text(json.dumps({"thread_id": "thread", "session_id": "s1", "sequence": 1, "messages": [{"message_id": "m1", "role": "user", "content": "Use Friday."}]}))
            with (root / "writes.csv").open("w", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=["row_id", "entry", "checkpoint_session"])
                writer.writeheader()
                writer.writerow({"row_id": "1", "entry": "Use Friday", "checkpoint_session": "s1"})
            with (root / "key.csv").open("w", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=["row_id", "model", "thread_id", "checkpoint_session"])
                writer.writeheader()
                writer.writerow({"row_id": "1", "model": "secret-model", "thread_id": "thread", "checkpoint_session": "s1"})
            sheet = export_trace_sheet(root / "writes.csv", root / "key.csv", source, root / "traces.csv")
            with sheet.open(newline="") as file:
                row = next(csv.DictReader(file))
            self.assertNotIn("model", row)
            self.assertEqual(json.loads(row["messages_json"])[0]["message_id"], "m1")

    def test_report_rejects_stale_scores_and_non_user_quotes(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            sheet = root / "traces.csv"
            key = root / "key.csv"
            scores = root / "scores.csv"
            row = {"row_id": "1", "entry": "Use Friday", "checkpoint_session": "s1", "messages_json": json.dumps([
                {"message_id": "u1", "role": "user", "content": "Use Friday."},
                {"message_id": "a1", "role": "assistant", "content": "Use Saturday."},
            ])}
            with sheet.open("w", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=row)
                writer.writeheader()
                writer.writerow(row)
            with key.open("w", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=["row_id", "model"])
                writer.writeheader()
                writer.writerow({"row_id": "1", "model": "writer"})
            score = {"row_id": "1", "input_sha256": _digest(row), "judge_model": "judge", "support": "supported", "evidence_json": json.dumps([{"message_id": "u1", "quote": "Use Friday."}]), "reason": "User said it.", "error": ""}

            def save_score():
                with scores.open("w", newline="") as file:
                    writer = csv.DictWriter(file, fieldnames=score)
                    writer.writeheader()
                    writer.writerow(score)

            save_score()
            report = report_traces(sheet, key, scores, root / "report.md")
            self.assertIn("1/1", report.read_text())
            score["input_sha256"] = "stale"
            save_score()
            with self.assertRaisesRegex(ValueError, "does not match sheet content"):
                report_traces(sheet, key, scores, root / "report.md")
            score["input_sha256"] = _digest(row)
            score["evidence_json"] = json.dumps([{"message_id": "a1", "quote": "Use Saturday."}])
            save_score()
            with self.assertRaisesRegex(ValueError, "Invalid user-message quote"):
                report_traces(sheet, key, scores, root / "report.md")


if __name__ == "__main__":
    unittest.main()
