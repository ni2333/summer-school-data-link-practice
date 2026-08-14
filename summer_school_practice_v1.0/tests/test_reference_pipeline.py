from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "ta_reference_package" / "reference_implementation"
sys.path.insert(0, str(REFERENCE))

from practice_reference import (  # noqa: E402
    FRAME_SIZE,
    STATUS_ALT_GEOMETRIC,
    VALID_LAT,
    build_current_situation,
    build_tracks,
    calculate_checksum,
    check_quality,
    decode_message_stream,
    decode_position_message,
    encode_position_message,
)
from run_all_reference import run, typed_anomaly_rows  # noqa: E402


def record(**overrides):
    base = {
        "target_id": "000001",
        "callsign": "TEST0001",
        "timestamp": 1710000060,
        "timestamp_source": "POSITION_TIME",
        "time_source": "position_time",
        "lat": 0.0,
        "lon": 0.0,
        "altitude": 0.0,
        "alt_type": "barometric",
        "speed": 0.0,
        "heading": 0.0,
        "vertical_rate": 0.0,
        "on_ground": True,
    }
    base.update(overrides)
    return base


class TeachingLinkTests(unittest.TestCase):
    def test_frame_length_and_roundtrip_zero(self):
        frame = encode_position_message(record(), 65535)
        self.assertEqual(len(frame), FRAME_SIZE)
        decoded = decode_position_message(frame)
        self.assertTrue(decoded["message_valid"])
        self.assertEqual(decoded["target_id"], "000001")
        self.assertAlmostEqual(decoded["lat"], 0.0, delta=180.0 / ((1 << 22) - 1))
        self.assertAlmostEqual(decoded["lon"], 0.0, delta=360.0 / ((1 << 22) - 1))
        self.assertEqual(decoded["speed"], 0.0)
        self.assertEqual(decoded["heading"], 0.0)
        self.assertEqual(decoded["vertical_rate"], 0.0)
        self.assertTrue(decoded["validity_flags"] & VALID_LAT)

    def test_missing_fields_are_not_zero(self):
        missing = record(callsign=None, lat=None, lon=None, altitude=None, alt_type="unknown", speed=None, heading=None, vertical_rate=None)
        decoded = decode_position_message(encode_position_message(missing, 1))
        self.assertTrue(decoded["message_valid"])
        self.assertEqual(decoded["validity_flags"], 0)
        self.assertIsNone(decoded["lat"])
        self.assertIsNone(decoded["heading"])

    def test_checksum_error_is_detected(self):
        frame = bytearray(encode_position_message(record(), 1))
        frame[20] ^= 0x01
        decoded = decode_position_message(bytes(frame))
        self.assertFalse(decoded["message_valid"])
        self.assertIn("CHECKSUM_ERROR", decoded["validation_errors"])

    def test_reserved_bits_error_is_detected(self):
        frame = bytearray(encode_position_message(record(), 1))
        frame[23] |= 0x40
        frame[39:41] = calculate_checksum(frame[:39]).to_bytes(2, "big")
        decoded = decode_position_message(bytes(frame))
        self.assertFalse(decoded["message_valid"])
        self.assertIn("RESERVED_BITS_ERROR", decoded["validation_errors"])

    def test_flag_value_inconsistency_is_detected(self):
        frame = bytearray(encode_position_message(record(lat=None), 1))
        frame[25] = 1
        frame[39:41] = calculate_checksum(frame[:39]).to_bytes(2, "big")
        decoded = decode_position_message(bytes(frame))
        self.assertFalse(decoded["message_valid"])
        self.assertIn("FLAG_VALUE_INCONSISTENCY", decoded["validation_errors"])

    def test_invalid_altitude_source_without_altitude(self):
        frame = bytearray(encode_position_message(record(altitude=None, alt_type="unknown"), 1))
        frame[37] |= STATUS_ALT_GEOMETRIC
        frame[39:41] = calculate_checksum(frame[:39]).to_bytes(2, "big")
        decoded = decode_position_message(bytes(frame))
        self.assertIn("FLAG_VALUE_INCONSISTENCY", decoded["validation_errors"])

    def test_heading_that_quantizes_to_360_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "量化后不得达到360.00度"):
            encode_position_message(record(heading=359.999), 1)


class PipelineTests(unittest.TestCase):
    def test_multitime_and_tail(self):
        stream = (ROOT / "student_package" / "data" / "partner_messages_multitime.bin").read_bytes()
        records, errors = decode_message_stream(stream)
        self.assertEqual(len(records), 9)
        self.assertFalse(errors)
        tracks = build_tracks(records)
        current = build_current_situation(records)
        self.assertEqual(len(tracks), 9)
        self.assertEqual(len(current), 3)
        self.assertEqual({row["track_length"] for row in current}, {3})
        tailed_records, tail_errors = decode_message_stream(stream + b"abc")
        self.assertEqual(len(tailed_records), 9)
        self.assertEqual(tail_errors[0]["problem_type"], "LENGTH_ERROR")

    def test_quality_expected_counts(self):
        rows = typed_anomaly_rows(ROOT / "student_package" / "data" / "m5" / "anomaly_cases.csv")
        alerts, quality = check_quality(rows)
        self.assertEqual(len(alerts), 5)
        self.assertEqual(sum(row["severity"] == "HIGH" for row in alerts), 1)
        self.assertEqual(sum(row["severity"] == "MEDIUM" for row in alerts), 4)
        self.assertEqual(len(quality), 6)

    def test_clean_end_to_end_run(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            summary = run(ROOT / "student_package", Path(temp_dir), use_sqlite=True)
            self.assertEqual(summary["roundtrip_failures"], 0)
            self.assertEqual(summary["multitime_frames"], 9)
            self.assertEqual(summary["track_rows"], 9)
            self.assertEqual(summary["targets"], 3)
            self.assertEqual(summary["alerts"], 5)
            self.assertEqual(summary["sqlite_rows"], 9)
            parsed = json.loads((Path(temp_dir) / "run_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(parsed["unified_messages"], 6)


if __name__ == "__main__":
    unittest.main(verbosity=2)
