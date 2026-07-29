# 助教 A 独立环境与正式包验收记录

## 基本信息

- 日期：2026-07-29
- 操作系统：Windows 11
- 工作目录：`summer_school_practice_v1.0/`
- Python：3.12.7（项目独立 `.venv`）
- 依赖：pandas 2.3.3、matplotlib 3.11.1
- 虚拟环境隔离：`include-system-site-packages = false`
- 验收命令：`.\.venv\Scripts\python.exe environment\run_all_checks.py`

## 验收结果

| 检查层次 | 结果 |
|---|---|
| 环境检查 | 6/6 通过 |
| 正式输入文件冒烟测试 | 5/5 通过 |
| 发布清单与学生包边界 | 3/3 通过 |
| 协议与流程自动化测试 | 10/10 通过 |
| M2-M6 端到端参考试跑 | 通过 |

M2-M6 参考链冻结指标与 `test_records/end_to_end_trial_2026-07-29.md` 一致：原始 5 条状态中 3 条可编码、9 帧多时刻消息、3 个目标、6 条统一消息、5 条告警、SQLite 9 行。

## 文档与目录复核

- 正式课程包根目录保持为 `summer_school_practice_v1.0/`。
- 学生材料、助教内部材料、环境工具、测试和试跑记录保持分目录管理。
- 环境安装与验证只在 `environment/README_environment.md` 维护；其他 README 只保留对应受众的任务入口或发布规则。
- `.venv`、学生运行输出和临时试跑输出均由 `.gitignore` 排除。

## 结论

助教 A 负责的独立环境、正式目录、版本清单和发布边界已完成本轮复核。当前版本为 `1.0.0-rc2` 助教联调候选版；B/C 交叉课堂身份计时试跑仍是最终冻结前置条件。
