from __future__ import annotations

import csv
import hashlib
import json
import sys
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "student_package" / "data" / "real_adsb"
REFERENCE = ROOT / "ta_reference_package" / "reference_implementation"
sys.path.insert(0, str(REFERENCE))

from practice_reference import FRAME_SIZE, build_tracks, decode_message_stream  # noqa: E402


class RealAdsbDatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.provenance = json.loads((DATA / "provenance.json").read_text(encoding="utf-8"))

    def test_provenance_and_license_are_explicit(self):
        self.assertEqual(self.provenance["provider"], "ADSB.lol")
        self.assertIn("api.adsb.lol", self.provenance["source_url"])
        self.assertIn("ODbL", self.provenance["license"])
        self.assertTrue(self.provenance["no_interpolation"])
        self.assertTrue(self.provenance["no_synthetic_values"])
        self.assertEqual(self.provenance["snapshot_count"], 3)

    def test_filtered_source_snapshots_match_checksums(self):
        self.assertEqual(len(self.provenance["sources"]), 3)
        for source in self.provenance["sources"]:
            path = DATA / source["file"]
            body = path.read_bytes()
            self.assertEqual(hashlib.sha256(body).hexdigest(), source["committed_filtered_file_sha256"])
            payload = json.loads(body)
            self.assertEqual(payload["source"], "ADSB.lol")
            self.assertEqual(payload["retained_aircraft_count"], len(payload["ac"]))
            for aircraft in payload["ac"]:
                self.assertIsNotNone(aircraft.get("lat"))
                self.assertIsNotNone(aircraft.get("lon"))
                self.assertTrue(str(aircraft.get("flight") or "").strip())
                self.assertIn(aircraft.get("dbFlags"), (None, 0))

    def test_normalized_dataset_has_all_snapshots(self):
        with (DATA / "normalized_aircraft_states.csv").open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), self.provenance["normalized_record_count"])
        self.assertGreater(len(rows), 9)
        self.assertEqual({row["snapshot_index"] for row in rows}, {"1", "2", "3"})
        self.assertTrue(all(row["target_id"] and row["lat_deg"] and row["lon_deg"] for row in rows))
        self.assertTrue(all(row["db_flags"] == "0" for row in rows))

    def test_three_by_three_tracks_are_real_and_complete(self):
        with (DATA / "real_tracks_3x3.csv").open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 9)
        self.assertEqual(Counter(row["target_id"] for row in rows), Counter({target: 3 for target in self.provenance["selected_targets"]}))
        for target in self.provenance["selected_targets"]:
            observations = [row for row in rows if row["target_id"] == target]
            self.assertEqual({row["snapshot_index"] for row in observations}, {"1", "2", "3"})
            self.assertEqual(len({row["timestamp_unix"] for row in observations}), 3)
            self.assertTrue(all(row["source_provider"] == "ADSB.lol" for row in observations))

    def test_binary_roundtrip_is_valid_offline(self):
        binary = (DATA / "real_partner_messages_multitime.bin").read_bytes()
        self.assertEqual(len(binary), 9 * FRAME_SIZE)
        decoded, stream_errors = decode_message_stream(binary)
        self.assertFalse(stream_errors)
        self.assertEqual(len(decoded), 9)
        self.assertTrue(all(row["message_valid"] for row in decoded))
        tracks = build_tracks(decoded)
        self.assertEqual(len(tracks), 9)
        self.assertEqual(Counter(row["target_id"] for row in tracks), Counter({target: 3 for target in self.provenance["selected_targets"]}))


if __name__ == "__main__":
    unittest.main()
