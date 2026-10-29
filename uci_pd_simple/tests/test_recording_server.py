"""Technical audio collection tests; synthetic tones are never training data."""
from array import array
import http.client
import io
import json
import math
from pathlib import Path
import sys
import tempfile
import threading
import unittest
import wave

from recording_server import CollectionServer, RecordingStore, inspect_wav


def make_wav(seconds=3, amplitude=.2, rate=16000):
    values = array("h", (round(amplitude * 32767 * math.sin(2 * math.pi * 180 * i / rate))
                         for i in range(round(seconds * rate))))
    if sys.byteorder != "little":
        values.byteswap()
    output = io.BytesIO()
    with wave.open(output, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(rate)
        audio.writeframes(values.tobytes())
    return output.getvalue()


class TestAudioValidation(unittest.TestCase):
    def test_valid_audio_metadata(self):
        info = inspect_wav(make_wav())
        self.assertEqual(info["duration_seconds"], 3)
        self.assertEqual(info["sample_rate"], 16000)
        self.assertEqual(info["quality"], "pass")
        self.assertEqual(info["clipping_ratio"], 0)

    def test_silence_and_short_duration_warn(self):
        info = inspect_wav(make_wav(.5, 0))
        self.assertEqual(len(info["warnings"]), 2)
        self.assertEqual(info["quality"], "review")

    def test_invalid_and_truncated_wav_rejected(self):
        for data in (b"not audio", make_wav()[:-20]):
            with self.assertRaises(ValueError):
                inspect_wav(data)

    def test_stereo_rejected(self):
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as audio:
            audio.setnchannels(2)
            audio.setsampwidth(2)
            audio.setframerate(16000)
            audio.writeframes(b"\0" * 64000)
        with self.assertRaisesRegex(ValueError, "单声道"):
            inspect_wav(buffer.getvalue())

    def test_clipping_warns(self):
        info = inspect_wav(make_wav(3, 1))
        self.assertTrue(any("削波" in warning for warning in info["warnings"]))


class TestStore(unittest.TestCase):
    def test_save_round_trip_and_reject_invalid_metadata(self):
        with tempfile.TemporaryDirectory() as folder:
            store = RecordingStore(Path(folder) / "recordings")
            data = make_wav()
            for session, task, consent in [("../escape", "vowel", "yes"),
                                           ("A1B2C3D4E5F6", "invalid", "yes"),
                                           ("A1B2C3D4E5F6", "vowel", "no")]:
                with self.assertRaises(ValueError):
                    store.save(data, session, task, "file", consent)
            self.assertEqual(store.list(), [])
            record = store.save(data, "A1B2C3D4E5F6", "vowel", "file", "yes")
            self.assertEqual(store.audio_path(record["id"]).read_bytes(), data)
            self.assertEqual(store.list()[0]["feature_status"], "pending")
            self.assertTrue(record["consent_confirmed"])
            with self.assertRaises(ValueError):
                store.audio_path("../../outside")


class TestAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.server = CollectionServer(("127.0.0.1", 0), Path(cls.temp.name), Path(cls.temp.name)/"missing-model")
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)
        cls.temp.cleanup()

    def request(self, method, path, body=None, headers=None):
        client = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        try:
            client.request(method, path, body, headers or {})
            response = client.getresponse()
            return response.status, response.getheader("Content-Type"), response.read()
        finally:
            client.close()

    def test_health_and_frontend(self):
        status, _, raw = self.request("GET", "/api/health")
        self.assertEqual(status, 200)
        self.assertFalse(json.loads(raw)["inference"])
        status, _, raw = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn(b"capture.js", raw)

    def test_save_list_and_replay(self):
        data = make_wav()
        status, _, raw = self.request("POST", "/api/recordings?session=A1B2C3D4E5F6"
                                     "&task=vowel&source=file&consent=yes", data,
                                     {"Content-Type": "audio/wav"})
        self.assertEqual(status, 201)
        record = json.loads(raw)["recording"]
        status, mime, replay = self.request("GET", record["audio_url"])
        self.assertEqual((status, mime, replay), (200, "audio/wav", data))
        status, _, raw = self.request("GET", "/api/recordings")
        self.assertIn(record["id"], [r["id"] for r in json.loads(raw)["recordings"]])

    def test_wrong_type_and_origin_rejected(self):
        status, _, _ = self.request("POST", "/api/recordings", b"{}",
                                     {"Content-Type": "application/json"})
        self.assertEqual(status, 415)
        status, _, _ = self.request("POST", "/api/recordings", make_wav(),
                                     {"Content-Type": "audio/wav", "Origin": "https://example.com"})
        self.assertEqual(status, 403)

    def test_no_consent_and_malformed_audio_rejected(self):
        status, _, _ = self.request("POST", "/api/recordings?session=A1B2C3D4E5F6"
                                     "&task=vowel&source=file&consent=no", make_wav(),
                                     {"Content-Type": "audio/wav"})
        self.assertEqual(status, 400)
        status, _, _ = self.request("POST", "/api/recordings?session=A1B2C3D4E5F6"
                                     "&task=vowel&source=file&consent=yes", b"not audio",
                                     {"Content-Type": "audio/wav"})
        self.assertEqual(status, 400)

    def test_bad_host_and_path_traversal(self):
        status, _, _ = self.request("GET", "/api/recordings", headers={"Host": "evil.example"})
        self.assertEqual(status, 403)

    def test_model_unavailable_does_not_fabricate_prediction(self):
        status, _, raw = self.request("GET", "/api/model")
        self.assertEqual(status, 200)
        self.assertFalse(json.loads(raw)["ready"])
        status, _, raw = self.request("POST", "/api/predict?task=reading&language=en&consent=yes",
                                     make_wav(), {"Content-Type": "audio/wav"})
        self.assertEqual(status, 503)
        self.assertNotIn("prediction", json.loads(raw))
        status, _, _ = self.request("GET", "/%2e%2e/recording_server.py")
        self.assertEqual(status, 403)


if __name__ == "__main__":
    unittest.main()
