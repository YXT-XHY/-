"""Load only trained, integrity-checked research artifacts. Never random weights."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import threading


class ModelUnavailable(RuntimeError):
    pass


class InputRejected(ValueError):
    pass


def artifact_status(directory: Path) -> dict:
    card_file = Path(directory) / "model_card.json"
    if not card_file.exists():
        progress_file = Path(directory) / "progress.json"
        progress = None
        if progress_file.exists():
            try:
                raw = json.loads(progress_file.read_text(encoding="utf-8"))
                progress = {key: raw.get(key) for key in ("status", "fold", "epoch", "elapsed_seconds")}
            except (OSError, ValueError):
                pass
        return {"ready": False, "reason": "模型尚未完成真实语音训练与验证", "progress": progress}
    try:
        card = json.loads(card_file.read_text(encoding="utf-8"))
        if card.get("format") != "neurodrive-audio-transformer-v1" or not card.get("trained") or card.get("synthetic") is not False:
            raise ModelUnavailable("缺少真实音频训练记录，拒绝使用随机或合成模型")
        if not card.get("deployment_allowed"):
            raise ModelUnavailable("当前模型未达到预先设定的内部验证门槛，不开放分类输出")
        for fold in card["folds"]:
            name = fold["file"]
            if Path(name).name != name or not name.endswith(".safetensors"):
                raise ModelUnavailable("模型文件名无效")
            path = directory / name
            if hashlib.sha256(path.read_bytes()).hexdigest() != fold["sha256"]:
                raise ModelUnavailable("模型权重完整性校验失败")
        if not card["folds"]:
            raise ModelUnavailable("无可用权重")
        return {"ready": True, "architecture": card["architecture"], "purpose": card["purpose"],
                "subjects": card["subjects"], "dataset": card["dataset"],
                "languages": card["languages"], "supported_tasks": card["supported_tasks"],
                "evaluation": card["evaluation"], "limitations": card["limitations"],
                "model_id": hashlib.sha256(card_file.read_bytes()).hexdigest()[:16]}
    except (OSError, KeyError, ValueError, ModelUnavailable) as exc:
        return {"ready": False, "reason": str(exc)}


class AudioPredictor:
    def __init__(self, directory: Path):
        import torch
        from safetensors.torch import load_file
        from .audio import AudioConfig
        from .model import ModelConfig, SpeechTransformer
        self.status = artifact_status(directory)
        if not self.status["ready"]:
            raise ModelUnavailable(self.status["reason"])
        self.card = json.loads((directory / "model_card.json").read_text(encoding="utf-8"))
        self.audio_config = AudioConfig(**self.card["audio_config"])
        self.models = []
        # CPU inference avoids retaining GPU memory in the local web server.
        torch.set_num_threads(min(4, torch.get_num_threads()))
        for fold in self.card["folds"]:
            model = SpeechTransformer(ModelConfig(**self.card["model_config"]))
            model.load_state_dict(load_file(str(directory / fold["file"])), strict=True)
            model.eval()
            self.models.append(model)
        self.lock = threading.Lock()

    def predict(self, payload: bytes, task: str, language: str, quality: dict) -> dict:
        import numpy as np
        import torch
        from .audio import load_audio, log_mel, segment_audio
        if task not in self.card["supported_tasks"]:
            raise InputRejected("当前模型未验证所选语音任务，请使用模型支持的任务重新采集")
        if quality["duration_seconds"] < 3 or quality["rms_dbfs"] < -40 or quality["clipping_ratio"] > .005:
            raise InputRejected("音频时长、音量或削波不满足推理要求，请调整后重新录制")
        samples = load_audio(payload, self.audio_config.sample_rate)
        frame_size = self.audio_config.sample_rate // 20
        frame_count = len(samples) // frame_size
        energies = np.sqrt(np.mean(samples[:frame_count*frame_size].reshape(frame_count, frame_size)**2, axis=1))
        if task == "reading" and float(energies.std() / max(float(energies.mean()), 1e-8)) < .015:
            raise InputRejected("信号变化过小，请提供自然朗读语音，而不是持续音或测试音")
        chunks = segment_audio(samples, self.audio_config)
        specs = torch.stack([log_mel(chunk, self.audio_config) for _, chunk in chunks])
        model_scores, attention = [], []
        with self.lock, torch.inference_mode():
            for model in self.models:
                logits, weights = model(specs, return_attention=True)
                model_scores.append(float(torch.sigmoid(logits.mean())))
                attention.append(weights.mean(dim=0).cpu().numpy())
        score, spread = float(np.mean(model_scores)), float(np.std(model_scores))
        outside_language = language not in self.card["languages"]
        low, high = self.card["uncertain_interval"]
        uncertain = low <= score <= high or spread > .20 or outside_language
        prediction = "uncertain" if uncertain else "pd_like" if score >= high else "hc_like"
        text = {"uncertain": "结果不确定", "pd_like": "更接近帕金森组语音", "hc_like": "更接近健康对照组语音"}[prediction]
        warnings = ["研究模型分类，不构成是否患病的临床诊断；模型分数不是患病概率。"]
        if outside_language:
            warnings.append("该语言未在训练数据中验证，分类结论已拒绝输出；可查看研究分数。")
        if spread > .20:
            warnings.append("模型间分歧较大，建议重新采集并复核。")
        weights = np.mean(attention, axis=0)
        # Temporal weights are only an attention visualization, not causal pathology evidence.
        bins = np.array_split(weights, min(24, len(weights)))
        return {"status": "ok", "task": task, "language": language, "prediction": prediction, "label": text,
                "model_score": round(score, 6), "model_spread": round(spread, 6),
                "model_scores": [round(p, 6) for p in model_scores],
                "uncertain": uncertain, "out_of_domain": outside_language,
                "model_id": self.status["model_id"], "architecture": self.card["architecture"],
                "segments": len(chunks), "segment_seconds": self.audio_config.seconds,
                "sample_rate": self.audio_config.sample_rate, "quality": quality,
                "attention": [round(float(part.mean()), 6) for part in bins],
                "attention_notice": "时间关注权重，不是病理定位。", "warnings": warnings,
                "evaluation": self.card["evaluation"]}
