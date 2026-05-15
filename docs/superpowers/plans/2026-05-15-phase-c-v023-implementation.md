# v0.23 决策-结果追踪系统 — 实施计划

> **文档版本**: v1.0
> **创建日期**: 2026-05-15
> **对齐文档**: Phase C 技术预研报告 v1.0
> **当前基线**: v0.21.0
> **目标版本**: v0.23.0

---

## 1. 概述

### 1.1 目标

实现 v0.23 决策-结果追踪系统，包含：
- **DecisionLog**：记录每次AI决策的完整上下文（跑者状态、工具调用、预测快照）
- **OutcomeRecord**：回填实际训练结果，计算执行忠实度和预测误差
- **DecisionLogHook**：扩展现有 ObservabilityHook，自动采集决策数据
- **EvolutionStore**：统一存储编排，Parquet按月分片
- **EvolutionEngine**：薄编排层，委托给子组件

### 1.2 范围边界

| 包含 | 不包含 |
|------|--------|
| DecisionLog 数据模型 | CalibrationEngine（v0.24） |
| OutcomeRecord 数据模型 | ResponseAnalyzer（v0.24） |
| DecisionTracker | EvolutionController（v0.25） |
| OutcomeCollector | PromptTuner（v0.25） |
| DecisionLogHook | calibration_profiles.json（v0.24） |
| EvolutionStore（decisions + outcomes） | prompt_params.json（v0.25） |
| EvolutionEngine 薄编排层 | 进化触发器（v0.25） |
| EvolutionError 异常 | |
| EvolutionConfig 配置 | |
| AppContext 集成 | |
| CLI 命令 + Handler | |
| Agent 工具 | |
| 单元测试 | |

### 1.3 依赖

| 依赖模块 | 用途 | 状态 |
|----------|------|------|
| transparency (ObservabilityHook) | Hook扩展基类 | ✅ 已有 |
| twin (DigitalTwinEngine) | 获取RunnerState快照 | ✅ 已有 |
| prediction (PredictionEngine) | 获取预测快照 | ✅ 已有 |
| storage (SessionRepository) | 查询实际训练数据 | ✅ 已有 |
| base (AppContext) | 依赖注入 | ✅ 已有 |

---

## 2. 任务分解

### Task 1: 异常与配置 — `exceptions.py` + `config.py`

**文件**:
- `src/core/evolution/exceptions.py`（新建）
- `src/core/evolution/config.py`（新建）

**实施步骤**:

1. 创建 `exceptions.py`，定义 `EvolutionError` 继承 `NanobotRunnerError`

```python
# src/core/evolution/exceptions.py
from dataclasses import dataclass
from src.core.base.exceptions import NanobotRunnerError


@dataclass
class EvolutionError(NanobotRunnerError):
    """进化模块异常"""
    error_code: str = "EVOLUTION_ERROR"
    recovery_suggestion: str | None = "请检查进化模块配置或数据完整性"


@dataclass
class DecisionLogError(EvolutionError):
    """决策日志异常"""
    error_code: str = "DECISION_LOG_ERROR"
    recovery_suggestion: str | None = "请检查决策日志数据格式"


@dataclass
class OutcomeCollectionError(EvolutionError):
    """结果回填异常"""
    error_code: str = "OUTCOME_COLLECTION_ERROR"
    recovery_suggestion: str | None = "请检查结果回填数据完整性"
```

2. 创建 `config.py`，定义进化配置

```python
# src/core/evolution/config.py
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class EvolutionConfig:
    """进化模块配置"""
    decisions_dir_name: str = "decisions"
    outcomes_dir_name: str = "outcomes"
    archive_after_months: int = 12
    default_feedback_prompt_days: int = 7
    fidelity_threshold: float = 0.7
    prediction_error_threshold: float = 0.05
    max_query_limit: int = 100
    default_query_limit: int = 20
```

**验收标准**:
- [x] EvolutionError 继承 NanobotRunnerError
- [x] DecisionLogError / OutcomeCollectionError 继承 EvolutionError
- [x] EvolutionConfig 包含所有阈值配置
- [x] 类型注解完整，无 `Any` 滥用

---

### Task 2: 核心数据模型 — `models.py`

**文件**: `src/core/evolution/models.py`（新建）

**实施步骤**:

1. 定义 `DecisionType` 枚举（扩展现有 transparency 的 DecisionType）

```python
class EvolutionDecisionType(str, Enum):
    """进化模块决策类型（扩展transparency的DecisionType）"""
    PLAN_GENERATION = "plan_generation"
    PREDICTION_QUERY = "prediction_query"
    RISK_ASSESSMENT = "risk_assessment"
    TRAINING_ADVICE = "training_advice"
    GENERAL = "general"
```

2. 定义 `ExecutionStatus` 枚举

```python
class ExecutionStatus(str, Enum):
    """执行状态"""
    PENDING = "pending"
    EXECUTED = "executed"
    SKIPPED = "skipped"
    MODIFIED = "modified"
```

3. 定义 `DecisionLog` frozen dataclass

```python
@dataclass(frozen=True)
class DecisionLog:
    """决策日志（不可变）

    记录一次AI决策的完整上下文。

    Attributes:
        decision_id: 唯一标识（UUID）
        timestamp: 决策发生时间
        runner_state: 决策时RunnerState快照（5维度数值摘要）
        decision_type: 决策类型
        tool_call_chain: 本次决策调用的所有工具及参数
        prediction_snapshot: 决策时的预测结果快照
        recommendation_text: 推荐文本摘要
        execution_status: 执行状态
        recommendation_accepted: 用户是否采纳推荐
        session_key: 会话标识
    """
    decision_id: str
    timestamp: datetime
    runner_state: dict[str, float]
    decision_type: EvolutionDecisionType
    tool_call_chain: list[dict[str, Any]]
    prediction_snapshot: dict[str, Any] | None = None
    recommendation_text: str = ""
    execution_status: ExecutionStatus = ExecutionStatus.PENDING
    recommendation_accepted: bool | None = None
    session_key: str = ""

    def to_dict(self) -> dict[str, Any]: ...
    def to_parquet_row(self) -> dict[str, Any]: ...
```

4. 定义 `OutcomeRecord` frozen dataclass

```python
@dataclass(frozen=True)
class OutcomeRecord:
    """结果回填记录（不可变）

    记录决策执行后的实际结果。

    Attributes:
        decision_id: 关联决策ID（FK）
        outcome_timestamp: 结果记录时间
        actual_vdot: 实际VDOT
        actual_injury: 是否发生伤病
        execution_fidelity: 执行忠实度（0-1）
        user_feedback_score: 用户评分（1-5）
        user_feedback_text: 用户文本反馈
        prediction_error: 预测误差百分比
        session_id: 关联训练Session
    """
    decision_id: str
    outcome_timestamp: datetime
    actual_vdot: float | None = None
    actual_injury: bool = False
    execution_fidelity: float | None = None
    user_feedback_score: int | None = None
    user_feedback_text: str = ""
    prediction_error: float | None = None
    session_id: str = ""

    def to_dict(self) -> dict[str, Any]: ...
    def to_parquet_row(self) -> dict[str, Any]: ...
```

5. 定义 `EvolutionStatus` 汇总数据类

```python
@dataclass(frozen=True)
class EvolutionStatus:
    """进化模块状态摘要"""
    total_decisions: int
    pending_decisions: int
    total_outcomes: int
    avg_fidelity: float | None
    avg_prediction_error: float | None
    avg_feedback_score: float | None
    last_decision_time: datetime | None

    def to_dict(self) -> dict[str, Any]: ...
```

**验收标准**:
- [x] 所有数据类使用 `frozen=True`
- [x] 提供 `to_dict()` 和 `to_parquet_row()` 方法
- [x] 类型注解完整，无 `Dict[str, Any]` 返回值
- [x] runner_state 仅存5维度数值摘要（vdot, ctl, atl, tsb, fatigue_score）
- [x] DecisionLog 与 OutcomeRecord 通过 decision_id 关联

---

### Task 3: 统一存储编排 — `evolution_store.py`

**文件**: `src/core/evolution/evolution_store.py`（新建）

**实施步骤**:

1. 定义 `EvolutionStore` 类，负责 decisions 和 outcomes 的 Parquet 读写

```python
class EvolutionStore:
    """进化模块统一存储编排

    负责 decisions/outcomes 的 Parquet 读写，
    按月分片，>12月自动归档。
    """

    def __init__(self, data_dir: Path, config: EvolutionConfig) -> None:
        self._data_dir = data_dir
        self._config = config
        self._decisions_dir = data_dir / config.decisions_dir_name
        self._outcomes_dir = data_dir / config.outcomes_dir_name

    def append_decision(self, decision: DecisionLog) -> None:
        """追加决策日志到当月Parquet文件"""
        # 1. 确定目标文件: decisions/2026-05/2026-05_decisions.parquet
        # 2. 读取已有数据（LazyFrame）或创建空DataFrame
        # 3. append新行 → collect → write_parquet
        # 4. 注意：使用 Polars append 模式，不重写整月文件

    def append_outcome(self, outcome: OutcomeRecord) -> None:
        """追加结果记录到当月Parquet文件"""
        # 同 append_decision 逻辑

    def query_decisions(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        decision_type: EvolutionDecisionType | None = None,
        execution_status: ExecutionStatus | None = None,
        limit: int = 20,
    ) -> list[DecisionLog]:
        """查询决策日志（LazyFrame优先）"""
        # 1. scan_parquet → filter → sort → limit → collect
        # 2. 反序列化为 DecisionLog 列表

    def query_outcomes(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 20,
    ) -> list[OutcomeRecord]:
        """查询结果记录（LazyFrame优先）"""

    def get_decision(self, decision_id: str) -> DecisionLog | None:
        """获取单个决策"""

    def update_execution_status(
        self, decision_id: str, status: ExecutionStatus
    ) -> bool:
        """更新决策执行状态"""
        # 1. 读取当月文件
        # 2. 定位 decision_id 行
        # 3. 更新 execution_status 列
        # 4. 写回文件

    def get_pending_decisions(self, days: int = 7) -> list[DecisionLog]:
        """获取待回填的决策（最近N天、状态为pending）"""

    def get_status_summary(self) -> EvolutionStatus:
        """获取进化模块状态摘要"""

    def archive_old_data(self) -> int:
        """归档>12月的数据（压缩为yearly归档文件）"""
```

2. 存储路径设计

```
~/.nanobot-runner/
├── decisions/
│   └── 2026-05/
│       └── 2026-05_decisions.parquet
├── outcomes/
│   └── 2026-05/
│       └── 2026-05_outcomes.parquet
```

**验收标准**:
- [x] 所有查询使用 LazyFrame（`scan_parquet` → `filter` → `collect`）
- [x] 仅最终输出时调用 `.collect()`
- [x] append 模式不重写整月文件
- [x] 归档逻辑正确（>12月数据压缩）
- [x] 异常使用 EvolutionError 子类

---

### Task 4: 决策追踪器 — `decision_tracker.py`

**文件**: `src/core/evolution/decision_tracker.py`（新建）

**实施步骤**:

1. 定义 `DecisionTracker` 类

```python
class DecisionTracker:
    """决策追踪器

    负责记录和查询AI决策日志。
    """

    def __init__(self, store: EvolutionStore) -> None:
        self._store = store

    def log_decision(self, decision: DecisionLog) -> str:
        """记录决策日志

        Args:
            decision: 决策日志

        Returns:
            str: decision_id
        """
        self._store.append_decision(decision)
        return decision.decision_id

    def query_decisions(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        decision_type: EvolutionDecisionType | None = None,
        execution_status: ExecutionStatus | None = None,
        limit: int = 20,
    ) -> list[DecisionLog]:
        """查询决策历史"""
        return self._store.query_decisions(
            start_date=start_date,
            end_date=end_date,
            decision_type=decision_type,
            execution_status=execution_status,
            limit=limit,
        )

    def get_decision(self, decision_id: str) -> DecisionLog | None:
        """获取单个决策"""
        return self._store.get_decision(decision_id)

    def update_execution_status(
        self, decision_id: str, status: ExecutionStatus
    ) -> bool:
        """更新决策执行状态"""
        return self._store.update_execution_status(decision_id, status)

    def get_pending_decisions(self, days: int = 7) -> list[DecisionLog]:
        """获取待回填的决策"""
        return self._store.get_pending_decisions(days=days)
```

**验收标准**:
- [x] 委托给 EvolutionStore，不直接操作 Parquet
- [x] log_decision 返回 decision_id
- [x] 类型注解完整

---

### Task 5: 结果回填收集器 — `outcome_collector.py`

**文件**: `src/core/evolution/outcome_collector.py`（新建）

**实施步骤**:

1. 定义 `OutcomeCollector` 类

```python
class OutcomeCollector:
    """结果回填收集器

    负责收集决策执行后的实际结果，
    计算执行忠实度和预测误差。
    """

    def __init__(
        self,
        store: EvolutionStore,
        session_repo: SessionRepository,
        config: EvolutionConfig,
    ) -> None:
        self._store = store
        self._session_repo = session_repo
        self._config = config

    def check_plan_execution(self, decision_id: str) -> OutcomeRecord:
        """检查计划执行忠实度

        忠实度算法：
        fidelity = 1 - weighted_avg(体积偏差, 强度偏差, 时间偏差)

        体积偏差 = |计划跑量 - 实际跑量| / 计划跑量
        强度偏差 = |计划TSS - 实际TSS| / max(计划TSS, 1)
        时间偏差 = |计划时长 - 实际时长| / 计划时长

        Args:
            decision_id: 关联决策ID

        Returns:
            OutcomeRecord: 包含执行忠实度的结果记录

        Raises:
            OutcomeCollectionError: 决策不存在或无法匹配训练
        """

    def check_prediction_accuracy(self, decision_id: str) -> OutcomeRecord:
        """检查预测准确度

        误差算法：
        VDOT误差 = |预测VDOT - 实际VDOT| / 实际VDOT

        Args:
            decision_id: 关联决策ID

        Returns:
            OutcomeRecord: 包含预测误差的结果记录
        """

    def record_feedback(
        self,
        decision_id: str,
        score: int,
        text: str = "",
        accepted: bool | None = None,
    ) -> OutcomeRecord:
        """记录用户反馈

        Args:
            decision_id: 关联决策ID
            score: 用户评分（1-5）
            text: 用户文本反馈
            accepted: 是否采纳推荐

        Returns:
            OutcomeRecord: 包含用户反馈的结果记录
        """

    def generate_feedback_prompt(self, days: int = 7) -> list[dict[str, Any]]:
        """生成反馈提示

        查找最近N天未回填的决策，生成反馈提示。

        Args:
            days: 回溯天数

        Returns:
            list[dict]: 反馈提示列表，每项包含 decision_id, decision_type, timestamp, recommendation_text
        """

    def get_outcomes(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 20,
    ) -> list[OutcomeRecord]:
        """查询结果记录"""
        return self._store.query_outcomes(
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )
```

**验收标准**:
- [x] check_plan_execution 计算忠实度算法正确
- [x] check_prediction_accuracy 计算预测误差算法正确
- [x] record_feedback 验证 score 范围 1-5
- [x] generate_feedback_prompt 返回未回填决策
- [x] 异常使用 OutcomeCollectionError

---

### Task 6: DecisionLogHook — 扩展 ObservabilityHook

**文件**: `src/core/evolution/decision_log_hook.py`（新建）

**实施步骤**:

1. 定义 `DecisionLogHook` 类，继承 `ObservabilityHook`

```python
class DecisionLogHook(ObservabilityHook):
    """决策日志钩子

    扩展 ObservabilityHook，在Agent迭代和工具调用时
    自动记录决策上下文到 DecisionLog。
    """

    def __init__(
        self,
        manager: ObservabilityManager,
        engine: TransparencyEngine | None,
        decision_tracker: DecisionTracker,
        twin_engine: DigitalTwinEngine,
        prediction_engine: PredictionEngine,
    ) -> None:
        super().__init__(manager=manager, engine=engine)
        self._decision_tracker = decision_tracker
        self._twin_engine = twin_engine
        self._prediction_engine = prediction_engine
        self._current_decision_id: str | None = None
        self._current_runner_state: dict[str, float] = {}

    async def before_iteration(self, context: AgentHookContext) -> None:
        """迭代前：获取跑者状态，创建DecisionLog"""
        # 1. 调用 super() 保留原有追踪逻辑
        await super().before_iteration(context)
        # 2. twin_engine.get_state_vector() → runner_state摘要
        try:
            snapshot = self._twin_engine.get_current_snapshot()
            state = snapshot.to_dict()
            self._current_runner_state = {
                "vdot": state.get("fitness", {}).get("vdot", 0.0),
                "ctl": state.get("load", {}).get("ctl", 0.0),
                "atl": state.get("load", {}).get("atl", 0.0),
                "tsb": state.get("load", {}).get("tsb", 0.0),
                "fatigue_score": state.get("body_signal", {}).get("fatigue_score", 0.0),
            }
        except Exception:
            self._current_runner_state = {}
        # 3. 生成 decision_id
        self._current_decision_id = f"dec_{uuid4().hex[:12]}"

    async def before_execute_tools(self, context: AgentHookContext) -> None:
        """工具执行前：记录工具调用链"""
        # 1. 调用 super() 保留原有追踪逻辑
        await super().before_execute_tools(context)
        # 2. 提取 tool_calls → tool_call_chain
        # tool_call_chain 存储在实例变量中，finalize时使用

    async def finalize_content(
        self, context: AgentHookContext, content: str
    ) -> str:
        """最终输出：记录预测快照，持久化DecisionLog"""
        # 1. 调用 super() 保留原有逻辑
        content = await super().finalize_content(context, content)
        # 2. 解析 content 识别决策类型
        decision_type = self._classify_decision(content)
        # 3. prediction_engine 查询当前预测 → prediction_snapshot
        prediction_snapshot = self._get_prediction_snapshot()
        # 4. 构建 DecisionLog 并持久化
        if self._current_decision_id is not None:
            decision = DecisionLog(
                decision_id=self._current_decision_id,
                timestamp=datetime.now(),
                runner_state=self._current_runner_state,
                decision_type=decision_type,
                tool_call_chain=self._tool_call_chain,
                prediction_snapshot=prediction_snapshot,
                recommendation_text=content[:500],
                session_key=self._current_trace_id or "",
            )
            self._decision_tracker.log_decision(decision)
        self._current_decision_id = None
        return content

    def _classify_decision(self, content: str) -> EvolutionDecisionType:
        """根据内容分类决策类型"""
        # 基于关键词匹配：
        # 包含"训练计划"/"周计划" → PLAN_GENERATION
        # 包含"预测"/"VDOT趋势" → PREDICTION_QUERY
        # 包含"伤病"/"风险" → RISK_ASSESSMENT
        # 包含"建议"/"推荐" → TRAINING_ADVICE
        # 默认 → GENERAL

    def _get_prediction_snapshot(self) -> dict[str, Any] | None:
        """获取当前预测快照"""
        # 从 prediction_engine 获取最新预测结果
```

**验收标准**:
- [x] 继承 ObservabilityHook，所有方法调用 super()
- [x] before_iteration 获取 runner_state 摘要（5维度数值）
- [x] before_execute_tools 记录工具调用链
- [x] finalize_content 持久化 DecisionLog
- [x] _classify_decision 基于关键词匹配
- [x] 异常不阻断原有 Hook 逻辑（try/except 包裹）

---

### Task 7: 进化引擎编排层 — `__init__.py` + EvolutionEngine

**文件**: `src/core/evolution/__init__.py`（新建）

**实施步骤**:

1. 定义 `EvolutionEngine` 薄编排层

```python
@dataclass
class EvolutionEngine:
    """进化引擎（薄编排层）

    不包含业务逻辑，仅委托给子组件。
    与 DigitalTwinEngine 同模式。
    """
    tracker: DecisionTracker
    collector: OutcomeCollector
    store: EvolutionStore
    config: EvolutionConfig

    def log_decision(self, decision: DecisionLog) -> str:
        return self.tracker.log_decision(decision)

    def query_decisions(self, **kwargs) -> list[DecisionLog]:
        return self.tracker.query_decisions(**kwargs)

    def get_decision(self, decision_id: str) -> DecisionLog | None:
        return self.tracker.get_decision(decision_id)

    def check_plan_execution(self, decision_id: str) -> OutcomeRecord:
        return self.collector.check_plan_execution(decision_id)

    def check_prediction_accuracy(self, decision_id: str) -> OutcomeRecord:
        return self.collector.check_prediction_accuracy(decision_id)

    def record_feedback(self, decision_id: str, score: int, **kwargs) -> OutcomeRecord:
        return self.collector.record_feedback(decision_id=decision_id, score=score, **kwargs)

    def generate_feedback_prompt(self, days: int = 7) -> list[dict[str, Any]]:
        return self.collector.generate_feedback_prompt(days=days)

    def get_status(self) -> EvolutionStatus:
        return self.store.get_status_summary()
```

2. 定义 `__init__.py` 导出

```python
from src.core.evolution.models import (
    DecisionLog,
    EvolutionDecisionType,
    EvolutionStatus,
    ExecutionStatus,
    OutcomeRecord,
)
from src.core.evolution.engine import EvolutionEngine

__all__ = [
    "DecisionLog",
    "EvolutionDecisionType",
    "EvolutionStatus",
    "EvolutionEngine",
    "ExecutionStatus",
    "OutcomeRecord",
]
```

**验收标准**:
- [x] EvolutionEngine 为薄编排层，不包含业务逻辑
- [x] 所有方法委托给子组件
- [x] __init__.py 导出完整

---

### Task 8: AppContext 集成

**文件**: `src/core/base/context.py`（修改）

**实施步骤**:

1. 在 `AppContext` 中新增 `evolution_engine` 属性

```python
@property
def evolution_engine(self) -> EvolutionEngine:
    """获取进化引擎（v0.23.0新增）"""
    from src.core.evolution.config import EvolutionConfig
    from src.core.evolution.engine import EvolutionEngine
    from src.core.evolution.evolution_store import EvolutionStore
    from src.core.evolution.outcome_collector import OutcomeCollector
    from src.core.evolution.decision_tracker import DecisionTracker

    engine = self.get_extension("evolution_engine")
    if engine is None:
        config = EvolutionConfig()
        store = EvolutionStore(
            data_dir=self.config.data_dir,
            config=config,
        )
        tracker = DecisionTracker(store=store)
        collector = OutcomeCollector(
            store=store,
            session_repo=self.session_repo,
            config=config,
        )
        engine = EvolutionEngine(
            tracker=tracker,
            collector=collector,
            store=store,
            config=config,
        )
        self.set_extension("evolution_engine", engine)
    return engine
```

2. 在 `TYPE_CHECKING` 块中添加导入

```python
if TYPE_CHECKING:
    from src.core.evolution.engine import EvolutionEngine
    # ... 其他已有导入
```

**验收标准**:
- [x] evolution_engine 使用懒加载模式（get_extension / set_extension）
- [x] 构建所有子组件（store → tracker → collector → engine）
- [x] TYPE_CHECKING 导入正确
- [x] 不影响现有属性

---

### Task 9: CLI Handler — `evolution_handler.py`

**文件**: `src/cli/handlers/evolution_handler.py`（新建）

**实施步骤**:

1. 定义 `EvolutionHandler` 类

```python
class EvolutionHandler:
    """进化模块业务逻辑层"""

    def __init__(self, context: AppContext | None = None) -> None:
        if context is None:
            context = AppContextFactory.create()
        self.context = context

    def _get_engine(self) -> EvolutionEngine:
        engine = self.context.evolution_engine
        if engine is None:
            raise RuntimeError("进化引擎未初始化，请先运行 nanobotrun system init")
        return engine

    def get_decision_history(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        decision_type: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """查询决策历史"""
        from datetime import datetime

        engine = self._get_engine()
        dt_type = None
        if decision_type:
            dt_type = EvolutionDecisionType(decision_type)
        start = datetime.strptime(start_date, "%Y-%m-%d") if start_date else None
        end = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None
        decisions = engine.query_decisions(
            start_date=start,
            end_date=end,
            decision_type=dt_type,
            limit=limit,
        )
        return [d.to_dict() for d in decisions]

    def record_feedback(
        self,
        decision_id: str,
        score: int,
        text: str = "",
        accepted: bool | None = None,
    ) -> dict[str, Any]:
        """记录用户反馈"""
        engine = self._get_engine()
        outcome = engine.record_feedback(
            decision_id=decision_id,
            score=score,
            text=text,
            accepted=accepted,
        )
        return outcome.to_dict()

    def check_prediction_accuracy(self, decision_id: str) -> dict[str, Any]:
        """检查预测准确度"""
        engine = self._get_engine()
        outcome = engine.check_prediction_accuracy(decision_id=decision_id)
        return outcome.to_dict()

    def check_plan_execution(self, decision_id: str) -> dict[str, Any]:
        """检查计划执行忠实度"""
        engine = self._get_engine()
        outcome = engine.check_plan_execution(decision_id=decision_id)
        return outcome.to_dict()

    def get_accuracy_summary(self, days: int = 30) -> dict[str, Any]:
        """获取预测准确度摘要"""
        from datetime import datetime, timedelta

        engine = self._get_engine()
        end = datetime.now()
        start = end - timedelta(days=days)
        outcomes = engine.collector.get_outcomes(start_date=start, end_date=end, limit=1000)
        errors = [o.prediction_error for o in outcomes if o.prediction_error is not None]
        if not errors:
            return {"message": "暂无预测准确度数据", "days": days}
        return {
            "days": days,
            "sample_count": len(errors),
            "avg_error": sum(errors) / len(errors),
            "max_error": max(errors),
            "min_error": min(errors),
        }

    def get_fidelity_summary(self, days: int = 30) -> dict[str, Any]:
        """获取执行忠实度摘要"""
        from datetime import datetime, timedelta

        engine = self._get_engine()
        end = datetime.now()
        start = end - timedelta(days=days)
        outcomes = engine.collector.get_outcomes(start_date=start, end_date=end, limit=1000)
        fidelities = [o.execution_fidelity for o in outcomes if o.execution_fidelity is not None]
        if not fidelities:
            return {"message": "暂无执行忠实度数据", "days": days}
        return {
            "days": days,
            "sample_count": len(fidelities),
            "avg_fidelity": sum(fidelities) / len(fidelities),
            "high_fidelity_count": sum(1 for f in fidelities if f >= 0.7),
            "low_fidelity_count": sum(1 for f in fidelities if f < 0.7),
        }

    def get_status(self) -> dict[str, Any]:
        """获取进化模块状态"""
        engine = self._get_engine()
        status = engine.get_status()
        return status.to_dict()
```

**验收标准**:
- [x] 遵循 TwinHandler / PredictionHandler 同模式
- [x] _get_engine 使用 AppContext 懒加载
- [x] 所有方法返回 dict（由 dataclass.to_dict() 转换）
- [x] 日期参数使用字符串输入，内部转换

---

### Task 10: CLI 命令 — `evolution.py`

**文件**: `src/cli/commands/evolution.py`（新建）

**实施步骤**:

1. 定义 CLI 命令组

```python
app = typer.Typer(help="自适应进化引擎命令", no_args_is_help=True)
```

2. 实现 `history` 命令

```python
@app.command(name="history")
def decision_history(
    start_date: str = typer.Option(None, "--start", "-s", help="开始日期(YYYY-MM-DD)"),
    end_date: str = typer.Option(None, "--end", "-e", help="结束日期(YYYY-MM-DD)"),
    decision_type: str = typer.Option(None, "--type", "-t", help="决策类型"),
    limit: int = typer.Option(20, "--limit", "-l", help="返回数量"),
) -> None:
    """查询决策历史

    Examples:
        nanobotrun evolution history --start 2026-05-01 --limit 10
        nanobotrun evolution history --type plan_generation
    """
```

3. 实现 `feedback` 命令

```python
@app.command(name="feedback")
def record_feedback(
    decision_id: str = typer.Argument(help="决策ID"),
    score: int = typer.Option(..., "--score", "-s", help="评分(1-5)"),
    text: str = typer.Option("", "--text", "-t", help="文本反馈"),
    accepted: bool = typer.Option(False, "--accepted", "-a", help="是否采纳推荐"),
) -> None:
    """记录用户反馈

    Examples:
        nanobotrun evolution feedback dec_abc123 --score 4 --text "很好" --accepted
    """
```

4. 实现 `accuracy` 命令

```python
@app.command(name="accuracy")
def prediction_accuracy(
    days: int = typer.Option(30, "--days", "-d", help="回溯天数"),
) -> None:
    """查看预测准确度

    Examples:
        nanobotrun evolution accuracy --days 30
    """
```

5. 实现 `fidelity` 命令

```python
@app.command(name="fidelity")
def execution_fidelity(
    days: int = typer.Option(30, "--days", "-d", help="回溯天数"),
) -> None:
    """查看执行忠实度

    Examples:
        nanobotrun evolution fidelity --days 30
    """
```

6. 实现 `status` 命令

```python
@app.command(name="status")
def evolution_status() -> None:
    """查看进化模块状态

    Examples:
        nanobotrun evolution status
    """
```

**验收标准**:
- [x] 遵循 twin.py / prediction.py 同模式
- [x] 使用 Rich Table/Panel 展示数据
- [x] 错误处理使用 CLIError + print_error
- [x] 所有命令有 Examples 文档

---

### Task 11: CLI 注册

**文件**:
- `src/cli/commands/__init__.py`（修改）
- `src/cli/app.py`（修改）

**实施步骤**:

1. 在 `__init__.py` 中添加导入和导出

```python
from src.cli.commands.evolution import app as evolution_app

__all__ = [
    # ... 已有
    "evolution_app",
]
```

2. 在 `app.py` 中注册命令

```python
from src.cli.commands import evolution_app

app.add_typer(evolution_app, name="evolution")
```

**验收标准**:
- [x] `nanobotrun evolution --help` 正常输出
- [x] 不影响现有命令

---

### Task 12: Agent 工具集成

**文件**: `src/agents/tools.py`（修改）

**实施步骤**:

1. 新增4个Agent工具类

```python
class RecordFeedbackTool(BaseTool):
    """记录用户反馈"""

    @property
    def name(self) -> str:
        return "record_feedback"

    @property
    def description(self) -> str:
        return "记录用户对AI决策的反馈评分和意见"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "decision_id": {"type": "string", "description": "决策ID"},
                "score": {"type": "integer", "description": "评分(1-5)", "minimum": 1, "maximum": 5},
                "text": {"type": "string", "description": "文本反馈(可选)"},
                "accepted": {"type": "boolean", "description": "是否采纳推荐(可选)"},
            },
            "required": ["decision_id", "score"],
        }

    async def execute(self, **kwargs: Any) -> Any:
        return self._run_sync(
            self.runner_tools.record_feedback,
            **kwargs,
        )


class CheckPlanExecutionTool(BaseTool):
    """检查计划执行忠实度"""

    @property
    def name(self) -> str:
        return "check_plan_execution"

    @property
    def description(self) -> str:
        return "检查训练计划的实际执行忠实度"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "decision_id": {"type": "string", "description": "决策ID"},
            },
            "required": ["decision_id"],
        }

    async def execute(self, **kwargs: Any) -> Any:
        return self._run_sync(
            self.runner_tools.check_plan_execution,
            **kwargs,
        )


class CheckPredictionAccuracyTool(BaseTool):
    """检查预测准确度"""

    @property
    def name(self) -> str:
        return "check_prediction_accuracy"

    @property
    def description(self) -> str:
        return "检查AI预测的准确度"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "decision_id": {"type": "string", "description": "决策ID"},
            },
            "required": ["decision_id"],
        }

    async def execute(self, **kwargs: Any) -> Any:
        return self._run_sync(
            self.runner_tools.check_prediction_accuracy,
            **kwargs,
        )


class GetDecisionHistoryTool(BaseTool):
    """查询决策历史"""

    @property
    def name(self) -> str:
        return "get_decision_history"

    @property
    def description(self) -> str:
        return "查询AI决策历史记录"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "开始日期(YYYY-MM-DD, 可选)"},
                "end_date": {"type": "string", "description": "结束日期(YYYY-MM-DD, 可选)"},
                "decision_type": {"type": "string", "description": "决策类型(可选)"},
                "limit": {"type": "integer", "description": "返回数量限制", "default": 20},
            },
        }

    async def execute(self, **kwargs: Any) -> Any:
        return self._run_sync(
            self.runner_tools.get_decision_history,
            **kwargs,
        )
```

2. 在 `RunnerTools` 中添加对应方法

```python
def record_feedback(self, decision_id: str, score: int, text: str = "", accepted: bool | None = None) -> dict[str, Any]:
    """记录用户反馈"""
    handler = EvolutionHandler(self.context)
    return handler.record_feedback(decision_id=decision_id, score=score, text=text, accepted=accepted)

def check_plan_execution(self, decision_id: str) -> dict[str, Any]:
    """检查计划执行忠实度"""
    handler = EvolutionHandler(self.context)
    return handler.check_plan_execution(decision_id=decision_id)

def check_prediction_accuracy(self, decision_id: str) -> dict[str, Any]:
    """检查预测准确度"""
    handler = EvolutionHandler(self.context)
    return handler.check_prediction_accuracy(decision_id=decision_id)

def get_decision_history(self, start_date: str | None = None, end_date: str | None = None, decision_type: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
    """查询决策历史"""
    handler = EvolutionHandler(self.context)
    return handler.get_decision_history(start_date=start_date, end_date=end_date, decision_type=decision_type, limit=limit)
```

3. 在工具注册列表中添加新工具

**验收标准**:
- [x] 4个工具类遵循 BaseTool 模式
- [x] RunnerTools 方法委托给 EvolutionHandler
- [x] 工具描述清晰
- [x] 参数 schema 完整

---

### Task 13: 单元测试

**文件**:
- `tests/unit/evolution/test_models.py`（新建）
- `tests/unit/evolution/test_decision_tracker.py`（新建）
- `tests/unit/evolution/test_outcome_collector.py`（新建）
- `tests/unit/evolution/test_evolution_store.py`（新建）
- `tests/unit/evolution/test_decision_log_hook.py`（新建）

**实施步骤**:

1. **test_models.py** — 测试数据模型
   - DecisionLog 创建与 to_dict / to_parquet_row
   - OutcomeRecord 创建与 to_dict / to_parquet_row
   - EvolutionStatus 创建与 to_dict
   - 枚举值正确性

2. **test_decision_tracker.py** — 测试决策追踪器
   - log_decision 正确委托给 store
   - query_decisions 参数传递正确
   - get_decision 返回正确结果
   - update_execution_status 委托正确

3. **test_outcome_collector.py** — 测试结果回填收集器
   - check_plan_execution 忠实度计算正确
   - check_prediction_accuracy 误差计算正确
   - record_feedback 验证 score 范围
   - generate_feedback_prompt 返回未回填决策

4. **test_evolution_store.py** — 测试存储编排
   - append_decision 写入正确
   - query_decisions 过滤正确
   - update_execution_status 更新正确
   - get_pending_decisions 返回正确
   - archive_old_data 归档正确

5. **test_decision_log_hook.py** — 测试决策日志钩子
   - before_iteration 获取 runner_state
   - before_execute_tools 记录工具调用
   - finalize_content 持久化 DecisionLog
   - _classify_decision 分类正确

**验收标准**:
- [x] 核心业务逻辑测试覆盖 ≥ 80%
- [x] Mock 外部依赖（twin_engine, prediction_engine, session_repo）
- [x] 不 Mock 内部业务逻辑
- [x] 使用 tmp_path 作为测试数据目录

---

## 3. 实施顺序

```
Task 1 (exceptions + config)
    │
    ▼
Task 2 (models)
    │
    ▼
Task 3 (evolution_store)
    │
    ├──► Task 4 (decision_tracker)
    │
    ├──► Task 5 (outcome_collector)
    │
    └──► Task 6 (decision_log_hook)
              │
              ▼
         Task 7 (EvolutionEngine + __init__.py)
              │
              ▼
         Task 8 (AppContext 集成)
              │
              ├──► Task 9 (CLI Handler)
              │         │
              │         ▼
              │    Task 10 (CLI 命令)
              │         │
              │         ▼
              │    Task 11 (CLI 注册)
              │
              └──► Task 12 (Agent 工具)
                        │
                        ▼
                   Task 13 (单元测试)
```

**关键路径**: Task 1 → 2 → 3 → 7 → 8 → 9 → 10 → 11

**可并行**: Task 4/5/6（依赖 Task 3），Task 12/13（依赖 Task 8）

---

## 4. 文件变更清单

| 操作 | 文件路径 | 说明 |
|------|----------|------|
| 新建 | `src/core/evolution/__init__.py` | 模块入口 + EvolutionEngine |
| 新建 | `src/core/evolution/models.py` | 核心数据模型 |
| 新建 | `src/core/evolution/exceptions.py` | 异常定义 |
| 新建 | `src/core/evolution/config.py` | 配置定义 |
| 新建 | `src/core/evolution/evolution_store.py` | 统一存储编排 |
| 新建 | `src/core/evolution/decision_tracker.py` | 决策追踪器 |
| 新建 | `src/core/evolution/outcome_collector.py` | 结果回填收集器 |
| 新建 | `src/core/evolution/decision_log_hook.py` | 决策日志钩子 |
| 修改 | `src/core/base/context.py` | 新增 evolution_engine 属性 |
| 新建 | `src/cli/handlers/evolution_handler.py` | CLI Handler |
| 新建 | `src/cli/commands/evolution.py` | CLI 命令 |
| 修改 | `src/cli/commands/__init__.py` | 注册 evolution_app |
| 修改 | `src/cli/app.py` | 注册 evolution 命令组 |
| 修改 | `src/agents/tools.py` | 新增4个Agent工具 |
| 新建 | `tests/unit/evolution/` | 单元测试目录 |

---

## 5. 风险与应对

| 风险 | 等级 | 应对 |
|------|------|------|
| DecisionLogHook 异常阻断原有Hook逻辑 | 中 | 所有扩展点用 try/except 包裹，异常仅日志记录 |
| Parquet按月分片写入性能 | 低 | 使用 Polars append 模式，避免重写整月文件 |
| runner_state 快照获取失败 | 中 | twin_engine 异常时使用空 dict，不阻断决策记录 |
| 用户反馈稀疏 | 高 | generate_feedback_prompt 主动询问 + 隐式反馈（采纳/忽略）自动记录 |
| 决策日志数据膨胀 | 中 | >12月自动归档压缩；runner_state仅存5维度数值摘要 |

---

## 6. v0.24/v0.25 扩展预留

本实施计划为后续版本预留了扩展点：

| 预留点 | 位置 | v0.24/v0.25 扩展方式 |
|--------|------|----------------------|
| EvolutionEngine 子组件 | `__init__.py` | v0.24 新增 calibration + response_analyzer 属性 |
| EvolutionStore | `evolution_store.py` | v0.24 新增 calibration_profiles.json 读写 |
| EvolutionConfig | `config.py` | v0.24/v0.25 新增校准阈值和进化触发配置 |
| DecisionLogHook | `decision_log_hook.py` | v0.24 在 finalize_content 中注入校准后预测 |
| AppContext | `context.py` | v0.24/v0.25 构建 calibration/response_analyzer/controller |
| CLI 命令 | `evolution.py` | v0.24 新增 calibration/response 命令 |
| Agent 工具 | `tools.py` | v0.24/v0.25 新增对应工具 |
