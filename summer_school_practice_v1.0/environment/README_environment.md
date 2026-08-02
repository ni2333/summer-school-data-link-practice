# 统一实验环境说明

本文是正式课程包唯一的环境安装、验证和降级说明。所有实践命令均使用课程包根目录下的 `.venv`，不依赖本机已经安装的第三方 Python 包。

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

该命令依次执行环境检查、文件冒烟测试、发布清单和学生/助教包边界检查、协议自动化测试、M2-M6 CSV 必做路径试跑以及 SQLite 选做路径试跑。必做检查必须全部通过；SQLite 不可用时输出 `WARN` 并继续，不阻断 CSV 必做路径。

## 离线环境

正式发布前应在与机房相同的操作系统和 Python 版本上准备离线依赖。联网准备机执行：

```powershell
.\.venv\Scripts\python.exe -m pip download --only-binary=:all: -r environment\requirements.txt -d environment\wheelhouse
```

将 `environment/wheelhouse/` 随部署介质复制到离线电脑后执行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --no-index --find-links environment\wheelhouse -r environment\requirements.txt
.\.venv\Scripts\python.exe environment\run_all_checks.py
```

如果不制作离线依赖目录，必须形成机房已预装所需版本的确认记录。学生必做任务不得依赖 OpenSky 实时 API、付费大模型、数据库服务器或管理员权限。

## 降级路径

- SQLite 不可用：继续使用 CSV 完成 M3 必做任务。
- 大模型不可用：使用 `pre_generated_mapping_candidate.csv` 完成 M4 人工核验。
- 学生前序结果错误：在模块结束后使用官方检查点继续后续任务，但检查点不得替代该模块本人提交。
- 中文路径、含空格路径或无管理员权限场景必须在冻结前完成验证；若验证失败，应记录原因并修复环境包。

## 常见错误

- 显示“独立虚拟环境”失败：确认命令使用 `.\.venv\Scripts\python.exe`，不要使用系统 `python` 运行实践。
- PowerShell 阻止脚本执行：使用 `powershell -ExecutionPolicy Bypass -File environment\setup.ps1`，不需要管理员权限。
- `pip` 无法联网：使用同平台、同 Python 版本准备的 `environment\wheelhouse` 离线安装。
- SQLite 显示 `WARN`：不修复也可完成必做任务，继续生成 `decoded_multitime.csv`、`track_table.csv` 和 `current_situation.csv`。
- 大模型不可用：直接读取 `student_package\reference\pre_generated_mapping_candidate.csv`，逐项人工核验后形成正式映射。
- 中文或空格路径读写失败：将完整错误和实际路径记入环境试跑记录，由助教 A 判断是否阻断发布。
