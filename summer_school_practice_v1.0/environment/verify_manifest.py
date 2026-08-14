from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifest.csv"
EXCLUDED_PARTS = {".venv", "__pycache__", "dist", "wheelhouse"}
EXCLUDED_PREFIXES = {
    "experiment/output/",
    "student_package/output/",
    "test_records/latest_reference_run/",
    "test_records/.last_trial_output",
    "test_records/latest_trial_report",
}


def main() -> int:
    with MANIFEST.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    normalized_paths = [row["path"].replace("\\", "/") for row in rows]
    listed = set(normalized_paths)
    missing = [row["path"] for row in rows if not (ROOT / row["path"]).is_file()]
    duplicate_paths = sorted(path for path in listed if normalized_paths.count(path) > 1)
    invalid_public = []
    for row in rows:
        relative = row["path"].replace("\\", "/")
        if row["student_public"].lower() != "true":
            continue
        parts = set(Path(relative).parts)
        if (
            parts & {"ta_reference_package", "tests", "test_records", "reference_implementation", "expected_results"}
            or Path(relative).name in {"case_manifest_internal.csv", "expected_alert_counts.json"}
            or relative == "student_package/data/opensky_real/roundtrip_report.csv"
        ):
            invalid_public.append(relative)
    unlisted = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or set(path.parts) & EXCLUDED_PARTS:
            continue
        relative = path.relative_to(ROOT).as_posix()
        if any(relative.startswith(prefix) for prefix in EXCLUDED_PREFIXES):
            continue
        if relative not in listed:
            unlisted.append(relative)

    checks = [
        ("清单路径存在", not missing, f"missing={missing}"),
        ("清单路径唯一", not duplicate_paths, f"duplicates={duplicate_paths}"),
        ("学生公开边界", not invalid_public, f"invalid_public={invalid_public}"),
        ("正式文件均入清单", not unlisted, f"unlisted={unlisted}"),
    ]
    for name, passed, detail in checks:
        print(f"[{'PASS' if passed else 'FAIL'}] {name}：{detail}")
    return 0 if all(passed for _, passed, _ in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
