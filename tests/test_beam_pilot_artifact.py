import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BeamPilotArtifactTests(unittest.TestCase):
    def test_saved_exploratory_score_arithmetic(self):
        answers = json.loads((ROOT / "scoring/beam_answers.json").read_text())
        scores = json.loads((ROOT / "scoring/beam_pilot_scores.json").read_text())
        self.assertEqual(set(answers), set(scores))
        self.assertEqual(len(scores), 10)
        values = []
        nuggets = 0
        for category, records in scores.items():
            self.assertEqual(len(records), 2)
            self.assertEqual(len(records), len(answers[category]))
            for answer, record in zip(answers[category], records):
                self.assertEqual(answer["question"], record["question"])
                self.assertTrue(answer["llm_response"])
                self.assertFalse(record["error"])
                self.assertTrue(record["nugget_scores"])
                self.assertTrue(all(value in {0, 0.5, 1} for value in record["nugget_scores"]))
                self.assertAlmostEqual(record["score"], sum(record["nugget_scores"]) / len(record["nugget_scores"]))
                nuggets += len(record["nugget_scores"])
                values.append(record["score"])
        self.assertEqual((len(values), nuggets), (20, 75))
        self.assertEqual(round(sum(values) / len(values) * 100, 1), 60.8)


if __name__ == "__main__":
    unittest.main()
