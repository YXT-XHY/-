"""Public acquisition tests use parser/transfer fixtures, never clinical audio."""
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError

from data_tools.public_data import (check_url, download, safe_name, is_candidate,
                                    summarize, PublicRedirect, Client)

PAYLOAD = b"public-transfer-fixture-not-clinical-data"


def record():
    return {"id": 123, "metadata": {"title": "Transfer test", "access_right": "open",
            "license": {"id": "cc-by-4.0"}, "creators": [{"name": "Test author"}]},
            "files": [{"key": "fixture.txt", "size": len(PAYLOAD),
                       "checksum": "md5:" + hashlib.md5(PAYLOAD).hexdigest(),
                       "links": {"self": "https://zenodo.org/api/files/test/fixture.txt"}}]}


class Response(io.BytesIO):
    def __init__(self, data, status=200, headers=None):
        super().__init__(data)
        self.status, self.headers = status, headers or {}


class FakeClient:
    def __init__(self, data=PAYLOAD, status=200, headers=None):
        self.data, self.status, self.headers, self.calls = data, status, headers, []

    def open(self, url, headers):
        self.calls.append((url, headers))
        return Response(self.data, self.status, self.headers)


class TestPublicData(unittest.TestCase):
    def test_bounded_metadata_response(self):
        client = Client()
        client.opener.open = Mock(return_value=Response(b"123456789"))
        with self.assertRaisesRegex(ValueError, "Metadata exceeds"):
            client.json("https://zenodo.org/api/records/123", max_bytes=8)

    def test_connection_retry_but_no_access_denial_retry(self):
        with patch("data_tools.public_data.time.sleep"):
            client = Client()
            client.opener.open = Mock(side_effect=[URLError("temporary"), Response(b'{}')])
            self.assertEqual(client.json("https://zenodo.org/api/records/123"), {})
            self.assertEqual(client.opener.open.call_count, 2)
            client.opener.open = Mock(side_effect=HTTPError("https://zenodo.org", 403, "Denied", {}, None))
            with self.assertRaises(HTTPError):
                client.open("https://zenodo.org/api/records/123")
            self.assertEqual(client.opener.open.call_count, 1)

    def test_irrelevant_search_hits_are_filtered_without_assigning_labels(self):
        item = record()
        self.assertFalse(is_candidate(item))
        item["metadata"]["description"] = "Mandarin speech in Parkinson's disease"
        self.assertFalse(is_candidate(item))
        item["metadata"]["resource_type"] = {"type": "dataset"}
        self.assertTrue(is_candidate(item))
        self.assertFalse(summarize(item)["eligible_for_training"])

    def test_no_clinical_eligibility_inferred_from_search(self):
        value = summarize(record())
        self.assertTrue(value["download_permitted_by_tool"])
        self.assertFalse(value["eligible_for_training"])
        self.assertIn("clinical diagnosis labels", value["review_required"])

    def test_restricted_unknown_license_and_missing_license_refused_before_network(self):
        for metadata in ({"access_right": "restricted"}, {"license": {"id": "custom"}},
                         {"license": {}}, {"access_right": "embargoed"}):
            with self.subTest(metadata=metadata), tempfile.TemporaryDirectory() as folder:
                item = record()
                item["metadata"].update(metadata)
                client = FakeClient()
                with self.assertRaisesRegex(ValueError, "Download refused"):
                    download(item, "fixture.txt", folder, client, 1000)
                self.assertFalse(client.calls)

    def test_destination_and_redirect_validation(self):
        for name in ("../x.wav", "C:x.wav", "CON.wav", "LPT1.txt", "evil.exe", "x.wav "):
            with self.subTest(name=name), self.assertRaises(ValueError):
                safe_name(name)
        for url in ("http://zenodo.org/a", "https://127.0.0.1/a", "https://zenodo.org.evil/a",
                    "https://user@zenodo.org/a", "https://zenodo.org:8080/a"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                check_url(url)
        with self.assertRaises(ValueError):
            PublicRedirect().redirect_request(None, None, 302, "", {}, "https://example.com/private")

    def test_download_receipt_hash_and_verified_reuse(self):
        with tempfile.TemporaryDirectory() as folder:
            client = FakeClient()
            value = download(record(), "fixture.txt", folder, client, 1000)
            self.assertEqual(Path(value["local_path"]).read_bytes(), PAYLOAD)
            self.assertEqual(value["sha256"], hashlib.sha256(PAYLOAD).hexdigest())
            self.assertTrue(value["repository_checksum_verified"])
            self.assertFalse(value["eligible_for_training"])
            download(record(), "fixture.txt", folder, client, 1000)
            self.assertEqual(len(client.calls), 1)

    def test_resume_and_range_ignored_restart(self):
        for honor_range in (True, False):
            with self.subTest(honor_range=honor_range), tempfile.TemporaryDirectory() as folder:
                root = Path(folder) / "123"
                root.mkdir()
                item = record()["files"][0]
                (root / "fixture.txt.part").write_bytes(PAYLOAD[:5])
                (root / "fixture.txt.download.json").write_text(json.dumps({"url": item["links"]["self"],
                    "size": item["size"], "checksum": item["checksum"]}), encoding="utf-8")
                client = FakeClient(PAYLOAD[5:] if honor_range else PAYLOAD, 206 if honor_range else 200,
                    {"Content-Range": f"bytes 5-{len(PAYLOAD)-1}/{len(PAYLOAD)}"} if honor_range else {})
                value = download(record(), "fixture.txt", folder, client, 1000)
                self.assertEqual(client.calls[0][1]["Range"], "bytes=5-")
                self.assertEqual(Path(value["local_path"]).read_bytes(), PAYLOAD)

    def test_mismatched_checksum_and_bad_range_never_publish(self):
        for client in (FakeClient(b"x" * len(PAYLOAD)), FakeClient(PAYLOAD, 206, {"Content-Range": "bad"})):
            with self.subTest(client=client), tempfile.TemporaryDirectory() as folder:
                with self.assertRaises(ValueError):
                    download(record(), "fixture.txt", folder, client, 1000)
                self.assertFalse((Path(folder) / "123" / "fixture.txt").exists())

    def test_incomplete_transfer_can_resume(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, "Incomplete"):
                download(record(), "fixture.txt", folder, FakeClient(PAYLOAD[:5]), 1000)
            value = download(record(), "fixture.txt", folder, FakeClient(PAYLOAD[5:], 206,
                {"Content-Range": f"bytes 5-{len(PAYLOAD)-1}/{len(PAYLOAD)}"}), 1000)
            self.assertEqual(Path(value["local_path"]).read_bytes(), PAYLOAD)

    def test_limits_changed_partial_and_existing_destination_are_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            client = FakeClient()
            with self.assertRaisesRegex(ValueError, "max-mb"):
                download(record(), "fixture.txt", folder, client, 1)
            root = Path(folder) / "123"
            root.mkdir()
            (root / "fixture.txt.part").write_bytes(b"previous")
            with self.assertRaisesRegex(ValueError, "different metadata"):
                download(record(), "fixture.txt", folder, client, 1000)
            (root / "fixture.txt").write_bytes(b"user-file")
            with self.assertRaisesRegex(ValueError, "refusing overwrite"):
                download(record(), "fixture.txt", folder, client, 1000)
            self.assertEqual((root / "fixture.txt").read_bytes(), b"user-file")
            self.assertFalse(client.calls)
