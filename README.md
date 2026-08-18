# 数据链软件暑期学校实验项目

本仓库实现《数据链软件暑期学校实践手册 M1-M6 统一基础实践底稿（最终修订稿）》中的实验流程。主要目录为 `summer_school_practice_v1.0/`。

## 文档入口

- 环境安装、独立虚拟环境和全量验证：`summer_school_practice_v1.0/environment/README_environment.md`
- 学生 M1-M6 任务、输入和输出：`summer_school_practice_v1.0/student_package/README.md`
- 学生个人仓库与最终提交办法：`summer_school_practice_v1.0/student_package/guides/student_submission_guide.md`
- OpenSky 完整实验：`summer_school_practice_v1.0/experiment/README.md`
- 参考实现和预期结果：`summer_school_practice_v1.0/ta_reference_package/README.md`
- 实验改进记录：`summer_school_practice_v1.0/release_notes.md`

安装命令只在环境说明中维护，其他 README 仅保留各自受众需要的入口和规则。

## 项目结构

```text
summer_school_practice_v1.0/
├─ student_package/       M1-M6 数据、Schema、模板和代码骨架
├─ ta_reference_package/  参考实现、边界值和错误用例
├─ experiment/            OpenSky 完整实验、输出和简版报告
├─ environment/           统一环境部署与验证
├─ tests/                 协议和端到端自动化测试
├─ test_records/          问题台账和实验记录
├─ manifest.csv           文件清单
└─ release_notes.md       实验改进记录
```

## 实验说明

- TeachingLink 是 41 字节学校自定义教学帧，不对应真实装备或行业协议。
- 课堂必做路径使用离线文件，不依赖实时 OpenSky、付费大模型、数据库服务器或管理员权限。
- OpenSky 完整实验使用 3 个官方接口离线快照，不需要实验时联网。
- SQLite 和预生成字段映射均可在本地运行。
