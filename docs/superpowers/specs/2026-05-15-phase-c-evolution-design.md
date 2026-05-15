# Phase C 自适应进化引擎 — 技术预研报告

> **文档版本**: v1.0
> **预研日期**: 2026-05-15
> **覆盖范围**: v0.23-v0.25 全链路
> **对齐文档**: 产品规划方案 v9.1 / 架构设计说明书 v8.0.0
> **当前基线**: v0.21.0

---

## 1. 执行摘要

### 1.1 预研结论

**推荐方案：B（独立进化引擎架构）** — 新增 `evolution` 核心子模块，与 `prediction`/`twin` 同级，统一编排追踪→校准→进化链路。

| 决策项 | 结论 |
|--------|------|
| 架构方案 | 独立进化引擎（方案B） |
| Hook接入方式 | 扩展现有 ObservabilityHook |
| 模型进化策略 | 偏差修正层（bias + scale 线性修正） |
| 提示优化方式 | 参数化提示调优（4维参数空间） |

### 1.2 核心选型理由

1. **只增加一个模块**：与项目"简单直白"原则一致，避免逻辑分散
2. **对现有模块零侵入**：evolution 只读取数据，唯一"写入"通过 Hook 扩展点
3. **版本间数据流自然衔接**：共享 `EvolutionStore` + `EvolutionEngine` 薄编排层
4. **v0.25 进化触发器拥有全局视角**：集中编排比分散感知更可靠

---

## 2. 需求分析

### 2.1 Phase C 功能需求分解

| 版本 | 主题 | 核心功能 | 依赖 |
|------|------|----------|------|
| v0.23 | 决策-结果追踪 | DecisionLog + 结果回填 + 预测校准 | transparency(AIDecision/Hook) + twin(StateVector) |
| v0.24 | 个性化学习 | 偏差修正校准 + 训练响应性分析 | prediction(PredictionRecord/BanisterIR) + v0.23数据 |
| v0.25 | 自适应进化 | 参数化提示调优 + 进化触发器 | personality(PersonalizationEngine) + v0.24数据 |

### 2.2 性能指标基线与目标

| 指标 | v0.22基线 | v0.23目标 | v0.24目标 | v0.25目标 |
|------|-----------|-----------|-----------|-----------|
| VDOT预测MAE | 基线测量 | 可测量 | ↓≥5% | ↓≥10% |
| 全马预测误差 | 基线测量 | 可测量 | ↓≥5% | ↓≥10% |
| 用户满意度 | 首次收集 | ≥3.5/5 | ≥3.8/5 | ≥4.0/5 |
| 推荐采纳率 | 首次收集 | 可测量 | ≥50% | ≥60% |
| 伤病预警召回率 | ≥75% | 维持≥75% | ≥78% | ≥80% |

### 2.3 业务场景

1. **场景1（v0.23）**：用户询问"下周训练建议"，Agent调用工具生成推荐 → DecisionLogHook自动记录决策上下文（跑者状态、工具调用、预测快照） → 用户执行训练后，OutcomeCollector回填实际结果
2. **场景2（v0.24）**：系统发现VDOT预测持续偏高0.5 → CalibrationEngine自动校准bias=-0.5 → 后续预测更准确
3. **场景3（v0.25）**：用户连续2次忽略推荐 → PromptTuner降低aggressiveness → 推荐变得更保守温和 → 采纳率回升

---

## 3. 技术方向对比

### 3.1 三个候选方案

#### 方案A：渐进式扩展架构

在现有 transparency/prediction/personality 模块上逐层叠加进化功能。

```
transparency  +DecisionLog Hook扩展
prediction    +Calibration Layer扩展
personality   +PromptTuner 参数扩展
       ↓           ↓            ↓
    共享存储层 (Parquet 按月分片)
```

**优势**：侵入性最低，每版本独立交付，复用现有基础设施
**风险**：进化逻辑分散3个模块，v0.25跨模块协调困难，长期维护产生耦合

#### 方案B：独立进化引擎架构（推荐）

新建 `evolution` 核心子模块，统一编排追踪→学习→进化链路。

```
transparency ──┐
prediction   ──┼──► evolution (新核心模块)
personality  ──┘     ├─ DecisionTracker (v0.23)
                      ├─ CalibrationEngine (v0.24)
                      ├─ EvolutionController (v0.25)
                      └─ EvolutionStore (统一存储)
```

**优势**：进化逻辑集中管理，统一存储编排，v0.25全局视角，对现有模块零侵入
**风险**：新增核心模块开发量中等偏大，需提前设计好模块间接口

#### 方案C：事件驱动管道架构

引入 EventBus 事件总线，各管道订阅事件独立处理。

```
Agent决策事件 ──┐
训练完成事件 ──┼──► EventBus ──► DecisionLogger / CalibrationPipeline / EvolutionTrigger
用户反馈事件 ──┘
```

**优势**：完全解耦，扩展性最强，天然支持异步
**风险**：引入EventBus增加复杂度，调试困难，与项目"简单直白"原则冲突，单用户场景过度设计

### 3.2 综合对比矩阵

| 评估维度 | A 渐进式 | B 独立引擎 | C 事件驱动 |
|----------|----------|------------|------------|
| 开发复杂度 | ⭐ 低 | ⭐⭐ 中 | ⭐⭐⭐ 高 |
| 侵入性 | ⭐⭐ 中 | ⭐ 低 | ⭐ 低 |
| 跨版本协调 | ⭐ 弱 | ⭐⭐⭐ 强 | ⭐⭐⭐ 强 |
| 与项目原则契合 | ⭐⭐⭐ 高 | ⭐⭐ 高 | ⭐ 低 |
| 可测试性 | ⭐⭐ 高 | ⭐⭐⭐ 高 | ⭐⭐ 中 |
| 长期可维护性 | ⭐⭐ 中 | ⭐⭐⭐ 高 | ⭐⭐⭐ 高 |

### 3.3 推荐理由

Phase C 三个版本本质是一条"进化链路"的三个环节——追踪→学习→进化。方案B通过独立 `evolution` 模块集中编排，既保持架构一致性（与 prediction/twin 同级），又为 v0.25 全局进化触发器提供天然编排中心。方案A分散逻辑导致协调成本高，方案C在单用户CLI场景过度设计。

---

## 4. 详细设计

### 4.1 模块结构

```
src/core/evolution/
├── __init__.py
├── models.py                    # 核心数据模型
├── decision_tracker.py          # v0.23 决策追踪器
├── outcome_collector.py         # v0.23 结果回填收集器
├── calibration_engine.py        # v0.24 偏差修正校准引擎
├── response_analyzer.py         # v0.24 训练响应性分析器
├── evolution_controller.py      # v0.25 自适应进化控制器
├── prompt_tuner.py              # v0.25 参数化提示调优器
├── evolution_store.py           # 统一存储编排
├── config.py                    # 进化配置
└── exceptions.py                # 进化模块异常定义
```

### 4.2 核心数据模型

#### DecisionLog

| 字段 | 类型 | 说明 | 来源 |
|------|------|------|------|
| decision_id | str | 唯一标识（UUID） | 自动生成 |
| timestamp | datetime | 决策发生时间 | Hook |
| runner_state | dict | 决策时 RunnerStateVector 快照 | twin引擎 |
| decision_type | str | plan_generation/prediction_query/risk_assessment | Hook分类 |
| tool_call_chain | list[dict] | 本次决策调用的所有工具及参数 | Hook |
| prediction_snapshot | dict \| None | 决策时的预测结果快照 | prediction引擎 |
| execution_status | str | pending/executed/skipped/modified | 结果回填 |
| recommendation_accepted | bool \| None | 用户是否采纳推荐 | 用户反馈 |
| session_key | str | 会话标识 | Hook |

#### OutcomeRecord

| 字段 | 类型 | 说明 |
|------|------|------|
| decision_id | str | 关联决策ID（FK） |
| outcome_timestamp | datetime | 结果记录时间 |
| actual_vdot | float \| None | 实际VDOT |
| actual_injury | bool | 是否发生伤病 |
| execution_fidelity | float \| None | 执行忠实度（0-1） |
| user_feedback_score | int \| None | 用户评分（1-5） |
| user_feedback_text | str | 用户文本反馈 |
| prediction_error | float \| None | 预测误差百分比 |
| session_id | str | 关联训练Session |

#### CalibrationProfile

| 字段 | 类型 | 说明 |
|------|------|------|
| profile_id | str | 唯一标识 |
| model_type | str | vdot/injury/race |
| calibration_type | str | bias_correction/scale_correction |
| bias_correction | float | 偏差修正值 |
| scale_correction | float | 缩放修正值 |
| last_calibrated_at | datetime | 最后校准时间 |
| sample_count | int | 校准样本数 |
| confidence | float | 校准置信度 |

#### PromptTuningParams

| 字段 | 类型 | 说明 |
|------|------|------|
| tone_intensity | float | 语气强度（0.0严厉-1.0温和） |
| detail_level_score | float | 详细程度（0.0简洁-1.0详细） |
| recommendation_aggressiveness | float | 推荐激进程度（0.0保守-1.0激进） |
| data_driven_weight | float | 数据驱动权重（0.0直觉-1.0数据） |
| adoption_rate | float | 最近30天采纳率 |
| last_adjusted | datetime | 最后调整时间 |

### 4.3 模块依赖关系

evolution 模块只读取现有模块数据，不修改它们内部逻辑：

```
                    ┌─────────────┐
                    │  evolution  │  ← 新增模块
                    └──┬──┬──┬──┬─┘
                       │  │  │  │
          ┌────────────┘  │  │  └──────────────┐
          ▼               ▼  ▼                 ▼
   ┌─────────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
   │ transparency│ │  twin    │ │prediction│ │personality│
   │ (Hook接入)  │ │(状态快照)│ │(校准目标)│ │(调优目标)│
   └─────────────┘ └──────────┘ └──────────┘ └──────────┘
```

唯一的"写入"是通过 Hook 扩展点（DecisionLogHook 继承 ObservabilityHook），这是对现有模块的扩展而非修改。

### 4.4 v0.23 决策追踪系统

#### 数据流

```
Agent交互开始
    │
    ▼
DecisionLogHook.before_iteration()
    ├─ 获取 RunnerState ← twin.get_state_vector()
    ├─ 创建 DecisionLog
    └─ 记录工具调用链
    │
    ▼
Agent 执行决策（工具调用/LLM推理）
    │
    ▼
DecisionLogHook.finalize_content()
    ├─ 记录预测快照 ← prediction_engine 查询
    ├─ 记录推荐文本
    └─ 持久化 DecisionLog → decisions/2026-05.parquet
    │
    ├── 训练完成后 ──► OutcomeCollector.check_plan_execution()
    ├── 用户反馈时 ──► OutcomeCollector.record_feedback()
    └── 定期校准   ──► OutcomeCollector.check_prediction_accuracy()
                        │
                        ▼
                   持久化 OutcomeRecord → outcomes/2026-05.parquet
```

#### DecisionLogHook 接口

```python
class DecisionLogHook(ObservabilityHook):
    """决策日志钩子 — 扩展 ObservabilityHook"""

    def __init__(
        self,
        manager: ObservabilityManager,
        engine: TransparencyEngine | None,
        decision_tracker: DecisionTracker,
        twin_engine: DigitalTwinEngine,
        prediction_engine: PredictionEngine,
    ): ...

    async def before_iteration(self, context: AgentHookContext) -> None:
        # 1. 调用 super() 保留原有追踪逻辑
        # 2. twin_engine.get_state_vector() → runner_state
        # 3. 创建 DecisionLog(runner_state=runner_state, ...)

    async def before_execute_tools(self, context: AgentHookContext) -> None:
        # 1. 调用 super() 保留原有追踪逻辑
        # 2. 提取 tool_calls → tool_call_chain

    async def finalize_content(self, context, content: str) -> str:
        # 1. 调用 super() 保留原有逻辑
        # 2. 解析 content 识别决策类型
        # 3. prediction_engine 查询当前预测 → prediction_snapshot
        # 4. decision_tracker.log_decision(decision_log) → 持久化
```

#### DecisionTracker 接口

```python
class DecisionTracker:
    def log_decision(self, decision: DecisionLog) -> str
    def query_decisions(self, start_date, end_date, decision_type, execution_status, limit) -> list[DecisionLog]
    def get_decision(self, decision_id: str) -> DecisionLog | None
    def update_execution_status(self, decision_id: str, status: str) -> bool
    def get_pending_decisions(self, days: int = 7) -> list[DecisionLog]
```

#### OutcomeCollector 接口

```python
class OutcomeCollector:
    def check_plan_execution(self, decision_id: str) -> OutcomeRecord
        # 忠实度算法：
        # fidelity = 1 - weighted_avg(体积偏差, 强度偏差, 时间偏差)

    def check_prediction_accuracy(self, decision_id: str) -> OutcomeRecord
        # 误差算法：
        # VDOT误差 = |预测VDOT - 实际VDOT| / 实际VDOT

    def record_feedback(self, decision_id, score, text, accepted) -> OutcomeRecord
    def generate_feedback_prompt(self, days: int = 7) -> list[dict]
    def get_outcomes(self, start_date, end_date, limit) -> list[OutcomeRecord]
```

#### v0.23 Agent 工具

| 工具名 | 功能 | 输入 | 输出 |
|--------|------|------|------|
| record_feedback | 记录用户反馈 | decision_id, score(1-5), text?, accepted? | OutcomeRecord |
| check_plan_execution | 检查计划执行忠实度 | decision_id | OutcomeRecord |
| check_prediction_accuracy | 检查预测准确度 | decision_id | OutcomeRecord |
| get_decision_history | 查询决策历史 | start_date?, end_date?, type?, limit? | list[DecisionLog] |

#### v0.23 CLI 命令

```bash
uv run nanobotrun evolution history [--start YYYY-MM-DD] [--end YYYY-MM-DD] [--type TYPE]
uv run nanobotrun evolution feedback <decision_id> --score 4 [--text "很好"] [--accepted]
uv run nanobotrun evolution accuracy [--days 30]
uv run nanobotrun evolution fidelity [--days 30]
uv run nanobotrun evolution status
```

### 4.5 v0.24 个性化学习

#### CalibrationEngine 工作原理

```
预测请求 → PredictionEngine.predict_vdot()
    │
    ▼
原始预测结果 (predicted_vdot = 45.2)
    │
    ▼
CalibrationEngine
    ├─ 查找 CalibrationProfile (model_type=vdot)
    ├─ 应用偏差修正: corrected = raw × scale + bias
    │   scale = 1.03, bias = -0.4
    └─ 结果: 45.2 × 1.03 - 0.4 = 45.8
    │
    ▼
校准后预测结果 (corrected_vdot = 45.8)
```

校准参数更新流程：
1. 从 OutcomeCollector 获取历史 prediction_error
2. 计算最近N条误差统计：bias = mean(预测-实际), scale = std(实际)/std(预测)
3. 指数移动平均更新：new_bias = α×old_bias + (1-α)×batch_bias, α=0.7
4. 持久化 CalibrationProfile

#### CalibrationEngine 接口

```python
class CalibrationEngine:
    def calibrate_vdot(self, prediction: VDOTPrediction) -> VDOTPrediction
    def calibrate_injury_risk(self, prediction: InjuryRiskPrediction) -> InjuryRiskPrediction
    def calibrate_race_result(self, prediction: RacePredictionResult) -> RacePredictionResult
    def update_calibration(self, model_type: str, min_samples: int = 10) -> CalibrationProfile
    def get_calibration_profile(self, model_type: str) -> CalibrationProfile | None
    def get_all_profiles(self) -> list[CalibrationProfile]
```

#### ResponseAnalyzer 训练响应性分析

核心问题："间歇训练对我提升大，还是阈值训练对我提升大？"

分析流程：
1. 从 DecisionLog + OutcomeRecord 获取历史数据（筛选 execution_fidelity ≥ 0.7）
2. 按训练类型分组（easy/tempo/interval/long_run）
3. 计算每组的 VDOT 响应性指标
4. 结合 Banister IR 参数个人化
5. 输出训练响应性报告

```python
class ResponseAnalyzer:
    def analyze_training_response(self, months: int = 6) -> TrainingResponseReport
    def get_personal_banister_params(self) -> BanisterParams
    def get_best_training_type(self) -> str
```

### 4.6 v0.25 自适应进化引擎

#### PromptTuner 参数化调优

4维参数空间：

| 参数 | 范围 | 含义 |
|------|------|------|
| tone_intensity | 0.0-1.0 | 严厉←→温和 |
| detail_level_score | 0.0-1.0 | 简洁←→详细 |
| recommendation_aggressiveness | 0.0-1.0 | 保守←→激进 |
| data_driven_weight | 0.0-1.0 | 直觉←→数据 |

调优反馈闭环：
1. 用户反馈收集（OutcomeRecord）
2. 采纳率统计（最近30天）
3. 参数调整（梯度调整，幅度0.05-0.1）
4. 参数持久化（JSON文件）
5. PromptTuner 应用参数到个性化输出

调整算法：
- 采纳率 < 0.4 → aggressiveness -= 0.1, tone_intensity += 0.05
- 采纳率 > 0.7 → aggressiveness += 0.05

```python
class PromptTuner:
    def get_params(self) -> PromptTuningParams
    def adjust_from_feedback(self, adoption_rate: float) -> PromptTuningParams
    def apply_to_suggestion(self, suggestion: PersonalizedSuggestion) -> PersonalizedSuggestion
    def reset_to_default(self) -> PromptTuningParams
```

#### EvolutionController 进化触发器

| 触发条件 | 动作 |
|----------|------|
| VDOT预测误差连续3次>5% | calibration_engine.update() |
| 伤病预警连续2次误报 | calibration_engine.update(injury) |
| 用户连续2次拒绝推荐 | prompt_tuner.adjust(adoption↓) |
| 新训练数据积累≥50条 | response_analyzer.reanalyze() |
| 月度复盘（每月1日） | generate_evolution_report() |
| 用户满意度<3.5持续2周 | prompt_tuner.adjust(tone↑) |

触发检测方式：
- 被动检测：每次 OutcomeCollector 回填时检查
- 主动检测：CLI命令 `evolution check-triggers`
- 定期检测：Cron心跳任务（已有基础设施）

```python
class EvolutionController:
    def check_triggers(self) -> list[EvolutionAction]
    def execute_action(self, action: EvolutionAction) -> bool
    def generate_evolution_report(self) -> EvolutionReport
    def get_evolution_status(self) -> EvolutionStatus
```

#### v0.24-v0.25 Agent 工具

| 版本 | 工具名 | 功能 |
|------|--------|------|
| v0.24 | analyze_training_response | 分析训练响应性 |
| v0.24 | get_calibration_status | 查看校准配置与效果 |
| v0.25 | check_evolution_triggers | 检查进化触发条件 |
| v0.25 | get_evolution_report | 获取月度进化报告 |
| v0.25 | adjust_prompt_params | 手动调整提示参数 |

#### v0.24-v0.25 CLI 命令

```bash
# v0.24 新增
uv run nanobotrun evolution calibration [--model-type TYPE]
uv run nanobotrun evolution response [--months 6]

# v0.25 新增
uv run nanobotrun evolution triggers
uv run nanobotrun evolution report [--month YYYY-MM]
uv run nanobotrun evolution tune --tone 0.7 --detail 0.5 --aggressive 0.3
```

### 4.7 存储设计

```
~/.nanobot-runner/
├── decisions/                          # v0.23 新增
│   └── 2026-05/
│       └── 2026-05_decisions.parquet   # 按月分片
├── outcomes/                           # v0.23 新增
│   └── 2026-05/
│       └── 2026-05_outcomes.parquet    # 按月分片
├── calibrations/                       # v0.24 新增
│   └── calibration_profiles.json       # 校准配置
├── tuning/                             # v0.25 新增
│   └── prompt_params.json              # 提示调优参数
├── twin/                               # v0.21 已有
├── models/                             # v0.20 已有
└── sessions/                           # 已有
```

EvolutionStore 统一接口：
- 写入：append模式（不重写整月文件）
- 查询：scan_parquet → filter → collect（LazyFrame优先）
- 归档：>12月数据压缩为yearly归档文件

### 4.8 AppContext 集成

新增 `evolution_engine` 属性，与 `prediction_engine`/`digital_twin_engine` 同模式（懒加载+扩展点）：

```python
@property
def evolution_engine(self) -> EvolutionEngine:
    """获取进化引擎（v0.23.0新增）"""
    engine = self.get_extension("evolution_engine")
    if engine is None:
        # 构建所有子组件...
        engine = EvolutionEngine(
            tracker=tracker,
            collector=collector,
            calibration=calibration,
            response_analyzer=response_analyzer,
            prompt_tuner=prompt_tuner,
            controller=controller,
        )
        self.set_extension("evolution_engine", engine)
    return engine
```

EvolutionEngine 为薄编排层（与 DigitalTwinEngine 同模式），不包含业务逻辑，仅委托给子组件。

### 4.9 三版本完整数据流总览

```
Agent交互                                                    用户训练
   │                                                           │
   ▼                                                           ▼
v0.23: 决策追踪
  DecisionLogHook → DecisionTracker → EvolutionStore
  OutcomeCollector ← 训练完成事件 ← SessionRepository
       │
       ├─ execution_fidelity ─────────────────────────┐
       ├─ prediction_error ───────────────────────┐   │
       └─ user_feedback ──────────────────────┐   │   │
                                              │   │   │
v0.24: 个性化学习                             │   │   │
  CalibrationEngine ← prediction_error ───────┘   │   │
       │ bias/scale 修正预测输出                    │   │
  ResponseAnalyzer ← execution_fidelity ───────────┘   │
       │ 个人化 Banister 参数                          │
                                                      │
v0.25: 自适应进化                                     │
  EvolutionController ← 所有触发条件检测              │
       ├─► CalibrationEngine.update()                 │
       ├─► ResponseAnalyzer.reanalyze()               │
  PromptTuner ← user_feedback ───────────────────────┘
       │ tone/detail/aggressiveness 调整
  EvolutionReport ← 月度复盘
```

---

## 5. 风险评估

| 风险 | 等级 | 影响版本 | 应对策略 |
|------|------|----------|----------|
| 决策日志数据膨胀 | 高 | v0.23 | Parquet按月分片 + >12月自动归档；runner_state仅存摘要，完整快照按需从twin重建 |
| 用户反馈稀疏 | 高 | v0.23-v0.25 | ① 轻量反馈（1-5星+可选文本）② generate_feedback_prompt()主动询问 ③ 隐式反馈自动记录 |
| 校准偏差方向错误 | 中 | v0.24 | ① 最少10条样本才触发 ② EMA(α=0.7)保证稳定 ③ 校准幅度上限±10% ④ 人工覆盖接口 |
| 进化方向偏差 | 中 | v0.25 | ① 月度进化报告供review ② 调整幅度小(0.05-0.1) ③ reset_to_default()回退 ④ 进化动作日志可追溯 |
| Hook扩展影响透明化 | 中 | v0.23 | ① 所有方法先调super()再扩展 ② twin/prediction查询失败graceful降级 ③ 不修改现有逻辑 |
| 训练响应性样本不足 | 低 | v0.24 | ① 最低样本数门槛(每组≥5) ② 不足时返回"数据不足" ③ 结合Banister参数化基线补充 |
| v0.22条件性跳过影响 | 低 | v0.23+ | DecisionLog不依赖多视角验证能力 |

---

## 6. 技术验证方案

### v0.23 验证

| 编号 | 验证项 | 方法 | 通过标准 |
|------|--------|------|----------|
| V1 | DecisionLogHook集成 | Mock AgentHookContext，验证DecisionLog各字段填充 | runner_state/tool_call_chain/prediction_snapshot非空 |
| V2 | 结果回填准确性 | 构造已知计划+实际训练数据 | fidelity误差<0.01, prediction_error误差<0.01 |
| V3 | Parquet存储读写 | 写入100条DecisionLog，按日期/类型查询 | 查询结果完整，无数据丢失 |
| V4 | 存储膨胀控制 | 写入13个月数据，触发归档 | 归档后磁盘占用减少>50% |

### v0.24 验证

| 编号 | 验证项 | 方法 | 通过标准 |
|------|--------|------|----------|
| V5 | 偏差修正有效性 | 构造已知偏差的预测数据 | 修正后MAE比修正前下降≥5% |
| V6 | 校准稳定性 | 注入异常值，验证参数变化幅度 | 单次异常值导致参数变化<5% |
| V7 | 训练响应性分析 | 构造已知响应模式的训练数据 | 识别结果与预期一致 |

### v0.25 验证

| 编号 | 验证项 | 方法 | 通过标准 |
|------|--------|------|----------|
| V8 | 提示参数调优闭环 | 模拟连续低采纳率 | aggressiveness下降，tone_intensity上升 |
| V9 | 进化触发器准确性 | 构造满足/不满足触发条件的数据 | 命中率100%，误触发率0% |
| V10 | 端到端进化闭环 | 模拟30天使用数据 | VDOT预测MAE比初始下降≥10% |

---

## 7. 技术选型汇总

| 类别 | 选型 | 版本 | 用途 |
|------|------|------|------|
| 数据存储 | Apache Parquet (via pyarrow) | 已有 | decisions/outcomes按月分片 |
| 查询引擎 | Polars LazyFrame | 0.20+ 已有 | EvolutionStore查询 |
| 配置存储 | JSON文件 | 标准库 | calibration_profiles / prompt_params |
| Hook框架 | nanobot-ai AgentHook | 已有 | DecisionLogHook扩展 |
| 数据模型 | frozen dataclass | 已有 | 所有evolution数据模型 |
| 异常体系 | NanobotRunnerError子类 | 已有 | EvolutionError |
| 依赖注入 | AppContext扩展属性 | 已有 | evolution_engine懒加载 |

无新增外部依赖，全部基于现有技术栈。

---

## 8. 附录

### 8.1 与产品规划对齐检查

| 产品规划要求 | 本设计覆盖 | 对齐状态 |
|-------------|-----------|----------|
| v0.23 决策日志（DecisionLog） | DecisionTracker + DecisionLogHook | ✅ |
| v0.23 追踪接入方式（Hook无侵入） | DecisionLogHook继承ObservabilityHook | ✅ |
| v0.23 结果回填机制 | OutcomeCollector（3个check方法） | ✅ |
| v0.23 存储设计（decisions/outcomes） | EvolutionStore + Parquet按月分片 | ✅ |
| v0.24 训练响应性分析 | ResponseAnalyzer | ✅ |
| v0.24 VDOT预测校准 | CalibrationEngine.calibrate_vdot() | ✅ |
| v0.24 伤病风险校准 | CalibrationEngine.calibrate_injury_risk() | ✅ |
| v0.24 训练响应校准（Banister IR） | ResponseAnalyzer + BanisterParams | ✅ |
| v0.25 提示策略优化（个性化语气） | PromptTuner.tone_intensity | ✅ |
| v0.25 信息密度调整 | PromptTuner.detail_level_score | ✅ |
| v0.25 推荐策略调整 | PromptTuner.recommendation_aggressiveness | ✅ |
| v0.25 进化触发器（6种条件） | EvolutionController | ✅ |
| v0.25 月度进化报告 | EvolutionController.generate_evolution_report() | ✅ |

### 8.2 术语表

| 术语 | 定义 |
|------|------|
| DecisionLog | AI决策的完整上下文记录 |
| OutcomeRecord | 决策执行后的实际结果记录 |
| CalibrationProfile | 偏差修正参数配置 |
| PromptTuningParams | 提示策略调优参数 |
| EvolutionEngine | 进化引擎薄编排层 |
| EvolutionStore | 统一存储编排 |
| 执行忠实度 | 实际训练与计划训练的吻合程度 |
| 偏差修正层 | 在预测输出上加bias+scale线性修正 |
| 参数化提示调优 | 维护提示参数表，根据反馈统计自动调整 |
