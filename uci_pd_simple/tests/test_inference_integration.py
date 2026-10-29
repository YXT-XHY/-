"""Real-artifact integration checks, not claims of independent clinical accuracy."""
import http.client
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
import wave

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "artifacts/audio_transformer_v1"
FIXTURE = ROOT / "tests/fixtures/public-mdvr-pd.wav"
AVAILABLE = (all(importlib.util.find_spec(name) for name in ("torch", "numpy", "scipy", "soundfile", "safetensors"))
             and (MODELS / "model_card.json").exists() and FIXTURE.exists())


@unittest.skipUnless(AVAILABLE, "Requires .venv-dl, trained artifacts and public audio QA fixture")
class TestRealInference(unittest.TestCase):
    def test_evaluation_endpoint_uses_subject_oof(self):
        status, data = self.request("/api/evaluation")
        self.assertEqual(status, 200)
        self.assertEqual(data["source"], "saved_subject_oof")
        self.assertEqual(data["metrics"]["fn"], 6)

    @classmethod
    def setUpClass(cls):
        from recording_server import CollectionServer
        cls.temp = tempfile.TemporaryDirectory()
        cls.server = CollectionServer(("127.0.0.1", 0), Path(cls.temp.name), MODELS)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.payload = FIXTURE.read_bytes()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(3)
        cls.temp.cleanup()

    def request(self, path, payload=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=30)
        try:
            connection.request("POST" if payload is not None else "GET", path, payload,
                               {"Content-Type": "audio/wav"} if payload is not None else {})
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally:
            connection.close()

    def test_real_weights_api_equals_direct_runtime(self):
        from recording_server import inspect_wav
        code, data = self.request("/api/predict?task=reading&language=en&consent=yes", self.payload)
        self.assertEqual(code, 200)
        result = data["prediction"]
        expected = self.server.predictor.predict(self.payload, "reading", "en", inspect_wav(self.payload))
        self.assertAlmostEqual(result["model_score"], expected["model_score"], places=6)
        self.assertEqual(len(result["model_scores"]), 5)
        self.assertIn(result["prediction"], {"pd_like", "hc_like", "uncertain"})
        self.assertEqual(result["sample_rate"], 16000)
        self.assertEqual(result["segments"], 4)
        self.assertTrue(result["warnings"])

    def test_out_of_domain_language_abstains(self):
        code, data = self.request("/api/predict?task=reading&language=zh&consent=yes", self.payload)
        self.assertEqual(code, 200)
        self.assertEqual(data["prediction"]["prediction"], "uncertain")
        self.assertTrue(data["prediction"]["out_of_domain"])

    def test_unsupported_task_refused(self):
        code, data = self.request("/api/predict?task=vowel&language=en&consent=yes", self.payload)
        self.assertEqual(code, 422)
        self.assertNotIn("prediction", data)

    def test_silent_audio_refused(self):
        encoded = io.BytesIO()
        with wave.open(encoded, "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(16000)
            audio.writeframes(b"\0" * 16000 * 2 * 4)
        code, data = self.request("/api/predict?task=reading&language=en&consent=yes", encoded.getvalue())
        self.assertEqual(code, 422)
        self.assertNotIn("prediction", data)

    def test_model_status_exposes_real_evaluation(self):
        code, data = self.request("/api/model")
        self.assertEqual(code, 200)
        self.assertTrue(data["ready"])
        self.assertEqual(data["evaluation"]["metrics"]["subjects"], 37)
        self.assertEqual(data["supported_tasks"], ["reading"])

    def test_no_inference_without_consent(self):
        code, data = self.request("/api/predict?task=reading&language=en&consent=no", self.payload)
        self.assertEqual(code, 400)
        self.assertNotIn("prediction", data)

    def test_constant_test_tone_is_not_treated_as_reading(self):
        from test_recording_server import make_wav
        code, data = self.request("/api/predict?task=reading&language=en&consent=yes", make_wav())
        self.assertEqual(code, 422)
        self.assertNotIn("prediction", data)
