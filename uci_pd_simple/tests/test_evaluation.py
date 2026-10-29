import json
from pathlib import Path
import tempfile
import unittest

from deep_learning.evaluation import build_evaluation

ROOT = Path(__file__).resolve().parents[1]


class TestEvaluation(unittest.TestCase):
    def test_real_oof_counts_and_roc_auc(self):
        data = build_evaluation(ROOT / "artifacts/audio_transformer_v1")
        self.assertEqual(data["metrics"]["subjects"], 37)
        self.assertEqual([data["metrics"][k] for k in ("tn", "fp", "fn", "tp")], [17, 4, 6, 10])
        self.assertAlmostEqual(data["metrics"]["auc"], 0.7589285714285714)
        self.assertEqual(data["roc"][0], {"fpr": 0, "tpr": 0})
        self.assertEqual(data["roc"][-1], {"fpr": 1, "tpr": 1})
        self.assertNotIn("subject", json.dumps(data["roc"]))

    def test_tied_scores_and_no_fabricated_or_inconsistent_data(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            rows = [{"subject": str(i), "label": label, "score": .5} for i, label in enumerate([0, 0, 1])]
            metrics = dict(subjects=3, auc=.5, accuracy=1/3, sensitivity=1, specificity=0,
                           balanced_accuracy=.5, tp=1, fp=2, tn=0, fn=0)
            card = {"threshold": .5, "dataset": ["parser-fixture"], "evaluation": {"metrics": metrics}}
            (root / "model_card.json").write_text(json.dumps(card), encoding="utf-8")
            path = root / "oof_predictions.json"
            path.write_text(json.dumps(rows), encoding="utf-8")
            self.assertEqual(build_evaluation(root)["metrics"]["auc"], .5)
            rows.append(rows[0])
            path.write_text(json.dumps(rows), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "one prediction"):
                build_evaluation(root)
            path.write_text(json.dumps(rows[:2]), encoding="utf-8")
            with self.assertRaises(ValueError):
                build_evaluation(root)
