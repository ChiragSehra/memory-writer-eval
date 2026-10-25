import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from memory_eval.beam import answer_beam_probes, import_beam_chat, score_beam_pilot
from memory_eval.io import load_threads
from memory_eval.types import CallResult


class FakeReader:
    last_messages = None

    def __init__(self, name, settings, runtime):
        pass

    def _stream(self, messages, json_mode):
        FakeReader.last_messages = messages
        return CallResult("Friday", "", None, 0, 12, 1, 0, True)


class FakeRubricJudge:
    calls = 0

    def __init__(self, name, settings, runtime):
        self.model = settings["model"]

    def _stream(self, messages, json_mode, response_format):
        FakeRubricJudge.calls += 1
        return CallResult(json.dumps({"nugget_scores": [1, 0.5], "reason": "One complete, one partial."}), "", None, 0, 12, 1, 0, True)


class BeamTests(unittest.TestCase):
    def test_import_preserves_batch_order_and_reader_uses_final_memory_only(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            chat = root / "chat.json"
            chat.write_text(json.dumps([
                {"batch_number": 1, "turns": [[{"role": "user", "content": "Friday"}, {"role": "assistant", "content": "Okay"}]]},
                {"batch_number": 2, "turns": [[{"role": "user", "content": "Saturday"}, {"role": "assistant", "content": "Okay"}]]},
            ]))
            source = root / "sessions"
            manifest = import_beam_chat(chat, source, "chat-1")
            self.assertEqual(json.loads(manifest.read_text())["message_count"], 4)
            sessions = load_threads(source)["chat-1"]
            self.assertEqual([session["session_id"] for session in sessions], ["batch-01", "batch-02"])
            run = root / "run"
            run.mkdir()
            (run / "results.json").write_text(json.dumps([
                {"model": "writer", "thread_id": "chat-1", "session_id": "batch-01", "memory_after": [{"content": "old"}]},
                {"model": "writer", "thread_id": "chat-1", "session_id": "batch-02", "memory_after": [{"content": "new"}]},
            ]))
            questions = root / "questions.json"
            questions.write_text(json.dumps({"knowledge_update": [{"question": "Which day?"}]}))
            config = {"local": {"model": "reader"}, "runtime": {}, "openrouter": {}}
            with patch("memory_eval.beam.MemoryWriter", FakeReader):
                output = answer_beam_probes(run, questions, config, "writer", "local", root / "answers.json", 2)
            self.assertEqual(json.loads(output.read_text())["knowledge_update"][0]["llm_response"], "Friday")
            self.assertEqual(json.loads(output.with_name("answers_metadata.json").read_text())["final_memory_entries"], 1)
            self.assertIn('"new"', FakeReader.last_messages[1]["content"])
            self.assertNotIn('"old"', FakeReader.last_messages[1]["content"])

            rows = json.loads((run / "results.json").read_text())
            (run / "results.json").write_text(json.dumps(list(reversed(rows))))
            with patch("memory_eval.beam.MemoryWriter", FakeReader):
                answer_beam_probes(run, questions, config, "writer", "local", root / "reordered_answers.json", 2)
            self.assertIn('"new"', FakeReader.last_messages[1]["content"])

            rows[1]["session_id"] = "batch-01"
            (run / "results.json").write_text(json.dumps(rows))
            with self.assertRaisesRegex(ValueError, "duplicate or missing batches"):
                answer_beam_probes(run, questions, config, "writer", "local", root / "bad_answers.json", 2)

    def test_exploratory_rubric_score_has_explicit_scope(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            questions = root / "questions.json"
            answers = root / "answers.json"
            questions.write_text(json.dumps({"information_extraction": [{"question": "Which day?", "rubric": ["Friday", "Morning"], "ideal_answer": "Friday morning"}]}))
            answers.write_text(json.dumps({"information_extraction": [{"question": "Which day?", "llm_response": "Friday"}]}))
            config = {"local": {}, "openrouter": {"models": [{"name": "judge", "model": "judge"}]}, "runtime": {}, "judge": {"max_output_tokens": 700}}
            FakeRubricJudge.calls = 0
            with patch("memory_eval.beam.MemoryWriter", FakeRubricJudge):
                output = score_beam_pilot(answers, questions, config, "judge", root / "scores.json")
            self.assertEqual(json.loads(output.read_text())["information_extraction"][0]["score"], 0.75)
            self.assertEqual(FakeRubricJudge.calls, 1)
            with patch("memory_eval.beam.MemoryWriter", FakeRubricJudge):
                score_beam_pilot(answers, questions, config, "judge", root / "scores.json")
            self.assertEqual(FakeRubricJudge.calls, 1)
            answers.write_text(json.dumps({"information_extraction": [{"question": "Which day?", "llm_response": "Saturday"}]}))
            with patch("memory_eval.beam.MemoryWriter", FakeRubricJudge):
                score_beam_pilot(answers, questions, config, "judge", root / "scores.json")
            self.assertEqual(FakeRubricJudge.calls, 2)
            self.assertIn("not a leaderboard-comparable", output.with_suffix(".md").read_text())


if __name__ == "__main__":
    unittest.main()
