from __future__ import annotations

import argparse
import csv
import json
import math
import sqlite3
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "ta_reference_package" / "reference_implementation"
sys.path.insert(0, str(REFERENCE))

from practice_reference import (  # noqa: E402
    FRAME_SIZE,
    build_current_situation,
    decode_position_message,
    encode_position_message,
    parse_open_sky_payload,
    save_records_to_sqlite,
    write_csv,
)


DATA_DIR = ROOT / "student_package" / "data" / "opensky_real"
DEFAULT_OUTPUT = ROOT / "experiment" / "output"

SOURCE_FIELDS = [
    "snapshot_index", "target_id", "callsign", "timestamp", "lat", "lon",
    "altitude", "alt_type", "speed", "heading", "vertical_rate", "on_ground",
]
TRANSMISSION_FIELDS = [
    "frame_no", "target_id", "timestamp", "frame_bytes", "checksum_valid",
    "receiver_target_count",
]
ERROR_FIELDS = [
    "frame_no", "target_id", "timestamp", "source_lat", "decoded_lat",
    "source_lon", "decoded_lon", "horizontal_error_m", "source_altitude_m",
    "decoded_altitude_m", "altitude_error_m", "source_speed_m_s",
    "decoded_speed_m_s", "speed_error_m_s", "source_heading_deg",
    "decoded_heading_deg", "heading_error_deg", "source_vertical_rate_m_s",
    "decoded_vertical_rate_m_s", "vertical_rate_error_m_s",
]
SITUATION_FIELDS = [
    "target_id", "callsign", "latest_time", "lat", "lon", "altitude", "speed",
    "heading", "vertical_rate", "on_ground", "track_length", "alt_type",
    "time_source", "message_valid", "status_flags", "validity_flags",
    "latitude_code", "longitude_code", "altitude_code", "speed_code",
    "heading_code", "vertical_rate_code",
]


def _optional_error(source: Any, decoded: Any) -> float | None:
    if source is None or decoded is None:
        return None
    return abs(float(decoded) - float(source))


def _horizontal_error_m(source: dict[str, Any], decoded: dict[str, Any]) -> float | None:
    if source.get("lat") is None or source.get("lon") is None:
        return None
    if decoded.get("lat") is None or decoded.get("lon") is None:
        return None
    radius_m = 6_371_008.8
    lat1 = math.radians(float(source["lat"]))
    lat2 = math.radians(float(decoded["lat"]))
    delta_lat = lat2 - lat1
    delta_lon = math.radians(float(decoded["lon"]) - float(source["lon"]))
    haversine = math.sin(delta_lat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    return 2 * radius_m * math.asin(min(1.0, math.sqrt(haversine)))


def load_source_records(data_dir: Path = DATA_DIR) -> list[dict[str, Any]]:
    provenance = json.loads((data_dir / "provenance.json").read_text(encoding="utf-8"))
    records: list[dict[str, Any]] = []
    for source in provenance["sources"]:
        payload = json.loads((data_dir / source["file"]).read_text(encoding="utf-8"))
        parsed, errors = parse_open_sky_payload(payload)
        if errors:
            raise RuntimeError(f"OpenSky 快照 {source['snapshot_index']} 有 {len(errors)} 条解析错误")
        for record in parsed:
            if record.get("lat") is None or record.get("lon") is None:
                continue
            record["snapshot_index"] = int(source["snapshot_index"])
            records.append(record)
    return records


def select_records(records: list[dict[str, Any]], target_limit: int) -> list[dict[str, Any]]:
    if target_limit < 1:
        raise ValueError("目标数量必须大于等于 1")
    counts = Counter(str(row["target_id"]) for row in records)
    ranked = sorted(counts, key=lambda target: (-counts[target], target))
    chosen = set(ranked[:target_limit])
    return sorted(
        (row for row in records if str(row["target_id"]) in chosen),
        key=lambda row: (int(row["timestamp"]), str(row["target_id"]), int(row["snapshot_index"])),
    )


def _metric(rows: list[dict[str, Any]], field: str, function) -> float:
    values = [float(row[field]) for row in rows if row[field] is not None]
    return function(values) if values else 0.0


def run_experiment(output_dir: Path, target_limit: int = 10, data_dir: Path = DATA_DIR) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    provenance = json.loads((data_dir / "provenance.json").read_text(encoding="utf-8"))
    source_records = select_records(load_source_records(data_dir), target_limit)
    if not source_records:
        raise RuntimeError("没有可用于实验的 OpenSky 有效位置记录")

    # 接收端从空态势开始；随后每收到一帧就更新一次当前态势。
    write_csv(output_dir / "receiver_situation_initial.csv", [], SITUATION_FIELDS)
    frames: list[bytes] = []
    decoded_records: list[dict[str, Any]] = []
    transmission_rows: list[dict[str, Any]] = []
    error_rows: list[dict[str, Any]] = []

    for frame_no, source in enumerate(source_records, start=1):
        frame = encode_position_message(source, frame_no)
        decoded = decode_position_message(frame)
        frames.append(frame)
        decoded_records.append(decoded)
        current = build_current_situation(decoded_records)
        transmission_rows.append({
            "frame_no": frame_no,
            "target_id": decoded["target_id"],
            "timestamp": decoded["timestamp"],
            "frame_bytes": len(frame),
            "checksum_valid": decoded["checksum"] == decoded["expected_checksum"],
            "receiver_target_count": len(current),
        })
        error_rows.append({
            "frame_no": frame_no,
            "target_id": source["target_id"],
            "timestamp": source["timestamp"],
            "source_lat": source.get("lat"),
            "decoded_lat": decoded.get("lat"),
            "source_lon": source.get("lon"),
            "decoded_lon": decoded.get("lon"),
            "horizontal_error_m": _horizontal_error_m(source, decoded),
            "source_altitude_m": source.get("altitude"),
            "decoded_altitude_m": decoded.get("altitude"),
            "altitude_error_m": _optional_error(source.get("altitude"), decoded.get("altitude")),
            "source_speed_m_s": source.get("speed"),
            "decoded_speed_m_s": decoded.get("speed"),
            "speed_error_m_s": _optional_error(source.get("speed"), decoded.get("speed")),
            "source_heading_deg": source.get("heading"),
            "decoded_heading_deg": decoded.get("heading"),
            "heading_error_deg": _optional_error(source.get("heading"), decoded.get("heading")),
            "source_vertical_rate_m_s": source.get("vertical_rate"),
            "decoded_vertical_rate_m_s": decoded.get("vertical_rate"),
            "vertical_rate_error_m_s": _optional_error(source.get("vertical_rate"), decoded.get("vertical_rate")),
        })

    current_situation = build_current_situation(decoded_records)
    write_csv(output_dir / "selected_source_states.csv", source_records, SOURCE_FIELDS)
    (output_dir / "transmitted_frames.bin").write_bytes(b"".join(frames))
    write_csv(output_dir / "transmission_log.csv", transmission_rows, TRANSMISSION_FIELDS)
    write_csv(output_dir / "decoded_states.csv", decoded_records)
    write_csv(output_dir / "receiver_situation_final.csv", current_situation, SITUATION_FIELDS)
    write_csv(output_dir / "precision_error_report.csv", error_rows, ERROR_FIELDS)

    sqlite_rows = save_records_to_sqlite(
        decoded_records,
        output_dir / "received_states.db",
        ROOT / "student_package" / "schema" / "optional_db_schema.sql",
    )
    connection = sqlite3.connect(output_dir / "received_states.db")
    try:
        sqlite_valid_rows = int(connection.execute("SELECT COUNT(*) FROM state_record WHERE message_valid=1").fetchone()[0])
    finally:
        connection.close()

    summary = {
        "data_provider": "The OpenSky Network",
        "source_snapshot_count": int(provenance["snapshot_count"]),
        "source_record_count": int(provenance["normalized_record_count"]),
        "selected_target_count": len({row["target_id"] for row in source_records}),
        "selected_record_count": len(source_records),
        "frame_size_bytes": FRAME_SIZE,
        "sent_frame_count": len(frames),
        "valid_received_frame_count": sum(bool(row["message_valid"]) for row in decoded_records),
        "final_receiver_target_count": len(current_situation),
        "sqlite_row_count": sqlite_rows,
        "sqlite_valid_row_count": sqlite_valid_rows,
        "max_horizontal_error_m": _metric(error_rows, "horizontal_error_m", max),
        "mean_horizontal_error_m": _metric(error_rows, "horizontal_error_m", lambda values: sum(values) / len(values)),
        "max_altitude_error_m": _metric(error_rows, "altitude_error_m", max),
        "max_speed_error_m_s": _metric(error_rows, "speed_error_m_s", max),
        "max_heading_error_deg": _metric(error_rows, "heading_error_deg", max),
        "max_vertical_rate_error_m_s": _metric(error_rows, "vertical_rate_error_m_s", max),
        "all_frames_valid": all(bool(row["message_valid"]) for row in decoded_records),
    }
    (output_dir / "experiment_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="运行 OpenSky → TeachingLink → 接收态势端到端实验")
    parser.add_argument("--targets", type=int, default=10, help="选择观测次数最多的目标数量，默认 10")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="实验输出目录")
    args = parser.parse_args()
    summary = run_experiment(args.output, args.targets)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["all_frames_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
