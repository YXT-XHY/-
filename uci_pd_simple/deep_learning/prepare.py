"""Verify the original MDVR-KCL archive and prepare a speaker-indexed manifest."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import zipfile

ARCHIVE_MD5 = "98c51bdd2b092b93f8bb038dea4505fa"
SOURCE = "https://zenodo.org/records/2867216"


def prepare(archive: Path, output: Path):
    hasher = hashlib.md5()
    with archive.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024*1024), b""):
            hasher.update(chunk)
    if hasher.hexdigest() != ARCHIVE_MD5:
        raise ValueError("MDVR-KCL 文件校验失败，不能作为官方原始语料使用")
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    with zipfile.ZipFile(archive) as zipped:
        names = zipped.namelist()
        print("Archive sample:", json.dumps(names[:35], ensure_ascii=False), flush=True)
        for item in zipped.infolist():
            if not item.filename.lower().endswith(".wav"):
                continue
            if item.file_size > 250*1024*1024:
                raise ValueError("异常大的音频文件")
            name = Path(item.filename.replace("\\", "/")).name
            match = re.search(r"(ID\d+)_(hc|pd)_", name, re.I)
            if not match:
                raise ValueError(f"无法确认受试者和标签: {item.filename}")
            # Extract under a stable sanitized folder, never trust archive paths.
            safe_parts = [p for p in Path(item.filename.replace("\\", "/")).parts
                          if p not in (".", "..", "/")]
            destination = output / "raw" / Path(*safe_parts)
            if not destination.resolve().is_relative_to(output.resolve()):
                raise ValueError("非法压缩路径")
            destination.parent.mkdir(parents=True, exist_ok=True)
            if not destination.exists() or destination.stat().st_size != item.file_size:
                with zipped.open(item) as src, destination.open("wb") as dest:
                    for chunk in iter(lambda: src.read(1024*1024), b""):
                        dest.write(chunk)
            task_path = item.filename.lower()
            task = "reading" if any(s in task_path for s in ("readtext", "read_text", "read text")) else "conversation"
            rows.append({"path": str(destination.resolve()), "subject": "MDVR_"+match[1].upper(),
                         "label": 1 if match[2].lower()=="pd" else 0,
                         "task": task, "language": "en", "dataset": "MDVR-KCL"})
    with (output / "manifest.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["path", "subject", "label", "task", "language", "dataset"])
        writer.writeheader()
        writer.writerows(rows)
    report = {"dataset": "MDVR-KCL", "source": SOURCE, "doi": "10.5281/zenodo.2867216",
              "license": "CC BY 4.0", "archive_md5": hasher.hexdigest(), "recordings": len(rows),
              "subjects": len({r["subject"] for r in rows}),
              "task_counts": {task: sum(r["task"]==task for r in rows) for task in {r["task"] for r in rows}},
              "citation": "Jaeger H, Trivedi D, Stadtschnitzer M. MDVR-KCL. Zenodo, 2019."}
    (output / "provenance.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, default=Path("data/mdvr-kcl/26_29_09_2017_KCL.zip"))
    parser.add_argument("--output", type=Path, default=Path("data/mdvr-kcl"))
    args = parser.parse_args()
    prepare(args.archive, args.output)
