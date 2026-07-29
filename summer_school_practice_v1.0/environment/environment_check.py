from __future__ import annotations

import argparse
import importlib.metadata
import importlib.util
import json
import platform
import re
import sqlite3
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path


MIN_PYTHON = (3, 10)


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str


def check_python() -> CheckResult:
    passed = sys.version_info >= MIN_PYTHON
    return CheckResult(
        "Python版本",
        passed,
        f"当前 {platform.python_version()}，要求 {MIN_PYTHON[0]}.{MIN_PYTHON[1]} 及以上",
    )


def check_module(
    module_name: str,
    minimum: tuple[int, ...],
    maximum_exclusive: tuple[int, ...],
) -> CheckResult:
    try:
        specification = importlib.util.find_spec(module_name)
        if specification is None:
            return CheckResult(f"依赖 {module_name}", False, "未找到可导入模块")
        version = importlib.metadata.version(module_name)
        parts = tuple(int(part) for part in re.findall(r"\d+", version)[:3])
    except Exception as exc:
        return CheckResult(f"依赖 {module_name}", False, f"检测失败：{exc}")
    passed = parts >= minimum and parts < maximum_exclusive
    requirement = f">={'.'.join(map(str, minimum))}, <{'.'.join(map(str, maximum_exclusive))}"
    return CheckResult(f"依赖 {module_name}", passed, f"已安装 {version}，要求 {requirement}")


def check_utf8_and_write(workspace: Path) -> CheckResult:
    test_directory = workspace / f"env_check_{uuid.uuid4().hex}"
    try:
        workspace.mkdir(parents=True, exist_ok=True)
        test_directory.mkdir()
        target = test_directory / "中文 空格 UTF-8.json"
        payload = {"status": "正常", "value": 0, "missing": None}
        target.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        loaded = json.loads(target.read_text(encoding="utf-8"))
        target.unlink()
        test_directory.rmdir()
        passed = loaded == payload
        return CheckResult("UTF-8与目录读写", passed, f"测试目录：{workspace}")
    except Exception as exc:
        try:
            target = test_directory / "中文 空格 UTF-8.json"
            if target.exists():
                target.unlink()
            if test_directory.exists():
                test_directory.rmdir()
        except Exception:
            pass
        return CheckResult("UTF-8与目录读写", False, str(exc))


def check_sqlite() -> CheckResult:
    try:
        connection = sqlite3.connect(":memory:")
        connection.execute("CREATE TABLE smoke_test(value INTEGER, note TEXT NULL)")
        connection.execute("INSERT INTO smoke_test VALUES (?, ?)", (0, None))
        row = connection.execute("SELECT value, note FROM smoke_test").fetchone()
        connection.close()
        return CheckResult("SQLite选做路径", row == (0, None), f"读取结果：{row}")
    except Exception as exc:
        return CheckResult("SQLite选做路径", False, str(exc))


def check_paths(project_root: Path) -> CheckResult:
    required = (
        project_root / "student_package",
        project_root / "student_package" / "data",
        project_root / "student_package" / "schema",
        project_root / "student_package" / "templates",
        project_root / "student_package" / "src_skeleton",
        project_root / "ta_reference_package",
        project_root / "ta_reference_package" / "checkpoints",
        project_root / "ta_reference_package" / "reference_implementation",
        project_root / "ta_reference_package" / "expected_results",
        project_root / "ta_reference_package" / "case_manifest_internal.csv",
        project_root / "environment",
        project_root / "test_records",
        project_root / "manifest.csv",
        project_root / "release_notes.md",
        project_root / "student_package" / "data" / "raw_states.json",
        project_root / "student_package" / "data" / "partner_messages_sample.bin",
        project_root / "student_package" / "data" / "partner_messages_multitime.bin",
        project_root / "student_package" / "data" / "anomaly_cases.csv",
        project_root / "student_package" / "schema" / "teaching_message_spec.md",
        project_root / "student_package" / "schema" / "unified_model.json",
        project_root / "student_package" / "guides" / "opensky_interface_summary.md",
        project_root / "student_package" / "guides" / "m1_guided_questions.md",
        project_root / "ta_reference_package" / "checkpoints" / "official_decoded_multitime.csv",
        project_root / "ta_reference_package" / "checkpoints" / "official_current_situation.csv",
        project_root / "ta_reference_package" / "reference_implementation" / "run_all_reference.py",
        project_root / "environment" / "run_full_trial.py",
        project_root / "tests" / "test_reference_pipeline.py",
    )
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        return CheckResult("正式目录结构", False, "缺少：" + "；".join(missing))
    student_ta_leaks = list((project_root / "student_package").rglob("*reference_implementation*"))
    if student_ta_leaks:
        return CheckResult("正式目录结构", False, "学生包中发现助教参考实现路径")
    return CheckResult("正式目录结构", True, f"根目录：{project_root}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="检查暑期学校统一Python环境。")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="工作区根目录，默认取脚本上一级目录。",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = args.project_root.resolve()
    writable_root = project_root / "test_records"
    results = [check_python()]
    results.extend(
        [
            check_module("pandas", (2, 0), (3, 0)),
            check_module("matplotlib", (3, 7), (4, 0)),
        ]
    )
    results.extend(
        [
            check_utf8_and_write(writable_root),
            check_sqlite(),
            check_paths(project_root),
        ]
    )

    print(f"操作系统：{platform.platform()}")
    print(f"Python可执行文件：{sys.executable}")
    print(f"当前目录：{Path.cwd()}")
    print()
    for result in results:
        marker = "PASS" if result.passed else "FAIL"
        print(f"[{marker}] {result.name}：{result.detail}")

    failed = [result for result in results if not result.passed]
    print()
    print(f"总结：{len(results) - len(failed)}/{len(results)}项通过")
    if failed:
        print("请先修复失败项，再进行模块试跑。")
        return 1
    print("环境基础检查通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
