# 统一实验环境说明

本文说明实验环境的安装、验证和降级方法。所有实践命令均使用项目根目录下的 `.venv`，不依赖本机已经安装的第三方 Python 包。

## 环境要求

- Python 3.10 及以上
- pandas 2.x
- matplotlib 3.7 及以上、4.0 以下
- Python 标准库：`json`、`csv`、`datetime`、`sqlite3`、`pathlib`

SQLite 只作为 M3 选做路径。大模型不可用时，M4 必须使用学校提供的预生成候选映射，不影响必做任务。

## 一键部署

在 `summer_school_practice_v1.0/` 根目录执行。脚本会创建 `.venv`、安装固定范围内的依赖并运行全部检查。

Windows PowerShell：

```powershell
powershell -ExecutionPolicy Bypass -File environment\setup.ps1
```

Linux/macOS：

```bash
bash environment/setup.sh
```

## 手动安装

Windows PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r environment\requirements.txt
```

Linux/macOS：

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -r environment/requirements.txt
```

这里的系统 `python` 或 `python3` 只用于创建虚拟环境；创建后不再用它运行实践代码。

## 全量验证

Windows PowerShell：

```powershell
.\.venv\Scripts\python.exe environment\run_all_checks.py
```

Linux/macOS：

```bash
./.venv/bin/python environment/run_all_checks.py
```

该命令依次执行环境检查、文件冒烟测试、文件清单检查、协议自动化测试、M2-M6 参考链、OpenSky 完整实验以及 SQLite 路径。所有实验检查应当通过。

## 离线环境

如果实验电脑不能联网，可在相同操作系统和 Python 版本的联网电脑执行：

```powershell
.\.venv\Scripts\python.exe -m pip download --only-binary=:all: -r environment\requirements.txt -d environment\wheelhouse
```

将 `environment/wheelhouse/` 随部署介质复制到离线电脑后执行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --no-index --find-links environment\wheelhouse -r environment\requirements.txt
.\.venv\Scripts\python.exe environment\run_all_checks.py
```

仓库已包含 OpenSky 离线快照，实验运行不依赖 OpenSky 实时 API、付费大模型、数据库服务器或管理员权限。

## 降级路径

- SQLite 不可用：继续使用 CSV 完成 M3 必做任务。
- 大模型不可用：使用 `pre_generated_mapping_candidate.csv` 完成 M4 人工核验。
- 学生前序结果错误：可用 `ta_reference_package/expected_results/` 中的参考结果定位差异。
- 中文路径、含空格路径或无管理员权限场景失败：保留完整报错和实际路径，再修复相应脚本。

## 常见错误

- 显示“独立虚拟环境”失败：确认命令使用 `.\.venv\Scripts\python.exe`，不要使用系统 `python` 运行实践。
- PowerShell 阻止脚本执行：使用 `powershell -ExecutionPolicy Bypass -File environment\setup.ps1`，不需要管理员权限。
- `pip` 无法联网：使用同平台、同 Python 版本准备的 `environment\wheelhouse` 离线安装。
- SQLite 显示 `WARN`：不修复也可完成必做任务，继续生成 `decoded_multitime.csv`、`track_table.csv` 和 `current_situation.csv`。
- 大模型不可用：直接读取 `student_package\reference\pre_generated_mapping_candidate.csv`，逐项人工核验后形成正式映射。
- 中文或空格路径读写失败：确认终端与文件均使用 UTF-8，并从项目根目录重新运行。
