from __future__ import annotations

import csv
import json
import math
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


FRAME_SIZE = 41
MAGIC = 0x4453
VERSION = 1
MESSAGE_TYPE = 1
MAX_22BIT = (1 << 22) - 1

VALID_LAT = 1 << 0
VALID_LON = 1 << 1
VALID_ALT = 1 << 2
VALID_SPEED = 1 << 3
VALID_HEADING = 1 << 4
VALID_VERTICAL_RATE = 1 << 5
VALID_CALLSIGN = 1 << 6

STATUS_ON_GROUND = 1 << 0
STATUS_ALT_GEOMETRIC = 1 << 1
STATUS_TIMESTAMP_FALLBACK = 1 << 2


class PracticeDataError(ValueError):
    def __init__(self, problem_type: str, field: str, value: Any, description: str):
        super().__init__(description)
        self.problem_type = problem_type
        self.field = field
        self.value = value
        self.description = description


def quantize_half_up(value: float) -> int:
    if value < 0:
        raise ValueError("quantize_half_up只接受非负中间值")
    return math.floor(value + 0.5)


def calculate_checksum(data_without_checksum: bytes) -> int:
    return sum(data_without_checksum) % 65536


def _required(value: Any, field: str) -> Any:
    if value is None:
        raise PracticeDataError("REQUIRED_FIELD_MISSING", field, value, f"必需字段{field}缺失")
    return value


def _optional_number(value: Any, field: str, minimum: float, maximum: float, *, maximum_inclusive: bool = True) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PracticeDataError("TYPE_ERROR", field, value, f"{field}必须为数值或null")
    numeric = float(value)
    upper_ok = numeric <= maximum if maximum_inclusive else numeric < maximum
    if numeric < minimum or not upper_ok:
        boundary = "≤" if maximum_inclusive else "<"
        raise PracticeDataError("OUT_OF_RANGE", field, value, f"{field}应满足{minimum}≤x{boundary}{maximum}")
    return numeric


def parse_state_vector(vector: list[Any]) -> dict[str, Any]:
    if not isinstance(vector, list) or len(vector) < 17:
        raise PracticeDataError("TYPE_ERROR", "state_vector", vector, "状态向量必须为至少17项的数组")

    target_id = _required(vector[0], "target_id")
    if not isinstance(target_id, str) or len(target_id) != 6:
        raise PracticeDataError("TYPE_ERROR", "target_id", target_id, "target_id必须为恰好6位十六进制字符串")
    try:
        int(target_id, 16)
    except ValueError as exc:
        raise PracticeDataError("TYPE_ERROR", "target_id", target_id, "target_id包含非十六进制字符") from exc

    time_position = vector[3]
    last_contact = vector[4]
    timestamp = time_position if time_position is not None else last_contact
    _required(timestamp, "timestamp")
    if isinstance(timestamp, bool) or not isinstance(timestamp, int) or not 0 < timestamp <= 0xFFFFFFFF:
        raise PracticeDataError("OUT_OF_RANGE", "timestamp", timestamp, "timestamp必须为uint32范围内的正整数")

    on_ground = _required(vector[8], "on_ground")
    if not isinstance(on_ground, bool):
        raise PracticeDataError("TYPE_ERROR", "on_ground", on_ground, "on_ground必须为布尔值")

    callsign = vector[1]
    if callsign is not None:
        if not isinstance(callsign, str):
            raise PracticeDataError("TYPE_ERROR", "callsign", callsign, "callsign必须为字符串或null")
        callsign = callsign.strip() or None
        if callsign is not None:
            try:
                encoded = callsign.encode("ascii")
            except UnicodeEncodeError as exc:
                raise PracticeDataError("ENCODING_ERROR", "callsign", callsign, "callsign必须为ASCII") from exc
            if len(encoded) > 8:
                raise PracticeDataError("ENCODING_ERROR", "callsign", callsign, "callsign不得超过8个ASCII字节")

    baro = _optional_number(vector[7], "baro_altitude", -1000, 64535)
    geo = _optional_number(vector[13], "geo_altitude", -1000, 64535)
    if baro is not None:
        altitude, alt_type = baro, "barometric"
    elif geo is not None:
        altitude, alt_type = geo, "geometric"
    else:
        altitude, alt_type = None, "unknown"

    return {
        "target_id": target_id.lower(),
        "callsign": callsign,
        "country": vector[2],
        "time_position": time_position,
        "last_contact": last_contact,
        "timestamp": timestamp,
        "timestamp_source": "POSITION_TIME" if time_position is not None else "LAST_CONTACT_FALLBACK",
        "time_source": "position_time" if time_position is not None else "last_contact_fallback",
        "lon": _optional_number(vector[5], "lon", -180, 180),
        "lat": _optional_number(vector[6], "lat", -90, 90),
        "baro_altitude": baro,
        "geo_altitude": geo,
        "altitude": altitude,
        "alt_type": alt_type,
        "on_ground": on_ground,
        "speed": _optional_number(vector[9], "speed", 0, 6553.5),
        "heading": _optional_number(vector[10], "heading", 0, 360, maximum_inclusive=False),
        "vertical_rate": _optional_number(vector[11], "vertical_rate", -327.68, 327.67),
        "position_source": vector[16],
        "source": "OpenSky",
    }


def parse_open_sky_payload(payload: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    states = payload.get("states")
    if not isinstance(states, list):
        raise PracticeDataError("TYPE_ERROR", "states", states, "states必须为数组")
    records: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for index, vector in enumerate(states, start=1):
        try:
            record = parse_state_vector(vector)
            record["record_no"] = index
            records.append(record)
        except PracticeDataError as exc:
            errors.append({
                "record_no": index,
                "target_id": vector[0] if isinstance(vector, list) and vector else None,
                "stage": "parse",
                "field": exc.field,
                "problem_type": exc.problem_type,
                "value": exc.value,
                "description": exc.description,
            })
    return records, errors


def _encode_optional(frame: bytearray, record: dict[str, Any], field: str, bit: int, start: int, length: int, encoder) -> int:
    value = record.get(field)
    if value is None:
        frame[start:start + length] = b"\x00" * length
        return 0
    code = encoder(float(value))
    frame[start:start + length] = int(code).to_bytes(length, "big", signed=False)
    return bit


def encode_position_message(record: dict[str, Any], message_seq: int) -> bytes:
    if not 0 <= message_seq <= 65535:
        raise PracticeDataError("OUT_OF_RANGE", "message_seq", message_seq, "message_seq必须为uint16")
    target_id = str(_required(record.get("target_id"), "target_id")).lower()
    if len(target_id) != 6:
        raise PracticeDataError("TYPE_ERROR", "target_id", target_id, "target_id必须为6位十六进制字符串")
    try:
        target_code = int(target_id, 16)
    except ValueError as exc:
        raise PracticeDataError("TYPE_ERROR", "target_id", target_id, "target_id包含非十六进制字符") from exc
    timestamp = int(_required(record.get("timestamp"), "timestamp"))
    if not 0 < timestamp <= 0xFFFFFFFF:
        raise PracticeDataError("OUT_OF_RANGE", "timestamp", timestamp, "timestamp超出uint32正整数范围")
    on_ground = _required(record.get("on_ground"), "on_ground")
    if not isinstance(on_ground, bool):
        raise PracticeDataError("TYPE_ERROR", "on_ground", on_ground, "on_ground必须为布尔值")

    frame = bytearray(FRAME_SIZE)
    frame[0:2] = MAGIC.to_bytes(2, "big")
    frame[2] = VERSION
    frame[3] = MESSAGE_TYPE
    frame[4:6] = FRAME_SIZE.to_bytes(2, "big")
    frame[6:8] = message_seq.to_bytes(2, "big")
    frame[8:12] = timestamp.to_bytes(4, "big")
    frame[12:15] = target_code.to_bytes(3, "big")

    validity = 0
    callsign = record.get("callsign")
    if callsign is not None:
        normalized = str(callsign).strip()
        try:
            callsign_bytes = normalized.encode("ascii")
        except UnicodeEncodeError as exc:
            raise PracticeDataError("ENCODING_ERROR", "callsign", callsign, "callsign必须为ASCII") from exc
        if not 1 <= len(callsign_bytes) <= 8:
            raise PracticeDataError("ENCODING_ERROR", "callsign", callsign, "callsign长度必须为1至8字节")
        frame[15:23] = callsign_bytes.ljust(8, b"\x00")
        validity |= VALID_CALLSIGN

    validity |= _encode_optional(
        frame, record, "lat", VALID_LAT, 23, 3,
        lambda value: quantize_half_up((value + 90.0) / 180.0 * MAX_22BIT)
        if -90.0 <= value <= 90.0 else _raise_range("lat", value, -90, 90),
    )
    validity |= _encode_optional(
        frame, record, "lon", VALID_LON, 26, 3,
        lambda value: quantize_half_up((value + 180.0) / 360.0 * MAX_22BIT)
        if -180.0 <= value <= 180.0 else _raise_range("lon", value, -180, 180),
    )
    validity |= _encode_optional(
        frame, record, "altitude", VALID_ALT, 29, 2,
        lambda value: quantize_half_up(value + 1000.0)
        if -1000.0 <= value <= 64535.0 else _raise_range("altitude", value, -1000, 64535),
    )
    validity |= _encode_optional(
        frame, record, "speed", VALID_SPEED, 31, 2,
        lambda value: quantize_half_up(value / 0.1)
        if 0.0 <= value <= 6553.5 else _raise_range("speed", value, 0, 6553.5),
    )
    validity |= _encode_optional(
        frame, record, "heading", VALID_HEADING, 33, 2,
        _encode_heading,
    )
    validity |= _encode_optional(
        frame, record, "vertical_rate", VALID_VERTICAL_RATE, 35, 2,
        lambda value: quantize_half_up((value + 327.68) / 0.01)
        if -327.68 <= value <= 327.67 else _raise_range("vertical_rate", value, -327.68, 327.67),
    )

    status = STATUS_ON_GROUND if on_ground else 0
    if record.get("altitude") is not None and record.get("alt_type") == "geometric":
        status |= STATUS_ALT_GEOMETRIC
    if str(record.get("timestamp_source", "")).upper() == "LAST_CONTACT_FALLBACK" or record.get("time_source") == "last_contact_fallback":
        status |= STATUS_TIMESTAMP_FALLBACK
    frame[37] = status
    frame[38] = validity
    frame[39:41] = calculate_checksum(frame[:39]).to_bytes(2, "big")
    return bytes(frame)


def _raise_range(field: str, value: float, minimum: float, maximum: float) -> int:
    raise PracticeDataError("OUT_OF_RANGE", field, value, f"{field}超出教学编码量程[{minimum}, {maximum}]")


def _encode_heading(value: float) -> int:
    if not 0.0 <= value < 360.0:
        return _raise_range("heading", value, 0, 360)
    code = quantize_half_up(value / 0.01)
    if code >= 36000:
        raise PracticeDataError("OUT_OF_RANGE", "heading", value, "航向量化后不得达到360.00度")
    return code


def _raw_zero_inconsistency(frame: bytes, validity: int, bit: int, start: int, end: int) -> bool:
    return not validity & bit and any(frame[start:end])


def decode_position_message(data: bytes) -> dict[str, Any]:
    errors: list[str] = []
    if len(data) != FRAME_SIZE:
        return {"message_valid": False, "validation_errors": ["LENGTH_ERROR"], "frame_length": len(data)}

    magic = int.from_bytes(data[0:2], "big")
    version = data[2]
    message_type = data[3]
    message_length = int.from_bytes(data[4:6], "big")
    if magic != MAGIC:
        errors.append("MAGIC_ERROR")
    if version != VERSION:
        errors.append("VERSION_ERROR")
    if message_type != MESSAGE_TYPE:
        errors.append("MESSAGE_TYPE_ERROR")
    if message_length != FRAME_SIZE:
        errors.append("LENGTH_ERROR")
    expected_checksum = calculate_checksum(data[:39])
    checksum = int.from_bytes(data[39:41], "big")
    if checksum != expected_checksum:
        errors.append("CHECKSUM_ERROR")

    status = data[37]
    validity = data[38]
    lat_code = int.from_bytes(data[23:26], "big")
    lon_code = int.from_bytes(data[26:29], "big")
    if status & 0xF8 or validity & 0x80 or lat_code > MAX_22BIT or lon_code > MAX_22BIT:
        errors.append("RESERVED_BITS_ERROR")

    regions = [
        (VALID_CALLSIGN, 15, 23), (VALID_LAT, 23, 26), (VALID_LON, 26, 29),
        (VALID_ALT, 29, 31), (VALID_SPEED, 31, 33), (VALID_HEADING, 33, 35),
        (VALID_VERTICAL_RATE, 35, 37),
    ]
    if any(_raw_zero_inconsistency(data, validity, bit, start, end) for bit, start, end in regions):
        errors.append("FLAG_VALUE_INCONSISTENCY")
    if not validity & VALID_ALT and status & STATUS_ALT_GEOMETRIC:
        errors.append("FLAG_VALUE_INCONSISTENCY")

    timestamp = int.from_bytes(data[8:12], "big")
    target_code = int.from_bytes(data[12:15], "big")
    if timestamp == 0:
        errors.append("REQUIRED_FIELD_MISSING")

    callsign = None
    if validity & VALID_CALLSIGN:
        try:
            callsign = data[15:23].rstrip(b"\x00").decode("ascii")
            if not callsign:
                errors.append("FLAG_VALUE_INCONSISTENCY")
        except UnicodeDecodeError:
            errors.append("ENCODING_ERROR")

    lat = lat_code / MAX_22BIT * 180.0 - 90.0 if validity & VALID_LAT and lat_code <= MAX_22BIT else None
    lon = lon_code / MAX_22BIT * 360.0 - 180.0 if validity & VALID_LON and lon_code <= MAX_22BIT else None
    altitude_code = int.from_bytes(data[29:31], "big")
    speed_code = int.from_bytes(data[31:33], "big")
    heading_code = int.from_bytes(data[33:35], "big")
    vertical_rate_code = int.from_bytes(data[35:37], "big")
    altitude = altitude_code - 1000.0 if validity & VALID_ALT else None
    speed = speed_code * 0.1 if validity & VALID_SPEED else None
    heading = heading_code * 0.01 if validity & VALID_HEADING else None
    vertical_rate = vertical_rate_code * 0.01 - 327.68 if validity & VALID_VERTICAL_RATE else None
    if heading is not None and not 0 <= heading < 360:
        errors.append("OUT_OF_RANGE")

    errors = list(dict.fromkeys(errors))
    fallback = bool(status & STATUS_TIMESTAMP_FALLBACK)
    alt_type = "unknown" if altitude is None else ("geometric" if status & STATUS_ALT_GEOMETRIC else "barometric")
    return {
        "target_id": f"{target_code:06x}",
        "callsign": callsign,
        "timestamp": timestamp,
        "timestamp_source": "LAST_CONTACT_FALLBACK" if fallback else "POSITION_TIME",
        "time_source": "last_contact_fallback" if fallback else "position_time",
        "message_seq": int.from_bytes(data[6:8], "big"),
        "lat": lat,
        "lon": lon,
        "altitude": altitude,
        "alt_type": alt_type,
        "speed": speed,
        "heading": heading,
        "vertical_rate": vertical_rate,
        "on_ground": bool(status & STATUS_ON_GROUND),
        "status_flags": status,
        "validity_flags": validity,
        "latitude_code": lat_code,
        "longitude_code": lon_code,
        "altitude_code": altitude_code,
        "speed_code": speed_code,
        "heading_code": heading_code,
        "vertical_rate_code": vertical_rate_code,
        "lat_valid": bool(validity & VALID_LAT),
        "lon_valid": bool(validity & VALID_LON),
        "altitude_valid": bool(validity & VALID_ALT),
        "speed_valid": bool(validity & VALID_SPEED),
        "heading_valid": bool(validity & VALID_HEADING),
        "vertical_rate_valid": bool(validity & VALID_VERTICAL_RATE),
        "callsign_valid": bool(validity & VALID_CALLSIGN),
        "checksum": checksum,
        "expected_checksum": expected_checksum,
        "message_valid": not errors,
        "validation_errors": errors,
        "source": "TeachingLink",
    }


def decode_message_stream(data: bytes) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    complete_length = len(data) - len(data) % FRAME_SIZE
    for offset in range(0, complete_length, FRAME_SIZE):
        record = decode_position_message(data[offset:offset + FRAME_SIZE])
        record["frame_no"] = offset // FRAME_SIZE + 1
        records.append(record)
    if len(data) != complete_length:
        errors.append({
            "record_no": complete_length // FRAME_SIZE + 1,
            "target_id": None,
            "stage": "stream_split",
            "field": "frame_length",
            "problem_type": "LENGTH_ERROR",
            "value": len(data) - complete_length,
            "description": "忽略不完整尾帧",
        })
    return records, errors


def build_tracks(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        if record.get("message_valid") and record.get("target_id") and record.get("timestamp"):
            grouped[str(record["target_id"])].append(record)
    tracks: list[dict[str, Any]] = []
    for target_id in sorted(grouped):
        ordered = sorted(grouped[target_id], key=lambda row: (int(row["timestamp"]), int(row.get("message_seq", 0))))
        for sequence, row in enumerate(ordered, start=1):
            tracks.append({
                "target_id": target_id,
                "timestamp": row["timestamp"],
                "message_seq": row.get("message_seq"),
                "track_sequence_no": sequence,
                "lat": row.get("lat"),
                "lon": row.get("lon"),
                "altitude": row.get("altitude"),
                "speed": row.get("speed"),
                "heading": row.get("heading"),
            })
    return tracks


def build_current_situation(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        if record.get("message_valid") and record.get("target_id") and record.get("timestamp"):
            grouped[str(record["target_id"])].append(record)
    output: list[dict[str, Any]] = []
    for target_id in sorted(grouped):
        ordered = sorted(grouped[target_id], key=lambda row: (int(row["timestamp"]), int(row.get("message_seq", 0))))
        latest = dict(ordered[-1])
        output.append({
            "target_id": target_id,
            "callsign": latest.get("callsign"),
            "latest_time": latest.get("timestamp"),
            "lat": latest.get("lat"),
            "lon": latest.get("lon"),
            "altitude": latest.get("altitude"),
            "speed": latest.get("speed"),
            "heading": latest.get("heading"),
            "vertical_rate": latest.get("vertical_rate"),
            "on_ground": latest.get("on_ground"),
            "track_length": len(ordered),
            "alt_type": latest.get("alt_type"),
            "time_source": latest.get("time_source"),
            "message_valid": latest.get("message_valid"),
            "status_flags": latest.get("status_flags"),
            "validity_flags": latest.get("validity_flags"),
            "latitude_code": latest.get("latitude_code"),
            "longitude_code": latest.get("longitude_code"),
            "altitude_code": latest.get("altitude_code"),
            "speed_code": latest.get("speed_code"),
            "heading_code": latest.get("heading_code"),
            "vertical_rate_code": latest.get("vertical_rate_code"),
        })
    return output


def save_records_to_sqlite(records: Iterable[dict[str, Any]], db_path: Path, schema_path: Path) -> int:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    connection = sqlite3.connect(db_path)
    connection.executescript(schema_path.read_text(encoding="utf-8"))
    columns = [
        "target_id", "callsign", "timestamp", "timestamp_source", "message_seq", "lat", "lon",
        "altitude", "alt_type", "speed", "heading", "vertical_rate", "on_ground", "status_flags",
        "validity_flags", "message_valid", "source",
    ]
    rows = []
    for record in records:
        row = [record.get(column) for column in columns]
        row[12] = int(bool(row[12]))
        row[15] = int(bool(row[15]))
        rows.append(row)
    placeholders = ",".join("?" for _ in columns)
    connection.executemany(f"INSERT INTO state_record ({','.join(columns)}) VALUES ({placeholders})", rows)
    connection.commit()
    count = connection.execute("SELECT COUNT(*) FROM state_record").fetchone()[0]
    connection.close()
    return int(count)


def map_current_to_unified(row: dict[str, Any], source: str) -> dict[str, Any]:
    timestamp = int(row.get("latest_time") or row.get("timestamp") or 0)
    lat = _to_optional_float(row.get("lat"))
    lon = _to_optional_float(row.get("lon"))
    altitude = _to_optional_float(row.get("altitude"))
    speed = _to_optional_float(row.get("speed"))
    heading = _to_optional_float(row.get("heading"))
    vertical_rate = _to_optional_float(row.get("vertical_rate"))
    message_valid = _to_bool(row.get("message_valid"), default=True)
    return {
        "track_id": str(row.get("target_id", "")).lower().zfill(6),
        "source": source,
        "timestamp": timestamp,
        "identity": {"callsign": _to_optional_text(row.get("callsign"))},
        "position": {
            "lat": lat,
            "lon": lon,
            "alt": altitude,
            "alt_type": str(row.get("alt_type") or ("barometric" if altitude is not None else "unknown")),
        },
        "motion": {"speed": speed, "heading": heading, "vertical_rate": vertical_rate},
        "status": {"on_ground": _to_bool(row.get("on_ground"), default=False)},
        "quality": {
            "position_valid": lat is not None and lon is not None and -90 <= lat <= 90 and -180 <= lon <= 180,
            "time_valid": timestamp > 0,
            "message_valid": message_valid,
            "time_source": str(row.get("time_source") or "position_time"),
            "anomaly_flags": [],
        },
    }


def _to_optional_text(value: Any) -> str | None:
    if value is None or str(value).strip() == "":
        return None
    return str(value).strip()


def _to_optional_float(value: Any) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    return float(value)


def _to_bool(value: Any, *, default: bool) -> bool:
    if value is None or str(value).strip() == "":
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "是"}


def check_quality(records: list[dict[str, Any]], batch_time: int = 1710000120) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    keys = [(str(row.get("target_id", "")), int(row.get("latest_time") or row.get("timestamp") or 0)) for row in records]
    duplicate_counts = Counter(keys)
    alerts: list[dict[str, Any]] = []
    quality_rows: list[dict[str, Any]] = []
    for row, key in zip(records, keys):
        target_id, record_time = key
        lat = _to_optional_float(row.get("lat"))
        lon = _to_optional_float(row.get("lon"))
        heading = _to_optional_float(row.get("heading"))
        row_alerts: list[dict[str, Any]] = []

        def add(alert_type: str, severity: str, field: str, description: str) -> None:
            alert = {
                "alert_time": batch_time,
                "target_id": target_id,
                "alert_type": alert_type,
                "severity": severity,
                "field": field,
                "description": description,
            }
            alerts.append(alert)
            row_alerts.append(alert)

        if lat is None or lon is None:
            add("POSITION_MISSING", "HIGH", "lat/lon", "纬度或经度为空")
        if batch_time - record_time > 60:
            add("DATA_DELAYED", "MEDIUM", "timestamp", "记录时间落后批次时间超过60秒")
        if duplicate_counts[key] > 1:
            add("DUPLICATE_RECORD", "MEDIUM", "target_id+timestamp", "联合键重复")
        if heading is not None and not 0 <= heading < 360:
            add("HEADING_OUT_OF_RANGE", "MEDIUM", "heading", "航向应满足0≤heading<360")

        severities = {alert["severity"] for alert in row_alerts}
        if "HIGH" in severities:
            level, display = "HIGH", "ERROR"
        elif "MEDIUM" in severities:
            level, display = "MEDIUM", "WARNING"
        else:
            level, display = "NONE", "NORMAL"
        quality_rows.append({
            "target_id": target_id,
            "timestamp": record_time,
            "position_valid": lat is not None and lon is not None,
            "delayed": batch_time - record_time > 60,
            "duplicate_detected": duplicate_counts[key] > 1,
            "heading_valid": heading is None or 0 <= heading < 360,
            "message_valid": _to_bool(row.get("message_valid"), default=True),
            "anomaly_level": level,
            "display_status": display,
        })
    return alerts, quality_rows


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            normalized = {
                key: json.dumps(value, ensure_ascii=False) if isinstance(value, (list, dict)) else value
                for key, value in row.items()
            }
            writer.writerow(normalized)


def write_ndjson(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")
