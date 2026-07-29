from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifest.csv"


def main() -> int:
    with MANIFEST.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    listed = {row["path"].replace("\\", "/") for row in rows}
    missing = [row["path"] for row in rows if not (ROOT / row["path"]).is_file()]
    invalid_public = [
        row["path"] for row in rows
        if row["student_public"].lower() == "true"
        and (row["path"].startswith("ta_reference_package/") or row["path"].startswith("test_records/"))
    ]
    unlisted_student = []
    for path in (ROOT / "student_package").rglob("*"):
        if not path.is_file() or "__pycache__" in path.parts or "output" in path.parts:
            continue
        relative = path.relative_to(ROOT).as_posix()
        if relative not in listed:
            unlisted_student.append(relative)

    checks = [
        ("清单路径存在", not missing, f"missing={missing}"),
        ("学生公开边界", not invalid_public, f"invalid_public={invalid_public}"),
        ("学生文件均入清单", not unlisted_student, f"unlisted={unlisted_student}"),
    ]
    for name, passed, detail in checks:
        print(f"[{'PASS' if passed else 'FAIL'}] {name}：{detail}")
    return 0 if all(passed for _, passed, _ in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
