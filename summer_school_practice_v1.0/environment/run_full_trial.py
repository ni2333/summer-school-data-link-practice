from __future__ import annotations

import csv
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "ta_reference_package" / "reference_implementation"
sys.path.insert(0, str(REFERENCE))

from run_all_reference import run  # noqa: E402


def csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    output = ROOT / "test_records" / ".last_trial_output"
    checks: list[dict[str, object]] = []

    def check(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "passed": passed, "detail": detail})

    try:
        summary = run(ROOT / "student_package", output, use_sqlite=True)
        check("端到端参考链", True, "M2-M6运行完成")
    except Exception as exc:
        summary = {}
        check("端到端参考链", False, repr(exc))

    required_outputs = [
        "parsed_open_states.csv", "encoded_messages.bin", "decoded_partner_states.csv", "validation_log.csv",
        "roundtrip_report.csv", "decoded_multitime.csv", "track_table.csv", "current_situation.csv", "states.db",
        "verified_mapping_table.csv", "unified_situation.ndjson", "alert_log.csv", "quality_situation.csv", "run_summary.json",
    ]
    missing = [name for name in required_outputs if not (output / name).exists()]
    check("M6关键成果齐全", not missing, "缺少：" + ", ".join(missing) if missing else f"{len(required_outputs)}项齐全")

    try:
        official_current = csv_rows(ROOT / "ta_reference_package" / "checkpoints" / "official_current_situation.csv")
        actual_current = csv_rows(output / "current_situation.csv")
        official_keys = {(row["target_id"], row["track_length"]) for row in official_current}
        actual_keys = {(row["target_id"], row["track_length"]) for row in actual_current}
        check("M3官方检查点", official_keys == actual_keys, f"实际={sorted(actual_keys)}")
    except Exception as exc:
        check("M3官方检查点", False, repr(exc))

    try:
        expected_counts = json.loads((ROOT / "ta_reference_package" / "checkpoints" / "expected_alert_counts.json").read_text(encoding="utf-8"))
        actual_alerts = csv_rows(output / "alert_log.csv")
        actual_counts = {
            "total_alerts": len(actual_alerts),
            "HIGH": sum(row["severity"] == "HIGH" for row in actual_alerts),
            "MEDIUM": sum(row["severity"] == "MEDIUM" for row in actual_alerts),
        }
        comparable = {key: expected_counts[key] for key in actual_counts}
        check("M5预期告警", actual_counts == comparable, f"实际={actual_counts}")
    except Exception as exc:
        check("M5预期告警", False, repr(exc))

    try:
        ndjson = [json.loads(line) for line in (output / "unified_situation.ndjson").read_text(encoding="utf-8").splitlines() if line.strip()]
        valid = len(ndjson) == 6 and all("quality" in row and "message_valid" in row["quality"] for row in ndjson)
        check("M4统一消息可重读", valid, f"对象数={len(ndjson)}")
    except Exception as exc:
        check("M4统一消息可重读", False, repr(exc))

    expected_summary = {
        "parsed_records": 3,
        "parse_validation_errors": 2,
        "encoded_frames": 3,
        "roundtrip_failures": 0,
        "multitime_frames": 9,
        "stream_errors": 0,
        "targets": 3,
        "track_rows": 9,
        "alerts": 5,
        "high_alerts": 1,
        "medium_alerts": 4,
        "sqlite_rows": 9,
    }
    summary_ok = all(summary.get(key) == value for key, value in expected_summary.items())
    check("冻结指标", summary_ok, json.dumps(summary, ensure_ascii=False, sort_keys=True))

    report = {
        "python": sys.version,
        "project_root": str(ROOT),
        "summary": summary,
        "checks": checks,
        "passed": all(item["passed"] for item in checks),
    }
    report_path = ROOT / "test_records" / "latest_trial_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for item in checks:
        print(f"[{'PASS' if item['passed'] else 'FAIL'}] {item['name']}：{item['detail']}")
    print(f"试跑报告：{report_path}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
