# 需求规格说明书

> **文档版本**: v15.0
> **最后更新**: 2026-06-06
> **当前基线**: v0.28.0
> **覆盖版本**: v0.29.0
> **对齐产品规划**: v14.0 (2026-06-06)
> **对齐架构设计**: v20.0.0 (2026-06-06)

---

## 1. 项目概述

### 1.1 产品定位

Nanobot Runner 是一款桌面端私人 AI 跑步助理，基于 nanobot-ai 框架构建。产品从"记录跑步"升级为"预测跑步"再到"进化跑步"，核心价值：**本地化、隐私可控、专业可信、预测未来、自我进化**。

### 1.2 演进愿景

| 阶段 | 核心能力 | 对应版本 | 状态 |
|------|----------|----------|------|
| **记录跑步** | FIT解析、数据存储、基础统计 | v0.5-v0.19 | ✅ 完成 |
| **预测跑步** | ML增强预测、What-If推演、风险预警 | v0.20-v0.22 | ✅ 完成 |
| **进化跑步** | 决策追踪、自适应学习、个性化进化 | v0.23-v0.25 | ✅ 完成 |
| **交互升级** | 底座升级、新特性适配、WebUI | v0.26-v0.29 | 🏗️ 进行中（v0.26-v0.28 完成，v0.29 规划中） |

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
| WebUI基础 | AI对话交互、基础设置、WebSocket通道 | v0.27 |
| WebUI数据可视化 | 6大页面、10个API端点、FastAPI+React独立服务 | v0.28 |

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

Phase A 已交付 v0.20 ML增强预测（VDOT/比赛/伤病+模型管理）、v0.21 数字孪生引擎（5维度状态向量+What-If推演+计划对比）、v0.22 质量收口（UAT验证+缺陷收敛）。关键验收：VDOT预测误差<5%、全马预测误差<8分钟、伤病预警召回率>75%、4周VDOT推演误差<8%、单计划4周推演<10秒。详细需求规格见Git历史版本。

---

## 4. Phase C：自适应进化引擎（v0.23-v0.25）✅ 已完成

Phase C 已交付完整的"决策→校准→优化"闭环：v0.23 决策追踪（DecisionLog+OutcomeRecord+DecisionLogHook）、v0.24 个性化学习（ResponseAnalyzer+CalibrationEngine+ModelEvolver）、v0.25 自适应进化（EvolutionController+PromptTuner+EvolutionReporter）。关键验收：决策自动记录100%、忠实度可计算率>80%、Hook接入延迟<100ms、训练类型效果排名一致率>70%、校准后VDOT MAE降低≥15%、闭环自动运行率>90%。详细需求规格见Git历史版本。

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

**当前状态**：v0.26.0（底座升级+新特性适配）、v0.27.0（WebUI基础）、v0.28.0（WebUI数据可视化）已完成；v0.29.0（WebUI管理控制台）规划中。

### 5.2 v0.26.0 — 底座升级 + 新特性适配 ✅ 已完成

**主题**：nanobot-ai 0.2.0 底座升级 + GoalState/推理可见化/Model Presets 适配

**核心交付**：

| 维度 | 交付内容 |
|------|----------|
| 底座升级 | `nanobot-ai>=0.2.0`、零回归、API兼容性100%、ruff/mypy/pytest全量通过 |
| GoalState 适配 | SOUL.md 注入使用指导 + DecisionLogHook 读取 `goal_state_raw()` 关联决策 |
| 推理可见化 | DecisionLogHook 重写 `emit_reasoning()` 追加缓冲区 + `finalize_content()` 写入快照 |
| Model Presets | config.json 配置预设 + CLI `model list` 查看 + `/model <preset>` 切换 |
| 性能 | CLI 核心命令响应时间退化<20%（以v0.25为基线） |

**关键验收**：底座兼容性100%、5075用例零失败、覆盖率82.63%、核心CLI命令不发生>20%性能退化、GoalState/推理可见化/Model Presets 三项特性功能正常。

**不做的扩展**：FallbackProvider、MCP Resources/Prompts（独立评估）、WebUI（v0.27.0）、不重构现有代码。

### 5.3 v0.27.0 — WebUI 基础 ✅ 已完成

**主题**：复用 nanobot-ai 原生 WebUI，实现 AI 对话交互 + 基础设置

**前置依赖**：v0.26.0（nanobot-ai≥0.2.0、GoalState/推理可见化/Model Presets 已适配）

**核心交付**：

| 维度 | 交付内容 |
|------|----------|
| WebUI 启动 | `nanobotrun gateway start --webui` 启用后浏览器访问 `http://127.0.0.1:8765` 可加载并对话 |
| 工具调用 | RunFlowAgent 全量工具在 WebUI 中可正常调用（与飞书通道一致） |
| 流式输出 | Agent 回复逐字流式展示（delta 间隔<200ms），推理过程可见 |
| 多会话管理 | WebUI 原生支持创建/切换/删除对话，标题自动生成 |
| 基础设置 | 设置面板可切换 Model Presets、查看 Provider/时区配置 |
| 品牌自定义 | `bot_name="Nanobot-Runner"`, `bot_icon="🏃‍♂️"` 写入 AgentsConfig.defaults |
| WebSocket 配置 | config.json `websocket` 配置节 + 环境变量 `NANOBOT_WS_*` 覆盖 |
| 安全认证 | 默认仅监听 127.0.0.1 + token 认证 + token_issue_path 短期令牌 |
| Gateway 增强 | `gateway start --webui` 标志，自动注入 WebSocket 配置 |
| 统一会话（可选） | config.json 可选 `unified_session` 字段，默认关闭 |

**关键验收**：4489 用例零失败、覆盖率81%、WebUI 首屏<3s、WebSocket握手<100ms、流式延迟<200ms、工具调用成功率≥99%、token认证默认启用、向后兼容（不启用WebUI时飞书/CLI功能不受影响）。

**不做的扩展**：自定义WebUI组件、跑步数据图表、计划/进化控制台、后端HTTP API、修改nanobot-ai前端、修改Agent工具逻辑。

### 5.4 v0.28.0 — WebUI 数据可视化 ✅ 已完成

**主题**：建设独立Web数据可视化服务，提供跑步数据图表、活动浏览、身体信号展示等能力

**核心交付**：

| 维度 | 交付内容 |
|------|----------|
| 后端服务 | FastAPI独立服务（端口8766）+ 10个API端点 + Token认证中间件 |
| 前端应用 | 独立React SPA（Vite+Recharts+React Router+TailwindCSS） |
| 6大页面 | 首页仪表盘、VDOT趋势页、训练负荷页、活动列表页、活动详情页、身体信号页 |
| 功能需求 | 20项需求全部交付（P0:9项、P1:8项、P2:2项、全局:1项） |
| 非功能需求 | 7项NFR全部达标（首屏<2s、图表<1s、API P95<500ms、数据一致性<0.1%） |
| 数据一致性 | 所有图表数据与CLI命令输出数值一致（误差<0.1%） |

**关键验收**：6大页面功能完整、20项需求全部通过、7项非功能需求达标、数据一致性与CLI误差<0.1%、向后兼容不影响CLI/飞书/nanobot-ai WebUI。

**API端点**：`/api/webui/dashboard`、`/api/webui/vdot/trend`、`/api/webui/training-load`、`/api/webui/training-load/trend`、`/api/webui/activities`、`/api/webui/activities/{id}`、`/api/webui/body-signals`、`/api/webui/body-signals/hrv`、`/api/webui/body-signals/fatigue`、`/api/webui/body-signals/recovery`

> 详细设计见 Git 历史版本与 [架构设计说明书 v19.0.0+](../architecture/架构设计说明书.md) §11

### 5.5 v0.29.0 — WebUI 管理控制台

**主题**：训练计划管理 + 进化引擎控制台

| 编号 | 需求 | 优先级 | 验收标准 |
|------|------|--------|----------|
| REQ-D-37 | 训练计划查看 | P0 | WebUI 中可查看当前训练计划及每日安排 |
| REQ-D-38 | 计划执行进度 | P0 | 可查看计划完成率、忠实度 |
| REQ-D-39 | 计划调整 | P1 | 可通过对话调整训练计划 |
| REQ-D-40 | 进化状态面板 | P0 | 可查看进化引擎状态、触发条件 |
| REQ-D-41 | 提示参数调整 | P1 | PromptTuner 4维参数可通过滑块调整 |
| REQ-D-42 | 月度进化报告 | P1 | 可查看历史进化报告 |

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

| 编号 | 需求 | 标准 | 适用版本 |
|------|------|------|----------|
| NFR-01 | 预测响应时间 | <5秒 | v0.20+ |
| NFR-02 | ML推理延迟 | <100ms | v0.20+ |
| NFR-03 | Hook接入延迟 | <100ms | v0.23+ |
| NFR-04 | 本地存储 | 所有数据本地存储，零外联 | 全版本 |
| NFR-05 | 不确定性声明 | 预测/推演输出标注置信区间和不确定性 | v0.20+ |
| NFR-06 | 无侵入接入 | 新模块通过Hook/包装接入，不修改核心逻辑 | 全版本 |
| NFR-07 | 降级策略 | 数据不足时自动降级到参数化基线 | v0.20+ |
| NFR-D-11 | WebUI 首屏加载 | 浏览器首次访问 < 3s | v0.27+ |
| NFR-D-12 | WebSocket 连接延迟 | 握手到连接建立 < 100ms | v0.27+ |
| NFR-D-13 | 流式输出延迟 | Agent delta 到 WebUI 展示 < 200ms | v0.27+ |
| NFR-D-14 | 工具调用兼容性 | WebUI 调用成功率与飞书一致（≥99%） | v0.27+ |
| NFR-D-15 | 安全默认 | WebSocket 仅监听 127.0.0.1；token 认证默认启用 | v0.27+ |
| NFR-D-16 | 向后兼容 | 不启用WebUI时飞书/CLI功能不受影响 | v0.27+ |
| NFR-D-17 | 仪表盘首屏加载 | < 2s | v0.28+ |
| NFR-D-18 | 图表渲染时间 | < 1s | v0.28+ |
| NFR-D-19 | 活动列表分页响应 | < 500ms | v0.28+ |
| NFR-D-20 | API响应时间 | < 500ms | v0.28+ |
| NFR-D-21 | 数据一致性 | 误差<0.1% | v0.28+ |
| NFR-D-22 | 向后兼容 | 不影响CLI/飞书 | v0.28+ |
| NFR-D-23 | 安全默认 | API需认证 | v0.28+ |

---

## 8. 验收总览

| Phase | 版本 | 状态 | 关键验收 |
|-------|------|------|----------|
| Phase A | v0.20-v0.22 | ✅ 已完成 | VDOT误差<5%、全马误差<8min、伤病召回率>75%、推演误差<8% |
| Phase C | v0.23-v0.25 | ✅ 已完成 | 决策记录100%、忠实度可计算率>80%、Hook延迟<100ms、闭环运行率>90% |
| Phase D | v0.26.0 | ✅ 已完成 | 底座兼容性100%、5075用例零失败、覆盖率82.63%、性能退化<20% |
| Phase D | v0.27.0 | ✅ 已完成 | 4489用例零失败、覆盖率81%、WebUI首屏<3s、流式延迟<200ms |
| Phase D | v0.28.0 | ✅ 已完成 | 6大页面20项需求全部通过、7项NFR达标、数据一致性<0.1%、向后兼容 |
| Phase D | v0.29.0 | 📋 规划中 | 训练计划管理+进化引擎控制台+PromptTuner可视化 |

---

## 9. 风险与缓解

> 已完成版本的实施风险已闭环。下表聚焦 v0.29.0 实施期间及之后的活跃风险。

| 风险 | 等级 | 影响 | 缓解措施 | 适用版本 |
|------|------|------|----------|----------|
| 原生 WebUI 扩展能力不确定 | 中 | nanobot-ai WebUI是否支持自定义页面/路由扩展需验证 | v0.27.0已验证基础链路；v0.28.0先做技术验证Spike | v0.28.0 |
| Recharts 与 nanobot-ai WebUI 集成 | 低 | React版本兼容性、打包体积 | Recharts轻量且React生态原生兼容；按需加载 | v0.28.0 |
| 上游 WebUI 版本变更影响 | 低 | nanobot-ai WebUI 更新可能影响自定义组件 | 锁定 nanobot-ai 版本；自定义组件独立维护 | 全版本 |
| WebUI API 层与核心模块耦合 | 中 | API层直接调用核心模块，接口变更影响两端 | API层薄封装，核心模块接口稳定；版本化API路径 | v0.28.0+ |
| 活动列表/详情数据量性能 | 低 | 大量跑步记录时列表加载慢 | 分页加载（默认20条）；LazyFrame延迟求值 | v0.28.0 |
| WebSocket 通道资源竞争 | 低 | 飞书和 WebSocket 通道共享 AgentLoop | nanobot-ai AgentLoop 天然支持多通道；单用户并发极低 | v0.27+ |
| 统一会话上下文混淆 | 低 | 多通道共享会话时上下文交错 | 默认不启用 unified_session；P2 级别按需启用 | v0.27+ |
| FallbackProvider 缺失导致 LLM 单点 | 低 | 单 Provider 故障时无容错 | 独立评估后决定是否纳入 v0.30+ | v0.30+ |
| MCP Resources/Prompts 推迟 | 低 | MCP 生态利用不充分 | 当前 MCP Tool 映射已满足需求；独立评估后决定 | v0.30+ |

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
