# 真实 ADS-B 数据扩展

本目录的数据来自 ADSB.lol 公开 API，不是手工捏造或随机生成的数据。它用于补充 M2/M3 的真实数据试跑；正式包内原有的合成小数据仍用于可重复的边界值和异常测试，二者用途不同。

数据出处与许可：ADSB.lol，Open Data Commons Open Database License（ODbL）1.0。使用或再分发时须保留来源署名，并遵守 ODbL 的署名、同许可共享等要求。推荐署名：`Contains information from ADSB.lol, made available under ODbL 1.0.`

文件说明：

- `source/*.json`：东京周边 100 海里查询的三个过滤后源快照。航空器原始字段未改写，只剔除无位置、无呼号、非标准 ICAO 地址或 `dbFlags` 非 0/null 的记录。
- `normalized_aircraft_states.csv`：三个快照的常用字段平铺表，原始单位保持为英尺、节、英尺/分钟和度。
- `real_tracks_3x3.csv`：三个共同目标、每个三个时刻的 TeachingLink 输入表，并明确记录单位换算和字段来源。
- `real_partner_messages_multitime.bin`：上述 9 条记录编码得到的 41 字节 TeachingLink 帧流。
- `real_partner_messages_decoded.csv`：参考解码器离线回读结果。
- `provenance.json`：来源 URL、抓取时刻、筛选规则、原始响应及提交文件的 SHA-256、单位换算和记录数。

没有插值、补值或人为构造观测值。位置时间按 ADSB.lol 响应时刻减去 `seen_pos` 计算；高度优先使用 `alt_geom`，缺失时用 `alt_baro`；速度及垂直速度仅做公开记录中的标准单位换算。

重新抓取（会产生当前时刻的新数据，结果自然会变化）：

```powershell
..\.venv\Scripts\python.exe ..\ta_reference_package\reference_implementation\download_real_adsb_dataset.py
```

来源文档：<https://www.adsb.lol/docs/open-data/api/> ；许可全文：<https://opendatacommons.org/licenses/odbl/1-0/>。
