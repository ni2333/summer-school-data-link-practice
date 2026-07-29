# 数据链软件暑期学校统一基础实践包

本仓库是《数据链软件暑期学校实践手册 M1-M6 统一基础实践底稿（最终修订稿）》的助教协作工作区。正式课程包固定为 `summer_school_practice_v1.0/`，仓库根目录不作为学生发布包。

## 文档入口

- 环境安装、独立虚拟环境和全量验证：`summer_school_practice_v1.0/environment/README_environment.md`
- 学生 M1-M6 任务、输入和输出：`summer_school_practice_v1.0/student_package/README.md`
- 助教参考实现和检查点发布：`summer_school_practice_v1.0/ta_reference_package/README.md`
- 版本状态和变更记录：`summer_school_practice_v1.0/release_notes.md`

安装命令只在环境说明中维护，其他 README 仅保留各自受众需要的入口和规则。

## 正式课程包

```text
summer_school_practice_v1.0/
├─ student_package/       学生可见材料，不含答案
├─ ta_reference_package/  助教内部材料，不得发给学生
├─ environment/           统一环境部署与验证
├─ tests/                 协议和端到端自动化测试
├─ test_records/          分工、问题和试跑记录
├─ manifest.csv           文件版本与发布边界清单
└─ release_notes.md       发布状态与变更记录
```

## 发布边界

- TeachingLink 是 41 字节学校自定义教学帧，不对应真实装备或行业协议。
- 课堂必做路径使用离线文件，不依赖实时 OpenSky、付费大模型、数据库服务器或管理员权限。
- SQLite 为选做；大模型不可用时使用预生成候选；前序失败时由助教按节点发布官方检查点。
- 学生包与助教包必须分开发放，`ta_reference_package/` 和 `test_records/` 不得进入学生发布包。
