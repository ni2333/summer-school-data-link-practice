# 数据链软件暑期学校学生实践包

本包包含 M1-M6 实验所需的离线数据、Schema、模板、提示和代码骨架。

## 开始前

先按 `../environment/README_environment.md` 在正式课程包根目录建立独立 `.venv`，并确认环境检查和文件冒烟测试通过。环境安装、验证命令和不可用时的降级路径统一以该文件为准。

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

### OpenSky 真实数据

`data/opensky_real/` 是从 OpenSky 官方匿名 REST API 实际下载的 3 个快照，共 71 条状态向量，不是人工编造数据。根目录 `experiment/run_opensky_experiment.py` 可直接用这些数据完成 10 个目标的编码、传输、接收、入库和精度对比实验。

## M4 语义互操作

- 输入：`data/m4/partner_current_situation.csv`、字段定义、`unified_model.json`。
- 候选：自行使用大模型，或使用 `reference/pre_generated_mapping_candidate.csv`。
- 骨架：`src_skeleton/m4_mapping.py`。
- 输出：候选映射、人工核验映射、`unified_situation.ndjson`、一页核验说明。
- 候选中故意保留可识别问题，不能直接当答案。

## M5 一致性保障

- 输入：`data/m5/anomaly_cases.csv`、`data/m5/anomaly_rules.csv`。
- 骨架：`src_skeleton/m5_quality.py`。
- 输出：`alert_log.csv`、`quality_situation.csv`、异常结果说明。
- 必做规则：位置缺失、延迟、联合键重复、航向越界。

## M6 综合演练

将 M2-M5 代码接入 `src_skeleton/run_all.py`，从空 `output/` 目录执行。README 使用 `templates/m6_README_template.md`，并记录输入、输出和实验结果；运行命令见该模板。

完整提交项见 `templates/submission_checklist.md`。
