"""Download only ReadText entries from the official ZIP using HTTP byte ranges.

Every file is checked against the official central-directory CRC and uncompressed
size. This is explicitly NOT a claim to have verified the complete ZIP MD5.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import struct
import time
from urllib.request import Request, urlopen
import zipfile
import zlib

URL = "https://zenodo.org/records/2867216/files/26_29_09_2017_KCL.zip?download=1"
TOTAL_BYTES = 606144431
TAIL_OFFSET = TOTAL_BYTES-65536


def read_range(start, end):
    request = Request(URL, headers={"Range": f"bytes={start}-{end}", "User-Agent": "NEURODRIVE-Research/1.0"})
    response = urlopen(request, timeout=45)
    expected = f"bytes {start}-{end}/{TOTAL_BYTES}"
    if response.status != 206 or response.headers.get("Content-Range") != expected:
        response.close()
        raise ValueError("Server did not honor the exact requested byte range")
    return response


def fetch_one(item, output):
    name = Path(item.filename).name
    match = re.fullmatch(r"(ID\d+)_(hc|pd)_[^/]+\.wav", name, re.I)
    if not match:
        raise ValueError(f"Unrecognized speaker filename {name}")
    target = output / "raw_reading" / name
    crc = lambda data: zlib.crc32(data) & 0xffffffff
    if target.exists():
        raw = target.read_bytes()
        if len(raw) == item.file_size and crc(raw) == item.CRC:
            return make_row(target, match, raw, item)
    start = item.header_offset + TAIL_OFFSET
    # Include enough local header slack; the compressed payload is sliced exactly below.
    size = 30 + len(item.filename.encode("utf-8")) + 1024 + item.compress_size
    partial = output / "ranges" / (name + ".part")
    partial.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(8):
        current = partial.stat().st_size if partial.exists() else 0
        if current >= size:
            break
        try:
            with read_range(start+current, start+size-1) as response, partial.open("ab") as dest:
                while chunk := response.read(65536):
                    dest.write(chunk)
            if partial.stat().st_size != size:
                raise OSError("Truncated byte range")
            break
        except Exception as exc:
            print(json.dumps({"retry": name, "attempt": attempt+1, "error": str(exc)}), flush=True)
            if attempt == 7:
                raise
            time.sleep(min(5*(attempt+1), 30))
    packed = partial.read_bytes()
    if packed[:4] != b"PK\x03\x04":
        raise ValueError(f"Wrong local ZIP header: {name}")
    name_len, extra_len = struct.unpack_from("<HH", packed, 26)
    offset = 30 + name_len + extra_len
    compressed = packed[offset:offset+item.compress_size]
    raw = zlib.decompress(compressed, -15) if item.compress_type == zipfile.ZIP_DEFLATED else compressed
    if len(raw) != item.file_size or crc(raw) != item.CRC:
        raise ValueError(f"ZIP CRC/size mismatch: {name}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    print(json.dumps({"downloaded": name, "bytes": len(raw), "crc_verified": True}), flush=True)
    return make_row(target, match, raw, item)


def make_row(target, match, raw, item):
    return {"path": str(target.resolve()), "subject": "MDVR_"+match[1].upper(),
            "label": 1 if match[2].lower()=="pd" else 0, "task": "reading",
            "language": "en", "dataset": "MDVR-KCL", "sha256": hashlib.sha256(raw).hexdigest(),
            "zip_crc32": item.CRC, "archive_entry": item.filename}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("data/mdvr-kcl"))
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    tail = args.output / "zip-tail.bin"
    if not tail.exists():
        with read_range(TAIL_OFFSET, TOTAL_BYTES-1) as response:
            tail.write_bytes(response.read())
    with zipfile.ZipFile(io.BytesIO(tail.read_bytes())) as zipped:
        items = [i for i in zipped.infolist() if "/ReadText/" in i.filename and i.filename.endswith(".wav")]
    if len(items) != 37:
        raise ValueError("Unexpected official archive contents")
    rows = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(fetch_one, item, args.output) for item in items]
        for future in as_completed(futures):
            rows.append(future.result())
    rows.sort(key=lambda row: row["subject"])
    with (args.output / "manifest.csv").open("w", encoding="utf-8", newline="") as handle:
        fields = ["path", "subject", "label", "task", "language", "dataset"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows({key: row[key] for key in fields} for row in rows)
    provenance = {"dataset": "MDVR-KCL", "source": "https://zenodo.org/records/2867216",
                  "doi": "10.5281/zenodo.2867216", "license": "CC BY 4.0",
                  "method": "official ZIP HTTP ranges, per-entry CRC32 and uncompressed size checked",
                  "full_archive_md5_verified": False, "official_archive_md5": "98c51bdd2b092b93f8bb038dea4505fa",
                  "subjects": 37, "recordings": len(rows), "pd_subjects": sum(r["label"] for r in rows),
                  "files": [{k:v for k,v in row.items() if k != "path"} for row in rows],
                  "citation": "Jaeger H, Trivedi D, Stadtschnitzer M. MDVR-KCL. Zenodo, 2019."}
    (args.output / "provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    print(json.dumps({"complete": True, "subjects": 37, "recordings": len(rows)}), flush=True)


if __name__ == "__main__":
    main()
