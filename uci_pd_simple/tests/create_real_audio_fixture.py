"""Public dataset excerpts for end-to-end QA; not external validation samples."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import soundfile as sf
from deep_learning.audio import load_audio

if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    for label, name in [("pd", "ID24_pd_2_0_0.wav"), ("hc", "ID01_hc_0_0_0.wav")]:
        samples = load_audio(root / "data/mdvr-kcl/raw_reading" / name)
        output = root / "tests/fixtures" / f"public-mdvr-{label}.wav"
        sf.write(output, samples[30*16000:50*16000], 16000, subtype="PCM_16")
        print(output)
