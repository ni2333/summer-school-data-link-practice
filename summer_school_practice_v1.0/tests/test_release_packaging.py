from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ReleasePackagingTests(unittest.TestCase):
    def test_m6_presentation_limit_matches_final_manual(self):
        outline = (ROOT / "student_package/templates/m6_presentation_outline.md").read_text(encoding="utf-8")
        checklist = (ROOT / "student_package/templates/submission_checklist.md").read_text(encoding="utf-8")
        self.assertIn("五页成果展示提纲", outline)
        self.assertNotIn("六页成果展示提纲", outline)
        self.assertIn("不超过5页", checklist)
        self.assertNotIn("不超过6页", checklist)

    def test_release_archives_respect_student_boundary(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            completed = subprocess.run(
                [
                    sys.executable,
                    "environment/build_release_packages.py",
                    "--output-dir",
                    temp_dir,
                    "--clean",
                ],
                cwd=ROOT,
                check=False,
            )
            self.assertEqual(completed.returncode, 0)
            student = Path(temp_dir) / "student_package_v1.0.zip"
            ta = Path(temp_dir) / "ta_reference_package_v1.0.zip"
            self.assertTrue(student.is_file())
            self.assertTrue(ta.is_file())
            with zipfile.ZipFile(student) as archive:
                student_names = set(archive.namelist())
            with zipfile.ZipFile(ta) as archive:
                ta_names = set(archive.namelist())
            self.assertIn(
                "summer_school_practice_v1.0/environment/run_student_checks.py",
                student_names,
            )
            self.assertNotIn(
                "summer_school_practice_v1.0/ta_reference_package/reference_implementation/practice_reference.py",
                student_names,
            )
            self.assertNotIn(
                "summer_school_practice_v1.0/student_package/data/opensky_real/roundtrip_report.csv",
                student_names,
            )
            self.assertNotIn(
                "summer_school_practice_v1.0/experiment/run_opensky_experiment.py",
                student_names,
            )
            self.assertIn(
                "summer_school_practice_v1.0/ta_reference_package/reference_implementation/practice_reference.py",
                ta_names,
            )
            self.assertIn(
                "summer_school_practice_v1.0/ta_reference_package/expected_results/opensky_real_roundtrip_report.csv",
                ta_names,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
