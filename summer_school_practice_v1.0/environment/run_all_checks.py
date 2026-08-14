from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(name: str, command: list[str]) -> bool:
    print(f"\n=== {name} ===", flush=True)
    completed = subprocess.run(command, cwd=ROOT, check=False)
    print(f"{name} exit={completed.returncode}", flush=True)
    return completed.returncode == 0


def main() -> int:
    required_checks = [
        run("环境检查", [sys.executable, "environment/environment_check.py"]),
        run("文件冒烟测试", [sys.executable, "environment/run_smoke_test.py"]),
        run("文件清单检查", [sys.executable, "environment/verify_manifest.py"]),
        run("自动化测试", [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"]),
        run("M2-M6 CSV必做路径试跑", [sys.executable, "environment/run_full_trial.py"]),
        run("OpenSky完整实验试跑", [sys.executable, "experiment/run_opensky_experiment.py", "--targets", "10"]),
    ]
    optional_checks = []
    if importlib.util.find_spec("sqlite3") is None:
        print("\n=== SQLite选做路径试跑 ===")
        print("[WARN] 当前Python不提供sqlite3；按CSV必做路径继续")
    else:
        optional_checks.append(
            run("SQLite选做路径试跑", [sys.executable, "environment/run_full_trial.py", "--sqlite"])
        )
    passed = sum(required_checks)
    print(f"\n必做总检查：{passed}/{len(required_checks)}项通过")
    if optional_checks:
        print(f"选做总检查：{sum(optional_checks)}/{len(optional_checks)}项通过；失败不阻断必做路径")
    return 0 if all(required_checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
