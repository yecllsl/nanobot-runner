# 更新日志

本文档记录 Nanobot Runner 的所有重要变更。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

> **历史版本归档**: [docs/archive/changelog/](docs/archive/changelog/)

---

## [0.25.0] - 2026-05-22

### 版本主题
**自适应进化控制** —— 进化触发规则引擎、提示参数调优、月度进化报告

> **版本说明**: v0.25.0 是Phase C（自适应进化引擎）的第三个版本，新增进化触发控制器、提示参数调优器和月度进化报告生成器，实现AI决策的自适应进化闭环。

**本版本已实现**:
- ✅ EvolutionController: 4触发规则(VDOT误差/连续拒绝/新数据积累/月度复盘) + persist-first执行
- ✅ PromptTuner: 4维参数空间(tone/detail/aggressive/data_driven) + 地板保护 + 弹回机制
- ✅ EvolutionReporter: 月度进化报告生成
- ✅ 5个新数据模型: EvolutionAction/TriggerCheckResult/PromptTuningParams/EvolutionReport/IncrementalLearnResult
- ✅ 3条CLI命令: evolution triggers/report/tune
- ✅ 3个Agent工具: check_evolution_triggers/get_evolution_report/adjust_prompt_params
- ✅ DecisionLogHook after_iteration回调: 自动检查进化触发条件

### Added
- EvolutionController: 4 trigger rules (VDOT误差/连续拒绝/新数据积累/月度复盘) with persist-first execution
- PromptTuner: 4-dim parameter space (tone/detail/aggressive/data_driven) with floor protection and bounce-back
- EvolutionReporter: Monthly evolution report generation
- EvolutionAction, TriggerCheckResult, PromptTuningParams, EvolutionReport, IncrementalLearnResult data models
- CLI commands: `evolution triggers`, `evolution report`, `evolution tune`
- Agent tools: check_evolution_triggers, get_evolution_report, adjust_prompt_params
- DecisionLogHook after_iteration callback for automatic evolution trigger checking

### Fixed
- H-01: DecisionLogHook holds EvolutionEngine reference (orchestration layer consistency)
- H-02: IncrementalLearnResult for structured partial failure tracking
- H-03: Parameter floor protection (aggressive>=0.1, data_driven>=0.2) with bounce-back mechanism
- PromptTuningParams.with_updates() data_driven logic bug fix
- EvolutionController rejection trigger checking wrong field (outcome vs decision)
- ResponseAnalyzer missing days parameter in get_decision_outcome_pairs call

---

## [0.24.0] - 2026-05-21

### 版本主题
**个性化学习** —— 测试验证体系升级，为v0.24个性化学习功能交付奠定质量基础

> **⚠️ 版本说明**: v0.24.0 是Phase C（自适应进化引擎）的第二个版本，完成测试验证阶段全部工作，产出测试策略、测试报告、Bug修复、回归测试报告及上线结论，确认代码库基线质量达标。

**本版本已实现**:
- ✅ 测试策略制定（34个测试用例覆盖P0+P1全部验收标准）
- ✅ 全量单元测试基线建立（3937 passed, 0 failed, 覆盖率81%）
- ✅ BUG-V024-001修复（工具计数断言51→54，expected_names补充）
- ✅ 回归测试验证通过（7/7上线门禁全部满足）
- ✅ 上线结论：建议上线

### 测试验证

#### 测试策略（TST-01）
- 覆盖需求：REQ-0.24-01(P0) 5/5 AC、REQ-0.24-02(P1) 6/6 AC、REQ-0.24-03(P1) 4/4 AC
- 核心测试用例：34个，覆盖功能/边界/异常/算法/向后兼容
- 架构评审整改验证：4项HIGH问题整改全部覆盖

#### 测试执行（TST-02）
- 全量单元测试：3838 passed（修复后3937 passed），1 skipped
- 覆盖率：81%（核心模块85-100%）
- Bug发现：1个LOW级（测试断言过期），生产代码0 Bug

#### Bug修复（DEV-02）
- BUG-V024-001：工具数量断言值51→54，expected_names补充
- 修复方式：TDD流程（确认失败→修改断言→验证通过）
- 修复验证：2/2 passed，全量回归0退化

#### 回归测试（TST-03）
- 修复后全量：3937 passed, 0 failed, 1 skipped
- 上线门禁：7/7全部通过（P0+P1 100%、致命Bug=0、严重Bug=0、覆盖率≥80%、核心流程≥95%、v0.23回归无破坏、修复验证通过）
- **上线结论：建议上线**

### 文档产出
- `docs/test/strategy_v0.24.0.md` - 测试策略
- `docs/test/测试报告_v0.24.0.md` - 测试报告
- `docs/test/Bug清单_v0.24.0.md` - Bug清单
- `docs/test/回归报告_v0.24.0.md` - 回归报告
- `docs/test/上线结论_v0.24.0.md` - 上线结论

---

## [0.23.0] - 2026-05-20

### 版本主题
**决策追踪模块** —— AI决策自动记录、结果回填、用户反馈收集、自适应进化引擎基础

> **⚠️ 版本说明**: v0.23.0 是Phase C（自适应进化引擎）的首个版本，新增决策追踪模块，实现AI决策自动记录与结果回填，为v0.24个性化学习和v0.25自适应进化奠定基础。

**本版本已实现**:
- ✅ 决策日志自动记录（DecisionLogHook无侵入接入）
- ✅ 结果回填机制（执行忠实度、预测准确度）
- ✅ 用户反馈收集（评分/文本/采纳状态）
- ✅ CLI命令组（evolution status/history/feedback/accuracy/fidelity）
- ✅ Agent工具集成（check_plan_execution/check_prediction_accuracy）
- ✅ 按月分片Parquet存储（decisions/outcomes）
- ✅ EvolutionConfig配置Schema（环境变量覆盖支持）

### 新增功能

#### 决策追踪模块（Evolution Engine）
- **DecisionLog**: 冻结数据类，10个字段，记录AI决策完整上下文
- **OutcomeRecord**: 冻结数据类，11个字段，记录决策执行结果
- **DecisionLogHook**: 继承AgentHook，无侵入接入Agent生命周期
- **EvolutionStore**: 按月分片Parquet存储，支持决策/结果配对查询
- **OutcomeCollector**: 执行忠实度计算、预测准确度评估、反馈收集
- **EvolutionEngine**: 决策追踪引擎编排层，统一接口

#### CLI命令组
- `uv run nanobotrun evolution status` - 查看进化状态
- `uv run nanobotrun evolution history [--start] [--end] [--type]` - 查询决策历史
- `uv run nanobotrun evolution feedback <decision_id> --score [--text] [--accepted]` - 提交反馈
- `uv run nanobotrun evolution accuracy [--days 30]` - 查看预测准确度
- `uv run nanobotrun evolution fidelity [--days 30]` - 查看执行忠实度

#### Agent工具
- `check_plan_execution()` - 检查计划执行忠实度
- `check_prediction_accuracy()` - 检查预测准确度

### 技术改进

#### 架构优化
- **Hook独立注册**: DecisionLogHook独立继承AgentHook，避免与ObservabilityHook状态竞争
- **依赖注入扩展**: AppContext新增evolution_engine属性
- **配置驱动**: EvolutionConfig遵循Pydantic-Settings模式，支持环境变量覆盖
- **执行忠实度公式**: 简化为`fidelity = 1 - (0.55 * 体积偏差 + 0.45 * 时间偏差)`

#### 数据模型
- **execution_status**: 统一为5种状态（pending/executed/skipped/modified/failed）
- **prediction_direction**: 新增字段（overestimate/underestimate/accurate/None）
- **runner_state摘要**: 5个关键指标（vdot/ctl/atl/tsb/fatigue_score）

---

## [0.22.1] - 2026-05-19

### 版本主题
**代码质量重构** —— 代码审查问题修复、架构优化、类型安全提升

> **⚠️ 版本说明**: v0.22.1 是代码质量专项重构版本，基于代码审查报告进行系统性修复，无新增功能模块。

**本版本已实现**:
- ✅ 修复17处 `# type: ignore` 注解，替换为正确类型提示
- ✅ 替换所有裸 `Exception` 为 `NanobotRunnerError` 自定义异常
- ✅ 修复 `ImportError` 与内置函数冲突问题
- ✅ 消除跨模块代码重复（Layer3去重）
- ✅ 拆分大文件为领域专用模块（Layer4）
- ✅ 清理重复方法、集中常量管理、合并测试文件（Layer5）

### 代码质量改进

#### 类型安全提升
- **修复type:ignore**: 17处类型忽略注解替换为正确类型提示
- **增强类型覆盖**: 核心模块类型注解覆盖率提升至≥80%

#### 异常处理规范化
- **统一异常类型**: 替换所有裸 `Exception` 为 `NanobotRunnerError`
- **修复命名冲突**: `ImportError` 重命名为 `DataImportError` 避免与内置函数冲突

#### 架构优化
- **去重优化**: 消除跨模块代码重复，统一公共逻辑
- **文件拆分**: 将大文件拆分为领域专用模块，提升可维护性
- **常量集中**: 集中管理常量，避免重复定义
- **测试合并**: 合并相关测试文件，减少测试碎片化

### 重构详情

#### Layer 1: 异常处理修复
- 替换 `except Exception` 为 `except NanobotRunnerError`
- 修复 `ImportError` 命名冲突

#### Layer 2: 类型注解修复
- 修复17处 `# type: ignore` 注解
- 补充缺失的类型提示

#### Layer 3: 代码去重
- 识别并消除跨模块重复代码
- 提取公共函数到独立模块

#### Layer 4: 文件拆分
- 拆分大文件为领域专用模块
- 优化模块边界和依赖关系

#### Layer 5: 清理与优化
- 删除重复方法定义
- 集中常量管理
- 合并相关测试文件

---

## [0.22.0] - 2026-05-18

### 版本主题
**质量收口版本** —— UAT验证、缺陷收敛、质量兜底、发布准备

> **⚠️ 版本说明**: v0.22.0 是Phase A（数字孪生跑者）的收官版本，聚焦质量验证与稳定性提升，无新增功能模块。

**本版本已实现**:
- ✅ UAT全面验证（数字孪生/ML预测/身体信号/数据管理/系统性能五大模块）
- ✅ 缺陷收敛（修复10+高优先级缺陷，修复率100%）
- ✅ 质量兜底（核心模块测试覆盖率≥80%，性能基准达标）
- ✅ 需求洞察（用户反馈收集与分析机制）
- ✅ 发布准备（文档同步、版本归档、发布检查清单）

### 质量改进

#### UAT验证
- **数字孪生模块UAT**: What-If推演、计划对比、状态向量生成全面验证
- **ML预测模块UAT**: VDOT趋势预测、比赛成绩预测、伤病风险预测验证
- **身体信号模块UAT**: HRV分析、疲劳度评估、恢复状态监控验证
- **数据管理UAT**: FIT导入、去重机制、统计分析验证
- **系统性能UAT**: 大数据量处理、内存占用、响应时间验证

#### 缺陷修复
- 修复数字孪生推演置信度计算精度问题
- 修复ML预测模型冷启动边界条件处理
- 修复身体信号分析数据缺失降级策略
- 修复Gateway Agent工具调用超时问题
- 修复CLI命令帮助信息不一致问题

#### 性能优化
- 优化Parquet查询性能（大数据量场景）
- 优化状态向量缓存刷新机制
- 优化ML模型加载内存占用

### 文档更新
- 同步更新CLI使用指南、API参考文档
- 更新架构设计说明书（v0.22质量收口架构）
- 完善发布检查清单和分支管理规范

---

## [0.21.0] - 2026-05-12

### 版本主题
**数字孪生引擎** —— 构建可推演的跑者生理模型，实现 What-If 推演能力

> **⚠️ 版本说明**: v0.21.0 在v0.20.1预测能力基础上，构建了**跑者数字孪生模型**，让用户"在训练前看到训练后的自己"。

**本版本已实现**:
- ✅ 5维度跑者状态向量（体能/负荷/身体信号/风险/训练模式）
- ✅ What-If 训练计划推演（逐周模拟VDOT/负荷/伤病变化）
- ✅ 多计划对比与智能推荐（评分算法自动推荐最优计划）
- ✅ `twin` CLI命令组（snapshot/simulate/compare）
- ✅ 3个Agent数字孪生工具（get_twin_snapshot/simulate_twin/compare_twin_plans）
- ✅ 状态向量24h缓存机制（TTL自动过期）
- ✅ 推演三层降级策略（ML增强→参数化→基础）
- ✅ 完整集成测试覆盖（StateVectorBuilder/WhatIfSimulator/DigitalTwinEngine）

### 新增功能

#### 数字孪生引擎核心
- **5维度状态向量**: 聚合体能(VDOT)、负荷(CTL/ATL/TSB)、身体信号(疲劳/恢复)、风险(伤病概率)、训练模式(周跑量/强度分布)
- **薄编排层架构**: DigitalTwinEngine作为编排器，复用v0.20 PredictionEngine/BodySignalEngine/TrainingLoadAnalyzer
- **状态向量缓存**: 计算后缓存24h，存储到 `~/.nanobot-runner/twin/state_vector.json`

#### What-If 推演能力
- **逐周推演**: 基于Banister IR模型逐周计算体能/疲劳变化，支持ML修正
- **周TSS估算**: 根据训练计划强度分布估算每周训练负荷
- **置信度衰减**: 推演周数越多置信度越低（L1每周-5%，L2每周-8%，L3每周-12%）
- **计划对比评分**: 综合VDOT提升(40%)、伤病风险(35%)、恢复余量(25%)自动推荐最优计划

#### CLI命令组 (twin)
- `twin snapshot`: 查看当前5维度跑者状态快照
- `twin simulate --plan-id <id>`: 推演指定训练计划效果
- `twin compare --plan-ids <id1,id2>`: 对比多个训练计划并推荐最优

#### Agent工具集成
- `get_twin_snapshot`: 获取当前跑者状态向量
- `simulate_twin`: 模拟训练计划效果
- `compare_twin_plans`: 对比多个训练计划

### 架构改进
- 新增 `src/core/twin/` 模块: DigitalTwinEngine/StateVectorBuilder/WhatIfSimulator
- 新增 `src/cli/commands/twin.py`: twin命令组CLI
- 更新 `src/core/base/context.py`: 新增twin_engine延迟属性
- 复用v0.20 PredictionEngine/TrainingResponsePredictor/BanisterIRModel
- 复用v0.19 BodySignalEngine/TrainingLoadAnalyzer

### 测试覆盖
- 新增单元测试: test_state_vector_builder.py, test_whatif_simulator.py, test_twin_engine.py
- 覆盖场景: 5维度构建、数据缺失降级、逐周推演、置信度衰减、计划对比评分、缓存一致性

---

## [0.20.1] - 2026-05-11

### 版本主题
**ML预测增强** - VDOT/伤病/比赛预测全面启用ML训练与推理，数据充足时自动启用ML模型

> **⚠️ 版本说明**: v0.20.1 在v0.20.0架构基础上，完成了ML预测层的**训练与推理实现**，数据充足的用户现在可以享受更精准的ML增强预测。

**本版本已实现**:
- ✅ VDOT趋势预测ML训练（GradientBoosting分位数回归 p10/p50/p90）
- ✅ VDOT趋势预测ML推理 + SHAP特征重要性分析
- ✅ 伤病风险预测ML训练（LR+GBDT集成模型）
- ✅ 伤病风险预测ML推理 + SHAP风险因子归因
- ✅ 比赛成绩预测个人化模型（Riegel曲线拟合 + 跑者类型学习）
- ✅ 训练响应预测器（TSB/恢复调整）
- ✅ ModelManager持久化（sklearn兼容、predictions.parquet、回滚支持）
- ✅ `predict model` CLI子命令组（status/train/rollback）
- ✅ 新增Agent工具：ReportInjuryTool、ManagePredictionModelTool
- ✅ 完整集成测试覆盖（E2E预测流程、降级链、跨模块数据流）

### 新增功能

#### VDOT ML增强预测
- **GradientBoosting分位数回归**: 训练p10/p50/p90三个分位数模型，提供置信区间
- **SHAP特征重要性**: 自动分析影响VDOT变化的关键因素（训练负荷、HRV、疲劳度等）
- **冷启动自动训练**: 数据充足时自动触发模型训练，无需手动干预
- **同日缓存机制**: 避免重复计算，提升响应速度

#### 伤病风险ML增强预测
- **LR+GBDT集成模型**: 逻辑回归提供基线风险，GBDT捕捉非线性风险模式
- **SHAP风险因子归因**: 识别主要风险因素及贡献度（如急性负荷突增、连续高强度训练）
- **三级预警系统**: 高/中/低风险分级，附带针对性预防建议
- **时间轴预测**: 未来21天伤病风险概率曲线

#### 个人化比赛成绩预测
- **Riegel曲线拟合**: 基于个人历史比赛/训练数据校准个人Riegel指数
- **跑者类型学习**: 自动识别跑者类型（速度型/耐力型/均衡型），调整预测策略
- **赛前状态调整**: 基于当前TSB/疲劳度调整预测成绩

#### 模型管理增强
- **模型持久化**: 训练完成的模型自动保存到 `~/.nanobot-runner/models/`
- **模型版本管理**: 跟踪模型版本、训练时间、验证误差
- **模型回滚**: 支持回滚到上一个稳定模型版本
- **CLI命令**: `nanobotrun predict model status/train/rollback`

### 架构改进
- 更新 `src/core/prediction/vdot_predictor.py`: 实现ML训练/推理、SHAP分析
- 更新 `src/core/prediction/injury_predictor.py`: 实现LR+GBDT集成训练/推理
- 更新 `src/core/prediction/race_predictor.py`: 实现Riegel拟合、跑者类型分类
- 更新 `src/core/prediction/training_response_predictor.py`: 实现TSB/恢复调整
- 更新 `src/core/prediction/model_manager.py`: 实现模型持久化、版本管理、回滚
- 新增 `src/cli/commands/prediction.py`: `model`子命令组
- 新增 `src/agents/tools.py`: ReportInjuryTool、ManagePredictionModelTool
- 更新 `src/core/base/context.py`: 新增prediction_engine延迟属性

### 测试覆盖
- 新增ML训练/推理单元测试（SHAP、集成权重、标签持久化、跑者分类）
- 新增E2E集成测试（完整预测流程、降级链、跨模块数据流）
- 所有预测器通过基准测试验证

---

## [0.20.0] - 2026-05-09

### 版本主题
**ML增强预测** - 为数据充足用户提供更精准的未来洞察，数据不足时自动降级

> **⚠️ 版本范围说明**: v0.20.0 完成了ML增强预测的**完整架构搭建**、**三层降级策略**和**CLI命令组**，所有预测功能可正常使用。
> 
> **本版本已实现**:
> - ✅ 完整的三层降级架构（ML增强 → 参数化基线 → 基础预测）
> - ✅ 数据充足度评估器（自动判断使用哪一层预测）
> - ✅ 特征工程模块（VDOT/伤病/比赛特征提取）
> - ✅ 参数化基线模型（Banister IR、规则基线、逻辑回归）
> - ✅ 模型生命周期管理（保存/加载/版本管理/回滚）
> - ✅ 完整的CLI命令组（predict status/vdot/race/injury-risk/model）
> - ✅ 7个Agent预测工具集成
> - ✅ 同日缓存机制
> 
> **v0.20.1 补充计划**:
> - 🔄 VDOT趋势预测的ML训练与推理（GradientBoosting分位数回归 + SHAP分析）
> - 🔄 伤病风险预测的ML训练与推理（LR+GBDT集成 + SHAP风险因子）
> - 🔄 比赛成绩预测的个人化模型训练（Riegel曲线拟合 + 跑者类型学习）
> 
> 当前版本中，数据充足时预测器会使用参数化基线模型（Banister IR/逻辑回归）提供预测，确保功能可用。ML增强层将在v0.20.1中基于积累的历史训练数据完成训练后启用。

### 新增功能

#### ML-VDOT趋势预测引擎
- **三层降级架构**: ML增强 → 参数化基线(Banister IR) → 基础预测(线性回归)
- **数据充足度评估**: 自动评估历史数据是否满足ML训练要求(18个月+/500+条记录)
- **特征工程**: 时序特征、负荷特征、身体信号特征提取
- **SHAP可解释性**: 提供预测结果的关键影响因素分析
- **置信区间**: 提供预测值的置信区间范围
- **CLI命令**: `nanobotrun predict vdot --days 30`

#### 个人化比赛成绩预测
- **Riegel公式个性化**: 基于个人历史比赛数据校准Riegel指数
- **配速策略生成**: 为预测比赛生成分段配速策略
- **最佳/最差情况**: 提供比赛成绩的乐观/悲观预测
- **赛前调整建议**: 基于当前状态给出赛前训练调整建议
- **CLI命令**: `nanobotrun predict race --distance 42.195`

#### ML伤病风险预测
- **多维度风险评估**: 急性负荷风险、慢性累积风险、身体信号风险
- **时间轴预测**: 未来21天伤病风险概率曲线
- **风险因素分析**: 识别主要风险因素及贡献度
- **三级预警**: 高/中/低风险分级预警
- **预防措施建议**: 基于风险类型给出针对性预防建议
- **CLI命令**: `nanobotrun predict injury --days 21`

#### 模型管理与校准
- **自动模型训练**: 数据充足时自动触发模型训练
- **模型版本管理**: 跟踪模型版本、训练时间、验证误差
- **模型性能监控**: 监控预测准确度，触发重新训练
- **人工校准接口**: 支持用户反馈校准预测结果
- **CLI命令**: `nanobotrun predict model status/train/calibrate`

#### 训练响应预测
- **负荷-响应关系**: 预测特定训练负荷下的身体响应
- **What-If推演**: 模拟不同训练方案的效果
- **个性化因子**: 基于个人历史响应模式个性化预测

### 架构改进
- 新增 `src/core/prediction/` 模块：预测引擎核心模块
  - `models.py`: 所有frozen dataclass数据模型
  - `config.py`: PredictionConfig配置类
  - `feature_engine.py`: 特征工程模块
  - `data_assessor.py`: 数据充足度评估
  - `vdot_predictor.py`: VDOT趋势预测引擎
  - `race_predictor.py`: 比赛成绩预测
  - `injury_predictor.py`: 伤病风险预测
  - `training_response_predictor.py`: 训练响应预测
  - `model_manager.py`: 模型生命周期管理
  - `prediction_engine.py`: 预测引擎编排层
  - `baselines/`: 基线模型(Banister IR、规则/逻辑回归伤病模型)
- 新增 `src/cli/commands/prediction.py`: predict命令组CLI
- 新增 `src/cli/handlers/prediction_handler.py`: 预测业务逻辑调用层
- 更新 `src/core/base/context.py`: 新增prediction_engine等延迟属性
- 更新 `src/agents/tools.py`: 新增7个Agent预测工具

### 技术栈更新
- 新增依赖: `scikit-learn>=1.5.0` (ML模型)
- 新增依赖: `scipy>=1.10.0` (科学计算)
- 新增依赖: `shap>=0.48.0` (模型可解释性)
- 新增依赖: `joblib>=1.3.0` (模型序列化)

### 质量门禁
- 新增预测模块完整单元测试覆盖
- 所有预测器通过基准测试验证
- 代码变更经过审查，无破坏性变更
- 文档更新完整，版本号一致

---

## [0.19.0] - 2026-05-06

### 版本主题
**让身体信号"会说话"** - 深度分析与自定义扩展，让跑者读懂身体信号

### 新增功能

#### 心率变异（HRV）分析
- **静息心率趋势**: 支持7/30/90天趋势查看，识别体能变化
- **心率恢复分析**: 运动后1分钟/3分钟心率恢复率计算
- **心率漂移检测**: 长距离跑步中心率漂移>10%预警
- **HRV基础统计**: 基于现有心率数据估算RMSSD/SDNN
- **CLI命令**: `nanobotrun analysis hrv --days 30`

#### 疲劳度与恢复评估
- **综合疲劳度评分**: 0-100分量化当前疲劳状态
- **恢复状态指示器**: 红/黄/绿三色状态指示
- **连续训练日监控**: 7天内高强度训练次数统计
- **休息日效果评估**: 对比休息前后关键指标变化
- **CLI命令**: `nanobotrun analysis fatigue/recovery`

#### 身体信号智能解读
- **异常信号预警**: 静息心率突增>10%预警
- **训练建议生成**: 基于身体状态给出可执行建议
- **身体信号摘要**: 每日/每周身体信号一句话总结
- **CLI命令**: `nanobotrun status today/weekly`

#### 深度对比分析 (P1)
- **周期对比**: 支持同期对比（如今年vs去年）
- **相似训练对比**: 按距离/配速筛选相似训练对比
- **训练负荷-表现关联**: 散点图显示负荷与表现关系

### 架构改进
- 新增 `src/core/analysis/hrv.py` 模块：心率变异分析引擎
- 新增 `src/core/analysis/fatigue.py` 模块：疲劳度评估引擎
- 新增 `src/core/analysis/body_signals.py` 模块：身体信号解读引擎
- 新增 `src/cli/commands/status.py` CLI命令模块

### 质量门禁
- 新增身体信号分析模块单元测试覆盖
- 代码变更经过审查，无破坏性变更
- 文档更新完整，版本号一致

---

## [0.18.0] - 2026-05-04

### 新增功能

#### 数据可视化模块
- **终端图表系统**: 基于 plotext 的终端内数据可视化渲染
- **VDOT 趋势图**: 支持 7/30/90/365 天时间范围的 VDOT 变化趋势折线图
- **训练负荷曲线**: CTL/ATL/TSB 三线同屏显示，TSB 正负区域颜色区分
- **心率区间分布**: 指定日期范围内的心率区间堆叠柱状图
- **CLI 命令**: `nanobotrun viz vdot/load/hr-zones`

#### 数据导出模块
- **多格式导出**: 支持 CSV/JSON/Parquet 格式导出跑步数据
- **灵活筛选**: 支持按日期范围、数据字段筛选导出
- **CLI 命令**: `nanobotrun export sessions --format csv/json/parquet`

### 核心模块增强

#### 用户画像引擎优化
- **双存储增强**: `save_profile_json` 支持接受 `RunnerProfile` 对象或字典，提升 API 灵活性
- **类型安全**: 完善类型注解，支持 `dict[str, Any]` 输入

#### 初始化向导改进
- **智能回退机制**: 迁移失败时（nanobot 配置不存在），自动回退到 FRESH 模式重新初始化
- **Force 模式增强**: `--force` 模式下自动处理配置缺失场景

### 架构改进
- 新增 `src/core/export/` 模块：数据导出引擎
- 新增 `src/core/visualization/` 模块：可视化渲染引擎
- 新增 `src/cli/commands/viz.py` 和 `export.py` CLI 命令模块

### 文档优化
- **v0.17.0 文档归档**: 将 v0.17.0 版本文档移至 archive 目录
- **UAT 测试用例新增**: 新增 cron 提醒、偏好设置、技能系统、透明化模块测试用例

### 质量门禁
- 新增集成测试和单元测试覆盖可视化与导出模块
- 代码变更经过审查，无破坏性变更
- 文档归档完整，保持项目目录整洁

---

## [0.17.0] - 2026-05-03

### 新增功能

#### Hook 组合系统
- **Hook 管理器**: 支持多 Hook 注册、执行链管理、优先级调度
- **流式输出 Hook**: 实时流式响应处理，支持 Gateway 集成
- **进度 Hook**: 训练计划执行进度追踪与通知
- **错误处理 Hook**: AI 决策异常自动分类与诊断建议

#### Subagent 架构
- **子智能体管理器**: 支持 data_analyst、report_writer、plan_optimizer 等角色
- **子智能体工具**: `SpawnSubagentTool` 支持动态创建子智能体执行任务
- **任务委派**: 主 Agent 可将复杂任务委派给专业子智能体

#### 异步用户确认系统
- **确认场景管理**: 支持训练计划确认、RPE 反馈收集、伤病风险调整
- **结构化提示生成**: 自动构建带选项的用户确认提示
- **响应解析**: 支持选项选择、关键词匹配、自然语言理解
- **CLI 回退**: 无异步接口环境下的命令行确认支持

#### Cron 训练提醒
- **训练提醒管理器**: 基于用户训练计划的智能提醒调度
- **Cron 回调处理器**: 定时任务注册与执行，支持飞书通知
- **Gateway 集成**: Gateway 服务启动时自动注册训练提醒任务
- **天气感知**: 提醒时可选查询天气并给出训练建议

#### LLM 超时控制
- **超时控制器**: 为 LLM 调用提供超时保护和优雅降级
- **多种策略**: 支持 RAISE、RETURN_NONE、FALLBACK、RETRY 策略
- **装饰器支持**: `create_timeout_decorator` 便捷装饰器函数

### CLI 命令扩展
- `nanobotrun gateway start` - 启动 Gateway 服务（集成 Hook、Cron、MCP）

### 质量门禁
- 单元测试 2847 个，通过率 100%
- 测试覆盖率 81%（core 模块达标）
- ruff format/check 0 错误
- mypy 类型检查 0 错误

---

## [0.16.1] - 2026-04-29

### Bug修复

#### 测试目录结构重构
- 重构测试目录结构以对齐源码结构
- 测试文件路径从 `tests/unit/{模块}/` 迁移到 `tests/unit/core/{模块}/`
- 提升代码可维护性和可读性

### 版本更新
- `pyproject.toml`: 0.16.0 → 0.16.1

---

## [0.16.0] - 2026-04-29

### 架构重构

#### Core 模块化重构
- **base/**: 基础设施模块 - 异常体系、日志管理、装饰器、结果模型、数据校验模式、上下文管理、用户档案
- **calculators/**: 计算器模块 - VDOT计算、比赛预测、心率分析、训练负荷分析、训练历史分析、伤病风险分析、统计聚合
- **config/**: 配置模块 - 配置管理、配置模式、LLM配置、环境变量管理、备份管理、配置同步
- **storage/**: 存储模块 - Parquet存储管理、会话仓库、索引管理、FIT解析、导入服务
- **report/**: 报告模块 - 报告生成、报告服务、异常数据过滤
- **models/**: 模型模块 - 用户档案模型、训练计划模型、分析相关模型（从1200+行大文件拆分）

#### 向后兼容
- 所有 `__init__.py` 提供完整的公共 API 重导出
- 模块间导入路径已正确更新
- 无破坏性变更

### 测试覆盖
- 单元测试 2749 个，通过率 100%
- 集成测试 272 个，通过率 100%
- E2E测试 80 个，通过率 100%
- 整体覆盖率 82%

### 质量门禁
- ruff format/check 通过
- mypy 类型检查 0 错误
- bandit 安全扫描通过（15个低风险历史遗留告警）

---

## [0.15.0] - 2026-04-28

### 新增功能

#### AI 决策透明化模块
- **透明化引擎**: 决策过程追踪、工具调用追踪、决策链路可视化
- **可观测性管理器**: AI 状态仪表盘、训练洞察报告、性能指标采集
- **追踪日志器**: 结构化决策树日志、多层级嵌套追踪、日志持久化
- **透明化展示**: Rich 表格展示、Markdown 洞察报告、时间线展示

#### 报告导出功能增强
- `report generate --output` 支持周报/月报导出为 Markdown 文件

#### 核心解析器增强
- 新增 Mock 文件检测，提升 FIT 解析健壮性

### CLI 命令扩展
- `nanobotrun transparency trace` - 查看 AI 决策追踪日志
- `nanobotrun transparency status` - 查看 AI 状态仪表盘
- `nanobotrun transparency insight` - 生成训练洞察报告
- `nanobotrun report generate --type weekly/monthly --output` - 导出报告

### 架构改进
- 新增 `src/core/transparency/` 模块，通过 Hook 机制无侵入式接入 AI 决策流程

### 测试覆盖
- 新增 73 个测试用例，整体通过率 100%
- 透明化引擎覆盖率 92%，可观测性管理器 80%

### CI/CD 修复
- 修复清华镜像源 403 错误（设为非默认源）
- 修复 ANSI 转义码导致测试失败问题
- 修复 Python 3.12 测试依赖安装失败问题

---

## [0.13.0] - 2026-04-27

### 新增功能

#### 智能技能生态版
- **MCP 工具管理基础设施**: ToolManager、MCPConfigHelper、自动发现/注册
- **天气 Agent 工具**: 自然语言天气查询、训练计划集成
- **地图 Agent 工具**: 路线规划、路线分析
- **健康数据 Agent 工具**: COROS 睡眠/HRV 数据同步与分析

#### CLI 工具管理命令
- `tools list/add/remove/enable/disable/import-claude/validate`

### 测试覆盖
- 新增 102+ 单元测试，工具管理器覆盖率 95%

---

## [0.12.0] - 2026-04-19

### 新增功能

#### 预测规划层
- **目标达成评估引擎**: 全马/半马完赛时间预测、置信区间、风险提示
- **长期周期规划引擎**: 多周期训练计划（基础期→进展期→巅峰期→比赛期→恢复期）
- **智能建议引擎**: 训练不足/过量风险识别、有氧基础检测、个性化建议

#### Agent 工具扩展
- GenerateLongTermPlanTool、EvaluateGoalAchievementTool、GetSmartAdviceTool

### 测试覆盖
- 新增 50+ 单元测试，目标预测引擎覆盖率 100%

---

## 历史版本

| 版本 | 日期 | 核心内容 |
|------|------|---------|
| [0.11.0](docs/archive/changelog/CHANGELOG_v0.11.0_and_older.md#0110---2026-04-19) | 2026-04-19 | 智能调整层、计划调整校验器、Prompt 模板引擎 |
| [0.10.0](docs/archive/changelog/CHANGELOG_v0.11.0_and_older.md#0100---2026-04-19) | 2026-04-19 | 数据感知层、训练响应分析器、计划执行仓储 |
| [0.9.5](docs/archive/changelog/CHANGELOG_v0.11.0_and_older.md#095---2026-04-20) | 2026-04-20 | Gateway 服务增强、智谱 AI 支持、数据查询优化 |
| [0.9.4](docs/archive/changelog/CHANGELOG_v0.11.0_and_older.md#094---2026-04-18) | 2026-04-18 | 配置管理基础设施、初始化向导、数据迁移引擎 |
| [0.9.3](docs/archive/changelog/CHANGELOG_v0.11.0_and_older.md#093---2026-04-15) | 2026-04-15 | 报告生成、飞书 Gateway 重构、领域模型统一 |
| [0.9.2](docs/archive/changelog/CHANGELOG_v0.11.0_and_older.md#092---2026-04-11) | 2026-04-11 | AGENTS.md 重构、CI/CD 优化 |
| [0.9.1](docs/archive/changelog/CHANGELOG_v0.11.0_and_older.md#091---2026-04-10) | 2026-04-10 | nanobot-ai 升级至 0.1.5 |
| [0.9.0](docs/archive/changelog/CHANGELOG_v0.11.0_and_older.md#090---2026-04-09) | 2026-04-09 | 依赖注入机制、SessionRepository 仓储层、CLI 架构重构 |

---

**完整历史版本详情**: [docs/archive/changelog/CHANGELOG_v0.11.0_and_older.md](docs/archive/changelog/CHANGELOG_v0.11.0_and_older.md)
