from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from practice_reference import decode_message_stream, encode_position_message


API_URL = "https://api.adsb.lol/v2/lat/35.6762/lon/139.6503/dist/100"
LICENSE_URL = "https://opendatacommons.org/licenses/odbl/1-0/"
PACKAGE_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PACKAGE_ROOT / "student_package" / "data" / "real_adsb"
SOURCE_DIR = OUTPUT_DIR / "source"
SNAPSHOT_COUNT = 3
INTERVAL_SECONDS = 10.0
TARGET_COUNT = 3

NORMALIZED_FIELDS = [
    "snapshot_index", "captured_at_utc", "response_now_ms", "target_id", "callsign",
    "lat_deg", "lon_deg", "alt_baro_ft", "alt_geom_ft", "ground_speed_kt",
    "track_deg", "baro_rate_ft_min", "geom_rate_ft_min", "seen_pos_s", "db_flags",
]
TRACK_FIELDS = [
    "snapshot_index", "captured_at_utc", "target_id", "callsign", "timestamp_utc",
    "timestamp_unix", "lat_deg", "lon_deg", "altitude_m", "altitude_source",
    "speed_m_s", "heading_deg", "vertical_rate_m_s", "vertical_rate_source",
    "on_ground", "source_provider",
]
DECODED_FIELDS = [
    "message_seq", "target_id", "callsign", "timestamp", "lat", "lon", "altitude",
    "alt_type", "speed", "heading", "vertical_rate", "on_ground", "message_valid",
]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def write_bytes(path: Path, data: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return sha256_bytes(data)


def fetch_snapshot(url: str) -> tuple[bytes, dict[str, Any]]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "summer-school-data-link-practice/1.0 (+GitHub educational dataset)"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        body = response.read()
    payload = json.loads(body)
    if not isinstance(payload, dict) or not isinstance(payload.get("ac"), list):
        raise RuntimeError("ADSB.lol 响应不包含预期的 ac 数组")
    return body, payload


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def is_eligible_aircraft(row: dict[str, Any]) -> bool:
    target_id = str(row.get("hex") or "").lower()
    callsign = str(row.get("flight") or "").strip()
    flags = row.get("dbFlags")
    return (
        re.fullmatch(r"[0-9a-f]{6}", target_id) is not None
        and bool(callsign)
        and len(callsign.encode("ascii", errors="ignore")) == len(callsign)
        and len(callsign.encode("ascii")) <= 8
        and flags in (None, 0)
        and is_number(row.get("lat"))
        and is_number(row.get("lon"))
    )


def has_protocol_fields(row: dict[str, Any]) -> bool:
    altitude = row.get("alt_geom") if is_number(row.get("alt_geom")) else row.get("alt_baro")
    rate = row.get("geom_rate") if is_number(row.get("geom_rate")) else row.get("baro_rate")
    track = row.get("track")
    return (
        is_eligible_aircraft(row)
        and is_number(altitude)
        and is_number(row.get("gs"))
        and is_number(track)
        and 0.0 <= float(track) < 359.995
        and is_number(rate)
        and is_number(row.get("seen_pos"))
    )


def iso_utc(epoch_seconds: float) -> str:
    return datetime.fromtimestamp(epoch_seconds, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def normalized_row(index: int, payload: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    return {
        "snapshot_index": index,
        "captured_at_utc": iso_utc(float(payload["now"]) / 1000.0),
        "response_now_ms": payload["now"],
        "target_id": str(row["hex"]).lower(),
        "callsign": str(row["flight"]).strip(),
        "lat_deg": row.get("lat"),
        "lon_deg": row.get("lon"),
        "alt_baro_ft": row.get("alt_baro"),
        "alt_geom_ft": row.get("alt_geom"),
        "ground_speed_kt": row.get("gs"),
        "track_deg": row.get("track"),
        "baro_rate_ft_min": row.get("baro_rate"),
        "geom_rate_ft_min": row.get("geom_rate"),
        "seen_pos_s": row.get("seen_pos"),
        "db_flags": row.get("dbFlags") or 0,
    }


def protocol_row(index: int, payload: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    if is_number(row.get("alt_geom")):
        altitude_ft = float(row["alt_geom"])
        altitude_source = "alt_geom"
    else:
        altitude_ft = float(row["alt_baro"])
        altitude_source = "alt_baro"
    if is_number(row.get("geom_rate")):
        rate_ft_min = float(row["geom_rate"])
        rate_source = "geom_rate"
    else:
        rate_ft_min = float(row["baro_rate"])
        rate_source = "baro_rate"
    timestamp = int(float(payload["now"]) / 1000.0 - float(row["seen_pos"]))
    return {
        "snapshot_index": index,
        "captured_at_utc": iso_utc(float(payload["now"]) / 1000.0),
        "target_id": str(row["hex"]).lower(),
        "callsign": str(row["flight"]).strip(),
        "timestamp_utc": iso_utc(timestamp),
        "timestamp_unix": timestamp,
        "lat_deg": float(row["lat"]),
        "lon_deg": float(row["lon"]),
        "altitude_m": altitude_ft * 0.3048,
        "altitude_source": altitude_source,
        "speed_m_s": float(row["gs"]) * 0.514444,
        "heading_deg": float(row["track"]),
        "vertical_rate_m_s": rate_ft_min * 0.00508,
        "vertical_rate_source": rate_source,
        "on_ground": False,
        "source_provider": "ADSB.lol",
    }


def write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def build_dataset(url: str, snapshots: int, interval: float, output_dir: Path) -> dict[str, Any]:
    source_dir = output_dir / "source"
    payloads: list[dict[str, Any]] = []
    source_metadata: list[dict[str, Any]] = []
    normalized: list[dict[str, Any]] = []

    for index in range(1, snapshots + 1):
        full_body, payload = fetch_snapshot(url)
        eligible = [row for row in payload["ac"] if isinstance(row, dict) and is_eligible_aircraft(row)]
        filtered_payload = {
            "source": "ADSB.lol",
            "source_url": url,
            "now": payload.get("now"),
            "total_in_api_response": payload.get("total", len(payload["ac"])),
            "retained_aircraft_count": len(eligible),
            "filter_note": "Unmodified aircraft records retained only when position and callsign exist and dbFlags is 0/null.",
            "ac": eligible,
        }
        filename = f"adsb_lol_tokyo_filtered_snapshot_{index:02d}.json"
        filtered_body = json_bytes(filtered_payload)
        filtered_sha = write_bytes(source_dir / filename, filtered_body)
        source_metadata.append({
            "snapshot_index": index,
            "file": f"source/{filename}",
            "captured_at_utc": iso_utc(float(payload["now"]) / 1000.0),
            "api_reported_total": payload.get("total", len(payload["ac"])),
            "retained_count": len(eligible),
            "full_response_sha256": sha256_bytes(full_body),
            "committed_filtered_file_sha256": filtered_sha,
        })
        payloads.append({**payload, "ac": eligible})
        normalized.extend(normalized_row(index, payload, row) for row in eligible)
        if index < snapshots:
            time.sleep(interval)

    complete_by_snapshot = [
        {str(row["hex"]).lower(): row for row in payload["ac"] if has_protocol_fields(row)}
        for payload in payloads
    ]
    common_targets = sorted(set.intersection(*(set(rows) for rows in complete_by_snapshot)))
    if len(common_targets) < TARGET_COUNT:
        raise RuntimeError(f"三个快照中只有 {len(common_targets)} 个完整共同目标，少于所需 {TARGET_COUNT} 个")
    selected = common_targets[:TARGET_COUNT]

    track_rows: list[dict[str, Any]] = []
    frames: list[bytes] = []
    for snapshot_index, (payload, rows) in enumerate(zip(payloads, complete_by_snapshot), start=1):
        for target_id in selected:
            converted = protocol_row(snapshot_index, payload, rows[target_id])
            track_rows.append(converted)
            frames.append(encode_position_message({
                "target_id": converted["target_id"],
                "callsign": converted["callsign"],
                "timestamp": converted["timestamp_unix"],
                "timestamp_source": "POSITION_TIME",
                "lat": converted["lat_deg"],
                "lon": converted["lon_deg"],
                "altitude": converted["altitude_m"],
                "alt_type": "geometric" if converted["altitude_source"] == "alt_geom" else "barometric",
                "speed": converted["speed_m_s"],
                "heading": converted["heading_deg"],
                "vertical_rate": converted["vertical_rate_m_s"],
                "on_ground": converted["on_ground"],
            }, len(frames) + 1))

    write_csv(output_dir / "normalized_aircraft_states.csv", NORMALIZED_FIELDS, normalized)
    write_csv(output_dir / "real_tracks_3x3.csv", TRACK_FIELDS, track_rows)
    binary = b"".join(frames)
    write_bytes(output_dir / "real_partner_messages_multitime.bin", binary)
    decoded, errors = decode_message_stream(binary)
    if errors or not all(row["message_valid"] for row in decoded):
        raise RuntimeError("生成的 TeachingLink 数据未通过参考解码器")
    write_csv(output_dir / "real_partner_messages_decoded.csv", DECODED_FIELDS, decoded)

    provenance = {
        "dataset_name": "ADSB.lol Tokyo-area three-snapshot teaching dataset",
        "provider": "ADSB.lol",
        "source_url": url,
        "provider_api_documentation": "https://www.adsb.lol/docs/open-data/api/",
        "license": "Open Data Commons Open Database License (ODbL) 1.0",
        "license_url": LICENSE_URL,
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "query": {"latitude": 35.6762, "longitude": 139.6503, "radius_nm": 100},
        "snapshot_count": snapshots,
        "snapshot_interval_seconds": interval,
        "sources": source_metadata,
        "normalization": {
            "retained_filter": "valid six-hex ICAO address; nonempty ASCII callsign <=8 bytes; lat/lon present; dbFlags is 0/null",
            "three_by_three_filter": "same target in all snapshots; numeric position, altitude, speed, heading, vertical rate and seen_pos",
            "timestamp": "floor(response now in seconds - aircraft seen_pos seconds)",
            "altitude": "prefer alt_geom, otherwise alt_baro; feet x 0.3048 = metres",
            "speed": "ground speed knots x 0.514444 = metres/second",
            "vertical_rate": "prefer geom_rate, otherwise baro_rate; feet/minute x 0.00508 = metres/second",
        },
        "selected_targets": selected,
        "normalized_record_count": len(normalized),
        "teaching_record_count": len(track_rows),
        "no_interpolation": True,
        "no_synthetic_values": True,
        "full_api_responses_committed": False,
        "full_api_response_note": "Only filtered source records are committed; hashes of full responses are retained for provenance.",
    }
    write_bytes(output_dir / "provenance.json", json_bytes(provenance))
    return provenance


def main() -> int:
    parser = argparse.ArgumentParser(description="Download and organize a traceable real ADS-B teaching dataset.")
    parser.add_argument("--url", default=API_URL)
    parser.add_argument("--snapshots", type=int, default=SNAPSHOT_COUNT)
    parser.add_argument("--interval", type=float, default=INTERVAL_SECONDS)
    parser.add_argument("--output", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()
    if args.snapshots < 3:
        parser.error("--snapshots 至少为 3")
    provenance = build_dataset(args.url, args.snapshots, args.interval, args.output)
    print(json.dumps({
        "output": str(args.output),
        "normalized_records": provenance["normalized_record_count"],
        "teaching_records": provenance["teaching_record_count"],
        "selected_targets": provenance["selected_targets"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
