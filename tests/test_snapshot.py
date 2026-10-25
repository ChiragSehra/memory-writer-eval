import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from memory_eval.snapshot import create_snapshot, verify_snapshot


class SnapshotTests(unittest.TestCase):
    def test_freeze_and_detect_changed_artifact(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            run = root / "run"
            run.mkdir()
            (run / "results.json").write_text(json.dumps([{"model": "local", "call": {"json_valid": True}}]))
            (run / "report.md").write_text("Report\n")
            (run / "synthetic_scores.json").write_text("[]\n")
            config = {"local": {"model": "test-model"}, "openrouter": {"models": []}, "runtime": {}, "judge": {"name": "test-judge"}}
            with patch("memory_eval.snapshot.load_threads", return_value={"thread": [{}]}):
                manifest = create_snapshot(run, root / "snapshot", config, {})
            self.assertEqual(verify_snapshot(manifest.parent)["writer_valid"], 1)
            self.assertEqual(verify_snapshot(manifest.parent, check_workspace=True)["writer_valid"], 1)
            self.assertTrue((manifest.parent / "source" / "config.yaml").is_file())
            (manifest.parent / "report.md").write_text("changed\n")
            with self.assertRaisesRegex(ValueError, "artifact changed"):
                verify_snapshot(manifest.parent)
            (manifest.parent / "report.md").write_text("Report\n")
            (manifest.parent / "source" / "config.yaml").write_text("changed\n")
            with self.assertRaisesRegex(ValueError, "bundled source changed"):
                verify_snapshot(manifest.parent)


if __name__ == "__main__":
    unittest.main()
