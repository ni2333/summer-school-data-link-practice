# OpenSky 数据链完整实验

本实验使用仓库内已经下载好的 OpenSky 官方接口快照，不需要联网。一次运行完成：读取真实状态向量、选择航空器、41 字节 TeachingLink 编码、模拟逐帧发送、接收解码、更新当前态势、保存 CSV/SQLite，并统计定点量化产生的精度误差。

在 `summer_school_practice_v1.0` 目录运行：

```powershell
.\.venv\Scripts\python.exe experiment\run_opensky_experiment.py --targets 10
```

结果写入 `experiment/output/`：

- `receiver_situation_initial.csv`：接收前的空态势表。
- `selected_source_states.csv`：本次选中的 OpenSky 原始状态。
- `transmitted_frames.bin`：模拟发送的 41 字节二进制帧。
- `transmission_log.csv`：逐帧接收过程和接收端目标数量。
- `decoded_states.csv`：接收端解码结果。
- `receiver_situation_final.csv`：接收完成后的最新态势。
- `received_states.db`：SQLite 接收记录。
- `precision_error_report.csv`：原始值与解码值的误差对比。
- `experiment_summary.json`：一页式结果摘要。

想做最小演示时，把 `--targets 10` 改成 `--targets 1` 即可。
