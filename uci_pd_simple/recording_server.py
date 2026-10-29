"""Local-only voice collection service. No extra Python dependencies required."""
from __future__ import annotations

import argparse
from array import array
from datetime import datetime, timezone
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import math
from pathlib import Path
import re
import sys
import threading
from urllib.parse import parse_qs, unquote, urlsplit
import uuid
import wave

ROOT = Path(__file__).resolve().parent
MAX_BYTES = 24 * 1024 * 1024
TASKS = {"vowel", "ddk", "reading"}
ID_PATTERN = re.compile(r"[a-f0-9]{32}\Z")


def inspect_wav(payload: bytes) -> dict:
    """Validate PCM WAV and compute technical quality, not disease features."""
    if len(payload) > MAX_BYTES:
        raise ValueError("音频不能超过 24 MB")
    try:
        with wave.open(io.BytesIO(payload), "rb") as audio:
            channels, width, rate, frames = (audio.getnchannels(), audio.getsampwidth(),
                                             audio.getframerate(), audio.getnframes())
            if channels != 1 or width != 2 or audio.getcomptype() != "NONE":
                raise ValueError("需要单声道、16 位 PCM WAV")
            if not 8000 <= rate <= 96000:
                raise ValueError("采样率须在 8–96 kHz 之间")
            duration = frames / rate
            if not .25 <= duration <= 120:
                raise ValueError("音频时长须在 0.25–120 秒之间")
            raw = audio.readframes(frames)
            if len(raw) != frames * 2:
                raise ValueError("WAV 数据不完整")
    except (wave.Error, EOFError) as exc:
        raise ValueError("不是有效的 PCM WAV 文件") from exc
    values = array("h")
    values.frombytes(raw)
    if sys.byteorder != "little":
        values.byteswap()
    peak = max(abs(v) for v in values) / 32768
    rms = math.sqrt(sum(v * v for v in values) / len(values)) / 32768
    clipping = sum(abs(v) >= 32700 for v in values) / len(values)
    warnings = []
    if duration < 3:
        warnings.append("音频短于 3 秒，建议重新采集")
    if rms < .01:
        warnings.append("音量偏低或接近静音")
    if clipping > .005:
        warnings.append("存在削波，请降低麦克风输入音量")
    return {"sample_rate": rate, "channels": channels, "bits": 16,
            "frames": frames, "duration_seconds": round(duration, 3),
            "rms_dbfs": round(20 * math.log10(max(rms, 1e-12)), 2),
            "peak": round(peak, 5), "clipping_ratio": round(clipping, 6),
            "warnings": warnings, "quality": "review" if warnings else "pass"}


class RecordingStore:
    def __init__(self, root: Path):
        self.root = Path(root)

    def save(self, payload: bytes, session: str, task: str, source: str,
             consent: str) -> dict:
        if not re.fullmatch(r"[A-Z0-9]{12}", session):
            raise ValueError("会话编号须为 12 位大写英数字")
        if task not in TASKS or source not in {"microphone", "file"}:
            raise ValueError("无效的任务或采集来源")
        if consent != "yes":
            raise ValueError("保存前须确认受试者同意")
        quality = inspect_wav(payload)
        record_id = uuid.uuid4().hex
        info = {"id": record_id, "session": session, "task": task, "source": source,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "consent_confirmed": True, "sha256": hashlib.sha256(payload).hexdigest(),
                "bytes": len(payload), **quality, "feature_status": "pending",
                "audio_url": f"/api/recordings/{record_id}/audio"}
        folder = self.root / record_id
        folder.mkdir(parents=True, exist_ok=False)
        try:
            (folder / "audio.wav").write_bytes(payload)
            (folder / "metadata.json.tmp").write_text(
                json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
            (folder / "metadata.json.tmp").replace(folder / "metadata.json")
        except OSError:
            # An unfinished folder is never returned by list(). Original audio is preserved.
            raise
        return info

    def list(self) -> list[dict]:
        records = []
        if self.root.exists():
            for path in self.root.glob("*/metadata.json"):
                if not ID_PATTERN.fullmatch(path.parent.name):
                    continue
                try:
                    records.append(json.loads(path.read_text(encoding="utf-8")))
                except (OSError, ValueError):
                    continue
        return sorted(records, key=lambda item: item["created_at"], reverse=True)

    def audio_path(self, record_id: str) -> Path:
        if not ID_PATTERN.fullmatch(record_id):
            raise ValueError("无效录音编号")
        path = self.root / record_id / "audio.wav"
        if not path.is_file() or not (path.parent / "metadata.json").is_file():
            raise FileNotFoundError("录音不存在")
        return path


class CollectionServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, storage: Path, model_dir: Path | None = None):
        self.store = RecordingStore(storage)
        self.model_dir = Path(model_dir) if model_dir else ROOT / "artifacts" / "audio_transformer_v1"
        self.predictor = None
        self.model_lock = threading.Lock()
        super().__init__(address, CollectionHandler)

    def model_status(self):
        from deep_learning.runtime import artifact_status
        return artifact_status(self.model_dir)

    def predict_audio(self, payload, task, language, quality):
        from deep_learning.runtime import AudioPredictor, ModelUnavailable
        with self.model_lock:
            if self.predictor is None:
                try:
                    self.predictor = AudioPredictor(self.model_dir)
                except ImportError as exc:
                    raise ModelUnavailable("请使用安装 requirements-dl.txt 的 .venv-dl 环境启动服务") from exc
        return self.predictor.predict(payload, task, language, quality)


class CollectionHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / "frontend"), **kwargs)

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Permissions-Policy", "microphone=(self), camera=()")
        super().end_headers()

    def json_response(self, status: int, data: dict):
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def local_request(self) -> bool:
        port = self.server.server_port
        hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
        host = self.headers.get("Host", "")
        origin = self.headers.get("Origin")
        return host in hosts and (origin is None or origin == f"http://{host}")

    def do_GET(self):
        if not self.local_request():
            return self.json_response(403, {"error": "仅允许本机同源访问"})
        path = urlsplit(self.path).path
        if path == "/api/health":
            return self.json_response(200, {"status": "ok", "mode": "local",
                                            "inference": self.server.model_status()["ready"]})
        if path == "/api/model":
            return self.json_response(200, self.server.model_status())
        if path == "/api/evaluation":
            from deep_learning.evaluation import build_evaluation
            try:
                return self.json_response(200, build_evaluation(self.server.model_dir))
            except (OSError, ValueError, KeyError, TypeError) as exc:
                return self.json_response(503, {"error": "评估数据不可用：" + str(exc)})
        if path == "/api/recordings":
            return self.json_response(200, {"recordings": self.server.store.list()})
        match = re.fullmatch(r"/api/recordings/([a-f0-9]{32})/audio", path)
        if match:
            try:
                data = self.server.store.audio_path(match[1]).read_bytes()
            except FileNotFoundError:
                return self.json_response(404, {"error": "录音不存在"})
            self.send_response(200)
            self.send_header("Content-Type", "audio/wav")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if path.startswith("/api/"):
            return self.json_response(404, {"error": "接口不存在"})
        public_root = (ROOT / "frontend").resolve()
        resolved = (public_root / unquote(path).lstrip("/")).resolve()
        if not resolved.is_relative_to(public_root) or any(
                part.startswith(".") for part in resolved.relative_to(public_root).parts):
            return self.json_response(403, {"error": "不可访问此路径"})
        super().do_GET()

    def list_directory(self, path):
        self.send_error(403, "Directory listing disabled")
        return None

    def do_POST(self):
        self.connection.settimeout(20)
        if not self.local_request():
            return self.reject_post(403, "仅允许本机同源访问")
        parsed = urlsplit(self.path)
        if parsed.path not in {"/api/recordings", "/api/predict"}:
            return self.reject_post(404, "接口不存在")
        if self.headers.get("Content-Type", "").split(";")[0] != "audio/wav":
            return self.reject_post(415, "需要 audio/wav")
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= MAX_BYTES:
                return self.json_response(413, {"error": "音频大小须在 1 字节至 24 MB 之间"})
            data = self.rfile.read(length)
            if len(data) != length:
                raise ValueError("上传不完整")
            params = parse_qs(parsed.query)
            get = lambda key: params.get(key, [""])[0]
            if parsed.path == "/api/predict":
                from deep_learning.runtime import ModelUnavailable, InputRejected
                if get("consent") != "yes":
                    raise ValueError("推理前须确认受试者同意")
                if get("task") not in TASKS or get("language") not in {"en", "zh"}:
                    raise ValueError("无效的任务或语言")
                quality = inspect_wav(data)
                try:
                    prediction = self.server.predict_audio(data, get("task"), get("language"), quality)
                except ModelUnavailable as exc:
                    return self.json_response(503, {"error": str(exc), "code": "model_unavailable"})
                except InputRejected as exc:
                    return self.json_response(422, {"error": str(exc), "code": "input_rejected"})
                return self.json_response(200, {"prediction": prediction})
            info = self.server.store.save(data, get("session"), get("task"),
                                          get("source"), get("consent"))
            self.json_response(201, {"recording": info})
        except (ValueError, wave.Error, EOFError) as exc:
            self.json_response(400, {"error": str(exc)})
        except (TimeoutError, OSError):
            self.json_response(500, {"error": "保存失败，请检查存储目录或重试"})

    def reject_post(self, code: int, message: str):
        # Drain a bounded declared body before closing. Otherwise Windows may reset
        # the TCP connection and discard the JSON error while a client is sending.
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if 0 < length <= MAX_BYTES:
                self.rfile.read(length)
        except (ValueError, TimeoutError, OSError):
            pass
        self.json_response(code, {"error": message})


def main():
    parser = argparse.ArgumentParser(description="NEURODRIVE 本机录音服务")
    parser.add_argument("--port", type=int, default=8767)
    parser.add_argument("--storage", type=Path, default=ROOT / "recordings")
    parser.add_argument("--model-dir", type=Path, default=ROOT / "artifacts" / "audio_transformer_v1")
    args = parser.parse_args()
    with CollectionServer(("127.0.0.1", args.port), args.storage, args.model_dir) as server:
        print(f"NEURODRIVE: http://127.0.0.1:{server.server_port}", flush=True)
        print(f"本机录音目录: {args.storage.resolve()}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
