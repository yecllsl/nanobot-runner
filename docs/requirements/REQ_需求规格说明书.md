# 需求规格说明书

> **文档版本**: v12.0
> **最后更新**: 2026-05-24
> **当前基线**: v0.25.0
> **覆盖版本**: v0.26.0 - v0.29.0
> **对齐产品规划**: v11.0 (2026-05-23)
> **对齐架构设计**: v14.0.0 (2026-05-24)

---

## 1. 项目概述

### 1.1 产品定位

Nanobot Runner 是一款桌面端私人 AI 跑步助理，基于 nanobot-ai 框架构建。产品从"记录跑步"升级为"预测跑步"再到"进化跑步"，核心价值：**本地化、隐私可控、专业可信、预测未来、自我进化**。

### 1.2 演进愿景

| 阶段 | 口号 | 核心能力 | 对应版本 | 状态 |
|------|------|----------|----------|------|
| **记录跑步** | "你的跑步数据管家" | FIT解析、数据存储、基础统计 | v0.5-v0.19 | ✅ 完成 |
| **预测跑步** | "你的数字孪生跑者" | ML增强预测、What-If推演、风险预警 | v0.20-v0.22 | ✅ 完成 |
| **进化跑步** | "越用越懂你的私人教练" | 决策追踪、自适应学习、个性化进化 | v0.23-v0.25 | ✅ 完成 |
| **交互升级** | "随时随地与你对话的AI教练" | 底座升级、新特性适配、WebUI | v0.26-v0.29 | 📋 规划中 |

### 1.3 目标用户

技术型严肃跑者：25-45岁技术从业者，规律跑步2年+，关注数据隐私，具备CLI操作能力。

### 1.4 已完成功能摘要

| 模块 | 核心能力 | 版本 |
|------|----------|------|
| 数据管理 | FIT解析、SHA256去重、Parquet按年分片 | v0.5 |
| 数据分析 | VDOT、TSS/ATL/CTL/TSB、心率漂移、用户画像 | v0.8-v0.9 |
| Agent交互 | 自然语言查询、智能建议、训练计划 | v0.8-v0.12 |
| CLI | 分层架构、Rich格式化 | v0.9 |
| 架构 | 依赖注入(AppContext)、Polars向量化 | v0.9-v0.16 |
| 工具生态 | MCP协议、AI自我诊断、决策透明化 | v0.13-v0.15 |
| 可视化与导出 | 终端图表(plotext)、多格式导出 | v0.18 |
| 身体信号分析 | HRV分析、疲劳度评估、恢复状态、身体信号解读 | v0.19 |
| ML增强预测 | VDOT趋势预测、比赛成绩预测、伤病风险预测、模型管理 | v0.20 |
| 数字孪生引擎 | 跑者状态向量(5维度)、What-If推演、计划对比 | v0.21 |
| 质量收口 | UAT验证、缺陷收敛 | v0.22 |
| 决策追踪 | 决策自动记录、结果回填、用户反馈、CLI命令组 | v0.23 |
| 个性化学习 | 训练响应性分析、预测校准、模型进化 | v0.24 |
| 自适应进化 | 进化触发器、提示调优、月度报告 | v0.25 |

---

## 2. 关键设计裁决

> 以下裁决统一了产品演进设计文档与架构设计说明书/产品规划方案之间的不一致。

### 2.1 技术选型裁决

| 裁决项 | 最终决定 | 理由 |
|--------|---------|------|
| ML框架 | **scikit-learn** (GradientBoostingRegressor/Classifier) | 轻量化优先，数据规模(100-2000条)下性能足够，技术栈一致性 |
| 模块命名 | `src/core/prediction/` / `src/core/twin/` / `src/core/evolution/` | prediction与架构设计一致；twin为v0.21新增；v0.23-v0.25统一为evolution/递增式添加 |
| 多Agent路线图 | **多Agent为增强手段，非核心依赖** | nanobot仅支持主-从后台任务模式，无Agent间协作能力 |

### 2.2 CLI命令与Agent工具命名规范

- **CLI命令组**: predict / twin / evolution 各自独立命令组，按版本递增式添加子命令
- **Agent工具命名**: snake_case风格，与现有工具命名规范一致
- **evolution命令组**: 覆盖v0.23-v0.25全部功能

| 版本 | CLI命令 | Agent工具 |
|------|---------|-----------|
| v0.23 | evolution history/feedback/accuracy/fidelity/status | record_feedback, check_plan_execution, check_prediction_accuracy, get_decision_history |
| v0.24 | evolution calibration/response | analyze_training_response, get_calibration_status |
| v0.25 | evolution triggers/report/tune | check_evolution_triggers, get_evolution_report, adjust_prompt_params |

---

## 3. Phase A：数字孪生跑者（v0.20-v0.22）✅ 已完成

Phase A 已全部完成交付，包含 v0.20 ML增强预测（VDOT/比赛/伤病+模型管理）、v0.21 数字孪生引擎（5维度状态向量+What-If推演+计划对比）、v0.22 质量收口（UAT验证+缺陷收敛）。详细需求规格见Git历史版本。

| 验收项 | 标准 | 版本 |
|--------|------|------|
| VDOT预测准确 | ML预测误差<5% | v0.20 |
| 比赛预测准确 | 全马预测误差<8分钟 | v0.20 |
| 伤病预警有效 | 3周前置预警召回率>75% | v0.20 |
| 推演准确性 | 4周VDOT推演误差<8% | v0.21 |
| 推演性能 | 单计划4周推演<10秒 | v0.21 |

---

## 4. Phase C：自适应进化引擎（v0.23-v0.25）✅ 已完成

Phase C 已全部完成交付，形成决策→校准→优化闭环：v0.23 决策追踪（DecisionLog+OutcomeRecord+DecisionLogHook）、v0.24 个性化学习（ResponseAnalyzer+CalibrationEngine+ModelEvolver）、v0.25 自适应进化（EvolutionController+PromptTuner+EvolutionReporter）。详细需求规格见Git历史版本。

| 验收项 | 标准 | 版本 |
|--------|------|------|
| 决策记录 | 每次AI决策100%自动记录 | v0.23 |
| 结果回填 | 计划执行忠实度可计算率>80% | v0.23 |
| Hook性能 | DecisionLogHook接入延迟<100ms | v0.23 |
| 响应性分析 | 训练类型效果排名一致率>70% | v0.24 |
| 预测校准 | 校准后VDOT MAE降低≥15% | v0.24 |
| 自进化闭环 | 闭环自动运行率>90% | v0.25 |

---

## 5. Phase D：交互升级（v0.26.0 - v0.29.0）

### 5.1 Phase 概述

**背景**：nanobot-ai 0.2.0 发布，引入 GoalState、FallbackProvider、WebUI 内置打包、Model Presets、推理可见化等重要新能力。RunFlowAgent 需升级底座并规划新特性适配，同时建设 WebUI 交互能力。

**Phase 目标**：
1. 安全升级底座到 nanobot-ai 0.2.0，零功能回归
2. 适配三项关键新特性（GoalState/推理可见化/Model Presets），增强现有功能
3. 建设WebUI交互能力，从纯CLI进化到Web交互
4. 评估剩余新特性（FallbackProvider/MCP Resources/Prompts），决定是否纳入后续版本

**设计文档**：[底座升级设计文档](../superpowers/specs/2026-05-23-nanobot-0.2.0-upgrade-design.md)

### 5.2 v0.26.0 — 底座升级 + 新特性适配

**主题**：nanobot-ai 0.2.0 底座升级 + GoalState/推理可见化/Model Presets 适配

#### 5.2.1 功能需求

| 编号 | 需求 | 优先级 | 验收标准 |
|------|------|--------|----------|
| REQ-D-01 | **底座依赖升级** | P0 | `pyproject.toml` 中 `nanobot-ai>=0.1.5.post2` → `nanobot-ai>=0.2.0`；`uv run pytest tests/` 全量通过 |
| REQ-D-02 | **API兼容性验证** | P0 | RunFlowAgent 使用的 nanobot-ai API 无 breaking change；DecisionLogHook 作为 AgentHook 子类可无缝兼容 |
| REQ-D-03 | **测试修复** | P0 | 因 API 变更导致的失败用例全部修复；`uv run ruff check src/` 无新增错误；`uv run mypy src/ --ignore-missing-imports` 无新增错误 |
| REQ-D-04 | **配置迁移** | P1 | nanobot-ai 0.2.0 配置 Schema 变更已适配；现有 config.json 可被 0.2.0 Config loader 正常加载 |
| REQ-D-05 | **依赖冲突预检** | P1 | `uv pip install --dry-run` 无依赖冲突；nanobot-ai 0.2.0 间接依赖与现有依赖无冲突 |
| REQ-D-06 | **ToolRegistry 注册验证** | P1 | `tools.py` 和 `tools_evolution.py` 中的工具注册 API 无变更，所有工具正常注册 |
| REQ-D-07 | **GoalState 适配** | P0 | SOUL.md 注入 GoalState 使用指导；DecisionLogHook 的 `after_iteration` 读取 `goal_state_raw(context.metadata)` 关联 DecisionLog；创建训练计划后 Agent 在新对话中能回忆当前计划目标 |
| REQ-D-08 | **推理可见化适配** | P0 | DecisionLogHook 重写 `emit_reasoning()` 将推理片段追加到内部缓冲区；`finalize_content()` 将推理缓冲区写入 DecisionLog 上下文快照；飞书对话中可见 Agent 推理过程；推理内容与最终建议逻辑一致 |
| REQ-D-09 | **Model Presets 适配** | P0 | config.json 可配置多个 Model Presets（名称+Provider+参数）；CLI 命令可查看当前预设列表；飞书/WebUI 中可通过 `/model <preset>` 切换预设（nanobot-ai 内置命令，RunFlowAgent 仅提供预设配置） |
| REQ-D-10 | **性能回归检查** | P1 | 核心 CLI 命令（data import、analysis vdot、plan create、evolution status）响应时间不退化 >20%（以 v0.25.0 为基线） |

#### 5.2.2 非功能需求

| 编号 | 需求 | 标准 |
|------|------|------|
| NFR-D-01 | 升级零回归 | 所有现有功能正常工作，无功能退化 |
| NFR-D-02 | Hook兼容性 | DecisionLogHook 接入延迟<100ms（与 v0.25.0 一致） |
| NFR-D-03 | 配置向后兼容 | 现有 config.json 无需手动修改即可正常使用 |
| NFR-D-04 | 推理流式延迟 | 推理可见化不增加 Agent 响应延迟>50ms |

#### 5.2.3 不做的事

- 不适配 FallbackProvider、MCP Resources/Prompts（独立评估任务，不占版本号）
- 不做 WebUI 相关工作（v0.27.0）
- 不重构现有代码
- 不修改用户配置文件格式

### 5.3 v0.27.0 — WebUI 基础

**主题**：复用 nanobot-ai 原生 WebUI，实现 AI 对话交互 + 基础设置

| 编号 | 需求 | 优先级 | 验收标准 |
|------|------|--------|----------|
| REQ-D-11 | WebUI 启动 | P0 | `nanobot gateway` 启动后，浏览器访问 WebUI 可正常对话 |
| REQ-D-12 | 工具调用 | P0 | 所有 RunFlowAgent 工具在 WebUI 中可正常调用 |
| REQ-D-13 | 流式输出 | P0 | Agent 回复逐字流式展示；推理展示正常 |
| REQ-D-14 | 多会话管理 | P1 | 创建/切换/删除对话正常；会话标题自动生成 |
| REQ-D-15 | 基础设置 | P1 | 模型切换、Provider 配置、时区等基础设置正常 |
| REQ-D-16 | 品牌自定义 | P2 | bot_name/bot_icon 配置为 RunFlowAgent 品牌 |

### 5.4 v0.28.0 — WebUI 数据可视化

**主题**：扩展 WebUI，增加跑步数据可视化能力

| 编号 | 需求 | 优先级 | 验收标准 |
|------|------|--------|----------|
| REQ-D-17 | VDOT 趋势图 | P0 | WebUI 中可查看 VDOT 随时间变化的折线图 |
| REQ-D-18 | 训练负荷图 | P0 | WebUI 中可查看 ATL/CTL/TSB 趋势 |
| REQ-D-19 | 身体信号面板 | P1 | WebUI 中可查看 HRV、疲劳度、恢复状态 |
| REQ-D-20 | 数据概览仪表盘 | P1 | 近7/30/90天跑步数据汇总 |
| REQ-D-21 | 图表数据一致性 | P0 | 图表数据与 CLI 命令输出一致 |
| REQ-D-22 | 时间范围筛选 | P1 | 图表支持 7/30/90/365 天筛选 |

### 5.5 v0.29.0 — WebUI 管理控制台

**主题**：训练计划管理 + 进化引擎控制台

| 编号 | 需求 | 优先级 | 验收标准 |
|------|------|--------|----------|
| REQ-D-23 | 训练计划查看 | P0 | WebUI 中可查看当前训练计划及每日安排 |
| REQ-D-24 | 计划执行进度 | P0 | 可查看计划完成率、忠实度 |
| REQ-D-25 | 计划调整 | P1 | 可通过对话调整训练计划 |
| REQ-D-26 | 进化状态面板 | P0 | 可查看进化引擎状态、触发条件 |
| REQ-D-27 | 提示参数调整 | P1 | PromptTuner 4维参数可通过滑块调整 |
| REQ-D-28 | 月度进化报告 | P1 | 可查看历史进化报告 |

### 5.6 独立评估任务（不占版本号）

**主题**：FallbackProvider 故障转移 + MCP Resources/Prompts 评估

| 编号 | 评估项 | 评估要点 |
|------|--------|----------|
| EVAL-D-01 | FallbackProvider | 多 Provider 配置需求、故障转移对建议一致性影响、断路器与 PromptTuner 交互 |
| EVAL-D-02 | MCP Resources/Prompts | 当前 MCP Tool 映射是否已满足、Resources/Prompts 增量价值、与 WebUI 数据可视化协同 |

**验收标准**：
1. 完成 FallbackProvider 评估报告，明确是否采纳及实施方案
2. 完成 MCP Resources/Prompts 评估报告，明确是否采纳及实施方案
3. 若采纳，相关功能开发完成并通过测试

---

## 6. v1.0.0 需求规划

**主题**: "你的私人 AI 教练"

| 维度 | 需求 |
|------|------|
| API稳定 | API冻结、向后兼容承诺 |
| 性能优化 | 大数据量查询优化、启动速度优化 |
| 稳定性 | 异常处理完善、数据完整性校验 |
| 文档 | 完整文档、快速入门指南、用户手册 |
| 社区就绪 | Issue模板、贡献指南 |

---

## 7. 非功能需求

| 编号 | 需求 | 标准 |
|------|------|------|
| NFR-01 | 预测响应时间 | <5秒 |
| NFR-02 | ML推理延迟 | <100ms |
| NFR-03 | Hook接入延迟 | <100ms |
| NFR-04 | 本地存储 | 所有数据本地存储，零外联 |
| NFR-05 | 不确定性声明 | 预测/推演输出标注置信区间和不确定性 |
| NFR-06 | 无侵入接入 | 新模块通过Hook/包装接入，不修改核心逻辑 |
| NFR-07 | 降级策略 | 数据不足时自动降级到参数化基线 |
| NFR-08 | 升级零回归 | 底座升级后所有现有功能正常工作 |
| NFR-09 | 配置向后兼容 | 新版底座配置Schema变更不破坏旧配置 |
| NFR-10 | 推理可见化延迟 | 推理流式展示不增加Agent响应延迟>50ms |

---

## 8. 验收总览

Phase A 及 Phase C 全部验收门禁已通过。Phase D 验收标准详见 §5.2-§5.6。

---

## 9. 风险与缓解

| 风险 | 等级 | 影响 | 缓解措施 |
|------|------|------|----------|
| 决策日志数据膨胀 | 中 | 长期运行后日志过大 | Parquet按月分片；自动归档旧数据 |
| 用户反馈稀疏 | 高 | 缺乏足够反馈驱动进化 | 轻量反馈机制；主动询问；隐式反馈自动记录 |
| 进化方向偏差 | 中 | 系统学习到的偏好与真实目标偏离 | 人工覆盖机制；月度进化报告review；reset_to_default()回退 |
| 多智能体架构约束 | 低 | nanobot底座不支持Agent间协作 | 待底座能力成熟后评估多视角方案 |
| nanobot-ai 0.2.0 API breaking change | 低 | 升级后现有功能异常 | 0.2.0 对 AgentHook 接口纯增量扩展，无破坏性变更；v0.26.0 全量测试覆盖 |
| 间接依赖冲突 | 中 | nanobot-ai 0.2.0 间接依赖与现有依赖冲突 | `uv pip install --dry-run` 预检 |
| config.json Schema 不兼容 | 低 | 新增字段破坏旧配置 | 0.2.0 新增字段均有默认值，Pydantic 向后兼容 |
| 原生 WebUI 不支持跑步数据可视化 | 中 | v0.27.0 无图表能力 | v0.27.0 先验证基础链路，v0.28.0 再扩展 |
| 上游 WebUI 版本变更影响 | 低 | nanobot-ai WebUI 更新影响 RunFlowAgent | 锁定 nanobot-ai 版本；自定义组件独立维护 |

---

## 附录A：术语表

| 术语 | 定义 |
|------|------|
| VDOT | 跑力值，衡量跑者有氧能力的指标 |
| Banister IR Model | 运动科学经典模型，描述训练刺激与体能响应的关系 |
| CTL/ATL/TSB | 慢性训练负荷(42天EWMA)/急性训练负荷(7天EWMA)/训练压力平衡 |
| SHAP | SHapley Additive exPlanations，特征重要性解释方法 |
| RunnerStateVector | 跑者状态向量，统一封装跑者当前全部生理状态 |
| DecisionLog | 决策日志，记录AI决策的完整上下文(frozen dataclass) |
| OutcomeRecord | 执行结果记录，通过decision_id关联DecisionLog |
| DecisionLogHook | 决策日志钩子，继承AgentHook，无侵入采集决策上下文 |
| EvolutionEngine | 进化引擎薄编排层，委托给各子组件 |
| EvolutionStore | 统一存储编排，管理decisions/outcomes/calibrations/tuning的Parquet+JSON读写 |
| 执行忠实度 | 计划训练vs实际训练的吻合程度(0-1) |
| 偏差修正层 | CalibrationEngine，在预测输出上加bias+scale线性修正 |
| 参数化提示调优 | PromptTuner，4维参数空间调整LLM输出风格 |
| ML增强预测 | 使用机器学习模型替代简单统计模型的预测能力 |
| 数字孪生 | 基于数据构建的、可推演的跑者生理模型 |
| 增量学习 | 用新数据更新现有模型而非重新训练 |
| 冷启动 | 新用户或数据不足时使用参数化基线模型的阶段 |
| GoalState | nanobot-ai 0.2.0 持久化目标系统，支持跨轮次目标追踪 |
| FallbackProvider | nanobot-ai 0.2.0 故障转移链，主备模型自动切换+断路器 |
| Model Presets | nanobot-ai 0.2.0 命名预设系统，快速切换模型+参数组合 |
| 推理可见化 | nanobot-ai 0.2.0 Chain-of-Thought 流式展示能力 |
| MCP Resources/Prompts | MCP 协议三要素中的资源和提示模板映射 |

## 附录B：变更记录

| 版本 | 日期 | 变更内容 |
|------|------|---------|
| v12.0 | 2026-05-24 | **Phase D 需求补充**：①新增 §5 Phase D 交互升级（v0.26-v0.29）完整需求规格；②v0.26.0 定义10项功能需求+4项非功能需求；③v0.27-v0.29 定义18项功能需求；④新增2项独立评估任务；⑤非功能需求新增NFR-08~NFR-10；⑥风险表新增5项Phase D相关风险；⑦术语表新增5项Phase D术语 |
| v11.1 | 2026-05-23 | **第二次精简**：①Section 3/4 Phase详细设计合并为验收标准单表；②Section 7验收总览合并为单句；③删除4.1/4.2/4.3三级子节 |
| v11.0 | 2026-05-23 | **v0.25.0发布修订**：①Phase C(v0.23-v0.25)标记为已完成并精简为摘要；②当前基线更新为v0.25.0；③精简冲突裁决为关键设计裁决；④删除已过时的详细验收标准和数据模型；⑤新增v0.24/v0.25功能摘要和成功标准 |
| v10.0 | 2026-05-20 | Phase C设计规格书对齐更新 |
| v9.0 | 2026-05-20 | Phase C设计规格书对齐更新 |
