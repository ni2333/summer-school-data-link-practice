from __future__ import annotations

import argparse
import csv
import zipfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifest.csv"
ARCHIVE_ROOT = "summer_school_practice_v1.0"
STUDENT_ARCHIVE = "student_package_v1.0.zip"
TA_ARCHIVE = "ta_reference_package_v1.0.zip"

FORBIDDEN_STUDENT_PARTS = {
    "experiment",
    "ta_reference_package",
    "tests",
    "test_records",
    "reference_implementation",
    "expected_results",
}
FORBIDDEN_STUDENT_NAMES = {
    "case_manifest_internal.csv",
    "expected_alert_counts.json",
}
FORBIDDEN_STUDENT_PATHS = {
    "student_package/data/opensky_real/roundtrip_report.csv",
}
REQUIRED_STUDENT_PATHS = {
    "environment/requirements.txt",
    "environment/README_environment.md",
    "environment/setup.ps1",
    "environment/setup.sh",
    "environment/environment_check.py",
    "environment/run_smoke_test.py",
    "environment/run_student_checks.py",
    "environment/build_wheelhouse.py",
    "student_package/README.md",
    "student_package/templates/checkpoint_switch.md",
    "student_package/templates/submission_checklist.md",
}


@dataclass(frozen=True)
class ManifestRow:
    path: str
    student_public: bool


def read_manifest_rows() -> list[ManifestRow]:
    with MANIFEST.open("r", encoding="utf-8-sig", newline="") as handle:
        source_rows = list(csv.DictReader(handle))
    return [
        ManifestRow(
            path=row["path"].replace("\\", "/"),
            student_public=row["student_public"].strip().lower() == "true",
        )
        for row in source_rows
    ]


def find_duplicate_manifest_paths(rows: list[ManifestRow]) -> list[str]:
    counts = Counter(row.path for row in rows)
    return sorted(path for path, count in counts.items() if count > 1)


def find_missing_manifest_paths(rows: list[ManifestRow]) -> list[str]:
    return [row.path for row in rows if not (ROOT / row.path).is_file()]


def find_missing_required_student_paths(paths: set[str]) -> list[str]:
    return sorted(REQUIRED_STUDENT_PATHS - paths)


def find_student_policy_violations(paths: set[str]) -> list[str]:
    violations: list[str] = []
    for value in sorted(paths):
        parts = set(Path(value).parts)
        if (
            parts & FORBIDDEN_STUDENT_PARTS
            or Path(value).name in FORBIDDEN_STUDENT_NAMES
            or value in FORBIDDEN_STUDENT_PATHS
        ):
            violations.append(value)
    return violations


def validate_student_paths(paths: set[str]) -> None:
    missing_required = find_missing_required_student_paths(paths)
    if missing_required:
        raise ValueError("学生包缺少必需文件：" + "；".join(missing_required))
    violations = find_student_policy_violations(paths)
    if violations:
        raise ValueError("学生包包含内部参考或答案文件：" + "；".join(violations))


def load_manifest() -> list[ManifestRow]:
    rows = read_manifest_rows()
    duplicates = find_duplicate_manifest_paths(rows)
    if duplicates:
        raise ValueError("manifest.csv存在重复路径：" + "；".join(duplicates))
    missing = find_missing_manifest_paths(rows)
    if missing:
        raise FileNotFoundError("manifest.csv存在缺失文件：" + "；".join(missing))
    validate_student_paths({row.path for row in rows if row.student_public})
    return rows


def archive_name(relative: str) -> str:
    return f"{ARCHIVE_ROOT}/{relative}"


def write_archive(target: Path, paths: list[str]) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    if temporary.exists():
        temporary.unlink()
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for relative in sorted(paths):
            data = (ROOT / relative).read_bytes()
            info = zipfile.ZipInfo(archive_name(relative), date_time=(2026, 8, 14, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    temporary.replace(target)


def verify_archive(target: Path, paths: set[str]) -> None:
    expected = {archive_name(path) for path in paths}
    with zipfile.ZipFile(target) as archive:
        names = archive.namelist()
        duplicates = sorted(name for name, count in Counter(names).items() if count > 1)
        actual = set(names)
        corrupt = archive.testzip()
        if duplicates:
            raise ValueError(f"{target.name}存在重复条目：{duplicates}")
        if corrupt:
            raise ValueError(f"{target.name}损坏条目：{corrupt}")
        if actual != expected:
            missing = sorted(expected - actual)
            extra = sorted(actual - expected)
            raise ValueError(f"{target.name}内容不一致：missing={missing}，extra={extra}")
        mismatched = [
            relative
            for relative in sorted(paths)
            if archive.read(archive_name(relative)) != (ROOT / relative).read_bytes()
        ]
    if mismatched:
        raise ValueError(f"{target.name}内容与当前源文件不一致：{mismatched}")


def package_plan(rows: list[ManifestRow]) -> tuple[list[str], list[str]]:
    student = [row.path for row in rows if row.student_public]
    ta = [row.path for row in rows]
    validate_student_paths(set(student))
    return student, ta


def validate_output_dir(output_dir: Path) -> None:
    if output_dir == ROOT or ROOT.is_relative_to(output_dir):
        raise ValueError(f"输出目录不得是课程包根目录或其上级目录：{output_dir}")


def clean_old_archives(output_dir: Path) -> None:
    for name in (STUDENT_ARCHIVE, TA_ARCHIVE):
        for target in (output_dir / name, output_dir / f"{name}.tmp"):
            if target.exists():
                target.unlink()


def verify_existing_archives(output_dir: Path, student_paths: list[str], ta_paths: list[str]) -> None:
    plans = [
        (output_dir / STUDENT_ARCHIVE, set(student_paths)),
        (output_dir / TA_ARCHIVE, set(ta_paths)),
    ]
    existing = [target for target, _ in plans if target.exists()]
    if not existing:
        print(f"[SKIP] 未发现已有候选ZIP：{output_dir}")
        return
    missing = [target.name for target, _ in plans if not target.is_file()]
    if missing:
        raise FileNotFoundError("候选ZIP不完整，缺少：" + "；".join(missing))
    for target, paths in plans:
        verify_archive(target, paths)
        print(f"[PASS] 已有候选ZIP与当前源文件一致：{target}")


def main() -> int:
    parser = argparse.ArgumentParser(description="生成并核对学生正式包和助教参考包候选文件。")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="检查清单、学生/助教边界及已有候选ZIP，不写ZIP",
    )
    parser.add_argument("--clean", action="store_true", help="生成前删除旧候选压缩包")
    args = parser.parse_args()

    rows = load_manifest()
    student_paths, ta_paths = package_plan(rows)
    print(f"[PASS] 学生包边界：{len(student_paths)}个公开文件")
    print(f"[PASS] 助教包清单：{len(ta_paths)}个正式文件")
    output_dir = args.output_dir.resolve()
    validate_output_dir(output_dir)
    if args.check_only:
        try:
            verify_existing_archives(output_dir, student_paths, ta_paths)
        except (OSError, ValueError) as exc:
            print(f"[FAIL] 候选ZIP检查：{exc}")
            return 1
        return 0

    if args.clean:
        clean_old_archives(output_dir)
    student_target = output_dir / STUDENT_ARCHIVE
    ta_target = output_dir / TA_ARCHIVE
    write_archive(student_target, student_paths)
    write_archive(ta_target, ta_paths)
    verify_archive(student_target, set(student_paths))
    verify_archive(ta_target, set(ta_paths))
    print(f"[PASS] 学生候选包：{student_target}")
    print(f"[PASS] 助教候选包：{ta_target}")
    print("说明：完成独立试跑和签字前，这两个文件仍是发布候选包，不得标记冻结。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
