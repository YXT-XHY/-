"""Subject-level visualization data computed from real held-out predictions."""
import json
import math
from pathlib import Path


def build_evaluation(directory):
    directory = Path(directory)
    card = json.loads((directory / "model_card.json").read_text(encoding="utf-8"))
    rows = json.loads((directory / "oof_predictions.json").read_text(encoding="utf-8"))
    if not rows or len({r["subject"] for r in rows}) != len(rows):
        raise ValueError("OOF records must contain exactly one prediction per subject")
    for row in rows:
        if row["label"] not in (0, 1) or not math.isfinite(row["score"]) or not 0 <= row["score"] <= 1:
            raise ValueError("Invalid OOF labels or scores")
    positive = sum(r["label"] for r in rows)
    negative = len(rows) - positive
    if not positive or not negative:
        raise ValueError("Both classes are required for ROC")
    points = [{"fpr": 0.0, "tpr": 0.0}]
    tp = fp = 0
    grouped = {}
    for row in rows:
        grouped.setdefault(row["score"], []).append(row["label"])
    for score in sorted(grouped, reverse=True):
        tp += sum(grouped[score])
        fp += len(grouped[score]) - sum(grouped[score])
        points.append({"fpr": fp / negative, "tpr": tp / positive})
    auc = sum((b["fpr"]-a["fpr"])*(b["tpr"]+a["tpr"])/2 for a, b in zip(points, points[1:]))
    threshold = card["threshold"]
    tp = sum(r["label"] == 1 and r["score"] >= threshold for r in rows)
    fp = sum(r["label"] == 0 and r["score"] >= threshold for r in rows)
    tn, fn = negative - fp, positive - tp
    metrics = {"subjects": len(rows), "auc": auc, "accuracy": (tp+tn)/len(rows),
               "sensitivity": tp/positive, "specificity": tn/negative,
               "balanced_accuracy": (tp/positive+tn/negative)/2, "tp": tp, "fp": fp, "tn": tn, "fn": fn}
    for key, value in metrics.items():
        if abs(value-card["evaluation"]["metrics"][key]) > 1e-6:
            raise ValueError("OOF data differs from model card: " + key)
    return {"metrics": metrics, "roc": points, "threshold": threshold,
            "auc_bootstrap_95": card["evaluation"].get("auc_bootstrap_95"),
            "dataset": card["dataset"], "unit": "subject", "source": "saved_subject_oof",
            "notice": "按受试者留出预测（OOF）；不是本次录音准确率，也不是部署集成模型的外部临床验证。"}
