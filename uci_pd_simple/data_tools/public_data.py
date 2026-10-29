"""Discover Zenodo public records and download explicitly selected open files.

Uses public read APIs only. Never logs in, extracts archives, or infers PD labels.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "public_discovery"
AGENT = "NeurodrivePublicResearch/1.0"
OPEN_LICENSES = {"cc-by-4.0", "cc0-1.0"}
QUERY = 'title:Parkinson AND (Mandarin OR Chinese OR Cantonese) AND (speech OR voice OR audio)'


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def check_url(url):
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or parsed.hostname != "zenodo.org" or parsed.port not in (None, 443)
            or parsed.username or parsed.password or parsed.fragment):
        raise ValueError("Only public HTTPS URLs on zenodo.org are supported")
    return url


class PublicRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        check_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class Client:
    def __init__(self):
        self.opener = build_opener(PublicRedirect())
        self.last_request = 0.0

    def open(self, url, headers=None):
        check_url(url)
        for attempt in range(3):
            # Single worker, at most one new request per second.
            time.sleep(max(0, 1 - (time.monotonic() - self.last_request)))
            self.last_request = time.monotonic()
            request = Request(url, headers={"User-Agent": AGENT, "Accept-Encoding": "identity", **(headers or {})})
            try:
                return self.opener.open(request, timeout=30)
            except HTTPError as exc:
                if exc.code not in (500, 502, 503, 504) or attempt == 2:
                    raise
            except (URLError, TimeoutError, ConnectionError):
                if attempt == 2:
                    raise
            time.sleep(2 ** (attempt + 1))

    def json(self, url, max_bytes=32 * 1024 * 1024):
        with self.open(url, {"Accept": "application/json"}) as response:
            content = response.read(max_bytes + 1)
        if len(content) > max_bytes:
            raise ValueError(f"Metadata exceeds {max_bytes} byte limit; narrow --query or reduce --limit")
        return json.loads(content)


def record_id(value):
    if not re.fullmatch(r"[1-9][0-9]{0,14}", str(value)):
        raise ValueError("Expected a numeric Zenodo record ID")
    return str(value)


def summarize(record):
    metadata = record.get("metadata", {})
    access = metadata.get("access_right")
    # Fail closed when repository metadata lacks a recognized access/license field.
    license_value = metadata.get("license", {})
    license_id = license_value.get("id", "") if isinstance(license_value, dict) else ""
    files = [{"name": f.get("key"), "size": f.get("size"), "checksum": f.get("checksum")}
             for f in record.get("files", [])]
    return {"id": record.get("id"), "title": metadata.get("title"),
            "resource_type": metadata.get("resource_type", {}),
            "description_excerpt": html.unescape(re.sub(r"<[^>]+>", " ", str(metadata.get("description", ""))))[:4000],
            "url": f"https://zenodo.org/records/{record_id(record['id'])}",
            "doi": metadata.get("doi"), "access": access, "license": license_id,
            "download_permitted_by_tool": access == "open" and license_id in OPEN_LICENSES,
            "eligible_for_training": False,
            "review_required": ["actual language", "clinical diagnosis labels", "subject IDs",
                                "consent and intended-use terms", "task and matched controls"],
            "files": files}


def is_candidate(record):
    metadata = record.get("metadata", {})
    text = html.unescape(re.sub(r"<[^>]+>", " ", " ".join(str(metadata.get(k, ""))
                         for k in ("title", "description", "keywords")))).casefold()
    keyword_match = all(re.search(pattern, text) for pattern in (
        r"parkinson|帕金森", r"mandarin|chinese|cantonese|中文|汉语|普通话|粤语",
        r"speech|voice|audio|语音"))
    kind = metadata.get("resource_type", {}).get("type")
    # An ASR model's long bibliography mentioning PD is not a PD data source.
    title_mentions_pd = re.search(r"parkinson|帕金森", str(metadata.get("title", "")).casefold())
    return bool(keyword_match and (kind in {"dataset", "audio", "video"} or title_mentions_pd))


def safe_name(name):
    if (not isinstance(name, str) or not name or len(name) > 180
            or re.search(r'[<>:"/\\|?*\x00-\x1f]', name) or name.endswith((".", " "))
            or name.split(".")[0].upper() in {"CON", "PRN", "AUX", "NUL",
                *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
            or Path(name).suffix.lower() not in {".wav", ".flac", ".mp3", ".ogg", ".m4a",
                                               ".zip", ".tar", ".gz", ".csv", ".tsv", ".pdf", ".txt", ".docx"}):
        raise ValueError("Unsafe or unsupported filename")
    return name


def checksum_spec(value):
    algorithm, separator, expected = str(value).partition(":")
    length = {"md5": 32, "sha256": 64}.get(algorithm)
    if not separator or not length or not re.fullmatch(rf"[0-9a-fA-F]{{{length}}}", expected):
        raise ValueError("Repository must provide an MD5 or SHA-256 checksum")
    return algorithm, expected.lower()


def file_hash(path, algorithm="sha256"):
    digest = hashlib.new(algorithm)
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def download(record, filename, output, client, max_bytes):
    summary = summarize(record)
    if not summary["download_permitted_by_tool"]:
        raise ValueError("Download refused: record must be open with CC BY 4.0 or CC0 1.0 license")
    safe_name(filename)
    item = next((f for f in record.get("files", []) if f.get("key") == filename), None)
    if not item:
        raise ValueError("Filename not present in the current official record")
    size = item.get("size")
    if type(size) is not int or size <= 0 or size > max_bytes:
        raise ValueError("Invalid file size or file exceeds --max-mb")
    algorithm, expected = checksum_spec(item.get("checksum"))
    url = check_url(item.get("links", {}).get("self", ""))
    folder = Path(output) / record_id(record["id"])
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / filename
    partial = folder / (filename + ".part")
    state_file = folder / (filename + ".download.json")
    identity = {"url": url, "size": size, "checksum": item["checksum"]}
    if target.exists():
        if target.stat().st_size != size or file_hash(target, algorithm) != expected:
            raise ValueError("Existing destination differs from repository; refusing overwrite")
    else:
        if partial.exists():
            if not state_file.exists() or json.loads(state_file.read_text(encoding="utf-8")) != identity:
                raise ValueError("Partial file belongs to different metadata; choose another output directory")
        save_json(state_file, identity)
        offset = partial.stat().st_size if partial.exists() else 0
        if offset > size:
            raise ValueError("Partial file exceeds expected size")
        if offset < size:
            headers = {"Range": f"bytes={offset}-"} if offset else {}
            with client.open(url, headers) as response:
                if response.status == 206:
                    expected_range = f"bytes {offset}-{size-1}/{size}"
                    if response.headers.get("Content-Range") != expected_range:
                        raise ValueError("Unexpected Content-Range; refusing to append")
                    mode = "ab" if offset else "wb"
                elif response.status == 200:
                    # Range ignored: restart rather than concatenate the full response.
                    offset, mode = 0, "wb"
                else:
                    raise ValueError(f"Unexpected download HTTP status: {response.status}")
                with partial.open(mode) as handle:
                    received = offset
                    while chunk := response.read(65536):
                        received += len(chunk)
                        if received > size:
                            raise ValueError("Response exceeds repository file size")
                        handle.write(chunk)
        if partial.stat().st_size != size:
            raise ValueError("Incomplete download; rerun the same command to resume")
        if file_hash(partial, algorithm) != expected:
            partial.unlink()
            raise ValueError("Checksum mismatch; rejected partial file removed, rerun to restart")
        partial.replace(target)
    receipt = {"downloaded_at_utc": timestamp(), "record": summary, "file": identity,
               "local_path": str(target.resolve()), "sha256": file_hash(target),
               "repository_checksum_verified": True, "eligible_for_training": False,
               "attribution": record.get("metadata", {}).get("creators", []),
               "notice": "Downloaded research material; clinical labels and language still require review."}
    save_json(folder / (filename + ".receipt.json"), receipt)
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("catalog", help="Show curated Chinese PD candidate access routes; offline")
    search = commands.add_parser("search", help="Search public Zenodo metadata; does not download audio")
    search.add_argument("--query", default=QUERY)
    search.add_argument("--limit", type=int, choices=range(1, 51), default=20)
    search.add_argument("--pages", type=int, choices=range(1, 11), default=3)
    inspect = commands.add_parser("inspect", help="Fetch an official record and its license/file metadata")
    inspect.add_argument("record", type=record_id)
    fetch = commands.add_parser("download", help="Download one selected file from an eligible open record")
    fetch.add_argument("record", type=record_id)
    fetch.add_argument("--file", required=True, action="append", help="Exact filename; repeat for a batch")
    fetch.add_argument("--max-mb", type=int, default=500)
    args = parser.parse_args(argv)
    try:
        if args.command == "catalog":
            result = json.loads((Path(__file__).parent / "sources.json").read_text(encoding="utf-8"))
        else:
            client = Client()
            if args.command == "search":
                candidates, seen, requests = [], set(), []
                for page in range(1, args.pages + 1):
                    url = "https://zenodo.org/api/records?" + urlencode({"q": args.query, "size": args.limit, "page": page})
                    response = client.json(url)
                    requests.append(url)
                    hits = response.get("hits", {}).get("hits", [])
                    for item in hits:
                        if item["id"] in seen:
                            continue
                        seen.add(item["id"])
                        if is_candidate(item):
                            candidates.append(summarize(item))
                    if len(hits) < args.limit:
                        break
                result = {"searched_at_utc": timestamp(), "query": args.query, "api_url": url,
                          "scope": "Zenodo public metadata only; not an exhaustive web search",
                          "requests": requests, "records_examined": len(seen),
                          "filter": "PD + Chinese + speech keywords, plus dataset/audio/video type or PD title; not clinical verification",
                          "total": response.get("hits", {}).get("total"),
                          "candidates": candidates}
                save_json(args.output / "search_results.json", result)
            else:
                record = client.json(f"https://zenodo.org/api/records/{args.record}")
                if record_id(record["id"]) != args.record:
                    raise ValueError("Repository returned a different record ID")
                save_json(args.output / args.record / "record.json", record)
                result = summarize(record) if args.command == "inspect" else {"downloads": [download(
                    record, name, args.output, client, args.max_mb * 1024 * 1024)
                    for name in dict.fromkeys(args.file)]}
        display = result
        if args.command == "search":
            display = {**result, "saved_to": str((args.output / "search_results.json").resolve()),
                       "candidates": [{k: r[k] for k in ("id", "title", "url", "access", "license",
                                                        "download_permitted_by_tool")} for r in result["candidates"]]}
        print(json.dumps(display, ensure_ascii=False, indent=2))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        if isinstance(exc, HTTPError) and exc.code in (401, 403):
            message = f"HTTP {exc.code}: access denied; no login or access-control bypass attempted"
        elif isinstance(exc, HTTPError) and exc.code == 429:
            message = "HTTP 429: rate limited; wait before retrying"
        else:
            message = str(exc)
        parser.exit(1, f"Error: {message}\n")
