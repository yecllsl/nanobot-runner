# v0.22.0 UAT 反馈记录表

> **测试日期**: 2026-05-15 起
> **测试环境**: Windows / Python 3.11+ / uv
> **测试模式**: AI Agent + 用户交互
> **测试基线**: v0.21.0 → v0.22.0

---

## 反馈记录

| 用例ID | 模块 | 执行时间 | CLI命令 | 预期结果 | 实际结果 | 用户判定 | 用户评论 | 痛点标记 |
|--------|------|---------|---------|---------|---------|---------|---------|---------|
| UAT-001 | 数据导入 | 08:43 | data import --force | 单文件导入成功 | 导入成功，显示记录数 | ✅通过 | -- | - |
| UAT-002 | 数据导入 | 08:37 | data import | 批量导入成功 | 637成功/37跳过 | ✅通过 | -- | - |
| UAT-003 | 数据导入 | 08:43 | data import(重复) | 去重跳过 | "文件已存在，跳过导入" | ✅通过 | 与UAT-001合并验证 | - |
| UAT-006~008 | 数据查询 | 08:48 | data stats / --year | 显示统计信息 | 637次/3810km/462h | ✅通过 | -- | - |
| UAT-009~014 | 数据分析 | 08:49 | analysis vdot/load/hr-drift | 分析结果合理 | VDOT=42.9~45.2, ATL=64.6 | ✅通过 | -- | - |
| UAT-018~020 | 报告生成 | 08:51 | report weekly | 周报生成正常 | 本周0次(无数据)，BUG-001未复现 | ✅通过 | -- | - |
| UAT-021~027 | 系统管理 | 08:52 | system version | 显示版本号 | v0.21.0 | ✅通过 | -- | - |
| UAT-043~047 | Cron提醒 | 08:53 | cron status | 显示配置状态 | 显示"未配置飞书凭证"但实际已配置 | ⚠️部分通过 | 飞书凭证已配置但cron未读取到 | P1 |
| UAT-048~051 | AI透明化 | 08:54 | transparency dashboard | 显示AI看板 | 正常显示进化等级/工具可靠性 | ✅通过 | -- | - |
| UAT-052~055 | 偏好管理 | 08:55 | preference show | 显示用户偏好 | "训练时段:早晨"与实际不符 | ⚠️部分通过 | 用户实际晚上19:00训练，偏好推断不准 | P2 |
| UAT-056~060 | 技能管理 | 08:56 | skill list | 列出技能 | 2个技能正常显示 | ✅通过 | -- | - |
| UAT-061~065 | 数据可视化(v0.18) | 09:00 | viz vdot/load/hr-zones | 可视化图表正常 | VDOT趋势/训练负荷/心率区间均正常 | ✅通过 | -- | - |
| UAT-066~070 | 数据导出(v0.18) | 09:03 | export sessions --format csv/json | 导出成功 | CSV/JSON均导出7条记录 | ✅通过 | --output为必填参数 | - |
| UAT-071~080 | 身体信号(v0.19) | 09:06 | analysis hrv/fatigue/recovery, status today | 分析结果合理 | HRV正常但有Warning；fatigue/recovery显示"暂无数据" | ⚠️部分通过 | fatigue/recovery未读取已导入数据；HRV有PerformanceWarning | P1 |
| UAT-081~091 | ML预测(v0.20) | 09:10 | predict vdot/race/injury | 预测结果合理 | VDOT=45/半马2:18/风险18.4，数据质量insufficient | ⚠️部分通过 | CLI命令是predict非prediction，文档与实现不一致 | P2 |
| UAT-092~100 | 数字孪生(v0.21) | 09:15 | twin snapshot/simulate/compare | 孪生引擎正常 | snapshot CTL/ATL=0与analysis load不一致；simulate/compare正常 | ⚠️部分通过 | CTL/ATL数据不一致；PerformanceWarning；数据质量empty | P1 |
| UAT-021~027 | 性能测试 | 09:20 | 各命令耗时测量 | 响应时间<5s | data stats=20.17s/twin snapshot=16.36s偏慢 | ⚠️部分通过 | data stats和twin snapshot响应偏慢 | P2 |

---

## 痛点汇总

| 痛点ID | 来源用例 | 痛点分类 | 痛点描述 | 严重程度 | 用户原话 |
|--------|---------|---------|---------|---------|---------|
| P1-001 | UAT-043~047 | 配置读取 | cron status显示"未配置飞书凭证"但.env.local中已配置NANOBOT_FEISHU_APP_ID等，ConfigManager未从环境变量读取飞书凭证 | 严重 | "未配置飞书应用凭证——实际已配置" |
| P2-001 | UAT-052~055 | 偏好推断 | preference show显示"训练时段:早晨"但用户实际晚上19:00训练，画像推断算法不准确 | 一般 | "训练时段和实际不符，我更多时间是在晚上19:00左右开始训练" |
| P1-002 | UAT-071~080 | 数据读取 | analysis fatigue/recovery显示"暂无训练数据"但实际已导入637条记录，数据读取逻辑异常 | 严重 | fatigue/recovery命令未读取到已导入数据 |
| P2-002 | UAT-071~080 | 性能警告 | HRV分析模块使用lf.columns触发Polars PerformanceWarning，应使用LazyFrame.collect_schema().names() | 一般 | PerformanceWarning: Determining column names of LazyFrame |
| P2-003 | UAT-081~091 | 文档一致性 | UAT指南中CLI命令写为prediction，实际命令为predict，文档与实现不一致 | 一般 | "CLI命令是predict而非prediction，需要改进" |
| P1-003 | UAT-092~100 | 数据不一致 | twin snapshot显示CTL=0/ATL=0，但analysis load显示CTL=64.6/ATL=64.6，同一数据源结果不一致 | 严重 | CTL/ATL数据不一致 |
| P2-004 | UAT-021~027 | 性能 | data stats=20.17s、twin snapshot=16.36s，637条数据下响应偏慢，需优化查询性能 | 一般 | data stats和twin snapshot响应偏慢 |

---

## 用户总体评价

- **最满意的功能**：（待填写）
- **最不满意的功能**：（待填写）
- **改进建议**：（待填写）
