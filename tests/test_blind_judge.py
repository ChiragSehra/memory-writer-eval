import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from memory_eval.blind_judge import _score, score_blind_sheet
from memory_eval.runner import export_blind_sheet
from memory_eval.types import CallResult


class FakeJudge:
    model = "different-judge"

    def __init__(self, quote: str):
        self.quote = quote
        self.messages = None

    def _stream(self, messages, json_mode, response_format):
        self.messages = messages
        return CallResult(
            raw_content=json.dumps({
                "correctness_score": 5,
                "support": "supported",
                "should_be_stored": "yes",
                "evidence_quote": self.quote,
                "reason": "The user stated the rule.",
            }),
            reasoning_content="",
            latency_ttft_s=None,
            latency_total_s=0,
            input_tokens=None,
            output_tokens=None,
            retries=0,
            json_valid=True,
        )


class BlindJudgeTests(unittest.TestCase):
    def test_score_never_sends_model_identity_and_flags_nonverbatim_quote(self):
        row = {"row_id": "1", "entry": "The report is due Friday.", "checkpoint_session": "s1", "transcript_history": "User: The report is due Friday."}
        judge = FakeJudge("The report is due on Friday")
        score = _score(row, judge)
        self.assertEqual(score["correctness_score"], "5")
        self.assertEqual(score["evidence_quote"], "")
        self.assertIn("not verbatim", score["reason"])
        self.assertEqual(score["error"], "")
        self.assertNotIn("model", judge.messages[1]["content"])

    def test_export_includes_complete_history_for_final_store(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            source = root / "sessions"
            source.mkdir()
            for index in (1, 2):
                (source / f"thread__s{index}.json").write_text(json.dumps({
                    "thread_id": "thread", "session_id": f"s{index}", "sequence": index,
                    "transcript": f"User: session {index}",
                }))
            run = root / "run"
            run.mkdir()
            (run / "results.json").write_text(json.dumps([
                {"model": "writer", "thread_id": "thread", "session_id": "s1", "memory_after": []},
                {"model": "writer", "thread_id": "thread", "session_id": "s2", "memory_after": [{"content": "fact", "source_session": "s1"}]},
            ]))
            sheet, key = export_blind_sheet(run, root / "sheet.csv", source)
            with sheet.open(newline="") as file:
                rows = list(csv.DictReader(file))
            self.assertEqual(len(rows), 1)
            self.assertIn("session 1", rows[0]["transcript_history"])
            self.assertIn("session 2", rows[0]["transcript_history"])
            self.assertNotIn("model", rows[0])
            self.assertTrue(key.exists())

    def test_second_judge_must_differ_from_first(self):
        with self.assertRaisesRegex(ValueError, "must differ"):
            score_blind_sheet("unused", "unused", {"judge": {"name": "glm"}}, "glm")


if __name__ == "__main__":
    unittest.main()
