import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from memory_eval.runner import run_models
from memory_eval.types import CallResult, Operation


class FakeWriter:
    calls = []

    def __init__(self, name, settings, runtime):
        pass

    def write(self, prompt, memory, transcript):
        self.__class__.calls.append((json.loads(memory), transcript))
        ops = [Operation(op="add", content="new fact")] if transcript == "first" else []
        return ops, CallResult("{}", "", None, 0.1, 1, 1, 0, True)


class RunnerResumeTests(unittest.TestCase):
    def test_retry_recomputes_later_cached_checkpoints(self):
        with tempfile.TemporaryDirectory() as root:
            run = Path(root) / "run"
            raw = run / "raw" / "local"
            raw.mkdir(parents=True)
            for session, valid in (("s1", False), ("s2", True)):
                (raw / f"thread__{session}.json").write_text(json.dumps({
                    "model": "local", "thread_id": "thread", "session_id": session,
                    "memory_after": [], "call": {"error": "bad JSON" if not valid else None},
                }))
            config = {"local": {}, "openrouter": {"models": []}, "runtime": {}}
            sessions = {"thread": [
                {"session_id": "s1", "transcript": "first"},
                {"session_id": "s2", "transcript": "second"},
            ]}
            FakeWriter.calls = []
            with patch("memory_eval.runner.MemoryWriter", FakeWriter), \
                 patch("memory_eval.runner.load_threads", return_value=sessions), \
                 patch("memory_eval.runner.prompt_text", return_value="prompt"), \
                 patch("memory_eval.runner.write_report"):
                run_models(config, "unused", resume_dir=str(run), retry_errors=True)
            self.assertEqual(len(FakeWriter.calls), 2)
            self.assertEqual(FakeWriter.calls[1][0][0]["content"], "new fact")
            rows = json.loads((run / "results.json").read_text())
            self.assertEqual(rows[1]["memory_before"][0]["content"], "new fact")


if __name__ == "__main__":
    unittest.main()
