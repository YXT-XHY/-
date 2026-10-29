"""Classify an audio window with the same trained runtime used by the web API."""
import argparse
import io
import json
from pathlib import Path

import numpy as np
import soundfile as sf

from recording_server import inspect_wav
from .audio import load_audio
from .runtime import AudioPredictor


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio", required=True, type=Path)
    parser.add_argument("--model-dir", type=Path, default=Path("artifacts/audio_transformer_v1"))
    parser.add_argument("--task", choices=["reading", "vowel", "ddk"], default="reading")
    parser.add_argument("--language", choices=["en", "zh"], default="en")
    parser.add_argument("--start", type=float, default=0)
    parser.add_argument("--seconds", type=float, default=30)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.start < 0 or not 3 <= args.seconds <= 120:
        parser.error("start must be >=0; seconds must be in [3,120]")
    samples = load_audio(args.audio, 16000)
    samples = samples[round(args.start*16000):round((args.start+args.seconds)*16000)]
    encoded = io.BytesIO()
    sf.write(encoded, np.clip(samples, -1, 1), 16000, format="WAV", subtype="PCM_16")
    payload = encoded.getvalue()
    result = AudioPredictor(args.model_dir).predict(payload, args.task, args.language, inspect_wav(payload))
    result["input_file"] = args.audio.name
    result["window_start_seconds"] = args.start
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
