# 实验参考实现

本目录用于复现实验链、核对边界值和运行错误用例。环境建立和全量验证见 `../environment/README_environment.md`。

## 组成

- `reference_implementation/`：M2-M6 可重复运行的参考实现和数据生成脚本。
- `checkpoints/`：各模块的参考结果。
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

这些参考结果只用于定位实验差异，不影响实验程序独立运行。
