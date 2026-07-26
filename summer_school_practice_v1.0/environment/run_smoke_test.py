from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SmokeResult:
    name: str
    passed: bool
    detail: str


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "smoke_data"


def read_json() -> SmokeResult:
    path = DATA / "sample.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        passed = value.get("name") == "环境冒烟测试" and value.get("zero") == 0
        return SmokeResult("JSON读取", passed, f"{path.name}，字段数={len(value)}")
    except Exception as exc:
        return SmokeResult("JSON读取", False, str(exc))


def read_binary() -> SmokeResult:
    path = DATA / "sample_frame.bin"
    try:
        value = path.read_bytes()
        passed = len(value) == 41
        return SmokeResult("二进制读取", passed, f"{path.name}，字节数={len(value)}，要求=41")
    except Exception as exc:
        return SmokeResult("二进制读取", False, str(exc))


def read_csv() -> SmokeResult:
    path = DATA / "sample.csv"
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        passed = len(rows) == 2 and rows[0]["target_id"] == "000001"
        return SmokeResult("CSV读取", passed, f"{path.name}，记录数={len(rows)}")
    except Exception as exc:
        return SmokeResult("CSV读取", False, str(exc))


def read_ndjson() -> SmokeResult:
    path = DATA / "sample.ndjson"
    try:
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        passed = len(rows) == 2 and rows[1]["quality"]["message_valid"] is True
        return SmokeResult("NDJSON读取", passed, f"{path.name}，对象数={len(rows)}")
    except Exception as exc:
        return SmokeResult("NDJSON读取", False, str(exc))


def main() -> int:
    results = [read_json(), read_binary(), read_csv(), read_ndjson()]
    for result in results:
        marker = "PASS" if result.passed else "FAIL"
        print(f"[{marker}] {result.name}：{result.detail}")
    failed = [result for result in results if not result.passed]
    print(f"总结：{len(results) - len(failed)}/{len(results)}项通过")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
