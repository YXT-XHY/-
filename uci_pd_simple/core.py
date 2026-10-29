# -*- coding: utf-8 -*-
"""Core logic for the minimal UCI Parkinson voice baseline.

Design goals
------------
- No scikit-learn dependency: only numpy + pandas.
- Subject-level evaluation (the 195 recordings come from 31/32 subjects).
- One deterministic, explainable model: standardized logistic regression.
- Everything runs on a laptop in a few seconds.

This is an educational/research baseline, not a clinical device.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "parkinsons.data"
ARTIFACTS_DIR = BASE_DIR / "artifacts"

FEATURES = [
    "MDVP:Fo(Hz)",
    "MDVP:Fhi(Hz)",
    "MDVP:Flo(Hz)",
    "MDVP:Jitter(%)",
    "MDVP:Jitter(Abs)",
    "MDVP:RAP",
    "MDVP:PPQ",
    "Jitter:DDP",
    "MDVP:Shimmer",
    "MDVP:Shimmer(dB)",
    "Shimmer:APQ3",
    "Shimmer:APQ5",
    "MDVP:APQ",
    "Shimmer:DDA",
    "NHR",
    "HNR",
    "RPDE",
    "DFA",
    "spread1",
    "spread2",
    "D2",
    "PPE",
]
TARGET = "status"
NAME = "name"
SUBJECT = "subject"


# --------------------------------------------------------------------------- data
def load_data(path: str | Path = DATA_PATH) -> pd.DataFrame:
    """Load and validate the UCI Parkinson's data file."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"Dataset not found: {path}. Put the UCI parkinsons.data file there."
        )
    df = pd.read_csv(path)
    missing = [c for c in [NAME, TARGET, *FEATURES] if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    df[SUBJECT] = df[NAME].astype(str).str.extract(r"(S\d+)", expand=False)
    if df[SUBJECT].isna().any():
        bad = df.loc[df[SUBJECT].isna(), NAME].head(5).tolist()
        raise ValueError(f"Could not parse subject IDs from names, e.g. {bad}")

    if df[FEATURES + [TARGET]].isna().any().any():
        raise ValueError("Dataset contains missing values in features or target.")
    df[TARGET] = df[TARGET].astype(int)
    if not set(df[TARGET].unique()).issubset({0, 1}):
        raise ValueError("Target must be binary (0/1).")

    # One label per subject is required for grouped evaluation.
    labels = df.groupby(SUBJECT)[TARGET].nunique()
    if (labels > 1).any():
        raise ValueError(f"Subjects with inconsistent labels: {labels[labels > 1].index.tolist()}")
    return df.reset_index(drop=True)


def summarize(df: pd.DataFrame) -> dict[str, Any]:
    """Small, printable dataset summary."""
    per_subject = df.groupby(SUBJECT).size()
    return {
        "rows": int(len(df)),
        "subjects": int(df[SUBJECT].nunique()),
        "pd_subjects": int(df.loc[df[TARGET] == 1, SUBJECT].nunique()),
        "hc_subjects": int(df.loc[df[TARGET] == 0, SUBJECT].nunique()),
        "pd_rows": int((df[TARGET] == 1).sum()),
        "hc_rows": int((df[TARGET] == 0).sum()),
        "features": len(FEATURES),
        "recordings_per_subject_min": int(per_subject.min()),
        "recordings_per_subject_max": int(per_subject.max()),
        "duplicate_names": int(df[NAME].duplicated().sum()),
    }


# --------------------------------------------------------------------------- model
def _sigmoid(z: np.ndarray) -> np.ndarray:
    z = np.clip(np.asarray(z, dtype=float), -35.0, 35.0)
    return 1.0 / (1.0 + np.exp(-z))


@dataclass
class Standardizer:
    mean: np.ndarray | None = None
    std: np.ndarray | None = None

    def fit(self, X: np.ndarray) -> "Standardizer":
        X = np.asarray(X, dtype=float)
        self.mean = X.mean(axis=0)
        self.std = X.std(axis=0)
        self.std = np.where(self.std < 1e-12, 1.0, self.std)
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        if self.mean is None or self.std is None:
            raise RuntimeError("Standardizer is not fitted.")
        return (np.asarray(X, dtype=float) - self.mean) / self.std


class LogisticRegression:
    """L2-regularized logistic regression fitted with Newton-Raphson (IRLS).

    The model is deliberately small and transparent: 22 coefficients + intercept.
    """

    def __init__(self, l2: float = 1.0, max_iter: int = 100, tol: float = 1e-8):
        self.l2 = float(l2)
        self.max_iter = int(max_iter)
        self.tol = float(tol)
        self.coef_: np.ndarray | None = None
        self.intercept_: float = 0.0
        self.n_iter_: int = 0

    def fit(self, X: np.ndarray, y: np.ndarray) -> "LogisticRegression":
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).reshape(-1)
        if X.ndim != 2:
            raise ValueError("X must be 2-D.")
        if len(X) != len(y):
            raise ValueError("X and y have different lengths.")
        if len(np.unique(y)) < 2:
            raise ValueError("y must contain both classes.")

        Xb = np.column_stack([np.ones(len(X)), X])
        beta = np.zeros(Xb.shape[1], dtype=float)
        n_features = X.shape[1]

        for it in range(1, self.max_iter + 1):
            eta = Xb @ beta
            p = _sigmoid(eta)
            w = np.clip(p * (1.0 - p), 1e-6, None)
            z = eta + (y - p) / w

            A = Xb.T @ (w[:, None] * Xb)
            # Do not regularize the intercept.
            A[1:, 1:] += self.l2 * np.eye(n_features)
            b = Xb.T @ (w * z)

            try:
                new_beta = np.linalg.solve(A, b)
            except np.linalg.LinAlgError:
                new_beta = np.linalg.lstsq(A, b, rcond=None)[0]

            if np.linalg.norm(new_beta - beta) < self.tol:
                beta = new_beta
                self.n_iter_ = it
                break
            beta = new_beta
        else:
            self.n_iter_ = self.max_iter

        self.intercept_ = float(beta[0])
        self.coef_ = beta[1:].astype(float)
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if self.coef_ is None:
            raise RuntimeError("Model is not fitted.")
        X = np.asarray(X, dtype=float)
        return _sigmoid(self.intercept_ + X @ self.coef_)

    def predict(self, X: np.ndarray, threshold: float = 0.5) -> np.ndarray:
        return (self.predict_proba(X) >= threshold).astype(int)


# --------------------------------------------------------------------------- metrics
def roc_auc(y: np.ndarray, p: np.ndarray) -> float:
    """Rank-based AUC with tie handling, implemented pairwise (n=195)."""
    y = np.asarray(y, dtype=int)
    p = np.asarray(p, dtype=float)
    pos = p[y == 1]
    neg = p[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    greater = (pos[:, None] > neg[None, :]).mean()
    equal = (pos[:, None] == neg[None, :]).mean()
    return float(greater + 0.5 * equal)


def compute_metrics(
    y: np.ndarray, p: np.ndarray, threshold: float = 0.5
) -> dict[str, float]:
    y = np.asarray(y, dtype=int)
    p = np.asarray(p, dtype=float)
    pred = (p >= threshold).astype(int)
    tp = int(((y == 1) & (pred == 1)).sum())
    tn = int(((y == 0) & (pred == 0)).sum())
    fp = int(((y == 0) & (pred == 1)).sum())
    fn = int(((y == 1) & (pred == 0)).sum())
    sens = tp / (tp + fn) if (tp + fn) else float("nan")
    spec = tn / (tn + fp) if (tn + fp) else float("nan")
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    f1 = 2 * prec * sens / (prec + sens) if (prec + sens) else 0.0
    acc = (tp + tn) / len(y) if len(y) else float("nan")
    brier = float(np.mean((p - y) ** 2))
    return {
        "n": int(len(y)),
        "threshold": float(threshold),
        "auc": roc_auc(y, p),
        "accuracy": float(acc),
        "sensitivity": float(sens),
        "specificity": float(spec),
        "precision": float(prec),
        "f1": float(f1),
        "brier": brier,
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
    }


def calibration_table(y: np.ndarray, p: np.ndarray, bins: int = 5) -> list[dict[str, float]]:
    y = np.asarray(y, dtype=float)
    p = np.asarray(p, dtype=float)
    edges = np.linspace(0.0, 1.0, bins + 1)
    idx = np.clip(np.digitize(p, edges[1:-1]), 0, bins - 1)
    out: list[dict[str, float]] = []
    for b in range(bins):
        mask = idx == b
        if not mask.any():
            continue
        out.append(
            {
                "bin": b + 1,
                "n": int(mask.sum()),
                "mean_predicted": float(p[mask].mean()),
                "observed_rate": float(y[mask].mean()),
            }
        )
    return out


def metrics_summary(metrics_df: pd.DataFrame) -> dict[str, dict[str, float]]:
    cols = ["auc", "accuracy", "sensitivity", "specificity", "precision", "f1", "brier"]
    out: dict[str, dict[str, float]] = {}
    for c in cols:
        s = metrics_df[c].astype(float)
        out[c] = {
            "mean": float(s.mean()),
            "std": float(s.std(ddof=1)) if len(s) > 1 else 0.0,
            "p2_5": float(s.quantile(0.025)),
            "p97_5": float(s.quantile(0.975)),
        }
    return out


# --------------------------------------------------------------------------- evaluation
def make_subject_folds(df: pd.DataFrame, n_splits: int = 5, seed: int = 42) -> list[list[str]]:
    """Stratified group folds: every subject appears in exactly one test fold."""
    if n_splits < 2:
        raise ValueError("n_splits must be >= 2.")
    labels = df.groupby(SUBJECT)[TARGET].first()
    if n_splits > len(labels):
        raise ValueError("n_splits cannot exceed the number of subjects.")
    rng = np.random.default_rng(seed)
    folds: list[list[str]] = [[] for _ in range(n_splits)]
    for label in (1, 0):
        ids = labels[labels == label].index.tolist()
        if len(ids) < n_splits:
            raise ValueError(
                f"Class {label} has only {len(ids)} subjects; reduce n_splits."
            )
        rng.shuffle(ids)
        offset = int(rng.integers(0, n_splits))
        for i, sid in enumerate(ids):
            folds[(i + offset) % n_splits].append(sid)
    return folds


def fit_on_subset(
    df: pd.DataFrame, mask: np.ndarray, l2: float = 1.0
) -> tuple[Standardizer, LogisticRegression]:
    X = df.loc[mask, FEATURES].to_numpy(dtype=float)
    y = df.loc[mask, TARGET].to_numpy(dtype=int)
    scaler = Standardizer().fit(X)
    model = LogisticRegression(l2=l2).fit(scaler.transform(X), y)
    return scaler, model


def cross_validate(
    df: pd.DataFrame,
    n_splits: int = 5,
    repeats: int = 20,
    l2: float = 1.0,
    threshold: float = 0.5,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Repeated subject-grouped CV.

    Returns
    -------
    metrics_df : one row per repeat (metrics computed on pooled OOF predictions)
    oof_df     : all out-of-fold predictions, with subject/true/probability
    """
    y_all = df[TARGET].to_numpy(dtype=int)
    metric_rows: list[dict[str, float]] = []
    oof_frames: list[pd.DataFrame] = []

    for r in range(repeats):
        folds = make_subject_folds(df, n_splits=n_splits, seed=1000 + r)
        p_oof = np.full(len(df), np.nan, dtype=float)
        for test_subjects in folds:
            test_mask = df[SUBJECT].isin(test_subjects).to_numpy()
            train_mask = ~test_mask
            scaler, model = fit_on_subset(df, train_mask, l2=l2)
            X_test = df.loc[test_mask, FEATURES].to_numpy(dtype=float)
            p_oof[test_mask] = model.predict_proba(scaler.transform(X_test))

        if np.isnan(p_oof).any():
            raise RuntimeError("Some rows were not assigned to a test fold.")
        m = compute_metrics(y_all, p_oof, threshold=threshold)
        m["repeat"] = r
        metric_rows.append(m)
        oof_frames.append(
            pd.DataFrame(
                {
                    "repeat": r,
                    "name": df[NAME],
                    "subject": df[SUBJECT],
                    "y_true": y_all,
                    "probability": p_oof,
                }
            )
        )

    return pd.DataFrame(metric_rows), pd.concat(oof_frames, ignore_index=True)


def random_row_split_check(
    df: pd.DataFrame,
    repeats: int = 20,
    test_size: float = 0.2,
    l2: float = 1.0,
    threshold: float = 0.5,
    seed: int = 2026,
) -> pd.DataFrame:
    """A deliberately *wrong* random row split, for teaching/leakage comparison.

    The same subject can appear in train and test because rows are split at random.
    Do not use these numbers as model performance.
    """
    rng = np.random.default_rng(seed)
    y = df[TARGET].to_numpy(dtype=int)
    n_test = max(2, int(round(len(df) * test_size)))
    rows: list[dict[str, float]] = []
    for r in range(repeats):
        idx = rng.permutation(len(df))
        test_idx = idx[:n_test]
        train_idx = idx[n_test:]
        train_mask = np.zeros(len(df), dtype=bool)
        train_mask[train_idx] = True
        test_mask = ~train_mask
        scaler, model = fit_on_subset(df, train_mask, l2=l2)
        X_test = df.loc[test_mask, FEATURES].to_numpy(dtype=float)
        p = model.predict_proba(scaler.transform(X_test))
        m = compute_metrics(y[test_mask], p, threshold=threshold)
        m["repeat"] = r
        rows.append(m)
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- persistence
def save_model(
    path: str | Path,
    scaler: Standardizer,
    model: LogisticRegression,
    metadata: dict[str, Any],
) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if scaler.mean is None or scaler.std is None or model.coef_ is None:
        raise RuntimeError("Cannot save an unfitted model.")
    payload = {
        "format": "uci-pd-logreg-v1",
        "features": FEATURES,
        "mean": scaler.mean.tolist(),
        "std": scaler.std.tolist(),
        "coef": model.coef_.tolist(),
        "intercept": float(model.intercept_),
        "threshold": float(metadata.get("threshold", 0.5)),
        "metadata": metadata,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_model(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("format") != "uci-pd-logreg-v1":
        raise ValueError("Unsupported model format.")
    if payload.get("features") != FEATURES:
        raise ValueError("Model feature list does not match the current code.")
    return payload


def predict_frame(df: pd.DataFrame, payload: dict[str, Any]) -> pd.DataFrame:
    missing = [c for c in FEATURES if c not in df.columns]
    if missing:
        raise ValueError(f"Input is missing features: {missing}")
    if df[FEATURES].isna().any().any():
        bad = df[FEATURES].isna().sum()
        bad = bad[bad > 0].to_dict()
        raise ValueError(f"Input contains missing values: {bad}")
    try:
        X = df[FEATURES].to_numpy(dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError("Input features must be numeric.") from exc

    mean = np.asarray(payload["mean"], dtype=float)
    std = np.asarray(payload["std"], dtype=float)
    coef = np.asarray(payload["coef"], dtype=float)
    z = ((X - mean) / std) @ coef + float(payload["intercept"])
    p = _sigmoid(z)
    out = df.copy()
    out["probability"] = p
    out["prediction"] = (p >= float(payload.get("threshold", 0.5))).astype(int)
    out["risk_band"] = np.where(p < 0.35, "low", np.where(p < 0.65, "medium", "high"))
    return out
