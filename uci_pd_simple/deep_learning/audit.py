"""Recompute held-out predictions from saved weights and audit subject separation."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from safetensors.torch import load_file
import torch

from .model import ModelConfig, SpeechTransformer
from .train import evaluate, metrics, write_json
from .runtime import artifact_status


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", type=Path, default=Path("artifacts/audio_transformer_v1"))
    parser.add_argument("--cache", type=Path, default=Path("data/mdvr-kcl/reading_logmel_v1.npz"))
    parser.add_argument("--manifest", type=Path, default=Path("data/mdvr-kcl/manifest.csv"))
    args = parser.parse_args()
    torch.set_num_threads(4)
    folder = args.model_dir
    card = json.loads((folder / "model_card.json").read_text(encoding="utf-8"))
    assert artifact_status(folder)["ready"], "Artifact not eligible for research classification"
    assert hashlib.sha256(args.manifest.read_bytes()).hexdigest() == card["manifest_sha256"]
    splits = json.loads((folder / "splits.json").read_text(encoding="utf-8"))
    stored_oof = json.loads((folder / "oof_predictions.json").read_text(encoding="utf-8"))
    with np.load(args.cache, allow_pickle=False) as cache:
        X, y, ids = cache["X"], cache["y"], cache["subjects"]
    all_subjects = set(ids)
    seen = set()
    recomputed = []
    maximum_error = 0.0
    for split, fold in zip(splits, card["folds"], strict=True):
        train, val, test = (set(split[k]) for k in ("train", "validation", "test"))
        assert not (train&val or train&test or val&test)
        assert train|val|test == all_subjects
        assert not seen&test
        seen |= test
        model = SpeechTransformer(ModelConfig(**card["model_config"]))
        model.load_state_dict(load_file(str(folder / fold["file"])))
        rows, _ = evaluate(model, X, y, ids, np.flatnonzero(np.isin(ids, list(test))), "cpu", 16)
        for row in rows:
            original = next(r for r in stored_oof if r["subject"]==row["subject"])
            assert original["fold"] == split["fold"]
            assert original["label"] == row["label"]
            error = abs(original["score"]-row["score"])
            maximum_error = max(maximum_error, error)
            assert error < 1e-4, f"Weight/prediction mismatch {row['subject']}: {error}"
            recomputed.append(row)
    assert seen == all_subjects and len(stored_oof) == len(all_subjects)
    recomputed_metrics = metrics(recomputed)
    for name in ("auc", "accuracy", "sensitivity", "specificity"):
        assert abs(recomputed_metrics[name]-card["evaluation"]["metrics"][name]) < 1e-9
    report = {"passed": True, "subjects": len(all_subjects), "outer_folds": len(splits),
              "no_subject_overlap": True, "every_subject_tested_once": True,
              "weights_sha256_verified": True, "manifest_verified": True,
              "cpu_vs_training_max_score_error": maximum_error,
              "recomputed_metrics": recomputed_metrics}
    write_json(folder / "audit.json", report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
