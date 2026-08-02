# 助教 A 必做与选做降级验收记录

## 基本信息

- 日期：2026-07-30
- 操作系统：Windows 11
- Python：3.12.7
- Python解释器：课程包 `.venv/Scripts/python.exe`
- 虚拟环境隔离：`include-system-site-packages = false`
- 依赖：pandas 2.3.3、matplotlib 3.11.1
- 验收命令：`.\.venv\Scripts\python.exe environment\run_all_checks.py`

## 环境与输入检查

| 检查 | 结果 |
|---|---|
| Python、依赖、独立虚拟环境、UTF-8读写、正式目录 | 必做 6/6 通过 |
| SQLite内存读写 | 选做 1/1 通过 |
| JSON、二进制、CSV、NDJSON、正式输入、M4预生成候选 | 6/6 通过 |
| 发布清单与学生包边界 | 3/3 通过 |
| 协议与流程自动化测试 | 10/10 通过 |

## 双路径试跑

### CSV必做路径

- 运行时不启用SQLite。
- M2-M6端到端参考链通过。
- 生成13项关键成果，不生成 `states.db`。
- 冻结指标：3条可编码状态、9帧多时刻消息、3个目标、6条统一消息、5条告警，`sqlite_rows = null`。

### SQLite选做路径

- 运行时显式启用SQLite。
- M2-M6端到端参考链通过。
- 生成14项关键成果，包括 `states.db`。
- 冻结指标与CSV路径一致，SQLite写入9行。

## 降级结论

- SQLite不可用时，环境检查输出非阻断警告，学生可使用CSV完成M3必做任务并继续M4-M6。
- 大模型不可用时，`pre_generated_mapping_candidate.csv` 可读取，共8条候选；学生仍必须依据字段定义人工核验。
- wheelhouse离线依赖需在与机房相同的平台和Python版本上生成，不能使用当前电脑结果替代机房确认。

## 当前边界

助教 A 的自动化环境与降级验证已完成。B需在未参与开发的Windows电脑验证中文路径、含空格路径和无管理员权限场景；C需仅使用学生材料和环境说明重新安装。两份记录完成前，环境状态保持候选版，不标记冻结。
