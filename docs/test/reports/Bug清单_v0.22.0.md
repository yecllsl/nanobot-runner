# v0.22.0 Bug清单

> **创建日期**: 2026-05-17
> **最后更新**: 2026-05-18
> **测试基线**: v0.21.0 → v0.22.0
> **来源**: UAT测试 + 自动化测试

---

## Bug清单

| Bug ID | 所属模块 | 严重等级 | 优先级 | Bug标题 | 状态 | 来源 | 创建日期 |
|--------|---------|---------|--------|---------|------|------|---------|
| BUG-2201 | Cron提醒 | 严重 | P0 | 飞书凭证已配置但cron status未读取 | 已闭环 | UAT | 2026-05-15 |
| BUG-2202 | 身体信号 | 严重 | P0 | fatigue/recovery显示"暂无数据"但实际已导入637条 | 已闭环 | UAT | 2026-05-15 |
| BUG-2203 | 数字孪生 | 严重 | P0 | twin snapshot CTL/ATL=0与analysis load不一致 | 已闭环 | UAT | 2026-05-15 |
| BUG-2204 | 偏好管理 | 一般 | P1 | 训练时段推断不准（显示"早晨"实际晚上19:00） | 待修复 | UAT | 2026-05-15 |
| BUG-2205 | 身体信号 | 一般 | P1 | HRV分析模块lf.columns触发Polars PerformanceWarning | 已闭环 | UAT | 2026-05-15 |
| BUG-2206 | ML预测 | 一般 | P1 | CLI命令名predict与文档prediction不一致 | 已闭环 | UAT | 2026-05-15 |
| BUG-2207 | 性能 | 一般 | P2 | data stats=20.17s/twin snapshot=16.36s响应偏慢 | 待修复 | UAT | 2026-05-15 |
| BUG-TEST-001 | 测试用例 | 一般 | P2 | test_plan_create_with_options日期参数过期 | 已闭环 | 自动化测试 | 2026-05-17 |

---

## Bug详情

### BUG-2201: Cron飞书凭证读取失败

- **严重等级**: 严重
- **优先级**: P0
- **来源**: UAT-043~047
- **复现步骤**:
  1. 通过`nanobotrun system init`配置飞书凭证（写入.env.local）
  2. 执行`nanobotrun cron status`
- **实际结果**: 显示"未配置飞书应用凭证 (feishu_app_id 或 feishu_app_secret)"
- **预期结果**: 正确读取.env.local中的NANOBOT_FEISHU_APP_ID等环境变量，显示飞书配置正常
- **根因分析**: ConfigManager从config.json读取feishu_app_id/feishu_app_secret，但初始化向导将凭证写入.env.local（NANOBOT_FEISHU_APP_ID格式），两处配置源不一致
- **修复建议**: ConfigManager增加从.env.local环境变量读取飞书凭证的fallback逻辑，或init向导同时写入config.json
- **出现版本**: v0.21.0

### BUG-2202: fatigue/recovery未读取已导入数据

- **严重等级**: 严重
- **优先级**: P0
- **来源**: UAT-071~080
- **复现步骤**:
  1. 导入637条跑步数据（`nanobotrun data import <path>`）
  2. 执行`nanobotrun analysis fatigue`
  3. 执行`nanobotrun analysis recovery`
- **实际结果**: fatigue显示"暂无训练数据"，recovery显示"暂无恢复状态数据"
- **预期结果**: 基于已导入数据计算并显示疲劳度评分和恢复状态
- **根因分析**: fatigue/recovery模块的数据查询条件可能与数据存储格式不匹配，或使用了不同的数据源路径
- **修复建议**: 排查fatigue/recovery的数据读取逻辑，确保与storage模块使用相同的查询路径和数据格式
- **出现版本**: v0.19.0

### BUG-2203: twin snapshot CTL/ATL与analysis load不一致

- **严重等级**: 严重
- **优先级**: P0
- **来源**: UAT-092~100
- **复现步骤**:
  1. 执行`nanobotrun analysis load` → 显示CTL=64.6, ATL=64.6, TSB=0.0
  2. 执行`nanobotrun twin snapshot` → 显示CTL=0.0, ATL=0.0, TSB=+0.0
- **实际结果**: twin snapshot的CTL/ATL为0，与analysis load的64.6不一致
- **预期结果**: 两个命令使用同一数据源，CTL/ATL值应一致
- **根因分析**: twin引擎的StateVectorBuilder可能使用了不同的数据查询逻辑或时间窗口，与AnalyticsEngine的训练负荷计算逻辑不一致
- **修复建议**: 统一twin引擎与analysis模块的负荷计算逻辑，确保数据源和算法一致
- **出现版本**: v0.21.0

### BUG-2204: 训练时段推断不准

- **严重等级**: 一般
- **优先级**: P1
- **来源**: UAT-052~055
- **复现步骤**:
  1. 导入大量晚间19:00左右的跑步数据
  2. 执行`nanobotrun preference show`
- **实际结果**: 显示"训练时段: 早晨"
- **预期结果**: 基于实际训练时间分布推断为"晚上"
- **根因分析**: 画像推断算法可能未正确统计训练时间分布，或默认值"早晨"覆盖了实际推断结果
- **修复建议**: 优化画像推断算法，基于训练记录的时间分布统计推断训练时段
- **出现版本**: v0.17.0

### BUG-2205: HRV分析PerformanceWarning

- **严重等级**: 一般
- **优先级**: P1
- **来源**: UAT-071~080
- **复现步骤**:
  1. 执行`nanobotrun analysis hrv --days 30`
- **实际结果**: 输出PerformanceWarning: "Determining the column names of a LazyFrame requires resolving its schema"
- **预期结果**: 无警告输出
- **根因分析**: hrv_analyzer.py第80行和第283行使用`lf.columns`，应替换为`lf.collect_schema().names()`
- **修复建议**: 将`lf.columns`替换为`lf.collect_schema().names()`，消除Polars PerformanceWarning
- **出现版本**: v0.19.0

### BUG-2206: CLI命令名与文档不一致

- **严重等级**: 一般
- **优先级**: P1
- **来源**: UAT-081~091
- **复现步骤**:
  1. 执行`nanobotrun prediction` → 报错"No such command 'prediction'. Did you mean 'predict'?"
- **实际结果**: CLI命令为`predict`，但文档/UAT指南中写为`prediction`
- **预期结果**: 文档与CLI命令名一致
- **根因分析**: 文档编写时未与CLI实现同步
- **修复建议**: 更新UAT指南和AGENTS.md中的命令名为`predict`
- **出现版本**: v0.20.0

### BUG-2207: 部分命令响应偏慢

- **严重等级**: 一般
- **优先级**: P2
- **来源**: UAT-025~027
- **复现步骤**:
  1. 在637条数据下执行`nanobotrun data stats` → 20.17s
  2. 执行`nanobotrun twin snapshot` → 16.36s
- **实际结果**: data stats=20.17s, twin snapshot=16.36s
- **预期结果**: <5s
- **根因分析**: 可能存在多次Parquet文件读取或未优化的查询逻辑
- **修复建议**: 优化查询性能，减少重复文件读取，利用LazyFrame延迟计算
- **出现版本**: v0.21.0

### BUG-TEST-001: 测试用例数据过期

- **严重等级**: 一般
- **优先级**: P2
- **来源**: 自动化集成测试
- **复现步骤**:
  1. 执行`uv run pytest tests/integration/module/test_plan_cli_integration_bug001.py::TestPlanCreateCommand::test_plan_create_with_options`
- **实际结果**: 测试失败，exit_code=2（CLI参数验证失败）
- **预期结果**: 测试通过
- **根因分析**: 测试用例中使用的目标日期`2026-05-01`已过期（当前日期2026-05-17），CLI验证逻辑拒绝了过去日期
- **修复建议**: 将测试用例中的日期更新为未来日期（如`2026-12-01`），或使用动态日期计算
- **出现版本**: 测试用例维护问题

---

## 修复进度统计

| 严重等级 | 总数 | 已修复 | 待修复 | 修复率 |
|---------|------|--------|--------|--------|
| 严重 | 3 | 3 | 0 | 100% |
| 一般 | 5 | 3 | 2 | 60% |
| **合计** | **8** | **6** | **2** | **75%** |

---

## Bug分布分析

### 按模块分布

| 模块 | Bug数 | 占比 |
|------|-------|------|
| 身体信号 | 2 | 25% |
| Cron提醒 | 1 | 12.5% |
| 数字孪生 | 1 | 12.5% |
| 偏好管理 | 1 | 12.5% |
| ML预测 | 1 | 12.5% |
| 性能 | 1 | 12.5% |
| 测试用例 | 1 | 12.5% |

### 按版本分布

| 版本 | Bug数 | 占比 |
|------|-------|------|
| v0.21.0 | 3 | 37.5% |
| v0.19.0 | 2 | 25% |
| v0.20.0 | 1 | 12.5% |
| v0.17.0 | 1 | 12.5% |
| 测试用例 | 1 | 12.5% |

### 按分类分布

| 分类 | Bug数 | 占比 |
|------|-------|------|
| 数据一致性 | 2 | 25% |
| 配置读取 | 1 | 12.5% |
| 偏好推断 | 1 | 12.5% |
| 性能警告 | 1 | 12.5% |
| 文档一致性 | 1 | 12.5% |
| 响应性能 | 1 | 12.5% |
| 测试数据 | 1 | 12.5% |

---

## 质量建议

1. **配置统一**: 统一ConfigManager对config.json和.env.local的读取逻辑，避免配置源不一致
2. **数据源统一**: 统一twin/analysis/body_signal模块的数据查询路径，确保一致性
3. **性能优化**: 优化data stats和twin snapshot的查询性能，目标<5s
4. **Polars最佳实践**: 将`lf.columns`替换为`lf.collect_schema().names()`，消除PerformanceWarning
5. **文档同步**: 更新UAT指南中CLI命令名，确保与实现一致
6. **测试数据维护**: 定期更新测试用例中的日期参数，避免过期
