"""Generate a synthetic 3-second tone for UI import QA, never participant data."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_recording_server import make_wav

if __name__ == "__main__":
    output = Path(__file__).parent / "fixtures" / "synthetic-tone.wav"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(make_wav())
    print(output.resolve())
