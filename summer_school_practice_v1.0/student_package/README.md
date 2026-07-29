# 数据链软件暑期学校学生实践包

版本：`1.0.0-rc1`。本包包含 M1-M6 必做主线所需的离线数据、Schema、模板、提示和代码骨架；不包含助教参考实现、内部 case、官方答案或预期告警数量。

## 开始前

在项目根目录完成环境部署并确认全部检查通过：

```powershell
.\.venv\Scripts\python.exe environment\environment_check.py
.\.venv\Scripts\python.exe environment\run_smoke_test.py
```

统一环境为 Python 3.10+、pandas 2.x、matplotlib 3.7-3.x，以及标准库 `json/csv/datetime/sqlite3/pathlib`。SQLite 为选做；课堂必做任务不访问实时 OpenSky。

## M1 体系理解

- 输入：`data/raw_states.json`、`guides/opensky_interface_summary.md`、`guides/m1_guided_questions.md`、`schema/teaching_message_spec.md`、字段字典。
- 模板：`templates/m1_system_template.md`。
- 输出：系统处理流程图、接口/通信/风险说明。

## M2 协议解析与消息编解码

- 输入：`raw_states.json`、两个字段字典、41 字节 TeachingLink 规范。
- 骨架：`src_skeleton/m2_protocol.py`。
- 输出：Parser/Codec、`encoded_messages.bin`、`decoded_partner_states.csv`、`validation_log.csv`、`roundtrip_report.csv`。
- 重点：大端字节序、22 位经纬度、统一量化、状态/有效性标志、保留位、教学校验和、真实零值与缺失值区分。

## M3 单源多时刻关联与当前态势

- 输入：`data/partner_messages_multitime.bin`（9 帧、369 字节）。
- 骨架：`src_skeleton/m3_tracks.py`。
- 输出：`decoded_multitime.csv`、`track_table.csv`、`current_situation.csv`；SQLite/航迹图选做。
- 输入帧边界已对齐；要求处理不完整尾帧，不要求失步重同步。

## M4 语义互操作

- 输入：`data/partner_current_situation.csv`、字段定义、`unified_model.json`。
- 候选：自行使用大模型，或使用 `reference/pre_generated_mapping_candidate.csv`。
- 骨架：`src_skeleton/m4_mapping.py`。
- 输出：候选映射、人工核验映射、`unified_situation.ndjson`、一页核验说明。
- 候选中故意保留可识别问题，不能直接当答案。

## M5 一致性保障

- 输入：`data/anomaly_cases.csv`、`data/anomaly_rules.csv`。
- 骨架：`src_skeleton/m5_quality.py`。
- 输出：`alert_log.csv`、`quality_situation.csv`、异常结果说明。
- 必做规则：位置缺失、延迟、联合键重复、航向越界。

## M6 综合演练

将 M2-M5 本人代码接入 `src_skeleton/run_all.py`，从空 `output/` 目录执行。README 使用 `templates/m6_README_template.md`，并记录是否启用 SQLite、候选映射来源和官方检查点使用情况。

## 官方检查点

检查点只在模块结束后由助教发布。允许用于解除后续阻塞，但不能替代本人前序成果；具体规则见 `templates/checkpoint_switch.md`。

完整提交项见 `templates/submission_checklist.md`。
