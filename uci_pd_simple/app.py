# -*- coding: utf-8 -*-
"""Command line entry point for the minimal UCI Parkinson baseline.

Examples
--------
python app.py summary
python app.py evaluate --repeats 20
python app.py train --repeats 20
python app.py predict --input data/parkinsons.data --output artifacts/predictions.csv
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from core import (
    ARTIFACTS_DIR,
    DATA_PATH,
    FEATURES,
    TARGET,
    compute_metrics,
    cross_validate,
    fit_on_subset,
    load_data,
    load_model,
    metrics_summary,
    predict_frame,
    random_row_split_check,
    save_model,
    summarize,
)

BASE_DIR = Path(__file__).resolve().parent


def _json_default(obj):
    if hasattr(obj, "item"):
        return obj.item()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default),
        encoding="utf-8",
    )


def cmd_summary(args: argparse.Namespace) -> int:
    df = load_data(args.data)
    info = summarize(df)
    print(json.dumps(info, ensure_ascii=False, indent=2))
    print("\nPer-subject recording counts:")
    print(df.groupby("subject").size().describe().to_string())
    print("\nNote: the distributed UCI file yields 32 subject IDs (24 PD / 8 HC);")
    print("the UCI catalogue text says 31 subjects (23 PD). This project uses the file as-is.")
    return 0


def cmd_evaluate(args: argparse.Namespace) -> int:
    df = load_data(args.data)
    print("Dataset:", json.dumps(summarize(df), ensure_ascii=False))
    metrics_df, oof_df = cross_validate(
        df, n_splits=args.folds, repeats=args.repeats, l2=args.l2, threshold=args.threshold
    )
    summary = metrics_summary(metrics_df)
    print(f"\nSubject-grouped CV: {args.repeats} repeats x {args.folds} folds")
    print(f"{'metric':<14}{'mean':>9}{'std':>9}{'2.5%':>9}{'97.5%':>9}")
    for name, vals in summary.items():
        print(
            f"{name:<14}{vals['mean']:>9.4f}{vals['std']:>9.4f}"
            f"{vals['p2_5']:>9.4f}{vals['p97_5']:>9.4f}"
        )

    leak = random_row_split_check(
        df, repeats=args.repeats, l2=args.l2, threshold=args.threshold
    )
    leak_summary = metrics_summary(leak)
    print("\nRandom row split (WRONG - same subject can leak across splits):")
    print(
        f"  AUC {leak_summary['auc']['mean']:.4f} +/- {leak_summary['auc']['std']:.4f} "
        f"| sensitivity {leak_summary['sensitivity']['mean']:.4f} "
        f"| specificity {leak_summary['specificity']['mean']:.4f}"
    )
    print("  Use the subject-grouped numbers above for any honest comparison.")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    metrics_df.to_csv(out_dir / "cv_metrics.csv", index=False)
    oof_df.to_csv(out_dir / "oof_predictions.csv", index=False)
    write_json(
        out_dir / "cv_summary.json",
        {
            "dataset": summarize(df),
            "config": {
                "folds": args.folds,
                "repeats": args.repeats,
                "l2": args.l2,
                "threshold": args.threshold,
            },
            "subject_grouped_cv": summary,
            "random_row_split_warning": leak_summary,
        },
    )
    print(f"\nSaved: {out_dir / 'cv_summary.json'}")
    print(f"Saved: {out_dir / 'oof_predictions.csv'}")
    return 0


def cmd_train(args: argparse.Namespace) -> int:
    df = load_data(args.data)
    full_mask = pd.Series(True, index=df.index).to_numpy()
    scaler, model = fit_on_subset(df, full_mask, l2=args.l2)

    metrics_df, oof_df = cross_validate(
        df, n_splits=args.folds, repeats=args.repeats, l2=args.l2, threshold=args.threshold
    )
    summary = metrics_summary(metrics_df)

    metadata = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset": summarize(df),
        "model": "L2 logistic regression (IRLS) + standardization",
        "features": FEATURES,
        "target": TARGET,
        "threshold": args.threshold,
        "l2": args.l2,
        "cv": {
            "protocol": "repeated stratified subject-grouped K-fold",
            "folds": args.folds,
            "repeats": args.repeats,
            "summary": summary,
        },
        "warning": "Research/education baseline only; not a clinical device.",
    }

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    model_path = save_model(out_dir / "model.json", scaler, model, metadata)
    metrics_df.to_csv(out_dir / "cv_metrics.csv", index=False)
    oof_df.to_csv(out_dir / "oof_predictions.csv", index=False)
    write_json(out_dir / "model_card.json", metadata)

    print(f"Saved model: {model_path}")
    print(f"Saved model card: {out_dir / 'model_card.json'}")
    print(
        f"CV AUC: {summary['auc']['mean']:.4f} +/- {summary['auc']['std']:.4f}; "
        f"sensitivity {summary['sensitivity']['mean']:.4f}; "
        f"specificity {summary['specificity']['mean']:.4f}"
    )
    print("Features used:", len(FEATURES))
    print("Coefficients (standardized scale):")
    for name, coef in sorted(zip(FEATURES, model.coef_), key=lambda x: abs(x[1]), reverse=True):
        print(f"  {name:<20}{coef: .4f}")
    return 0


def cmd_predict(args: argparse.Namespace) -> int:
    payload = load_model(args.model)
    df = pd.read_csv(args.input)
    out = predict_frame(df, payload)
    out_dir = Path(args.output).parent
    out_dir.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.output, index=False)
    cols = [c for c in ["name", "subject", "probability", "prediction", "risk_band"] if c in out.columns]
    print(out[cols].head(20).to_string(index=False))
    if "status" in out.columns:
        m = compute_metrics(out["status"].to_numpy(), out["probability"].to_numpy())
        print("\nMetrics on this input (WARNING: in-sample if this file was used for training):")
        print(json.dumps(m, ensure_ascii=False, indent=2))
    print(f"\nSaved: {args.output}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Minimal UCI Parkinson voice baseline (subject-grouped evaluation)."
    )
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("summary", help="Inspect the dataset.")
    s.add_argument("--data", type=Path, default=DATA_PATH)
    s.set_defaults(func=cmd_summary)

    e = sub.add_parser("evaluate", help="Repeated subject-grouped CV + leakage check.")
    e.add_argument("--data", type=Path, default=DATA_PATH)
    e.add_argument("--folds", type=int, default=5)
    e.add_argument("--repeats", type=int, default=20)
    e.add_argument("--l2", type=float, default=1.0)
    e.add_argument("--threshold", type=float, default=0.5)
    e.add_argument("--out-dir", type=Path, default=ARTIFACTS_DIR)
    e.set_defaults(func=cmd_evaluate)

    t = sub.add_parser("train", help="Fit the final model and save artifacts.")
    t.add_argument("--data", type=Path, default=DATA_PATH)
    t.add_argument("--folds", type=int, default=5)
    t.add_argument("--repeats", type=int, default=20)
    t.add_argument("--l2", type=float, default=1.0)
    t.add_argument("--threshold", type=float, default=0.5)
    t.add_argument("--out-dir", type=Path, default=ARTIFACTS_DIR)
    t.set_defaults(func=cmd_train)

    pr = sub.add_parser("predict", help="Score a CSV with the 22 UCI features.")
    pr.add_argument("--model", type=Path, default=ARTIFACTS_DIR / "model.json")
    pr.add_argument("--input", type=Path, required=True)
    pr.add_argument("--output", type=Path, default=ARTIFACTS_DIR / "predictions.csv")
    pr.set_defaults(func=cmd_predict)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except (FileNotFoundError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
