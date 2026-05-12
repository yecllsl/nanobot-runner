# v0.21.0 数字孪生引擎 — 测试策略

> **文档版本**: v1.0
> **创建日期**: 2026-05-12
> **目标版本**: v0.21.0
> **对齐文档**:
> - [需求规格说明书 v8.4](../requirements/REQ_需求规格说明书.md)
> - [架构设计说明书 v8.0.0](../architecture/架构设计说明书.md)
> - [产品规划方案 v9.1](../product/产品规划方案.md)
> - [v0.21数字孪生引擎设计规格 v1.1](../superpowers/specs/2026-05-10-v0.21-digital-twin-design.md)
> - [测试策略与规范 v3.1](./测试策略与规范.md)
> - [v0.20.1 测试策略](./strategy_v0.20.1.md)

---

## 1. 测试范围

### 1.1 版本概述

**版本主题**: 数字孪生引擎 —— 构建可推演的跑者生理模型
**核心目标**: 实现What-If推演能力，让用户"在训练前看到训练后的自己"
**目标用户**: 有明确训练目标的高级用户（计划参加比赛的跑者）
**前置依赖**: v0.20预测引擎、v0.19身体信号引擎

**MVP Twin设计决策**:

| 设计项 | v0.21 MVP决策 | 延后项 |
|--------|--------------|--------|
| 计划输入 | ✅ 仅支持系统生成的计划（通过plan_id引用PlanManager中的计划） | ❌ 用户手动构建计划（延后评估） |
| 推演能力 | ✅ simulate_plan + compare_plans | ❌ find_optimal_plan自动寻优（延后到v0.22+评估） |
| 状态缓存 | ✅ RunnerStateVector缓存到本地文件，TTL=24h | — |

### 1.2 v0.21.0 增量变更范围

| 变更类别 | 变更内容 | 影响范围 |
|---------|---------|---------|
| 新增twin核心子模块 | StateVectorBuilder、WhatIfSimulator、DigitalTwinEngine | `src/core/twin/` |
| 新增数据模型 | 5维度状态向量、推演结果、计划对比模型 | `src/core/twin/models.py` |
| 新增CLI命令组 | twin status/simulate/compare | `src/cli/commands/twin.py` |
| 新增CLI Handler | twin_handler.py业务逻辑调用层 | `src/cli/handlers/twin_handler.py` |
| 新增Agent工具 | get_runner_state、simulate_plan、compare_plans | `src/agents/tools.py` |
| AppContext扩展 | twin_engine懒加载属性 | `src/core/base/context.py` |
| 状态向量缓存 | JSON序列化+TTL=24h机制 | `~/.nanobot-runner/twin/state_vector.json` |
| 自定义异常 | TwinEngineError继承NanobotRunnerError | `src/core/exceptions.py` |

### 1.3 测试需求覆盖

| 需求ID | 需求名称 | 优先级 | v0.21增量 | 测试类型 |
|--------|---------|--------|-----------|---------|
| REQ-0.21-01 | 跑者状态向量 | P0 | 5维度聚合+缓存机制 | 单元+集成+E2E |
| REQ-0.21-02 | What-If推演引擎 | P0 | simulate_plan+compare_plans | 单元+集成+E2E |
| REQ-0.21-03 | 最优计划搜索 | P1 | 延后到v0.22+评估 | 不纳入 |

### 1.4 不纳入测试范围

- v0.20/v0.19已测试通过的预测引擎、身体信号引擎（仅做回归验证）
- 第三方依赖内部实现（scikit-learn、scipy、shap、joblib等）
- nanobot-ai框架核心功能
- 操作系统级别的文件系统行为
- LLM模型输出内容的不确定性验证
- v0.22+版本功能（多视角验证、决策追踪等）

---

## 2. 测试类型与策略

### 2.1 单元测试（Unit Testing）

**职责**: 开发工程师主责，测试工程师负责规范指导和结果校验

**v0.21.0 增量覆盖范围**:

| 模块 | 测试文件 | 增量用例数 | 说明 |
|------|---------|-----------|------|
| `src/core/twin/models.py` | `test_models.py` | 12 | 5维度数据模型序列化/反序列化 |
| `src/core/twin/state_vector_builder.py` | `test_state_vector_builder.py` | 15 | 5维度构建+降级策略+防御性设计 |
| `src/core/twin/whatif_simulator.py` | `test_whatif_simulator.py` | 18 | 逐周推演+三层降级+置信度衰减 |
| `src/core/twin/twin_engine.py` | `test_twin_engine.py` | 15 | 薄编排层+缓存机制+计划加载 |
| `src/cli/commands/twin.py` | `test_twin_commands.py` | 8 | CLI命令注册+参数校验 |
| `src/cli/handlers/twin_handler.py` | `test_twin_handler.py` | 6 | Handler业务逻辑调用 |
| `src/core/base/context.py` | `test_context_twin.py` | 4 | AppContext twin_engine懒加载 |
| `src/agents/tools.py` | `test_tools_twin.py` | 6 | 3个新Agent工具注册+返回格式 |

**覆盖率要求**:

| 模块 | 最低覆盖率 | 说明 |
|------|-----------|------|
| `src/core/twin/` | ≥80% | 核心孪生逻辑 |
| `src/core/twin/models.py` | ≥85% | 数据模型定义 |
| `src/core/twin/state_vector_builder.py` | ≥85% | 状态向量构建核心 |
| `src/core/twin/whatif_simulator.py` | ≥85% | 推演核心 |
| `src/core/twin/twin_engine.py` | ≥80% | 编排层 |
| `src/cli/commands/twin.py` | ≥60% | CLI命令层 |
| `src/cli/handlers/twin_handler.py` | ≥60% | Handler层 |

### 2.2 集成测试（Integration Testing）

**职责划分**:

| 测试类型 | 目录 | 负责人 |
|---------|------|--------|
| 模块内集成测试 | `tests/integration/module/` | 开发工程师 |
| 场景级集成测试 | `tests/integration/scene/` | 测试工程师 |

**v0.21.0 模块内集成测试范围**:

| 测试场景 | 验证内容 | 预期结果 |
|---------|---------|---------|
| StateVectorBuilder端到端 | 从Parquet读取到生成RunnerStateVector的完整流程 | 5维度数据正确填充 |
| WhatIfSimulator端到端 | 从HypotheticalPlan到SimulationResult的完整推演 | 每周快照正确生成 |
| DigitalTwinEngine编排 | get_current_snapshot/simulate/compare_plans完整调用链 | 结果正确组装 |
| CLI命令集成 | twin status/simulate/compare命令正确调用Handler | Rich格式化输出正确 |
| Agent工具集成 | 3个新Agent工具正确调用核心模块并返回JSON | JSON格式符合规范 |
| AppContext集成 | twin_engine懒加载正确创建并缓存 | 多次调用返回同一实例 |

### 2.3 场景级集成测试（Scene Integration Testing）

**职责**: 测试工程师主责

**v0.21.0 核心场景清单**:

| 场景ID | 场景名称 | 前置条件 | 验证内容 | 优先级 |
|--------|---------|---------|---------|--------|
| SC-01 | 跑者状态向量构建与缓存 | 有≥30天训练数据 | 5维度正确聚合，缓存TTL=24h生效 | P0 |
| SC-02 | 单计划What-If推演 | 有有效plan_id，数据充足 | 4周推演结果正确，每周快照完整 | P0 |
| SC-03 | 多计划对比推演 | 有2-5个有效plan_id | 对比表格正确，综合推荐评分合理 | P0 |
| SC-04 | 推演三层降级策略 | ML模型可用/不可用/Banister未拟合 | 自动降级，prediction_type标注正确 | P0 |
| SC-05 | 状态向量缓存失效与刷新 | 缓存过期或--refresh | 自动重新计算，缓存更新 | P1 |
| SC-06 | 空数据降级 | 无训练数据 | data_quality=EMPTY，零值填充 | P1 |
| SC-07 | 计划不存在异常 | 无效plan_id | TwinEngineError正确抛出 | P1 |
| SC-08 | 推演性能验证 | 单计划4周/3计划对比 | 响应时间<10秒/<30秒 | P1 |

### 2.4 E2E测试（End-to-End Testing）

**职责**: 测试工程师主责

**v0.21.0 E2E测试场景**:

| 场景ID | 场景名称 | 用户旅程 | 验证内容 | 优先级 |
|--------|---------|---------|---------|--------|
| E2E-01 | 查看当前跑者状态 | 用户执行`twin status` | 5维度Rich格式化输出，数据正确 | P0 |
| E2E-02 | 模拟训练计划效果 | 用户执行`twin simulate --plan <id> --weeks 4` | 推演结果完整，标注prediction_type | P0 |
| E2E-03 | 对比多个训练计划 | 用户执行`twin compare --plans <id1,id2,id3>` | 对比表格+综合推荐，评分合理 | P0 |
| E2E-04 | Agent查询跑者状态 | 用户问"我现在的状态如何？" | Agent调用get_runner_state，返回JSON | P0 |
| E2E-05 | Agent模拟计划效果 | 用户问"如果按计划A练4周会怎样？" | Agent调用simulate_plan，返回推演结果 | P0 |
| E2E-06 | 缓存机制验证 | 同日内多次执行`twin status` | 第二次命中缓存，响应时间<500ms | P1 |

---

## 3. 门禁规则

### 3.1 准入规则（测试准入条件）

| 门禁项 | 标准 | 验证方式 |
|--------|------|---------|
| 代码提交 | 所有代码已提交到feature分支 | Git log检查 |
| 单元测试通过率 | 100% | `uv run pytest tests/unit/core/twin/ --tb=short` |
| 代码覆盖率 | core≥80%, agents≥70%, cli≥60% | `uv run pytest --cov=src/core/twin --cov-report=term-missing` |
| Lint检查 | 0错误 | `uv run ruff check src/core/twin/ src/cli/commands/twin.py src/cli/handlers/twin_handler.py` |
| 类型检查 | 0错误 | `uv run mypy src/core/twin/ --ignore-missing-imports` |
| 依赖安装 | 无新增依赖或已审批 | `uv pip list` 对比requirements |
| 前置模块测试通过 | v0.20/v0.19回归测试通过 | `uv run pytest tests/unit/core/prediction/ tests/unit/core/body_signal/` |

### 3.2 准出规则（测试通过标准）

| 门禁项 | 标准 | 验证方式 |
|--------|------|---------|
| P0用例通过率 | 100% | 测试执行报告 |
| P1用例通过率 | ≥90% | 测试执行报告 |
| 致命/严重bug | 0个 | Bug清单 |
| 一般bug修复率 | ≥90% | Bug清单 |
| 核心业务流程 | 全量闭环 | E2E测试报告 |
| 性能指标 | 状态聚合<3秒，单计划推演<10秒，3计划对比<30秒 | 性能测试报告 |
| 缓存命中率 | 同日缓存命中率>90%（非--refresh场景） | 缓存统计日志 |

### 3.3 覆盖率要求

| 模块 | 最低覆盖率 | 说明 |
|------|-----------|------|
| `src/core/twin/` | ≥80% | 核心孪生逻辑 |
| `src/core/twin/models.py` | ≥85% | 数据模型定义 |
| `src/core/twin/state_vector_builder.py` | ≥85% | 状态向量构建核心 |
| `src/core/twin/whatif_simulator.py` | ≥85% | 推演核心 |
| `src/core/twin/twin_engine.py` | ≥80% | 编排层 |
| `src/cli/commands/twin.py` | ≥60% | CLI命令层 |
| `src/cli/handlers/twin_handler.py` | ≥60% | Handler层 |
| `src/agents/tools.py` (twin相关) | ≥70% | Agent工具层 |

---

## 4. 测试用例清单

### 4.1 P0核心用例（必须100%覆盖）

| 用例ID | 所属模块 | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 用例类型 |
|--------|---------|---------|---------|---------|---------|--------|---------|
| UT-TWIN-001 | models | 5维度状态向量序列化 | 无 | 创建RunnerStateVector实例，调用to_dict() | 返回完整JSON，5维度数据正确 | P0 | 功能测试 |
| UT-TWIN-002 | models | 状态向量反序列化 | 有JSON数据 | 从JSON创建RunnerStateVector实例 | 实例属性与JSON一致 | P0 | 功能测试 |
| UT-TWIN-003 | models | 缓存过期判定 | 创建StateVectorCache | 设置created_at为25小时前，调用is_expired() | 返回True | P0 | 功能测试 |
| UT-TWIN-004 | models | 缓存未过期判定 | 创建StateVectorCache | 设置created_at为1小时前，调用is_expired() | 返回False | P0 | 功能测试 |
| UT-TWIN-005 | state_vector_builder | 5维度状态向量构建 | 有≥30天训练数据 | 调用build() | 返回RunnerStateVector，5维度数据非零 | P0 | 功能测试 |
| UT-TWIN-006 | state_vector_builder | 体能维度构建 | PredictionEngine可用 | 调用build_fitness() | vdot/vdot_trend/vo2max_estimate正确 | P0 | 功能测试 |
| UT-TWIN-007 | state_vector_builder | 负荷维度构建 | TrainingLoadAnalyzer可用 | 调用build_load() | ctl/atl/tsb/acwr正确 | P0 | 功能测试 |
| UT-TWIN-008 | state_vector_builder | 身体信号维度构建 | BodySignalEngine可用 | 调用build_body_signal() | fatigue_score/recovery_status/resting_hr/hrv_rmssd正确 | P0 | 功能测试 |
| UT-TWIN-009 | state_vector_builder | 风险维度构建 | PredictionEngine可用 | 调用build_risk() | injury_risk_7d/injury_risk_28d/overtraining_risk正确 | P0 | 功能测试 |
| UT-TWIN-010 | state_vector_builder | 训练模式维度构建 | SessionRepository有数据 | 调用build_training_pattern() | weekly_volume_km/intensity_distribution/long_run_frequency正确 | P0 | 功能测试 |
| UT-TWIN-011 | state_vector_builder | 空数据降级 | 无训练数据 | 调用build() | data_quality=EMPTY，零值填充 | P0 | 异常测试 |
| UT-TWIN-012 | state_vector_builder | 部分数据降级 | 部分维度数据缺失 | 调用build() | data_quality=INSUFFICIENT，缺失维度零值 | P0 | 异常测试 |
| UT-TWIN-013 | state_vector_builder | 维度构建异常处理 | 某维度依赖抛出异常 | 调用build() | 异常维度零值，data_quality=INSUFFICIENT | P0 | 异常测试 |
| UT-TWIN-014 | whatif_simulator | 单周推演 | 有current_state和week_plan | 调用simulate_week() | 返回新的RunnerStateVector | P0 | 功能测试 |
| UT-TWIN-015 | whatif_simulator | 多周推演 | 有initial_state和HypotheticalPlan | 调用simulate() | 返回每周SimulationWeekSnapshot列表 | P0 | 功能测试 |
| UT-TWIN-016 | whatif_simulator | ML增强推演 | ML模型可用 | 调用simulate()，prediction_type="ml_enhanced" | 每周置信度衰减5% | P0 | 功能测试 |
| UT-TWIN-017 | whatif_simulator | 参数化推演 | ML不可用，Banister已拟合 | 调用simulate()，prediction_type="parametric" | 每周置信度衰减8% | P0 | 功能测试 |
| UT-TWIN-018 | whatif_simulator | 基础推演 | Banister未拟合 | 调用simulate()，prediction_type="basic" | 每周置信度衰减12% | P0 | 功能测试 |
| UT-TWIN-019 | whatif_simulator | 周TSS估算 | 有WeeklyPlanSpec | 调用estimate_weekly_tss() | 返回合理TSS值 | P0 | 功能测试 |
| UT-TWIN-020 | twin_engine | 获取当前状态 | 有StateVectorBuilder | 调用get_current_snapshot() | 返回RunnerStateVector | P0 | 功能测试 |
| UT-TWIN-021 | twin_engine | 状态缓存命中 | 缓存未过期 | 调用get_current_snapshot(use_cache=True) | 返回缓存结果，不重新计算 | P0 | 功能测试 |
| UT-TWIN-022 | twin_engine | 状态缓存刷新 | 缓存未过期 | 调用get_current_snapshot(use_cache=False) | 重新计算并更新缓存 | P0 | 功能测试 |
| UT-TWIN-023 | twin_engine | 单计划推演 | 有有效plan_id | 调用simulate(plan_id, weeks=4) | 返回SimulationResult | P0 | 功能测试 |
| UT-TWIN-024 | twin_engine | 多计划对比 | 有2-5个有效plan_id | 调用compare_plans_by_ids() | 返回PlanComparison | P0 | 功能测试 |
| UT-TWIN-025 | twin_engine | 计划不存在 | 无效plan_id | 调用simulate(无效plan_id) | 抛出TwinEngineError | P0 | 异常测试 |
| UT-TWIN-026 | twin_engine | plan_ids数量校验 | plan_ids数量<2或>5 | 调用compare_plans_by_ids() | 抛出TwinEngineError | P0 | 边界测试 |
| UT-TWIN-027 | twin_engine | 综合推荐评分计算 | 有PlanComparisonMetrics | 调用calculate_recommendation_score() | 返回0-100评分 | P0 | 功能测试 |
| UT-TWIN-028 | cli | twin status命令 | CLI环境 | 执行`twin status` | Rich格式化输出5维度状态 | P0 | 功能测试 |
| UT-TWIN-029 | cli | twin status --refresh | CLI环境 | 执行`twin status --refresh` | 强制刷新并输出 | P0 | 功能测试 |
| UT-TWIN-030 | cli | twin simulate命令 | 有有效plan_id | 执行`twin simulate --plan <id> --weeks 4` | Rich格式化输出推演结果 | P0 | 功能测试 |
| UT-TWIN-031 | cli | twin compare命令 | 有2-3个有效plan_id | 执行`twin compare --plans <id1,id2,id3>` | Rich格式化输出对比表格 | P0 | 功能测试 |
| UT-TWIN-032 | agent | get_runner_state工具 | Agent环境 | 调用get_runner_state | 返回RunnerStateVector JSON | P0 | 功能测试 |
| UT-TWIN-033 | agent | simulate_plan工具 | Agent环境 | 调用simulate_plan(plan_id, weeks) | 返回SimulationResult JSON | P0 | 功能测试 |
| UT-TWIN-034 | agent | compare_plans工具 | Agent环境 | 调用compare_plans(plan_ids) | 返回PlanComparison JSON | P0 | 功能测试 |
| UT-TWIN-035 | context | twin_engine懒加载 | AppContext初始化 | 访问context.twin_engine | 创建并缓存DigitalTwinEngine实例 | P0 | 功能测试 |
| UT-TWIN-036 | context | twin_engine缓存 | 已访问过twin_engine | 再次访问context.twin_engine | 返回同一实例 | P0 | 功能测试 |

### 4.2 P1重要用例（高优先级覆盖）

| 用例ID | 所属模块 | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 用例类型 |
|--------|---------|---------|---------|---------|---------|--------|---------|
| UT-TWIN-101 | models | IntensityDistribution权重校验 | 创建IntensityDistribution | zone1+zone2+zone3=100 | 验证通过 | P1 | 边界测试 |
| UT-TWIN-102 | models | frozen dataclass不可变性 | 创建RunnerStateVector | 尝试修改属性 | 抛出AttributeError | P1 | 边界测试 |
| UT-TWIN-103 | state_vector_builder | VO2max估算为None | 无VO2max数据 | 调用build_fitness() | vo2max_estimate=None | P1 | 异常测试 |
| UT-TWIN-104 | state_vector_builder | 静息心率为None | 无静息心率数据 | 调用build_body_signal() | resting_hr=None | P1 | 异常测试 |
| UT-TWIN-105 | state_vector_builder | HRV-RMSSD为None | 无HRV数据 | 调用build_body_signal() | hrv_rmssd=None | P1 | 异常测试 |
| UT-TWIN-106 | whatif_simulator | 推演周数边界 | weeks=1 | 调用simulate() | 返回1周快照 | P1 | 边界测试 |
| UT-TWIN-107 | whatif_simulator | 推演周数边界 | weeks=12 | 调用simulate() | 返回12周快照 | P1 | 边界测试 |
| UT-TWIN-108 | whatif_simulator | 推演周数超限 | weeks=13 | 调用simulate() | 抛出异常或截断 | P1 | 边界测试 |
| UT-TWIN-109 | whatif_simulator | 置信度下限 | 推演多周后 | 检查confidence | confidence>=0.0 | P1 | 边界测试 |
| UT-TWIN-110 | twin_engine | 缓存文件不存在 | 删除缓存文件 | 调用get_current_snapshot() | 重新计算并创建缓存 | P1 | 异常测试 |
| UT-TWIN-111 | twin_engine | 缓存文件损坏 | 缓存文件JSON格式错误 | 调用get_current_snapshot() | 重新计算并覆盖缓存 | P1 | 异常测试 |
| UT-TWIN-112 | twin_engine | 计划转换逻辑 | 有TrainingPlan | 调用_convert_training_plan() | 正确聚合为WeeklyPlanSpec | P1 | 功能测试 |
| UT-TWIN-113 | twin_engine | 计划转换空daily_plans | TrainingPlan.weeks有周但无daily_plans | 调用_convert_training_plan() | 正确处理空列表 | P1 | 边界测试 |
| UT-TWIN-114 | cli | twin status --json | CLI环境 | 执行`twin status --json` | JSON格式输出 | P1 | 功能测试 |
| UT-TWIN-115 | cli | twin simulate --json | CLI环境 | 执行`twin simulate --plan <id> --weeks 4 --json` | JSON格式输出 | P1 | 功能测试 |
| UT-TWIN-116 | cli | twin compare --json | CLI环境 | 执行`twin compare --plans <id1,id2> --json` | JSON格式输出 | P1 | 功能测试 |
| UT-TWIN-117 | cli | twin simulate参数校验 | weeks=0 | 执行`twin simulate --plan <id> --weeks 0` | 参数错误提示 | P1 | 边界测试 |
| UT-TWIN-118 | cli | twin compare参数校验 | plan_ids=1个 | 执行`twin compare --plans <id1>` | 参数错误提示 | P1 | 边界测试 |
| UT-TWIN-119 | agent | get_runner_state use_cache参数 | Agent环境 | 调用get_runner_state(use_cache=False) | 强制刷新 | P1 | 功能测试 |
| UT-TWIN-120 | exception | TwinEngineError继承 | 创建TwinEngineError | 检查isinstance(e, NanobotRunnerError) | True | P1 | 功能测试 |

### 4.3 P2边缘用例（可选覆盖）

| 用例ID | 所属模块 | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 用例类型 |
|--------|---------|---------|---------|---------|---------|--------|---------|
| UT-TWIN-201 | models | 极端VDOT值 | vdot=10.0或vdot=80.0 | 创建FitnessDimension | 正常存储 | P2 | 边界测试 |
| UT-TWIN-202 | models | 极端TSB值 | tsb=-50或tsb=50 | 创建LoadDimension | 正常存储 | P2 | 边界测试 |
| UT-TWIN-203 | models | 伤病风险边界 | injury_risk=0.0或100.0 | 创建RiskDimension | 正常存储 | P2 | 边界测试 |
| UT-TWIN-204 | state_vector_builder | 单点数据 | 仅1条训练记录 | 调用build() | data_quality=INSUFFICIENT | P2 | 边界测试 |
| UT-TWIN-205 | whatif_simulator | 零跑量计划 | weekly_volume_km=0 | 调用simulate_week() | 正常处理 | P2 | 边界测试 |
| UT-TWIN-206 | whatif_simulator | 超高强度计划 | intensity_multiplier=3.0 | 调用simulate_week() | 正常处理 | P2 | 边界测试 |
| UT-TWIN-207 | twin_engine | 并发缓存访问 | 多线程同时调用get_current_snapshot() | 检查缓存一致性 | 无竞态条件 | P2 | 并发测试 |
| UT-TWIN-208 | twin_engine | 缓存目录不存在 | 删除twin缓存目录 | 调用get_current_snapshot() | 自动创建目录 | P2 | 异常测试 |

---

## 5. 场景级集成测试用例

### 5.1 核心业务场景

| 场景ID | 场景名称 | 前置条件 | 测试步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|---------|--------|
| SC-01 | 跑者状态向量构建与缓存 | 有≥30天训练数据 | 1. 执行`twin status`<br>2. 记录响应时间<br>3. 再次执行`twin status`<br>4. 记录响应时间<br>5. 检查缓存文件 | 1. 5维度正确输出<br>2. 首次计算<3秒<br>3. 第二次命中缓存<br>4. 响应<500ms<br>5. 缓存文件存在且TTL=24h | P0 |
| SC-02 | 单计划What-If推演 | 有有效plan_id，数据充足 | 1. 执行`twin simulate --plan <id> --weeks 4`<br>2. 检查输出内容<br>3. 检查prediction_type标注 | 1. 推演结果完整<br>2. 包含4周快照<br>3. 标注prediction_type和置信度 | P0 |
| SC-03 | 多计划对比推演 | 有2-5个有效plan_id | 1. 执行`twin compare --plans <id1,id2,id3>`<br>2. 检查对比表格<br>3. 检查综合推荐 | 1. 对比表格正确<br>2. 包含VDOT/伤病/恢复维度<br>3. 综合推荐评分0-100 | P0 |
| SC-04 | 推演三层降级策略 | 准备三种数据状态 | 1. ML模型可用时推演<br>2. ML不可用时推演<br>3. Banister未拟合时推演 | 1. prediction_type=ml_enhanced<br>2. prediction_type=parametric<br>3. prediction_type=basic | P0 |
| SC-05 | 状态向量缓存刷新 | 缓存未过期 | 1. 执行`twin status --refresh`<br>2. 检查响应时间<br>3. 检查缓存更新时间 | 1. 重新计算<br>2. 响应时间<3秒<br>3. 缓存更新时间刷新 | P1 |
| SC-06 | 空数据降级 | 无训练数据 | 1. 执行`twin status`<br>2. 检查输出 | 1. data_quality=EMPTY<br>2. 零值填充<br>3. 提示"暂无数据" | P1 |
| SC-07 | 计划不存在异常 | 无效plan_id | 1. 执行`twin simulate --plan invalid_id`<br>2. 检查错误输出 | 1. 抛出TwinEngineError<br>2. 提示"计划不存在" | P1 |
| SC-08 | 推演性能验证 | 有有效plan_id | 1. 记录单计划4周推演时间<br>2. 记录3计划对比时间 | 1. <10秒<br>2. <30秒 | P1 |

---

## 6. E2E测试用例

### 6.1 用户旅程测试

| 场景ID | 场景名称 | 用户旅程 | 测试步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|---------|--------|
| E2E-01 | 查看当前跑者状态 | 用户执行`twin status` | 1. 启动CLI<br>2. 执行`twin status`<br>3. 检查输出格式和内容 | 1. Rich格式化输出<br>2. 5维度数据正确<br>3. 响应时间<3秒 | P0 |
| E2E-02 | 模拟训练计划效果 | 用户执行`twin simulate --plan <id> --weeks 4` | 1. 启动CLI<br>2. 执行模拟命令<br>3. 检查推演结果 | 1. 推演结果完整<br>2. 标注prediction_type<br>3. 包含每周快照 | P0 |
| E2E-03 | 对比多个训练计划 | 用户执行`twin compare --plans <id1,id2,id3>` | 1. 启动CLI<br>2. 执行对比命令<br>3. 检查对比结果 | 1. 对比表格正确<br>2. 综合推荐评分合理<br>3. 推荐最优计划 | P0 |
| E2E-04 | Agent查询跑者状态 | 用户问"我现在的状态如何？" | 1. 启动Agent<br>2. 输入查询<br>3. 检查Agent响应 | 1. Agent调用get_runner_state<br>2. 返回JSON格式<br>3. 5维度数据正确 | P0 |
| E2E-05 | Agent模拟计划效果 | 用户问"如果按计划A练4周会怎样？" | 1. 启动Agent<br>2. 输入查询<br>3. 检查Agent响应 | 1. Agent调用simulate_plan<br>2. 返回推演结果JSON<br>3. 包含每周快照 | P0 |
| E2E-06 | 缓存机制验证 | 同日内多次执行`twin status` | 1. 首次执行`twin status`<br>2. 记录时间<br>3. 再次执行<br>4. 记录时间 | 1. 首次计算<3秒<br>2. 第二次命中缓存<br>3. 响应<500ms | P1 |

---

## 7. 性能测试

### 7.1 性能指标

| 指标 | 目标 | 测试方法 |
|------|------|---------|
| 状态向量聚合 | <3秒 | 500条年度数据全量计算 |
| 单计划4周推演 | <10秒 | simulate_plan(plan_id, weeks=4) |
| 3计划对比推演 | <30秒 | compare_plans_by_ids([id1,id2,id3]) |
| 缓存命中响应 | <500ms | 同日内第二次调用get_current_snapshot() |
| CLI命令响应 | <5秒 | twin status/simulate/compare命令 |

### 7.2 性能测试场景

| 场景ID | 场景名称 | 数据规模 | 测试步骤 | 预期结果 |
|--------|---------|---------|---------|---------|
| PERF-01 | 状态向量聚合性能 | 500条训练记录 | 调用build()并计时 | <3秒 |
| PERF-02 | 单计划推演性能 | 4周推演 | 调用simulate()并计时 | <10秒 |
| PERF-03 | 多计划对比性能 | 3计划×4周 | 调用compare_plans_by_ids()并计时 | <30秒 |
| PERF-04 | 缓存命中性能 | 缓存已存在 | 调用get_current_snapshot(use_cache=True)并计时 | <500ms |

---

## 8. 测试数据准备

### 8.1 测试数据需求

| 数据类型 | 数据规模 | 用途 | 来源 |
|---------|---------|------|------|
| 训练记录 | 500条，覆盖18个月 | 状态向量构建、推演测试 | 脱敏真实数据或Mock |
| 训练计划 | 3-5个有效plan_id | 计划模拟、对比测试 | PlanManager创建测试计划 |
| 身体信号数据 | 90天 | 身体信号维度构建 | BodySignalEngine Mock |
| 预测模型数据 | ML模型已训练/未训练 | 三层降级测试 | PredictionEngine Mock |

### 8.2 Mock策略

| 模块 | Mock内容 | 不Mock内容 |
|------|---------|-----------|
| StateVectorBuilder | SessionRepository、PredictionEngine、BodySignalEngine | 聚合逻辑、降级策略 |
| WhatIfSimulator | BanisterIRModel、PredictionEngine | 推演循环、置信度衰减 |
| DigitalTwinEngine | StateVectorBuilder、PlanManager | 编排逻辑、缓存机制 |
| CLI Handler | DigitalTwinEngine | 命令解析、Rich格式化 |
| Agent工具 | DigitalTwinEngine | 工具注册、JSON序列化 |

---

## 9. 测试环境配置

### 9.1 测试环境

| 环境项 | 配置 |
|--------|------|
| 操作系统 | Windows 11 / macOS |
| Python版本 | 3.11+ |
| 包管理 | uv |
| 测试框架 | pytest |
| 覆盖率工具 | pytest-cov |
| Lint工具 | ruff |
| 类型检查 | mypy |

### 9.2 测试目录结构

```
tests/unit/core/twin/
├── __init__.py
├── test_models.py
├── test_state_vector_builder.py
├── test_whatif_simulator.py
├── test_twin_engine.py
└── test_context_twin.py

tests/integration/module/
├── test_twin_integration.py

tests/integration/scene/
├── test_twin_scenarios.py

tests/e2e/
├── test_twin_e2e.py
```

---

## 10. 测试进度计划

### 10.1 测试阶段

| 阶段 | 内容 | 准入条件 | 准出条件 |
|------|------|---------|---------|
| 单元测试 | 核心模块单元测试 | 代码提交完成 | 覆盖率达标，100%通过 |
| 模块集成测试 | 模块间交互测试 | 单元测试通过 | 集成场景100%通过 |
| 场景集成测试 | 核心业务场景测试 | 模块集成通过 | P0场景100%通过 |
| E2E测试 | 用户旅程端到端测试 | 场景集成通过 | P0用户旅程100%通过 |
| 性能测试 | 性能指标验证 | E2E测试通过 | 所有性能指标达标 |
| 回归测试 | v0.20/v0.19回归验证 | 全量测试通过 | 无回归缺陷 |

### 10.2 测试轮次

| 轮次 | 内容 | 目标 |
|------|------|------|
| 第1轮 | 单元测试+模块集成 | 核心功能验证 |
| 第2轮 | 场景集成+E2E | 业务流程验证 |
| 第3轮 | 性能测试+回归 | 全量验证 |
| 第4轮 | Bug修复回归 | 缺陷闭环 |

---

## 11. 风险与应对

### 11.1 测试风险

| 风险 | 等级 | 影响 | 应对措施 |
|------|------|------|---------|
| v0.20预测引擎未完全稳定 | 🔴 高 | 推演结果不准确 | 先验证v0.20回归，再测试twin |
| BanisterIRModel参数拟合失败 | 🟡 中 | 降级策略受影响 | 准备Mock参数，验证降级逻辑 |
| 缓存机制并发问题 | 🟡 中 | 缓存数据不一致 | 增加并发测试用例 |
| 测试数据不足 | 🟡 中 | 部分场景无法覆盖 | 使用Mock数据补充 |

### 11.2 质量风险

| 风险 | 等级 | 影响 | 应对措施 |
|------|------|------|---------|
| 推演精度不达标 | 🔴 高 | 用户体验差 | 明确标注"模拟结果，非确定性预测" |
| 性能指标不达标 | 🟡 中 | 响应慢 | 优化数据查询，增加缓存 |
| 缓存命中率低 | 🟡 中 | 重复计算 | 检查TTL逻辑，优化缓存策略 |

---

## 12. 测试交付物

| 交付物 | 路径 | 说明 |
|--------|------|------|
| 测试策略文档 | `/docs/test/strategy_v0.21.0.md` | 本文档 |
| 全量测试用例清单 | `/docs/test/test_cases_v0.21.0.md` | 用例详细清单 |
| 单元测试代码 | `tests/unit/core/twin/` | 单元测试脚本 |
| 集成测试代码 | `tests/integration/scene/test_twin_scenarios.py` | 场景集成测试脚本 |
| E2E测试代码 | `tests/e2e/test_twin_e2e.py` | E2E测试脚本 |
| 轮次测试报告 | `/docs/test/reports/测试报告_v0.21.0_轮次N.md` | 每轮测试报告 |
| Bug清单 | `/docs/test/reports/Bug清单_v0.21.0.md` | 缺陷跟踪清单 |
| 全量测试报告 | `/docs/test/reports/测试报告_v0.21.0_全量.md` | 最终测试报告 |

---

## 13. 上线门禁评估

### 13.1 上线标准

| 门禁项 | 标准 | 状态 |
|--------|------|------|
| P0用例通过率 | 100% | ⬜ 待验证 |
| P1用例通过率 | ≥90% | ⬜ 待验证 |
| 致命/严重bug | 0个 | ⬜ 待验证 |
| 一般bug修复率 | ≥90% | ⬜ 待验证 |
| 核心业务流程 | 全量闭环 | ⬜ 待验证 |
| 性能指标 | 全部达标 | ⬜ 待验证 |
| 缓存命中率 | >90% | ⬜ 待验证 |

### 13.2 上线风险评估

| 风险项 | 评估 | 建议 |
|--------|------|------|
| 推演精度 | 受限于Banister IR模型，v0.21为MVP版本 | 明确标注"模拟结果，非确定性预测" |
| 数据依赖 | 依赖v0.20/v0.19模块稳定性 | 先完成回归测试 |
| 缓存机制 | 首次实现，可能存在边界问题 | 增加异常测试覆盖 |

---

## 14. 附录

### 14.1 术语表

| 术语 | 定义 |
|------|------|
| RunnerStateVector | 跑者状态向量，5维度综合状态 |
| What-If推演 | 模拟训练计划执行后的状态演变 |
| StateVectorBuilder | 状态向量构建器 |
| WhatIfSimulator | What-If推演器 |
| DigitalTwinEngine | 数字孪生引擎（薄编排层） |
| HypotheticalPlan | 假设计划（v0.21仅支持系统计划引用） |
| SimulationResult | 推演结果 |
| PlanComparison | 计划对比结果 |
| TTL | Time To Live，缓存存活时间 |

### 14.2 参考文档

- [需求规格说明书 v8.4](../requirements/REQ_需求规格说明书.md)
- [架构设计说明书 v8.0.0](../architecture/架构设计说明书.md)
- [产品规划方案 v9.1](../product/产品规划方案.md)
- [v0.21数字孪生引擎设计规格 v1.1](../superpowers/specs/2026-05-10-v0.21-digital-twin-design.md)
- [测试策略与规范 v3.1](./测试策略与规范.md)
- [v0.20.1 测试策略](./strategy_v0.20.1.md)
