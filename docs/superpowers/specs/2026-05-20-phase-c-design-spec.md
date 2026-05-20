# Phase C 自适应进化引擎 — 设计规格书

> **文档版本**: v1.0
> **设计日期**: 2026-05-20
> **覆盖范围**: v0.23-v0.25 全链路
> **对齐文档**: 产品规划方案 v9.2 / 需求规格说明书 v8.6 / 技术预研报告 v1.0
> **当前基线**: v0.22.0

---

## 1. 设计决策记录

### 1.1 澄清过程中确认的关键决策

| 决策项 | 选项 | 结论 | 理由 |
|--------|------|------|------|
| 模块架构 | 方案A多模块 / 方案B单一模块 / 混合 | **方案B：单一 evolution/ 模块** | 进化逻辑集中管理，与 prediction/twin 同级，v0.25 全局视角 |
| 校准层归属 | v0.23 P1 / v0.24 | **v0.24 交付** | 校准需结果回填数据积累，v0.23 范围更聚焦 |
| 数据模型 | DecisionRecord单体 / DecisionLog+OutcomeRecord分离 | **分离模型** | 职责清晰，查询高效，与存储分片自然对齐 |
| 决策类型枚举 | 复用现有DecisionType / 新定义枚举 | **复用现有 DecisionType** | 与 AIDecision 一致，避免类型碎片化 |
| Hook集成 | 新建独立Hook / 修改现有Hook | **新建 DecisionLogHook** | 对现有 Hook 零侵入，所有方法先调 super() 再扩展 |
| v0.23范围 | 精简 / 增强 | **精简+复用AskUserConfirm** | 决策日志+结果回填+Agent工具+CLI，反馈收集复用现有提问能力 |
| 反馈收集 | 新建机制 / 复用AskUserConfirmManager | **复用 AskUserConfirmManager** | 扩展 ConfirmScenario 枚举，不重复造轮子 |

### 1.2 与需求规格说明书 v8.6 的偏差

| 偏差项 | v8.6 原定义 | 本设计 | 理由 |
|--------|------------|--------|------|
| 模块命名 | v0.23→tracking/, v0.24→personalization/, v0.25→evolution/ | 统一为 evolution/ | 预研报告推荐，进化逻辑集中 |
| REQ-0.23-03 归属 | v0.23 P1 | v0.24 | 校准需数据积累 |
| 数据模型 | DecisionRecord 单体 | DecisionLog + OutcomeRecord 分离 | 职责清晰 |
| Hook命名 | DecisionTrackingHook | DecisionLogHook | 与 DecisionLog 数据模型命名一致 |

---

## 2. 模块结构

```
src/core/evolution/
├── __init__.py                    # 模块导出 + create_evolution_engine() 工厂
├── models.py                      # 核心数据模型
├── decision_tracker.py            # v0.23 决策追踪器
├── outcome_collector.py           # v0.23 结果回填收集器
├── calibration_engine.py          # v0.24 偏差修正校准引擎
├── response_analyzer.py           # v0.24 训练响应性分析器
├── evolution_controller.py        # v0.25 自适应进化控制器
├── prompt_tuner.py                # v0.25 参数化提示调优器
├── evolution_store.py             # 统一存储编排（Parquet + JSON）
├── decision_log_hook.py           # v0.23 DecisionLogHook
├── config.py                      # 进化配置
└── exceptions.py                  # EvolutionError 异常体系
```

---

## 3. 核心数据模型

### 3.1 DecisionLog

决策上下文记录，由 DecisionLogHook 自动采集。

```python
@dataclass(frozen=True)
class DecisionLog:
    decision_id: str                              # UUID
    timestamp: datetime                           # 决策时间
    runner_state: dict                            # RunnerStateVector 摘要快照
    decision_type: DecisionType                   # 复用现有枚举
    tool_call_chain: list[dict]                   # 工具调用链 [{name, args, result_summary}]
    prediction_snapshot: dict | None              # 预测快照（如有预测）
    recommendation_text: str | None               # 推荐文本摘要
    execution_status: str                         # pending/executed/skipped/modified
    recommendation_accepted: bool | None          # 用户是否采纳推荐
    session_key: str                              # 会话标识
```

### 3.2 OutcomeRecord

执行结果记录，由 OutcomeCollector 回填。

```python
@dataclass(frozen=True)
class OutcomeRecord:
    outcome_id: str                               # UUID
    decision_id: str                              # FK → DecisionLog
    outcome_timestamp: datetime                   # 结果时间
    actual_vdot: float | None                     # 实际VDOT
    actual_injury: bool                           # 是否伤病
    execution_fidelity: float | None              # 执行忠实度 0-1
    user_feedback_score: int | None               # 1-5星
    user_feedback_text: str | None                # 文本反馈
    prediction_error: float | None                # 预测误差%
    session_id: str | None                        # 关联训练Session
```

### 3.3 CalibrationProfile（v0.24）

```python
@dataclass(frozen=True)
class CalibrationProfile:
    profile_id: str
    model_type: str                               # vdot/injury/race
    calibration_type: str                         # bias_correction/scale_correction
    bias_correction: float                        # 偏差修正值
    scale_correction: float                       # 缩放修正值
    last_calibrated_at: datetime
    sample_count: int                             # 校准样本数
    confidence: float                             # 校准置信度
```

### 3.4 PromptTuningParams（v0.25）

```python
@dataclass(frozen=True)
class PromptTuningParams:
    tone_intensity: float                         # 0.0严厉-1.0温和
    detail_level_score: float                     # 0.0简洁-1.0详细
    recommendation_aggressiveness: float          # 0.0保守-1.0激进
    data_driven_weight: float                     # 0.0直觉-1.0数据
    adoption_rate: float                          # 最近30天采纳率
    last_adjusted: datetime
```

---

## 4. 模块依赖关系

```
                    ┌─────────────┐
                    │  evolution  │  ← 新增模块
                    └──┬──┬──┬──┬─┘
                       │  │  │  │
          ┌────────────┘  │  │  └──────────────┐
          ▼               ▼  ▼                 ▼
   ┌─────────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
   │ transparency│ │  twin    │ │prediction│ │ask_user  │
   │ (Hook接入)  │ │(状态快照)│ │(校准目标)│ │_confirm  │
   └─────────────┘ └──────────┘ └──────────┘ │(反馈收集)│
                                              └──────────┘
```

**依赖原则**：
- evolution 只读取现有模块数据，不修改它们内部逻辑
- 唯一"写入"通过 Hook 扩展点（DecisionLogHook 继承 ObservabilityHook）
- 反馈收集复用 AskUserConfirmManager，扩展 ConfirmScenario 枚举

---

## 5. v0.23 决策-结果追踪系统

### 5.1 数据流

```
Agent交互开始
    │
    ▼
DecisionLogHook.before_iteration()
    ├─ super() 保留原有追踪逻辑
    ├─ twin_engine.get_current_snapshot() → runner_state 摘要
    └─ 创建 DecisionLog(runner_state=..., execution_status=pending)
    │
    ▼
DecisionLogHook.before_execute_tools()
    ├─ super() 保留原有追踪逻辑
    └─ 提取 tool_calls → tool_call_chain
    │
    ▼
Agent 执行决策（工具调用/LLM推理）
    │
    ▼
DecisionLogHook.finalize_content()
    ├─ super() 保留原有逻辑
    ├─ 解析 content 识别决策类型
    ├─ prediction_engine 查询当前预测 → prediction_snapshot
    ├─ 提取推荐文本 → recommendation_text
    └─ decision_tracker.log_decision(decision_log) → 持久化
    │
    ▼
训练完成后 → OutcomeCollector.check_plan_execution()
用户反馈时 → OutcomeCollector.record_feedback()（复用 AskUserConfirmManager）
定期校准   → OutcomeCollector.check_prediction_accuracy()
                    │
                    ▼
           持久化 OutcomeRecord → outcomes/YYYY-MM.parquet
```

### 5.2 DecisionLogHook 接口

```python
class DecisionLogHook(ObservabilityHook):
    """决策日志钩子 — 继承 ObservabilityHook，零侵入扩展"""

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
        # 2. twin_engine.get_current_snapshot() → runner_state 摘要
        # 3. 创建 DecisionLog(runner_state=..., execution_status=pending)

    async def before_execute_tools(self, context: AgentHookContext) -> None:
        # 1. 调用 super() 保留原有追踪逻辑
        # 2. 提取 tool_calls → tool_call_chain

    async def finalize_content(self, context, content: str) -> str:
        # 1. 调用 super() 保留原有逻辑
        # 2. 解析 content 识别决策类型
        # 3. prediction_engine 查询当前预测 → prediction_snapshot
        # 4. 提取推荐文本 → recommendation_text
        # 5. decision_tracker.log_decision() → 持久化
```

### 5.3 DecisionTracker 接口

```python
class DecisionTracker:
    def log_decision(self, decision: DecisionLog) -> str
    def query_decisions(
        self, start_date: date | None = None, end_date: date | None = None,
        decision_type: DecisionType | None = None,
        execution_status: str | None = None, limit: int = 50
    ) -> list[DecisionLog]
    def get_decision(self, decision_id: str) -> DecisionLog | None
    def update_execution_status(self, decision_id: str, status: str) -> bool
    def get_pending_decisions(self, days: int = 7) -> list[DecisionLog]
```

### 5.4 OutcomeCollector 接口

```python
class OutcomeCollector:
    def check_plan_execution(self, decision_id: str) -> OutcomeRecord
        # 忠实度算法：fidelity = 1 - weighted_avg(体积偏差, 强度偏差, 时间偏差)

    def check_prediction_accuracy(self, decision_id: str) -> OutcomeRecord
        # 误差算法：VDOT误差 = |预测VDOT - 实际VDOT| / 实际VDOT

    def record_feedback(
        self, decision_id: str, score: int | None = None,
        text: str | None = None, accepted: bool | None = None
    ) -> OutcomeRecord
        # 复用 AskUserConfirmManager 的 ConfirmResult

    def generate_feedback_prompt(self, decision_id: str) -> ConfirmPrompt
        # 扩展 ConfirmScenario.DECISION_FEEDBACK

    def get_outcomes(
        self, start_date: date | None = None, end_date: date | None = None,
        limit: int = 50
    ) -> list[OutcomeRecord]
```

### 5.5 AskUserConfirmManager 集成

**扩展 ConfirmScenario 枚举**：

```python
class ConfirmScenario(Enum):
    TRAINING_PLAN = "training_plan"
    RPE_FEEDBACK = "rpe_feedback"
    INJURY_RISK_ADJUSTMENT = "injury_risk_adjustment"
    DECISION_FEEDBACK = "decision_feedback"       # v0.23 新增
    GENERIC = "generic"
```

**OutcomeCollector.generate_feedback_prompt()** 调用 AskUserConfirmManager 创建反馈提示：

```python
def generate_feedback_prompt(self, decision_id: str) -> ConfirmPrompt:
    manager = AskUserConfirmManager()
    decision = self._tracker.get_decision(decision_id)
    prompt = ConfirmPrompt(
        scenario=ConfirmScenario.DECISION_FEEDBACK,
        title="决策反馈",
        message=f"关于{decision.decision_type.value}的建议，您的体验如何？",
        options=[
            ConfirmOption(key="5", label="很有帮助", value=5),
            ConfirmOption(key="4", label="有帮助", value=4),
            ConfirmOption(key="3", label="一般", value=3),
            ConfirmOption(key="2", label="不太有帮助", value=2),
            ConfirmOption(key="1", label="没帮助", value=1),
        ],
        metadata={"decision_id": decision_id},
    )
    return prompt
```

### 5.6 v0.23 Agent 工具

| 工具名 | 功能 | 输入 | 输出 |
|--------|------|------|------|
| record_feedback | 记录用户反馈 | decision_id, score(1-5), text?, accepted? | OutcomeRecord |
| check_plan_execution | 检查计划执行忠实度 | decision_id | OutcomeRecord |
| check_prediction_accuracy | 检查预测准确度 | decision_id | OutcomeRecord |
| get_decision_history | 查询决策历史 | start_date?, end_date?, type?, limit? | list[DecisionLog] |

### 5.7 v0.23 CLI 命令

```bash
uv run nanobotrun evolution history [--start YYYY-MM-DD] [--end YYYY-MM-DD] [--type TYPE]
uv run nanobotrun evolution feedback <decision_id> --score 4 [--text "很好"] [--accepted]
uv run nanobotrun evolution accuracy [--days 30]
uv run nanobotrun evolution fidelity [--days 30]
uv run nanobotrun evolution status
```

---

## 6. v0.24 个性化学习

### 6.1 CalibrationEngine

偏差修正层：在预测输出上加 bias + scale 线性修正。

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

```python
class CalibrationEngine:
    def calibrate_vdot(self, prediction: VDOTPrediction) -> VDOTPrediction
    def calibrate_injury_risk(self, prediction: InjuryRiskPrediction) -> InjuryRiskPrediction
    def calibrate_race_result(self, prediction: RacePredictionResult) -> RacePredictionResult
    def update_calibration(self, model_type: str, min_samples: int = 10) -> CalibrationProfile
    def get_calibration_profile(self, model_type: str) -> CalibrationProfile | None
    def get_all_profiles(self) -> list[CalibrationProfile]
```

### 6.2 ResponseAnalyzer

训练响应性分析：回答"间歇训练对我提升大，还是阈值训练对我提升大？"

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

### 6.3 v0.24 Agent 工具

| 工具名 | 功能 |
|--------|------|
| analyze_training_response | 分析训练响应性 |
| get_calibration_status | 查看校准配置与效果 |

### 6.4 v0.24 CLI 命令

```bash
uv run nanobotrun evolution calibration [--model-type TYPE]
uv run nanobotrun evolution response [--months 6]
```

---

## 7. v0.25 自适应进化引擎

### 7.1 PromptTuner

4维参数空间：

| 参数 | 范围 | 含义 |
|------|------|------|
| tone_intensity | 0.0-1.0 | 严厉←→温和 |
| detail_level_score | 0.0-1.0 | 简洁←→详细 |
| recommendation_aggressiveness | 0.0-1.0 | 保守←→激进 |
| data_driven_weight | 0.0-1.0 | 直觉←→数据 |

调整算法：
- 采纳率 < 0.4 → aggressiveness -= 0.1, tone_intensity += 0.05
- 采纳率 > 0.7 → aggressiveness += 0.05
- 满意度 < 3.5 → tone_intensity += 0.05, detail_level_score += 0.05

```python
class PromptTuner:
    def get_params(self) -> PromptTuningParams
    def adjust_from_feedback(self, adoption_rate: float) -> PromptTuningParams
    def apply_to_suggestion(self, suggestion: PersonalizedSuggestion) -> PersonalizedSuggestion
    def reset_to_default(self) -> PromptTuningParams
```

### 7.2 EvolutionController

| 触发条件 | 动作 |
|----------|------|
| VDOT预测误差连续3次>5% | calibration_engine.update() |
| 伤病预警连续2次误报 | calibration_engine.update(injury) |
| 用户连续2次拒绝推荐 | prompt_tuner.adjust(adoption↓) |
| 新训练数据积累≥50条 | response_analyzer.reanalyze() |
| 月度复盘（每月1日） | generate_evolution_report() |
| 用户满意度<3.5持续2周 | prompt_tuner.adjust(tone↑) |

```python
class EvolutionController:
    def check_triggers(self) -> list[EvolutionAction]
    def execute_action(self, action: EvolutionAction) -> bool
    def generate_evolution_report(self) -> EvolutionReport
    def get_evolution_status(self) -> EvolutionStatus
```

### 7.3 v0.25 Agent 工具

| 工具名 | 功能 |
|--------|------|
| check_evolution_triggers | 检查进化触发条件 |
| get_evolution_report | 获取月度进化报告 |
| adjust_prompt_params | 手动调整提示参数 |

### 7.4 v0.25 CLI 命令

```bash
uv run nanobotrun evolution triggers
uv run nanobotrun evolution report [--month YYYY-MM]
uv run nanobotrun evolution tune --tone 0.7 --detail 0.5 --aggressive 0.3
```

---

## 8. 存储设计

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

---

## 9. AppContext 集成

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
            calibration=calibration,       # v0.24 激活
            response_analyzer=response_analyzer,  # v0.24 激活
            prompt_tuner=prompt_tuner,     # v0.25 激活
            controller=controller,         # v0.25 激活
        )
        self.set_extension("evolution_engine", engine)
    return engine
```

EvolutionEngine 为薄编排层（与 DigitalTwinEngine 同模式），不包含业务逻辑，仅委托给子组件。

---

## 10. 三版本完整数据流总览

```
Agent交互                                                    用户训练
   │                                                           │
   ▼                                                           ▼
v0.23: 决策追踪
  DecisionLogHook → DecisionTracker → EvolutionStore
  OutcomeCollector ← 训练完成事件 ← SessionRepository
  OutcomeCollector ← 用户反馈 ← AskUserConfirmManager
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

## 11. 风险评估

| 风险 | 等级 | 影响版本 | 应对策略 |
|------|------|----------|----------|
| 决策日志数据膨胀 | 高 | v0.23 | Parquet按月分片 + >12月自动归档；runner_state仅存摘要 |
| 用户反馈稀疏 | 高 | v0.23-v0.25 | 复用AskUserConfirmManager轻量反馈；隐式反馈自动记录 |
| 校准偏差方向错误 | 中 | v0.24 | 最少10条样本才触发；EMA(α=0.7)保证稳定；校准幅度上限±10% |
| 进化方向偏差 | 中 | v0.25 | 月度进化报告供review；调整幅度小(0.05-0.1)；reset_to_default()回退 |
| Hook扩展影响透明化 | 中 | v0.23 | 所有方法先调super()再扩展；twin/prediction查询失败graceful降级 |
| 训练响应性样本不足 | 低 | v0.24 | 最低样本数门槛(每组≥5)；不足时返回"数据不足" |

---

## 12. 技术选型汇总

| 类别 | 选型 | 版本 | 用途 |
|------|------|------|------|
| 数据存储 | Apache Parquet (via pyarrow) | 已有 | decisions/outcomes按月分片 |
| 查询引擎 | Polars LazyFrame | 0.20+ 已有 | EvolutionStore查询 |
| 配置存储 | JSON文件 | 标准库 | calibration_profiles / prompt_params |
| Hook框架 | nanobot-ai AgentHook | 已有 | DecisionLogHook扩展 |
| 反馈收集 | AskUserConfirmManager | 已有(v0.17) | 扩展ConfirmScenario |
| 数据模型 | frozen dataclass | 已有 | 所有evolution数据模型 |
| 异常体系 | NanobotRunnerError子类 | 已有 | EvolutionError |
| 依赖注入 | AppContext扩展属性 | 已有 | evolution_engine懒加载 |

**无新增外部依赖，全部基于现有技术栈。**
