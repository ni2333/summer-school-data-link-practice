from __future__ import annotations

import csv
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiment"
sys.path.insert(0, str(EXPERIMENT))

from run_opensky_experiment import run_experiment  # noqa: E402


class OpenSkyExperimentTests(unittest.TestCase):
    def test_ten_target_end_to_end_experiment(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir)
            summary = run_experiment(output, target_limit=10)
            self.assertEqual(summary["selected_target_count"], 10)
            self.assertEqual(summary["sent_frame_count"], summary["valid_received_frame_count"])
            self.assertEqual(summary["sent_frame_count"], summary["sqlite_row_count"])
            self.assertEqual(summary["sqlite_row_count"], summary["sqlite_valid_row_count"])
            self.assertTrue(summary["all_frames_valid"])
            self.assertEqual((output / "transmitted_frames.bin").stat().st_size, summary["sent_frame_count"] * 41)

            with (output / "receiver_situation_initial.csv").open(encoding="utf-8-sig", newline="") as handle:
                self.assertEqual(list(csv.DictReader(handle)), [])
            with (output / "receiver_situation_final.csv").open(encoding="utf-8-sig", newline="") as handle:
                final_rows = list(csv.DictReader(handle))
            self.assertEqual(len(final_rows), 10)
            self.assertTrue(all(int(row["track_length"]) >= 2 for row in final_rows))

            connection = sqlite3.connect(output / "received_states.db")
            try:
                db_count = connection.execute("SELECT COUNT(*) FROM state_record").fetchone()[0]
            finally:
                connection.close()
            self.assertEqual(db_count, summary["sent_frame_count"])

    def test_precision_stays_inside_protocol_quantization_steps(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            summary = run_experiment(Path(temp_dir), target_limit=10)
            self.assertLess(summary["max_horizontal_error_m"], 5.0)
            self.assertLessEqual(summary["max_altitude_error_m"], 0.5 + 1e-9)
            self.assertLessEqual(summary["max_speed_error_m_s"], 0.05 + 1e-9)
            self.assertLessEqual(summary["max_heading_error_deg"], 0.005 + 1e-9)
            self.assertLessEqual(summary["max_vertical_rate_error_m_s"], 0.005 + 1e-9)

    def test_single_target_mode_and_deterministic_summary(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            summary_1 = run_experiment(Path(first), target_limit=1)
            summary_2 = run_experiment(Path(second), target_limit=1)
            self.assertEqual(summary_1, summary_2)
            self.assertEqual(summary_1["selected_target_count"], 1)
            self.assertGreaterEqual(summary_1["selected_record_count"], 2)
            saved = json.loads((Path(first) / "experiment_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(saved, summary_1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
