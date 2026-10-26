import tempfile
import unittest
from pathlib import Path

from memory_eval.io import load_threads
from memory_eval.synthetic import THREADS, generate


class QuietReplacementTests(unittest.TestCase):
    def test_later_single_cutover_supersedes_prior_plan_without_correction_cue(self):
        thread = dict(THREADS)["atlas-migration"]
        first, second = thread
        self.assertIn("12 November", first[2][1])
        self.assertIn("blue deployment", first[2][1])
        self.assertEqual(sum("production cutover is" in fact for fact in second[2]), 1)
        self.assertIn("19 November", second[2][1])
        self.assertIn("green deployment", second[2][1])
        self.assertNotIn("12 November", " ".join(second[2]))
        self.assertNotIn("blue deployment", " ".join(second[2]))
        self.assertNotIn("update", second[1].lower())
        self.assertNotIn("correction", second[1].lower())
        with tempfile.TemporaryDirectory() as root:
            generate(root)
            sessions = load_threads(root)["atlas-migration"]
            self.assertEqual([session["session_id"] for session in sessions], [first[0], second[0]])


if __name__ == "__main__":
    unittest.main()
