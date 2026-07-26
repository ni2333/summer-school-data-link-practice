# 统一实验环境说明

## 环境要求

- Python 3.10及以上
- pandas 2.x
- matplotlib 3.7及以上、4.0以下
- Python标准库：`json`、`csv`、`datetime`、`sqlite3`、`pathlib`

SQLite只作为M3选做路径。大模型不可用时，M4必须使用学校提供的预生成候选映射，不影响必做任务。

## 推荐安装

```powershell
cd summer_school_practice_v1.0
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r environment\requirements.txt
```

## 检查环境

```powershell
python environment\environment_check.py
python environment\run_smoke_test.py
```

两个命令都应输出总结，并以退出码0结束。

## 离线环境

正式发布前应准备可离线安装的依赖包，或确认机房环境已经预装所需版本。学生必做任务不得依赖OpenSky实时API、付费大模型、数据库服务器或管理员权限。

## 降级路径

- SQLite不可用：继续使用CSV完成M3必做任务。
- 大模型不可用：使用`pre_generated_mapping_candidate.csv`完成M4人工核验。
- 学生前序结果错误：在模块结束后使用官方检查点继续后续任务，但检查点不得替代该模块本人提交。
- 中文路径、含空格路径或无管理员权限场景必须在冻结前完成验证；若验证失败，应记录原因并修复环境包。
