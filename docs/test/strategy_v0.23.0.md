# Nanobot Runner v0.23.0 测试策略文档

> **文档版本**: v1.0
> **测试版本**: v0.23.0
> **模块**: 决策追踪（Decision Tracking）
> **制定日期**: 2026-05-20
> **测试周期**: 2026-05-20 ~ 2026-05-27
> **测试环境**: Windows 11 / Python 3.11+ / uv / pytest

---

## 1. 测试范围

### 1.1 被测模块清单

| 模块路径 | 组件 | 功能描述 | 测试类型 |
|---------|------|---------|---------|
| `src/core/evolution/models.py` | DecisionLog, OutcomeRecord, PredictionAccuracyStats | 核心数据模型（frozen dataclass） | 单元测试 |
| `src/core/evolution/config.py` | EvolutionConfig | 配置Schema与验证 | 单元测试 |
| `src/core/evolution/decision_logger.py` | DecisionLogger | 决策日志记录、状态更新、历史查询 | 单元测试 |
| `src/core/evolution/outcome_collector.py` | OutcomeCollector, PlanExecutionDataAdapter, calculate_fidelity, calculate_prediction_error | 结果回填、忠实度/误差计算 | 单元测试 |
| `src/core/evolution/evolution_store.py` | EvolutionStore | Parquet按月分片存储、LazyFrame查询 | 单元测试 |
| `src/core/evolution/evolution_engine.py` | EvolutionEngine | 薄编排层、状态统计 | 单元测试 |
| `src/core/evolution/decision_log_hook.py` | DecisionLogHook | Agent Hook（继承AgentHook） | 单元测试 |
| `src/core/base/context.py` | AppContext.evolution_engine | 扩展属性懒加载 | 单元测试 |
| `src/core/plan/ask_user_confirm.py` | ConfirmScenario.DECISION_FEEDBACK | AskUserConfirmManager扩展 | 单元测试 |
| `src/core/transparency/hook_integration.py` | create_composite_hook | 可选注册DecisionLogHook | 集成测试 |
| `src/cli/commands/evolution.py` | evolution CLI命令组 | history/feedback/accuracy/fidelity/status | 单元测试 |
| `src/cli/handlers/evolution_handler.py` | EvolutionHandler | CLI业务逻辑调用层 | 单元测试 |
| `src/agents/tools_evolution.py` | 4个Agent工具类 | record_feedback/check_plan_execution/check_prediction_accuracy/get_decision_history | 单元测试 |

### 1.2 跨模块集成测试范围

| 集成场景 | 涉及模块 | 验证目标 |
|---------|---------|---------|
| Hook到存储落盘 | DecisionLogHook -> EvolutionEngine -> EvolutionStore | 端到端决策日志持久化 |
| Hook独立性 | DecisionLogHook + ObservabilityHook | 双Hook并行无状态竞争 |
| 计划执行回填 | OutcomeCollector + PlanExecutionDataAdapter + PlanManager | fidelity计算链路 |
| 决策-结果关联 | DecisionLog + OutcomeRecord via decision_id | 关联正确性 |
| AppContext扩展 | AppContext -> EvolutionEngine -> Store | 懒加载与共享实例 |

---

## 2. 测试类型与优先级

### 2.1 优先级定义

| 优先级 | 定义 | 覆盖标准 |
|--------|------|---------|
| **P0** | 核心业务流程，阻断发布 | 100%覆盖，必须全部通过 |
| **P1** | 重要功能，影响主流程 | 100%覆盖，必须全部通过 |
| **P2** | 边缘场景、体验优化 | 80%覆盖，允许少量跳过 |

### 2.2 测试类型矩阵

| 测试类型 | 优先级 | 覆盖模块 | 用例数 | 目标 |
|---------|--------|---------|--------|------|
| 单元测试 | P0 | `src/core/evolution/`全部8个文件 + CLI + Agent工具 | 11个测试文件 | 核心逻辑100%覆盖 |
| 集成测试 | P0 | Hook+Store+Engine端到端 | 1个测试文件 | 5大场景100%覆盖 |
| 性能测试 | P1 | Hook延迟、存储写入、查询性能 | 1个测试文件 | 阈值达标 |
| E2E测试 | P1 | CLI命令完整执行 | 1个测试文件 | 5个命令全验证 |

---

## 3. 准入准出门禁规则（量化）

### 3.1 测试准入规则（开发交付→测试接收）

| 门禁ID | 规则描述 | 量化标准 | 检查方式 |
|--------|---------|---------|---------|
| ADM-01 | 单元测试通过率 | =100% | `uv run pytest tests/unit/core/evolution/ -q` |
| ADM-02 | 代码静态检查通过 | ruff零报错、mypy无类型错误 | `uv run ruff check src/core/evolution/` |
| ADM-03 | 核心模型frozen约束 | DecisionLog/OutcomeRecord不可变 | 单元测试验证 |
| ADM-04 | Parquet Schema一致性 | 存储字段与模型定义一致 | 集成测试验证 |

### 3.2 测试准出规则（测试完成→发布准入）

| 门禁ID | 规则描述 | 量化标准 | 检查方式 |
|--------|---------|---------|---------|
| EXG-01 | **P0用例通过率** | **=100%** | pytest报告 |
| EXG-02 | **P1用例通过率** | **>=95%** | pytest报告 |
| EXG-03 | **核心模块覆盖率** | `core/evolution/` **>=80%** | pytest-cov |
| EXG-04 | **Agent工具覆盖率** | `agents/` **>=70%** | pytest-cov |
| EXG-05 | **CLI覆盖率** | `cli/` **>=60%** | pytest-cov |
| EXG-06 | **无致命/严重bug** | 致命=0, 严重=0 | Bug清单 |
| EXG-07 | **一般bug修复率** | >=90% | Bug清单 |
| EXG-08 | Hook性能延迟 | finalize_content <100ms | 性能测试 |
| EXG-09 | 同步写入延迟 | save_decision <50ms | 性能测试 |
| EXG-10 | 决策记录完整性 | 每次Agent对话100%记录 | 集成测试 |
| EXG-11 | 中文数据持久化 | Parquet读写中文无乱码 | 集成测试 |

### 3.3 门禁规则汇总

- **准入规则数**: 4条
- **准出规则数**: 11条
- **总计门禁规则数**: **15条**

---

## 4. 覆盖率要求

### 4.1 分模块覆盖率目标

| 模块 | 目标覆盖率 | 当前状态 | 差距 |
|------|-----------|---------|------|
| `src/core/evolution/` | >=80% | 待测量 | - |
| `src/agents/tools_evolution.py` | >=70% | 待测量 | - |
| `src/cli/commands/evolution.py` | >=60% | 待测量 | - |
| `src/cli/handlers/evolution_handler.py` | >=60% | 待测量 | - |

### 4.2 关键函数强制覆盖清单

| 函数/方法 | 所属文件 | 覆盖等级 |
|-----------|---------|---------|
| `DecisionLog.to_dict/from_dict` | models.py | 强制 |
| `OutcomeRecord.to_dict/from_dict` | models.py | 强制 |
| `EvolutionConfig.__post_init__` | config.py | 强制 |
| `DecisionLogger.log_decision` | decision_logger.py | 强制 |
| `DecisionLogger.update_execution_status` | decision_logger.py | 强制 |
| `calculate_fidelity` | outcome_collector.py | 强制 |
| `calculate_prediction_error` | outcome_collector.py | 强制 |
| `OutcomeCollector.check_plan_execution` | outcome_collector.py | 强制 |
| `OutcomeCollector.check_prediction_accuracy` | outcome_collector.py | 强制 |
| `EvolutionStore.save_decision/query_decisions` | evolution_store.py | 强制 |
| `EvolutionStore.get_decision_outcome_pairs` | evolution_store.py | 强制 |
| `EvolutionEngine.get_evolution_status` | evolution_engine.py | 强制 |
| `DecisionLogHook.finalize_content` | decision_log_hook.py | 强制 |
| `DecisionLogHook._infer_decision_type` | decision_log_hook.py | 强制 |
| `create_composite_hook` (可选参数分支) | hook_integration.py | 强制 |

---

## 5. 测试用例清单

### 5.1 核心场景（P0）

#### 5.1.1 数据模型层

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|---------|--------|
| EV-M-001 | DecisionLog创建与frozen约束 | 无 | 创建DecisionLog实例，尝试修改字段 | 抛出AttributeError | P0 |
| EV-M-002 | DecisionLog序列化与反序列化 | 有完整字段的DecisionLog | 调用to_dict()后from_dict()还原 | 字段值完全一致 | P0 |
| EV-M-003 | OutcomeRecord prediction_direction字段 | 创建OutcomeRecord | 验证字段名为prediction_direction | 非error_direction | P0 |
| EV-M-004 | execution_status五种状态支持 | 无 | 分别创建pending/executed/skipped/modified/failed状态 | 全部成功创建 | P0 |

#### 5.1.2 存储层

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|---------|--------|
| EV-S-001 | Parquet按月分片写入 | 临时目录 | 写入5月和6月决策 | 分别生成对应目录和文件 | P0 |
| EV-S-002 | 跨月查询 | 有多月数据 | 查询跨两个月的日期范围 | 返回两个月的数据 | P0 |
| EV-S-003 | 中文文本持久化 | 无 | 保存含中文的recommendation_text | 读取后中文无乱码 | P0 |
| EV-S-004 | 决策-结果配对查询 | 有关联的决策和结果 | 调用get_decision_outcome_pairs | 返回正确配对列表 | P0 |
| EV-S-005 | 原子更新决策状态 | 已有决策记录 | 调用update_decision修改status | 文件内容更新，其他字段不变 | P0 |

#### 5.1.3 结果回填

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|---------|--------|
| EV-O-001 | 完美执行fidelity=1.0 | 计划=实际 | calculate_fidelity | 返回1.0 | P0 |
| EV-O-002 | 大偏差fidelity=0.0 | 实际=0 | calculate_fidelity | 返回0.0 | P0 |
| EV-O-003 | 预测误差5%阈值判定 | predicted=1.05*actual | calculate_prediction_error | direction=accurate | P0 |
| EV-O-004 | 预测误差方向判定 | predicted>1.05*actual | calculate_prediction_error | direction=overestimate | P0 |
| EV-O-005 | check_plan_execution完整链路 | 有plan_adapter | 调用check_plan_execution | 返回含fidelity的OutcomeRecord | P0 |
| EV-O-006 | check_prediction_accuracy完整链路 | 有prediction_snapshot | 调用check_prediction_accuracy | 返回含error/direction的OutcomeRecord + stats | P0 |

#### 5.1.4 Hook层

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|---------|--------|
| EV-H-001 | Hook继承AgentHook | 无 | 检查DecisionLogHook继承链 | 直接继承AgentHook | P0 |
| EV-H-002 | finalize_content创建决策日志 | Hook已初始化 | 调用finalize_content | 决策已持久化，content原样返回 | P0 |
| EV-H-003 | 决策类型推断优先级 | 无 | 传入含多类型关键词的content | 按优先级返回最高类型 | P0 |
| EV-H-004 | 防重复记录机制 | 已调用finalize_content | 再次调用finalize_content | 只产生1条决策记录 | P0 |
| EV-H-005 | TwinEngine注入状态获取 | 注入mock TwinEngine | 调用finalize_content | runner_state含实际值 | P0 |
| EV-H-006 | TwinEngine失败回退 | TwinEngine抛异常 | 调用finalize_content | runner_state字段为None，不抛异常 | P0 |

#### 5.1.5 集成场景

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|---------|--------|
| EV-I-001 | Hook到存储端到端 | 完整环境 | before_iteration->before_execute_tools->finalize_content | JSONL/Parquet有记录 | P0 |
| EV-I-002 | 双Hook独立触发 | ObservabilityManager+DecisionLogHook | 同时触发两个Hook | 各自输出独立完整 | P0 |
| EV-I-003 | 决策-结果关联 | 已记录决策 | record_feedback->query_outcomes | decision_id一致关联 | P0 |
| EV-I-004 | 同一决策多条结果 | 已记录决策 | feedback+check_plan+check_accuracy | 3条OutcomeRecord关联同一decision_id | P0 |
| EV-I-005 | AppContext懒加载 | 无 | 首次访问evolution_engine | 延迟创建，缓存复用 | P0 |

### 5.2 边界场景（P1）

| 用例ID | 用例名称 | 操作步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|--------|
| EV-B-001 | 空存储查询 | query_decisions空目录 | 返回空列表，不抛异常 | P1 |
| EV-B-002 | 更新不存在的决策 | update_decision随机ID | 返回False | P1 |
| EV-B-003 | 无plan_adapter计算fidelity | plan_adapter=None | fidelity=None | P1 |
| EV-B-004 | 无prediction_snapshot计算误差 | snapshot=None | error=None, direction=None | P1 |
| EV-B-005 | 评分为1和5的边界 | score=1, score=5 | 均成功记录 | P1 |
| EV-B-006 | 长文本截断 | content>500字符 | recommendation_text<=500 | P1 |
| EV-B-007 | 零计划值fidelity | planned_volume=0 | fidelity=1.0 | P1 |
| EV-B-008 | 实际VDOT为0计算误差 | actual=0, predicted>0 | error=100%, direction=overestimate | P1 |
| EV-B-009 | 决策类型无匹配 | content无关键词 | 返回GENERAL | P1 |
| EV-B-010 | 空tool_call_chain | tool_calls为空 | tool_call_chain为空列表 | P1 |

### 5.3 异常场景（P1）

| 用例ID | 用例名称 | 操作步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|--------|
| EV-E-001 | 配置验证失败 | feedback_prompt_frequency=0 | 抛出ValueError | P1 |
| EV-E-002 | 对不存在决策记录反馈 | record_feedback随机ID | 抛出ValueError("决策不存在") | P1 |
| EV-E-003 | 对不存在决策检查计划 | check_plan_execution随机ID | 抛出ValueError("决策不存在") | P1 |
| EV-E-004 | 对不存在决策检查精度 | check_prediction_accuracy随机ID | 抛出ValueError("决策不存在") | P1 |
| EV-E-005 | Hook写入失败不阻断 | log_decision抛异常 | finalize_content仍返回content | P1 |
| EV-E-006 | CLI无效评分 | --score=6 | exit_code=1 | P1 |
| EV-E-007 | CLI评分为0 | --score=0 | exit_code=1 | P1 |
| EV-E-008 | 无效决策类型过滤 | get_history(type="invalid") | 抛出ValueError | P1 |

### 5.4 CLI与Agent工具场景（P1）

| 用例ID | 用例名称 | 操作步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|--------|
| EV-C-001 | history命令展示表格 | evolution history | Rich表格输出，含决策ID/时间/类型/状态 | P1 |
| EV-C-002 | history空记录提示 | evolution history（无数据） | 输出"暂无决策历史记录" | P1 |
| EV-C-003 | feedback命令记录 | evolution feedback dec_001 --score 4 | 输出反馈已记录面板 | P1 |
| EV-C-004 | accuracy命令面板 | evolution accuracy | 输出精度统计面板 | P1 |
| EV-C-005 | fidelity命令无数据 | evolution fidelity（无数据） | 输出"暂无执行忠实度数据" | P1 |
| EV-C-006 | status命令状态分布 | evolution status | 输出状态分布和类型分布 | P1 |
| EV-A-001 | RecordFeedbackTool参数校验 | score<1或score>5 | 工具参数schema拦截 | P1 |
| EV-A-002 | GetDecisionHistoryTool日期过滤 | start_date/end_date | 正确传递参数 | P1 |

### 5.5 性能场景（P1）

| 用例ID | 用例名称 | 阈值 | 优先级 |
|--------|---------|------|--------|
| EV-P-001 | before_iteration平均延迟 | <50ms | P1 |
| EV-P-002 | before_execute_tools平均延迟 | <10ms | P1 |
| EV-P-003 | finalize_content平均延迟 | <100ms | P1 |
| EV-P-004 | save_decision同步写入延迟 | <50ms | P1 |
| EV-P-005 | 1年范围查询耗时 | <2秒 | P1 |
| EV-P-006 | Hook开销对比（有/无Hook） | 差异<100ms | P1 |

---

## 6. 风险识别与应对

### 6.1 高风险项

| 风险ID | 风险描述 | 影响 | 概率 | 应对措施 | 负责人 |
|--------|---------|------|------|---------|--------|
| R-01 | **决策日志数据膨胀** | 长期运行后Parquet文件过大，查询性能下降 | 中 | 按月分片已缓解；测试验证365条数据查询<2s | 测试工程师 |
| R-02 | **Hook增加主流程延迟** | finalize_content超过100ms影响Agent响应 | 中 | 性能测试监控；runner_state摘要O(1)提取；同步写入<50ms | 测试工程师 |
| R-03 | **用户反馈稀疏** | 缺乏足够反馈驱动v0.24进化 | 高 | 测试验证AskUserConfirmManager集成；反馈收集率>30% | 测试工程师 |
| R-04 | **Parquet Schema演进** | v0.24新增字段导致旧数据不兼容 | 低 | 测试验证Schema字段全部使用String存储复杂类型，预留扩展空间 | 测试工程师 |

### 6.2 中风险项

| 风险ID | 风险描述 | 影响 | 概率 | 应对措施 |
|--------|---------|------|------|---------|
| R-05 | 结果回填阻塞主流程 | check_plan_execution同步执行耗时 | 中 | 测试验证当前为同步实现，v0.24评估异步化 |
| R-06 | PlanManager缺少批量接口 | PlanExecutionDataAdapter需逐条封装 | 中 | 测试验证Adapter封装正确性；Mock PlanManager测试 |
| R-07 | 循环依赖（transparency<->evolution） | create_composite_hook可选参数规避 | 低 | 测试验证不传evolution_engine时不注册Hook |
| R-08 | 异步写入失败导致日志丢失 | 默认同步已规避；配置开启异步时风险 | 低 | 测试验证默认async_write_enabled=False |

### 6.3 风险应对策略

1. **性能基线建立**: 在CI中集成性能测试，每次提交对比Hook延迟基线
2. **数据量压测**: 使用365条/年数据量验证查询性能，确保5年内数据量可接受
3. **降级测试**: 验证TwinEngine失败、PlanManager不可用时的graceful降级
4. **Schema兼容性预留**: 验证Parquet使用JSON String存储复杂字段，新增字段不影响旧数据读取

---

## 7. 测试执行计划

### 7.1 轮次安排

| 轮次 | 时间 | 重点 | 目标 |
|------|------|------|------|
| 第一轮 | 2026-05-20 ~ 2026-05-22 | 单元测试全量执行 + 覆盖率测量 | 发现基础缺陷，覆盖率达标 |
| 第二轮 | 2026-05-23 ~ 2026-05-24 | 集成测试 + 性能测试 | 验证端到端链路，性能阈值 |
| 第三轮 | 2026-05-25 ~ 2026-05-26 | 回归测试 + bug修复验证 | 致命/严重bug清零 |
| 第四轮 | 2026-05-27 | 最终验收 + 准出门禁检查 | 发布决策 |

### 7.2 测试命令

```bash
# 单元测试（evolution模块）
uv run pytest tests/unit/core/evolution/ -v --cov=src/core/evolution --cov-report=term-missing

# 集成测试
uv run pytest tests/integration/test_evolution_integration.py -v

# 性能测试
uv run pytest tests/performance/test_evolution_performance.py -v -s

# CLI测试
uv run pytest tests/unit/cli/test_evolution_cli.py -v

# 全量测试
uv run pytest tests/ -k evolution --cov=src/core/evolution --cov=src/cli/commands/evolution --cov=src/agents/tools_evolution --cov-report=term-missing
```

---

## 8. 测试交付物

| 交付物 | 路径 | 说明 |
|--------|------|------|
| 测试策略文档 | `docs/test/strategy_v0.23.0.md` | 本文档 |
| 单元测试代码 | `tests/unit/core/evolution/` | 11个测试文件 |
| 集成测试代码 | `tests/integration/test_evolution_integration.py` | 端到端场景 |
| 性能测试代码 | `tests/performance/test_evolution_performance.py` | 性能阈值验证 |
| CLI测试代码 | `tests/unit/cli/test_evolution_cli.py` | CLI命令测试 |
| 轮次测试报告 | `docs/test/轮次报告_v0.23.0_第N轮.md` | 每轮输出 |
| Bug清单 | `docs/test/bug_list_v0.23.0.md` | 全量bug跟踪 |
| 测试报告 | `docs/test/测试报告_v0.23.0.md` | 最终质量评估 |

---

## 9. 关键数据统计

| 指标 | 数值 |
|------|------|
| **测试用例总数** | **68条**（P0: 28条 / P1: 40条） |
| **单元测试文件数** | **11个** |
| **集成测试场景数** | **5个** |
| **性能测试阈值项** | **6项** |
| **CLI命令覆盖数** | **5个** |
| **Agent工具覆盖数** | **4个** |
| **覆盖率要求: core** | **>=80%** |
| **覆盖率要求: agents** | **>=70%** |
| **覆盖率要求: cli** | **>=60%** |
| **准入规则数** | **4条** |
| **准出规则数** | **11条** |
| **总计门禁规则数** | **15条** |
| **高风险项** | **4项** |
| **中风险项** | **4项** |

---

## 10. 测试结论模板（最终轮次填写）

```
测试版本: v0.23.0
测试轮次: 第N轮
测试周期: YYYY-MM-DD ~ YYYY-MM-DD

## 用例执行情况

| 类型 | 总数 | 通过 | 失败 | 跳过 | 通过率 |
|------|------|------|------|------|--------|
| P0   | 28   |      |      |      |        |
| P1   | 40   |      |      |      |        |
| 合计 | 68   |      |      |      |        |

## Bug统计

| 严重等级 | 新增 | 已修复 | 待修复 | 驳回 |
|---------|------|--------|--------|------|
| 致命    |      |        |        |      |
| 严重    |      |        |        |      |
| 一般    |      |        |        |      |
| 优化    |      |        |        |      |

## 覆盖率结果

| 模块 | 目标 | 实际 | 是否达标 |
|------|------|------|---------|
| core/evolution | >=80% |      |         |
| agents         | >=70% |      |         |
| cli            | >=60% |      |         |

## 性能结果

| 指标 | 阈值 | 实际 | 是否达标 |
|------|------|------|---------|
| finalize_content | <100ms |      |         |
| save_decision    | <50ms  |      |         |
| 1年查询          | <2s    |      |         |

## 测试结论
- [ ] 通过 / 不通过
- 原因说明:

## 剩余风险
1. 

## 上线建议
- 建议发布 / 建议修复后重新测试
```
