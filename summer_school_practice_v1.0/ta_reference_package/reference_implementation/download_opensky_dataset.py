from __future__ import annotations

import argparse
import csv
import hashlib
import json
import time
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from practice_reference import (
    PracticeDataError,
    decode_position_message,
    encode_position_message,
    parse_open_sky_payload,
)


API_BASE = "https://opensky-network.org/api/states/all"
API_DOCUMENTATION = "https://openskynetwork.github.io/opensky-api/rest.html"
DEFAULT_BBOX = {"lamin": 45.5, "lomin": 5.0, "lamax": 49.5, "lomax": 12.0}
PACKAGE_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PACKAGE_ROOT / "student_package" / "data" / "opensky_real"
ROUNDTRIP_OUTPUT = PACKAGE_ROOT / "ta_reference_package" / "expected_results" / "opensky_real_roundtrip_report.csv"

NORMALIZED_FIELDS = [
    "snapshot_index", "snapshot_time", "vector_index", "icao24", "callsign",
    "origin_country", "time_position", "last_contact", "longitude", "latitude",
    "baro_altitude_m", "on_ground", "velocity_m_s", "true_track_deg",
    "vertical_rate_m_s", "sensors", "geo_altitude_m", "squawk", "spi",
    "position_source", "category",
]
ROUNDTRIP_FIELDS = [
    "snapshot_index", "vector_index", "target_id", "timestamp", "outcome",
    "problem_type", "message_seq", "message_valid", "lat_error_deg", "lon_error_deg",
]


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def iso_utc(epoch_seconds: int | float) -> str:
    return datetime.fromtimestamp(epoch_seconds, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def value_at(vector: list[Any], index: int) -> Any:
    return vector[index] if index < len(vector) else None


def api_url(bbox: dict[str, float]) -> str:
    return f"{API_BASE}?{urllib.parse.urlencode(bbox)}"


def fetch(url: str) -> tuple[bytes, dict[str, Any], dict[str, str]]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "summer-school-data-link-practice/1.0 educational"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        body = response.read()
        headers = {
            "content_type": response.headers.get("Content-Type", ""),
            "rate_limit_remaining": response.headers.get("X-Rate-Limit-Remaining", ""),
        }
    payload = json.loads(body)
    if not isinstance(payload, dict) or not isinstance(payload.get("time"), int):
        raise RuntimeError("OpenSky 响应缺少整数 time")
    if not isinstance(payload.get("states"), list) or not payload["states"]:
        raise RuntimeError("OpenSky 响应没有状态向量，请更换时间或边界框后重试")
    return body, payload, headers


def normalized_row(snapshot_index: int, snapshot_time: int, vector_index: int, vector: list[Any]) -> dict[str, Any]:
    return {
        "snapshot_index": snapshot_index,
        "snapshot_time": snapshot_time,
        "vector_index": vector_index,
        "icao24": value_at(vector, 0),
        "callsign": value_at(vector, 1),
        "origin_country": value_at(vector, 2),
        "time_position": value_at(vector, 3),
        "last_contact": value_at(vector, 4),
        "longitude": value_at(vector, 5),
        "latitude": value_at(vector, 6),
        "baro_altitude_m": value_at(vector, 7),
        "on_ground": value_at(vector, 8),
        "velocity_m_s": value_at(vector, 9),
        "true_track_deg": value_at(vector, 10),
        "vertical_rate_m_s": value_at(vector, 11),
        "sensors": json.dumps(value_at(vector, 12), ensure_ascii=False),
        "geo_altitude_m": value_at(vector, 13),
        "squawk": value_at(vector, 14),
        "spi": value_at(vector, 15),
        "position_source": value_at(vector, 16),
        "category": value_at(vector, 17),
    }


def write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def build_dataset(
    output_dir: Path,
    roundtrip_output: Path,
    snapshots: int,
    interval: float,
    bbox: dict[str, float],
) -> dict[str, Any]:
    source_dir = output_dir / "source"
    source_dir.mkdir(parents=True, exist_ok=True)
    url = api_url(bbox)
    normalized: list[dict[str, Any]] = []
    frames: list[bytes] = []
    roundtrip_rows: list[dict[str, Any]] = []
    source_metadata: list[dict[str, Any]] = []
    parse_error_count = 0
    parsed_record_count = 0
    target_observations: Counter[str] = Counter()

    for snapshot_index in range(1, snapshots + 1):
        body, payload, response_headers = fetch(url)
        filename = f"opensky_central_europe_snapshot_{snapshot_index:02d}.json"
        source_path = source_dir / filename
        source_path.write_bytes(body)
        states = payload["states"]
        source_metadata.append({
            "snapshot_index": snapshot_index,
            "file": f"source/{filename}",
            "snapshot_time": payload["time"],
            "snapshot_time_utc": iso_utc(payload["time"]),
            "state_count": len(states),
            "sha256": sha256_bytes(body),
            "content_type": response_headers["content_type"],
            "rate_limit_remaining_after_request": response_headers["rate_limit_remaining"],
        })
        for vector_index, vector in enumerate(states, start=1):
            if not isinstance(vector, list):
                raise RuntimeError(f"快照 {snapshot_index} 的状态向量 {vector_index} 不是数组")
            normalized.append(normalized_row(snapshot_index, payload["time"], vector_index, vector))

        parsed, parse_errors = parse_open_sky_payload(payload)
        parsed_record_count += len(parsed)
        parse_error_count += len(parse_errors)
        parse_errors_by_record = {int(error["record_no"]): error for error in parse_errors}
        parsed_by_record = {int(record["record_no"]): record for record in parsed}
        for vector_index in range(1, len(states) + 1):
            if vector_index in parse_errors_by_record:
                error = parse_errors_by_record[vector_index]
                roundtrip_rows.append({
                    "snapshot_index": snapshot_index,
                    "vector_index": vector_index,
                    "target_id": error.get("target_id"),
                    "timestamp": "",
                    "outcome": "PARSE_REJECTED",
                    "problem_type": error.get("problem_type"),
                    "message_seq": "",
                    "message_valid": "",
                    "lat_error_deg": "",
                    "lon_error_deg": "",
                })
                continue
            record = parsed_by_record[vector_index]
            target_observations[str(record["target_id"])] += 1
            if record.get("lat") is None or record.get("lon") is None:
                roundtrip_rows.append({
                    "snapshot_index": snapshot_index,
                    "vector_index": vector_index,
                    "target_id": record["target_id"],
                    "timestamp": record["timestamp"],
                    "outcome": "NO_POSITION_SKIPPED",
                    "problem_type": "",
                    "message_seq": "",
                    "message_valid": "",
                    "lat_error_deg": "",
                    "lon_error_deg": "",
                })
                continue
            try:
                frame = encode_position_message(record, len(frames) + 1)
                decoded = decode_position_message(frame)
            except PracticeDataError as exc:
                roundtrip_rows.append({
                    "snapshot_index": snapshot_index,
                    "vector_index": vector_index,
                    "target_id": record["target_id"],
                    "timestamp": record["timestamp"],
                    "outcome": "ENCODE_REJECTED",
                    "problem_type": exc.problem_type,
                    "message_seq": "",
                    "message_valid": "",
                    "lat_error_deg": "",
                    "lon_error_deg": "",
                })
                continue
            frames.append(frame)
            roundtrip_rows.append({
                "snapshot_index": snapshot_index,
                "vector_index": vector_index,
                "target_id": record["target_id"],
                "timestamp": record["timestamp"],
                "outcome": "ROUNDTRIP_OK" if decoded["message_valid"] else "DECODE_REJECTED",
                "problem_type": "" if decoded["message_valid"] else "|".join(decoded["validation_errors"]),
                "message_seq": decoded["message_seq"],
                "message_valid": decoded["message_valid"],
                "lat_error_deg": abs(float(decoded["lat"]) - float(record["lat"])),
                "lon_error_deg": abs(float(decoded["lon"]) - float(record["lon"])),
            })
        if snapshot_index < snapshots:
            time.sleep(interval)

    if not frames:
        raise RuntimeError("真实快照中没有可完成 TeachingLink 往返的有位置记录")
    write_csv(output_dir / "normalized_state_vectors.csv", NORMALIZED_FIELDS, normalized)
    write_csv(roundtrip_output, ROUNDTRIP_FIELDS, roundtrip_rows)
    (output_dir / "opensky_real_messages.bin").write_bytes(b"".join(frames))
    repeated_targets = sorted(target for target, count in target_observations.items() if count >= 2)
    provenance = {
        "dataset_name": "OpenSky Central Europe three-snapshot teaching dataset",
        "provider": "The OpenSky Network",
        "source_url": url,
        "api_documentation": API_DOCUMENTATION,
        "downloaded_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "query_bbox_wgs84": bbox,
        "anonymous_api": True,
        "snapshot_count": snapshots,
        "requested_interval_seconds": interval,
        "sources": source_metadata,
        "normalized_record_count": len(normalized),
        "parsed_record_count": parsed_record_count,
        "parse_error_count": parse_error_count,
        "encoded_frame_count": len(frames),
        "repeated_targets": repeated_targets,
        "no_interpolation": True,
        "no_synthetic_values": True,
    }
    (output_dir / "provenance.json").write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return provenance


def main() -> int:
    parser = argparse.ArgumentParser(description="Download traceable real OpenSky state-vector snapshots.")
    parser.add_argument("--output", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--roundtrip-output", type=Path, default=ROUNDTRIP_OUTPUT)
    parser.add_argument("--snapshots", type=int, default=3)
    parser.add_argument("--interval", type=float, default=11.0)
    parser.add_argument("--lamin", type=float, default=DEFAULT_BBOX["lamin"])
    parser.add_argument("--lomin", type=float, default=DEFAULT_BBOX["lomin"])
    parser.add_argument("--lamax", type=float, default=DEFAULT_BBOX["lamax"])
    parser.add_argument("--lomax", type=float, default=DEFAULT_BBOX["lomax"])
    args = parser.parse_args()
    if args.snapshots < 1:
        parser.error("--snapshots 必须大于等于 1")
    if args.interval < 10 and args.snapshots > 1:
        parser.error("匿名接口时间分辨率为 10 秒，多快照间隔不得小于 10 秒")
    bbox = {"lamin": args.lamin, "lomin": args.lomin, "lamax": args.lamax, "lomax": args.lomax}
    if not (-90 <= args.lamin < args.lamax <= 90 and -180 <= args.lomin < args.lomax <= 180):
        parser.error("边界框范围或顺序无效")
    provenance = build_dataset(args.output, args.roundtrip_output, args.snapshots, args.interval, bbox)
    print(json.dumps({
        "output": str(args.output),
        "roundtrip_output": str(args.roundtrip_output),
        "snapshots": provenance["snapshot_count"],
        "records": provenance["normalized_record_count"],
        "encoded_frames": provenance["encoded_frame_count"],
        "repeated_targets": len(provenance["repeated_targets"]),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
