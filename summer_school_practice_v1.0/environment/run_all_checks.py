from __future__ import annotations

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
    checks = [
        run("环境检查", [sys.executable, "environment/environment_check.py"]),
        run("文件冒烟测试", [sys.executable, "environment/run_smoke_test.py"]),
        run("发布清单检查", [sys.executable, "environment/verify_manifest.py"]),
        run("自动化测试", [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"]),
        run("M2-M6端到端试跑", [sys.executable, "environment/run_full_trial.py"]),
    ]
    passed = sum(checks)
    print(f"\n总检查：{passed}/{len(checks)}项通过")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
