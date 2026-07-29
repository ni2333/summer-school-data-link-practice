# 数据链软件暑期学校统一基础实践包

本仓库实现《数据链软件暑期学校实践手册 M1-M6 统一基础实践底稿（最终修订稿）》的离线实验环境、学生实践包、助教参考包、自动检查和试跑记录。

## 快速部署

Windows PowerShell：

```powershell
cd summer_school_practice_v1.0
powershell -ExecutionPolicy Bypass -File environment\setup.ps1
.\.venv\Scripts\python.exe environment\run_all_checks.py
```

Linux/macOS：

```bash
cd summer_school_practice_v1.0
bash environment/setup.sh
./.venv/bin/python environment/run_all_checks.py
```

最后一个命令依次验证环境、正式输入读取、发布清单与学生/助教包边界、协议自动化测试、M2-M6 参考链和官方检查点。所有检查均应以退出码 0 结束。

## 目录边界

- `student_package/`：可发给学生的离线数据、Schema、模板、提示和代码骨架；不含答案。
- `ta_reference_package/`：仅助教内部使用的参考实现、官方检查点、错误用例和预期结果。
- `environment/`：统一环境部署与验证脚本。
- `tests/`：协议和端到端自动化测试。
- `test_records/`：三位助教的分工、问题台账和独立试跑记录。

## 冻结口径

- TeachingLink 是 41 字节学校自定义教学帧，不对应真实装备或行业协议。
- 课堂必做路径使用离线文件，不依赖实时 OpenSky、付费大模型、数据库服务器或管理员权限。
- SQLite 为选做；大模型不可用时使用预生成候选；前序失败时由助教按节点发布官方检查点。
- 学生包与助教包必须分开发放，`ta_reference_package/` 不得复制到学生环境。

详细模块说明见 `summer_school_practice_v1.0/student_package/README.md`，助教发布流程见 `summer_school_practice_v1.0/ta_reference_package/README.md`。
