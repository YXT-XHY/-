"""Prevent invalid cohort imports and diagnosis/source confounding."""
import csv
from pathlib import Path
import tempfile
import unittest

from test_deep_learning import DL_AVAILABLE


@unittest.skipUnless(DL_AVAILABLE, "Requires deep learning environment")
class TestTrainingManifest(unittest.TestCase):
    def read_rows(self, entries):
        from deep_learning.train import read_manifest
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            rows = []
            for index, entry in enumerate(entries):
                # Parser-only fixtures; never used as training audio.
                audio = root / f"sample_{index}.wav"
                audio.write_bytes(f"manifest-parser-fixture-{index}".encode())
                row = dict(path=audio.name, subject=f"S{index}", label=str(index % 2),
                           task="reading", language="zh", dataset="clinical")
                row.update(entry)
                rows.append(row)
            manifest = root / "manifest.csv"
            with manifest.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
            return read_manifest(manifest)

    def test_balanced_chinese_cohort_and_repeated_subject(self):
        rows, labels = self.read_rows([{}, {}, {"subject": "S0", "label": "0"}])
        self.assertEqual(labels, {"S0": 0, "S1": 1})
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(Path(row["path"]).is_absolute() for row in rows))

    def test_language_and_source_confounding_rejected(self):
        for entries in ([{"language": "zh"}, {"language": "en"}],
                        [{"dataset": "healthy_asr"}, {"dataset": "pd_clinic"}]):
            with self.subTest(entries=entries):
                with self.assertRaisesRegex(ValueError, "confound"):
                    self.read_rows(entries)

    def test_missing_identity_or_unknown_diagnosis_rejected(self):
        for entry in ({"subject": " "}, {"language": ""}, {"label": "unknown"}):
            with self.subTest(entry=entry):
                with self.assertRaises(ValueError):
                    self.read_rows([entry, {}])

    def test_single_class_or_conflicting_subject_labels_rejected(self):
        with self.assertRaisesRegex(ValueError, "both HC and PD"):
            self.read_rows([{"label": "1"}, {"label": "1"}])
        with self.assertRaisesRegex(ValueError, "Conflicting labels"):
            self.read_rows([{}, {"subject": "S0"}])
