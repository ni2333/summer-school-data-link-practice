# M4 两种来源字段定义

本文件与 `teaching_message_spec.md`、`opensky_field_dictionary.csv`、`partner_field_dictionary.csv`、`unified_model.json` 一起构成 M4 人工核验的权威依据。

## OpenSky 当前态势来源

- `target_id`：六位十六进制字符串，映射为 `track_id`。
- `latest_time`：Unix 秒，映射为 `timestamp`。
- `lat/lon`：已经是度；任一为空时 `quality.position_valid=false`。
- `altitude`：米；`alt_type` 保留 barometric/geometric/unknown。
- `speed`、`vertical_rate`：m/s；`heading`：度。
- `time_source`：position_time 或 last_contact_fallback；时间回退不等于时间无效。

## TeachingLink 当前态势来源

- 协议整数必须结合 `validity_flags`、比例因子和偏置解释。
- 有效位为 0 时统一模型字段必须为 `null`，不能把占位整数 0 当真实值。
- `status_flags.bit1` 仅在高度有效时解释高度来源。
- `status_flags.bit2` 表示时间来源回退，不直接令 `quality.time_valid=false`。
- `message_valid` 只由完整帧接收判据产生，不能推断来源可信或内容真实。

## 人工核验要求

候选映射只用于辅助。每条正式映射必须填写单位转换、空值策略、证据和 `verified`；至少用一个真实零值样例和一个字段缺失样例验证。
