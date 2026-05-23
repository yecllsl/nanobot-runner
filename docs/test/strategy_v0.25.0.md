# 测试策略文档 v0.25.0

> **版本**: v1.0.0
> **生成日期**: 2026-05-23
> **测试范围**: v0.25.0 自适应进化引擎
> **制定人**: 测试工程师 (TST-01)
> **输入依据**: 需求规格说明书 v10.0 / 架构设计说明书 v12.0.2 / 架构评审报告 v0.25.0 / 开发交付报告 v0.25.0 / 代码评审报告 v0.25.0 / 任务清单 v0.25.0
> **对齐规范**: `.trae/完整流程调用规范.md` 4.1节/10.2节/10.3节

---

## 1. 测试范围

### 1.1 版本概述

v0.25.0 在 `src/core/evolution/` 模块递增式添加 3 个核心子组件 + 3 项架构评审整改，完成 Phase C 自适应进化引擎的最终阶段：

| 组件 | 职责 | 对应需求 | 优先级 |
|------|------|----------|--------|
| EvolutionController | 进化触发器（4条触发规则 + persist-first 执行策略） | REQ-0.25-01 | P0 |
| PromptTuner | 提示调优器（4维参数空间 + 自动微调 + JSON 持久化） | REQ-0.25-02 | P1 |
| EvolutionReporter | 进化报告器（月度报告生成 + 个性化程度） | REQ-0.25-03 | P2 |

### 1.2 新增/修改模块清单

| 模块 | 变更类型 | 文件路径 |
|------|---------|----------|
| **进化控制器** | 新增 | `src/core/evolution/evolution_controller.py` |
| **提示调优器** | 新增 | `src/core/evolution/prompt_tuner.py` |
| **进化报告器** | 新增 | `src/core/evolution/evolution_reporter.py` |
| 数据模型 | 扩展 | `src/core/evolution/models.py` |
| 进化存储层 | 扩展 | `src/core/evolution/evolution_store.py` |
| 进化引擎编排层 | 扩展 | `src/core/evolution/evolution_engine.py` |
| Agent钩子 | 扩展 | `src/core/evolution/decision_log_hook.py` |
| 配置 | 扩展 | `src/core/evolution/config.py` |
| 应用上下文 | 扩展 | `src/core/base/context.py` |
| CLI命令 | 扩展 | `src/cli/commands/evolution.py`, `src/cli/handlers/evolution_handler.py` |
| Agent工具 | 扩展 | `src/agents/tools_evolution.py` |

### 1.3 不在测试范围的模块

- v0.23 决策追踪系统（DecisionLogger / OutcomeCollector / DecisionLogHook基础功能）-- 已在 v0.23 测试完成，仅回归验证
- v0.24 个性化学习系统（ResponseAnalyzer / CalibrationEngine / ModelEvolver）-- 已在 v0.24 测试完成，仅回归验证
- v0.20-v0.22 预测/孪生/质量收口模块 -- 仅回归验证
- 非功能需求验证（性能基准/安全审计）-- 由对应专项测试覆盖

---

## 2. 测试层级

### 2.1 层级划分

| 层级 | 主责方 | 目录 | 覆盖率目标 |
|------|--------|------|-----------|
| **单元测试** | 开发工程师已完成 | `tests/unit/core/evolution/` | core模块 >= 85% |
| **集成测试** | 开发工程师已完成 | `tests/integration/` | 关键链路覆盖 |
| **场景级集成测试** | 测试工程师（本文档主责） | `tests/integration/scene/` | P0/P1 场景 100% |
| **E2E测试** | 测试工程师（本文档主责） | `tests/e2e/` | P0 用户旅程 100% |
| **回归测试** | 测试工程师（本文档主责） | 全量 `tests/` | P0/P1 Bug 100% 验证 |

### 2.2 现有测试资产盘点

| 维度 | 数量 | 状态 |
|------|------|------|
| 全量测试用例 | **4471** | 全部通过 (4037 passed，含 evolution 366 + 集成 27) |
| evolution 单元测试 | 14 个测试文件 | models 99% / prompt_tuner 100% / controller 82% / engine 86% / store 84% / hook 92% / config 100% |
| evolution 集成测试 | 3 个测试文件 | test_evolution_controller_hook / test_prompt_tuner_chain / test_evolution_reporter_chain |
| 现有 E2E 测试 | 6 个测试文件 | test_user_journey / test_plan_e2e / test_transparency_e2e 等 |
| 现有场景集成测试 | 6 个测试文件 | test_real_workflow / test_sprint3_e2e 等 |

---

## 3. 测试用例设计

### 3.1 EvolutionController 测试用例（4条触发规则）

#### TC-CONTROLLER-001 ~ 004：VDOT预测误差触发规则 (TR-01)

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|---------|--------|
| TC-CTRL-001 | VDOT误差连续3次>5%触发重训练 | Store 中存在连续3次 prediction-actual 配对，误差分别为 6.2%/7.1%/5.8% | 调用 check_triggers() | TriggerCheckResult.triggered_actions 包含 1 个 action_type="retrain_model"、target_model_type="vdot"、priority="high" 的 EvolutionAction | P0 |
| TC-CTRL-002 | VDOT误差仅2次>5%不触发 | Store 中存在连续2次误差>5%（第3次误差<5%或不存在） | 调用 check_triggers() | triggered_actions 为空，skipped_conditions 包含 "VDOT预测误差未达连续3次阈值" | P0 |
| TC-CTRL-003 | VDOT配对数据不足3条不触发 | Store 中 prediction-actual 配对 < 3 条 | 调用 check_triggers() | triggered_actions 为空，skipped_conditions 包含 "VDOT预测配对数据不足(需≥3条)" | P1 |
| TC-CTRL-004 | VDOT查询限制 days=90 生效 | Store 中 91 天前有连续3次>5%误差，最近90天内无配对 | 调用 check_triggers() | triggered_actions 为空（仅扫描90天内数据） | P0 |

#### TC-CONTROLLER-005 ~ 008：连续拒绝触发规则 (TR-02)

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|---------|--------|
| TC-CTRL-005 | 连续2次拒绝推荐触发策略调整 | Store 中存在连续2条 DecisionLog + OutcomeRecord，recommendation_accepted 均为 False | 调用 check_triggers() | triggered_actions 包含 action_type="adjust_strategy"、target_model_type="prompt"、priority="medium" 的 EvolutionAction | P0 |
| TC-CTRL-006 | 仅1次拒绝不触发 | Store 中仅1条 recommendation_accepted=False | 调用 check_triggers() | triggered_actions 为空 | P0 |
| TC-CTRL-007 | 拒绝-接受-拒绝不触发（非连续） | 序列：拒绝 -> 接受 -> 拒绝 | 调用 check_triggers() | triggered_actions 为空（仅检查最近2条，第1和第3条之间被接受打断） | P1 |
| TC-CTRL-008 | 拒绝查询限制 days=90 生效 | 91天前有连续2次拒绝，最近90天内无拒绝 | 调用 check_triggers() | triggered_actions 为空 | P1 |

#### TC-CONTROLLER-009 ~ 012：新数据积累触发规则 (TR-03)

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|---------|--------|
| TC-CTRL-009 | 新数据积累>=50条触发增量学习 | trigger_state 中 last_incremental_count=100，count_decisions()=155 | 调用 check_triggers() | triggered_actions 包含 action_type="incremental_learn"、target_model_type="all"、priority="medium" 的 EvolutionAction | P0 |
| TC-CTRL-010 | 新数据积累<50条不触发 | trigger_state 中 last_incremental_count=100，count_decisions()=130 | 调用 check_triggers() | triggered_actions 为空，skipped_conditions 包含 "新数据积累不足" | P0 |
| TC-CTRL-011 | trigger_state 首次空值从0开始计数 | trigger_state.json 不存在（首次调用） | 调用 _load_last_incremental_count() | 返回 0 | P0 |
| TC-CTRL-012 | 增量学习成功后更新 trigger_state | 执行 incremental_learn 动作成功 | 动作执行完成后检查 trigger_state | trigger_state.json 中 last_incremental_count 更新为当前 count_decisions() 值 | P0 |

#### TC-CONTROLLER-013 ~ 014：月度复盘触发规则 (TR-04)

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|---------|--------|
| TC-CTRL-013 | 当月未生成报告触发月度复盘 | trigger_state 中 last_monthly_report="2026-04"，当前月份=2026-05 | 调用 check_triggers() | triggered_actions 包含 action_type="generate_report"、priority="low" 的 EvolutionAction | P0 |
| TC-CTRL-014 | 当月已生成报告不触发 | trigger_state 中 last_monthly_report="2026-05"，当前月份=2026-05 | 调用 check_triggers() | triggered_actions 为空，skipped_conditions 包含 "当月已生成报告" | P1 |

#### TC-CONTROLLER-015 ~ 020：动作执行 (persist-first 语义 + C-01 整改)

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|---------|--------|
| TC-CTRL-015 | retrain_model 先持久化后生效 | Mock ModelEvolver + EvolutionStore | 执行 execute_action(retrain_model) | 调用顺序：① save_model_params() → ② apply_params_to_instance()。save 失败则不调用 apply | P0 |
| TC-CTRL-016 | retrain_model 持久化失败不修改实例 | Mock save_model_params() 抛出异常 | 执行 execute_action(retrain_model) | apply_params_to_instance() 不被调用，action.executed=True，execution_result 含 "持久化异常" | P0 |
| TC-CTRL-017 | incremental_learn 逐模型持久化-生效 | Mock 3个模型均进化成功 | 执行 execute_action(incremental_learn) | 每个模型先 save_model_params() 再 apply_params_to_instance()，全部成功 | P0 |
| TC-CTRL-018 | incremental_learn 部分失败可追溯 (H-02) | vdot成功、injury数据不足、training_response持久化失败 | 执行 execute_action(incremental_learn) | execution_result 为 dict[str, list[IncrementalLearnResult]]，包含 3 个模型的 success/mae_before/mae_after/error。vdot=True, injury=False(ValueError), training_response=False(持久化异常) | P0 |
| TC-CTRL-019 | adjust_strategy 调用 auto_adjust_on_rejection | Mock PromptTuner | 执行 execute_action(adjust_strategy) | PromptTuner.auto_adjust_on_rejection() 被调用 1 次 | P1 |
| TC-CTRL-020 | generate_report 调用 Reporter.generate_report | Mock EvolutionReporter | 执行 execute_action(generate_report) | EvolutionReporter.generate_report() 被调用 1 次 | P1 |

#### TC-CONTROLLER-021 ~ 023：性能预算 (C-02 整改)

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|---------|--------|
| TC-CTRL-021 | check_triggers() 在1000条数据下<50ms | Store 含 1000 条决策+结果记录 | 计时执行 check_triggers() | 耗时 < 50ms | P0 |
| TC-CTRL-022 | check_triggers() 超50ms输出warning日志 | Mock Store 查询耗时 60ms | 执行 check_triggers() | logger.warning 输出含 "性能超预算" + 实际耗时 | P1 |
| TC-CTRL-023 | count_decisions() 轻量计数不加载全量数据 | Store 含 5000 条决策 | 调用 count_decisions() | 返回 5000，不 collect() 全量数据到内存 | P1 |

#### TC-CONTROLLER-024 ~ 025：异步执行

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|---------|--------|
| TC-CTRL-024 | execute_pending_actions() 使用 daemon Thread | triggered_actions 非空 | DecisionLogHook.after_iteration() 触发 | 创建 threading.Thread(daemon=True)，线程名含 "evolution"，不阻塞 after_iteration 返回 | P0 |
| TC-CTRL-025 | check_triggers() 同步执行不阻塞主流程 | - | 模拟 after_iteration() 调用 | check_triggers() 返回后 after_iteration 继续执行，execute_pending_actions 在独立线程 | P0 |

### 3.2 PromptTuner 测试用例（4维参数空间）

#### TC-TUNER-001 ~ 005：参数管理

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|---------|--------|
| TC-TUNER-001 | 首次 get_params() 返回默认值 | tuning/prompt_params.json 不存在 | 调用 get_params() | 返回全部 0.5 的 PromptTuningParams，update_count=0 | P0 |
| TC-TUNER-002 | get_params() 加载已持久化参数 | tuning/prompt_params.json 含 tone_intensity=0.7 | 调用 get_params() | 返回 tone_intensity=0.7, 其余保持 from_dict 后的值 | P0 |
| TC-TUNER-003 | update_params() 手动更新4维参数 | 当前参数全 0.5 | 调用 update_params(tone=0.7, detail=0.3, aggressive=0.2, data_driven=0.8) | tone=0.7, detail=0.3, aggressive=0.2, data_driven=0.8, update_count 自增 1 | P0 |
| TC-TUNER-004 | with_updates() clamp 到 [0.0, 1.0] | 当前全 0.5 | 调用 with_updates(tone=1.5, aggressive=-0.3) | tone=1.0(clamp), aggressive=0.0(clamp) | P0 |
| TC-TUNER-005 | reset_to_default() 恢复全部 0.5 | 当前参数 tone=0.7, detail=0.3 | 调用 reset_to_default() | 全部恢复 0.5，prompt_params.json 更新 | P0 |

#### TC-TUNER-006 ~ 009：自动微调 (auto_adjust_on_feedback)

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|---------|--------|
| TC-TUNER-006 | 低评分降低语气强度 | avg_score=2.0, acceptance_rate=0.5, 当前 tone=0.5 | 调用 auto_adjust_on_feedback(avg_score=2.0, acceptance_rate=0.5) | tone_intensity 降低 0.05（从 0.5 到 0.45） | P0 |
| TC-TUNER-007 | 高评分微幅提高语气 | avg_score=4.5, acceptance_rate=0.5, 当前 tone=0.5 | 调用 auto_adjust_on_feedback(avg_score=4.5, acceptance_rate=0.5) | tone_intensity 提高 0.025（step×0.5） | P1 |
| TC-TUNER-008 | 低接受率降低激进程度 | avg_score=3.0, acceptance_rate=0.2, 当前 aggressive=0.5 | 调用 auto_adjust_on_feedback(avg_score=3.0, acceptance_rate=0.2) | recommendation_aggressiveness 降低 0.05 | P0 |
| TC-TUNER-009 | 数据充足提高 data_driven | avg_score=3.0, acceptance_rate=0.5, Store 含 25 条配对，当前 data_driven=0.5 | 调用 auto_adjust_on_feedback(avg_score=3.0, acceptance_rate=0.5) | data_driven_weight 提高 0.025 | P1 |

#### TC-TUNER-010 ~ 013：拒绝调整 + 参数下限保护 (H-03 整改)

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|---------|--------|
| TC-TUNER-010 | auto_adjust_on_rejection 降低 aggressive + data_driven | 当前 aggressive=0.5, data_driven=0.5 | 调用 auto_adjust_on_rejection() | aggressive=0.45, data_driven=0.475（降低 step 和 step×0.5） | P0 |
| TC-TUNER-011 | aggressive 下限保护不低于 0.1 | 当前 aggressive=0.12 | 调用 auto_adjust_on_rejection() | aggressive=0.10（clamp 到下限 0.1，不降至 0.07） | P0 |
| TC-TUNER-012 | data_driven 下限保护不低于 0.2 | 当前 data_driven=0.21 | 调用 auto_adjust_on_rejection() | data_driven=0.20（clamp 到下限 0.2） | P0 |
| TC-TUNER-013 | 连续10次拒绝后参数不低于下限 | 初始 aggressive=0.5, data_driven=0.5 | 连续调用 auto_adjust_on_rejection() 10 次 | aggressive >= 0.1, data_driven >= 0.2 | P0 |

#### TC-TUNER-014 ~ 015：反弹机制 (H-03 整改)

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|---------|--------|
| TC-TUNER-014 | 接受推荐时 aggressive 恢复步长 0.08 | 当前 aggressive=0.15, acceptance_rate=0.8, avg_score=4.0 | 调用 auto_adjust_on_feedback(avg_score=4.0, acceptance_rate=0.8) | aggressive 增加 0.08（恢复步长 > 降低步长 0.05） | P0 |
| TC-TUNER-015 | 接近下限时输出 warning 日志 | 当前 aggressive=0.12 | 调用 auto_adjust_on_rejection() | logger.warning 输出含 "参数接近下限" 信息 | P1 |

#### TC-TUNER-016 ~ 017：JSON 持久化

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|---------|--------|
| TC-TUNER-016 | update_params 后持久化到 JSON | tuning/ 目录存在 | 调用 update_params(tone=0.7) | tuning/prompt_params.json 写入，含 tone_intensity=0.7 | P0 |
| TC-TUNER-017 | JSON文件损坏时返回默认值 | prompt_params.json 内容为无效 JSON | 调用 get_params() | 返回默认值（全部 0.5），不抛出异常 | P1 |

### 3.3 EvolutionReporter 测试用例（月度报告）

#### TC-REPORTER-001 ~ 007：报告生成

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|---------|--------|
| TC-REP-001 | generate_report() 返回完整 EvolutionReport | Store 含 50 条决策+结果，Calibration/PromptTuner 有数据 | 调用 generate_report(month="2026-05") | EvolutionReport 全部字段非空，report_id 为 UUID，month="2026-05" | P0 |
| TC-REP-002 | total_decisions 正确统计月度决策数 | Store 中 2026-05 有 47 条决策 | 调用 generate_report(month="2026-05") | total_decisions=47 | P0 |
| TC-REP-003 | decision_acceptance_rate 正确计算 | 47 条决策中 32 条 recommendation_accepted=True | 调用 generate_report(month="2026-05") | decision_acceptance_rate=32/47≈0.68 | P0 |
| TC-REP-004 | 个性化程度计算 (P2-01) | 各模型有校准参数，PromptTuner 参数偏离 0.5 | 调用 generate_report() | personalization_degree 在 0.0-1.0 范围内，基于3维度加权 | P1 |
| TC-REP-005 | 数据不足时 graceful 降级 | Store 中无 2026-05 数据 | 调用 generate_report(month="2026-05") | total_decisions=0, acceptance_rate=0.0，不抛异常 | P1 |
| TC-REP-006 | 校准摘要从 CalibrationEngine 获取 | 3个模型各有校准配置 | 调用 generate_report() | calibration_summary 为 dict，含 {"vdot": {...}, "injury": {...}, "training_response": {...}} | P1 |
| TC-REP-007 | 提示调优摘要从 PromptTuner 获取 | PromptTuner 中 tone=0.45, detail=0.50, aggressive=0.35 | 调用 generate_report() | prompt_tuning_summary 含 {"tone_intensity": 0.45, ...} | P1 |

#### TC-REPORTER-008 ~ 009：月度复盘集成

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|---------|--------|
| TC-REP-008 | 报告生成后更新 last_monthly_report | trigger_state 中 last_monthly_report="2026-04" | 执行 generate_report(month="2026-05") + 更新 trigger_state | trigger_state.json 中 last_monthly_report="2026-05" | P0 |
| TC-REP-009 | 当月已生成报告不重复触发 | last_monthly_report="2026-05" | 执行 _check_monthly_review_trigger() | 返回 None | P1 |

### 3.4 架构评审整改测试用例

#### TC-FIX-001 ~ 003：H-01 编排层一致性

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|---------|--------|
| TC-FIX-001 | DecisionLogHook 持有 EvolutionEngine 引用 | AppContext 完整注入 v0.25 组件 | 检查 DecisionLogHook 构造函数 | 参数为 evolution_engine: EvolutionEngine（而非 evolution_controller） | P0 |
| TC-FIX-002 | after_iteration 通过 EvolutionEngine 间接调用 | Hook 连接完整 | 触发 after_iteration | 调用路径: hook -> engine.check_evolution_triggers() -> controller.check_triggers() | P0 |
| TC-FIX-003 | 异步执行通过 engine.execute_evolution_action() | triggered_actions 非空 | after_iteration 触发异步执行 | daemon 线程调用 engine.execute_evolution_action() 而非 controller.execute_pending_actions() | P0 |

#### TC-FIX-004 ~ 006：H-02 部分失败处理

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|---------|--------|
| TC-FIX-004 | IncrementalLearnResult 结构化记录 | 3个模型分别返回成功/数据不足/异常 | 执行 incremental_learn | execution_result 为 dict，含按 model_type 分组的 IncrementalLearnResult 列表 | P0 |
| TC-FIX-005 | 部分失败时 action.executed=True | vdot 成功但 injury 失败 | 执行 incremental_learn | action.executed=True, execution_result 中 vdot.success=True, injury.success=False | P0 |
| TC-FIX-006 | execution_result 向后兼容字符串 | 执行 retrain_model 动作 | 检查 execution_result | execution_result 为 str 类型（如 "模型进化完成: MAE 0.052→0.041"） | P1 |

#### TC-FIX-007 ~ 009：H-03 参数下限保护

（已在 TC-TUNER-011 ~ 015 中覆盖，此处仅汇总交叉引用）
- TC-TUNER-011: aggressive 下限 0.1
- TC-TUNER-012: data_driven 下限 0.2
- TC-TUNER-013: 连续 10 次拒绝后保护生效
- TC-TUNER-014: 反弹机制步长 0.08

### 3.5 CLI 命令测试用例

| 用例ID | 用例名称 | 操作步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|--------|
| TC-CLI-001 | evolution triggers 输出已触发动作 | `uv run nanobotrun evolution triggers` | Rich 面板输出已触发动作（类型/原因/优先级）和跳过条件 | P0 |
| TC-CLI-002 | evolution triggers 无触发时输出空状态 | Store 中无触发条件满足 | 同上命令 | 面板输出 "无待执行进化动作"，skipped_conditions 列出所有跳过原因 | P1 |
| TC-CLI-003 | evolution report --month 2026-05 | `uv run nanobotrun evolution report --month 2026-05` | Rich 面板输出月度进化报告（决策数/准确率/接受率/模型版本/个性化程度/建议） | P0 |
| TC-CLI-004 | evolution report 无参数默认当月 | `uv run nanobotrun evolution report` | 输出当月进化报告，month 字段为当前月份 | P1 |
| TC-CLI-005 | evolution tune --tone 0.7 --detail 0.5 --aggressive 0.3 --data-driven 0.6 | `uv run nanobotrun evolution tune --tone 0.7 --detail 0.5 --aggressive 0.3 --data-driven 0.6` | Rich 面板输出调整后的参数，tone=0.7, detail=0.5, aggressive=0.3, data_driven=0.6 | P0 |
| TC-CLI-006 | evolution tune 参数范围校验 | `uv run nanobotrun evolution tune --tone 1.5` | 报错：参数必须在 0.0-1.0 范围内 | P0 |
| TC-CLI-007 | evolution tune 部分参数更新 | `uv run nanobotrun evolution tune --tone 0.7` | 仅 tone 更新为 0.7，其余参数保持原值 | P1 |
| TC-CLI-008 | evolution status 显示 v0.25 状态 | `uv run nanobotrun evolution status` | Rich 面板含 "v0.25 进化状态" 分区：个性化程度/上次进化时间/进化动作数/提示调优参数 | P0 |
| TC-CLI-009 | v0.25 组件未初始化时友好提示 | evolution_controller 未注入 | 执行任意 v0.25 CLI 命令 | 输出 "请先初始化v0.25组件"，success=false | P1 |

### 3.6 Agent 工具测试用例

| 用例ID | 用例名称 | 操作步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|--------|
| TC-AGENT-001 | check_evolution_triggers 返回 JSON | Agent 调用 check_evolution_triggers 工具 | 返回 {success: true, data: [{action_id, action_type, trigger_reason, ...}]} | P0 |
| TC-AGENT-002 | get_evolution_report 无参数返回当月报告 | Agent 调用 get_evolution_report 工具 | 返回 {success: true, data: {report_id, month, total_decisions, ...}} | P0 |
| TC-AGENT-003 | get_evolution_report --month 返回指定月 | Agent 调用 get_evolution_report(month="2026-05") | data.month="2026-05" | P1 |
| TC-AGENT-004 | adjust_prompt_params 部分更新 | Agent 调用 adjust_prompt_params(tone=0.7, aggressive=0.3) | 返回 {success: true, data: {tone_intensity: 0.7, recommendation_aggressiveness: 0.3, ...}}，其余维度不变 | P0 |
| TC-AGENT-005 | adjust_prompt_params 全部更新 | Agent 调用 adjust_prompt_params(tone=0.7, detail=0.5, aggressive=0.3, data_driven=0.6) | 返回 {success: true, data: {tone_intensity: 0.7, detail_level_score: 0.5, recommendation_aggressiveness: 0.3, data_driven_weight: 0.6}} | P0 |
| TC-AGENT-006 | v0.25 组件未初始化时返回错误 | evolution_engine 未注入 v0.25 组件 | Agent 调用任意 v0.25 工具 | 返回 {success: false, message: "请先初始化v0.25组件"} | P1 |

### 3.7 代码评审 P2 问题专项测试

| 用例ID | 用例名称 | 对应 P2 问题 | 验证方法 | 优先级 |
|--------|---------|-------------|---------|--------|
| TC-P2-001 | 个性化程度 3 维度加权计算 | P2-01 | 检查 EvolutionReporter._get_personalization_degree() 实际计算逻辑：是否包含校准偏离(0.4) + 调优偏离(0.3) + 进化次数(0.3) | P1 |
| TC-P2-002 | EvolutionConfig 含 v0.25 配置项 | P2-02 | 检查 config.py 是否包含 trigger_vdot_error_threshold 等 8 个字段 | P1 |
| TC-P2-003 | 预测准确率趋势基于真实数据 | P2-03 | 检查 _get_prediction_accuracy_trend() 是否基于 get_prediction_actual_pairs() 计算 MAE | P1 |
| TC-P2-004 | evolution_actions_count 正确更新 | P2-04 | 执行 execute_action() 后检查 trigger_state 中 evolution_actions_count 自增 | P1 |
| TC-P2-005 | last_evolution_time 正确更新 | P2-05 | 执行 execute_action() 后检查 trigger_state 中 last_evolution_time 更新为当前时间 | P1 |

### 3.8 回归测试用例

| 用例ID | 用例名称 | 测试范围 | 预期结果 | 优先级 |
|--------|---------|---------|---------|--------|
| TC-REG-001 | v0.23 决策追踪功能正常 | evolution history/feedback/accuracy/fidelity/status 命令 | 全部正常执行，输出格式不变 | P0 |
| TC-REG-002 | v0.24 个性化学习功能正常 | evolution calibration/response 命令 | 全部正常执行，输出格式不变 | P0 |
| TC-REG-003 | DecisionLogHook 基础功能不受影响 | 一次 Agent 对话产生一条 DecisionLog | DecisionLog 正确写入 decisions/ Parquet | P0 |
| TC-REG-004 | OutcomeCollector 基础功能不受影响 | check_plan_execution/check_prediction_accuracy 工具 | OutcomeRecord 正确写入 outcomes/ Parquet | P0 |
| TC-REG-005 | 全量单元测试 4037 通过 | `uv run pytest tests/` | 全部通过 | P0 |
| TC-REG-006 | mypy 类型检查通过 | `uv run mypy src/ --ignore-missing-imports` | 无新增类型错误 | P0 |
| TC-REG-007 | ruff lint 通过 | `uv run ruff check src/ tests/` | 无新增 lint 错误 | P0 |

---

## 4. 准入准出标准

### 4.1 测试准入标准（对齐规范 10.2）

在测试工程师开始执行场景级集成测试和 E2E 测试之前，必须满足以下全部条件：

| # | 准入条件 | 当前状态 | 验证方式 |
|---|---------|---------|---------|
| 1 | 开发交付报告已提交 | ✅ `docs/development/交付报告_v0.25.0.md` | 文档确认 |
| 2 | 单元测试覆盖率 >= 80% | ✅ models 99%/prompt_tuner 100%/controller 82%/engine 86%/store 84%/hook 92% | `pytest --cov` |
| 3 | 本地核心场景验证通过 | ✅ 开发工程师已验证 | 交付报告第10节质量验证 |
| 4 | 代码评审通过（REV-01） | ✅ `docs/review/代码评审报告_v0.25.0.md` 结论"通过" | 评审报告 |
| 5 | 功能开发每步已完成 verification 验证 | ✅ ruff/mypy/bandit 全部通过 | 交付报告第10节 |

**准入结论**: **全部满足**，可进入测试阶段。

### 4.2 测试准出标准（上线门禁）

以下条件**必须全部满足**才能输出测试通过报告，放行进入发布环节：

| # | 准出条件 | 量化标准 | 验证方式 |
|---|---------|---------|---------|
| 1 | P0 级测试用例 100% 通过 | 35+ 个 P0 用例全部通过 | 测试执行报告 |
| 2 | P1 级测试用例通过率 >= 95% | 25+ 个 P1 用例通过率 >= 95% | 测试执行报告 |
| 3 | 无致命（Blocker）级别 Bug | Blocker = 0 | Bug 清单 |
| 4 | 无严重（Critical）级别 Bug | Critical = 0 | Bug 清单 |
| 5 | 一般（Major）级别 Bug 修复率 >= 90% | Major 修复 >= 90% | Bug 清单 |
| 6 | v0.23/v0.24 回归测试 100% 通过 | TC-REG-001 ~ 007 全部通过 | 回归报告 |
| 7 | 全量单元测试 4471 个全部通过 | `uv run pytest tests/` 通过率 100% | CI 执行 |
| 8 | mypy 类型检查无新增错误 | `uv run mypy src/` 通过 | CI 执行 |
| 9 | ruff lint 无新增错误 | `uv run ruff check src/ tests/` 通过 | CI 执行 |
| 10 | check_triggers() 性能达标 | 1000 条数据下 < 50ms | 性能测试 |
| 11 | Hook 接入延迟 < 100ms (NFR-05) | after_iteration 总延迟 < 100ms | 性能测试 |

**不符合上线标准的处理**:
- 若 P0 用例未 100% 通过、存在 Blocker/Critical Bug，**必须明确禁止发布**，告知用户和运维智能体禁止发布，提供详细不通过原因和必须修复的问题清单
- 修复完成后重新执行回归测试，直到全部条件满足

### 4.3 发布准入标准（对齐规范 10.3）

发布准入由运维工程师主导，测试工程师提供上线结论：

| # | 发布准入条件 | 量化标准 |
|---|------------|---------|
| 1 | 测试上线结论为"建议上线" | 测试准出 11 项全部满足 |
| 2 | P0/P1 级 Bug 100% 修复验证 | 回归验证通过 |
| 3 | CICD 流水线验证通过 | 无构建失败 |
| 4 | 版本号已更新 | 版本号正确 |
| 5 | 用户文档已更新 | AGENTS.md / 架构设计 / 需求规格 |
| 6 | 全局指路文档已更新 | CHANGELOG 等 |

---

## 5. Mock 策略

### 5.1 Mock 原则

| 原则 | 说明 |
|------|------|
| **Mock 外部依赖** | EvolutionStore / CalibrationEngine / ModelEvolver / PromptTuner / EvolutionReporter / PredictionEngine |
| **禁止 Mock 内部业务逻辑** | EvolutionController.check_triggers() / execute_action() / PromptTuner.auto_adjust_*() 的核心算法逻辑不 Mock |
| **集成测试使用真实 Store + 临时目录** | 使用 `tmp_path` fixture 创建隔离的测试数据目录 |
| **E2E 测试使用真实 AppContext（无 LLM）** | 通过 CLI 命令调用，Mock LLM 响应 |

### 5.2 各组件 Mock 策略

| 组件 | 单元测试 | 集成测试 | E2E 测试 |
|------|---------|---------|---------|
| EvolutionController | Mock Store/CalibrationEngine/ModelEvolver/PromptTuner/Reporter | 真实 EvolutionStore + 临时目录 + Mock 其他 | 真实全链路 |
| PromptTuner | Mock EvolutionStore | 真实 EvolutionStore + 临时目录 | 真实全链路 |
| EvolutionReporter | Mock Store/CalibrationEngine/PromptTuner | 真实 EvolutionStore + 临时目录 + Mock CE/PT | 真实全链路 |
| DecisionLogHook | Mock EvolutionEngine（测试回调路径） | 真实 EvolutionStore + 临时目录 | - |

### 5.3 Mock 示例

```python
# EvolutionController 单元测试 Mock 示例
from unittest.mock import Mock, patch

@pytest.fixture
def mock_store():
    store = Mock(spec=EvolutionStore)
    store.get_prediction_actual_pairs.return_value = [
        (50.0, 47.0),  # error: 6.4%
        (51.0, 47.5),  # error: 7.4%
        (52.0, 49.0),  # error: 6.1%
    ]
    store.get_decision_outcome_pairs.return_value = []
    store.count_decisions.return_value = 100
    store.load_trigger_state.return_value = 0
    return store

@pytest.fixture
def controller(mock_store, mock_calibration, mock_evolver, mock_tuner, mock_reporter, config):
    return EvolutionController(
        store=mock_store,
        calibration_engine=mock_calibration,
        model_evolver=mock_evolver,
        prompt_tuner=mock_tuner,
        evolution_reporter=mock_reporter,
        config=config,
    )
```

---

## 6. 测试数据要求

### 6.1 测试数据构造

| 数据类型 | 数量要求 | 用途 | 构造方式 |
|---------|---------|------|---------|
| DecisionLog | 100-1000 条 | 触发条件检测性能测试 | `DecisionLogFactory` 辅助函数生成 |
| OutcomeRecord | 100-500 条 | 结果回填 + 配对查询 | `OutcomeRecordFactory` 辅助函数生成 |
| prediction-actual 配对 | 10-50 条 | VDOT 误差触发测试 | 构造不同误差的配对数据 |
| trigger_state.json | 2 种状态 | 缓存测试：空文件 / 含上次记录数 | 临时目录写入 |
| prompt_params.json | 3 种状态 | 持久化测试：不存在 / 默认值 / 自定义值 | 临时目录写入 |

### 6.2 测试数据约束

- **禁止使用真实用户数据**: 所有测试数据必须为脱敏/构造数据
- **单用户场景**: 所有数据在同一 `session_key` 下，符合项目单用户设计
- **数据隔离**: 每个测试使用独立的临时目录 (`tmp_path` fixture)，不污染全局状态
- **数据清理**: 测试结束后自动清理临时目录（pytest tmp_path 机制）

### 6.3 性能测试数据量

| 场景 | 数据量 | 目标延迟 |
|------|--------|---------|
| check_triggers() 基准 | 1000 条决策 + 500 条结果 | < 50ms |
| check_triggers() 压力 | 5000 条决策 + 2000 条结果 | < 100ms |
| count_decisions() | 10000 条决策（12 个月分片） | < 10ms |
| generate_report() | 500 条决策 + 300 条结果 | < 3s |

---

## 7. 风险评估

### 7.1 已识别风险

| 风险ID | 风险描述 | 等级 | 影响 | 缓解措施 | 验证方法 |
|--------|---------|------|------|---------|---------|
| R-01 | check_triggers() 性能退化 | 高 | Agent 交互延迟增加，用户体验下降 | C-02 整改已落地：days=90 限制 + trigger_state 缓存 + 性能监控日志 | TC-CTRL-021: 1000条数据<50ms |
| R-02 | daemon 线程数据一致性 | 高 | 进化结果静默丢失，校准-进化闭环断裂 | C-01 整改 "先持久化后生效" | TC-CTRL-015/016 |
| R-03 | incremental_learn 部分失败状态不一致 | 中 | 系统状态不一致且难以追溯 | H-02 整改 IncrementalLearnResult 结构化 | TC-CTRL-018 |
| R-04 | 提示调优参数极端化 | 中 | aggressive=0 导致推荐永远保守 | H-03 整改：下限保护 + 反弹机制 | TC-TUNER-011~015 |
| R-05 | EvolutionReporter 报告数据不准确 | 中 | P2-03/P2-04/P2-05：硬编码 MAE / 计数为0 / 时间为None | 代码评审已识别，需在测试中验证 | TC-P2-003/004/005 |
| R-06 | 回归风险：v0.25 破坏 v0.23/v0.24 | 中 | 现有进化功能异常 | v0.25 为递增式添加（可选注入），未注入时行为不变 | TC-REG-001~007 |
| R-07 | EvolutionConfig 缺失 v0.25 配置项 | 低 | 触发阈值和调优参数不可配置 | P2-02 已识别，模块级常量替代 | TC-P2-002 |
| R-08 | 个性化程度计算与架构设计不一致 | 低 | 报告数据不准确 | P2-01 已识别 | TC-P2-001 |
| R-09 | EvolutionReporter 多个方法吞异常 | 低 | 报告数据错误无法排查 | P3-06 建议添加日志 | 代码审查 |

### 7.2 风险应对时间线

| 阶段 | 应对措施 |
|------|---------|
| **测试前** | 确认 C-01/C-02/H-01/H-02/H-03 全部整改代码已合入 |
| **测试中** | 优先执行 P0 用例（35+ 个），发现 Blocker/Critical 立即提交 Bug |
| **测试后** | 针对 P2 问题（P2-01~P2-05）给出是否阻塞上线的明确判断 |

---

## 8. 测试执行计划

### 8.1 执行阶段

| 阶段 | 内容 | 预计用例数 | 预计工时 |
|------|------|-----------|---------|
| **阶段1：单元测试验证** | 执行现有 evolution 366 个单元测试，验证覆盖率达标 | 366 | 0.5h |
| **阶段2：集成测试验证** | 执行现有 3 个 evolution 集成测试 | 27 | 0.5h |
| **阶段3：场景级集成测试** | 执行本文档设计的 TC-CTRL/TUNER/REP/FIX 场景用例 | ~55 | 6h |
| **阶段4：CLI/Agent 工具测试** | 执行 CLI 命令和 Agent 工具端到端验证 | ~15 | 3h |
| **阶段5：回归测试** | 执行全量 4471 个测试用例 | 4471 | 1h (CI) |
| **阶段6：性能基准测试** | check_triggers() < 50ms / Hook 延迟 < 100ms | 2 | 1h |
| **阶段7：Bug 修复跟踪** | 根据测试结果提交 Bug、跟踪修复、回归验证 | - | 按需 |

### 8.2 执行顺序

```
阶段1（单元测试验证）→ 阶段2（集成测试验证）
    ↓ （通过后）
阶段3（场景级集成测试）
    ↓ （通过后）
阶段4（CLI/Agent 工具测试）
    ↓ （通过后）
阶段5（全量回归测试）+ 阶段6（性能基准测试）
    ↓ （通过后）
阶段7（Bug 修复跟踪，如有）
    ↓ （全部通过后）
输出测试通过报告
```

---

## 9. 测试环境

| 配置项 | 要求 |
|--------|------|
| Python | 3.11+ |
| 操作系统 | Windows（开发环境）/ Linux/macOS（CI 兼容） |
| 测试框架 | pytest 9.0+ |
| Mock 框架 | pytest-mock / unittest.mock |
| 覆盖率工具 | pytest-cov |
| 临时目录 | pytest tmp_path fixture |
| 测试数据目录 | `tests/data/evolution/`（如需预置数据） |
| CLI 测试 | 通过 `CliRunner` 或直接调用 handler |
| 性能测试 | `time.monotonic()` 计时 + `pytest-benchmark`（可选） |

---

## 10. 测试用例优先级统计

| 优先级 | 数量 | 说明 |
|--------|------|------|
| P0 | 35 | 核心业务逻辑 + 4条触发规则 + 3项架构整改 + CLI/Agent 核心功能 + 回归 |
| P1 | 28 | 边界条件 + 异常场景 + 性能监控 + 代码评审 P2 问题验证 |
| P2 | - | （本文档未设计 P2 级别用例，P2 功能由基础覆盖兜底） |
| **总计** | **63** | |

---

## 11. 附录

### 附录 A：与需求规格的覆盖矩阵

| 需求ID | 需求描述 | 优先级 | 覆盖用例 |
|--------|---------|--------|----------|
| REQ-0.25-01 AC-01 | VDOT误差连续3次>5%触发重训练 | P0 | TC-CTRL-001~004 |
| REQ-0.25-01 AC-02 | 连续2次拒绝调整推荐策略 | P0 | TC-CTRL-005~008 |
| REQ-0.25-01 AC-03 | 新数据>=50条触发增量学习 | P0 | TC-CTRL-009~012 |
| REQ-0.25-01 AC-04 | 月度复盘生成进化报告 | P0 | TC-CTRL-013~014, TC-REP-008~009 |
| REQ-0.25-01 AC-05 | 异步执行不阻塞主流程 | P0 | TC-CTRL-024~025 |
| REQ-0.25-02 AC-01 | 个性化语气 (tone_intensity) | P0 | TC-TUNER-001~007 |
| REQ-0.25-02 AC-02 | 信息密度 (detail_level_score) | P0 | TC-TUNER-001~005 |
| REQ-0.25-02 AC-03 | 推荐策略 (recommendation_aggressiveness) | P0 | TC-TUNER-008~015 |
| REQ-0.25-02 AC-04 | 可回滚 (reset_to_default) | P0 | TC-TUNER-005 |
| REQ-0.25-03 AC-01 | evolution status 进化引擎状态 | P0 | TC-CLI-008 |
| REQ-0.25-03 AC-02 | 状态面板展示各项指标 | P0 | TC-CLI-008 |
| REQ-0.25-03 AC-03 | evolution triggers 手动检查 | P0 | TC-CLI-001~002 |

### 附录 B：与架构设计决策的验证矩阵

| ADR | 设计决策 | 验证用例 |
|-----|---------|---------|
| ADR-009 | 规则引擎 + daemon Thread | TC-CTRL-001~025（全部触发规则 + 执行策略） |
| ADR-010 | 4维连续参数空间 + JSON 持久化 | TC-TUNER-001~017（全部参数管理 + 自动调优） |
| C-01 | 先持久化后生效 | TC-CTRL-015~016 |
| C-02 | 性能预算 < 50ms + 查询限制 + 缓存 | TC-CTRL-021~023 |
| H-01 | 编排层一致性 | TC-FIX-001~003 |
| H-02 | IncrementalLearnResult 结构化 | TC-FIX-004~006 |
| H-03 | 参数下限保护 + 反弹机制 | TC-TUNER-011~015 |

### 附录 C：变更记录

| 版本 | 日期 | 变更内容 |
|------|------|---------|
| v1.0.0 | 2026-05-23 | 初始版本：基于需求规格 v10.0、架构设计 v12.0.2、架构评审 v0.25.0、开发交付 v0.25.0、代码评审 v0.25.0、任务清单 v0.25.0 生成。覆盖 3 个核心子组件 + 3 项架构整改，共 63 个测试用例（P0:35, P1:28），对齐规范 10.2/10.3 准入准出标准。 |