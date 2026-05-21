# 测试策略 - v0.24.0 个性化学习

> **文档版本**: v1.0.0 | **创建日期**: 2026-05-21
> **对应指令**: TST-01 测试策略
> **覆盖版本**: v0.24.0
> **需求依据**: REQ_需求规格说明书 v10.0 (Section 4.2)
> **架构依据**: 架构设计说明书 v11.1.0 (Section 8.3)
> **评审依据**: 架构评审报告_v0.24.0.md
> **当前基线版本**: v0.23.0 (tag: v0.23.0)
> **开发分支**: feature/0.24.0

---

## 1. 测试范围与优先级

### 1.1 版本目标

v0.24.0 版本主题为 **个性化学习**，核心目标是让系统理解"这个跑者对什么训练响应最好"，并校准预测偏差。基于 v0.23.0 决策追踪系统（DecisionLog + OutcomeRecord）的数据积累，实现三个核心能力：训练响应性分析、预测校准、模型进化。

### 1.2 需求覆盖矩阵

| 需求ID | 优先级 | 需求描述 | 测试状态 | 核心组件 |
|--------|--------|---------|----------|----------|
| REQ-0.24-01 | **P0** | 训练响应性分析 | 必测 | ResponseAnalyzer |
| REQ-0.24-02 | **P1** | 预测校准层 | 必测 | CalibrationEngine |
| REQ-0.24-03 | **P1** | 个人化模型进化 | 必测 | ModelEvolver |
| REQ-0.24-04 | **P2** | 最佳训练窗口预测 | 排除（v0.25+） | TrainingWindowAnalyzer |

> **排除说明**: REQ-0.24-04 架构设计 Section 8.3.14 明确排除，CTL-VDOT 关联分析需 >= 6 个月数据，MVP 阶段用户数据不足，不纳入 v0.24.0 测试范围。

### 1.3 P-09 遗留项

| 遗留项 | 描述 | 测试状态 |
|--------|------|----------|
| P-09 | Fidelity 公式从二维度（体积0.55+时间0.45）升级为三维度（体积0.40+强度0.30+时间0.30） | 必测 |

### 1.4 新增/修改文件清单

| 文件路径 | 类型 | 说明 |
|---------|------|------|
| `src/core/evolution/response_analyzer.py` | 新增 | 训练响应性分析器 |
| `src/core/evolution/calibration_engine.py` | 新增 | 校准引擎 |
| `src/core/evolution/model_evolver.py` | 新增 | 模型进化器 |
| `src/core/evolution/models.py` | 扩展 | 新增6个v0.24数据模型 |
| `src/core/evolution/config.py` | 扩展 | 新增6个v0.24配置项 |
| `src/core/evolution/evolution_store.py` | 扩展 | 新增5个方法（读写校准/参数） |
| `src/core/evolution/evolution_engine.py` | 扩展 | 新增5个方法+构造函数扩展 |
| `src/core/evolution/outcome_collector.py` | 扩展 | Fidelity公式升级为三维度 |
| `src/agents/tools_evolution.py` | 扩展 | 新增2个Agent工具 |
| `src/cli/commands/evolution.py` | 扩展 | 新增2个CLI命令 |
| `src/cli/handlers/evolution_handler.py` | 扩展 | 新增2个handler方法 |
| `src/core/base/context.py` | 扩展 | AppContext新增属性+构建逻辑 |

### 1.5 不修改文件（无侵入原则保障）

以下 v0.23 已交付文件 v0.24 不做任何修改，仅通过测试验证其未被破坏：

| 文件 | 说明 |
|------|------|
| `src/core/evolution/decision_log_hook.py` | Hook 不修改 |
| `src/core/prediction/` 全部文件 | PredictionEngine 代码零修改 |
| `src/core/evolution/decision_logger.py` | 不修改 |
| `src/cli/app.py` | CLI 入口不修改 |

---

## 2. 测试类型与策略

### 2.1 测试金字塔分布

```
           /\
          /E2E\         2项：CLI命令端到端
         /------\
        /  集成  \       5项：跨模块数据流+AppContext
       /----------\
      /   单元测试  \    35+项：ResponseAnalyzer/CalibrationEngine/ModelEvolver
     /--------------\
    /  现有回归测试   \   150+项：v0.23全量回归
   /------------------\
```

### 2.2 各类型测试策略

#### 2.2.1 单元测试

| 项目 | 说明 |
|------|------|
| **覆盖范围** | ResponseAnalyzer / CalibrationEngine / ModelEvolver / EvolutionConfig / 数据模型 / Fidelity公式 |
| **测试框架** | pytest + unittest.mock |
| **预期用例数** | >= 35 个 |
| **覆盖率目标** | 新增核心模块 >= 85% |
| **存放目录** | `tests/unit/core/evolution/` |
| **目标文件** | `test_response_analyzer.py` / `test_calibration_engine.py` / `test_model_evolver.py` / `test_config.py`（扩展） / `test_models.py`（扩展） |
| **核心验证点** | 训练类型推断、响应评分计算、偏差检测、EMA更新、幅度限制、Banister参数调整、fidelity三维度计算、数据不足降级 |

#### 2.2.2 集成测试

| 项目 | 说明 |
|------|------|
| **覆盖范围** | EvolutionStore + CalibrationEngine 联动 / EvolutionEngine + 所有v0.24子组件 / AppContext扩展 / 校准JSON读写 / Agent工具注册 |
| **测试框架** | pytest + tmp_path（临时目录） |
| **预期用例数** | >= 8 个 |
| **存放目录** | `tests/integration/` |
| **目标文件** | `test_evolution_integration.py`（扩展）/ 新增 `test_v024_integration.py` |
| **核心验证点** | 端到端校准流程、端到端响应分析、参数持久化+启动加载、EvolutionStore JSON读写、Agent工具连通性 |

#### 2.2.3 端到端（E2E）测试

| 项目 | 说明 |
|------|------|
| **覆盖范围** | CLI命令 `evolution calibration` / `evolution response` |
| **测试框架** | pytest + Typer CliRunner |
| **预期用例数** | >= 4 个 |
| **存放目录** | `tests/unit/cli/commands/` 或 `tests/e2e/` |
| **目标文件** | `test_evolution_cli.py`（扩展） |
| **核心验证点** | 命令参数解析、Rich面板输出、终端退出码、错误处理 |

#### 2.2.4 性能测试

| 项目 | 说明 |
|------|------|
| **覆盖范围** | 响应性分析耗时 / 校准计算耗时 / 校准配置读写耗时 |
| **测试框架** | pytest + time.perf_counter |
| **预期用例数** | >= 3 个 |
| **存放目录** | `tests/performance/` |
| **目标文件** | `test_evolution_performance.py`（扩展） |
| **性能指标** | 响应性分析 < 3秒 / 校准计算 < 1秒 / 配置读写 < 100ms |

#### 2.2.5 回归测试

| 项目 | 说明 |
|------|------|
| **覆盖范围** | v0.23 全部单元测试 + 集成测试 |
| **目标准则** | v0.23 已有测试 100% 通过，确认 v0.24 变更无破坏 |
| **测试量** | 150+ 个已有测试用例 |
| **执行方式** | `uv run pytest tests/unit/ tests/integration/` |

---

## 3. 测试准入准出标准

### 3.1 准入标准（Entry Criteria）

以下条件全部满足后，方可进入测试执行阶段：

| 编号 | 准入条件 | 验证方式 | 执行人 |
|------|---------|----------|--------|
| E-01 | 开发工程师交付单元测试报告，且通过率 = 100% | 审阅DEV交付报告 | 开发工程师 |
| E-02 | 新增核心模块（ResponseAnalyzer/CalibrationEngine/ModelEvolver）单元测试覆盖率 >= 85% | `pytest --cov` 报告 | 开发工程师 |
| E-03 | 代码通过 ruff check + mypy 类型检查 | 终端执行验证 | 开发工程师 |
| E-04 | 架构评审报告已通过（CRITICAL=0，HIGH 已修复） | 审阅架构评审报告 | 架构师 |
| E-05 | v0.23 已有测试全部通过，无退化 | 终端执行验证 | 开发工程师 |
| E-06 | 代码已合并至 feature/0.24.0 分支 | Git验证 | 开发工程师 |

### 3.2 准出标准（Exit Criteria）

以下条件全部满足后，方可输出测试通过报告，放行进入发布环节：

| 编号 | 准出条件 | 量化指标 | 验证方式 |
|------|---------|----------|----------|
| X-01 | P0 用例 100% 通过 | REQ-0.24-01 全部AC通过 | 测试执行结果 |
| X-02 | P1 用例 100% 通过 | REQ-0.24-02、REQ-0.24-03 全部AC通过 | 测试执行结果 |
| X-03 | 无致命/严重 Bug | CRITICAL=0, HIGH=0 | Bug清单审计 |
| X-04 | 一般 Bug 修复率 >= 90% | MEDIUM 类 Bug 修复率 | Bug清单审计 |
| X-05 | 核心业务流程全量闭环 | 响应分析+校准+进化全链路通过 | 集成测试结果 |
| X-06 | 回归测试 100% 通过 | v0.23 全部用例通过 | `pytest` 输出 |
| X-07 | 性能指标达标 | 分析<3s, 校准<1s, 读写<100ms | 性能测试结果 |
| X-08 | 需求验收标准 100% 覆盖 | REQ-0.24-01/02/03 共15项AC | AC 覆盖率矩阵 |

### 3.3 上线门禁（Release Gate）

| 门禁项 | 通过标准 | 不通过后果 |
|--------|---------|-----------|
| 核心用例通过率 | P0+P1 用例 100% | **禁止发布**，明确告知运维智能体 |
| 致命/严重 Bug | 0 个 | **禁止发布**，强制修复后重测 |
| 回归破坏 | v0.23 全部用例通过 | **禁止发布**，定位并修复退化 |
| 性能退化 | 不劣于基线 | 标记风险后可放行（非阻断） |

---

## 4. 测试环境与数据

### 4.1 运行环境

| 项目 | 规范 |
|------|------|
| **操作系统** | Windows 10+/11, macOS 13+, Linux (Ubuntu 22.04+) |
| **Python** | 3.11.x（项目要求 Python >= 3.11, <3.13） |
| **包管理** | uv Latest |
| **核心依赖** | polars >= 0.20, pyarrow, scikit-learn >= 1.3.0, scipy >= 1.10.0 |
| **测试依赖** | pytest >= 8.0, pytest-cov, pytest-mock |
| **执行命令** | `uv run pytest tests/` |

### 4.2 测试数据要求

| 数据类型 | 构造方式 | 说明 |
|----------|---------|------|
| DecisionLog 测试数据 | `DecisionLog.from_dict()` 手动构造 | 包含不同的 runner_state、prediction_snapshot、recommendation_text、tool_call_chain |
| OutcomeRecord 测试数据 | `OutcomeRecord.from_dict()` 手动构造 | 包含实际的 actual_vdot、execution_fidelity、prediction_error |
| 训练-结果配对数据 | 时间关联的 DecisionLog + OutcomeRecord | 通过 decision_id 配对 |
| Parquet 测试数据 | EvolutionStore 写入临时目录 | 使用 tmp_path fixture |
| 校准配置 JSON | 手动构造 CalibrationProfile + 写入临时 `calibrations/` 目录 |
| 强度因子数据 | PlanExecutionData 含 planned/actual intensity_factor | 覆盖5种session_type |

### 4.3 Mock 策略

遵循测试指南 `docs/guides/testing_guide.md` 的规范：

| 组件 | Mock 策略 | 原因 |
|------|----------|------|
| **EvolutionStore** | 单元测试 Mock，集成测试用真实实例+临时目录 | 隔离存储依赖 |
| **PredictionEngine** | 单元测试 Mock，集成测试不Mock | 单元隔离、集成验证 |
| **SessionRepository** | 单元测试 Mock | ResponseAnalyzer 已不依赖（整改 HIGH-1） |
| **CalibrationEngine** | 单元测试 Mock（ModelEvolver 测试时），集成测试不Mock | 隔离校准依赖 |
| **LLM / Agent 工具** | 单元测试 Mock，E2E 测试不Mock | Agent 调用外部服务 |
| **文件系统** | 使用 `tmp_path` fixture，不Mock | 精确验证 JSON 读写 |

### 4.4 测试数据构造规范

**严禁使用真实用户数据**。所有测试数据必须为虚构数据：

```python
# DecisionLog 虚构数据示例
mock_decision = DecisionLog.from_dict({
    "decision_id": "test-d-001",
    "timestamp": "2026-01-15T08:00:00",
    "runner_state": {"vdot": 45.0, "ctl": 60.0, "atl": 55.0, "tsb": 5.0, "fatigue_score": 0.3},
    "decision_type": "TRAINING_ADVICE",
    "tool_call_chain": [
        {"name": "predict_training_response", "args": {"session_type": "interval"}, "result_summary": "..."}
    ],
    "prediction_snapshot": {"predicted_vdot": 45.5, "model_type": "vdot"},
    "recommendation_text": "建议本周进行2次间歇训练",
    "execution_status": "executed",
    "recommendation_accepted": True,
    "session_key": "test-session-001",
})

# OutcomeRecord 虚构数据示例
mock_outcome = OutcomeRecord.from_dict({
    "outcome_id": "test-o-001",
    "decision_id": "test-d-001",
    "outcome_timestamp": "2026-01-22T08:00:00",
    "actual_vdot": 45.2,
    "actual_injury": False,
    "execution_fidelity": 0.85,
    "user_feedback_score": 4,
    "user_feedback_text": "感觉间歇训练效果很好",
    "prediction_error": 0.66,
    "prediction_direction": "overestimate",
    "session_id": "session-001",
})
```

---

## 5. 核心测试用例设计

### 5.1 REQ-0.24-01（P0）：训练响应性分析

#### TC-0.24-01-01：正常场景 - 齐全数据下的训练类型效果排名

| 字段 | 内容 |
|------|------|
| **用例ID** | TC-0.24-01-01 |
| **所属模块** | ResponseAnalyzer |
| **优先级** | P0 |
| **用例类型** | 单元测试 - 功能测试 |
| **前置条件** | 构造 >= 30 条 DecisionLog + OutcomeRecord 配对（5种训练类型各 >= 5 条，fidelity >= 0.7），各类型VDOT变化量有梯级差异（interval 最高，recovery 最低） |
| **操作步骤** | 1. 注入 Mock EvolutionStore，返回预设配对数据<br>2. 调用 `ResponseAnalyzer.analyze(months=6)` |
| **预期结果** | 1. `TrainingResponseReport.data_sufficient = True`<br>2. `training_responses` 含5个 TrainingTypeResponse<br>3. `best_type = "interval"`（VDOT 提升最大）<br>4. `worst_type = "recovery"`（VDOT 提升最小）<br>5. 各类型 `response_score` 介于 [0, 1]<br>6. 排名与输入数据的VDOT变化量一致 |
| **验证点** | 排名正确性、数据充足标识、画像摘要文本、各类型样本数 |

---

#### TC-0.24-01-02：边界场景 - 数据不足（某类型样本 < 5）

| 字段 | 内容 |
|------|------|
| **用例ID** | TC-0.24-01-02 |
| **所属模块** | ResponseAnalyzer |
| **优先级** | P0 |
| **用例类型** | 单元测试 - 边界条件测试 |
| **前置条件** | 构造配对数据：interval 3条, threshold 6条, long 6条, recovery 2条, easy 7条（interval 和 recovery 不满足 >= 5 门槛） |
| **操作步骤** | 1. 注入 Mock EvolutionStore<br>2. 调用 `ResponseAnalyzer.analyze(months=6)` |
| **预期结果** | 1. `TrainingResponseReport.data_sufficient = False`<br>2. interval 和 recovery 标记为不参与排名<br>3. 仅 threshold/long/easy 参与排名<br>4. `profile_summary` 含"数据不足"提示 |
| **验证点** | 数据不足降级逻辑、不足类型不参与排名、data_sufficient 标识正确 |

---

#### TC-0.24-01-03：数据流 - VDOT变化量计算路径（架构评审 HIGH-1 整改验证）

| 字段 | 内容 |
|------|------|
| **用例ID** | TC-0.24-01-03 |
| **所属模块** | ResponseAnalyzer |
| **优先级** | P0 |
| **用例类型** | 单元测试 - 集成验证 |
| **前置条件** | 构造 DecisionLog（runner_state.vdot=45.0）和 OutcomeRecord（actual_vdot=45.3, fidelity>=0.7） |
| **操作步骤** | 1. 验证 `ResponseAnalyzer._get_eligible_pairs()` 返回该配对<br>2. 验证 VDOT 变化量计算：`avg_vdot_delta = 45.3 - 45.0 = 0.3` |
| **预期结果** | 1. 配对通过 fidelity 筛选<br>2. VDOT 变化量正确计算<br>3. **未调用** SessionRepository 的任何方法（无侵入验证） |
| **验证点** | 不使用 SessionRepository、仅用 DecisionLog.runner_state.vdot + OutcomeRecord.actual_vdot |

---

#### TC-0.24-01-04：训练类型推断 - 三级优先级验证（架构评审 HIGH-4 整改验证）

| 字段 | 内容 |
|------|------|
| **用例ID** | TC-0.24-01-04 |
| **所属模块** | ResponseAnalyzer |
| **优先级** | P0 |
| **用例类型** | 单元测试 - 算法验证 |
| **前置条件** | 构造3组不同来源的训练类型数据 |
| **操作步骤** | 1. **优先级1**: 构造 tool_call_chain 含 `predict_training_response` 且 `session_type="interval"` → 验证推断为 "interval"<br>2. **优先级2**: 构造 recommendation_text="本周进行节奏跑训练" → 验证推断为 "threshold"<br>3. **优先级3**: 无可匹配数据 → 验证推断为 "unknown"<br>4. **冲突规则**: 构造 recommendation_text="轻松恢复跑"（同时匹配 easy 和 recovery） → 验证 "recovery" 优先 |
| **预期结果** | 1. 结构化数据优先被使用<br>2. 关键词匹配正确<br>3. recovery 优先于 easy<br>4. 无匹配返回 "unknown"，不参与排名 |
| **验证点** | 三级优先级规则、冲突解决规则、兜底返回 "unknown" |

---

#### TC-0.24-01-05：异常场景 - 无决策-结果配对数据

| 字段 | 内容 |
|------|------|
| **用例ID** | TC-0.24-01-05 |
| **所属模块** | ResponseAnalyzer |
| **优先级** | P1 |
| **用例类型** | 单元测试 - 异常场景测试 |
| **前置条件** | EvolutionStore 返回空配对列表 |
| **操作步骤** | 调用 `ResponseAnalyzer.analyze(months=6)` |
| **预期结果** | 1. `total_pairs = 0`, `eligible_pairs = 0`<br>2. `data_sufficient = False`<br>3. `best_type = None`, `worst_type = None`<br>4. `profile_summary` 含"暂无数据"提示<br>5. 不抛出异常 |
| **验证点** | 空数据优雅降级、不阻塞流程 |

---

#### TC-0.24-01-06：响应性评分计算

| 字段 | 内容 |
|------|------|
| **用例ID** | TC-0.24-01-06 |
| **所属模块** | ResponseAnalyzer |
| **优先级** | P0 |
| **用例类型** | 单元测试 - 算法验证 |
| **前置条件** | 构造训练类型：interval 有 avg_vdot_delta=0.15, avg_fidelity=0.85 |
| **操作步骤** | 调用 `_calculate_response_score(avg_vdot_delta=0.15, avg_fidelity=0.85)` |
| **预期结果** | `response_score = normalize(0.15) × 0.6 + 0.85 × 0.4`，值在 [0, 1] 范围内 |
| **验证点** | 评分公式正确（VDOT 权重 0.6 + 忠实度权重 0.4） |

---

### 5.2 REQ-0.24-02（P1）：预测校准层

#### TC-0.24-02-01：正常场景 - 样本充足时执行校准

| 字段 | 内容 |
|------|------|
| **用例ID** | TC-0.24-02-01 |
| **所属模块** | CalibrationEngine |
| **优先级** | P0 |
| **用例类型** | 单元测试 - 功能测试 |
| **前置条件** | 构造 15 条预测-实际配对数据（VDOT 预测值系统高估 3%，mean(predicted)=46.5, mean(actual)=45.1），Mock EvolutionStore 返回这些配对 |
| **操作步骤** | 1. 调用 `CalibrationEngine.run_calibration(model_type="vdot")`<br>2. 调用 `CalibrationEngine.apply_calibration("vdot", 46.5)` |
| **预期结果** | 1. `CalibrationReport.direction = "overestimate"`<br>2. `CalibrationReport.sample_count = 15`<br>3. `CalibrationReport.scale_after ≈ 45.1 / 46.5 ≈ 0.97`<br>4. 校准后 `corrected = 46.5 × 0.97 = 45.105`<br>5. 校准配置已保存到 `calibrations/vdot_calibration.json` |
| **验证点** | 偏差方向正确、scale 计算正确、校准修正生效、JSON 持久化 |

---

#### TC-0.24-02-02：边界场景 - 样本不足时拒绝校准

| 字段 | 内容 |
|------|------|
| **用例ID** | TC-0.24-02-02 |
| **所属模块** | CalibrationEngine |
| **优先级** | P0 |
| **用例类型** | 单元测试 - 边界条件测试 |
| **前置条件** | 构造 8 条预测-实际配对数据（< calibration_min_samples=10） |
| **操作步骤** | 调用 `CalibrationEngine.run_calibration(model_type="vdot")` |
| **预期结果** | 1. 返回 `None` 或抛出明确提示 "样本不足，至少需要10条配对数据"<br>2. 不执行校准<br>3. 不写入校准配置 |
| **验证点** | 最低样本门槛、不执行校准、不写入文件 |

---

#### TC-0.24-02-03：EMA 更新稳定性验证

| 字段 | 内容 |
|------|------|
| **用例ID** | TC-0.24-02-03 |
| **所属模块** | CalibrationEngine |
| **优先级** | P0 |
| **用例类型** | 单元测试 - 算法验证 |
| **前置条件** | 当前 CalibrationProfile.scale=1.0，新计算 new_scale=0.95 |
| **操作步骤** | 调用 `_update_params_ema(current_scale=1.0, new_scale=0.95, alpha=0.7)` |
| **预期结果** | `scale = 0.7 × 0.95 + 0.3 × 1.0 = 0.965` |
| **验证点** | EMA 更新公式正确（alpha=0.7） |

---

#### TC-0.24-02-04：校准幅度上限限制

| 字段 | 内容 |
|------|------|
| **用例ID** | TC-0.24-02-04 |
| **所属模块** | CalibrationEngine |
| **优先级** | P0 |
| **用例类型** | 单元测试 - 边界条件测试 |
| **前置条件** | 构造极端数据使 new_scale 计算结果为 0.85（偏差 -15%，超出 ±10% 上限） |
| **操作步骤** | 调用 `_enforce_amplitude_limit(scale=0.85)` |
| **预期结果** | 返回 `scale=0.90`（被 clamp 至 [0.9, 1.1]） |
| **验证点** | 幅度限制生效、不超过 ±10% |

---

#### TC-0.24-02-05：异常场景 - predicted 和 actual 类型不匹配

| 字段 | 内容 |
|------|------|
| **用例ID** | TC-0.24-02-05 |
| **所属模块** | CalibrationEngine |
| **优先级** | P1 |
| **用例类型** | 单元测试 - 异常场景测试 |
| **前置条件** | EvolutionStore.get_prediction_actual_pairs() 返回空列表（prediction_snapshot 结构不匹配） |
| **操作步骤** | 调用 `CalibrationEngine.run_calibration(model_type="vdot")` |
| **预期结果** | 返回样本不足提示，不抛出异常 |
| **验证点** | 空数据优雅降级、prediction_snapshot Schema 验证 |

---

#### TC-0.24-02-06：校准重置功能

| 字段 | 内容 |
|------|------|
| **用例ID** | TC-0.24-02-06 |
| **所属模块** | CalibrationEngine |
| **优先级** | P1 |
| **用例类型** | 单元测试 - 功能测试 |
| **前置条件** | 已有校准配置 scale=0.97 |
| **操作步骤** | 调用 `CalibrationEngine.reset_calibration(model_type="vdot")` |
| **预期结果** | 1. 返回 `CalibrationProfile.default("vdot")`（scale=1.0）<br>2. `apply_calibration("vdot", 46.5)` 返回 `46.5`（无修正） |
| **验证点** | 重置到默认值、修正失效 |

---

#### TC-0.24-02-07：CalibrationReport 的 from_dict/to_dict 往返一致性

| 字段 | 内容 |
|------|------|
| **用例ID** | TC-0.24-02-07 |
| **所属模块** | CalibrationEngine + models |
| **优先级** | P1 |
| **用例类型** | 单元测试 - 数据模型测试 |
| **前置条件** | 构造 CalibrationReport 实例 |
| **操作步骤** | 1. `data = report.to_dict()`<br>2. `restored = CalibrationReport.from_dict(data)` |
| **预期结果** | restored 所有字段与原始 report 一致 |
| **验证点** | from_dict/to_dict 往返一致性（架构评审 LOW-1） |

---

### 5.3 REQ-0.24-03（P1）：个人化模型进化

#### TC-0.24-03-01：VDOT 预测模型进化 - 高估场景参数调整

| 字段 | 内容 |
|------|------|
| **用例ID** | TC-0.24-03-01 |
| **所属模块** | ModelEvolver |
| **优先级** | P0 |
| **用例类型** | 单元测试 - 功能测试 |
| **前置条件** | 构造 CalibrationReport：direction="overestimate", magnitude=0.05 |
| **操作步骤** | 调用 `ModelEvolver.evolve_vdot_model()` |
| **预期结果** | 1. `parameter_changes` 包含 tau_fitness 增加（体能积累更慢）、k1 降低<br>2. 单次调整幅度不超过参数值的 5%<br>3. `ModelEvolutionResult.improvement_pct >= 0` |
| **验证点** | Banister IR 参数调整方向正确、调整幅度限制、进化结果完整 |

---

#### TC-0.24-03-02：伤病风险模型进化 - 阈值调整

| 字段 | 内容 |
|------|------|
| **用例ID** | TC-0.24-03-02 |
| **所属模块** | ModelEvolver |
| **优先级** | P0 |
| **用例类型** | 单元测试 - 功能测试 |
| **前置条件** | 构造 CalibrationReport：direction="underestimate"（低估伤病风险），实际伤病事件多于预测 |
| **操作步骤** | 调用 `ModelEvolver.evolve_injury_model()` |
| **预期结果** | 1. `parameter_changes` 包含 risk_warning_threshold 降低（更敏感）<br>2. 调整幅度不超过 5%<br>3. 参数变更记录完整 |
| **验证点** | 风险阈值调整方向正确、调整幅度限制 |

---

#### TC-0.24-03-03：参数持久化机制验证（架构评审 HIGH-3 整改验证）

| 字段 | 内容 |
|------|------|
| **用例ID** | TC-0.24-03-03 |
| **所属模块** | ModelEvolver + EvolutionStore |
| **优先级** | P0 |
| **用例类型** | 集成测试 |
| **前置条件** | 使用 tmp_path 作为 data_dir，初始无校准参数文件 |
| **操作步骤** | 1. 调用 `ModelEvolver.evolve_vdot_model()`<br>2. 验证 `calibrations/vdot_params.json` 文件已创建<br>3. 调用 `EvolutionStore.load_model_params("vdot")` 验证参数已持久化<br>4. 模拟 AppContext 启动：加载参数覆盖 PredictionConfig 默认值 |
| **预期结果** | 1. 参数 JSON 文件存在且内容正确<br>2. 加载的参数值与进化结果一致<br>3. `PredictionConfig` 参数被正确覆盖 |
| **验证点** | JSON 文件读写、参数覆盖加载、跨启动持久化 |

---

#### TC-0.24-03-04：训练响应模型进化 - Banister IR 参数校准

| 字段 | 内容 |
|------|------|
| **用例ID** | TC-0.24-03-04 |
| **所属模块** | ModelEvolver |
| **优先级** | P1 |
| **用例类型** | 单元测试 - 功能测试 |
| **前置条件** | 构造 CalibrationReport：direction="underestimate", model_type="training_response" |
| **操作步骤** | 调用 `ModelEvolver.evolve_training_response_model()` |
| **预期结果** | 1. `parameter_changes` 包含 tau_fitness 减少（体能积累更快）、k1 提高<br>2. 调整幅度不超过 5% |
| **验证点** | Banister IR 参数双向调整、低估场景方向正确 |

---

#### TC-0.24-03-05：参数调整幅度限制验证

| 字段 | 内容 |
|------|------|
| **用例ID** | TC-0.24-03-05 |
| **所属模块** | ModelEvolver |
| **优先级** | P1 |
| **用例类型** | 单元测试 - 边界条件测试 |
| **前置条件** | 当前 tau_fitness=42.0 |
| **操作步骤** | 模拟连续3次进化均高估，每次调用 `_adjust_banister_params()` |
| **预期结果** | 每次调整后 tau_fitness 变化不超过 `42.0 × 5% = 2.1` |
| **验证点** | 单次调整幅度上限 5% |

---

### 5.4 P-09 遗留：Fidelity 公式升级

#### TC-P09-01：三维度 Fidelity 计算 - 正常场景

| 字段 | 内容 |
|------|------|
| **用例ID** | TC-P09-01 |
| **所属模块** | OutcomeCollector（Fidelity 公式） |
| **优先级** | P0 |
| **用例类型** | 单元测试 - 算法验证 |
| **前置条件** | 构造 PlanExecutionData：体积偏差 0.05, 强度偏差 0.04, 时间偏差 0.03 |
| **操作步骤** | 调用 `_calculate_fidelity(volume_dev=0.05, intensity_dev=0.04, time_dev=0.03)` |
| **预期结果** | `fidelity = 1 - (0.40 × 0.05 + 0.30 × 0.04 + 0.30 × 0.03) = 1 - (0.020 + 0.012 + 0.009) = 0.959` |
| **验证点** | 三维度权重正确（体积 0.40 + 强度 0.30 + 时间 0.30） |

---

#### TC-P09-02：向后兼容 - planned_intensity_factor 为 0 时回退双维度

| 字段 | 内容 |
|------|------|
| **用例ID** | TC-P09-02 |
| **所属模块** | OutcomeCollector（Fidelity 公式） |
| **优先级** | P0 |
| **用例类型** | 单元测试 - 向后兼容测试 |
| **前置条件** | 构造 PlanExecutionData：体积偏差 0.05, 时间偏差 0.03, planned_intensity_factor=0 |
| **操作步骤** | 调用 `_calculate_fidelity()` 检测到 `planned_intensity_factor == 0` |
| **预期结果** | 回退到 v0.23 公式：`fidelity = 1 - (0.55 × 0.05 + 0.45 × 0.03) = 1 - (0.0275 + 0.0135) = 0.959` |
| **验证点** | 向后兼容性、v0.23 公式正确回退 |

---

#### TC-P09-03：强度因子查表规则验证

| 字段 | 内容 |
|------|------|
| **用例ID** | TC-P09-03 |
| **所属模块** | OutcomeCollector（Fidelity 公式） |
| **优先级** | P1 |
| **用例类型** | 单元测试 - 查表规则测试 |
| **前置条件** | 构造 session_type="interval" |
| **操作步骤** | 从查表获取 `planned_intensity_factor` |
| **预期结果** | `planned_intensity_factor = 1.1`（interval 对应的 TSS/min） |
| **验证点** | 5 种 session_type 查表值：interval=1.1, threshold=0.9, long=0.65, recovery=0.45, easy=0.50 |

---

### 5.5 CLI 命令端到端测试

#### TC-CLI-01：evolution calibration 命令正常执行

| 字段 | 内容 |
|------|------|
| **用例ID** | TC-CLI-01 |
| **所属模块** | CLI commands |
| **优先级** | P0 |
| **用例类型** | E2E 测试 |
| **前置条件** | 使用 Typer CliRunner，确保 calibrations/ 目录使用临时路径 |
| **操作步骤** | `runner.invoke(app, ["evolution", "calibration", "--model-type", "vdot"])` |
| **预期结果** | 1. 退出码 = 0<br>2. 输出含 "校准报告" / "Evolution 校准报告" / 模型类型<br>3. Rich 面板格式正确 |
| **验证点** | 命令参数解析、面板输出、非零退出码 |

---

#### TC-CLI-02：evolution calibration 样本不足提示

| 字段 | 内容 |
|------|------|
| **用例ID** | TC-CLI-02 |
| **所属模块** | CLI commands |
| **优先级** | P1 |
| **用例类型** | E2E 测试 |
| **前置条件** | Mock EvolutionStore 返回 < 10 条配对数据 |
| **操作步骤** | `runner.invoke(app, ["evolution", "calibration", "--model-type", "vdot"])` |
| **预期结果** | 1. 退出码 = 0（非错误退出）<br>2. 输出含"样本不足"提示信息 |
| **验证点** | 数据不足时的用户友好提示 |

---

#### TC-CLI-03：evolution response 命令正常执行

| 字段 | 内容 |
|------|------|
| **用例ID** | TC-CLI-03 |
| **所属模块** | CLI commands |
| **优先级** | P0 |
| **用例类型** | E2E 测试 |
| **前置条件** | Mock EvolutionStore 返回足够配对数据，构造不同类型训练数据 |
| **操作步骤** | `runner.invoke(app, ["evolution", "response", "--months", "6"])` |
| **预期结果** | 1. 退出码 = 0<br>2. 输出含各训练类型排名<br>3. 输出含画像摘要<br>4. 最佳/最差训练类型标识正确 |
| **验证点** | 命令参数解析、排名输出、画像摘要 |

---

#### TC-CLI-04：evolution response 数据不足提示

| 字段 | 内容 |
|------|------|
| **用例ID** | TC-CLI-04 |
| **所属模块** | CLI commands |
| **优先级** | P1 |
| **用例类型** | E2E 测试 |
| **前置条件** | Mock EvolutionStore 返回空配对数据 |
| **操作步骤** | `runner.invoke(app, ["evolution", "response", "--months", "6"])` |
| **预期结果** | 1. 退出码 = 0<br>2. 输出含"数据不足"/"暂无数据"提示 |
| **验证点** | 空数据场景用户友好提示 |

---

### 5.6 集成测试用例

#### TC-INT-01：端到端校准流程（EvolutionStore + CalibrationEngine）

| 字段 | 内容 |
|------|------|
| **用例ID** | TC-INT-01 |
| **所属模块** | EvolutionStore + CalibrationEngine |
| **优先级** | P0 |
| **用例类型** | 集成测试 |
| **前置条件** | 使用 tmp_path 创建临时数据目录，预置 DecisionLog + OutcomeRecord 数据 |
| **操作步骤** | 1. 初始化 EvolutionStore（tmp_path）<br>2. 写入 15 条预测-结果配对数据<br>3. 初始化 CalibrationEngine，注入 store<br>4. 调用 run_calibration("vdot")<br>5. 验证 calibrations/vdot_calibration.json 文件存在<br>6. 读取文件验证内容正确 |
| **预期结果** | 1. 校准流程完整执行<br>2. JSON 文件正确写入<br>3. 校准报告数据正确 |
| **验证点** | 文件系统读写、组件间数据传递、JSON 格式正确 |

---

#### TC-INT-02：参数持久化 + AppContext 启动加载

| 字段 | 内容 |
|------|------|
| **用例ID** | TC-INT-02 |
| **所属模块** | ModelEvolver + EvolutionStore + AppContext |
| **优先级** | P0 |
| **用例类型** | 集成测试 |
| **前置条件** | 使用 tmp_path 创建临时数据目录 |
| **操作步骤** | 1. 执行 ModelEvolver.evolve_vdot_model()<br>2. 持久化参数到 JSON<br>3. 模拟 AppContext 启动：创建新的 PredictionConfig，加载 model_params 覆盖<br>4. 验证 BanisterIRModel 使用进化后的参数 |
| **预期结果** | 1. 参数持久化成功<br>2. 覆盖加载成功<br>3. PredictionConfig 参数为进化后值 |
| **验证点** | 跨组件参数传递、持久化→加载全链路、参数覆盖验证 |

---

#### TC-INT-03：EvolutionEngine 编排层集成

| 字段 | 内容 |
|------|------|
| **用例ID** | TC-INT-03 |
| **所属模块** | EvolutionEngine + 所有 v0.24 子组件 |
| **优先级** | P1 |
| **用例类型** | 集成测试 |
| **前置条件** | 使用 tmp_path + Mock PredictionEngine |
| **操作步骤** | 1. 构建 EvolutionEngine（含 v0.24 子组件）<br>2. 调用 analyze_training_response(months=6)<br>3. 调用 run_calibration(model_type="vdot")<br>4. 调用 evolve_model(model_type="vdot")<br>5. 调用 apply_calibration_to_prediction("vdot", 46.5) |
| **预期结果** | 所有方法正确委托，不抛异常 |
| **验证点** | 薄编排层委托正确、v0.24 子组件注入生效 |

---

#### TC-INT-04：Agent 工具注册验证

| 字段 | 内容 |
|------|------|
| **用例ID** | TC-INT-04 |
| **所属模块** | agents/tools_evolution.py |
| **优先级** | P1 |
| **用例类型** | 集成测试 |
| **前置条件** | AppContext 初始化完成 |
| **操作步骤** | 1. 验证 `analyze_training_response` 工具已注册<br>2. 验证 `get_calibration_status` 工具已注册<br>3. 调用工具获取返回 JSON |
| **预期结果** | 1. 工具注册成功<br>2. 返回 JSON 含 `success`/`data`/`message` 字段 |
| **验证点** | 工具注册、JSON 返回格式规范 |

---

### 5.7 性能测试用例

#### TC-PERF-01：响应性分析耗时

| 字段 | 内容 |
|------|------|
| **用例ID** | TC-PERF-01 |
| **所属模块** | ResponseAnalyzer |
| **优先级** | P1 |
| **用例类型** | 性能测试 |
| **前置条件** | 构造 200 条配对数据（模拟年度数据量） |
| **操作步骤** | 执行 `ResponseAnalyzer.analyze(months=6)` 并计时 |
| **预期结果** | 耗时 < 3 秒 |
| **验证点** | 性能基准达标 |

---

#### TC-PERF-02：校准计算耗时

| 字段 | 内容 |
|------|------|
| **用例ID** | TC-PERF-02 |
| **所属模块** | CalibrationEngine |
| **优先级** | P1 |
| **用例类型** | 性能测试 |
| **前置条件** | 构造 100 条配对数据 |
| **操作步骤** | 执行 `CalibrationEngine.run_calibration("vdot")` 并计时 |
| **预期结果** | 耗时 < 1 秒 |
| **验证点** | O(n) 计算性能 |

---

#### TC-PERF-03：校准配置读写耗时

| 字段 | 内容 |
|------|------|
| **用例ID** | TC-PERF-03 |
| **所属模块** | EvolutionStore |
| **优先级** | P2 |
| **用例类型** | 性能测试 |
| **前置条件** | 使用 tmp_path |
| **操作步骤** | 执行 `save_calibration_profile()` + `load_calibration_profile()` 并计时 |
| **预期结果** | 总耗时 < 100ms |
| **验证点** | JSON 文件读写性能达标 |

---

## 6. 风险评估与缓解

### 6.1 测试层面风险

| 编号 | 风险 | 等级 | 影响 | 缓解措施 |
|------|------|------|------|----------|
| **R-01** | 校准样本不足导致校准功能无法触发 | **高** | P1 需求（REQ-0.24-02/03）无法验证核心校准流程，用户使用 6 个月后才积累够 10 条配对数据 | 1. 单元测试用 Mock 数据绕过样本量限制<br>2. 集成测试预置充足数据<br>3. 在 `evolution status` 中提示用户数据积累进度<br>4. 降低测试用 `calibration_min_samples` 配置值加快验证 |
| **R-02** | 训练类型推断准确率影响 P0 需求可靠性 | **中** | 若 LLM 输出的 recommendation_text 格式变化，关键词匹配失效，导致大量配对数据标记为 "unknown" | 1. 已实现三级优先级（结构化数据 > 关键词 > 兜底）<br>2. 单元测试覆盖 5 种训练类型推断场景<br>3. 增加 `tool_call_chain` 中的结构化数据采集（优先级 1 不受 LLM 影响） |
| **R-03** | ModelEvolver 参数持久化文件损坏 | **中** | 进化后参数文件损坏，AppContext 启动加载失败，系统回退到默认参数，用户不可感知 | 1. `load_model_params()` 增加 JSON 校验<br>2. 校验失败时使用默认值并写警告日志<br>3. 集成测试覆盖文件损坏恢复场景<br>4. 保留 `reset_to_default()` 手动回退能力 |
| **R-04** | 回归测试量大，CI 执行时间过长 | **低** | 150+ 回归用例 + 35+ 新增用例，全量执行可能超过 5 分钟 | 1. 开发阶段按模块分步执行<br>2. 增量测试优先：`pytest tests/unit/core/evolution/`<br>3. 全量回归仅在合并前执行一次 |
| **R-05** | v0.23 已有代码被 v0.24 扩展意外破坏 | **中** | decision_log_hook.py 声明"不修改"，但 evolution_store.py / outcome_collector.py 的扩展可能引入副作用 | 1. v0.23 全量回归测试 100% 通过<br>2. 代码审查重点关注修改文件的变更范围<br>3. 集成测试覆盖 DecisionLogHook + v0.24 组件联动 |
| **R-06** | Fidelity 三维度公式中 actual_intensity_factor 无法获取 | **中** | 若 session 数据无 TSS 或查表失败，强度偏差无法计算，公式回退可能降低 fidelity 精确度 | 1. 已实现三级降级：优先 session TSS → 次选查表 → 兜底双维度<br>2. 单元测试覆盖三种路径<br>3. 向后兼容保证功能不阻塞 |

### 6.2 需求层面风险

| 编号 | 风险 | 等级 | 影响 | 缓解措施 |
|------|------|------|------|----------|
| **R-07** | VDOT 变化量数据稀疏（架构评审 HIGH-1 关联风险） | **高** | OutcomeRecord.actual_vdot 仅在 check_prediction_accuracy 调用时填充，大量记录为 None，实际可用配对极少 | 1. 已在架构 v11.1.0 中改用 DecisionLog.runner_state.vdot（自动采集）<br>2. 增加实际 Vodot 回填的提醒（evolution status 提示）<br>3. 测试数据手工构造完整配对 |
| **R-08** | prediction_snapshot 结构不统一（架构评审 HIGH-2 关联风险） | **中** | 若 DecisionLogHook 未按标准 Schema 填写 prediction_snapshot，CalibrationEngine 提取失败 | 1. 架构 v11.1.0 已定义标准 Schema<br>2. `get_prediction_actual_pairs()` 实现过滤逻辑<br>3. 单元测试覆盖 Schema 验证 |

---

## 7. 测试执行计划

### 7.1 分阶段执行

| 阶段 | 测试内容 | 执行时机 | 预期耗时 | 负责角色 |
|------|---------|----------|----------|---------|
| **阶段 1** | 数据模型 + Config + Fidelity 公式单元测试 | 开发交付后立即执行 | 30分钟 | 测试工程师 |
| **阶段 2** | ResponseAnalyzer / CalibrationEngine / ModelEvolver 单元测试 | 阶段1通过后 | 1小时 | 测试工程师 |
| **阶段 3** | 集成测试（EvolutionStore + Engine + AppContext） | 阶段2通过后 | 45分钟 | 测试工程师 |
| **阶段 4** | CLI E2E 测试 | 阶段3通过后 | 20分钟 | 测试工程师 |
| **阶段 5** | 性能测试 | 阶段4通过后 | 15分钟 | 测试工程师 |
| **阶段 6** | 全量回归测试 | 阶段5通过后 | 10分钟 | 测试工程师 |
| **阶段 7** | Bug 修复 + 回归测试 | 发现 Bug 后 | 按需 | 开发+测试 |

### 7.2 执行命令快速参考

```bash
# 阶段1：新增模块单元测试
uv run pytest tests/unit/core/evolution/ -v --cov=src/core/evolution --cov-report=term-missing

# 阶段2-3：集成测试
uv run pytest tests/integration/test_evolution_integration.py -v
uv run pytest tests/integration/test_v024_integration.py -v

# 阶段4：CLI测试
uv run pytest tests/unit/cli/ -k "evolution" -v

# 阶段5：性能测试
uv run pytest tests/performance/test_evolution_performance.py -v

# 阶段6：全量回归
uv run pytest tests/unit/ tests/integration/ -v --no-cov

# 覆盖率检查
uv run pytest tests/unit/core/evolution/ --cov=src/core/evolution --cov-fail-under=85
```

---

## 8. Bug 严重等级定义

| 等级 | 定义 | 示例 |
|------|------|------|
| **致命** | 阻断核心业务流程，无法继续测试 | ResponseAnalyzer.analyze() 抛出未捕获异常，CLI 命令崩溃 |
| **严重** | 核心功能异常，影响主流程使用 | 校准后 scale 计算错误导致修正方向反转，fidelity 公式权重错误 |
| **一般** | 非核心功能异常，不影响主流程 | 数据不足时提示信息不友好，JSON 读写日志缺失 |
| **优化** | 体验/规范类问题，不影响功能使用 | from_dict() 方法缺失（架构评审 LOW-1），注释不规范 |

---

## 9. 相关文档

| 文档 | 路径 | 内容 |
|------|------|------|
| 需求规格说明书 | `docs/requirements/REQ_需求规格说明书.md` | v0.24.0 需求定义和验收标准 |
| 架构设计说明书 | `docs/architecture/架构设计说明书.md` | v0.24.0 架构设计（Section 8.3） |
| 架构评审报告 | `docs/architecture/架构评审报告_v0.24.0.md` | 架构评审结论和整改清单 |
| 测试指南 | `docs/guides/testing_guide.md` | Mock策略、测试数据、隐私红线 |
| 开发指南 | `docs/guides/development_guide.md` | 编码规范、Polars约束 |
| 指令手册 | `.trae/指令手册.md` | TST-01/02/03 指令定义 |

---

*文档版本: v1.0.0 | 创建日期: 2026-05-21 | 作者: 测试工程师*