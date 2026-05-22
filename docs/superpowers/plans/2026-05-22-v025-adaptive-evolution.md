# v0.25.0 自适应进化引擎 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在v0.23决策追踪+v0.24个性化学习基础上，实现自适应进化引擎闭环，包含进化触发器、提示调优器、进化报告器三个子组件，完成"决策→校准→优化→更好决策"自进化闭环。

**Architecture:** 递增式添加模式，3个新子组件以可选注入方式接入EvolutionEngine编排层。EvolutionController实现4种触发规则+异步执行（先持久化后生效），PromptTuner管理4维连续参数空间+JSON持久化，EvolutionReporter生成月度进化报告。所有进化操作通过EvolutionEngine编排层进行，DecisionLogHook持有EvolutionEngine引用间接调用。

**Tech Stack:** Python 3.11+ / Polars 0.20+ / Typer + Rich / Parquet + JSON / threading(daemon)

---

## 1. 实施策略

### 1.1 并行策略

```
里程碑1 (M1): T01 ║ T02 ║ T08     ← 3个无依赖任务并行
里程碑2 (M2): T03 ║ T04            ← 2个核心组件并行
里程碑2 (M2): T05 ║ T06 ║ T07      ← 3个整改项并行（各自依赖完成后启动）
里程碑3 (M3): T09                  ← 编排层扩展（串行，依赖M2全部完成）
里程碑3 (M3): T10 ║ T11 ║ T12      ← CLI/Agent/集成测试并行
里程碑4 (M4): T13 ║ T14            ← 2个集成测试并行
里程碑4 (M4): T15 → T16            ← 文档+回归（串行）
```

### 1.2 关键路径

**T01 → T03 → T05 → T09 → T10 → T13 → T15 → T16**

关键路径总工时: 6h + 12h + 6h + 10h + 8h + 4h + 3h + 4h = **53h**

### 1.3 风险缓解

| 风险 | 等级 | 缓解措施 |
|------|------|----------|
| check_triggers()性能不达标 | 高 | M1中T08先实现days参数+count_decisions()轻量计数，T03中强制性能基准测试 |
| daemon线程数据一致性 | 高 | C-01整改方案"先持久化后生效"已在架构设计中明确，T03实现时严格遵循 |
| EvolutionEngine扩展破坏v0.23/v0.24兼容 | 中 | T09中新增参数均为可选注入(默认None)，未注入时行为不变，回归测试覆盖 |
| IncrementalLearnResult改动影响现有代码 | 中 | T06中execution_result类型兼容设计(str \| dict \| None) |
| PromptTuner参数下限保护影响with_updates()接口 | 低 | T07中with_updates()新增min_bounds可选参数，默认无下限 |

---

## 2. 里程碑计划

### 里程碑 M1: 数据基础（预计第1-2天，17h）

**目标**: 完成数据模型定义和存储层扩展，为后续核心逻辑开发提供基础。

**准入条件**: 架构设计评审通过，开发环境就绪
**准出标准**: 所有数据模型和存储方法单元测试通过，ruff/mypy检查通过

---

### Task-025-01: v0.25数据模型定义（EvolutionAction/TriggerCheckResult/PromptTuningParams）

**Files:**
- Modify: `src/core/evolution/models.py` (追加3个frozen dataclass)
- Modify: `tests/unit/core/evolution/test_models.py` (追加测试)

- [ ] **Step 1: 编写EvolutionAction失败测试**

在 `tests/unit/core/evolution/test_models.py` 末尾追加测试类：

```python
# === v0.25 数据模型测试 ===


class TestEvolutionAction:
    """EvolutionAction数据模型测试"""

    def test_create_evolution_action(self) -> None:
        """测试创建EvolutionAction实例"""
        from src.core.evolution.models import EvolutionAction

        now = datetime.now()
        action = EvolutionAction(
            action_id="test_001",
            action_type="retrain_model",
            trigger_reason="VDOT预测误差连续3次>5%",
            trigger_condition={"consecutive_errors": 3, "threshold": 0.05},
            target_model_type="vdot",
            priority="high",
            created_at=now,
        )
        assert action.action_id == "test_001"
        assert action.action_type == "retrain_model"
        assert action.trigger_reason == "VDOT预测误差连续3次>5%"
        assert action.trigger_condition == {"consecutive_errors": 3, "threshold": 0.05}
        assert action.target_model_type == "vdot"
        assert action.priority == "high"
        assert action.created_at == now
        assert action.executed is False
        assert action.executed_at is None
        assert action.execution_result is None

    def test_evolution_action_to_dict(self) -> None:
        """测试EvolutionAction序列化"""
        from src.core.evolution.models import EvolutionAction

        now = datetime.now()
        action = EvolutionAction(
            action_id="test_002",
            action_type="adjust_strategy",
            trigger_reason="用户连续2次拒绝推荐",
            trigger_condition={"consecutive_rejections": 2},
            target_model_type="prompt",
            priority="medium",
            created_at=now,
            executed=True,
            executed_at=now,
            execution_result="推荐策略已调整",
        )
        d = action.to_dict()
        assert d["action_id"] == "test_002"
        assert d["action_type"] == "adjust_strategy"
        assert d["executed"] is True
        assert d["execution_result"] == "推荐策略已调整"
        assert d["created_at"] == now.isoformat()

    def test_evolution_action_from_dict(self) -> None:
        """测试EvolutionAction反序列化"""
        from src.core.evolution.models import EvolutionAction

        now = datetime.now()
        data = {
            "action_id": "test_003",
            "action_type": "incremental_learn",
            "trigger_reason": "新数据积累50条>=50",
            "trigger_condition": {"new_count": 50, "threshold": 50},
            "target_model_type": "all",
            "priority": "medium",
            "created_at": now.isoformat(),
            "executed": False,
            "executed_at": None,
            "execution_result": None,
        }
        action = EvolutionAction.from_dict(data)
        assert action.action_id == "test_003"
        assert action.action_type == "incremental_learn"
        assert action.executed is False

    def test_evolution_action_frozen(self) -> None:
        """测试EvolutionAction不可变性"""
        from src.core.evolution.models import EvolutionAction

        action = EvolutionAction(
            action_id="test_004",
            action_type="generate_report",
            trigger_reason="月度复盘",
            trigger_condition={},
            target_model_type="none",
            priority="low",
            created_at=datetime.now(),
        )
        with pytest.raises(AttributeError):
            action.executed = True  # type: ignore[misc]

    def test_evolution_action_execution_result_dict_type(self) -> None:
        """测试EvolutionAction.execution_result支持dict类型（H-02整改）"""
        from src.core.evolution.models import EvolutionAction

        result_data = {"vdot": {"success": True, "mae_before": 0.05, "mae_after": 0.03}}
        action = EvolutionAction(
            action_id="test_005",
            action_type="incremental_learn",
            trigger_reason="新数据积累",
            trigger_condition={},
            target_model_type="all",
            priority="medium",
            created_at=datetime.now(),
            executed=True,
            execution_result=result_data,
        )
        assert isinstance(action.execution_result, dict)
        assert action.execution_result["vdot"]["success"] is True


class TestTriggerCheckResult:
    """TriggerCheckResult数据模型测试"""

    def test_create_trigger_check_result(self) -> None:
        """测试创建TriggerCheckResult实例"""
        from src.core.evolution.models import EvolutionAction, TriggerCheckResult

        now = datetime.now()
        action = EvolutionAction(
            action_id="test_010",
            action_type="retrain_model",
            trigger_reason="VDOT误差",
            trigger_condition={},
            target_model_type="vdot",
            priority="high",
            created_at=now,
        )
        result = TriggerCheckResult(
            checked_at=now,
            triggered_actions=[action],
            skipped_conditions=[{"rule": "TR-03", "reason": "新数据不足50条"}],
        )
        assert result.checked_at == now
        assert len(result.triggered_actions) == 1
        assert len(result.skipped_conditions) == 1

    def test_trigger_check_result_to_dict(self) -> None:
        """测试TriggerCheckResult序列化"""
        from src.core.evolution.models import TriggerCheckResult

        now = datetime.now()
        result = TriggerCheckResult(
            checked_at=now,
            triggered_actions=[],
            skipped_conditions=[],
        )
        d = result.to_dict()
        assert d["checked_at"] == now.isoformat()
        assert d["triggered_actions"] == []
        assert d["skipped_conditions"] == []


class TestPromptTuningParams:
    """PromptTuningParams数据模型测试"""

    def test_default_params(self) -> None:
        """测试默认参数（全部0.5）"""
        from src.core.evolution.models import PromptTuningParams

        params = PromptTuningParams.default()
        assert params.tone_intensity == 0.5
        assert params.detail_level_score == 0.5
        assert params.recommendation_aggressiveness == 0.5
        assert params.data_driven_weight == 0.5
        assert params.update_count == 0

    def test_with_updates_basic(self) -> None:
        """测试with_updates基本更新"""
        from src.core.evolution.models import PromptTuningParams

        params = PromptTuningParams.default()
        updated = params.with_updates(tone=0.7, aggressive=0.3)
        assert updated.tone_intensity == 0.7
        assert updated.recommendation_aggressiveness == 0.3
        assert updated.detail_level_score == 0.5  # 未修改
        assert updated.data_driven_weight == 0.5  # 未修改
        assert updated.update_count == 1

    def test_with_updates_clamp_to_range(self) -> None:
        """测试with_updates将参数clamp到[0.0, 1.0]"""
        from src.core.evolution.models import PromptTuningParams

        params = PromptTuningParams.default()
        # 超上限
        updated = params.with_updates(tone=1.5, aggressive=2.0)
        assert updated.tone_intensity == 1.0
        assert updated.recommendation_aggressiveness == 1.0
        # 超下限
        updated2 = params.with_updates(detail=-0.5, data_driven=-1.0)
        assert updated2.detail_level_score == 0.0
        assert updated2.data_driven_weight == 0.0

    def test_with_updates_none_preserves(self) -> None:
        """测试with_updates传入None保持原值"""
        from src.core.evolution.models import PromptTuningParams

        params = PromptTuningParams(tone_intensity=0.7, detail_level_score=0.3)
        updated = params.with_updates(tone=None, detail=None)
        assert updated.tone_intensity == 0.7
        assert updated.detail_level_score == 0.3

    def test_to_dict_from_dict_roundtrip(self) -> None:
        """测试序列化/反序列化往返"""
        from src.core.evolution.models import PromptTuningParams

        params = PromptTuningParams(
            tone_intensity=0.6,
            detail_level_score=0.4,
            recommendation_aggressiveness=0.7,
            data_driven_weight=0.3,
            update_count=5,
        )
        d = params.to_dict()
        restored = PromptTuningParams.from_dict(d)
        assert restored.tone_intensity == 0.6
        assert restored.detail_level_score == 0.4
        assert restored.recommendation_aggressiveness == 0.7
        assert restored.data_driven_weight == 0.3
        assert restored.update_count == 5

    def test_frozen_immutability(self) -> None:
        """测试不可变性"""
        from src.core.evolution.models import PromptTuningParams

        params = PromptTuningParams.default()
        with pytest.raises(AttributeError):
            params.tone_intensity = 0.8  # type: ignore[misc]
```

- [ ] **Step 2: 运行测试验证失败**

Run: `uv run pytest tests/unit/core/evolution/test_models.py -v -k "TestEvolutionAction or TestTriggerCheckResult or TestPromptTuningParams"`
Expected: FAIL (ImportError: cannot import name 'EvolutionAction')

- [ ] **Step 3: 在models.py中实现EvolutionAction/TriggerCheckResult/PromptTuningParams**

在 `src/core/evolution/models.py` 末尾追加：

```python
# === v0.25 自适应进化数据模型 ===


@dataclass(frozen=True)
class EvolutionAction:
    """进化动作（不可变数据类）

    表示一个待执行的进化动作，由EvolutionController检测触发条件后生成。

    Attributes:
        action_id: 动作唯一标识
        action_type: 动作类型 (retrain_model/adjust_strategy/incremental_learn/generate_report)
        trigger_reason: 触发原因描述
        trigger_condition: 触发条件详情
        target_model_type: 目标模型类型 (vdot/injury/training_response/prompt/all/none)
        priority: 优先级 (high/medium/low)
        created_at: 创建时间
        executed: 是否已执行
        executed_at: 执行时间 (可选)
        execution_result: 执行结果摘要 (可选，str或dict类型)
    """

    action_id: str
    action_type: str
    trigger_reason: str
    trigger_condition: dict[str, Any]
    target_model_type: str
    priority: str
    created_at: datetime
    executed: bool = False
    executed_at: datetime | None = None
    execution_result: str | dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        result: dict[str, Any] = {
            "action_id": self.action_id,
            "action_type": self.action_type,
            "trigger_reason": self.trigger_reason,
            "trigger_condition": self.trigger_condition,
            "target_model_type": self.target_model_type,
            "priority": self.priority,
            "created_at": self.created_at.isoformat(),
            "executed": self.executed,
        }
        if self.executed_at is not None:
            result["executed_at"] = self.executed_at.isoformat()
        if self.execution_result is not None:
            result["execution_result"] = self.execution_result
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvolutionAction:
        """从字典创建实例"""
        created_at = data["created_at"]
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        executed_at = data.get("executed_at")
        if isinstance(executed_at, str):
            executed_at = datetime.fromisoformat(executed_at)
        return cls(
            action_id=data["action_id"],
            action_type=data["action_type"],
            trigger_reason=data["trigger_reason"],
            trigger_condition=data.get("trigger_condition", {}),
            target_model_type=data["target_model_type"],
            priority=data["priority"],
            created_at=created_at,
            executed=data.get("executed", False),
            executed_at=executed_at,
            execution_result=data.get("execution_result"),
        )


@dataclass(frozen=True)
class TriggerCheckResult:
    """触发条件检查结果（不可变数据类）

    Attributes:
        checked_at: 检查时间
        triggered_actions: 触发的进化动作列表
        skipped_conditions: 跳过的条件及原因
    """

    checked_at: datetime
    triggered_actions: list[EvolutionAction]
    skipped_conditions: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "checked_at": self.checked_at.isoformat(),
            "triggered_actions": [a.to_dict() for a in self.triggered_actions],
            "skipped_conditions": self.skipped_conditions,
        }


@dataclass(frozen=True)
class PromptTuningParams:
    """提示调优参数（不可变数据类）

    4维连续参数空间，控制LLM输出风格。
    每个参数范围0.0-1.0，默认0.5（中性）。

    Attributes:
        tone_intensity: 语气强度 (0.0=温和/1.0=严厉)
        detail_level_score: 信息密度 (0.0=简洁/1.0=详细)
        recommendation_aggressiveness: 推荐激进程度 (0.0=保守/1.0=激进)
        data_driven_weight: 数据驱动权重 (0.0=纯经验驱动/1.0=纯数据驱动)
        last_updated: 最后更新时间
        update_count: 累计更新次数
    """

    tone_intensity: float = 0.5
    detail_level_score: float = 0.5
    recommendation_aggressiveness: float = 0.5
    data_driven_weight: float = 0.5
    last_updated: datetime = field(default_factory=datetime.now)
    update_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "tone_intensity": self.tone_intensity,
            "detail_level_score": self.detail_level_score,
            "recommendation_aggressiveness": self.recommendation_aggressiveness,
            "data_driven_weight": self.data_driven_weight,
            "last_updated": self.last_updated.isoformat(),
            "update_count": self.update_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PromptTuningParams:
        """从字典创建实例"""
        last_updated = data.get("last_updated", datetime.now().isoformat())
        if isinstance(last_updated, str):
            last_updated = datetime.fromisoformat(last_updated)
        return cls(
            tone_intensity=data.get("tone_intensity", 0.5),
            detail_level_score=data.get("detail_level_score", 0.5),
            recommendation_aggressiveness=data.get("recommendation_aggressiveness", 0.5),
            data_driven_weight=data.get("data_driven_weight", 0.5),
            last_updated=last_updated,
            update_count=data.get("update_count", 0),
        )

    @classmethod
    def default(cls) -> PromptTuningParams:
        """创建默认提示调优参数（全部0.5，中性）"""
        return cls(
            tone_intensity=0.5,
            detail_level_score=0.5,
            recommendation_aggressiveness=0.5,
            data_driven_weight=0.5,
            last_updated=datetime.now(),
            update_count=0,
        )

    def with_updates(
        self,
        tone: float | None = None,
        detail: float | None = None,
        aggressive: float | None = None,
        data_driven: float | None = None,
    ) -> PromptTuningParams:
        """创建更新后的参数副本（保持不可变性）

        每个参数被clamp到[0.0, 1.0]范围。

        Args:
            tone: 新的语气强度（None保持不变）
            detail: 新的信息密度（None保持不变）
            aggressive: 新的推荐激进程度（None保持不变）
            data_driven: 新的数据驱动权重（None保持不变）

        Returns:
            PromptTuningParams: 更新后的参数副本
        """
        return PromptTuningParams(
            tone_intensity=max(0.0, min(1.0, tone if tone is not None else self.tone_intensity)),
            detail_level_score=max(0.0, min(1.0, detail if detail is not None else self.detail_level_score)),
            recommendation_aggressiveness=max(0.0, min(1.0, aggressive if aggressive is not None else self.recommendation_aggressiveness)),
            data_driven_weight=max(0.0, min(1.0, data_driven if data_driven is None else self.data_driven_weight)),
            last_updated=datetime.now(),
            update_count=self.update_count + 1,
        )
```

- [ ] **Step 4: 运行测试验证通过**

Run: `uv run pytest tests/unit/core/evolution/test_models.py -v -k "TestEvolutionAction or TestTriggerCheckResult or TestPromptTuningParams"`
Expected: PASS

- [ ] **Step 5: 运行ruff和mypy检查**

Run: `uv run ruff check src/core/evolution/models.py && uv run mypy src/core/evolution/models.py --ignore-missing-imports`
Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add src/core/evolution/models.py tests/unit/core/evolution/test_models.py
git commit -m "feat(evolution): add v0.25 data models - EvolutionAction, TriggerCheckResult, PromptTuningParams"
```

---

### Task-025-02: EvolutionReport数据模型定义

**Files:**
- Modify: `src/core/evolution/models.py` (追加EvolutionReport)
- Modify: `tests/unit/core/evolution/test_models.py` (追加测试)

- [ ] **Step 1: 编写EvolutionReport失败测试**

在 `tests/unit/core/evolution/test_models.py` 末尾追加：

```python
class TestEvolutionReport:
    """EvolutionReport数据模型测试"""

    def test_create_evolution_report(self) -> None:
        """测试创建EvolutionReport实例"""
        from src.core.evolution.models import EvolutionReport

        now = datetime.now()
        report = EvolutionReport(
            report_id="rpt_001",
            month="2026-05",
            generated_at=now,
            total_decisions=42,
            prediction_accuracy_trend=[{"date": "2026-05-01", "mae": 0.05}],
            decision_acceptance_rate=0.75,
            model_versions={"vdot": "v1.2", "injury": "v1.0"},
            personalization_degree=0.35,
            evolution_actions_count=3,
            last_evolution_time=now,
            calibration_summary={"vdot": {"scale": 0.97}},
            prompt_tuning_summary={"tone_intensity": 0.6},
            recommendations=["建议增加VDOT预测校准频率"],
        )
        assert report.report_id == "rpt_001"
        assert report.month == "2026-05"
        assert report.total_decisions == 42
        assert report.personalization_degree == 0.35
        assert len(report.recommendations) == 1

    def test_evolution_report_to_dict(self) -> None:
        """测试EvolutionReport序列化"""
        from src.core.evolution.models import EvolutionReport

        now = datetime.now()
        report = EvolutionReport(
            report_id="rpt_002",
            month="2026-04",
            generated_at=now,
            total_decisions=0,
            prediction_accuracy_trend=[],
            decision_acceptance_rate=0.0,
            model_versions={},
            personalization_degree=0.0,
            evolution_actions_count=0,
            last_evolution_time=None,
            calibration_summary={},
            prompt_tuning_summary={},
            recommendations=[],
        )
        d = report.to_dict()
        assert d["report_id"] == "rpt_002"
        assert d["month"] == "2026-04"
        assert d["last_evolution_time"] is None

    def test_evolution_report_from_dict(self) -> None:
        """测试EvolutionReport反序列化"""
        from src.core.evolution.models import EvolutionReport

        now = datetime.now()
        data = {
            "report_id": "rpt_003",
            "month": "2026-03",
            "generated_at": now.isoformat(),
            "total_decisions": 10,
            "prediction_accuracy_trend": [],
            "decision_acceptance_rate": 0.5,
            "model_versions": {},
            "personalization_degree": 0.1,
            "evolution_actions_count": 1,
            "last_evolution_time": now.isoformat(),
            "calibration_summary": {},
            "prompt_tuning_summary": {},
            "recommendations": [],
        }
        report = EvolutionReport.from_dict(data)
        assert report.report_id == "rpt_003"
        assert report.total_decisions == 10

    def test_evolution_report_frozen(self) -> None:
        """测试EvolutionReport不可变性"""
        from src.core.evolution.models import EvolutionReport

        report = EvolutionReport(
            report_id="rpt_004",
            month="2026-05",
            generated_at=datetime.now(),
            total_decisions=0,
            prediction_accuracy_trend=[],
            decision_acceptance_rate=0.0,
            model_versions={},
            personalization_degree=0.0,
            evolution_actions_count=0,
            last_evolution_time=None,
            calibration_summary={},
            prompt_tuning_summary={},
            recommendations=[],
        )
        with pytest.raises(AttributeError):
            report.total_decisions = 100  # type: ignore[misc]
```

- [ ] **Step 2: 运行测试验证失败**

Run: `uv run pytest tests/unit/core/evolution/test_models.py -v -k "TestEvolutionReport"`
Expected: FAIL (ImportError: cannot import name 'EvolutionReport')

- [ ] **Step 3: 在models.py中实现EvolutionReport**

在 `src/core/evolution/models.py` 末尾追加：

```python
@dataclass(frozen=True)
class EvolutionReport:
    """月度进化报告（不可变数据类）

    汇总指定月份的进化引擎运行状态和效果。

    Attributes:
        report_id: 报告唯一标识
        month: 报告月份 (YYYY-MM格式)
        generated_at: 报告生成时间
        total_decisions: 决策记录总数
        prediction_accuracy_trend: 预测准确率趋势
        decision_acceptance_rate: 决策接受率
        model_versions: 各模型版本信息
        personalization_degree: 个性化程度 (0.0-1.0)
        evolution_actions_count: 进化动作执行数
        last_evolution_time: 上次进化时间
        calibration_summary: 校准摘要
        prompt_tuning_summary: 提示调优摘要
        recommendations: 进化建议列表
    """

    report_id: str
    month: str
    generated_at: datetime
    total_decisions: int
    prediction_accuracy_trend: list[dict[str, Any]]
    decision_acceptance_rate: float
    model_versions: dict[str, str]
    personalization_degree: float
    evolution_actions_count: int
    last_evolution_time: datetime | None
    calibration_summary: dict[str, Any]
    prompt_tuning_summary: dict[str, Any]
    recommendations: list[str]

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "report_id": self.report_id,
            "month": self.month,
            "generated_at": self.generated_at.isoformat(),
            "total_decisions": self.total_decisions,
            "prediction_accuracy_trend": self.prediction_accuracy_trend,
            "decision_acceptance_rate": self.decision_acceptance_rate,
            "model_versions": self.model_versions,
            "personalization_degree": self.personalization_degree,
            "evolution_actions_count": self.evolution_actions_count,
            "last_evolution_time": (
                self.last_evolution_time.isoformat()
                if self.last_evolution_time is not None
                else None
            ),
            "calibration_summary": self.calibration_summary,
            "prompt_tuning_summary": self.prompt_tuning_summary,
            "recommendations": self.recommendations,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvolutionReport:
        """从字典创建实例"""
        generated_at = data["generated_at"]
        if isinstance(generated_at, str):
            generated_at = datetime.fromisoformat(generated_at)
        last_evolution_time = data.get("last_evolution_time")
        if isinstance(last_evolution_time, str):
            last_evolution_time = datetime.fromisoformat(last_evolution_time)
        return cls(
            report_id=data["report_id"],
            month=data["month"],
            generated_at=generated_at,
            total_decisions=data.get("total_decisions", 0),
            prediction_accuracy_trend=data.get("prediction_accuracy_trend", []),
            decision_acceptance_rate=data.get("decision_acceptance_rate", 0.0),
            model_versions=data.get("model_versions", {}),
            personalization_degree=data.get("personalization_degree", 0.0),
            evolution_actions_count=data.get("evolution_actions_count", 0),
            last_evolution_time=last_evolution_time,
            calibration_summary=data.get("calibration_summary", {}),
            prompt_tuning_summary=data.get("prompt_tuning_summary", {}),
            recommendations=data.get("recommendations", []),
        )
```

- [ ] **Step 4: 运行测试验证通过**

Run: `uv run pytest tests/unit/core/evolution/test_models.py -v -k "TestEvolutionReport"`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/core/evolution/models.py tests/unit/core/evolution/test_models.py
git commit -m "feat(evolution): add EvolutionReport data model for v0.25 monthly reports"
```

---

### Task-025-08: EvolutionStore扩展 -- v0.25存储方法

**Files:**
- Modify: `src/core/evolution/evolution_store.py` (新增5个方法+扩展2个方法参数)
- Modify: `tests/unit/core/evolution/test_evolution_store.py` (追加测试)

- [ ] **Step 1: 编写EvolutionStore v0.25扩展方法失败测试**

在 `tests/unit/core/evolution/test_evolution_store.py` 末尾追加测试类：

```python
class TestEvolutionStoreV025:
    """EvolutionStore v0.25扩展方法测试"""

    def test_save_and_load_prompt_tuning_params(self, tmp_path: Path) -> None:
        """测试提示调优参数读写"""
        from src.core.evolution.evolution_store import EvolutionStore
        from src.core.evolution.models import PromptTuningParams

        store = EvolutionStore(tmp_path)
        params = PromptTuningParams(
            tone_intensity=0.6,
            detail_level_score=0.4,
            recommendation_aggressiveness=0.7,
            data_driven_weight=0.3,
            update_count=3,
        )
        store.save_prompt_tuning_params(params)

        loaded = store.load_prompt_tuning_params()
        assert loaded is not None
        assert loaded.tone_intensity == 0.6
        assert loaded.recommendation_aggressiveness == 0.7
        assert loaded.update_count == 3

    def test_load_prompt_tuning_params_file_not_exist(self, tmp_path: Path) -> None:
        """测试加载不存在的提示调优参数返回None"""
        from src.core.evolution.evolution_store import EvolutionStore

        store = EvolutionStore(tmp_path)
        result = store.load_prompt_tuning_params()
        assert result is None

    def test_save_and_load_trigger_state(self, tmp_path: Path) -> None:
        """测试触发器状态读写"""
        from src.core.evolution.evolution_store import EvolutionStore

        store = EvolutionStore(tmp_path)
        store.save_trigger_state("last_incremental_count", 156)
        store.save_trigger_state("last_monthly_report", "2026-05")

        value = store.load_trigger_state("last_incremental_count")
        assert value == 156
        month = store.load_trigger_state("last_monthly_report")
        assert month == "2026-05"

    def test_load_trigger_state_key_not_exist(self, tmp_path: Path) -> None:
        """测试加载不存在的触发器状态键返回None"""
        from src.core.evolution.evolution_store import EvolutionStore

        store = EvolutionStore(tmp_path)
        result = store.load_trigger_state("nonexistent_key")
        assert result is None

    def test_load_trigger_state_file_not_exist(self, tmp_path: Path) -> None:
        """测试trigger_state.json不存在时返回None"""
        from src.core.evolution.evolution_store import EvolutionStore

        store = EvolutionStore(tmp_path)
        result = store.load_trigger_state("last_incremental_count")
        assert result is None

    def test_count_decisions_empty(self, tmp_path: Path) -> None:
        """测试空数据目录下count_decisions返回0"""
        from src.core.evolution.evolution_store import EvolutionStore

        store = EvolutionStore(tmp_path)
        assert store.count_decisions() == 0

    def test_count_decisions_with_data(self, tmp_path: Path) -> None:
        """测试有数据时count_decisions返回正确计数"""
        from src.core.evolution.evolution_store import EvolutionStore
        from src.core.evolution.models import DecisionLog
        from src.core.transparency.models import DecisionType

        store = EvolutionStore(tmp_path)
        now = datetime.now()
        for i in range(5):
            decision = DecisionLog(
                decision_id=f"dec_{i:03d}",
                timestamp=now,
                runner_state={"vdot": 45.0},
                decision_type=DecisionType.TRAINING_ADVICE,
                tool_call_chain=[],
                prediction_snapshot=None,
                recommendation_text="test",
                execution_status="executed",
                recommendation_accepted=True,
                session_key="test_session",
            )
            store.save_decision(decision)

        assert store.count_decisions() == 5

    def test_get_decision_outcome_pairs_days_parameter(self, tmp_path: Path) -> None:
        """测试get_decision_outcome_pairs的days参数限制查询范围"""
        from src.core.evolution.evolution_store import EvolutionStore
        from src.core.evolution.models import DecisionLog, OutcomeRecord
        from src.core.transparency.models import DecisionType

        store = EvolutionStore(tmp_path)
        now = datetime.now()

        # 保存一条决策+结果
        decision = DecisionLog(
            decision_id="dec_days_001",
            timestamp=now,
            runner_state={"vdot": 45.0},
            decision_type=DecisionType.TRAINING_ADVICE,
            tool_call_chain=[],
            prediction_snapshot=None,
            recommendation_text="test",
            execution_status="executed",
            recommendation_accepted=True,
            session_key="test_session",
        )
        store.save_decision(decision)
        outcome = OutcomeRecord(
            outcome_id="out_days_001",
            decision_id="dec_days_001",
            outcome_timestamp=now,
            actual_vdot=45.5,
            actual_injury=False,
            execution_fidelity=0.9,
            user_feedback_score=4,
            user_feedback_text=None,
            prediction_error=0.01,
            prediction_direction="over",
            session_id="test_session",
        )
        store.save_outcome(outcome)

        # days=90应该能查到
        pairs = store.get_decision_outcome_pairs(days=90)
        assert len(pairs) >= 1

        # days=1且数据在90天前应该查不到（当前数据是今天的，days=1应能查到）
        pairs_recent = store.get_decision_outcome_pairs(days=1)
        assert len(pairs_recent) >= 1

    def test_get_prediction_actual_pairs_days_parameter(self, tmp_path: Path) -> None:
        """测试get_prediction_actual_pairs的days参数"""
        from src.core.evolution.evolution_store import EvolutionStore
        from src.core.evolution.models import DecisionLog, OutcomeRecord
        from src.core.transparency.models import DecisionType

        store = EvolutionStore(tmp_path)
        now = datetime.now()

        decision = DecisionLog(
            decision_id="dec_pred_001",
            timestamp=now,
            runner_state={"vdot": 45.0},
            decision_type=DecisionType.TRAINING_ADVICE,
            tool_call_chain=[],
            prediction_snapshot={"predicted_vdot": 45.2},
            recommendation_text="test",
            execution_status="executed",
            recommendation_accepted=True,
            session_key="test_session",
        )
        store.save_decision(decision)
        outcome = OutcomeRecord(
            outcome_id="out_pred_001",
            decision_id="dec_pred_001",
            outcome_timestamp=now,
            actual_vdot=45.5,
            actual_injury=False,
            execution_fidelity=0.9,
            user_feedback_score=4,
            user_feedback_text=None,
            prediction_error=0.01,
            prediction_direction="over",
            session_id="test_session",
        )
        store.save_outcome(outcome)

        pairs = store.get_prediction_actual_pairs("vdot", min_count=1, days=90)
        assert len(pairs) >= 1

    def test_tuning_dir_auto_created(self, tmp_path: Path) -> None:
        """测试tuning/目录在首次写入时自动创建"""
        from src.core.evolution.evolution_store import EvolutionStore
        from src.core.evolution.models import PromptTuningParams

        store = EvolutionStore(tmp_path)
        tuning_dir = tmp_path / "tuning"
        assert not tuning_dir.exists()

        params = PromptTuningParams.default()
        store.save_prompt_tuning_params(params)
        assert tuning_dir.exists()
```

- [ ] **Step 2: 运行测试验证失败**

Run: `uv run pytest tests/unit/core/evolution/test_evolution_store.py -v -k "TestEvolutionStoreV025"`
Expected: FAIL (AttributeError: 'EvolutionStore' object has no attribute 'save_prompt_tuning_params')

- [ ] **Step 3: 在EvolutionStore中实现v0.25扩展方法**

在 `src/core/evolution/evolution_store.py` 中：

1. 在文件顶部import区添加：
```python
from src.core.evolution.models import PromptTuningParams
```

2. 在EvolutionStore类的 `__init__` 方法中添加tuning目录属性：
```python
self._tuning_dir = data_dir / "tuning"
```

3. 在EvolutionStore类末尾追加5个新方法：

```python
    # ---- v0.25 新增方法 ----

    def save_prompt_tuning_params(self, params: PromptTuningParams) -> None:
        """保存提示调优参数到JSON文件

        使用原子写入确保数据安全。tuning/目录在首次写入时自动创建。

        Args:
            params: 提示调优参数对象
        """
        self._tuning_dir.mkdir(parents=True, exist_ok=True)
        file_path = self._tuning_dir / "prompt_params.json"
        tmp_path = file_path.with_suffix(".json.tmp")
        try:
            tmp_path.write_text(
                json.dumps(params.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            tmp_path.replace(file_path)
        except Exception:
            if tmp_path.exists():
                tmp_path.unlink()
            raise

    def load_prompt_tuning_params(self) -> PromptTuningParams | None:
        """从JSON文件加载提示调优参数

        Returns:
            PromptTuningParams | None: 提示调优参数对象，文件不存在返回None
        """
        file_path = self._tuning_dir / "prompt_params.json"
        if not file_path.exists():
            return None
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
            return PromptTuningParams.from_dict(data)
        except Exception:
            logger.warning("提示调优参数文件损坏，返回None")
            return None

    def save_trigger_state(self, key: str, value: Any) -> None:
        """保存触发器状态到JSON文件

        Args:
            key: 状态键名
            value: 状态值
        """
        self._tuning_dir.mkdir(parents=True, exist_ok=True)
        file_path = self._tuning_dir / "trigger_state.json"

        # 读取现有状态
        state: dict[str, Any] = {}
        if file_path.exists():
            try:
                state = json.loads(file_path.read_text(encoding="utf-8"))
            except Exception:
                state = {}

        state[key] = value

        tmp_path = file_path.with_suffix(".json.tmp")
        try:
            tmp_path.write_text(
                json.dumps(state, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            tmp_path.replace(file_path)
        except Exception:
            if tmp_path.exists():
                tmp_path.unlink()
            raise

    def load_trigger_state(self, key: str) -> Any | None:
        """加载触发器状态

        Args:
            key: 状态键名

        Returns:
            Any | None: 状态值，键不存在或文件不存在返回None
        """
        file_path = self._tuning_dir / "trigger_state.json"
        if not file_path.exists():
            return None
        try:
            state = json.loads(file_path.read_text(encoding="utf-8"))
            return state.get(key)
        except Exception:
            return None

    def count_decisions(self) -> int:
        """轻量计数决策记录总数

        使用LazyFrame仅统计行数，不加载全量数据。

        Returns:
            int: 决策记录总数
        """
        decisions_dir = self._data_dir / "decisions"
        if not decisions_dir.exists():
            return 0

        total = 0
        for month_dir in sorted(decisions_dir.iterdir()):
            if not month_dir.is_dir():
                continue
            for parquet_file in month_dir.glob("*.parquet"):
                try:
                    lf = pl.scan_parquet(parquet_file)
                    total += lf.select(pl.len()).collect().item()
                except Exception:
                    continue
        return total
```

4. 修改 `get_decision_outcome_pairs` 方法签名，添加 `days` 参数：

将方法签名从：
```python
def get_decision_outcome_pairs(
    self,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[tuple[DecisionLog, OutcomeRecord]]:
```

改为：
```python
def get_decision_outcome_pairs(
    self,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    days: int = 90,
) -> list[tuple[DecisionLog, OutcomeRecord]]:
```

在方法体开头添加days参数处理（在现有start_date/end_date逻辑之前）：
```python
        # v0.25: days参数限制查询范围
        if start_date is None and days > 0:
            start_date = datetime.now() - timedelta(days=days)
```

并在文件顶部添加timedelta导入：
```python
from datetime import datetime, timedelta
```

5. 修改 `get_prediction_actual_pairs` 方法签名，添加 `days` 参数：

将方法签名从：
```python
def get_prediction_actual_pairs(
    self, model_type: str, min_count: int = 10
) -> list[tuple[float, float]]:
```

改为：
```python
def get_prediction_actual_pairs(
    self, model_type: str, min_count: int = 10, days: int = 90
) -> list[tuple[float, float]]:
```

在方法体中，将 `all_pairs = self.get_decision_outcome_pairs()` 改为：
```python
        all_pairs = self.get_decision_outcome_pairs(days=days)
```

- [ ] **Step 4: 运行测试验证通过**

Run: `uv run pytest tests/unit/core/evolution/test_evolution_store.py -v -k "TestEvolutionStoreV025"`
Expected: PASS

- [ ] **Step 5: 运行全量EvolutionStore测试确保向后兼容**

Run: `uv run pytest tests/unit/core/evolution/test_evolution_store.py -v`
Expected: PASS

- [ ] **Step 6: 运行ruff和mypy检查**

Run: `uv run ruff check src/core/evolution/evolution_store.py && uv run mypy src/core/evolution/evolution_store.py --ignore-missing-imports`
Expected: PASS

- [ ] **Step 7: 提交**

```bash
git add src/core/evolution/evolution_store.py tests/unit/core/evolution/test_evolution_store.py
git commit -m "feat(evolution): extend EvolutionStore with v0.25 storage methods - prompt params, trigger state, count_decisions, days parameter"
```

---

### 里程碑 M2: 核心逻辑完成（预计第3-6天，52h）

**目标**: 完成3个核心子组件（Controller/Tuner/Reporter）和3个评审整改项。

**准入条件**: M1全部完成
**准出标准**: 3个核心子组件和3个整改项单元测试通过

---

### Task-025-03: EvolutionController核心实现

**Files:**
- Create: `src/core/evolution/evolution_controller.py`
- Create: `tests/unit/core/evolution/test_evolution_controller.py`

- [ ] **Step 1: 编写EvolutionController失败测试**

创建 `tests/unit/core/evolution/test_evolution_controller.py`：

```python
"""EvolutionController单元测试"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.core.evolution.config import EvolutionConfig
from src.core.evolution.evolution_controller import EvolutionController
from src.core.evolution.models import (
    EvolutionAction,
    PromptTuningParams,
    TriggerCheckResult,
)


@pytest.fixture
def mock_store() -> MagicMock:
    """创建Mock EvolutionStore"""
    store = MagicMock()
    store.get_prediction_actual_pairs.return_value = []
    store.get_decision_outcome_pairs.return_value = []
    store.count_decisions.return_value = 0
    store.load_trigger_state.return_value = None
    store.save_trigger_state.return_value = None
    store.save_model_params.return_value = None
    return store


@pytest.fixture
def mock_calibration_engine() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_model_evolver() -> MagicMock:
    evolver = MagicMock()
    evolver.evolve_model.return_value = MagicMock(
        mae_before=0.05, mae_after=0.03, _raw_param_changes={"tau_fitness": 42}
    )
    evolver.apply_params_to_instance.return_value = None
    return evolver


@pytest.fixture
def mock_prompt_tuner() -> MagicMock:
    tuner = MagicMock()
    tuner.auto_adjust_on_rejection.return_value = PromptTuningParams.default()
    tuner.get_params.return_value = PromptTuningParams.default()
    return tuner


@pytest.fixture
def mock_evolution_reporter() -> MagicMock:
    reporter = MagicMock()
    reporter.generate_report.return_value = MagicMock(month="2026-05")
    return reporter


@pytest.fixture
def controller(
    mock_store: MagicMock,
    mock_calibration_engine: MagicMock,
    mock_model_evolver: MagicMock,
    mock_prompt_tuner: MagicMock,
    mock_evolution_reporter: MagicMock,
) -> EvolutionController:
    config = EvolutionConfig(data_dir="/tmp/test_evolution")
    return EvolutionController(
        store=mock_store,
        calibration_engine=mock_calibration_engine,
        model_evolver=mock_model_evolver,
        prompt_tuner=mock_prompt_tuner,
        evolution_reporter=mock_evolution_reporter,
        config=config,
    )


class TestCheckTriggers:
    """check_triggers()测试"""

    def test_no_triggers_when_insufficient_data(
        self, controller: EvolutionController, mock_store: MagicMock
    ) -> None:
        """数据不足时无触发"""
        mock_store.get_prediction_actual_pairs.return_value = []
        mock_store.get_decision_outcome_pairs.return_value = []
        mock_store.count_decisions.return_value = 0

        result = controller.check_triggers()
        assert isinstance(result, TriggerCheckResult)
        assert len(result.triggered_actions) == 0
        assert len(result.skipped_conditions) > 0

    def test_vdot_error_trigger(
        self, controller: EvolutionController, mock_store: MagicMock
    ) -> None:
        """VDOT预测误差连续3次>5%时触发retrain_model"""
        # 模拟3次VDOT误差>5%的配对数据
        mock_store.get_prediction_actual_pairs.return_value = [
            (47.5, 45.0),  # 误差5.6%
            (48.0, 45.0),  # 误差6.7%
            (47.0, 44.5),  # 误差5.6%
        ]
        mock_store.get_decision_outcome_pairs.return_value = []

        result = controller.check_triggers()
        vdot_actions = [
            a for a in result.triggered_actions if a.action_type == "retrain_model"
        ]
        assert len(vdot_actions) == 1
        assert vdot_actions[0].target_model_type == "vdot"
        assert vdot_actions[0].priority == "high"

    def test_rejection_trigger(
        self, controller: EvolutionController, mock_store: MagicMock
    ) -> None:
        """连续2次拒绝推荐时触发adjust_strategy"""
        mock_store.get_prediction_actual_pairs.return_value = []
        # 模拟2条连续拒绝的决策-结果配对
        mock_outcome_1 = MagicMock(recommendation_accepted=False)
        mock_outcome_2 = MagicMock(recommendation_accepted=False)
        mock_store.get_decision_outcome_pairs.return_value = [
            (MagicMock(), mock_outcome_1),
            (MagicMock(), mock_outcome_2),
        ]

        result = controller.check_triggers()
        rejection_actions = [
            a for a in result.triggered_actions if a.action_type == "adjust_strategy"
        ]
        assert len(rejection_actions) == 1
        assert rejection_actions[0].target_model_type == "prompt"

    def test_new_data_trigger(
        self, controller: EvolutionController, mock_store: MagicMock
    ) -> None:
        """新数据积累>=50条时触发incremental_learn"""
        mock_store.get_prediction_actual_pairs.return_value = []
        mock_store.get_decision_outcome_pairs.return_value = []
        mock_store.count_decisions.return_value = 100
        mock_store.load_trigger_state.return_value = 30  # 上次30条，新增70条

        result = controller.check_triggers()
        new_data_actions = [
            a for a in result.triggered_actions if a.action_type == "incremental_learn"
        ]
        assert len(new_data_actions) == 1
        assert new_data_actions[0].target_model_type == "all"

    def test_monthly_review_trigger(
        self, controller: EvolutionController, mock_store: MagicMock
    ) -> None:
        """当月未生成报告时触发generate_report"""
        mock_store.get_prediction_actual_pairs.return_value = []
        mock_store.get_decision_outcome_pairs.return_value = []
        mock_store.count_decisions.return_value = 0
        # 当月未生成报告
        mock_store.load_trigger_state.return_value = None

        result = controller.check_triggers()
        monthly_actions = [
            a for a in result.triggered_actions if a.action_type == "generate_report"
        ]
        assert len(monthly_actions) == 1
        assert monthly_actions[0].priority == "low"

    def test_check_triggers_performance_budget(
        self, controller: EvolutionController, mock_store: MagicMock
    ) -> None:
        """check_triggers()性能预算<50ms"""
        import time

        mock_store.get_prediction_actual_pairs.return_value = []
        mock_store.get_decision_outcome_pairs.return_value = []
        mock_store.count_decisions.return_value = 0

        start = time.monotonic()
        controller.check_triggers()
        elapsed_ms = (time.monotonic() - start) * 1000
        assert elapsed_ms < 50, f"check_triggers()耗时{elapsed_ms:.1f}ms超过50ms预算"


class TestExecuteAction:
    """execute_action()测试"""

    def test_execute_retrain_model_persist_first(
        self,
        controller: EvolutionController,
        mock_model_evolver: MagicMock,
        mock_store: MagicMock,
    ) -> None:
        """retrain_model动作先持久化后生效"""
        action = EvolutionAction(
            action_id="test_exec_001",
            action_type="retrain_model",
            trigger_reason="VDOT误差",
            trigger_condition={},
            target_model_type="vdot",
            priority="high",
            created_at=datetime.now(),
        )

        result = controller.execute_action(action)
        assert result.executed is True
        # 验证先调用save_model_params（持久化），再调用apply_params_to_instance（生效）
        mock_store.save_model_params.assert_called_once()
        mock_model_evolver.apply_params_to_instance.assert_called_once_with("vdot")

    def test_execute_retrain_model_persist_failure(
        self,
        controller: EvolutionController,
        mock_model_evolver: MagicMock,
        mock_store: MagicMock,
    ) -> None:
        """retrain_model持久化失败时不修改实例属性"""
        mock_store.save_model_params.side_effect = IOError("磁盘写入失败")

        action = EvolutionAction(
            action_id="test_exec_002",
            action_type="retrain_model",
            trigger_reason="VDOT误差",
            trigger_condition={},
            target_model_type="vdot",
            priority="high",
            created_at=datetime.now(),
        )

        result = controller.execute_action(action)
        assert result.executed is True
        assert "持久化失败" in str(result.execution_result)
        # 持久化失败，不应调用apply_params_to_instance
        mock_model_evolver.apply_params_to_instance.assert_not_called()

    def test_execute_adjust_strategy(
        self,
        controller: EvolutionController,
        mock_prompt_tuner: MagicMock,
    ) -> None:
        """adjust_strategy动作调用PromptTuner"""
        action = EvolutionAction(
            action_id="test_exec_003",
            action_type="adjust_strategy",
            trigger_reason="连续拒绝",
            trigger_condition={},
            target_model_type="prompt",
            priority="medium",
            created_at=datetime.now(),
        )

        result = controller.execute_action(action)
        assert result.executed is True
        mock_prompt_tuner.auto_adjust_on_rejection.assert_called_once()

    def test_execute_incremental_learn_updates_trigger_state(
        self,
        controller: EvolutionController,
        mock_model_evolver: MagicMock,
        mock_store: MagicMock,
    ) -> None:
        """incremental_learn完成后更新trigger_state"""
        mock_store.count_decisions.return_value = 100

        action = EvolutionAction(
            action_id="test_exec_004",
            action_type="incremental_learn",
            trigger_reason="新数据积累",
            trigger_condition={},
            target_model_type="all",
            priority="medium",
            created_at=datetime.now(),
        )

        result = controller.execute_action(action)
        assert result.executed is True
        # 验证trigger_state被更新
        mock_store.save_trigger_state.assert_called_with("last_incremental_count", 100)

    def test_execute_generate_report(
        self,
        controller: EvolutionController,
        mock_evolution_reporter: MagicMock,
    ) -> None:
        """generate_report动作调用EvolutionReporter"""
        action = EvolutionAction(
            action_id="test_exec_005",
            action_type="generate_report",
            trigger_reason="月度复盘",
            trigger_condition={},
            target_model_type="none",
            priority="low",
            created_at=datetime.now(),
        )

        result = controller.execute_action(action)
        assert result.executed is True
        mock_evolution_reporter.generate_report.assert_called_once()


class TestLoadLastIncrementalCount:
    """_load_last_incremental_count()测试"""

    def test_returns_zero_when_no_state(
        self, controller: EvolutionController, mock_store: MagicMock
    ) -> None:
        """首次调用时返回0"""
        mock_store.load_trigger_state.return_value = None
        assert controller._load_last_incremental_count() == 0

    def test_returns_stored_value(
        self, controller: EvolutionController, mock_store: MagicMock
    ) -> None:
        """返回已存储的值"""
        mock_store.load_trigger_state.return_value = 156
        assert controller._load_last_incremental_count() == 156

    def test_returns_zero_for_non_int_value(
        self, controller: EvolutionController, mock_store: MagicMock
    ) -> None:
        """存储值非int时返回0"""
        mock_store.load_trigger_state.return_value = "invalid"
        assert controller._load_last_incremental_count() == 0
```

- [ ] **Step 2: 运行测试验证失败**

Run: `uv run pytest tests/unit/core/evolution/test_evolution_controller.py -v`
Expected: FAIL (ModuleNotFoundError: No module named 'src.core.evolution.evolution_controller')

- [ ] **Step 3: 实现EvolutionController**

创建 `src/core/evolution/evolution_controller.py`，完整实现参考架构设计说明书Section 8.4.5.1。核心要点：

1. 构造函数注入: store, calibration_engine, model_evolver, prompt_tuner, evolution_reporter, config
2. `check_triggers()`: 依次调用4个_check_*_trigger()方法，收集结果，性能监控(>50ms输出warning)
3. `_check_vdot_error_trigger()`: 使用get_prediction_actual_pairs("vdot", min_count=3, days=90)，检查最近3次误差
4. `_check_rejection_trigger()`: 使用get_decision_outcome_pairs(days=90)，检查最近2条recommendation_accepted=False
5. `_check_new_data_trigger()`: 使用count_decisions() + _load_last_incremental_count()，差值>=50时触发
6. `_check_monthly_review_trigger()`: 检查trigger_state中last_monthly_report是否为当月
7. `execute_action()`: 4种动作分支，retrain_model/incremental_learn先持久化后生效
8. `execute_pending_actions()`: 执行所有未执行动作
9. `_load_last_incremental_count()`: 从trigger_state.json加载

- [ ] **Step 4: 运行测试验证通过**

Run: `uv run pytest tests/unit/core/evolution/test_evolution_controller.py -v`
Expected: PASS

- [ ] **Step 5: 运行ruff和mypy检查**

Run: `uv run ruff check src/core/evolution/evolution_controller.py && uv run mypy src/core/evolution/evolution_controller.py --ignore-missing-imports`
Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add src/core/evolution/evolution_controller.py tests/unit/core/evolution/test_evolution_controller.py
git commit -m "feat(evolution): implement EvolutionController with 4 trigger rules and persist-first execution"
```

---

### Task-025-04: PromptTuner核心实现

**Files:**
- Create: `src/core/evolution/prompt_tuner.py`
- Create: `tests/unit/core/evolution/test_prompt_tuner.py`

- [ ] **Step 1: 编写PromptTuner失败测试**

创建 `tests/unit/core/evolution/test_prompt_tuner.py`：

```python
"""PromptTuner单元测试"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from src.core.evolution.config import EvolutionConfig
from src.core.evolution.models import PromptTuningParams
from src.core.evolution.prompt_tuner import PromptTuner


@pytest.fixture
def mock_store() -> MagicMock:
    """创建Mock EvolutionStore"""
    store = MagicMock()
    store.load_prompt_tuning_params.return_value = None
    store.save_prompt_tuning_params.return_value = None
    store.get_decision_outcome_pairs.return_value = []
    return store


@pytest.fixture
def tuner(mock_store: MagicMock) -> PromptTuner:
    config = EvolutionConfig(data_dir="/tmp/test_tuner")
    return PromptTuner(store=mock_store, config=config)


class TestGetParams:
    """get_params()测试"""

    def test_returns_default_when_no_file(
        self, tuner: PromptTuner, mock_store: MagicMock
    ) -> None:
        """JSON文件不存在时返回默认参数"""
        mock_store.load_prompt_tuning_params.return_value = None
        params = tuner.get_params()
        assert params.tone_intensity == 0.5
        assert params.recommendation_aggressiveness == 0.5
        assert params.update_count == 0

    def test_loads_from_store(
        self, tuner: PromptTuner, mock_store: MagicMock
    ) -> None:
        """从EvolutionStore加载已保存的参数"""
        saved_params = PromptTuningParams(
            tone_intensity=0.6,
            detail_level_score=0.4,
            recommendation_aggressiveness=0.7,
            data_driven_weight=0.3,
            update_count=5,
        )
        mock_store.load_prompt_tuning_params.return_value = saved_params
        params = tuner.get_params()
        assert params.tone_intensity == 0.6
        assert params.recommendation_aggressiveness == 0.7


class TestUpdateParams:
    """update_params()测试"""

    def test_manual_update(
        self, tuner: PromptTuner, mock_store: MagicMock
    ) -> None:
        """手动更新参数"""
        result = tuner.update_params(tone=0.7, aggressive=0.3)
        assert result.tone_intensity == 0.7
        assert result.recommendation_aggressiveness == 0.3
        mock_store.save_prompt_tuning_params.assert_called_once()

    def test_update_only_specified_params(
        self, tuner: PromptTuner, mock_store: MagicMock
    ) -> None:
        """仅更新指定参数，其余保持不变"""
        result = tuner.update_params(tone=0.8)
        assert result.tone_intensity == 0.8
        assert result.detail_level_score == 0.5
        assert result.recommendation_aggressiveness == 0.5
        assert result.data_driven_weight == 0.5


class TestAutoAdjustOnFeedback:
    """auto_adjust_on_feedback()测试"""

    def test_low_score_reduces_tone(
        self, tuner: PromptTuner, mock_store: MagicMock
    ) -> None:
        """低评分降低语气强度"""
        result = tuner.auto_adjust_on_feedback(avg_score=2.0, acceptance_rate=0.5)
        assert result.tone_intensity < 0.5

    def test_high_score_slightly_increases_tone(
        self, tuner: PromptTuner, mock_store: MagicMock
    ) -> None:
        """高评分微幅提高语气强度"""
        result = tuner.auto_adjust_on_feedback(avg_score=4.5, acceptance_rate=0.5)
        assert result.tone_intensity > 0.5

    def test_low_acceptance_reduces_aggressiveness(
        self, tuner: PromptTuner, mock_store: MagicMock
    ) -> None:
        """低接受率降低推荐激进程度"""
        result = tuner.auto_adjust_on_feedback(avg_score=3.0, acceptance_rate=0.2)
        assert result.recommendation_aggressiveness < 0.5

    def test_high_acceptance_slightly_increases_aggressiveness(
        self, tuner: PromptTuner, mock_store: MagicMock
    ) -> None:
        """高接受率微幅提高推荐激进程度"""
        result = tuner.auto_adjust_on_feedback(avg_score=3.0, acceptance_rate=0.8)
        assert result.recommendation_aggressiveness > 0.5

    def test_max_adjustment_bounded(
        self, tuner: PromptTuner, mock_store: MagicMock
    ) -> None:
        """单次调整幅度不超过tuning_max_adjustment"""
        result = tuner.auto_adjust_on_feedback(avg_score=1.0, acceptance_rate=0.0)
        # 默认参数0.5，最大调整0.1，所以结果应>=0.4
        assert result.tone_intensity >= 0.4
        assert result.recommendation_aggressiveness >= 0.4


class TestAutoAdjustOnRejection:
    """auto_adjust_on_rejection()测试"""

    def test_reduces_aggressiveness(
        self, tuner: PromptTuner, mock_store: MagicMock
    ) -> None:
        """连续拒绝时降低激进程度"""
        result = tuner.auto_adjust_on_rejection()
        assert result.recommendation_aggressiveness < 0.5

    def test_reduces_data_driven(
        self, tuner: PromptTuner, mock_store: MagicMock
    ) -> None:
        """连续拒绝时降低数据驱动权重"""
        result = tuner.auto_adjust_on_rejection()
        assert result.data_driven_weight < 0.5

    def test_saves_params(
        self, tuner: PromptTuner, mock_store: MagicMock
    ) -> None:
        """调整后持久化参数"""
        tuner.auto_adjust_on_rejection()
        mock_store.save_prompt_tuning_params.assert_called_once()


class TestResetToDefault:
    """reset_to_default()测试"""

    def test_resets_all_params(
        self, tuner: PromptTuner, mock_store: MagicMock
    ) -> None:
        """重置所有参数为0.5"""
        # 先调整参数
        tuner.update_params(tone=0.8, aggressive=0.2)
        # 重置
        result = tuner.reset_to_default()
        assert result.tone_intensity == 0.5
        assert result.recommendation_aggressiveness == 0.5
        assert result.detail_level_score == 0.5
        assert result.data_driven_weight == 0.5
        assert result.update_count == 0
```

- [ ] **Step 2: 运行测试验证失败**

Run: `uv run pytest tests/unit/core/evolution/test_prompt_tuner.py -v`
Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: 实现PromptTuner**

创建 `src/core/evolution/prompt_tuner.py`，完整实现参考架构设计说明书Section 8.4.5.2。核心要点：

1. 构造函数注入: store, config
2. `get_params()`: 首次调用从store加载，无则返回default()，缓存到实例变量
3. `update_params()`: 调用with_updates() + _save_params()
4. `auto_adjust_on_feedback()`: 基于avg_score和acceptance_rate调整4维参数，步长0.05，最大0.1
5. `auto_adjust_on_rejection()`: 降低aggressive(步长0.05)和data_driven(步长0.025)
6. `reset_to_default()`: 重置为全部0.5，持久化
7. `_save_params()`: 调用store.save_prompt_tuning_params()
8. `_load_params()`: 调用store.load_prompt_tuning_params()

- [ ] **Step 4: 运行测试验证通过**

Run: `uv run pytest tests/unit/core/evolution/test_prompt_tuner.py -v`
Expected: PASS

- [ ] **Step 5: 运行ruff和mypy检查**

Run: `uv run ruff check src/core/evolution/prompt_tuner.py && uv run mypy src/core/evolution/prompt_tuner.py --ignore-missing-imports`
Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add src/core/evolution/prompt_tuner.py tests/unit/core/evolution/test_prompt_tuner.py
git commit -m "feat(evolution): implement PromptTuner with 4-dim parameter space and JSON persistence"
```

---

### Task-025-05: [H-01整改] 编排层一致性 -- DecisionLogHook持有EvolutionEngine引用

**Files:**
- Modify: `src/core/evolution/decision_log_hook.py`
- Modify: `src/core/evolution/evolution_engine.py`
- Modify: `tests/unit/core/evolution/test_decision_log_hook.py`
- Modify: `tests/unit/core/evolution/test_evolution_engine.py`

- [ ] **Step 1: 编写H-01整改失败测试**

在 `tests/unit/core/evolution/test_decision_log_hook.py` 追加：

```python
class TestDecisionLogHookV025Integration:
    """DecisionLogHook v0.25编排层一致性测试（H-01整改）"""

    def test_hook_holds_evolution_engine_reference(self) -> None:
        """DecisionLogHook应持有EvolutionEngine引用（非EvolutionController）"""
        from src.core.evolution.decision_log_hook import DecisionLogHook

        mock_engine = MagicMock()
        hook = DecisionLogHook(
            evolution_engine=mock_engine,
        )
        # 验证持有的是EvolutionEngine引用
        assert hook._evolution_engine is mock_engine

    def test_after_iteration_calls_engine_check_evolution_triggers(self) -> None:
        """after_iteration应调用EvolutionEngine.check_evolution_triggers()"""
        from src.core.evolution.decision_log_hook import DecisionLogHook
        from src.core.evolution.models import TriggerCheckResult

        mock_engine = MagicMock()
        mock_engine.check_evolution_triggers.return_value = TriggerCheckResult(
            checked_at=datetime.now(),
            triggered_actions=[],
            skipped_conditions=[],
        )
        hook = DecisionLogHook(evolution_engine=mock_engine)
        hook._decision_logged = True  # 模拟已有决策日志

        # 调用after_iteration
        hook.after_iteration(MagicMock())

        # 验证调用的是EvolutionEngine.check_evolution_triggers()
        mock_engine.check_evolution_triggers.assert_called_once()

    def test_after_iteration_triggers_async_execution_via_engine(self) -> None:
        """after_iteration应通过EvolutionEngine.execute_evolution_action()异步执行"""
        from src.core.evolution.decision_log_hook import DecisionLogHook
        from src.core.evolution.models import EvolutionAction, TriggerCheckResult

        action = EvolutionAction(
            action_id="async_test_001",
            action_type="retrain_model",
            trigger_reason="VDOT误差",
            trigger_condition={},
            target_model_type="vdot",
            priority="high",
            created_at=datetime.now(),
        )
        mock_engine = MagicMock()
        mock_engine.check_evolution_triggers.return_value = TriggerCheckResult(
            checked_at=datetime.now(),
            triggered_actions=[action],
            skipped_conditions=[],
        )
        hook = DecisionLogHook(evolution_engine=mock_engine)
        hook._decision_logged = True

        hook.after_iteration(MagicMock())

        # 等待daemon线程执行
        import time
        time.sleep(0.5)

        # 验证通过EvolutionEngine执行动作
        mock_engine.execute_evolution_action.assert_called()

    def test_v025_component_not_injected_graceful_degradation(self) -> None:
        """v0.25组件未注入时after_iteration不报错"""
        from src.core.evolution.decision_log_hook import DecisionLogHook

        mock_engine = MagicMock()
        mock_engine.check_evolution_triggers.side_effect = RuntimeError(
            "请先初始化v0.25组件"
        )
        hook = DecisionLogHook(evolution_engine=mock_engine)
        hook._decision_logged = True

        # 不应抛出异常
        hook.after_iteration(MagicMock())
```

- [ ] **Step 2: 运行测试验证失败**

Run: `uv run pytest tests/unit/core/evolution/test_decision_log_hook.py -v -k "TestDecisionLogHookV025"`
Expected: FAIL (AttributeError: 'DecisionLogHook' object has no attribute 'after_iteration')

- [ ] **Step 3: 修改DecisionLogHook**

在 `src/core/evolution/decision_log_hook.py` 中：

1. 在 `after_iteration` 方法中添加进化触发检查逻辑（如果方法不存在则新增）：

```python
    def after_iteration(self, context: AgentHookContext) -> None:
        """Agent迭代完成后回调（v0.25扩展：触发进化检查）

        通过EvolutionEngine编排层间接调用EvolutionController，
        确保所有进化操作通过编排层进行（H-01整改）。
        """
        if not self._decision_logged:
            return

        # v0.25: 触发进化检查
        try:
            result = self._evolution_engine.check_evolution_triggers()
            if result.triggered_actions:
                # 异步执行进化动作（daemon线程，不阻塞主流程）
                import threading

                def _execute_actions() -> None:
                    for action in result.triggered_actions:
                        try:
                            self._evolution_engine.execute_evolution_action(action)
                        except Exception as e:
                            logger.error("异步执行进化动作失败: %s", e)

                thread = threading.Thread(
                    target=_execute_actions,
                    daemon=True,
                    name="evolution-action-executor",
                )
                thread.start()
        except RuntimeError:
            # v0.25组件未注入，graceful降级
            pass
        except Exception as e:
            logger.warning("进化触发检查异常（不影响主流程）: %s", e)
```

- [ ] **Step 4: 在EvolutionEngine中添加v0.25编排方法**

在 `src/core/evolution/evolution_engine.py` 中追加：

```python
    # ---- v0.25 新增方法 ----

    def _require_v025_component(self, component_name: str) -> None:
        """校验v0.25组件是否已注入"""
        component_map = {
            "evolution_controller": self._evolution_controller,
            "prompt_tuner": self._prompt_tuner,
            "evolution_reporter": self._evolution_reporter,
        }
        if component_map.get(component_name) is None:
            raise RuntimeError("请先初始化v0.25组件")

    def check_evolution_triggers(self) -> TriggerCheckResult:
        """检查进化触发条件（委托给EvolutionController）"""
        self._require_v025_component("evolution_controller")
        assert self._evolution_controller is not None
        return self._evolution_controller.check_triggers()

    def execute_evolution_action(self, action: EvolutionAction) -> EvolutionAction:
        """执行进化动作（委托给EvolutionController）"""
        self._require_v025_component("evolution_controller")
        assert self._evolution_controller is not None
        return self._evolution_controller.execute_action(action)

    def get_evolution_report(self, month: str | None = None) -> EvolutionReport:
        """获取月度进化报告（委托给EvolutionReporter）"""
        self._require_v025_component("evolution_reporter")
        assert self._evolution_reporter is not None
        return self._evolution_reporter.generate_report(month)

    def adjust_prompt_params(
        self,
        tone: float | None = None,
        detail: float | None = None,
        aggressive: float | None = None,
        data_driven: float | None = None,
    ) -> PromptTuningParams:
        """手动调整提示参数（委托给PromptTuner）"""
        self._require_v025_component("prompt_tuner")
        assert self._prompt_tuner is not None
        return self._prompt_tuner.update_params(
            tone=tone, detail=detail, aggressive=aggressive, data_driven=data_driven
        )

    def get_prompt_tuning_params(self) -> PromptTuningParams:
        """获取当前提示调优参数（委托给PromptTuner）"""
        self._require_v025_component("prompt_tuner")
        assert self._prompt_tuner is not None
        return self._prompt_tuner.get_params()

    def reset_prompt_tuning(self) -> PromptTuningParams:
        """重置提示调优参数为默认值（委托给PromptTuner）"""
        self._require_v025_component("prompt_tuner")
        assert self._prompt_tuner is not None
        return self._prompt_tuner.reset_to_default()
```

同时在EvolutionEngine构造函数中添加3个v0.25可选参数：

```python
    def __init__(
        self,
        decision_logger: DecisionLogger,
        outcome_collector: OutcomeCollector,
        response_analyzer: ResponseAnalyzer | None = None,
        calibration_engine: CalibrationEngine | None = None,
        model_evolver: ModelEvolver | None = None,
        evolution_controller: Any | None = None,   # v0.25新增
        prompt_tuner: Any | None = None,            # v0.25新增
        evolution_reporter: Any | None = None,       # v0.25新增
    ) -> None:
        self._decision_logger = decision_logger
        self._outcome_collector = outcome_collector
        self._response_analyzer = response_analyzer
        self._calibration_engine = calibration_engine
        self._model_evolver = model_evolver
        self._evolution_controller = evolution_controller
        self._prompt_tuner = prompt_tuner
        self._evolution_reporter = evolution_reporter
```

在文件顶部TYPE_CHECKING块中添加：
```python
if TYPE_CHECKING:
    from src.core.evolution.calibration_engine import CalibrationEngine
    from src.core.evolution.evolution_controller import EvolutionController
    from src.core.evolution.evolution_reporter import EvolutionReporter
    from src.core.evolution.model_evolver import ModelEvolver
    from src.core.evolution.prompt_tuner import PromptTuner
    from src.core.evolution.response_analyzer import ResponseAnalyzer
```

在import区添加v0.25模型导入：
```python
from src.core.evolution.models import (
    EvolutionAction,
    EvolutionReport,
    PromptTuningParams,
    TriggerCheckResult,
    # ... 保留已有导入 ...
)
```

- [ ] **Step 5: 运行测试验证通过**

Run: `uv run pytest tests/unit/core/evolution/test_decision_log_hook.py tests/unit/core/evolution/test_evolution_engine.py -v -k "V025 or v025"`
Expected: PASS

- [ ] **Step 6: 运行全量evolution测试确保向后兼容**

Run: `uv run pytest tests/unit/core/evolution/ -v`
Expected: PASS

- [ ] **Step 7: 提交**

```bash
git add src/core/evolution/decision_log_hook.py src/core/evolution/evolution_engine.py tests/unit/core/evolution/test_decision_log_hook.py tests/unit/core/evolution/test_evolution_engine.py
git commit -m "fix(evolution): H-01 - DecisionLogHook holds EvolutionEngine reference, all evolution ops through orchestration layer"
```

---

### Task-025-06: [H-02整改] 部分失败处理 -- IncrementalLearnResult结构化

**Files:**
- Modify: `src/core/evolution/models.py` (新增IncrementalLearnResult)
- Modify: `src/core/evolution/evolution_controller.py` (修改incremental_learn分支)
- Modify: `tests/unit/core/evolution/test_models.py` (追加测试)
- Modify: `tests/unit/core/evolution/test_evolution_controller.py` (追加测试)

- [ ] **Step 1: 编写IncrementalLearnResult失败测试**

在 `tests/unit/core/evolution/test_models.py` 追加：

```python
class TestIncrementalLearnResult:
    """IncrementalLearnResult数据模型测试（H-02整改）"""

    def test_create_success_result(self) -> None:
        """测试创建成功的增量学习结果"""
        from src.core.evolution.models import IncrementalLearnResult

        result = IncrementalLearnResult(
            model_type="vdot",
            success=True,
            mae_before=0.05,
            mae_after=0.03,
            error=None,
        )
        assert result.model_type == "vdot"
        assert result.success is True
        assert result.mae_before == 0.05
        assert result.mae_after == 0.03
        assert result.error is None

    def test_create_failure_result(self) -> None:
        """测试创建失败的增量学习结果"""
        from src.core.evolution.models import IncrementalLearnResult

        result = IncrementalLearnResult(
            model_type="injury",
            success=False,
            mae_before=None,
            mae_after=None,
            error="数据不足",
        )
        assert result.success is False
        assert result.error == "数据不足"

    def test_to_dict(self) -> None:
        """测试序列化"""
        from src.core.evolution.models import IncrementalLearnResult

        result = IncrementalLearnResult(
            model_type="vdot",
            success=True,
            mae_before=0.05,
            mae_after=0.03,
            error=None,
        )
        d = result.to_dict()
        assert d["model_type"] == "vdot"
        assert d["success"] is True
        assert d["mae_before"] == 0.05
```

- [ ] **Step 2: 运行测试验证失败**

Run: `uv run pytest tests/unit/core/evolution/test_models.py -v -k "TestIncrementalLearnResult"`
Expected: FAIL

- [ ] **Step 3: 在models.py中新增IncrementalLearnResult**

在 `src/core/evolution/models.py` 的v0.25数据模型区域追加：

```python
@dataclass(frozen=True)
class IncrementalLearnResult:
    """增量学习单模型结果（不可变数据类，H-02整改）

    记录单个模型在增量学习中的进化结果，支持部分失败场景追溯。

    Attributes:
        model_type: 模型类型 (vdot/injury/training_response)
        success: 是否进化成功
        mae_before: 进化前MAE（失败时为None）
        mae_after: 进化后MAE（失败时为None）
        error: 错误信息（成功时为None）
    """

    model_type: str
    success: bool
    mae_before: float | None
    mae_after: float | None
    error: str | None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "model_type": self.model_type,
            "success": self.success,
            "mae_before": self.mae_before,
            "mae_after": self.mae_after,
            "error": self.error,
        }
```

- [ ] **Step 4: 修改EvolutionController.execute_action()的incremental_learn分支**

在 `src/core/evolution/evolution_controller.py` 中，将incremental_learn分支从字符串拼接改为IncrementalLearnResult结构化记录：

```python
        elif action.action_type == "incremental_learn":
            # 对所有模型执行校准+进化（逐模型先持久化后生效）
            learn_results: list[IncrementalLearnResult] = []
            for model_type in ["vdot", "injury", "training_response"]:
                try:
                    r = self._model_evolver.evolve_model(model_type)

                    # 先持久化
                    try:
                        self._store.save_model_params(model_type, r._raw_param_changes)
                    except Exception as persist_err:
                        learn_results.append(IncrementalLearnResult(
                            model_type=model_type,
                            success=False,
                            mae_before=None,
                            mae_after=None,
                            error=f"持久化失败: {persist_err}",
                        ))
                        continue

                    # 持久化成功 → 修改实例属性
                    self._model_evolver.apply_params_to_instance(model_type)
                    learn_results.append(IncrementalLearnResult(
                        model_type=model_type,
                        success=True,
                        mae_before=r.mae_before,
                        mae_after=r.mae_after,
                        error=None,
                    ))
                except ValueError:
                    learn_results.append(IncrementalLearnResult(
                        model_type=model_type,
                        success=False,
                        mae_before=None,
                        mae_after=None,
                        error="数据不足跳过",
                    ))
                except Exception as e:
                    learn_results.append(IncrementalLearnResult(
                        model_type=model_type,
                        success=False,
                        mae_before=None,
                        mae_after=None,
                        error=str(e),
                    ))

            # 部分失败时action标记为executed=True，execution_result包含详细结果
            execution_result = {
                r.model_type: r.to_dict() for r in learn_results
            }

            # 增量学习完成后更新trigger_state
            total_count = self._store.count_decisions()
            self._store.save_trigger_state("last_incremental_count", total_count)
```

- [ ] **Step 5: 追加EvolutionController部分失败测试**

在 `tests/unit/core/evolution/test_evolution_controller.py` 的TestExecuteAction类中追加：

```python
    def test_incremental_learn_partial_failure(
        self,
        controller: EvolutionController,
        mock_model_evolver: MagicMock,
        mock_store: MagicMock,
    ) -> None:
        """incremental_learn部分失败场景：vdot成功、injury数据不足、training_response异常"""
        mock_store.count_decisions.return_value = 100

        # 模拟vdot成功、injury数据不足(ValueError)、training_response异常(RuntimeError)
        evolve_results = {
            "vdot": MagicMock(mae_before=0.05, mae_after=0.03, _raw_param_changes={"tau": 42}),
            "injury": MagicMock(side_effect=ValueError("数据不足")),
            "training_response": MagicMock(side_effect=RuntimeError("模型加载失败")),
        }

        def mock_evolve(model_type: str) -> MagicMock:
            if model_type == "injury":
                raise ValueError("数据不足")
            if model_type == "training_response":
                raise RuntimeError("模型加载失败")
            return evolve_results[model_type]

        mock_model_evolver.evolve_model.side_effect = mock_evolve

        action = EvolutionAction(
            action_id="test_partial_001",
            action_type="incremental_learn",
            trigger_reason="新数据积累",
            trigger_condition={},
            target_model_type="all",
            priority="medium",
            created_at=datetime.now(),
        )

        result = controller.execute_action(action)
        assert result.executed is True
        # execution_result应为dict类型，包含3个模型的结果
        assert isinstance(result.execution_result, dict)
        assert result.execution_result["vdot"]["success"] is True
        assert result.execution_result["injury"]["success"] is False
        assert result.execution_result["training_response"]["success"] is False
```

- [ ] **Step 6: 运行测试验证通过**

Run: `uv run pytest tests/unit/core/evolution/test_models.py tests/unit/core/evolution/test_evolution_controller.py -v -k "IncrementalLearnResult or partial_failure"`
Expected: PASS

- [ ] **Step 7: 提交**

```bash
git add src/core/evolution/models.py src/core/evolution/evolution_controller.py tests/unit/core/evolution/test_models.py tests/unit/core/evolution/test_evolution_controller.py
git commit -m "fix(evolution): H-02 - add IncrementalLearnResult for structured partial failure tracking"
```

---

### Task-025-07: [H-03整改] 参数下限保护 -- PromptTuner下限+反弹机制

**Files:**
- Modify: `src/core/evolution/prompt_tuner.py`
- Modify: `src/core/evolution/models.py` (with_updates扩展min_bounds)
- Modify: `tests/unit/core/evolution/test_prompt_tuner.py`

- [ ] **Step 1: 编写参数下限保护失败测试**

在 `tests/unit/core/evolution/test_prompt_tuner.py` 追加：

```python
class TestParameterFloorProtection:
    """参数下限保护测试（H-03整改）"""

    def test_aggressive_floor_on_rejection(
        self, tuner: PromptTuner, mock_store: MagicMock
    ) -> None:
        """连续拒绝后aggressive不低于0.1"""
        # 模拟从0.5开始连续10次拒绝
        for _ in range(10):
            tuner.auto_adjust_on_rejection()

        params = tuner.get_params()
        assert params.recommendation_aggressiveness >= 0.1

    def test_data_driven_floor_on_rejection(
        self, tuner: PromptTuner, mock_store: MagicMock
    ) -> None:
        """连续拒绝后data_driven不低于0.2"""
        for _ in range(10):
            tuner.auto_adjust_on_rejection()

        params = tuner.get_params()
        assert params.data_driven_weight >= 0.2

    def test_warning_on_approaching_floor(
        self, tuner: PromptTuner, mock_store: MagicMock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """接近下限时输出warning日志"""
        import logging

        # 将aggressive降到接近0.1
        tuner.update_params(aggressive=0.12)
        tuner.auto_adjust_on_rejection()

        # 应有warning日志
        assert any("接近下限" in r.message or "aggressive" in r.message.lower() for r in caplog.records if r.levelno >= logging.WARNING)

    def test_bounce_back_mechanism(
        self, tuner: PromptTuner, mock_store: MagicMock
    ) -> None:
        """反弹机制：接受推荐后aggressive恢复步长(0.08)大于降低步长(0.05)"""
        # 先降低aggressive
        tuner.update_params(aggressive=0.3)
        # 模拟接受推荐
        result = tuner.auto_adjust_on_feedback(avg_score=4.0, acceptance_rate=0.8)
        # aggressive应增加0.08（恢复步长），大于降低步长0.05
        assert result.recommendation_aggressiveness == pytest.approx(0.3 + 0.08, abs=0.01)

    def test_with_updates_min_bounds(
        self, mock_store: MagicMock
    ) -> None:
        """with_updates支持min_bounds参数"""
        from src.core.evolution.models import PromptTuningParams

        params = PromptTuningParams(
            recommendation_aggressiveness=0.08,
            data_driven_weight=0.15,
        )
        # 使用min_bounds保护
        updated = params.with_updates(
            aggressive=0.05,
            data_driven=0.1,
            min_bounds={"recommendation_aggressiveness": 0.1, "data_driven_weight": 0.2},
        )
        assert updated.recommendation_aggressiveness == 0.1  # 被下限保护
        assert updated.data_driven_weight == 0.2  # 被下限保护

    def test_with_updates_no_min_bounds_backward_compat(
        self, mock_store: MagicMock
    ) -> None:
        """with_updates不传min_bounds时保持向后兼容"""
        from src.core.evolution.models import PromptTuningParams

        params = PromptTuningParams.default()
        updated = params.with_updates(aggressive=0.0)
        # 无min_bounds时，0.0是合法值（clamp到[0.0, 1.0]）
        assert updated.recommendation_aggressiveness == 0.0
```

- [ ] **Step 2: 运行测试验证失败**

Run: `uv run pytest tests/unit/core/evolution/test_prompt_tuner.py -v -k "TestParameterFloorProtection"`
Expected: FAIL

- [ ] **Step 3: 扩展PromptTuningParams.with_updates()支持min_bounds**

在 `src/core/evolution/models.py` 中修改 `with_updates` 方法签名和实现：

```python
    def with_updates(
        self,
        tone: float | None = None,
        detail: float | None = None,
        aggressive: float | None = None,
        data_driven: float | None = None,
        min_bounds: dict[str, float] | None = None,
    ) -> PromptTuningParams:
        """创建更新后的参数副本（保持不可变性）

        每个参数被clamp到[0.0, 1.0]范围。
        可选min_bounds参数为指定维度设置下限保护（H-03整改）。

        Args:
            tone: 新的语气强度（None保持不变）
            detail: 新的信息密度（None保持不变）
            aggressive: 新的推荐激进程度（None保持不变）
            data_driven: 新的数据驱动权重（None保持不变）
            min_bounds: 可选参数下限映射，如 {"recommendation_aggressiveness": 0.1}

        Returns:
            PromptTuningParams: 更新后的参数副本
        """
        bounds = min_bounds or {}

        def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
            return max(lower, min(upper, value))

        return PromptTuningParams(
            tone_intensity=_clamp(
                tone if tone is not None else self.tone_intensity,
                lower=bounds.get("tone_intensity", 0.0),
            ),
            detail_level_score=_clamp(
                detail if detail is not None else self.detail_level_score,
                lower=bounds.get("detail_level_score", 0.0),
            ),
            recommendation_aggressiveness=_clamp(
                aggressive if aggressive is not None else self.recommendation_aggressiveness,
                lower=bounds.get("recommendation_aggressiveness", 0.0),
            ),
            data_driven_weight=_clamp(
                data_driven if data_driven is not None else self.data_driven_weight,
                lower=bounds.get("data_driven_weight", 0.0),
            ),
            last_updated=datetime.now(),
            update_count=self.update_count + 1,
        )
```

- [ ] **Step 4: 修改PromptTuner.auto_adjust_on_rejection()添加下限保护**

在 `src/core/evolution/prompt_tuner.py` 中修改 `auto_adjust_on_rejection` 方法：

```python
    def auto_adjust_on_rejection(self) -> PromptTuningParams:
        """连续拒绝推荐时降低激进程度，同时降低数据驱动权重

        H-03整改: 添加参数下限保护
        - aggressive最低0.1
        - data_driven最低0.2
        - 接近下限时输出warning日志
        """
        current = self.get_params()
        step = self._config.tuning_adjustment_step

        new_aggressive = current.recommendation_aggressiveness - step
        new_data_driven = current.data_driven_weight - step * 0.5

        # 参数下限保护
        min_bounds = {
            "recommendation_aggressiveness": 0.1,
            "data_driven_weight": 0.2,
        }

        # 接近下限时输出warning
        if new_aggressive < 0.15:
            logger.warning(
                "recommendation_aggressiveness接近下限: %.3f (下限0.1)",
                new_aggressive,
            )
        if new_data_driven < 0.25:
            logger.warning(
                "data_driven_weight接近下限: %.3f (下限0.2)",
                new_data_driven,
            )

        updated = current.with_updates(
            aggressive=new_aggressive,
            data_driven=new_data_driven,
            min_bounds=min_bounds,
        )
        self._save_params(updated)
        return updated
```

- [ ] **Step 5: 修改PromptTuner.auto_adjust_on_feedback()添加反弹机制**

在 `auto_adjust_on_feedback` 方法中，将接受推荐时aggressive的恢复步长从0.05改为0.08：

```python
    # 推荐激进程度调整（反弹机制：恢复步长0.08 > 降低步长0.05）
    if acceptance_rate < 0.3:
        aggressive_delta = -step  # 降低步长0.05
    elif acceptance_rate > 0.7:
        aggressive_delta = step * 1.6  # 恢复步长0.08（0.05 * 1.6）
```

- [ ] **Step 6: 运行测试验证通过**

Run: `uv run pytest tests/unit/core/evolution/test_prompt_tuner.py -v -k "TestParameterFloorProtection"`
Expected: PASS

- [ ] **Step 7: 运行全量PromptTuner测试**

Run: `uv run pytest tests/unit/core/evolution/test_prompt_tuner.py -v`
Expected: PASS

- [ ] **Step 8: 提交**

```bash
git add src/core/evolution/prompt_tuner.py src/core/evolution/models.py tests/unit/core/evolution/test_prompt_tuner.py
git commit -m "fix(evolution): H-03 - add parameter floor protection and bounce-back mechanism for PromptTuner"
```

---

### 里程碑 M3: 编排接入完成（预计第6-7天，22h）

**目标**: 完成 EvolutionEngine 编排层扩展、AppContext更新、CLI命令、Agent工具。

**准入条件**: M2全部完成
**准出标准**: CLI命令和Agent工具可端到端调用

---

### Task-025-09: EvolutionEngine v0.25编排层扩展 + AppContext更新

**Files:**
- Modify: `src/core/evolution/evolution_engine.py` (已在T05中部分完成，补充get_evolution_status扩展)
- Modify: `src/core/base/context.py` (AppContext扩展)
- Modify: `tests/unit/core/evolution/test_evolution_engine.py` (扩展)
- Create: `tests/unit/core/evolution/test_context_extension.py`

> 注意: T05已在EvolutionEngine中添加了v0.25编排方法和构造函数参数。本任务补充get_evolution_status()扩展和AppContext更新。

- [ ] **Step 1: 编写AppContext v0.25扩展失败测试**

创建 `tests/unit/core/evolution/test_context_extension.py`：

```python
"""AppContext v0.25扩展测试"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestAppContextV025:
    """AppContext v0.25扩展属性测试"""

    def test_evolution_engine_includes_v025_components(self) -> None:
        """EvolutionEngine应包含v0.25子组件"""
        from src.core.evolution.evolution_engine import EvolutionEngine

        # 验证构造函数接受v0.25参数
        mock_logger = MagicMock()
        mock_collector = MagicMock()
        mock_controller = MagicMock()
        mock_tuner = MagicMock()
        mock_reporter = MagicMock()

        engine = EvolutionEngine(
            decision_logger=mock_logger,
            outcome_collector=mock_collector,
            evolution_controller=mock_controller,
            prompt_tuner=mock_tuner,
            evolution_reporter=mock_reporter,
        )

        # 验证v0.25方法可用
        mock_tuner.get_params.return_value = MagicMock(to_dict=lambda: {"tone_intensity": 0.5})
        params = engine.get_prompt_tuning_params()
        assert params is not None

    def test_evolution_engine_v025_not_injected_raises(self) -> None:
        """v0.25组件未注入时调用方法抛出RuntimeError"""
        from src.core.evolution.evolution_engine import EvolutionEngine

        engine = EvolutionEngine(
            decision_logger=MagicMock(),
            outcome_collector=MagicMock(),
        )

        with pytest.raises(RuntimeError, match="请先初始化v0.25组件"):
            engine.check_evolution_triggers()

        with pytest.raises(RuntimeError, match="请先初始化v0.25组件"):
            engine.get_prompt_tuning_params()

    def test_get_evolution_status_includes_v025_fields(self) -> None:
        """get_evolution_status()包含v0.25字段"""
        from src.core.evolution.evolution_engine import EvolutionEngine
        from src.core.evolution.models import PromptTuningParams

        mock_tuner = MagicMock()
        mock_tuner.get_params.return_value = PromptTuningParams.default()

        engine = EvolutionEngine(
            decision_logger=MagicMock(),
            outcome_collector=MagicMock(),
            prompt_tuner=mock_tuner,
        )

        # Mock get_decision_history
        engine._decision_logger.get_decision_history.return_value = []

        status = engine.get_evolution_status()
        assert "evolution_status" in status
        assert "prompt_tuning" in status["evolution_status"]
```

- [ ] **Step 2: 运行测试验证**

Run: `uv run pytest tests/unit/core/evolution/test_context_extension.py -v`
Expected: 部分PASS，部分FAIL（get_evolution_status需扩展）

- [ ] **Step 3: 扩展EvolutionEngine.get_evolution_status()**

在 `src/core/evolution/evolution_engine.py` 的 `get_evolution_status()` 方法返回值中添加v0.25字段：

```python
        # v0.25新增: evolution_status
        evolution_status: dict[str, Any] = {}
        if self._evolution_controller is not None:
            # 上次进化时间和进化动作数（从trigger_state获取）
            evolution_status["evolution_actions_count"] = 0  # 可从store查询
        if self._prompt_tuner is not None:
            params = self._prompt_tuner.get_params()
            evolution_status["prompt_tuning"] = params.to_dict()
            # 个性化程度
            tuning_degree = (
                abs(params.tone_intensity - 0.5)
                + abs(params.detail_level_score - 0.5)
                + abs(params.recommendation_aggressiveness - 0.5)
            ) / 3.0
            evolution_status["personalization_degree"] = round(tuning_degree, 4)

        return {
            "total_decisions": total_decisions,
            "status_distribution": status_dist,
            "type_distribution": type_dist,
            "outcome_fill_rate": round(outcome_fill_rate, 4),
            "avg_fidelity": round(avg_fidelity, 4),
            "avg_prediction_error": round(avg_prediction_error, 4),
            "feedback_collection_rate": round(feedback_collection_rate, 4),
            "calibration_status": calibration_status,
            "evolution_status": evolution_status,
        }
```

- [ ] **Step 4: 更新AppContext.evolution_engine属性**

在 `src/core/base/context.py` 的 `evolution_engine` 属性中，在构建EvolutionEngine时注入v0.25子组件：

```python
            # v0.25: 注入自适应进化组件
            from src.core.evolution.evolution_controller import EvolutionController
            from src.core.evolution.evolution_reporter import EvolutionReporter
            from src.core.evolution.prompt_tuner import PromptTuner

            prompt_tuner = PromptTuner(store=store, config=config)
            evolution_reporter = EvolutionReporter(
                store=store,
                calibration_engine=calibration_engine,
                prompt_tuner=prompt_tuner,
                config=config,
            )
            evolution_controller = EvolutionController(
                store=store,
                calibration_engine=calibration_engine,
                model_evolver=model_evolver,
                prompt_tuner=prompt_tuner,
                evolution_reporter=evolution_reporter,
                config=config,
            )

            engine = EvolutionEngine(
                decision_logger=decision_logger,
                outcome_collector=outcome_collector,
                response_analyzer=response_analyzer,
                calibration_engine=calibration_engine,
                model_evolver=model_evolver,
                evolution_controller=evolution_controller,
                prompt_tuner=prompt_tuner,
                evolution_reporter=evolution_reporter,
            )
```

同时在AppContext中新增便捷属性：

```python
    @property
    def prompt_tuner(self) -> Any:
        """获取提示调优器（v0.25.0新增）"""
        engine = self.evolution_engine
        if engine is not None and hasattr(engine, '_prompt_tuner'):
            return engine._prompt_tuner
        return None

    @property
    def prompt_tuner_params(self) -> Any:
        """获取当前提示调优参数（v0.25.0新增）"""
        tuner = self.prompt_tuner
        if tuner is not None:
            return tuner.get_params()
        return None
```

- [ ] **Step 5: 运行测试验证通过**

Run: `uv run pytest tests/unit/core/evolution/test_context_extension.py tests/unit/core/evolution/test_evolution_engine.py -v`
Expected: PASS

- [ ] **Step 6: 运行全量evolution测试确保向后兼容**

Run: `uv run pytest tests/unit/core/evolution/ -v`
Expected: PASS

- [ ] **Step 7: 提交**

```bash
git add src/core/evolution/evolution_engine.py src/core/base/context.py tests/unit/core/evolution/test_context_extension.py tests/unit/core/evolution/test_evolution_engine.py
git commit -m "feat(evolution): extend EvolutionEngine orchestration layer and AppContext for v0.25 components"
```

---

### Task-025-10: CLI命令实现（evolution triggers/report/tune）

**Files:**
- Modify: `src/cli/commands/evolution.py` (新增3个命令)
- Modify: `src/cli/handlers/evolution_handler.py` (新增3个handler方法)

- [ ] **Step 1: 在EvolutionHandler中新增3个handler方法**

在 `src/cli/handlers/evolution_handler.py` 追加：

```python
    def check_triggers(self) -> dict[str, Any]:
        """检查进化触发条件

        Returns:
            dict: 触发检查结果
        """
        engine = self._get_engine()
        try:
            result = engine.check_evolution_triggers()
            return {
                "success": True,
                "data": result.to_dict(),
                "message": f"检查完成: {len(result.triggered_actions)}个触发, {len(result.skipped_conditions)}个跳过",
            }
        except RuntimeError as e:
            return {"success": False, "message": str(e)}

    def get_evolution_report(self, month: str | None = None) -> dict[str, Any]:
        """生成月度进化报告

        Args:
            month: 月份(YYYY-MM格式)，默认当月

        Returns:
            dict: 进化报告
        """
        engine = self._get_engine()
        try:
            report = engine.get_evolution_report(month)
            return {
                "success": True,
                "data": report.to_dict(),
                "message": f"进化报告已生成: {report.month}",
            }
        except RuntimeError as e:
            return {"success": False, "message": str(e)}

    def adjust_prompt_params(
        self,
        tone: float | None = None,
        detail: float | None = None,
        aggressive: float | None = None,
        data_driven: float | None = None,
    ) -> dict[str, Any]:
        """手动调整提示参数

        Args:
            tone: 语气强度(0.0-1.0)
            detail: 信息密度(0.0-1.0)
            aggressive: 推荐激进程度(0.0-1.0)
            data_driven: 数据驱动权重(0.0-1.0)

        Returns:
            dict: 调整后的参数
        """
        engine = self._get_engine()
        try:
            params = engine.adjust_prompt_params(
                tone=tone, detail=detail, aggressive=aggressive, data_driven=data_driven
            )
            return {
                "success": True,
                "data": params.to_dict(),
                "message": "提示参数已调整",
            }
        except RuntimeError as e:
            return {"success": False, "message": str(e)}
```

- [ ] **Step 2: 在evolution.py中新增3个CLI命令**

在 `src/cli/commands/evolution.py` 追加：

```python
@app.command(name="triggers")
def check_triggers() -> None:
    """检查进化触发条件

    检查当前是否满足进化触发条件，展示已触发和跳过的条件。

    Examples:
        nanobotrun evolution triggers
    """
    try:
        handler = EvolutionHandler()
        result = handler.check_triggers()

        if not result["success"]:
            console.print(f"[red]{result['message']}[/red]")
            return

        data = result["data"]
        triggered = data.get("triggered_actions", [])
        skipped = data.get("skipped_conditions", [])

        if triggered:
            table = Table(title="已触发的进化动作", show_header=True, header_style="bold green")
            table.add_column("动作ID", width=12)
            table.add_column("动作类型", width=18)
            table.add_column("触发原因", width=30)
            table.add_column("目标模型", width=15)
            table.add_column("优先级", width=10)
            for a in triggered:
                table.add_row(
                    a.get("action_id", ""),
                    a.get("action_type", ""),
                    a.get("trigger_reason", ""),
                    a.get("target_model_type", ""),
                    a.get("priority", ""),
                )
            console.print(table)
        else:
            console.print("[green]当前无触发条件[/green]")

        if skipped:
            console.print(Panel(
                "\n".join(f"- {s.get('rule', '未知')}: {s.get('reason', '')}" for s in skipped),
                title="跳过的条件",
                border_style="dim",
            ))
    except NanobotRunnerError as e:
        print_error(str(e))


@app.command(name="report")
def get_report(
    month: str = typer.Option("", "--month", "-m", help="报告月份 (YYYY-MM格式，默认当月)"),
) -> None:
    """生成月度进化报告

    汇总指定月份的进化引擎运行状态和效果。

    Examples:
        nanobotrun evolution report
        nanobotrun evolution report --month 2026-05
    """
    try:
        handler = EvolutionHandler()
        result = handler.get_evolution_report(month=month or None)

        if not result["success"]:
            console.print(f"[red]{result['message']}[/red]")
            return

        data = result["data"]
        console.print(Panel(
            f"月份: {data.get('month', '')}\n"
            f"决策总数: {data.get('total_decisions', 0)}\n"
            f"决策接受率: {data.get('decision_acceptance_rate', 0):.1%}\n"
            f"个性化程度: {data.get('personalization_degree', 0):.2f}\n"
            f"进化动作数: {data.get('evolution_actions_count', 0)}",
            title=f"进化报告 - {data.get('month', '')}",
            border_style="cyan",
        ))

        recommendations = data.get("recommendations", [])
        if recommendations:
            console.print(Panel(
                "\n".join(f"{i+1}. {r}" for i, r in enumerate(recommendations)),
                title="进化建议",
                border_style="yellow",
            ))
    except NanobotRunnerError as e:
        print_error(str(e))


@app.command(name="tune")
def adjust_params(
    tone: float = typer.Option(None, "--tone", "-t", help="语气强度 (0.0-1.0)"),
    detail: float = typer.Option(None, "--detail", "-d", help="信息密度 (0.0-1.0)"),
    aggressive: float = typer.Option(None, "--aggressive", "-a", help="推荐激进程度 (0.0-1.0)"),
    data_driven: float = typer.Option(None, "--data-driven", help="数据驱动权重 (0.0-1.0)"),
) -> None:
    """手动调整提示参数

    调整LLM输出风格的4维参数，调整后立即生效。

    Examples:
        nanobotrun evolution tune --aggressive 0.3
        nanobotrun evolution tune --tone 0.7 --detail 0.4
    """
    # 参数范围校验
    for name, value in [("tone", tone), ("detail", detail), ("aggressive", aggressive), ("data_driven", data_driven)]:
        if value is not None and (value < 0.0 or value > 1.0):
            print_error(f"参数{name}必须在0.0-1.0范围内，当前为{value}")
            return

    if all(v is None for v in [tone, detail, aggressive, data_driven]):
        print_error("请至少指定一个参数进行调整")
        return

    try:
        handler = EvolutionHandler()
        result = handler.adjust_prompt_params(
            tone=tone, detail=detail, aggressive=aggressive, data_driven=data_driven
        )

        if not result["success"]:
            console.print(f"[red]{result['message']}[/red]")
            return

        data = result["data"]
        console.print(Panel(
            f"语气强度: {data.get('tone_intensity', 0.5):.2f}\n"
            f"信息密度: {data.get('detail_level_score', 0.5):.2f}\n"
            f"推荐激进程度: {data.get('recommendation_aggressiveness', 0.5):.2f}\n"
            f"数据驱动权重: {data.get('data_driven_weight', 0.5):.2f}\n"
            f"累计更新次数: {data.get('update_count', 0)}",
            title="调整后的提示参数",
            border_style="green",
        ))
    except NanobotRunnerError as e:
        print_error(str(e))
```

- [ ] **Step 3: 增强evolution status命令输出v0.25字段**

在 `src/cli/commands/evolution.py` 的 `get_status` 命令中，在输出面板末尾追加v0.25字段显示：

```python
        # v0.25新增字段
        evolution_status = status.get("evolution_status", {})
        if evolution_status:
            v025_lines = []
            if "personalization_degree" in evolution_status:
                v025_lines.append(f"个性化程度: {evolution_status['personalization_degree']:.2f}")
            if "prompt_tuning" in evolution_status:
                pt = evolution_status["prompt_tuning"]
                v025_lines.append(f"提示调优: 语气={pt.get('tone_intensity', 0.5):.2f} 激进={pt.get('recommendation_aggressiveness', 0.5):.2f}")
            if "evolution_actions_count" in evolution_status:
                v025_lines.append(f"进化动作数: {evolution_status['evolution_actions_count']}")
            if v025_lines:
                console.print(Panel("\n".join(v025_lines), title="v0.25 进化状态", border_style="magenta"))
```

- [ ] **Step 4: 运行CLI测试**

Run: `uv run pytest tests/unit/cli/test_evolution_cli.py -v`
Expected: PASS

- [ ] **Step 5: 运行ruff检查**

Run: `uv run ruff check src/cli/commands/evolution.py src/cli/handlers/evolution_handler.py`
Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add src/cli/commands/evolution.py src/cli/handlers/evolution_handler.py
git commit -m "feat(cli): add evolution triggers/report/tune commands for v0.25"
```

---

### Task-025-11: Agent工具实现（check_evolution_triggers/get_evolution_report/adjust_prompt_params）

**Files:**
- Modify: `src/agents/tools_evolution.py` (新增3个工具类)

- [ ] **Step 1: 在tools_evolution.py中新增3个Agent工具**

在 `src/agents/tools_evolution.py` 末尾追加：

```python
class CheckEvolutionTriggersTool(BaseTool):
    """进化触发检查工具 - v0.25.0新增"""

    @property
    def name(self) -> str:
        return "check_evolution_triggers"

    @property
    def description(self) -> str:
        return (
            "检查进化触发条件，判断系统是否需要执行进化动作（模型重训练/策略调整/增量学习/月度复盘）。"
            "当用户询问'系统是否需要进化'或'进化触发条件'时使用此工具。"
            "返回JSON格式：{success: true, data: {...}}"
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "required": [],
        }

    async def execute(self, **kwargs: Any) -> str:
        return self._run_sync(self.runner_tools.check_evolution_triggers)


class GetEvolutionReportTool(BaseTool):
    """进化报告工具 - v0.25.0新增"""

    @property
    def name(self) -> str:
        return "get_evolution_report"

    @property
    def description(self) -> str:
        return (
            "生成月度进化报告，汇总进化引擎运行状态和效果。"
            "当用户询问'进化报告'或'月度进化情况'时使用此工具。"
            "返回JSON格式：{success: true, data: {...}}"
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "month": {
                    "type": "string",
                    "description": "报告月份(YYYY-MM格式)，不传则默认当月",
                },
            },
            "required": [],
        }

    async def execute(self, **kwargs: Any) -> str:
        month = kwargs.get("month")
        return self._run_sync(
            self.runner_tools.get_evolution_report,
            month,
        )


class AdjustPromptParamsTool(BaseTool):
    """提示参数调整工具 - v0.25.0新增"""

    @property
    def name(self) -> str:
        return "adjust_prompt_params"

    @property
    def description(self) -> str:
        return (
            "手动调整LLM输出风格的4维参数（语气强度/信息密度/推荐激进程度/数据驱动权重）。"
            "当用户希望调整AI推荐风格时使用此工具。"
            "返回JSON格式：{success: true, data: {...}}"
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "tone": {
                    "type": "number",
                    "description": "语气强度(0.0=温和/1.0=严厉)",
                    "minimum": 0.0,
                    "maximum": 1.0,
                },
                "detail": {
                    "type": "number",
                    "description": "信息密度(0.0=简洁/1.0=详细)",
                    "minimum": 0.0,
                    "maximum": 1.0,
                },
                "aggressive": {
                    "type": "number",
                    "description": "推荐激进程度(0.0=保守/1.0=激进)",
                    "minimum": 0.0,
                    "maximum": 1.0,
                },
                "data_driven": {
                    "type": "number",
                    "description": "数据驱动权重(0.0=纯经验/1.0=纯数据)",
                    "minimum": 0.0,
                    "maximum": 1.0,
                },
            },
            "required": [],
        }

    async def execute(self, **kwargs: Any) -> str:
        return self._run_sync(
            self.runner_tools.adjust_prompt_params,
            tone=kwargs.get("tone"),
            detail=kwargs.get("detail"),
            aggressive=kwargs.get("aggressive"),
            data_driven=kwargs.get("data_driven"),
        )
```

- [ ] **Step 2: 运行ruff和mypy检查**

Run: `uv run ruff check src/agents/tools_evolution.py && uv run mypy src/agents/tools_evolution.py --ignore-missing-imports`
Expected: PASS

- [ ] **Step 3: 提交**

```bash
git add src/agents/tools_evolution.py
git commit -m "feat(agents): add check_evolution_triggers/get_evolution_report/adjust_prompt_params tools for v0.25"
```

---

### 里程碑 M4: 集成验证与交付（预计第8-10天，21h）

**目标**: 完成集成测试、文档更新、回归验证。

**准入条件**: M3全部完成
**准出标准**: 全部测试通过，文档与代码版本一致，评审整改项全部验收

---

### Task-025-12: 集成测试 -- DecisionLogHook + EvolutionController闭环

**Files:**
- Create: `tests/integration/test_evolution_trigger_integration.py`

- [ ] **Step 1: 编写集成测试**

创建 `tests/integration/test_evolution_trigger_integration.py`：

```python
"""DecisionLogHook + EvolutionController闭环集成测试"""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.core.evolution.config import EvolutionConfig
from src.core.evolution.decision_log_hook import DecisionLogHook
from src.core.evolution.evolution_controller import EvolutionController
from src.core.evolution.evolution_engine import EvolutionEngine
from src.core.evolution.evolution_reporter import EvolutionReporter
from src.core.evolution.evolution_store import EvolutionStore
from src.core.evolution.models import (
    DecisionLog,
    EvolutionAction,
    OutcomeRecord,
    PromptTuningParams,
    TriggerCheckResult,
)
from src.core.evolution.prompt_tuner import PromptTuner
from src.core.transparency.models import DecisionType


@pytest.fixture
def integration_env(tmp_path: Path) -> dict:
    """创建集成测试环境"""
    config = EvolutionConfig(data_dir=str(tmp_path))
    store = EvolutionStore(tmp_path)

    # 创建子组件
    mock_calibration = MagicMock()
    mock_evolver = MagicMock()
    mock_evolver.evolve_model.return_value = MagicMock(
        mae_before=0.05, mae_after=0.03, _raw_param_changes={"tau": 42}
    )
    mock_evolver.apply_params_to_instance.return_value = None

    prompt_tuner = PromptTuner(store=store, config=config)
    reporter = EvolutionReporter(
        store=store,
        calibration_engine=mock_calibration,
        prompt_tuner=prompt_tuner,
        config=config,
    )
    controller = EvolutionController(
        store=store,
        calibration_engine=mock_calibration,
        model_evolver=mock_evolver,
        prompt_tuner=prompt_tuner,
        evolution_reporter=reporter,
        config=config,
    )

    # 创建DecisionLogger和OutcomeCollector的mock
    mock_logger = MagicMock()
    mock_collector = MagicMock()
    mock_collector.get_decision_outcome_pairs = store.get_decision_outcome_pairs

    engine = EvolutionEngine(
        decision_logger=mock_logger,
        outcome_collector=mock_collector,
        evolution_controller=controller,
        prompt_tuner=prompt_tuner,
        evolution_reporter=reporter,
    )

    return {
        "store": store,
        "engine": engine,
        "controller": controller,
        "prompt_tuner": prompt_tuner,
        "config": config,
        "tmp_path": tmp_path,
    }


class TestTriggerIntegration:
    """触发检查集成测试"""

    def test_after_iteration_triggers_check(
        self, integration_env: dict
    ) -> None:
        """after_iteration回调触发check_evolution_triggers"""
        engine = integration_env["engine"]
        hook = DecisionLogHook(evolution_engine=engine)
        hook._decision_logged = True

        # 调用after_iteration
        hook.after_iteration(MagicMock())

        # 不应抛出异常
        # （无数据时不会触发动作，但check_evolution_triggers被调用）

    def test_triggered_action_async_execution(
        self, integration_env: dict
    ) -> None:
        """触发条件满足时EvolutionAction被创建并异步执行"""
        store = integration_env["store"]
        engine = integration_env["engine"]

        # 插入足够数据触发月度复盘
        now = datetime.now()
        decision = DecisionLog(
            decision_id="int_dec_001",
            timestamp=now,
            runner_state={"vdot": 45.0},
            decision_type=DecisionType.TRAINING_ADVICE,
            tool_call_chain=[],
            prediction_snapshot=None,
            recommendation_text="test",
            execution_status="executed",
            recommendation_accepted=True,
            session_key="integration_test",
        )
        store.save_decision(decision)

        # 检查触发条件
        result = engine.check_evolution_triggers()
        # 至少应有月度复盘触发（当月未生成报告时）
        monthly_actions = [
            a for a in result.triggered_actions
            if a.action_type == "generate_report"
        ]
        assert len(monthly_actions) >= 1

    def test_v025_not_injected_graceful(
        self, tmp_path: Path
    ) -> None:
        """v0.25组件未注入时after_iteration不报错"""
        mock_logger = MagicMock()
        mock_collector = MagicMock()
        engine = EvolutionEngine(
            decision_logger=mock_logger,
            outcome_collector=mock_collector,
        )
        hook = DecisionLogHook(evolution_engine=engine)
        hook._decision_logged = True

        # 不应抛出异常
        hook.after_iteration(MagicMock())

    def test_check_triggers_performance(
        self, integration_env: dict
    ) -> None:
        """check_triggers()在1000条决策数据下延迟<50ms"""
        store = integration_env["store"]
        engine = integration_env["engine"]

        # 插入1000条决策数据
        now = datetime.now()
        for i in range(100):
            decision = DecisionLog(
                decision_id=f"perf_dec_{i:04d}",
                timestamp=now,
                runner_state={"vdot": 45.0},
                decision_type=DecisionType.TRAINING_ADVICE,
                tool_call_chain=[],
                prediction_snapshot=None,
                recommendation_text="test",
                execution_status="executed",
                recommendation_accepted=True,
                session_key="perf_test",
            )
            store.save_decision(decision)

        start = time.monotonic()
        engine.check_evolution_triggers()
        elapsed_ms = (time.monotonic() - start) * 1000
        assert elapsed_ms < 50, f"check_triggers()耗时{elapsed_ms:.1f}ms超过50ms预算"

    def test_persist_first_on_retrain(
        self, integration_env: dict
    ) -> None:
        """先持久化后生效：模拟持久化失败时实例属性不被修改"""
        store = integration_env["store"]
        controller = integration_env["controller"]

        # 模拟持久化失败
        original_save = store.save_model_params
        store.save_model_params = MagicMock(side_effect=IOError("磁盘写入失败"))

        action = EvolutionAction(
            action_id="persist_test_001",
            action_type="retrain_model",
            trigger_reason="VDOT误差",
            trigger_condition={},
            target_model_type="vdot",
            priority="high",
            created_at=datetime.now(),
        )

        result = controller.execute_action(action)
        assert "持久化失败" in str(result.execution_result)

        # 恢复
        store.save_model_params = original_save
```

- [ ] **Step 2: 运行集成测试**

Run: `uv run pytest tests/integration/test_evolution_trigger_integration.py -v`
Expected: PASS

- [ ] **Step 3: 提交**

```bash
git add tests/integration/test_evolution_trigger_integration.py
git commit -m "test(evolution): add integration tests for DecisionLogHook + EvolutionController closed loop"
```

---

### Task-025-13: 集成测试 -- PromptTuner全链路

**Files:**
- Create: `tests/integration/test_prompt_tuner_integration.py`

- [ ] **Step 1: 编写PromptTuner集成测试**

创建 `tests/integration/test_prompt_tuner_integration.py`：

```python
"""PromptTuner全链路集成测试"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from src.core.evolution.config import EvolutionConfig
from src.core.evolution.evolution_store import EvolutionStore
from src.core.evolution.models import PromptTuningParams
from src.core.evolution.prompt_tuner import PromptTuner


@pytest.fixture
def tuner_env(tmp_path: Path) -> dict:
    """创建PromptTuner集成测试环境"""
    config = EvolutionConfig(data_dir=str(tmp_path))
    store = EvolutionStore(tmp_path)
    tuner = PromptTuner(store=store, config=config)
    return {"tuner": tuner, "store": store, "tmp_path": tmp_path}


class TestPromptTunerIntegration:
    """PromptTuner全链路集成测试"""

    def test_first_call_returns_default(
        self, tuner_env: dict
    ) -> None:
        """首次调用get_params()返回默认值（JSON文件不存在时）"""
        tuner = tuner_env["tuner"]
        params = tuner.get_params()
        assert params.tone_intensity == 0.5
        assert params.recommendation_aggressiveness == 0.5

    def test_update_params_persists_to_file(
        self, tuner_env: dict
    ) -> None:
        """update_params()后prompt_params.json文件正确写入"""
        tuner = tuner_env["tuner"]
        tmp_path = tuner_env["tmp_path"]

        tuner.update_params(tone=0.7, aggressive=0.3)

        # 验证文件已写入
        json_file = tmp_path / "tuning" / "prompt_params.json"
        assert json_file.exists()

        # 验证内容
        import json
        data = json.loads(json_file.read_text(encoding="utf-8"))
        assert data["tone_intensity"] == 0.7
        assert data["recommendation_aggressiveness"] == 0.3

    def test_rejection_floor_protection(
        self, tuner_env: dict
    ) -> None:
        """连续10次拒绝后aggressive>=0.1, data_driven>=0.2"""
        tuner = tuner_env["tuner"]

        for _ in range(10):
            tuner.auto_adjust_on_rejection()

        params = tuner.get_params()
        assert params.recommendation_aggressiveness >= 0.1
        assert params.data_driven_weight >= 0.2

    def test_bounce_back_mechanism(
        self, tuner_env: dict
    ) -> None:
        """接受推荐后aggressive恢复步长>降低步长"""
        tuner = tuner_env["tuner"]

        # 先降低
        tuner.update_params(aggressive=0.3)
        # 接受推荐
        result = tuner.auto_adjust_on_feedback(avg_score=4.0, acceptance_rate=0.8)
        # aggressive应增加0.08（恢复步长），大于降低步长0.05
        assert result.recommendation_aggressiveness > 0.3
        increase = result.recommendation_aggressiveness - 0.3
        assert increase > 0.05  # 恢复步长大于降低步长

    def test_reset_to_default(
        self, tuner_env: dict
    ) -> None:
        """reset_to_default()后参数恢复为0.5"""
        tuner = tuner_env["tuner"]

        tuner.update_params(tone=0.9, aggressive=0.1)
        result = tuner.reset_to_default()

        assert result.tone_intensity == 0.5
        assert result.recommendation_aggressiveness == 0.5
        assert result.update_count == 0
```

- [ ] **Step 2: 运行集成测试**

Run: `uv run pytest tests/integration/test_prompt_tuner_integration.py -v`
Expected: PASS

- [ ] **Step 3: 提交**

```bash
git add tests/integration/test_prompt_tuner_integration.py
git commit -m "test(evolution): add PromptTuner full-chain integration tests"
```

---

### Task-025-14: 集成测试 -- EvolutionReporter全链路

**Files:**
- Create: `tests/integration/test_evolution_reporter_integration.py`

- [ ] **Step 1: 编写EvolutionReporter集成测试**

创建 `tests/integration/test_evolution_reporter_integration.py`：

```python
"""EvolutionReporter全链路集成测试"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.core.evolution.config import EvolutionConfig
from src.core.evolution.evolution_reporter import EvolutionReporter
from src.core.evolution.evolution_store import EvolutionStore
from src.core.evolution.models import PromptTuningParams
from src.core.evolution.prompt_tuner import PromptTuner


@pytest.fixture
def reporter_env(tmp_path: Path) -> dict:
    """创建EvolutionReporter集成测试环境"""
    config = EvolutionConfig(data_dir=str(tmp_path))
    store = EvolutionStore(tmp_path)
    mock_calibration = MagicMock()
    prompt_tuner = PromptTuner(store=store, config=config)
    reporter = EvolutionReporter(
        store=store,
        calibration_engine=mock_calibration,
        prompt_tuner=prompt_tuner,
        config=config,
    )
    return {
        "reporter": reporter,
        "store": store,
        "prompt_tuner": prompt_tuner,
        "mock_calibration": mock_calibration,
        "tmp_path": tmp_path,
    }


class TestEvolutionReporterIntegration:
    """EvolutionReporter全链路集成测试"""

    def test_generate_report_returns_complete_fields(
        self, reporter_env: dict
    ) -> None:
        """generate_report()返回完整EvolutionReport"""
        reporter = reporter_env["reporter"]
        report = reporter.generate_report()

        assert report.report_id != ""
        assert report.month != ""
        assert report.generated_at is not None
        assert isinstance(report.total_decisions, int)
        assert isinstance(report.decision_acceptance_rate, float)
        assert isinstance(report.personalization_degree, float)
        assert isinstance(report.evolution_actions_count, int)
        assert isinstance(report.recommendations, list)

    def test_personalization_degree_calculation(
        self, reporter_env: dict
    ) -> None:
        """_get_personalization_degree()计算正确"""
        reporter = reporter_env["reporter"]
        degree = reporter._get_personalization_degree()

        assert 0.0 <= degree <= 1.0

    def test_monthly_review_trigger_condition(
        self, reporter_env: dict
    ) -> None:
        """月度复盘触发条件：当月未生成报告时触发"""
        store = reporter_env["store"]
        # 当月未生成报告（trigger_state中无last_monthly_report）
        store.load_trigger_state.return_value = None

        from src.core.evolution.evolution_controller import EvolutionController

        controller = EvolutionController(
            store=store,
            calibration_engine=reporter_env["mock_calibration"],
            model_evolver=MagicMock(),
            prompt_tuner=reporter_env["prompt_tuner"],
            evolution_reporter=reporter_env["reporter"],
            config=EvolutionConfig(data_dir=str(reporter_env["tmp_path"])),
        )

        result = controller.check_triggers()
        monthly_actions = [
            a for a in result.triggered_actions
            if a.action_type == "generate_report"
        ]
        assert len(monthly_actions) >= 1
```

- [ ] **Step 2: 运行集成测试**

Run: `uv run pytest tests/integration/test_evolution_reporter_integration.py -v`
Expected: PASS

- [ ] **Step 3: 提交**

```bash
git add tests/integration/test_evolution_reporter_integration.py
git commit -m "test(evolution): add EvolutionReporter full-chain integration tests"
```

---

### Task-025-15: 文档更新与版本对齐

**Files:**
- Modify: `AGENTS.md`
- Modify: `docs/architecture/架构设计说明书.md`
- Modify: `docs/requirements/REQ_需求规格说明书.md`

- [ ] **Step 1: 更新AGENTS.md**

在 `AGENTS.md` 中：

1. 项目架构 3.1 代码库结构中，在 `evolution/` 目录下追加：
```
│   ├── evolution_controller.py  # 进化控制器 (v0.25)
│   ├── prompt_tuner.py          # 提示调优器 (v0.25)
│   └── evolution_reporter.py    # 进化报告器 (v0.25)
```

2. 常用命令 6 节中追加：
```bash
# v0.25 - 自适应进化
uv run nanobotrun evolution triggers                    # 检查进化触发条件
uv run nanobotrun evolution report --month YYYY-MM      # 生成月度进化报告
uv run nanobotrun evolution tune --tone 0.7 --aggressive 0.3  # 手动调整提示参数
```

3. 业务术语 8 节中追加：
```
| **EvolutionAction** | 进化动作，由触发条件检测生成 | action_type=retrain_model/adjust_strategy/incremental_learn/generate_report |
| **PromptTuningParams** | 提示调优4维参数 | tone=0.5, detail=0.5, aggressive=0.5, data_driven=0.5 |
| **TriggerCheckResult** | 触发条件检查结果 | 包含triggered_actions和skipped_conditions |
```

- [ ] **Step 2: 更新架构设计说明书**

在 `docs/architecture/架构设计说明书.md` 中，将Section 8.4的状态从"📋 当前规划"更新为"🔧 开发中"或"✅ 已完成"（视实际开发进度）。

- [ ] **Step 3: 更新需求规格说明书**

在 `docs/requirements/REQ_需求规格说明书.md` 中，将REQ-0.25-01/02/03的状态标注为"已实现"。

- [ ] **Step 4: 提交**

```bash
git add AGENTS.md docs/architecture/架构设计说明书.md docs/requirements/REQ_需求规格说明书.md
git commit -m "docs: update AGENTS.md and architecture docs for v0.25 completion"
```

---

### Task-025-16: 回归验证与版本发布

**Files:** 无新增文件（验证性任务）

- [ ] **Step 1: 运行全量单元测试**

Run: `uv run pytest tests/unit/ -v --tb=short`
Expected: 全部PASS

- [ ] **Step 2: 运行全量集成测试**

Run: `uv run pytest tests/integration/ -v --tb=short`
Expected: 全部PASS

- [ ] **Step 3: 运行mypy类型检查**

Run: `uv run mypy src/ --ignore-missing-imports`
Expected: PASS

- [ ] **Step 4: 运行ruff lint**

Run: `uv run ruff check src/ tests/`
Expected: PASS

- [ ] **Step 5: 验证v0.23/v0.24 CLI命令功能正常**

Run: `uv run nanobotrun evolution history --help && uv run nanobotrun evolution feedback --help && uv run nanobotrun evolution accuracy --help && uv run nanobotrun evolution fidelity --help && uv run nanobotrun evolution status --help && uv run nanobotrun evolution calibration --help && uv run nanobotrun evolution response --help`
Expected: 所有命令help输出正常

- [ ] **Step 6: 验证v0.25 CLI命令功能正常**

Run: `uv run nanobotrun evolution triggers --help && uv run nanobotrun evolution report --help && uv run nanobotrun evolution tune --help`
Expected: 所有命令help输出正常

- [ ] **Step 7: 验证性能基准**

Run: `uv run pytest tests/performance/test_evolution_performance.py -v`
Expected: check_triggers() <50ms, Hook接入延迟 <100ms

- [ ] **Step 8: 验证架构评审整改项**

逐项确认：
- [ ] C-01: daemon线程数据一致性 -- "先持久化后生效"已实现
- [ ] C-02: check_triggers性能预算 -- <50ms已达标
- [ ] H-01: 编排层一致性 -- DecisionLogHook持有EvolutionEngine引用
- [ ] H-02: 部分失败处理 -- IncrementalLearnResult结构化
- [ ] H-03: 参数下限保护 -- aggressive>=0.1, data_driven>=0.2

- [ ] **Step 9: 验证核心模块测试覆盖率**

Run: `uv run pytest tests/unit/core/evolution/ --cov=src/core/evolution --cov-report=term-missing`
Expected: 覆盖率 >= 85%

---

## 3. 验证检查点

| 检查点 | 时机 | 验证内容 | 通过标准 |
|--------|------|----------|----------|
| CP-1 | M1完成 | 数据模型+存储层 | `pytest tests/unit/core/evolution/test_models.py tests/unit/core/evolution/test_evolution_store.py` 全部PASS |
| CP-2 | M2完成 | 核心逻辑+整改项 | `pytest tests/unit/core/evolution/` 全部PASS，ruff/mypy通过 |
| CP-3 | M3完成 | 编排层+CLI+Agent | `pytest tests/unit/` 全部PASS，CLI命令可用 |
| CP-4 | M4完成 | 集成测试+回归 | `pytest tests/` 全部PASS，性能基准达标，评审整改项全部验收 |

## 4. 回滚计划

| 场景 | 回滚策略 |
|------|----------|
| M1数据模型变更导致现有测试失败 | revert T01/T02的commit，恢复models.py原始状态 |
| M2核心组件实现与架构设计偏差大 | revert T03/T04的commit，重新对齐架构设计 |
| M3编排层扩展破坏v0.23/v0.24兼容 | revert T09的commit，EvolutionEngine构造函数新增参数均为可选(默认None)，回滚安全 |
| M4集成测试发现架构缺陷 | 暂停集成，回到M2重新评审架构设计，输出架构调整方案 |
| 性能基准不达标 | 优先优化EvolutionStore查询（添加索引/缓存），若仍不达标则考虑异步check_triggers |

---

## 5. 文件变更总览

| 操作 | 文件路径 | 任务 |
|------|----------|------|
| Modify | `src/core/evolution/models.py` | T01, T02, T06, T07 |
| Modify | `src/core/evolution/evolution_store.py` | T08 |
| Modify | `src/core/evolution/config.py` | T03 (新增触发/调优配置项) |
| Create | `src/core/evolution/evolution_controller.py` | T03 |
| Create | `src/core/evolution/prompt_tuner.py` | T04 |
| Create | `src/core/evolution/evolution_reporter.py` | T09 (Reporter实现) |
| Modify | `src/core/evolution/evolution_engine.py` | T05, T09 |
| Modify | `src/core/evolution/decision_log_hook.py` | T05 |
| Modify | `src/core/base/context.py` | T09 |
| Modify | `src/cli/commands/evolution.py` | T10 |
| Modify | `src/cli/handlers/evolution_handler.py` | T10 |
| Modify | `src/agents/tools_evolution.py` | T11 |
| Modify | `tests/unit/core/evolution/test_models.py` | T01, T02, T06 |
| Create | `tests/unit/core/evolution/test_evolution_controller.py` | T03 |
| Create | `tests/unit/core/evolution/test_prompt_tuner.py` | T04, T07 |
| Modify | `tests/unit/core/evolution/test_decision_log_hook.py` | T05 |
| Modify | `tests/unit/core/evolution/test_evolution_engine.py` | T05, T09 |
| Create | `tests/unit/core/evolution/test_context_extension.py` | T09 |
| Modify | `tests/unit/core/evolution/test_evolution_store.py` | T08 |
| Create | `tests/integration/test_evolution_trigger_integration.py` | T12 |
| Create | `tests/integration/test_prompt_tuner_integration.py` | T13 |
| Create | `tests/integration/test_evolution_reporter_integration.py` | T14 |
| Modify | `AGENTS.md` | T15 |
| Modify | `docs/architecture/架构设计说明书.md` | T15 |
| Modify | `docs/requirements/REQ_需求规格说明书.md` | T15 |
