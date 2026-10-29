# -*- coding: utf-8 -*-
"""Smoke tests: run with `python -m unittest discover -s tests -v`."""
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import core  # noqa: E402


class TestData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.df = core.load_data()

    def test_shape_and_labels(self):
        self.assertEqual(len(self.df), 195)
        self.assertEqual(len(core.FEATURES), 22)
        self.assertEqual(self.df[core.TARGET].nunique(), 2)
        self.assertEqual(self.df[core.SUBJECT].nunique(), 32)

    def test_one_label_per_subject(self):
        labels = self.df.groupby(core.SUBJECT)[core.TARGET].nunique()
        self.assertTrue((labels == 1).all())

    def test_no_missing_features(self):
        self.assertFalse(self.df[core.FEATURES].isna().any().any())

    def test_inconsistent_subject_labels_raise(self):
        df = pd.read_csv(core.DATA_PATH)
        subject = df.loc[0, "name"].split("_")[2]
        idx = df.index[df["name"].str.contains(subject)][0]
        df.loc[idx, "status"] = 1 - df.loc[idx, "status"]
        path = ROOT / "artifacts" / "_test_bad_labels.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            df.to_csv(path, index=False)
            with self.assertRaises(ValueError):
                core.load_data(path)
        finally:
            path.unlink(missing_ok=True)


class TestFoldsAndModel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.df = core.load_data()

    def test_folds_are_disjoint_and_complete(self):
        folds = core.make_subject_folds(self.df, n_splits=5, seed=42)
        all_subjects = set(self.df[core.SUBJECT])
        seen = set()
        for fold in folds:
            self.assertGreater(len(fold), 0)
            self.assertTrue(seen.isdisjoint(fold))
            seen.update(fold)
        self.assertEqual(seen, all_subjects)

    def test_too_many_folds_raises(self):
        with self.assertRaises(ValueError):
            core.make_subject_folds(self.df, n_splits=9, seed=42)

    def test_cv_is_deterministic(self):
        a, _ = core.cross_validate(self.df, repeats=3)
        b, _ = core.cross_validate(self.df, repeats=3)
        self.assertTrue(np.allclose(a["auc"].to_numpy(), b["auc"].to_numpy()))

    def test_model_probabilities(self):
        mask = np.ones(len(self.df), dtype=bool)
        scaler, model = core.fit_on_subset(self.df, mask, l2=1.0)
        X = scaler.transform(self.df[core.FEATURES].to_numpy())
        p = model.predict_proba(X)
        self.assertEqual(p.shape, (len(self.df),))
        self.assertTrue(((p >= 0) & (p <= 1)).all())
        self.assertEqual(model.coef_.shape, (len(core.FEATURES),))

    def test_metrics_perfect_and_reversed(self):
        y = np.array([0, 0, 1, 1])
        self.assertAlmostEqual(core.roc_auc(y, y), 1.0)
        self.assertAlmostEqual(core.roc_auc(y, 1 - y), 0.0)
        m = core.compute_metrics(y, y)
        self.assertEqual(m["tp"], 2)
        self.assertEqual(m["tn"], 2)
        self.assertAlmostEqual(m["sensitivity"], 1.0)
        self.assertAlmostEqual(m["specificity"], 1.0)


class TestPersistence(unittest.TestCase):
    def test_save_load_predict(self):
        df = core.load_data()
        mask = np.ones(len(df), dtype=bool)
        scaler, model = core.fit_on_subset(df, mask, l2=1.0)
        path = ROOT / "artifacts" / "_test_model.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            core.save_model(path, scaler, model, {"threshold": 0.5})
            payload = core.load_model(path)
            out = core.predict_frame(df.head(5), payload)
        finally:
            path.unlink(missing_ok=True)
        self.assertIn("probability", out.columns)
        self.assertTrue(((out["probability"] >= 0) & (out["probability"] <= 1)).all())
        self.assertEqual(len(out), 5)

    def test_predict_rejects_missing_and_nan(self):
        df = core.load_data()
        mask = np.ones(len(df), dtype=bool)
        scaler, model = core.fit_on_subset(df, mask, l2=1.0)
        path = ROOT / "artifacts" / "_test_model_validation.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            core.save_model(path, scaler, model, {"threshold": 0.5})
            payload = core.load_model(path)
            missing = df.head(3).drop(columns=[core.FEATURES[0]])
            with self.assertRaises(ValueError):
                core.predict_frame(missing, payload)
            nan_df = df.head(3).copy()
            nan_df.loc[nan_df.index[0], core.FEATURES[0]] = np.nan
            with self.assertRaises(ValueError):
                core.predict_frame(nan_df, payload)
        finally:
            path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
