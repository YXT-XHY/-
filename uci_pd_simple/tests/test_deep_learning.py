"""Architecture and refusal tests. No synthetic model is published."""
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
import wave

DL_AVAILABLE = all(importlib.util.find_spec(name) for name in ("torch", "numpy", "scipy", "soundfile", "sklearn", "safetensors"))


class TestArtifactRefusal(unittest.TestCase):
    def test_missing_weights_no_random_fallback(self):
        from deep_learning.runtime import artifact_status
        with tempfile.TemporaryDirectory() as folder:
            self.assertFalse(artifact_status(Path(folder))["ready"])

    def test_synthetic_or_unvalidated_model_refused(self):
        from deep_learning.runtime import artifact_status
        with tempfile.TemporaryDirectory() as folder:
            card = Path(folder) / "model_card.json"
            card.write_text(json.dumps({"format": "neurodrive-audio-transformer-v1", "trained": True,
                                        "synthetic": True, "deployment_allowed": True}), encoding="utf-8")
            self.assertFalse(artifact_status(Path(folder))["ready"])
            card.write_text(json.dumps({"format": "neurodrive-audio-transformer-v1", "trained": True,
                                        "synthetic": False, "deployment_allowed": False}), encoding="utf-8")
            self.assertFalse(artifact_status(Path(folder))["ready"])


@unittest.skipUnless(DL_AVAILABLE, "Run with .venv-dl after installing requirements-dl.txt")
class TestAudioAndTransformer(unittest.TestCase):
    def test_audio_resampling_and_silent_rejection(self):
        import numpy as np
        from deep_learning.audio import AudioConfig, load_audio, log_mel, segment_audio
        raw = io.BytesIO()
        with wave.open(raw, "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(48000)
            audio.writeframes(np.zeros(48000*3, dtype="<i2").tobytes())
        samples = load_audio(raw.getvalue())
        self.assertEqual(len(samples), 48000)
        with self.assertRaisesRegex(ValueError, "静音"):
            segment_audio(samples, AudioConfig())
        mel = log_mel(samples, AudioConfig())
        self.assertEqual(mel.shape[0], 64)
        self.assertTrue(np.isfinite(mel.numpy()).all())

    def test_segment_limit_covers_long_audio(self):
        import numpy as np
        from deep_learning.audio import AudioConfig, segment_audio
        config = AudioConfig()
        samples = np.ones(16000*120, np.float32)*.1
        chunks = segment_audio(samples, config, max_segments=4)
        self.assertEqual(len(chunks), 4)
        self.assertEqual(chunks[0][0], 0)
        self.assertEqual(chunks[-1][0], 114)

    def test_transformer_backprop_and_attention(self):
        import torch
        from deep_learning.model import ModelConfig, SpeechTransformer
        torch.set_num_threads(2)
        model = SpeechTransformer(ModelConfig(dropout=0))
        x = torch.randn(2, 64, 201)
        output, attention = model(x, return_attention=True)
        self.assertEqual(output.shape, (2,))
        torch.testing.assert_close(attention.sum(dim=1), torch.ones(2))
        output.square().mean().backward()
        self.assertGreater(float(model.convolution[0].weight.grad.abs().sum()), 0)
        self.assertGreater(float(model.transformer.layers[0].self_attn.in_proj_weight.grad.abs().sum()), 0)

    def test_subject_aggregation_and_metric_unit(self):
        import numpy as np
        from deep_learning.train import aggregate_subjects, metrics
        rows = aggregate_subjects(np.array([0,0,1,1]), np.array([-2,-1,1,2]), np.array(["A","A","B","B"]))
        self.assertEqual(len(rows), 2)
        self.assertEqual(metrics(rows)["subjects"], 2)
        self.assertEqual(metrics(rows)["auc"], 1)


if __name__ == "__main__":
    unittest.main()
