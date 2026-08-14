from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ReleasePackagingTests(unittest.TestCase):
    def build_archives(self, output_dir: str) -> tuple[Path, Path]:
        completed = subprocess.run(
            [
                sys.executable,
                "-X",
                "utf8",
                "environment/build_release_packages.py",
                "--output-dir",
                output_dir,
                "--clean",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        return (
            Path(output_dir) / "student_package_v1.0.zip",
            Path(output_dir) / "ta_reference_package_v1.0.zip",
        )

    def test_m6_presentation_limit_matches_final_manual(self):
        outline = (ROOT / "student_package/templates/m6_presentation_outline.md").read_text(encoding="utf-8")
        checklist = (ROOT / "student_package/templates/submission_checklist.md").read_text(encoding="utf-8")
        self.assertIn("五页成果展示提纲", outline)
        self.assertNotIn("六页成果展示提纲", outline)
        self.assertIn("不超过5页", checklist)
        self.assertNotIn("不超过6页", checklist)

    def test_release_archives_respect_student_boundary(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            student, ta = self.build_archives(temp_dir)
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

    def test_check_only_rejects_stale_archive_content(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            student, _ = self.build_archives(temp_dir)
            temporary = student.with_suffix(".tmp")
            stale_entry = "summer_school_practice_v1.0/environment/setup.ps1"
            with zipfile.ZipFile(student) as source, zipfile.ZipFile(temporary, "w") as target:
                for info in source.infolist():
                    data = source.read(info.filename)
                    if info.filename == stale_entry:
                        data += b"\n# stale candidate\n"
                    target.writestr(info, data)
            temporary.replace(student)
            completed = subprocess.run(
                [
                    sys.executable,
                    "-X",
                    "utf8",
                    "environment/build_release_packages.py",
                    "--output-dir",
                    temp_dir,
                    "--check-only",
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("内容与当前源文件不一致", completed.stdout + completed.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
