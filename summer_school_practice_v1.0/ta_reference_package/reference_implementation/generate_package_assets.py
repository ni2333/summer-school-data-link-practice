from __future__ import annotations

import json
from pathlib import Path

from practice_reference import (
    FRAME_SIZE,
    build_current_situation,
    build_tracks,
    check_quality,
    decode_message_stream,
    decode_position_message,
    encode_position_message,
    map_current_to_unified,
    parse_open_sky_payload,
    quantize_half_up,
    write_csv,
    write_ndjson,
)


ROOT = Path(__file__).resolve().parents[2]
STUDENT = ROOT / "student_package"
TA = ROOT / "ta_reference_package"


def vector(
    target_id: str,
    callsign: str | None,
    timestamp: int | None,
    lon: float | None,
    lat: float | None,
    altitude: float | None,
    on_ground: bool,
    speed: float | None,
    heading: float | None,
    vertical_rate: float | None,
    *,
    geo_altitude: float | None = None,
    last_contact: int | None = None,
) -> list[object]:
    return [
        target_id,
        callsign,
        "China",
        timestamp,
        last_contact if last_contact is not None else timestamp,
        lon,
        lat,
        altitude,
        on_ground,
        speed,
        heading,
        vertical_rate,
        None,
        geo_altitude,
        "1234",
        False,
        0,
    ]


def make_record(
    target_id: str,
    callsign: str | None,
    timestamp: int,
    lat: float | None,
    lon: float | None,
    altitude: float | None,
    speed: float | None,
    heading: float | None,
    vertical_rate: float | None,
    *,
    on_ground: bool = False,
    alt_type: str = "barometric",
    time_source: str = "position_time",
) -> dict[str, object]:
    return {
        "target_id": target_id,
        "callsign": callsign,
        "timestamp": timestamp,
        "timestamp_source": "LAST_CONTACT_FALLBACK" if time_source == "last_contact_fallback" else "POSITION_TIME",
        "time_source": time_source,
        "lat": lat,
        "lon": lon,
        "altitude": altitude,
        "speed": speed,
        "heading": heading,
        "vertical_rate": vertical_rate,
        "on_ground": on_ground,
        "alt_type": alt_type if altitude is not None else "unknown",
    }


def write_student_inputs() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    data_dir = STUDENT / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    raw_payload = {
        "time": 1710000120,
        "states": [
            vector("780abc", "CES1234 ", 1710000060, 121.4737, 31.2304, 9800.0, False, 230.5, 86.0, 0.0),
            vector("000001", "TEST0001", 1710000090, 0.0, 0.0, 0.0, True, 0.0, 0.0, 0.0),
            vector("780def", None, None, 120.1551, 30.2741, None, False, None, 270.0, -1.2, geo_altitude=7600.0, last_contact=1710000120),
            vector("780bad", "BADTIME", None, 116.4074, 39.9042, 10000.0, False, 240.0, 90.0, 0.0, last_contact=None),
            vector("780bee", "BADHEAD", 1710000120, 114.0579, 22.5431, 9000.0, False, 220.0, 360.0, 0.0),
        ],
    }
    (data_dir / "raw_states.json").write_text(json.dumps(raw_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    multitime_records = [
        make_record("000001", "TEST0001", 1710000060, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, on_ground=True),
        make_record("000001", "TEST0001", 1710000090, 0.01, 0.01, 10.0, 10.0, 45.0, 0.0),
        make_record("000001", "TEST0001", 1710000120, 0.02, 0.02, 20.0, 20.0, 90.0, 0.0),
        make_record("780abc", "CES1234", 1710000060, 31.2304, 121.4737, 9800.0, 230.5, 86.0, 0.0),
        make_record("780abc", "CES1234", 1710000090, 31.2404, 121.4837, 9850.0, 231.0, 87.0, 1.0),
        make_record("780abc", "CES1234", 1710000120, 31.2504, 121.4937, 9900.0, 231.5, 88.0, 1.5),
        make_record("780def", None, 1710000060, 30.2741, 120.1551, 7500.0, None, 270.0, -1.2, alt_type="geometric", time_source="last_contact_fallback"),
        make_record("780def", None, 1710000090, 30.2641, 120.1451, 7450.0, None, 269.0, -1.0, alt_type="geometric"),
        make_record("780def", None, 1710000120, None, None, 7400.0, None, 268.0, -0.8, alt_type="geometric"),
    ]
    frames = [encode_position_message(record, index) for index, record in enumerate(multitime_records, start=1)]
    stream = b"".join(frames)
    assert len(stream) == 9 * FRAME_SIZE
    (data_dir / "partner_messages_multitime.bin").write_bytes(stream)
    (data_dir / "partner_messages_sample.bin").write_bytes(b"".join(frames[:3]))
    (TA / "test_cases").mkdir(parents=True, exist_ok=True)
    (TA / "test_cases" / "partner_messages_incomplete_tail.bin").write_bytes(stream + b"\x01\x02\x03")

    anomaly_rows = [
        {"target_id": "780abc", "timestamp": 1710000110, "lat": 31.25, "lon": 121.49, "heading": 88.0, "message_valid": True},
        {"target_id": "780def", "timestamp": 1710000110, "lat": None, "lon": 120.15, "heading": 268.0, "message_valid": True},
        {"target_id": "000001", "timestamp": 1710000000, "lat": 0.02, "lon": 0.02, "heading": 90.0, "message_valid": True},
        {"target_id": "780aaa", "timestamp": 1710000100, "lat": 35.0, "lon": 110.0, "heading": 180.0, "message_valid": True},
        {"target_id": "780aaa", "timestamp": 1710000100, "lat": 35.1, "lon": 110.1, "heading": 181.0, "message_valid": True},
        {"target_id": "780bbb", "timestamp": 1710000110, "lat": 22.54, "lon": 114.05, "heading": 360.0, "message_valid": True},
    ]
    write_csv(data_dir / "anomaly_cases.csv", anomaly_rows)
    write_csv(data_dir / "anomaly_rules.csv", [
        {"rule_id": "R1", "alert_type": "POSITION_MISSING", "condition": "lat或lon为空", "severity": "HIGH"},
        {"rule_id": "R2", "alert_type": "DATA_DELAYED", "condition": "batch_time-record_time>60", "severity": "MEDIUM"},
        {"rule_id": "R3", "alert_type": "DUPLICATE_RECORD", "condition": "target_id和timestamp均相同", "severity": "MEDIUM"},
        {"rule_id": "R4", "alert_type": "HEADING_OUT_OF_RANGE", "condition": "heading非空且heading<0或heading>=360", "severity": "MEDIUM"},
    ])
    parsed, parse_errors = parse_open_sky_payload(raw_payload)
    assert len(parsed) == 3 and len(parse_errors) == 2
    return parsed, multitime_records


def write_reference_outputs(parsed: list[dict[str, object]]) -> None:
    checkpoints = TA / "checkpoints"
    expected = TA / "expected_results"
    checkpoints.mkdir(parents=True, exist_ok=True)
    expected.mkdir(parents=True, exist_ok=True)

    write_csv(checkpoints / "official_parsed_open_states.csv", parsed)
    stream = (STUDENT / "data" / "partner_messages_multitime.bin").read_bytes()
    decoded, stream_errors = decode_message_stream(stream)
    assert len(decoded) == 9 and not stream_errors and all(row["message_valid"] for row in decoded)
    write_csv(checkpoints / "official_decoded_multitime.csv", decoded)
    tracks = build_tracks(decoded)
    current = build_current_situation(decoded)
    assert len(tracks) == 9 and len(current) == 3 and all(row["track_length"] == 3 for row in current)
    write_csv(checkpoints / "official_current_situation.csv", current)
    write_csv(STUDENT / "data" / "partner_current_situation.csv", current)

    verified_mapping = [
        {"source_format": "OpenSky", "input_field": "target_id", "unified_field": "track_id", "mapping_rule": "六位小写十六进制字符串", "unit_conversion": "none", "null_strategy": "required", "evidence": "source_field_definitions.md", "verified": True},
        {"source_format": "OpenSky", "input_field": "latest_time", "unified_field": "timestamp", "mapping_rule": "直接映射", "unit_conversion": "seconds", "null_strategy": "required", "evidence": "source_field_definitions.md", "verified": True},
        {"source_format": "TeachingLink", "input_field": "latitude_code+validity_flags.bit0", "unified_field": "position.lat", "mapping_rule": "有效时code/(2^22-1)*180-90", "unit_conversion": "degree", "null_strategy": "无效位映射null", "evidence": "teaching_message_spec.md", "verified": True},
        {"source_format": "TeachingLink", "input_field": "longitude_code+validity_flags.bit1", "unified_field": "position.lon", "mapping_rule": "有效时code/(2^22-1)*360-180", "unit_conversion": "degree", "null_strategy": "无效位映射null", "evidence": "teaching_message_spec.md", "verified": True},
        {"source_format": "TeachingLink", "input_field": "altitude_code+validity_flags.bit2", "unified_field": "position.alt", "mapping_rule": "有效时code-1000", "unit_conversion": "meter", "null_strategy": "无效位映射null", "evidence": "teaching_message_spec.md", "verified": True},
        {"source_format": "TeachingLink", "input_field": "status_flags.bit2", "unified_field": "quality.time_source", "mapping_rule": "0=position_time,1=last_contact_fallback", "unit_conversion": "none", "null_strategy": "required", "evidence": "teaching_message_spec.md", "verified": True},
        {"source_format": "TeachingLink", "input_field": "message_valid", "unified_field": "quality.message_valid", "mapping_rule": "完整帧接收判据", "unit_conversion": "none", "null_strategy": "required", "evidence": "teaching_message_spec.md", "verified": True},
    ]
    write_csv(checkpoints / "official_verified_mapping.csv", verified_mapping)
    unified = [map_current_to_unified(row, "TeachingLink") for row in current]
    write_ndjson(checkpoints / "unified_message_reference.ndjson", unified)

    anomaly_rows = _read_csv_typed(STUDENT / "data" / "anomaly_cases.csv")
    alerts, quality = check_quality(anomaly_rows)
    write_csv(expected / "expected_alert_log.csv", alerts)
    write_csv(expected / "expected_quality_situation.csv", quality)
    counts = {
        "total_alerts": len(alerts),
        "HIGH": sum(row["severity"] == "HIGH" for row in alerts),
        "MEDIUM": sum(row["severity"] == "MEDIUM" for row in alerts),
        "by_type": {kind: sum(row["alert_type"] == kind for row in alerts) for kind in sorted({row["alert_type"] for row in alerts})},
    }
    (checkpoints / "expected_alert_counts.json").write_text(json.dumps(counts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    sample = (STUDENT / "data" / "partner_messages_sample.bin").read_bytes()
    sample_rows, _ = decode_message_stream(sample)
    hex_rows = []
    for index in range(0, len(sample), FRAME_SIZE):
        frame = sample[index:index + FRAME_SIZE]
        decoded_frame = decode_position_message(frame)
        hex_rows.append({
            "frame_no": index // FRAME_SIZE + 1,
            "target_id": decoded_frame["target_id"],
            "hex": frame.hex(),
            "checksum": decoded_frame["checksum"],
            "validity_flags": decoded_frame["validity_flags"],
            "status_flags": decoded_frame["status_flags"],
        })
    write_csv(expected / "sample_frame_reference.csv", hex_rows)
    write_csv(expected / "sample_decoded_reference.csv", sample_rows)

    boundary_values = [
        {"field": "latitude", "source": -90.0, "code": quantize_half_up(0.0), "decoded": -90.0},
        {"field": "latitude", "source": 90.0, "code": (1 << 22) - 1, "decoded": 90.0},
        {"field": "longitude", "source": -180.0, "code": 0, "decoded": -180.0},
        {"field": "longitude", "source": 180.0, "code": (1 << 22) - 1, "decoded": 180.0},
        {"field": "heading", "source": 0.0, "code": 0, "decoded": 0.0},
        {"field": "vertical_rate", "source": -327.68, "code": 0, "decoded": -327.68},
    ]
    write_csv(expected / "boundary_value_reference.csv", boundary_values)


def _read_csv_typed(path: Path) -> list[dict[str, object]]:
    import csv

    rows: list[dict[str, object]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            typed: dict[str, object] = dict(row)
            for field in ("timestamp", "latest_time"):
                if field in typed and str(typed[field]).strip():
                    typed[field] = int(str(typed[field]))
            for field in ("lat", "lon", "heading"):
                if field in typed:
                    typed[field] = None if not str(typed[field]).strip() else float(str(typed[field]))
            if "message_valid" in typed:
                typed["message_valid"] = str(typed["message_valid"]).lower() == "true"
            rows.append(typed)
    return rows


def main() -> int:
    parsed, _ = write_student_inputs()
    write_reference_outputs(parsed)
    print("实践包数据、检查点和预期结果生成完成。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
