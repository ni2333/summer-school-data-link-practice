from __future__ import annotations

from pathlib import Path

from build_release_packages import (
    ROOT,
    find_duplicate_manifest_paths,
    find_missing_manifest_paths,
    find_missing_required_student_paths,
    find_student_policy_violations,
    read_manifest_rows,
)
EXCLUDED_PARTS = {".venv", "__pycache__", "dist", "wheelhouse"}
EXCLUDED_PREFIXES = {
    "experiment/output/",
    "experiment/rendered_report",
    "student_package/output/",
    "test_records/latest_reference_run/",
    "test_records/.last_trial_output",
    "test_records/latest_trial_report",
}


def main() -> int:
    rows = read_manifest_rows()
    listed = {row.path for row in rows}
    missing = find_missing_manifest_paths(rows)
    duplicate_paths = find_duplicate_manifest_paths(rows)
    student_paths = {row.path for row in rows if row.student_public}
    missing_required = find_missing_required_student_paths(student_paths)
    invalid_public = find_student_policy_violations(student_paths)
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
        ("学生包必需文件", not missing_required, f"missing_required={missing_required}"),
        ("学生公开边界", not invalid_public, f"invalid_public={invalid_public}"),
        ("正式文件均入清单", not unlisted, f"unlisted={unlisted}"),
    ]
    for name, passed, detail in checks:
        print(f"[{'PASS' if passed else 'FAIL'}] {name}：{detail}")
    return 0 if all(passed for _, passed, _ in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
