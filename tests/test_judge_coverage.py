import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from memory_eval.judge import score_synthetic
from memory_eval.types import CallResult


class FakeJudge:
    calls = 0

    def __init__(self, name, settings, runtime):
        self.model = settings["model"]

    def _stream(self, messages, json_mode, response_format):
        self.__class__.calls += 1
        return CallResult(json.dumps({"expected_facts": 1, "recalled_facts": 1, "hallucinated_entries": 0, "duplicate_entries": 0, "stale_entries": 0, "errors": []}), "", None, 0, None, None, 0, True)


class JudgeCoverageTests(unittest.TestCase):
    def test_retry_preserves_success_and_counts_invalid_writer_separately(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            run = root / "run"
            run.mkdir()
            corpus = root / "corpus"
            corpus.mkdir()
            (corpus / "thread__ground_truth.json").write_text(json.dumps({"after_each_session": [
                {"session_id": session, "ideal_memory": ["fact"]} for session in ("s1", "s2", "s3")
            ]}))
            (run / "results.json").write_text(json.dumps([
                {"model": "local", "thread_id": "thread", "session_id": session, "call": {"json_valid": valid}, "memory_after": [{"content": "fact"}]}
                for session, valid in (("s1", True), ("s2", True), ("s3", False))
            ]))
            old_score = {"expected_facts": 1, "recalled_facts": 1, "hallucinated_entries": 0, "duplicate_entries": 0, "stale_entries": 0, "errors": []}
            (run / "synthetic_scores.json").write_text(json.dumps([
                {"model": "local", "thread_id": "thread", "session_id": "s1", "score": old_score, "call": {}},
                {"model": "local", "thread_id": "thread", "session_id": "s2", "score": {"error": "old failure"}, "call": {}},
            ]))
            (run / "report.md").write_text("# Existing report\n")
            config = {"local": {}, "openrouter": {"base_url": "unused", "models": [{"name": "glm", "model": "glm"}]}, "runtime": {}, "judge": {"name": "glm", "reasoning_effort": "low"}}
            FakeJudge.calls = 0
            with patch("memory_eval.judge.MemoryWriter", FakeJudge):
                score_synthetic(run, config, corpus, retry_errors=True)
            scores = json.loads((run / "synthetic_scores.json").read_text())
            self.assertEqual(FakeJudge.calls, 1)
            self.assertEqual(len(scores), 3)
            self.assertEqual(sum(row["writer_json_valid"] is False for row in scores), 1)
            self.assertEqual(sum("error" not in row["score"] for row in scores), 2)
            self.assertIn("2/2", (run / "report.md").read_text())


if __name__ == "__main__":
    unittest.main()
