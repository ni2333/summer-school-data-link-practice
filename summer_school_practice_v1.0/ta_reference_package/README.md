# 助教内部参考包

版本：`1.0.0-rc3`。本目录仅供助教进行参考链复验和按节点发布检查点，不得发给学生。环境建立和全量验证统一见 `../environment/README_environment.md`。

## 组成

- `reference_implementation/`：M2-M6 可重复运行的参考实现和数据生成脚本。
- `checkpoints/`：按模块节点发布的官方检查点。
- `expected_results/`：样例帧十六进制、边界值、M5 预期告警和质量态势。
- `test_cases/`：错误帧或不完整尾帧等内部用例。
- `case_manifest_internal.csv`：用例与预期结果索引。

## 参考链运行

CSV 必做路径：

```powershell
.\.venv\Scripts\python.exe ta_reference_package\reference_implementation\run_all_reference.py
```

SQLite 选做路径：

```powershell
.\.venv\Scripts\python.exe ta_reference_package\reference_implementation\run_all_reference.py --sqlite
```

固定预期：原始 5 条状态中 3 条可编码、2 条解析错误；多时间片 9 帧、3 个目标、每条航迹 3 点；M5 共 5 条告警（HIGH 1、MEDIUM 4）。启用 SQLite 时另应写入 9 行；SQLite 不可用不影响 CSV 必做路径。

## 发布检查点

模块主责助教核对内容后，由集成助教统一复制指定文件；禁止把整个目录共享给学生。

- M2 后：`official_parsed_open_states.csv`、`official_decoded_multitime.csv`
- M3 后：`official_current_situation.csv`
- M4 后：`official_verified_mapping.csv`、`unified_message_reference.ndjson`
- M5 后：`expected_alert_counts.json` 中的类型与数量清单
