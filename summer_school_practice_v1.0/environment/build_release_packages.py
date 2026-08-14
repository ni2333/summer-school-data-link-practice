from __future__ import annotations

import argparse
import csv
import zipfile
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifest.csv"
ARCHIVE_ROOT = "summer_school_practice_v1.0"
STUDENT_ARCHIVE = "student_package_v1.0.zip"
TA_ARCHIVE = "ta_reference_package_v1.0.zip"

FORBIDDEN_STUDENT_PARTS = {
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


def load_manifest() -> list[ManifestRow]:
    with MANIFEST.open("r", encoding="utf-8-sig", newline="") as handle:
        source_rows = list(csv.DictReader(handle))
    rows = [
        ManifestRow(
            path=row["path"].replace("\\", "/"),
            student_public=row["student_public"].strip().lower() == "true",
        )
        for row in source_rows
    ]
    paths = [row.path for row in rows]
    if len(paths) != len(set(paths)):
        raise ValueError("manifest.csv存在重复路径")
    missing = [row.path for row in rows if not (ROOT / row.path).is_file()]
    if missing:
        raise FileNotFoundError("manifest.csv存在缺失文件：" + "；".join(missing))
    return rows


def validate_student_paths(paths: set[str]) -> None:
    missing_required = sorted(REQUIRED_STUDENT_PATHS - paths)
    if missing_required:
        raise ValueError("学生包缺少必需文件：" + "；".join(missing_required))
    violations: list[str] = []
    for value in sorted(paths):
        parts = set(Path(value).parts)
        if (
            parts & FORBIDDEN_STUDENT_PARTS
            or Path(value).name in FORBIDDEN_STUDENT_NAMES
            or value in FORBIDDEN_STUDENT_PATHS
        ):
            violations.append(value)
    if violations:
        raise ValueError("学生包包含内部参考或答案文件：" + "；".join(violations))


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
        actual = set(archive.namelist())
        corrupt = archive.testzip()
    if corrupt:
        raise ValueError(f"{target.name}损坏条目：{corrupt}")
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise ValueError(f"{target.name}内容不一致：missing={missing}，extra={extra}")


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


def main() -> int:
    parser = argparse.ArgumentParser(description="生成并核对学生正式包和助教参考包候选文件。")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    parser.add_argument("--check-only", action="store_true", help="只检查清单和学生/助教边界，不写ZIP")
    parser.add_argument("--clean", action="store_true", help="生成前删除旧候选压缩包")
    args = parser.parse_args()

    rows = load_manifest()
    student_paths, ta_paths = package_plan(rows)
    print(f"[PASS] 学生包边界：{len(student_paths)}个公开文件")
    print(f"[PASS] 助教包清单：{len(ta_paths)}个正式文件")
    if args.check_only:
        return 0

    output_dir = args.output_dir.resolve()
    validate_output_dir(output_dir)
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
