# 更新日志

本文档记录 Nanobot Runner 的所有重要变更。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

> **历史版本归档**: [docs/archive/changelog/](docs/archive/changelog/)

---

## [0.27.0] - 2026-05-31

### 版本主题
**WebUI 基础** —— 配置驱动启用 nanobot-ai 内置 WebUI，AI 对话交互 + 基础设置

> v0.27.0 是 Phase D（交互升级）的第二个版本，通过配置驱动方式启用 nanobot-ai 原生 WebUI，实现浏览器端 AI 对话交互能力，从纯 CLI 进化到 Web 交互。

**本版本已实现**:
- ✅ WebSocket 通道配置：config.json 新增 `websocket` 配置节，支持环境变量覆盖
- ✅ Gateway CLI 增强：`gateway start --webui` 标志启用 WebUI
- ✅ 品牌自定义：bot_name="Nanobot-Runner", bot_icon="🏃‍♂️"
- ✅ 安全认证：默认启用 token 认证，仅监听 127.0.0.1
- ✅ 向后兼容：不启用 WebUI 时飞书/CLI 功能不受影响
- ✅ 全量回归 4489 用例零失败，覆盖率 81%

### Added
- ConfigManager.get_websocket_config() 方法，读取 WebSocket 通道配置，支持环境变量覆盖（NANOBOT_WS_*）
- RunnerProviderAdapter.webui_enabled 参数，接收 CLI `--webui` 标志
- RunnerProviderAdapter._build_websocket_channel_config() 方法，构建 WebSocket 通道配置
- Gateway CLI `--webui` 标志，启用时自动配置 WebSocket 通道
- WebUI 访问地址显示（http://{host}:{port}）
- Token 获取方式提示（curl http://{host}:{port}/token）
- WebUI Settings API 拦截（防止写入 ~/.nanobot/config.json，保持配置独立性）
- 品牌字段支持（bot_name/bot_icon/unified_session）写入 AgentsConfig.defaults
- ADR-015 WebSocket 通道配置方式决策记录
- ADR-016 WebUI 启用方式决策记录
- ADR-017 安全认证策略决策记录

### Changed
- RunnerProviderAdapter._build_nanobot_config_from_runner() 新增 WebSocket 配置构建逻辑
- gateway start 命令启动信息显示 WebUI 专属交互信息

### Security
- WebSocket 通道默认仅监听 127.0.0.1（本地访问）
- 默认启用 token 认证（websocket_requires_token=True）
- 采用 token_issue_path 短期令牌签发机制

### 测试验证
- 新增 25 个 WebSocket 配置单元测试（test_websocket_config.py）
- 新增 19 个 ProviderAdapter WebSocket 配置构建单元测试
- 新增 25 个 WebUI 启动集成测试
- 单元测试 4134 passed (100% 通过率)
- 集成测试 355 passed (100% 通过率)
- 代码覆盖率 core 81% ≥ 80% 目标

### 文档产出
- `docs/test/strategy_v0.27.0.md` - 测试策略
- `docs/test/测试报告_v0.27.0.md` - 测试报告
- `docs/test/上线结论_v0.27.0.md` - 上线结论（建议上线）

---

## [0.26.0] - 2026-05-24

### 版本主题
**Phase D 底座升级与推理可见化** —— nanobot-ai 0.2.0底座升级、GoalState适配、推理过程流式可见化、Model Presets预设管理

> v0.26.0 是Phase D（底座升级与平台增强）的首个版本，完成nanobot-ai从0.1.5.post2到0.2.0的底座升级，新增GoalState决策目标状态追踪、推理过程流式可见化（reasoning visibility）和Model Presets多模型预设管理，为后续Agent能力增强奠定基础。

**本版本已实现**:
- ✅ nanobot-ai 0.2.0 底座升级（兼容性100%验证）
- ✅ GoalState适配：DecisionLog新增goal_state字段，追踪每次决策的目标状态
- ✅ 推理可见化：emit_reasoning/emit_reasoning_end/finalize_content三段式推理流
- ✅ Model Presets：AppConfig.model_presets字段，支持多模型预设列表管理
- ✅ CLI命令: `model list` - 查看可用模型预设列表
- ✅ 全量回归5075用例零失败，覆盖率82.63%

### Added
- DecisionLog.goal_state 字段，记录决策时的5维度目标状态
- goal_state_raw() 方法，从metadata提取goal_state
- after_iteration() 回调，自动读取metadata并写入DecisionLog
- emit_reasoning() 追加推理片段到缓冲区
- emit_reasoning_end() 标记推理完成
- finalize_content() 将推理写入prediction_snapshot
- before_iteration() 重置推理状态
- AppConfig.model_presets 字段，支持模型预设配置
- `model list` CLI命令，查看可用模型预设列表
- ModelHandler.list_presets 返回预设列表
- ADR-012 GoalState适配决策记录
- ADR-013 推理可见化适配决策记录
- ADR-014 Model Presets适配决策记录

### Changed
- nanobot-ai 底座从0.1.5.post2升级至0.2.0
- 底座兼容性：ruff/mypy/pytest全量验证通过
- 依赖版本：nanobot-ai>=0.2.0

### Fixed
- 测试隔离性优化：偶发flaky test（test_memory_version_list_and_restore）已记录跟踪（优化级，不影响发布）

---

## [0.25.0] - 2026-05-22

### 版本主题
**自适应进化控制** —— 进化触发规则引擎、提示参数调优、月度进化报告

> v0.25.0 是Phase C（自适应进化引擎）的第三个版本，新增进化触发控制器、提示参数调优器和月度进化报告生成器，实现AI决策的自适应进化闭环。

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

> v0.24.0 是Phase C（自适应进化引擎）的第二个版本，完成测试验证阶段全部工作，产出测试策略、测试报告、Bug修复、回归测试报告及上线结论，确认代码库基线质量达标。

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
- 上线门禁：7/7全部通过
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

> v0.23.0 是Phase C（自适应进化引擎）的首个版本，新增决策追踪模块，实现AI决策自动记录与结果回填，为v0.24个性化学习和v0.25自适应进化奠定基础。

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

## 历史版本摘要

> 以下为v0.22.1及更早版本的摘要记录，详细变更见归档文档。

| 版本 | 日期 | 核心内容 |
|------|------|---------|
| [0.22.1](docs/archive/changelog/CHANGELOG_v0.22.1.md) | 2026-05-19 | 代码质量重构：17处type:ignore修复、裸Exception替换、跨模块去重、文件拆分 |
| [0.22.0](docs/archive/changelog/CHANGELOG_v0.22.0.md) | 2026-05-18 | 质量收口版本：UAT验证、缺陷收敛、质量兜底、发布准备 |
| [0.21.0](docs/archive/changelog/CHANGELOG_v0.21.0.md) | 2026-05-12 | 数字孪生引擎：5维度状态向量、What-If推演、计划对比 |
| [0.20.1](docs/archive/changelog/CHANGELOG_v0.20.1.md) | 2026-05-11 | ML预测增强：VDOT/伤病/比赛ML训练推理、SHAP分析、模型管理 |
| [0.20.0](docs/archive/changelog/CHANGELOG_v0.20.0.md) | 2026-05-09 | ML增强预测架构：三层降级策略、特征工程、CLI命令组 |
| [0.19.0](docs/archive/changelog/CHANGELOG_v0.19.0.md) | 2026-05-06 | 身体信号分析：HRV分析、疲劳度评估、恢复状态、身体信号解读 |
| [0.18.0](docs/archive/changelog/CHANGELOG_v0.18.0.md) | 2026-05-04 | 数据可视化与导出：终端图表(plotext)、多格式导出 |
| [0.17.0](docs/archive/changelog/CHANGELOG_v0.17.0.md) | 2026-05-03 | AI底座激活：Hook组合、Subagent、异步确认、Cron提醒 |
| [0.16.1](docs/archive/changelog/CHANGELOG_v0.16.1.md) | 2026-04-29 | 测试目录结构重构 |
| [0.16.0](docs/archive/changelog/CHANGELOG_v0.16.0.md) | 2026-04-29 | Core模块化重构：base/calculators/config/storage/report/models |
| [0.15.0](docs/archive/changelog/CHANGELOG_v0.15.0.md) | 2026-04-28 | AI决策透明化：决策追踪、可观测性、追踪日志器 |
| [0.13.0](docs/archive/changelog/CHANGELOG_v0.13.0.md) | 2026-04-27 | 智能技能生态：MCP工具管理、天气/地图/健康Agent工具 |
| [0.12.0](docs/archive/changelog/CHANGELOG_v0.12.0.md) | 2026-04-19 | 预测规划层：目标达成评估、长期周期规划、智能建议 |
| [0.11.0](docs/archive/changelog/CHANGELOG_v0.11.0_and_older.md#0110---2026-04-19) | 2026-04-19 | 智能调整层、计划调整校验器、Prompt模板引擎 |
| [0.10.0](docs/archive/changelog/CHANGELOG_v0.11.0_and_older.md#0100---2026-04-19) | 2026-04-19 | 数据感知层、训练响应分析器、计划执行仓储 |
| [0.9.5](docs/archive/changelog/CHANGELOG_v0.11.0_and_older.md#095---2026-04-20) | 2026-04-20 | Gateway服务增强、智谱AI支持、数据查询优化 |
| [0.9.4](docs/archive/changelog/CHANGELOG_v0.11.0_and_older.md#094---2026-04-18) | 2026-04-18 | 配置管理基础设施、初始化向导、数据迁移引擎 |
| [0.9.3](docs/archive/changelog/CHANGELOG_v0.11.0_and_older.md#093---2026-04-15) | 2026-04-15 | 报告生成、飞书Gateway重构、领域模型统一 |
| [0.9.2](docs/archive/changelog/CHANGELOG_v0.11.0_and_older.md#092---2026-04-11) | 2026-04-11 | AGENTS.md重构、CI/CD优化 |
| [0.9.1](docs/archive/changelog/CHANGELOG_v0.11.0_and_older.md#091---2026-04-10) | nanobot-ai升级至0.1.5 |
| [0.9.0](docs/archive/changelog/CHANGELOG_v0.11.0_and_older.md#090---2026-04-09) | 依赖注入机制、SessionRepository仓储层、CLI架构重构 |

**完整历史版本详情**: [docs/archive/changelog/](docs/archive/changelog/)
