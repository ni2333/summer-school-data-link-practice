from __future__ import annotations

import csv
import hashlib
import json
import sys
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "student_package" / "data" / "opensky_real"
REFERENCE = ROOT / "ta_reference_package" / "reference_implementation"
sys.path.insert(0, str(REFERENCE))

from practice_reference import FRAME_SIZE, decode_message_stream, parse_open_sky_payload  # noqa: E402


class OpenSkyRealDatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.provenance = json.loads((DATA / "provenance.json").read_text(encoding="utf-8"))

    def test_01_source_and_processing_are_explicit(self):
        self.assertEqual(self.provenance["provider"], "The OpenSky Network")
        self.assertIn("opensky-network.org/api/states/all", self.provenance["source_url"])
        self.assertTrue(self.provenance["anonymous_api"])
        self.assertTrue(self.provenance["no_interpolation"])
        self.assertTrue(self.provenance["no_synthetic_values"])

    def test_02_official_api_documentation_is_recorded(self):
        self.assertIn("opensky-api/rest.html", self.provenance["api_documentation"])
        self.assertNotIn("distribution_review_required", self.provenance)

    def test_03_three_raw_snapshots_match_sha256(self):
        self.assertEqual(self.provenance["snapshot_count"], 3)
        self.assertEqual(len(self.provenance["sources"]), 3)
        for source in self.provenance["sources"]:
            body = (DATA / source["file"]).read_bytes()
            self.assertEqual(hashlib.sha256(body).hexdigest(), source["sha256"])
            payload = json.loads(body)
            self.assertEqual(payload["time"], source["snapshot_time"])
            self.assertEqual(len(payload["states"]), source["state_count"])

    def test_04_raw_vectors_have_official_shape_and_bbox_positions(self):
        bbox = self.provenance["query_bbox_wgs84"]
        for source in self.provenance["sources"]:
            payload = json.loads((DATA / source["file"]).read_text(encoding="utf-8"))
            for vector in payload["states"]:
                self.assertGreaterEqual(len(vector), 17)
                self.assertRegex(vector[0], r"^[0-9a-f]{6}$")
                if vector[5] is not None and vector[6] is not None:
                    self.assertGreaterEqual(vector[5], bbox["lomin"])
                    self.assertLessEqual(vector[5], bbox["lomax"])
                    self.assertGreaterEqual(vector[6], bbox["lamin"])
                    self.assertLessEqual(vector[6], bbox["lamax"])

    def test_05_normalized_count_and_values_match_raw_sources(self):
        with (DATA / "normalized_state_vectors.csv").open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        expected_count = sum(source["state_count"] for source in self.provenance["sources"])
        self.assertEqual(len(rows), expected_count)
        self.assertEqual(len(rows), self.provenance["normalized_record_count"])
        self.assertEqual({row["snapshot_index"] for row in rows}, {"1", "2", "3"})
        self.assertNotIn("000001", {row["icao24"] for row in rows})
        self.assertNotIn("TEST0001", {row["callsign"].strip() for row in rows})

    def test_06_reference_parser_acceptance_matches_provenance(self):
        parsed_count = 0
        error_count = 0
        for source in self.provenance["sources"]:
            payload = json.loads((DATA / source["file"]).read_text(encoding="utf-8"))
            parsed, errors = parse_open_sky_payload(payload)
            parsed_count += len(parsed)
            error_count += len(errors)
        self.assertEqual(parsed_count, self.provenance["parsed_record_count"])
        self.assertEqual(error_count, self.provenance["parse_error_count"])
        self.assertGreater(parsed_count, 0)

    def test_07_teachinglink_binary_is_fully_decodable(self):
        binary = (DATA / "opensky_real_messages.bin").read_bytes()
        self.assertEqual(len(binary), self.provenance["encoded_frame_count"] * FRAME_SIZE)
        decoded, stream_errors = decode_message_stream(binary)
        self.assertFalse(stream_errors)
        self.assertEqual(len(decoded), self.provenance["encoded_frame_count"])
        self.assertTrue(all(row["message_valid"] for row in decoded))

    def test_08_roundtrip_report_accounts_for_every_source_vector(self):
        with (DATA / "roundtrip_report.csv").open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), self.provenance["normalized_record_count"])
        counts = Counter(row["outcome"] for row in rows)
        self.assertEqual(counts["ROUNDTRIP_OK"], self.provenance["encoded_frame_count"])
        self.assertEqual(counts["PARSE_REJECTED"], self.provenance["parse_error_count"])

    def test_09_snapshot_times_are_distinct_and_ordered(self):
        times = [source["snapshot_time"] for source in self.provenance["sources"]]
        self.assertEqual(times, sorted(times))
        self.assertEqual(len(set(times)), 3)
        self.assertGreaterEqual(times[-1] - times[0], 10)

    def test_10_multiple_aircraft_repeat_across_snapshots(self):
        repeated = self.provenance["repeated_targets"]
        self.assertGreaterEqual(len(repeated), 1)
        self.assertTrue(all(len(target) == 6 for target in repeated))


if __name__ == "__main__":
    unittest.main()
