from __future__ import annotations

import argparse
import json
from pathlib import Path

from practice_reference import (
    MAX_22BIT,
    build_current_situation,
    build_tracks,
    check_quality,
    decode_message_stream,
    decode_position_message,
    encode_position_message,
    map_current_to_unified,
    parse_open_sky_payload,
    read_csv,
    save_records_to_sqlite,
    write_csv,
    write_ndjson,
)


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STUDENT = ROOT / "student_package"
DEFAULT_OUTPUT = ROOT / "test_records" / "latest_reference_run"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="运行M2-M6助教参考处理链。")
    parser.add_argument("--student-root", type=Path, default=DEFAULT_STUDENT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--sqlite", action="store_true", help="同时验证SQLite选做路径")
    return parser.parse_args()


def clean_output(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    for path in output.iterdir():
        if path.is_file():
            path.unlink()


def tolerance(field: str) -> float:
    return {
        "lat": 180.0 / MAX_22BIT,
        "lon": 360.0 / MAX_22BIT,
        "altitude": 1.0,
        "speed": 0.1,
        "heading": 0.01,
        "vertical_rate": 0.01,
    }[field]


def typed_anomaly_rows(path: Path) -> list[dict[str, object]]:
    rows = read_csv(path)
    for row in rows:
        row["timestamp"] = int(row["timestamp"])
        for field in ("lat", "lon", "heading"):
            row[field] = None if row[field].strip() == "" else float(row[field])
        row["message_valid"] = row["message_valid"].lower() == "true"
    return rows


def run(student_root: Path, output: Path, use_sqlite: bool) -> dict[str, object]:
    clean_output(output)
    payload = json.loads((student_root / "data" / "raw_states.json").read_text(encoding="utf-8"))
    parsed, validation_errors = parse_open_sky_payload(payload)
    write_csv(output / "parsed_open_states.csv", parsed)

    encoded_frames = []
    decoded_frames = []
    roundtrip_rows = []
    for sequence, record in enumerate(parsed, start=1):
        frame = encode_position_message(record, sequence)
        encoded_frames.append(frame)
        decoded = decode_position_message(frame)
        decoded_frames.append(decoded)
        for field in ("lat", "lon", "altitude", "speed", "heading", "vertical_rate"):
            source_value = record.get(field)
            decoded_value = decoded.get(field)
            source_valid = source_value is not None
            decoded_valid = decoded_value is not None
            absolute_error = None if not source_valid else abs(float(source_value) - float(decoded_value))
            allowed = tolerance(field)
            roundtrip_rows.append({
                "field": f"{record['target_id']}.{field}",
                "source_value": source_value,
                "source_valid": source_valid,
                "protocol_code": decoded.get({"lat": "latitude_code", "lon": "longitude_code"}.get(field, field + "_code")),
                "flag_bit": {"lat": 0, "lon": 1, "altitude": 2, "speed": 3, "heading": 4, "vertical_rate": 5}[field],
                "decoded_value": decoded_value,
                "decoded_valid": decoded_valid,
                "absolute_error/tolerance": "missing" if absolute_error is None else f"{absolute_error:.9f}/{allowed:.9f}",
                "passed": source_valid == decoded_valid and (absolute_error is None or absolute_error <= allowed + 1e-12),
            })
    (output / "encoded_messages.bin").write_bytes(b"".join(encoded_frames))
    write_csv(output / "decoded_partner_states.csv", decoded_frames)
    write_csv(output / "validation_log.csv", validation_errors, ["record_no", "target_id", "stage", "field", "problem_type", "value", "description"])
    write_csv(output / "roundtrip_report.csv", roundtrip_rows)

    multitime_bytes = (student_root / "data" / "partner_messages_multitime.bin").read_bytes()
    decoded_multitime, stream_errors = decode_message_stream(multitime_bytes)
    write_csv(output / "decoded_multitime.csv", decoded_multitime)
    write_csv(output / "stream_validation_log.csv", stream_errors, ["record_no", "target_id", "stage", "field", "problem_type", "value", "description"])
    tracks = build_tracks(decoded_multitime)
    current = build_current_situation(decoded_multitime)
    write_csv(output / "track_table.csv", tracks)
    write_csv(output / "current_situation.csv", current)

    sqlite_rows = None
    if use_sqlite:
        sqlite_rows = save_records_to_sqlite(
            decoded_multitime,
            output / "states.db",
            student_root / "schema" / "optional_db_schema.sql",
        )

    open_sky_current = []
    for record in parsed:
        row = dict(record)
        row["latest_time"] = row["timestamp"]
        row["message_valid"] = True
        open_sky_current.append(row)
    unified = [map_current_to_unified(row, "OpenSky") for row in open_sky_current]
    unified.extend(map_current_to_unified(row, "TeachingLink") for row in current)
    write_ndjson(output / "unified_situation.ndjson", unified)

    verified_mapping = read_csv(ROOT / "ta_reference_package" / "checkpoints" / "official_verified_mapping.csv")
    write_csv(output / "verified_mapping_table.csv", verified_mapping)

    anomaly_rows = typed_anomaly_rows(student_root / "data" / "anomaly_cases.csv")
    alerts, quality = check_quality(anomaly_rows)
    write_csv(output / "alert_log.csv", alerts)
    write_csv(output / "quality_situation.csv", quality)

    summary = {
        "parsed_records": len(parsed),
        "parse_validation_errors": len(validation_errors),
        "encoded_frames": len(encoded_frames),
        "roundtrip_failures": sum(not row["passed"] for row in roundtrip_rows),
        "multitime_frames": len(decoded_multitime),
        "stream_errors": len(stream_errors),
        "targets": len(current),
        "track_rows": len(tracks),
        "track_lengths": {row["target_id"]: row["track_length"] for row in current},
        "unified_messages": len(unified),
        "alerts": len(alerts),
        "high_alerts": sum(row["severity"] == "HIGH" for row in alerts),
        "medium_alerts": sum(row["severity"] == "MEDIUM" for row in alerts),
        "sqlite_rows": sqlite_rows,
    }
    (output / "run_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    args = parse_args()
    summary = run(args.student_root.resolve(), args.output_dir.resolve(), args.sqlite)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    failed = (
        summary["roundtrip_failures"] != 0
        or summary["stream_errors"] != 0
        or summary["multitime_frames"] != 9
        or summary["targets"] != 3
        or summary["alerts"] != 5
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
