"""Speaker-disjoint nested validation for the raw audio CNN/Transformer."""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import random
import time

import numpy as np
from safetensors.torch import save_file
from sklearn.metrics import (accuracy_score, balanced_accuracy_score, brier_score_loss,
                             confusion_matrix, roc_auc_score)
from sklearn.model_selection import StratifiedKFold, train_test_split
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler

from .audio import AudioConfig, load_audio, log_mel, segment_audio
from .model import ModelConfig, SpeechTransformer


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    temporary.replace(path)


def seed_everything(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def read_manifest(path: Path, task="reading"):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    required = {"path", "subject", "label", "task", "language", "dataset"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError(f"Manifest requires {required}")
    selected = [r for r in rows if r["task"] == task]
    if not selected:
        raise ValueError(f"No recordings for task={task}; inspect manifest task labels")
    subjects = {}
    hashes = {}
    strata = {}
    for row in selected:
        for field in ("path", "subject", "label", "task", "language", "dataset"):
            row[field] = (row[field] or "").strip()
            if not row[field]:
                raise ValueError(f"Empty manifest field: {field}")
        if row["label"] not in {"0", "1"}:
            raise ValueError("Labels must be 0=HC / 1=PD")
        if row["subject"] in subjects and subjects[row["subject"]] != int(row["label"]):
            raise ValueError("Conflicting labels for the same subject")
        subjects[row["subject"]] = int(row["label"])
        strata.setdefault((row["dataset"], row["language"]), set()).add(int(row["label"]))
        audio = Path(row["path"])
        if not audio.is_absolute():
            audio = path.parent / audio
        if not audio.is_file():
            raise ValueError(f"Missing audio: {audio}")
        row["path"] = str(audio.resolve())
        digest = hashlib.sha256(audio.read_bytes()).hexdigest()
        if digest in hashes:
            raise ValueError(f"Duplicate audio files: {row['path']} and {hashes[digest]}")
        hashes[digest] = row["path"]
    if set(subjects.values()) != {0, 1}:
        raise ValueError("Training requires both HC and PD subjects")
    for (dataset, language), labels in strata.items():
        if labels != {0, 1}:
            raise ValueError(f"Dataset/language stratum {dataset}/{language} contains only one class; "
                             "do not confound diagnosis with data source or language")
    return selected, subjects


def prepare_cache(rows, audio_config, cache: Path):
    identity = hashlib.sha256(json.dumps({"rows": [
        {**r, "bytes": Path(r["path"]).stat().st_size, "mtime": Path(r["path"]).stat().st_mtime_ns}
        for r in rows], "audio": audio_config.to_dict(), "version": 1}, sort_keys=True).encode()).hexdigest()
    if cache.exists():
        with np.load(cache, allow_pickle=False) as saved:
            if str(saved["identity"].item()) == identity:
                return saved["X"], saved["y"], saved["subjects"], saved["starts"]
    specs, labels, subjects, starts = [], [], [], []
    for index, row in enumerate(rows):
        samples = load_audio(Path(row["path"]), audio_config.sample_rate)
        chunks = segment_audio(samples, audio_config, max_segments=20)
        for start, chunk in chunks:
            specs.append(log_mel(chunk, audio_config).numpy())
            labels.append(int(row["label"]))
            subjects.append(row["subject"])
            starts.append(start)
        print(json.dumps({"preprocess": index+1, "of": len(rows), "segments": len(chunks),
                          "subject": row["subject"]}), flush=True)
    X = np.stack(specs).astype(np.float32)
    y, ids, starts = np.array(labels, np.int64), np.array(subjects), np.array(starts)
    cache.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(cache, identity=identity, X=X, y=y, subjects=ids, starts=starts)
    return X, y, ids, starts


class SpectrogramDataset(Dataset):
    def __init__(self, X, y, indices, augment=False):
        self.X, self.y, self.indices, self.augment = X, y, indices, augment

    def __len__(self):
        return len(self.indices)

    def __getitem__(self, item):
        index = self.indices[item]
        x = torch.from_numpy(self.X[index].copy())
        if self.augment:
            # Only training windows are augmented. Never modify validation/test audio.
            x += torch.randn_like(x) * .015
            for dimension, max_width in [(0, 5), (1, 25)]:
                width = int(torch.randint(0, max_width+1, ()).item())
                start = int(torch.randint(0, max(1, x.shape[dimension]-width+1), ()).item())
                if dimension == 0:
                    x[start:start+width, :] = 0
                else:
                    x[:, start:start+width] = 0
        return x, float(self.y[index])


def aggregate_subjects(labels, logits, ids):
    rows = []
    for subject in sorted(set(ids)):
        mask = ids == subject
        true = np.unique(labels[mask])
        if len(true) != 1:
            raise ValueError("Subject labels must be consistent")
        mean_logit = float(np.asarray(logits)[mask].mean())
        score = float(1 / (1 + np.exp(-np.clip(mean_logit, -35, 35))))
        rows.append({"subject": subject, "label": int(true[0]), "logit": mean_logit,
                     "score": score, "segments": int(mask.sum())})
    return rows


def metrics(rows):
    y = np.array([r["label"] for r in rows])
    p = np.array([r["score"] for r in rows])
    tn, fp, fn, tp = confusion_matrix(y, p >= .5, labels=[0, 1]).ravel()
    return {"subjects": len(rows), "auc": float(roc_auc_score(y, p)),
            "accuracy": float(accuracy_score(y, p >= .5)),
            "balanced_accuracy": float(balanced_accuracy_score(y, p >= .5)),
            "sensitivity": float(tp / max(1, tp+fn)),
            "specificity": float(tn / max(1, tn+fp)),
            "brier": float(brier_score_loss(y, p)),
            "tp": int(tp), "tn": int(tn), "fp": int(fp), "fn": int(fn)}


def bootstrap_auc(rows, count=2000):
    rng = np.random.default_rng(2026)
    y = np.array([r["label"] for r in rows])
    p = np.array([r["score"] for r in rows])
    positive, negative = np.flatnonzero(y == 1), np.flatnonzero(y == 0)
    values = []
    for _ in range(count):
        selected = np.r_[rng.choice(positive, len(positive)), rng.choice(negative, len(negative))]
        values.append(roc_auc_score(y[selected], p[selected]))
    return [float(np.quantile(values, .025)), float(np.quantile(values, .975))]


@torch.no_grad()
def evaluate(model, X, y, ids, indices, device, batch_size):
    model.eval()
    output = []
    loader = DataLoader(SpectrogramDataset(X, y, indices), batch_size=batch_size, shuffle=False)
    for batch, _ in loader:
        output.extend(model(batch.to(device)).cpu().tolist())
    rows = aggregate_subjects(y[indices], np.array(output), ids[indices])
    logits = torch.tensor([r["logit"] for r in rows])
    labels = torch.tensor([float(r["label"]) for r in rows])
    loss = float(nn.functional.binary_cross_entropy_with_logits(logits, labels))
    return rows, loss


def train(args):
    start_time = time.time()
    torch.set_num_threads(min(4, torch.get_num_threads()))
    seed_everything(args.seed)
    device = torch.device("cuda" if args.device == "auto" and torch.cuda.is_available()
                          else "cpu" if args.device == "auto" else args.device)
    audio_config, model_config = AudioConfig(), ModelConfig()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if (output / "model_card.json").exists():
        raise ValueError("Output already contains a published model; choose a new --output")
    rows, labels_by_subject = read_manifest(args.manifest.resolve(), args.task)
    names = np.array(sorted(labels_by_subject))
    subject_labels = np.array([labels_by_subject[name] for name in names])
    if min(Counter(subject_labels).values()) < args.folds:
        raise ValueError("Not enough subjects per class for grouped folds")
    X, y, ids, starts = prepare_cache(rows, audio_config, args.cache)
    print(json.dumps({"device": str(device), "segments": len(X), "subjects": len(names),
                      "parameters": sum(p.numel() for p in SpeechTransformer(model_config).parameters())}), flush=True)
    outer = StratifiedKFold(n_splits=args.folds, shuffle=True, random_state=args.seed)
    oof, folds, splits = [], [], []
    for fold, (remaining, heldout) in enumerate(outer.split(names, subject_labels)):
        seed_everything(args.seed+fold)
        train_ids, val_ids = train_test_split(names[remaining], test_size=.22,
                                             stratify=subject_labels[remaining], random_state=args.seed+fold)
        test_ids = names[heldout]
        assert not (set(train_ids)&set(val_ids) or set(train_ids)&set(test_ids) or set(val_ids)&set(test_ids))
        train_idx = np.flatnonzero(np.isin(ids, train_ids))
        val_idx = np.flatnonzero(np.isin(ids, val_ids))
        test_idx = np.flatnonzero(np.isin(ids, test_ids))
        counts = Counter(ids[train_idx])
        class_subjects = Counter(labels_by_subject[s] for s in train_ids)
        weights = [1/(counts[ids[i]]*class_subjects[int(y[i])]) for i in train_idx]
        generator = torch.Generator().manual_seed(args.seed+fold)
        sampler = WeightedRandomSampler(weights, len(train_idx), replacement=True, generator=generator)
        loader = DataLoader(SpectrogramDataset(X, y, train_idx, augment=True), sampler=sampler,
                            batch_size=args.batch_size, num_workers=0)
        model = SpeechTransformer(model_config).to(device)
        optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=.02)
        best_loss, best_state, best_epoch, stale = float("inf"), None, 0, 0
        history = []
        for epoch in range(1, args.epochs+1):
            model.train()
            total = 0
            for batch, targets in loader:
                batch, targets = batch.to(device), targets.float().to(device)
                optimizer.zero_grad(set_to_none=True)
                loss = nn.functional.binary_cross_entropy_with_logits(model(batch), targets)
                if not torch.isfinite(loss):
                    raise RuntimeError("Nonfinite training loss")
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), 1)
                optimizer.step()
                total += float(loss.detach())*len(batch)
            val_rows, val_loss = evaluate(model, X, y, ids, val_idx, device, args.batch_size)
            line = {"fold": fold+1, "epoch": epoch, "train_loss": total/len(train_idx),
                    "validation_loss": val_loss, "validation_auc": metrics(val_rows)["auc"]}
            history.append(line)
            print(json.dumps(line), flush=True)
            write_json(output / "progress.json", {"status": "training", **line,
                                                   "elapsed_seconds": round(time.time()-start_time)})
            if val_loss < best_loss-1e-4:
                best_loss, best_epoch, stale = val_loss, epoch, 0
                best_state = {k:v.detach().cpu().contiguous().clone() for k,v in model.state_dict().items()}
            else:
                stale += 1
            if stale >= args.patience:
                break
        model.load_state_dict(best_state)
        test_rows, _ = evaluate(model, X, y, ids, test_idx, device, args.batch_size)
        for row in test_rows:
            row["fold"] = fold+1
        oof.extend(test_rows)
        model_file = output / f"fold_{fold+1}.safetensors"
        save_file(best_state, str(model_file), metadata={"architecture": "cnn_transformer_v1", "labels": "0=HC,1=PD"})
        digest = hashlib.sha256(model_file.read_bytes()).hexdigest()
        folds.append({"file": model_file.name, "sha256": digest, "best_epoch": best_epoch,
                      "validation_loss": best_loss, "test": metrics(test_rows)})
        splits.append({"fold": fold+1, "train": train_ids.tolist(), "validation": val_ids.tolist(),
                       "test": test_ids.tolist()})
        write_json(output / f"history_{fold+1}.json", history)
        write_json(output / "splits.json", splits)
        write_json(output / "oof_predictions.json", oof)
    all_metrics = metrics(oof)
    ci = bootstrap_auc(oof)
    card = {"format": "neurodrive-audio-transformer-v1", "architecture": "CNN + Transformer Encoder + attention pooling",
            "trained": True, "synthetic": False, "purpose": "research_classification",
            "model_config": model_config.to_dict(), "audio_config": audio_config.to_dict(),
            "labels": {"0": "healthy_control", "1": "parkinsons"}, "folds": folds,
            "dataset": sorted({r["dataset"] for r in rows}), "languages": sorted({r["language"] for r in rows}),
            "supported_tasks": [args.task], "subjects": len(names), "recordings": len(rows), "segments": len(X),
            "seed": args.seed, "threshold": .5, "uncertain_interval": [.35, .65],
            "evaluation": {"protocol": "stratified subject-disjoint outer CV with inner validation early stopping",
                           "unit": "subject", "metrics": all_metrics, "auc_bootstrap_95": ci,
                           "ensemble_note": "OOF metrics estimate held-out fold models, not the deployed ensemble directly."},
            "manifest_sha256": hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
            "training_seconds": round(time.time()-start_time),
            "limitations": ["Small case-control dataset; not a prospective screening cohort.",
                            "No independent Mandarin validation; not a medical diagnosis.",
                            "Raw model score is not calibrated population disease probability.",
                            "Conversation audio excluded to reduce interviewer contamination."],
            "deployment_allowed": bool(all_metrics["auc"] >= .65 and all_metrics["balanced_accuracy"] >= .60)}
    provenance = args.manifest.parent / "provenance.json"
    if provenance.exists():
        card["data_provenance"] = json.loads(provenance.read_text(encoding="utf-8"))
    write_json(output / "model_card.json", card)
    write_json(output / "progress.json", {"status": "complete", "metrics": all_metrics})
    print(json.dumps(card, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=Path("data/mdvr-kcl/manifest.csv"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/audio_transformer_v1"))
    parser.add_argument("--cache", type=Path, default=Path("data/mdvr-kcl/reading_logmel_v1.npz"))
    parser.add_argument("--task", choices=["reading", "vowel", "ddk"], default="reading")
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--epochs", type=int, default=80)
    parser.add_argument("--patience", type=int, default=12)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    train(parser.parse_args())
