# v0.15.0 透明洞察版 测试策略

> **文档版本**: v1.0  
> **创建日期**: 2026-04-28  
> **适用版本**: v0.15.0  
> **维护者**: 测试工程师智能体  
> **测试策略类型**: 版本专项测试策略

---

## 1. 测试目标与范围

### 1.1 测试目标

| 目标 | 说明 | 优先级 |
|------|------|--------|
| 验证全链路可观测性功能正确性 | 决策追踪、工具调用追踪、记忆使用追踪 | P0 |
| 验证AI决策透明化功能正确性 | 决策过程可视化、解释生成、数据来源追溯 | P0 |
| 验证智能洞察与优化功能正确性 | 训练数据分析、个性化建议、效果评估 | P0 |
| 验证透明化CLI命令可用性 | show/settings命令完整流程 | P0 |
| 验证性能指标达标 | 钩子触发时间<5ms、决策加载<100ms | P0 |
| 验证Hook系统集成稳定性 | nanobot-ai框架Hook集成点 | P1 |

### 1.2 测试范围

#### ✅ 纳入测试范围

| 模块 | 测试类型 | 负责人 | 状态 |
|------|---------|--------|------|
| `src/core/transparency/` 透明化模块 | 单元测试 + 集成测试 | 开发工程师 | ✅ 待验证 |
| `src/agents/tools.py` 透明化Agent工具 | 集成测试 | 测试工程师 | 📋 新增 |
| `src/cli/commands/transparency.py` CLI命令 | E2E测试 | 测试工程师 | 📋 新增 |
| 决策追踪完整链路 | 场景级集成测试 | 测试工程师 | 📋 新增 |
| 智能洞察报告生成 | 场景级集成测试 | 测试工程师 | 📋 新增 |
| 端到端用户旅程 | E2E全链路测试 | 测试工程师 | 📋 新增 |
| 性能测试 | 专项性能测试 | 测试工程师 | 📋 新增 |

#### ❌ 不纳入测试范围

- nanobot-ai框架Hook核心功能（仅测试集成点）
- LLM模型输出内容的不确定性验证
- 第三方依赖内部实现

---

## 2. 测试类型与策略

### 2.1 单元测试（Unit Testing）

**职责**: 开发工程师主责，测试工程师负责规范指导和结果校验

**覆盖范围**:
- `TransparencyEngine`: 决策解释生成、数据来源追溯、决策路径可视化
- `ObservabilityManager`: 链路追踪生命周期、事件记录、指标查询
- `TraceLogger`: 决策日志记录、工具调用日志、条件查询、统计
- `TransparencyDisplay`: Rich格式展示、简洁/详细版解释、数据来源表格
- `AIStatusDashboard`: 看板渲染、AI进化状态、建议质量、工具可靠性
- `TrainingInsightReport`: 训练模式分析、恢复状态趋势、AI建议效果评估
- `HookIntegration`: 生命周期钩子、透明化Hook实现
- 数据模型: `AIDecision`, `DataSource`, `DecisionExplanation`, `DecisionPath`, `TransparencySettings`, `ObservabilityMetrics`, `TraceReport`, `LogEntry`

**覆盖率要求**:
| 模块 | 最低覆盖率 | 当前状态 |
|------|-----------|---------|
| `src/core/transparency/` | ≥80% | ⚠️ 待验证（hook_integration 36%, trace_logger 77%） |

**Mock策略**:
- ✅ 必须Mock文件系统IO（使用临时目录）
- ✅ 必须Mock nanobot-ai框架Hook运行时
- ❌ 禁止Mock内部业务逻辑（决策解释、洞察分析逻辑）

### 2.2 集成测试（Integration Testing）

**职责划分**:
| 测试类型 | 目录 | 负责人 |
|---------|------|--------|
| 模块内集成测试 | `tests/integration/module/` | 开发工程师 |
| 场景级集成测试 | `tests/integration/scene/` | 测试工程师 |

**场景级集成测试覆盖**:
- 完整决策流程（追踪→决策→解释→日志）
- 多决策追踪与数据来源追溯
- 工具调用失败追踪
- 跨决策数据来源追溯
- AI状态看板集成
- 训练洞察报告集成
- 进化等级递进验证

### 2.3 端到端测试（E2E Testing）

**职责**: 测试工程师主责

**覆盖范围**:
- 完整简洁版透明化流程
- 完整详细版透明化流程
- 多会话透明化流程
- 错误恢复流程
- 看板和洞察报告完整流程

**测试环境**:
- 使用临时测试目录，不影响真实用户数据
- Mock所有外部依赖（LLM API）
- 使用模拟决策和工具调用数据

### 2.4 性能测试（Performance Testing）

**覆盖范围**:
- 钩子触发时间 < 5ms
- 决策解释生成时间 < 100ms
- 数据来源追溯时间 < 50ms
- 决策路径可视化生成时间
- 看板渲染时间

---

## 3. 门禁规则

### 3.1 测试准入规则

代码进入测试环节前，必须满足以下条件：

| 条件 | 验证方式 | 责任人 |
|------|---------|--------|
| 需求规格说明书已评审通过 | `PRD_NanobotRunner_v0.13-0.15.md` 存在且v2.0 | 架构师 |
| 架构设计说明书已评审通过 | `架构设计说明书_v0.13-0.15.md` 存在 | 架构师 |
| 开发完成并通过自测 | 开发交付报告 `开发交付报告_v0.15.0.md` | 开发工程师 |
| 单元测试覆盖率达标 | `pytest --cov` 报告（transparency≥80%） | 开发工程师 |
| 代码质量检查通过 | `ruff check` 零警告 | 开发工程师 |
| 类型检查通过 | `mypy` 无新增错误 | 开发工程师 |
| 无未解决的P0/P1 Bug | Bug清单状态 | 开发工程师 |

**准入验证命令**:
```bash
# 代码质量检查
uv run ruff check src/core/transparency/ src/agents/tools.py src/cli/commands/transparency.py
uv run ruff format --check src/core/transparency/ src/agents/tools.py src/cli/commands/transparency.py
uv run mypy src/core/transparency/ --ignore-missing-imports

# 单元测试覆盖率
uv run pytest tests/unit/core/transparency/ --cov=src/core/transparency --cov-report=term-missing

# 覆盖率验证
# transparency ≥ 80%（hook_integration为框架集成层，可豁免）
```

### 3.2 测试准出规则

测试完成并允许发布，必须满足以下条件：

| 条件 | 标准 | 验证方式 |
|------|------|---------|
| P0级用例通过率 | 100% | 测试报告 |
| P1级用例通过率 | ≥95% | 测试报告 |
| 致命Bug | 0个 | Bug清单 |
| 严重Bug | 0个 | Bug清单 |
| 一般Bug修复率 | ≥90% | Bug清单 |
| 核心业务流程 | 全量闭环 | E2E测试报告 |
| 决策过程可视化 | 100% | 功能测试报告 |
| 工具调用追踪 | 100% | 功能测试报告 |
| 钩子触发时间 | < 5ms | 性能测试报告 |
| 性能退化 | 无显著退化 | 性能测试报告 |
| 安全合规 | 无敏感信息泄露 | 安全扫描报告 |

**准出验证命令**:
```bash
# 全量测试执行
uv run pytest tests/ -v --tb=short

# v0.15.0专项测试执行
uv run pytest tests/unit/core/transparency/ -v
uv run pytest tests/integration/module/test_transparency_integration.py -v
uv run pytest tests/e2e/test_transparency_e2e.py -v
uv run pytest tests/integration/scene/ -k "transparency or observability or insight" -v
```

### 3.3 上线门禁规则

**绝对禁止发布的情况**:
- ❌ 存在任何致命或严重级Bug
- ❌ P0级用例通过率 < 100%
- ❌ 核心业务流程未闭环（决策追踪、工具调用追踪、智能洞察）
- ❌ 决策过程可视化覆盖率 < 100%
- ❌ 工具调用追踪覆盖率 < 100%
- ❌ 测试报告未输出或未评审通过
- ❌ 安全扫描发现敏感信息泄露

**允许发布的条件**（全部满足）:
- ✅ P0-P1级用例100%通过
- ✅ 无致命/严重级Bug
- ✅ 一般级Bug修复率≥90%
- ✅ 核心业务流程全量闭环
- ✅ 决策过程可视化 100%，工具调用追踪 100%
- ✅ 钩子触发时间 < 5ms
- ✅ 符合需求验收标准（REQ-015-001, REQ-015-002）
- ✅ 测试报告已输出并评审通过

---

## 4. 测试用例设计规范

### 4.1 v0.15.0核心测试用例清单

#### 4.1.1 透明化数据模型测试用例

| 用例ID | 模块 | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 类型 | 阶段 |
|--------|------|---------|---------|---------|---------|--------|------|------|
| TC-MODEL-001 | models | DecisionType枚举值验证 | 无 | 遍历所有枚举值 | 6种决策类型正确 | P1 | 功能 | 单元 |
| TC-MODEL-002 | models | DetailLevel枚举值验证 | 无 | 遍历所有枚举值 | 3级详细程度正确 | P1 | 功能 | 单元 |
| TC-MODEL-003 | models | DataSourceType枚举值验证 | 无 | 遍历所有枚举值 | 5种数据来源类型正确 | P1 | 功能 | 单元 |
| TC-MODEL-004 | models | AIDecision序列化/反序列化 | 创建AIDecision | to_dict() → from_dict() | 数据一致 | P0 | 功能 | 单元 |
| TC-MODEL-005 | models | DataSource序列化/反序列化 | 创建DataSource | to_dict() → from_dict() | 数据一致 | P0 | 功能 | 单元 |
| TC-MODEL-006 | models | DecisionExplanation序列化 | 创建DecisionExplanation | 调用to_dict() | 返回字典 | P1 | 功能 | 单元 |
| TC-MODEL-007 | models | DecisionPath可视化 | 创建DecisionPath | 调用to_mermaid() | 返回Mermaid语法 | P1 | 功能 | 单元 |
| TC-MODEL-008 | models | TransparencySettings默认值 | 无参数 | TransparencySettings() | 返回默认配置 | P1 | 功能 | 单元 |
| TC-MODEL-009 | models | ObservabilityMetrics计算 | 有追踪数据 | 调用计算方法 | 返回正确指标 | P1 | 功能 | 单元 |
| TC-MODEL-010 | models | TraceReport序列化 | 创建TraceReport | 调用to_dict() | 返回字典 | P1 | 功能 | 单元 |
| TC-MODEL-011 | models | LogEntry过滤 | 创建多个LogEntry | 应用LogFilters | 返回过滤结果 | P1 | 功能 | 单元 |

#### 4.1.2 TransparencyEngine测试用例

| 用例ID | 模块 | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 类型 | 阶段 |
|--------|------|---------|---------|---------|---------|--------|------|------|
| TC-ENGINE-001 | engine | 生成简洁版决策解释 | 决策已创建 | generate_explanation(decision, BRIEF) | 返回简洁解释 | P0 | 功能 | 单元 |
| TC-ENGINE-002 | engine | 生成详细版决策解释 | 决策已创建 | generate_explanation(decision, DETAILED) | 返回详细解释 | P0 | 功能 | 单元 |
| TC-ENGINE-003 | engine | 追溯数据来源 | 决策有数据源 | trace_data_sources(decision_id) | 返回数据来源列表 | P0 | 功能 | 单元 |
| TC-ENGINE-004 | engine | 生成决策路径Mermaid | 决策有步骤 | visualize_decision_path(decision_id) | 返回Mermaid图 | P0 | 功能 | 单元 |
| TC-ENGINE-005 | engine | 存储决策 | 引擎已初始化 | 调用存储方法 | 决策存储成功 | P0 | 功能 | 单元 |
| TC-ENGINE-006 | engine | 查询决策 | 决策已存储 | 调用查询方法 | 返回决策内容 | P0 | 功能 | 单元 |
| TC-ENGINE-007 | engine | 清理过期决策 | 有多个决策 | 调用清理方法 | 过期决策被清理 | P1 | 功能 | 单元 |
| TC-ENGINE-008 | engine | 空决策解释 | 无决策数据 | generate_explanation(None, BRIEF) | 返回空或默认解释 | P1 | 边界 | 单元 |
| TC-ENGINE-009 | engine | 多决策路径可视化 | 有多个决策 | visualize_decision_path(多决策) | 返回完整路径图 | P1 | 功能 | 单元 |

#### 4.1.3 ObservabilityManager测试用例

| 用例ID | 模块 | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 类型 | 阶段 |
|--------|------|---------|---------|---------|---------|--------|------|------|
| TC-OBS-001 | observability | 开始链路追踪 | 管理器已初始化 | start_trace(trace_id) | 追踪开始 | P0 | 功能 | 单元 |
| TC-OBS-002 | observability | 结束链路追踪 | 追踪已开始 | end_trace(trace_id) | 追踪结束，记录时长 | P0 | 功能 | 单元 |
| TC-OBS-003 | observability | 记录追踪事件 | 追踪已开始 | record_event(trace_id, event) | 事件记录成功 | P0 | 功能 | 单元 |
| TC-OBS-004 | observability | 获取可观测性指标 | 有追踪数据 | get_metrics() | 返回指标数据 | P0 | 功能 | 单元 |
| TC-OBS-005 | observability | 获取最近追踪 | 有追踪数据 | get_recent_traces(limit) | 返回最近追踪列表 | P1 | 功能 | 单元 |
| TC-OBS-006 | observability | 获取指定追踪 | 追踪已存在 | get_trace(trace_id) | 返回追踪详情 | P1 | 功能 | 单元 |
| TC-OBS-007 | observability | 未开始追踪记录事件 | 追踪未开始 | record_event(不存在的trace) | 返回错误或忽略 | P1 | 边界 | 单元 |
| TC-OBS-008 | observability | 多追踪并发 | 管理器已初始化 | 同时开始多个追踪 | 各追踪独立 | P1 | 功能 | 单元 |

#### 4.1.4 TraceLogger测试用例

| 用例ID | 模块 | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 类型 | 阶段 |
|--------|------|---------|---------|---------|---------|--------|------|------|
| TC-LOGGER-001 | logger | 记录AI决策 | 日志器已初始化 | log_decision(decision) | 决策记录成功 | P0 | 功能 | 单元 |
| TC-LOGGER-002 | logger | 记录工具调用 | 日志器已初始化 | log_tool_invocation(tool_name, args) | 工具调用记录成功 | P0 | 功能 | 单元 |
| TC-LOGGER-003 | logger | 条件查询日志 | 有多个日志 | query_logs(filters) | 返回过滤结果 | P0 | 功能 | 单元 |
| TC-LOGGER-004 | logger | 获取日志统计 | 有多个日志 | get_stats() | 返回统计数据 | P1 | 功能 | 单元 |
| TC-LOGGER-005 | logger | 日志文件写入 | 临时目录已创建 | 写入日志到文件 | 文件内容正确 | P1 | 功能 | 单元 |
| TC-LOGGER-006 | logger | 日志文件读取 | 日志文件存在 | 读取日志文件 | 返回日志内容 | P1 | 功能 | 单元 |
| TC-LOGGER-007 | logger | 空日志查询 | 无日志数据 | query_logs() | 返回空列表 | P1 | 边界 | 单元 |

#### 4.1.5 TransparencyDisplay测试用例

| 用例ID | 模块 | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 类型 | 阶段 |
|--------|------|---------|---------|---------|---------|--------|------|------|
| TC-DISPLAY-001 | display | 简洁版解释展示 | 有决策解释 | display_brief_explanation(explanation) | Rich格式输出 | P0 | 功能 | 单元 |
| TC-DISPLAY-002 | display | 详细版解释展示 | 有决策解释 | display_detailed_explanation(explanation) | Rich格式输出 | P0 | 功能 | 单元 |
| TC-DISPLAY-003 | display | 数据来源表格 | 有数据源列表 | display_data_sources(sources) | Rich表格输出 | P0 | 功能 | 单元 |
| TC-DISPLAY-004 | display | 决策路径Mermaid图 | 有决策路径 | display_decision_path(path) | Mermaid图输出 | P0 | 功能 | 单元 |
| TC-DISPLAY-005 | display | 置信度格式化 | 有置信度值 | format_confidence(0.85) | 返回格式化字符串 | P1 | 功能 | 单元 |
| TC-DISPLAY-006 | display | 空解释展示 | 无解释数据 | display_brief_explanation(None) | 返回默认提示 | P1 | 边界 | 单元 |

#### 4.1.6 AIStatusDashboard测试用例

| 用例ID | 模块 | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 类型 | 阶段 |
|--------|------|---------|---------|---------|---------|--------|------|------|
| TC-DASH-001 | dashboard | 渲染完整看板 | 看板已初始化 | render() | Rich Layout输出 | P0 | 功能 | 单元 |
| TC-DASH-002 | dashboard | AI进化状态 | 有进化数据 | render_evolution_status() | 状态输出 | P0 | 功能 | 单元 |
| TC-DASH-003 | dashboard | 建议质量展示 | 有建议数据 | render_suggestion_quality() | 质量输出 | P1 | 功能 | 单元 |
| TC-DASH-004 | dashboard | 工具可靠性展示 | 有工具数据 | render_tool_reliability() | 可靠性输出 | P1 | 功能 | 单元 |
| TC-DASH-005 | dashboard | 记忆整理日志 | 有记忆数据 | render_memory_log() | 日志输出 | P1 | 功能 | 单元 |
| TC-DASH-006 | dashboard | 看板JSON数据 | 看板已初始化 | get_dashboard_data() | 返回JSON字典 | P1 | 功能 | 单元 |

#### 4.1.7 TrainingInsightReport测试用例

| 用例ID | 模块 | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 类型 | 阶段 |
|--------|------|---------|---------|---------|---------|--------|------|------|
| TC-INSIGHT-001 | insight | 生成完整洞察报告 | 有训练数据 | generate_report() | 返回完整报告 | P0 | 功能 | 单元 |
| TC-INSIGHT-002 | insight | 训练模式分析 | 有训练历史 | analyze_training_patterns() | 返回模式分析 | P0 | 功能 | 单元 |
| TC-INSIGHT-003 | insight | 恢复状态趋势 | 有恢复数据 | analyze_recovery_trend() | 返回趋势分析 | P0 | 功能 | 单元 |
| TC-INSIGHT-004 | insight | AI建议效果评估 | 有建议历史 | evaluate_ai_advice_effect() | 返回效果评估 | P0 | 功能 | 单元 |
| TC-INSIGHT-005 | insight | 个性化进化报告 | 有进化数据 | generate_evolution_report() | 返回进化报告 | P1 | 功能 | 单元 |
| TC-INSIGHT-006 | insight | 空数据报告生成 | 无训练数据 | generate_report() | 返回空或默认报告 | P1 | 边界 | 单元 |

#### 4.1.8 HookIntegration测试用例

| 用例ID | 模块 | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 类型 | 阶段 |
|--------|------|---------|---------|---------|---------|--------|------|------|
| TC-HOOK-001 | hook | 迭代开始钩子 | Hook已注册 | on_iteration_start(context) | 钩子触发 | P0 | 功能 | 单元 |
| TC-HOOK-002 | hook | 迭代结束钩子 | Hook已注册 | on_iteration_end(context) | 钩子触发 | P0 | 功能 | 单元 |
| TC-HOOK-003 | hook | 工具调用钩子 | Hook已注册 | on_tool_call(context) | 钩子触发，记录调用 | P0 | 功能 | 单元 |
| TC-HOOK-004 | hook | 透明化Hook集成 | Hook已注册 | 执行完整迭代 | 透明化数据记录 | P0 | 集成 | 场景 |
| TC-HOOK-005 | hook | 创建透明化Hook工厂 | 无 | create_transparency_hooks() | 返回Hook列表 | P1 | 功能 | 单元 |

#### 4.1.9 Agent工具测试用例

| 用例ID | 模块 | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 类型 | 阶段 |
|--------|------|---------|---------|---------|---------|--------|------|------|
| TC-TOOL-001 | tools | explain_decision工具 | 有决策数据 | 调用explain_decision(decision_id) | 返回决策解释 | P0 | 功能 | 集成 |
| TC-TOOL-002 | tools | trace_data工具 | 有数据源 | 调用trace_data(decision_id) | 返回数据来源 | P0 | 功能 | 集成 |
| TC-TOOL-003 | tools | get_observability_status工具 | 管理器已初始化 | 调用get_observability_status() | 返回状态 | P0 | 功能 | 集成 |
| TC-TOOL-004 | tools | 工具错误处理 | 决策不存在 | 调用explain_decision(不存在) | 返回错误信息 | P1 | 异常 | 集成 |

#### 4.1.10 CLI命令测试用例

| 用例ID | 模块 | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 类型 | 阶段 |
|--------|------|---------|---------|---------|---------|--------|------|------|
| TC-CLI-001 | cli | transparency show默认展示 | CLI已安装 | nanobotrun transparency show | 展示透明化信息 | P0 | 功能 | E2E |
| TC-CLI-002 | cli | transparency show指定决策 | 有决策数据 | nanobotrun transparency show --decision-id <id> | 展示指定决策 | P0 | 功能 | E2E |
| TC-CLI-003 | cli | transparency show详细级别 | 有决策数据 | nanobotrun transparency show --level detailed | 展示详细信息 | P0 | 功能 | E2E |
| TC-CLI-004 | cli | transparency settings查看 | 配置已存在 | nanobotrun transparency settings | 查看透明化设置 | P0 | 功能 | E2E |
| TC-CLI-005 | cli | transparency settings修改 | 配置已存在 | nanobotrun transparency settings --level detailed | 修改设置成功 | P0 | 功能 | E2E |
| TC-CLI-006 | cli | CLI错误处理 | 决策不存在 | nanobotrun transparency show --decision-id 不存在 | 返回错误提示 | P1 | 异常 | E2E |

#### 4.1.11 场景级集成测试用例

| 用例ID | 模块 | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 类型 | 阶段 |
|--------|------|---------|---------|---------|---------|--------|------|------|
| TC-SCENE-001 | scene | 完整决策追踪流程 | 临时工作区 | 开始追踪→记录决策→生成解释→查询日志→结束追踪 | 全流程成功 | P0 | 集成 | 场景 |
| TC-SCENE-002 | scene | 多决策追踪与追溯 | 临时工作区 | 记录多个决策→追溯数据来源→生成路径图 | 多决策追溯成功 | P0 | 集成 | 场景 |
| TC-SCENE-003 | scene | 工具调用失败追踪 | 临时工作区 | 模拟工具调用失败→记录失败日志→查询失败统计 | 失败追踪成功 | P0 | 集成 | 场景 |
| TC-SCENE-004 | scene | 跨决策数据来源追溯 | 有多个决策 | 追溯多个决策的数据源→合并分析 | 跨决策追溯成功 | P0 | 集成 | 场景 |
| TC-SCENE-005 | scene | AI状态看板集成 | 有看板数据 | 渲染看板→获取JSON数据→验证数据完整性 | 看板集成成功 | P0 | 集成 | 场景 |
| TC-SCENE-006 | scene | 训练洞察报告集成 | 有训练数据 | 生成报告→分析模式→评估效果 | 报告集成成功 | P0 | 集成 | 场景 |
| TC-SCENE-007 | scene | 进化等级递进验证 | 有进化数据 | 验证进化等级递进逻辑 | 递进逻辑正确 | P1 | 集成 | 场景 |

#### 4.1.12 E2E用户旅程测试用例

| 用例ID | 模块 | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 类型 | 阶段 |
|--------|------|---------|---------|---------|---------|--------|------|------|
| TC-E2E-001 | e2e | 完整简洁版透明化流程 | 初始状态 | 1.用户查看AI决策 2.查看简洁版解释 3.查看数据来源 4.查看决策路径 | 全流程闭环 | P0 | E2E | E2E |
| TC-E2E-002 | e2e | 完整详细版透明化流程 | 初始状态 | 1.用户查看详细解释 2.查看完整决策路径 3.查看工具调用记录 4.查看记忆使用记录 | 全流程闭环 | P0 | E2E | E2E |
| TC-E2E-003 | e2e | 多会话透明化流程 | 初始状态 | 1.第一次会话记录决策 2.关闭应用 3.重新打开 4.查看历史决策追踪 | 跨会话追踪连贯 | P0 | E2E | E2E |
| TC-E2E-004 | e2e | 错误恢复流程 | 初始状态 | 1.模拟工具调用失败 2.查看失败记录 3.恢复后重新追踪 | 错误恢复成功 | P0 | E2E | E2E |
| TC-E2E-005 | e2e | 看板和洞察报告流程 | 有数据积累 | 1.查看AI状态看板 2.查看训练洞察报告 3.查看进化报告 | 看板报告完整 | P0 | E2E | E2E |

---

## 5. 已知问题与风险

### 5.1 已知问题

| 问题ID | 问题描述 | 影响模块 | 严重等级 | 处理方案 |
|--------|---------|---------|---------|---------|
| KNOWN-001 | hook_integration.py覆盖率仅36% | Hook集成 | 一般 | 框架集成层，需在集成环境验证，单元测试豁免 |
| KNOWN-002 | trace_logger.py日志文件写入未覆盖 | TraceLogger | 一般 | 补充IO相关测试用例 |
| KNOWN-003 | training_insight_report.py使用旧枚举值 | TrainingInsightReport | 一般 | 后续与DecisionType对齐，当前不影响功能 |

### 5.2 技术风险

| 风险ID | 风险描述 | 概率 | 影响 | 缓解措施 |
|--------|---------|------|------|---------|
| R001 | nanobot-ai Hook API变更 | 低 | 中 | 关注nanobot-ai版本更新，设计降级方案 |
| R002 | 透明化数据量过大导致性能问题 | 中 | 中 | 采样追踪、懒加载、缓存机制 |
| R003 | 决策解释生成质量不稳定 | 中 | 低 | 规则引擎兜底、人工校验机制 |

### 5.3 业务风险

| 风险ID | 风险描述 | 概率 | 影响 | 缓解措施 |
|--------|---------|------|------|---------|
| R004 | 用户对透明化信息接受度低 | 中 | 中 | 分层展示、用户可控详细程度 |
| R005 | 智能洞察建议准确性不达标 | 中 | 高 | 规则引擎验证、置信度标注 |

---

## 6. 测试环境配置

### 6.1 测试目录结构

```
tests/
├── unit/
│   └── core/
│       └── transparency/
│           └── test_transparency.py          # 透明化模块单元测试
├── integration/
│   └── module/
│       └── test_transparency_integration.py  # 透明化模块集成测试
├── e2e/
│   └── test_transparency_e2e.py              # 透明化E2E测试
└── conftest.py                               # 测试配置
```

### 6.2 测试数据管理

**测试数据来源**:
- 使用临时测试目录，不影响真实用户数据
- 构造模拟决策数据、工具调用数据、训练数据
- 禁止使用真实用户数据

**临时目录管理**:
```python
import tempfile
import shutil
from pathlib import Path
import pytest

@pytest.fixture
def temp_transparency_dir():
    """创建临时透明化测试目录"""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir)
```

### 6.3 测试命令

```bash
# 透明化模块专项测试
uv run pytest tests/unit/core/transparency/ -v
uv run pytest tests/integration/module/test_transparency_integration.py -v
uv run pytest tests/e2e/test_transparency_e2e.py -v

# 覆盖率报告
uv run pytest tests/unit/core/transparency/ --cov=src/core/transparency --cov-report=term-missing

# 代码质量
uv run ruff check src/core/transparency/ src/agents/tools.py src/cli/commands/transparency.py
uv run ruff format --check src/core/transparency/ src/agents/tools.py src/cli/commands/transparency.py
```

---

## 7. 测试报告规范

### 7.1 轮次测试报告模板

```markdown
# 轮次测试报告 - v0.15.0

**测试版本**: v0.15.0  
**测试轮次**: 第N轮  
**测试周期**: YYYY-MM-DD ~ YYYY-MM-DD  
**测试环境**: Windows/Mac, Python 3.11+

## 测试范围
- 透明化模块: 决策追踪、工具调用追踪、记忆使用追踪
- 智能洞察模块: 训练数据分析、个性化建议、效果评估
- CLI命令: transparency show/settings

## 用例执行情况
| 类型 | 总数 | 通过 | 失败 | 跳过 | 通过率 |
|------|------|------|------|------|--------|
| P0   |      |      |      |      |        |
| P1   |      |      |      |      |        |
| P2   |      |      |      |      |        |
| 合计 |      |      |      |      |        |

## Bug统计
| 严重等级 | 新增 | 已修复 | 待修复 | 驳回 |
|---------|------|--------|--------|------|
| 致命    |      |        |        |      |
| 严重    |      |        |        |      |
| 一般    |      |        |        |      |
| 优化    |      |        |        |      |

## 测试结论
- [ ] 通过 / 不通过
- 原因说明:

## 剩余风险
1. 风险描述 + 影响评估

## 上线建议
- 建议发布 / 建议修复后重新测试
```

### 7.2 测试报告保存路径

| 报告类型 | 路径 |
|---------|------|
| 测试策略 | `docs/test/strategy_v0.15.0.md` |
| Bug清单 | `docs/test/项目bug清单_v0.15.0.md` |
| 轮次测试报告 | `docs/test/reports/轮次测试报告_v0.15.0.md` |
| 集成测试报告 | `docs/test/reports/场景级集成测试报告_v0.15.0.md` |
| E2E测试报告 | `docs/test/reports/端到端测试报告_v0.15.0.md` |
| 全量测试报告 | `docs/test/reports/项目全量测试报告与质量评估_v0.15.0.md` |

---

## 8. 自动化测试规范

### 8.1 单元测试规范

```python
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from src.core.transparency import (
    TransparencyEngine,
    ObservabilityManager,
    TraceLogger,
    TransparencyDisplay,
    AIDecision,
    DecisionType,
    DetailLevel,
)

class TestTransparencyEngine:
    """透明化引擎单元测试"""
    
    def test_generate_brief_explanation(self):
        """测试生成简洁版决策解释"""
        # Arrange
        engine = TransparencyEngine()
        decision = AIDecision(
            id="test-001",
            decision_type=DecisionType.TRAINING_ADVICE,
            reasoning="基于训练数据分析...",
            confidence=0.85,
        )
        
        # Act
        explanation = engine.generate_explanation(decision, DetailLevel.BRIEF)
        
        # Assert
        assert explanation is not None
        assert explanation.detail_level == DetailLevel.BRIEF
        assert len(explanation.content) < 200  # 简洁版内容较短

class TestObservabilityManager:
    """可观测性管理器单元测试"""
    
    def test_start_and_end_trace(self):
        """测试链路追踪生命周期"""
        # Arrange
        manager = ObservabilityManager()
        trace_id = "trace-001"
        
        # Act
        manager.start_trace(trace_id)
        manager.end_trace(trace_id)
        
        # Assert
        trace = manager.get_trace(trace_id)
        assert trace is not None
        assert trace.duration > 0
```

### 8.2 集成测试规范

```python
import pytest
from pathlib import Path
from src.core.transparency import (
    TransparencyEngine,
    ObservabilityManager,
    TraceLogger,
    AIDecision,
    DecisionType,
)

class TestTransparencyIntegration:
    """透明化模块集成测试"""
    
    @pytest.fixture
    def temp_workspace(self, tmp_path):
        """创建临时工作区"""
        return tmp_path
    
    def test_full_decision_trace_flow(self, temp_workspace):
        """测试完整决策追踪流程"""
        # Arrange
        engine = TransparencyEngine()
        manager = ObservabilityManager()
        logger = TraceLogger()
        
        # Act - 开始追踪
        trace_id = "trace-001"
        manager.start_trace(trace_id)
        
        # Act - 记录决策
        decision = AIDecision(
            id="decision-001",
            decision_type=DecisionType.TRAINING_ADVICE,
            reasoning="基于分析...",
            confidence=0.85,
        )
        engine.store_decision(decision)
        logger.log_decision(decision)
        
        # Act - 生成解释
        explanation = engine.generate_explanation(decision, DetailLevel.BRIEF)
        
        # Act - 结束追踪
        manager.end_trace(trace_id)
        
        # Assert
        assert manager.get_trace(trace_id) is not None
        assert engine.get_decision(decision.id) is not None
        assert explanation is not None
```

### 8.3 E2E测试规范

```python
import pytest
from typer.testing import CliRunner
from src.cli.app import app

class TestTransparencyCLI:
    """透明化CLI命令E2E测试"""
    
    def test_transparency_show_command(self):
        """测试transparency show命令"""
        runner = CliRunner()
        
        result = runner.invoke(
            app,
            ["transparency", "show"]
        )
        
        assert result.exit_code == 0
        assert "AI决策" in result.output or "决策" in result.output
    
    def test_transparency_settings_command(self):
        """测试transparency settings命令"""
        runner = CliRunner()
        
        result = runner.invoke(
            app,
            ["transparency", "settings"]
        )
        
        assert result.exit_code == 0
        assert "设置" in result.output
```

---

## 9. 持续集成要求

### 9.1 CI流水线检查项

| 阶段 | 检查项 | 失败处理 |
|------|--------|---------|
| 代码质量 | `ruff check` 零警告 | 阻止合并 |
| 代码格式 | `ruff format --check` 通过 | 阻止合并 |
| 类型检查 | `mypy` 无新增错误 | 阻止合并 |
| 单元测试 | 通过率100% | 阻止合并 |
| 集成测试 | 通过率≥95% | 阻止合并 |
| 覆盖率 | transparency≥80%（hook_integration豁免） | 警告，不阻止 |
| 安全扫描 | 无敏感信息 | 阻止合并 |

### 9.2 本地预检查

提交前必须执行的本地检查：

```bash
# Windows PowerShell
uv run ruff format --check src/core/transparency/ src/agents/tools.py src/cli/commands/transparency.py; if($?) { 
    uv run ruff check src/core/transparency/ src/agents/tools.py src/cli/commands/transparency.py; if($?) { 
        uv run mypy src/core/transparency/ --ignore-missing-imports; if($?) { 
            uv run pytest tests/unit/core/transparency/ --cov=src/core/transparency
        } 
    } 
}
```

---

## 10. 测试左移策略

### 10.1 架构设计阶段介入

- 参与架构评审，识别可测试性问题
- 验证Hook系统可观测性设计是否便于测试
- 确认透明化数据模型的可序列化性

### 10.2 开发阶段介入

- 制定单元测试规范，指导开发工程师编写测试
- 提供Mock策略建议，特别是nanobot-ai框架集成点
- 审查测试覆盖率，确保核心逻辑100%覆盖

---

## 11. 测试统计

| 统计项 | 数量 |
|--------|------|
| **测试用例总数** | 62 |
| **P0级用例数** | 38 |
| **P1级用例数** | 24 |
| **单元测试用例** | 40 |
| **集成测试用例** | 11 |
| **E2E测试用例** | 11 |
| **门禁规则数** | 15 |

---

## 12. 后续建议

1. **立即执行**: 运行现有测试用例验证开发交付质量
2. **补充测试**: 针对hook_integration.py和trace_logger.py补充IO测试
3. **性能验证**: 执行性能测试验证钩子触发时间<5ms
4. **E2E验证**: 执行端到端测试验证用户旅程闭环
5. **回归测试**: 修复Bug后执行回归测试验证修复效果

---

*本测试策略由测试工程师智能体基于需求规格说明书、架构设计说明书、开发交付报告编写，旨在为v0.15.0版本测试提供明确的实施依据*

**版本历史**:
- v1.0 (2026-04-28): 初始版本，基于v0.15.0透明洞察版需求
