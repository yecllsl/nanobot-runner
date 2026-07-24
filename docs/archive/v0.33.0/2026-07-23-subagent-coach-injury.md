# Subagent 教练+伤病预防师 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 扩展 v0.17.0 `spawn_subagent` 模式，新增 `coach`（教练）和 `injury_prevention`（伤病预防师）两个 subagent 角色，复用 nanobot-ai 0.2.2 原生 SpawnTool，不引入编排器。

**Architecture:** 主 Agent 通过 `spawn_subagent` 工具调用新角色，RunnerTools 预查询数据 + 记忆文档拼装 task，经 `SpawnSubagentTool` 交给 nanobot 底座后台执行，结果通过 MessageBus 回注主会话。角色定义是纯数据（`subagent_roles.py`），无新抽象。

**Tech Stack:** Python 3.11+ / nanobot-ai 0.2.2 / pytest / Polars / 现有 RunnerTools 工具集

## Global Constraints

- 不改动 nanobot-ai 底座 `SpawnTool` / `SubagentManager`（原生能力够用）
- 不改动现有 `data_analyst` / `report_writer`（向后兼容）
- 上下文限制 8000 字符（`SpawnSubagentTool.MAX_CONTEXT_LENGTH`）
- 所有新增方法遵循 snake_case，类名 PascalCase
- 记忆文档存储于 `~/.nanobot-runner/memory/subagents/{role}.json`
- 不引入新依赖
- 遵循 TDD：先写失败测试 → 写最少实现 → 重构

---

### Task 1: 新建 subagent_roles.py 角色定义模块

**Files:**
- Create: `src/agents/subagent_roles.py`
- Test: `tests/unit/agents/test_subagent_roles.py`

**Interfaces:**
- Consumes: `SpawnSubagentTool.CONTEXT_SEPARATOR` / `CONTEXT_END` / `MAX_CONTEXT_LENGTH`（来自 `src/agents/tools_twin.py`）
- Produces: `SubagentRole` 数据类、`ROLES` 注册表、`COACH_PROMPT`、`INJURY_PROMPT`、`build_task()` 方法

- [ ] **Step 1: 创建测试目录并写失败测试**

创建 `tests/unit/agents/test_subagent_roles.py`：

```python
"""subagent_roles 模块单元测试"""
from __future__ import annotations

import json

import pytest

from src.agents.subagent_roles import (
    COACH_PROMPT,
    INJURY_PROMPT,
    ROLES,
    SubagentRole,
)


class TestSubagentRole:
    """SubagentRole 数据类测试"""

    def test_role_build_task_contains_prompt(self):
        """build_task 输出应包含角色 prompt 片段"""
        role = ROLES["coach"]
        task = role.build_task("帮我分析训练", {"vdot": 45.2})
        assert "教练" in task
        assert COACH_PROMPT.split("\n")[0] in task

    def test_role_build_task_contains_user_request(self):
        """build_task 输出应包含用户请求"""
        role = ROLES["injury_prevention"]
        task = role.build_task("膝盖不舒服", {"risk": "low"})
        assert "膝盖不舒服" in task

    def test_role_build_task_contains_context_separator(self):
        """build_task 输出应包含数据上下文分隔符"""
        role = ROLES["coach"]
        task = role.build_task("请求", {"data": 1})
        assert "---数据上下文---" in task
        assert "---数据上下文结束---" in task

    def test_role_build_task_under_8000(self):
        """正常数据量下 task 应小于 8000 字符"""
        role = ROLES["coach"]
        normal_context = {"vdot": 45.2, "load": {"atl": 50, "ctl": 60}}
        task = role.build_task("分析训练", normal_context)
        assert len(task) < 8000

    def test_role_build_task_serializes_dict(self):
        """build_task 应将 dict 序列化为 JSON"""
        role = ROLES["coach"]
        task = role.build_task("请求", {"key": "值"})
        assert '"key"' in task
        assert "值" in task


class TestRolesRegistry:
    """ROLES 注册表测试"""

    def test_roles_registry_contains_coach(self):
        assert "coach" in ROLES
        assert isinstance(ROLES["coach"], SubagentRole)

    def test_roles_registry_contains_injury_prevention(self):
        assert "injury_prevention" in ROLES
        assert isinstance(ROLES["injury_prevention"], SubagentRole)

    def test_coach_role_name_matches_key(self):
        assert ROLES["coach"].name == "coach"

    def test_injury_role_name_matches_key(self):
        assert ROLES["injury_prevention"].name == "injury_prevention"

    def test_coach_prompt_mentions_vdot(self):
        """教练 prompt 应提及 VDOT（核心数据源）"""
        assert "VDOT" in COACH_PROMPT

    def test_injury_prompt_mentions_risk(self):
        """伤病预防师 prompt 应提及风险预测"""
        assert "风险" in INJURY_PROMPT or "伤病" in INJURY_PROMPT

    def test_roles_count_is_two(self):
        """MVP 阶段 ROLES 仅含 2 个新角色（不包含旧 data_analyst/report_writer）"""
        assert len(ROLES) == 2
```

- [ ] **Step 2: 运行测试验证失败**

Run: `uv run pytest tests/unit/agents/test_subagent_roles.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.agents.subagent_roles'`

- [ ] **Step 3: 创建 subagent_roles.py 实现**

创建 `src/agents/subagent_roles.py`：

```python
"""Subagent 角色定义模块

定义专业 subagent 的角色 prompt 和注册表。每个角色是纯数据（SubagentRole），
由 RunnerTools 在 _prepare_subagent_context 中按角色预查询数据，
再通过 build_task 拼装为 nanobot-ai SpawnTool 可识别的 task 字符串。

设计原则（ponytail）：
- 纯数据，无抽象，无反射调用
- 新增角色 = 在 ROLES 加一条
- prompt 片段由 build_task 注入 task 开头，subagent 按.task 行事
"""

from __future__ import annotations

import json
from dataclasses import dataclass

# 复用 SpawnSubagentTool 的上下文分隔符常量（保持与 v0.17.0 模式一致）
CONTEXT_SEPARATOR: str = "\n---数据上下文---\n"
CONTEXT_END: str = "\n---数据上下文结束---"


# 教练角色系统 prompt 片段
COACH_PROMPT: str = """你是资深跑步教练，专精于基于 VDOT 和训练负荷数据的训练计划制定。
你的职责：
- 分析近期训练数据，给出配速和训练量建议
- 基于数字孪生推演结果，推荐训练方案
- 调整训练计划以逼近用户目标赛事
你不负责伤病诊断、营养建议、装备选择。
输出格式：结构化建议 + 理由 + 可执行动作。"""


# 伤病预防师角色系统 prompt 片段
INJURY_PROMPT: str = """你是运动医学背景的伤病预防师，基于伤病风险预测模型和身体信号数据工作。
你的职责：
- 解读伤病风险预测结果（ML/参数化/规则三层降级）
- 识别急性负荷过高、HRV 异常、心率漂移过大等风险信号
- 给出恢复建议（休息/减量/交叉训练）
- 标记需要停止训练的红线信号
你不负责训练计划制定、营养建议。
输出格式：风险等级 + 风险因素 + 恢复建议 + 红线警告（如有）。"""


@dataclass(frozen=True)
class SubagentRole:
    """Subagent 角色定义（纯数据）

    Attributes:
        name: 角色名（与 ROLES key 一致，用于 spawn_subagent 的 subagent_type 参数）
        prompt: 角色系统 prompt 片段，注入 task 开头定义 subagent 行为
        context_builders: 预查询方法名元组（文档性，MVP 不做反射调用）
    """

    name: str
    prompt: str
    context_builders: tuple[str, ...]

    def build_task(self, user_request: str, context_data: dict) -> str:
        """拼装 task：角色 prompt + 用户请求 + 数据上下文

        Args:
            user_request: 用户原始请求
            context_data: 预查询数据字典（含 memory 字段）

        Returns:
            str: 组装后的 task 字符串，格式：
                {prompt}\n\n用户请求：{request}\n---数据上下文---\n{json}\n---数据上下文结束---
        """
        return (
            f"{self.prompt}\n\n"
            f"用户请求：{user_request}\n"
            f"{CONTEXT_SEPARATOR}"
            f"{json.dumps(context_data, ensure_ascii=False, default=str, indent=2)}"
            f"{CONTEXT_END}"
        )


# 角色注册表：新增角色在此添加一条即可
ROLES: dict[str, SubagentRole] = {
    "coach": SubagentRole(
        name="coach",
        prompt=COACH_PROMPT,
        context_builders=(
            "get_vdot_trend",
            "get_training_load",
            "get_recent_runs",
            "_get_plan_status_safe",
            "_load_subagent_memory",
        ),
    ),
    "injury_prevention": SubagentRole(
        name="injury_prevention",
        prompt=INJURY_PROMPT,
        context_builders=(
            "predict_injury_risk",
            "get_hrv_analysis",
            "get_fatigue_score",
            "get_recovery_status",
            "get_hr_drift_analysis",
            "get_training_load",
            "_load_subagent_memory",
        ),
    ),
}
```

- [ ] **Step 4: 运行测试验证通过**

Run: `uv run pytest tests/unit/agents/test_subagent_roles.py -v`
Expected: 11 passed

- [ ] **Step 5: 提交**

```bash
git add src/agents/subagent_roles.py tests/unit/agents/test_subagent_roles.py
git commit -m "feat(agents): 新增 subagent_roles 模块定义教练与伤病预防师角色"
```

---

### Task 2: RunnerTools 新增记忆加载与计划状态查询方法

**Files:**
- Modify: `src/agents/tools.py`（RunnerTools 类，在 `_prepare_subagent_context` 方法前插入新私有方法）
- Test: `tests/unit/agents/test_runner_tools_memory.py`

**Interfaces:**
- Consumes: `ConfigManager.base_dir`（来自 `src/core/config/manager.py`）、`AppContext.plan_manager`（来自 `src/core/base/context.py`）
- Produces: `RunnerTools._load_subagent_memory(role) -> dict`、`RunnerTools._get_plan_status_safe() -> dict | None`

- [ ] **Step 1: 写失败测试**

创建 `tests/unit/agents/test_runner_tools_memory.py`：

```python
"""RunnerTools 记忆加载与计划状态查询单元测试"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.agents.tools import RunnerTools


class TestLoadSubagentMemory:
    """_load_subagent_memory 方法测试"""

    def test_load_memory_missing_file_returns_empty(self, tmp_path: Path):
        """记忆文件不存在时返回空 dict"""
        with patch.object(RunnerTools, "__init__", lambda self, ctx=None: None):
            tools = RunnerTools()
            tools._runner_config = MagicMock()
            tools._runner_config.base_dir = tmp_path
            result = tools._load_subagent_memory("coach")
        assert result == {}

    def test_load_memory_valid_json_returns_dict(self, tmp_path: Path):
        """有效 JSON 文件返回解析后的 dict"""
        memory_dir = tmp_path / "memory" / "subagents"
        memory_dir.mkdir(parents=True)
        (memory_dir / "coach.json").write_text(
            json.dumps({"user_goal": "全马破4"}, ensure_ascii=False),
            encoding="utf-8",
        )
        with patch.object(RunnerTools, "__init__", lambda self, ctx=None: None):
            tools = RunnerTools()
            tools._runner_config = MagicMock()
            tools._runner_config.base_dir = tmp_path
            result = tools._load_subagent_memory("coach")
        assert result == {"user_goal": "全马破4"}

    def test_load_memory_corrupt_json_returns_empty(self, tmp_path: Path):
        """损坏的 JSON 返回空 dict"""
        memory_dir = tmp_path / "memory" / "subagents"
        memory_dir.mkdir(parents=True)
        (memory_dir / "coach.json").write_text("{invalid json", encoding="utf-8")
        with patch.object(RunnerTools, "__init__", lambda self, ctx=None: None):
            tools = RunnerTools()
            tools._runner_config = MagicMock()
            tools._runner_config.base_dir = tmp_path
            result = tools._load_subagent_memory("coach")
        assert result == {}

    def test_load_memory_unknown_role_returns_empty(self, tmp_path: Path):
        """未知角色返回空 dict"""
        with patch.object(RunnerTools, "__init__", lambda self, ctx=None: None):
            tools = RunnerTools()
            tools._runner_config = MagicMock()
            tools._runner_config.base_dir = tmp_path
            result = tools._load_subagent_memory("unknown_role")
        assert result == {}


class TestGetPlanStatusSafe:
    """_get_plan_status_safe 方法测试"""

    def test_get_plan_status_no_plan_manager_returns_none(self):
        """无 plan_manager 时返回 None"""
        with patch.object(RunnerTools, "__init__", lambda self, ctx=None: None):
            tools = RunnerTools()
            tools._context = MagicMock()
            tools._context.plan_manager = None
            result = tools._get_plan_status_safe()
        assert result is None

    def test_get_plan_status_exception_returns_none(self):
        """plan_manager 抛异常时返回 None"""
        with patch.object(RunnerTools, "__init__", lambda self, ctx=None: None):
            tools = RunnerTools()
            tools._context = MagicMock()
            tools._context.plan_manager = MagicMock()
            tools._context.plan_manager.list_plans.side_effect = Exception("db error")
            result = tools._get_plan_status_safe()
        assert result is None
```

- [ ] **Step 2: 运行测试验证失败**

Run: `uv run pytest tests/unit/agents/test_runner_tools_memory.py -v`
Expected: FAIL with `AttributeError: 'RunnerTools' object has no attribute '_load_subagent_memory'`

- [ ] **Step 3: 修改 RunnerTools.__init__ 保存 context 和 config 引用**

在 `src/agents/tools.py` 的 `RunnerTools.__init__` 中（约第 125-137 行），在 `self.profile_storage = context.profile_storage` 之后新增：

```python
    def __init__(self, context: AppContext | None = None):
        """
        初始化工具集

        Args:
            context: 应用上下文（可选），未提供则使用全局上下文
        """
        if context is None:
            context = AppContextFactory.create()

        self.storage = context.storage
        self.analytics = context.analytics
        self.profile_storage = context.profile_storage
        # v0.33.0 新增：subagent 记忆与计划状态查询所需引用
        self._context = context
        self._runner_config = context.config
```

- [ ] **Step 4: 在 RunnerTools 类中新增私有方法**

在 `src/agents/tools.py` 的 `RunnerTools` 类中，`# ---- Subagent 方法 ----` 注释块（约第 1441 行）之前插入：

```python
    # ----------------------------------------------------------------
    # Subagent 记忆与上下文辅助方法（v0.33.0 新增）
    # ----------------------------------------------------------------

    def _load_subagent_memory(self, role: str) -> dict[str, Any]:
        """加载 subagent 记忆文档

        从 ~/.nanobot-runner/memory/subagents/{role}.json 读取。
        文件不存在或 JSON 损坏时返回空 dict（宽容读取，不抛异常）。

        Args:
            role: 角色名（如 "coach" / "injury_prevention"）

        Returns:
            dict: 记忆数据，失败时返回 {}
        """
        try:
            memory_path = (
                self._runner_config.base_dir / "memory" / "subagents" / f"{role}.json"
            )
            if not memory_path.exists():
                return {}
            return json.loads(memory_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError) as e:
            logger.warning("加载 subagent 记忆失败 role=%s: %s", role, e)
            return {}

    def _get_plan_status_safe(self) -> dict[str, Any] | None:
        """安全查询当前训练计划状态

        通过 plan_manager 查询最近的计划。无计划或查询失败时返回 None。

        Returns:
            dict | None: 计划状态，失败时返回 None
        """
        try:
            plan_manager = getattr(self._context, "plan_manager", None)
            if plan_manager is None:
                return None
            # 尝试获取计划列表（plan_manager 接口可能因版本而异，宽容处理）
            plans = plan_manager.list_plans() if hasattr(plan_manager, "list_plans") else []
            if not plans:
                return None
            # 取最近一条计划的状态摘要
            latest = plans[-1] if isinstance(plans, list) else None
            if latest is None:
                return None
            return {"plan_id": getattr(latest, "plan_id", str(latest))}
        except Exception as e:
            logger.warning("查询计划状态失败: %s", e)
            return None
```

- [ ] **Step 5: 运行测试验证通过**

Run: `uv run pytest tests/unit/agents/test_runner_tools_memory.py -v`
Expected: 6 passed

- [ ] **Step 6: 提交**

```bash
git add src/agents/tools.py tests/unit/agents/test_runner_tools_memory.py
git commit -m "feat(agents): RunnerTools 新增 subagent 记忆加载与计划状态查询方法"
```

---

### Task 3: _prepare_subagent_context 新增 coach 与 injury_prevention 分支

**Files:**
- Modify: `src/agents/tools.py`（`_prepare_subagent_context` 方法，约第 1525-1588 行）
- Test: `tests/unit/agents/test_prepare_subagent_context_new_roles.py`

**Interfaces:**
- Consumes: Task 1 的 `ROLES`、Task 2 的 `_load_subagent_memory` / `_get_plan_status_safe`
- Produces: 扩展后的 `_prepare_subagent_context`，支持 `subagent_type="coach"` 和 `"injury_prevention"`

- [ ] **Step 1: 写失败测试**

创建 `tests/unit/agents/test_prepare_subagent_context_new_roles.py`：

```python
"""_prepare_subagent_context 新角色分支单元测试"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.agents.tools import RunnerTools


@pytest.fixture
def runner_tools():
    """构造带 mock 依赖的 RunnerTools"""
    with patch.object(RunnerTools, "__init__", lambda self, ctx=None: None):
        tools = RunnerTools()
        tools._context = MagicMock()
        tools._runner_config = MagicMock()
        tools._runner_config.base_dir = MagicMock()
        tools._runner_config.base_dir.__truediv__ = MagicMock(return_value=MagicMock())
        # mock 业务方法
        tools.get_vdot_trend = MagicMock(return_value={"vdot": 45.2})
        tools.get_training_load = MagicMock(return_value={"atl": 50, "ctl": 60})
        tools.get_recent_runs = MagicMock(return_value=[{"distance_km": 10}])
        tools.predict_injury_risk = MagicMock(
            return_value={"success": True, "data": {"risk_level": "low"}}
        )
        tools.get_hrv_analysis = MagicMock(return_value={"rmssd": 35.0})
        tools.get_fatigue_score = MagicMock(return_value={"score": 3})
        tools.get_recovery_status = MagicMock(return_value={"status": "good"})
        tools.get_hr_drift_analysis = MagicMock(return_value={"drift": 5.0})
        tools._load_subagent_memory = MagicMock(return_value={"user_goal": "marathon"})
        tools._get_plan_status_safe = MagicMock(return_value={"plan_id": "p1"})
        return tools


class TestPrepareCoachContext:
    """教练角色预查询测试"""

    def test_coach_context_contains_vdot(self, runner_tools: RunnerTools):
        ctx = runner_tools._prepare_subagent_context(
            subagent_type="coach", user_request="分析训练"
        )
        assert "vdot_trend" in ctx
        assert ctx["vdot_trend"] == {"vdot": 45.2}

    def test_coach_context_contains_training_load(self, runner_tools: RunnerTools):
        ctx = runner_tools._prepare_subagent_context(
            subagent_type="coach", user_request="分析训练"
        )
        assert "training_load" in ctx

    def test_coach_context_contains_recent_runs(self, runner_tools: RunnerTools):
        ctx = runner_tools._prepare_subagent_context(
            subagent_type="coach", user_request="分析训练"
        )
        assert "recent_runs" in ctx

    def test_coach_context_contains_plan_status(self, runner_tools: RunnerTools):
        ctx = runner_tools._prepare_subagent_context(
            subagent_type="coach", user_request="分析训练"
        )
        assert ctx["plan_status"] == {"plan_id": "p1"}

    def test_coach_context_contains_memory(self, runner_tools: RunnerTools):
        ctx = runner_tools._prepare_subagent_context(
            subagent_type="coach", user_request="分析训练"
        )
        assert ctx["memory"] == {"user_goal": "marathon"}

    def test_coach_context_contains_user_request(self, runner_tools: RunnerTools):
        ctx = runner_tools._prepare_subagent_context(
            subagent_type="coach", user_request="帮我安排下周训练"
        )
        assert ctx["user_request"] == "帮我安排下周训练"


class TestPrepareInjuryContext:
    """伤病预防师角色预查询测试"""

    def test_injury_context_contains_injury_risk(self, runner_tools: RunnerTools):
        ctx = runner_tools._prepare_subagent_context(
            subagent_type="injury_prevention", user_request="膝盖不舒服"
        )
        assert "injury_risk" in ctx
        assert ctx["injury_risk"]["success"] is True

    def test_injury_context_contains_hrv(self, runner_tools: RunnerTools):
        ctx = runner_tools._prepare_subagent_context(
            subagent_type="injury_prevention", user_request="评估"
        )
        assert "hrv_analysis" in ctx

    def test_injury_context_contains_fatigue(self, runner_tools: RunnerTools):
        ctx = runner_tools._prepare_subagent_context(
            subagent_type="injury_prevention", user_request="评估"
        )
        assert "fatigue" in ctx

    def test_injury_context_contains_recovery(self, runner_tools: RunnerTools):
        ctx = runner_tools._prepare_subagent_context(
            subagent_type="injury_prevention", user_request="评估"
        )
        assert "recovery" in ctx

    def test_injury_context_contains_hr_drift(self, runner_tools: RunnerTools):
        ctx = runner_tools._prepare_subagent_context(
            subagent_type="injury_prevention", user_request="评估"
        )
        assert "hr_drift" in ctx

    def test_injury_context_contains_memory(self, runner_tools: RunnerTools):
        ctx = runner_tools._prepare_subagent_context(
            subagent_type="injury_prevention", user_request="评估"
        )
        assert "memory" in ctx

    def test_injury_context_contains_training_load(self, runner_tools: RunnerTools):
        ctx = runner_tools._prepare_subagent_context(
            subagent_type="injury_prevention", user_request="评估"
        )
        assert "training_load" in ctx


class TestPrepareContextBackwardCompat:
    """旧角色（data_analyst/report_writer）向后兼容测试"""

    def test_data_analyst_still_works(self, runner_tools: RunnerTools):
        """data_analyst 分支应保持原有行为"""
        ctx = runner_tools._prepare_subagent_context(
            subagent_type="data_analyst", user_request="分析"
        )
        # data_analyst 原本就查询 vdot_trend 和 training_load
        assert "vdot_trend" in ctx
        assert "training_load" in ctx

    def test_report_writer_still_works(self, runner_tools: RunnerTools):
        """report_writer 分支应保持原有行为"""
        ctx = runner_tools._prepare_subagent_context(
            subagent_type="report_writer", user_request="周报"
        )
        assert "running_stats" in ctx or "recent_runs" in ctx
```

- [ ] **Step 2: 运行测试验证失败**

Run: `uv run pytest tests/unit/agents/test_prepare_subagent_context_new_roles.py -v`
Expected: FAIL（`coach` 和 `injury_prevention` 分支不存在，context 不含对应字段）

- [ ] **Step 3: 修改 _prepare_subagent_context 新增两个分支**

在 `src/agents/tools.py` 的 `_prepare_subagent_context` 方法中（约第 1549 行 `try:` 之后），在 `if subagent_type == "data_analyst":` 之前插入两个新分支：

```python
        try:
            if subagent_type == "coach":
                # 教练 Subagent：预查询 VDOT、训练负荷、近期跑步、计划状态、记忆
                context["vdot_trend"] = self.get_vdot_trend(limit=20)
                context["training_load"] = self.get_training_load(days=42)
                context["recent_runs"] = self.get_recent_runs(limit=10)
                context["plan_status"] = self._get_plan_status_safe()
                context["memory"] = self._load_subagent_memory("coach")
                context["user_request"] = user_request

            elif subagent_type == "injury_prevention":
                # 伤病预防师 Subagent：预查询伤病风险、HRV、疲劳、恢复、心率漂移、负荷、记忆
                context["injury_risk"] = self.predict_injury_risk(days=21)
                context["hrv_analysis"] = self.get_hrv_analysis(days=30)
                context["fatigue"] = self.get_fatigue_score()
                context["recovery"] = self.get_recovery_status()
                context["hr_drift"] = self.get_hr_drift_analysis()
                context["training_load"] = self.get_training_load(days=42)
                context["memory"] = self._load_subagent_memory("injury_prevention")
                context["user_request"] = user_request

            elif subagent_type == "data_analyst":
```

（保留原有 `data_analyst` 和 `report_writer` 分支不变）

- [ ] **Step 4: 运行测试验证通过**

Run: `uv run pytest tests/unit/agents/test_prepare_subagent_context_new_roles.py -v`
Expected: 17 passed

- [ ] **Step 5: 运行全量回归确保旧测试不破**

Run: `uv run pytest tests/unit/agents/ -v`
Expected: 全部 PASS（含原有 data_analyst/report_writer 相关测试）

- [ ] **Step 6: 提交**

```bash
git add src/agents/tools.py tests/unit/agents/test_prepare_subagent_context_new_roles.py
git commit -m "feat(agents): _prepare_subagent_context 新增 coach 与 injury_prevention 预查询分支"
```

---

### Task 4: _invoke_subagent 扩展 valid_types 与 build_task 集成

**Files:**
- Modify: `src/agents/tools.py`（`_invoke_subagent` 方法，约第 1700 行；`spawn_subagent` 方法，约第 1478-1482 行）
- Test: `tests/unit/agents/test_invoke_subagent_valid_types.py`

**Interfaces:**
- Consumes: Task 1 的 `ROLES`、`SubagentRole.build_task`
- Produces: `spawn_subagent` 对新角色调用 `ROLES[type].build_task()` 而非通用 `_build_subagent_task`

- [ ] **Step 1: 写失败测试**

创建 `tests/unit/agents/test_invoke_subagent_valid_types.py`：

```python
"""_invoke_subagent valid_types 扩展测试"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.agents.tools import RunnerTools


@pytest.fixture
def runner_tools():
    with patch.object(RunnerTools, "__init__", lambda self, ctx=None: None):
        tools = RunnerTools()
        return tools


class TestInvokeSubagentValidTypes:
    """_invoke_subagent 应接受新角色类型"""

    def test_coach_is_valid_type(self, runner_tools: RunnerTools):
        result = runner_tools._invoke_subagent("coach", "task content")
        assert result["status"] != "error"
        assert result["subagent_type"] == "coach"

    def test_injury_prevention_is_valid_type(self, runner_tools: RunnerTools):
        result = runner_tools._invoke_subagent("injury_prevention", "task content")
        assert result["status"] != "error"
        assert result["subagent_type"] == "injury_prevention"

    def test_unknown_type_returns_error(self, runner_tools: RunnerTools):
        result = runner_tools._invoke_subagent("unknown", "task content")
        assert result["status"] == "error"


class TestSpawnSubagentUsesRoleBuildTask:
    """spawn_subagent 对新角色应使用 ROLES[type].build_task"""

    def test_spawn_coach_uses_role_prompt(self, runner_tools: RunnerTools):
        """coach 角色的 task 应包含教练 prompt"""
        with patch.object(runner_tools, "_prepare_subagent_context") as mock_ctx, \
             patch.object(runner_tools, "_invoke_subagent") as mock_invoke:
            mock_ctx.return_value = {"vdot": 45.2}
            mock_invoke.return_value = {"status": "ready_to_spawn"}
            runner_tools.spawn_subagent(
                subagent_type="coach", user_request="分析训练"
            )
        # 验证 _invoke_subagent 被调用时 task 包含教练 prompt
        call_args = mock_invoke.call_args
        task = call_args.kwargs.get("task") or call_args.args[1]
        assert "教练" in task
        assert "VDOT" in task

    def test_spawn_injury_uses_role_prompt(self, runner_tools: RunnerTools):
        """injury_prevention 角色的 task 应包含伤病预防师 prompt"""
        with patch.object(runner_tools, "_prepare_subagent_context") as mock_ctx, \
             patch.object(runner_tools, "_invoke_subagent") as mock_invoke:
            mock_ctx.return_value = {"risk": "low"}
            mock_invoke.return_value = {"status": "ready_to_spawn"}
            runner_tools.spawn_subagent(
                subagent_type="injury_prevention", user_request="评估风险"
            )
        call_args = mock_invoke.call_args
        task = call_args.kwargs.get("task") or call_args.args[1]
        assert "伤病预防师" in task or "伤病" in task
```

- [ ] **Step 2: 运行测试验证失败**

Run: `uv run pytest tests/unit/agents/test_invoke_subagent_valid_types.py -v`
Expected: FAIL（`coach`/`injury_prevention` 不在 valid_types，task 不含角色 prompt）

- [ ] **Step 3: 修改 _invoke_subagent 扩展 valid_types**

在 `src/agents/tools.py` 的 `_invoke_subagent` 方法中（约第 1700 行），将：

```python
        valid_types = ["data_analyst", "report_writer"]
```

改为：

```python
        valid_types = ["data_analyst", "report_writer", "coach", "injury_prevention"]
```

- [ ] **Step 4: 修改 spawn_subagent 对新角色使用 ROLES[type].build_task**

在 `src/agents/tools.py` 的 `spawn_subagent` 方法中（约第 1478-1482 行），将：

```python
            # 2. 组装task参数（数据上下文格式）
            task = self._build_subagent_task(
                user_request=user_request,
                context_data=context_data,
            )
```

改为：

```python
            # 2. 组装task参数
            # 新角色（coach/injury_prevention）使用 ROLES[type].build_task 注入角色 prompt
            # 旧角色（data_analyst/report_writer）保持原 _build_subagent_task 行为
            from src.agents.subagent_roles import ROLES

            if subagent_type in ROLES:
                task = ROLES[subagent_type].build_task(user_request, context_data)
            else:
                task = self._build_subagent_task(
                    user_request=user_request,
                    context_data=context_data,
                )
```

- [ ] **Step 5: 运行测试验证通过**

Run: `uv run pytest tests/unit/agents/test_invoke_subagent_valid_types.py -v`
Expected: 5 passed

- [ ] **Step 6: 运行全量回归**

Run: `uv run pytest tests/unit/agents/ -v`
Expected: 全部 PASS

- [ ] **Step 7: 提交**

```bash
git add src/agents/tools.py tests/unit/agents/test_invoke_subagent_valid_types.py
git commit -m "feat(agents): _invoke_subagent 扩展 valid_types 并对新角色使用 ROLES.build_task"
```

---

### Task 5: SpawnSubagentTool 枚举与 TOOL_DESCRIPTIONS 更新

**Files:**
- Modify: `src/agents/tools_twin.py`（`SpawnSubagentTool.parameters`，约第 423-447 行）
- Modify: `src/agents/tools.py`（`TOOL_DESCRIPTIONS["spawn_subagent"]`，约第 2864-2872 行）
- Test: `tests/unit/agents/test_spawn_tool_enum.py`

**Interfaces:**
- Consumes: 无
- Produces: `SpawnSubagentTool.parameters` 枚举含 4 个角色，`TOOL_DESCRIPTIONS` 描述更新

- [ ] **Step 1: 写失败测试**

创建 `tests/unit/agents/test_spawn_tool_enum.py`：

```python
"""SpawnSubagentTool 枚举扩展测试"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.agents.tools import TOOL_DESCRIPTIONS
from src.agents.tools_twin import SpawnSubagentTool


class TestSpawnSubagentToolEnum:
    """SpawnSubagentTool.parameters 应包含 4 个角色"""

    @pytest.fixture
    def tool(self):
        runner_tools = MagicMock()
        return SpawnSubagentTool(runner_tools)

    def test_enum_contains_coach(self, tool: SpawnSubagentTool):
        enum_values = tool.parameters["properties"]["subagent_type"]["enum"]
        assert "coach" in enum_values

    def test_enum_contains_injury_prevention(self, tool: SpawnSubagentTool):
        enum_values = tool.parameters["properties"]["subagent_type"]["enum"]
        assert "injury_prevention" in enum_values

    def test_enum_contains_legacy_types(self, tool: SpawnSubagentTool):
        """旧角色应保留"""
        enum_values = tool.parameters["properties"]["subagent_type"]["enum"]
        assert "data_analyst" in enum_values
        assert "report_writer" in enum_values

    def test_enum_has_four_types(self, tool: SpawnSubagentTool):
        enum_values = tool.parameters["properties"]["subagent_type"]["enum"]
        assert len(enum_values) == 4


class TestToolDescriptions:
    """TOOL_DESCRIPTIONS 应更新描述"""

    def test_description_mentions_coach(self):
        desc = TOOL_DESCRIPTIONS["spawn_subagent"]["description"]
        assert "教练" in desc or "coach" in desc

    def test_description_mentions_injury(self):
        desc = TOOL_DESCRIPTIONS["spawn_subagent"]["description"]
        assert "伤病" in desc or "injury" in desc

    def test_parameters_subagent_type_mentions_coach(self):
        params = TOOL_DESCRIPTIONS["spawn_subagent"]["parameters"]
        assert "教练" in params["subagent_type"] or "coach" in params["subagent_type"]
```

- [ ] **Step 2: 运行测试验证失败**

Run: `uv run pytest tests/unit/agents/test_spawn_tool_enum.py -v`
Expected: FAIL（枚举仅含 2 个旧角色，描述未提及教练/伤病）

- [ ] **Step 3: 修改 SpawnSubagentTool.parameters 枚举**

在 `src/agents/tools_twin.py` 的 `SpawnSubagentTool.parameters`（约第 423-447 行），将 `subagent_type` 字段改为：

```python
                "subagent_type": {
                    "type": "string",
                    "description": "Subagent类型: coach(教练) / injury_prevention(伤病预防师) / data_analyst(数据分析) / report_writer(报告撰写)",
                    "enum": ["coach", "injury_prevention", "data_analyst", "report_writer"],
                },
```

- [ ] **Step 4: 更新 SpawnSubagentTool.description**

在 `src/agents/tools_twin.py` 的 `SpawnSubagentTool.description`（约第 415-420 行），改为：

```python
    @property
    def description(self) -> str:
        return (
            "调用Subagent执行专项任务。支持教练(coach)、伤病预防师(injury_prevention)、"
            "数据分析(data_analyst)、报告撰写(report_writer)四种Subagent。"
            "主Agent会自动预查询相关数据并传入Subagent。当用户需要训练建议、伤病风险评估、"
            "深度数据分析、生成训练周报/月报时使用此工具。"
            "返回JSON格式: {success: true, data: {subagent_type, result, context_size}} 或 "
            "{success: false, error: 错误信息, fallback_result: 降级结果}"
        )
```

- [ ] **Step 5: 更新 TOOL_DESCRIPTIONS**

在 `src/agents/tools.py` 的 `TOOL_DESCRIPTIONS["spawn_subagent"]`（约第 2864-2872 行），改为：

```python
    "spawn_subagent": {
        "description": "调用Subagent执行专项任务。支持教练(coach)、伤病预防师(injury_prevention)、数据分析(data_analyst)、报告撰写(report_writer)四种Subagent。主Agent会自动预查询相关数据并传入Subagent。当用户需要训练建议、伤病风险评估、深度数据分析、生成训练周报/月报时使用此工具。返回JSON格式: {success: true, data: {subagent_type, result, context_size}} 或 {success: false, error: 错误信息, fallback_result: 降级结果}",
        "parameters": {
            "subagent_type": "Subagent类型: coach(教练) / injury_prevention(伤病预防师) / data_analyst(数据分析) / report_writer(报告撰写)",
            "user_request": "用户的原始请求描述",
            "date_range": "日期范围（可选，格式：YYYY-MM-DD ~ YYYY-MM-DD）",
            "report_type": "报告类型（可选，仅report_writer使用）：weekly/monthly/summary",
        },
    },
```

- [ ] **Step 6: 运行测试验证通过**

Run: `uv run pytest tests/unit/agents/test_spawn_tool_enum.py -v`
Expected: 7 passed

- [ ] **Step 7: 提交**

```bash
git add src/agents/tools_twin.py src/agents/tools.py tests/unit/agents/test_spawn_tool_enum.py
git commit -m "feat(agents): SpawnSubagentTool 枚举与 TOOL_DESCRIPTIONS 扩展 4 个角色"
```

---

### Task 6: 新增 UpdateSubagentMemoryTool 工具

**Files:**
- Modify: `src/agents/tools.py`（新增 `UpdateSubagentMemoryTool` 类，注册到工具列表）
- Test: `tests/unit/agents/test_update_subagent_memory_tool.py`

**Interfaces:**
- Consumes: Task 2 的 `RunnerTools._load_subagent_memory`（读旧记忆合并）
- Produces: `UpdateSubagentMemoryTool` 工具，Agent 可调用更新记忆

- [ ] **Step 1: 写失败测试**

创建 `tests/unit/agents/test_update_subagent_memory_tool.py`：

```python
"""UpdateSubagentMemoryTool 工具测试"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.agents.tools import RunnerTools, UpdateSubagentMemoryTool


@pytest.fixture
def tool_and_tools(tmp_path: Path):
    """构造工具实例和 mock RunnerTools"""
    with patch.object(RunnerTools, "__init__", lambda self, ctx=None: None):
        runner_tools = RunnerTools()
        runner_tools._runner_config = MagicMock()
        runner_tools._runner_config.base_dir = tmp_path
        runner_tools._load_subagent_memory = MagicMock(return_value={})
        tool = UpdateSubagentMemoryTool(runner_tools)
        return tool, runner_tools


class TestUpdateSubagentMemoryTool:
    """update_subagent_memory 工具测试"""

    def test_tool_name(self, tool_and_tools):
        tool, _ = tool_and_tools
        assert tool.name == "update_subagent_memory"

    def test_update_memory_writes_json(self, tool_and_tools, tmp_path: Path):
        """更新记忆应写入 JSON 文件"""
        tool, runner_tools = tool_and_tools
        runner_tools._load_subagent_memory.return_value = {"existing": "data"}

        result = tool.runner_tools._update_subagent_memory(
            role="coach", key="user_goal", value="全马破4"
        )

        memory_file = tmp_path / "memory" / "subagents" / "coach.json"
        assert memory_file.exists()
        saved = json.loads(memory_file.read_text(encoding="utf-8"))
        assert saved["existing"] == "data"
        assert saved["user_goal"] == "全马破4"

    def test_update_memory_returns_success(self, tool_and_tools):
        """更新记忆返回 success=True"""
        tool, runner_tools = tool_and_tools
        result = tool.runner_tools._update_subagent_memory(
            role="coach", key="user_goal", value="marathon"
        )
        assert result["success"] is True

    def test_update_memory_unknown_role_still_writes(self, tool_and_tools, tmp_path: Path):
        """未知角色也应能写入（不限制角色名，宽容）"""
        tool, runner_tools = tool_and_tools
        result = tool.runner_tools._update_subagent_memory(
            role="custom_role", key="k", value="v"
        )
        assert result["success"] is True
        assert (tmp_path / "memory" / "subagents" / "custom_role.json").exists()
```

- [ ] **Step 2: 运行测试验证失败**

Run: `uv run pytest tests/unit/agents/test_update_subagent_memory_tool.py -v`
Expected: FAIL with `ImportError: cannot import name 'UpdateSubagentMemoryTool'`

- [ ] **Step 3: 在 RunnerTools 新增 _update_subagent_memory 私有方法**

在 `src/agents/tools.py` 的 `RunnerTools` 类中，Task 2 新增的 `_get_plan_status_safe` 方法之后插入：

```python
    def _update_subagent_memory(self, role: str, key: str, value: Any) -> dict[str, Any]:
        """更新 subagent 记忆文档的单个字段

        读取现有记忆 → 合并新字段 → 写回文件。惰性创建目录。

        Args:
            role: 角色名
            key: 记忆字段名
            value: 字段值

        Returns:
            dict: {"success": True, "role": role, "key": key}
        """
        try:
            memory_dir = (
                self._runner_config.base_dir / "memory" / "subagents"
            )
            memory_dir.mkdir(parents=True, exist_ok=True)
            memory_path = memory_dir / f"{role}.json"

            # 读取现有记忆（复用宽容读取逻辑）
            memory = self._load_subagent_memory(role)
            memory[key] = value
            memory["last_updated"] = datetime.now().isoformat()

            memory_path.write_text(
                json.dumps(memory, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )
            logger.info("更新 subagent 记忆 role=%s key=%s", role, key)
            return {"success": True, "role": role, "key": key}
        except (OSError, ValueError, TypeError) as e:
            logger.error("更新 subagent 记忆失败 role=%s: %s", role, e)
            return {"success": False, "error": str(e)}
```

- [ ] **Step 4: 新增 UpdateSubagentMemoryTool 类**

在 `src/agents/tools.py` 中，`SpawnSubagentTool` 相关代码之后（或在工具类定义区域的合适位置）新增：

```python
class UpdateSubagentMemoryTool(BaseTool):
    """更新 subagent 记忆工具 - v0.33.0 新增

    允许主 Agent 在收到 subagent 结果后，将关键信息写入对应角色的记忆文档，
    供下次 spawn 时作为上下文注入。

    使用场景：
    - 教练 subagent 返回建议后，记录 user_goal / preferred_training_style
    - 伤病预防师标记风险等级后，记录 injury_history / last_alert_level
    """

    @property
    def name(self) -> str:
        return "update_subagent_memory"

    @property
    def description(self) -> str:
        return (
            "更新 subagent 记忆文档。当 subagent 返回结果后，将关键信息"
            "（如用户目标、偏好、伤病史、风险阈值）写入对应角色记忆，"
            "供下次调用时作为上下文。返回JSON: {success: true, role, key} 或 {success: false, error}"
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "role": {
                    "type": "string",
                    "description": "角色名: coach / injury_prevention",
                    "enum": ["coach", "injury_prevention"],
                },
                "key": {
                    "type": "string",
                    "description": "记忆字段名（如 user_goal / injury_history / preferred_training_style）",
                },
                "value": {
                    "description": "字段值（任意类型：字符串/数字/对象/数组）",
                },
            },
            "required": ["role", "key", "value"],
        }

    async def execute(self, **kwargs: Any) -> str:
        role = kwargs.get("role", "")
        key = kwargs.get("key", "")
        value = kwargs.get("value")
        return self._run_sync(
            self.runner_tools._update_subagent_memory,
            role=role,
            key=key,
            value=value,
        )
```

- [ ] **Step 5: 在工具注册列表中注册新工具**

在 `src/agents/tools.py` 的工具注册列表中（约第 2691 行 `SpawnSubagentTool(runner_tools),` 之后），新增：

```python
        SpawnSubagentTool(runner_tools),
        UpdateSubagentMemoryTool(runner_tools),
```

- [ ] **Step 6: 在 TOOL_DESCRIPTIONS 中添加新工具描述**

在 `src/agents/tools.py` 的 `TOOL_DESCRIPTIONS` 中（`spawn_subagent` 条目之后），新增：

```python
    "update_subagent_memory": {
        "description": "更新 subagent 记忆文档。当 subagent 返回结果后，将关键信息（如用户目标、偏好、伤病史、风险阈值）写入对应角色记忆，供下次调用时作为上下文。返回JSON: {success: true, role, key} 或 {success: false, error}",
        "parameters": {
            "role": "角色名: coach / injury_prevention",
            "key": "记忆字段名（如 user_goal / injury_history / preferred_training_style）",
            "value": "字段值（任意类型）",
        },
    },
```

- [ ] **Step 7: 运行测试验证通过**

Run: `uv run pytest tests/unit/agents/test_update_subagent_memory_tool.py -v`
Expected: 4 passed

- [ ] **Step 8: 提交**

```bash
git add src/agents/tools.py tests/unit/agents/test_update_subagent_memory_tool.py
git commit -m "feat(agents): 新增 UpdateSubagentMemoryTool 工具支持记忆持久化"
```

---

### Task 7: 集成测试

**Files:**
- Create: `tests/integration/agents/test_spawn_subagent_new_roles.py`

**Interfaces:**
- Consumes: Task 1-6 的全部产出
- Produces: 端到端集成测试，验证 spawn_subagent 对新角色的完整调用链

- [ ] **Step 1: 写集成测试**

创建 `tests/integration/agents/test_spawn_subagent_new_roles.py`：

```python
"""spawn_subagent 新角色集成测试

验证从 spawn_subagent 入口到 _invoke_subagent 的完整调用链，
Mock 到 SubagentManager.spawn 边界（不实际调用 nanobot 底座）。
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.agents.tools import RunnerTools


@pytest.fixture
def runner_tools_with_mocks():
    """构造完整 mock 的 RunnerTools，业务方法返回固定数据"""
    with patch.object(RunnerTools, "__init__", lambda self, ctx=None: None):
        tools = RunnerTools()
        tools._context = MagicMock()
        tools._runner_config = MagicMock()
        tools._runner_config.base_dir = MagicMock()
        # 业务方法 mock
        tools.get_vdot_trend = MagicMock(return_value={"vdot": 45.2, "trend": "up"})
        tools.get_training_load = MagicMock(
            return_value={"atl": 50, "ctl": 60, "tsb": 10}
        )
        tools.get_recent_runs = MagicMock(
            return_value=[{"distance_km": 10, "duration_min": 50}]
        )
        tools.predict_injury_risk = MagicMock(
            return_value={"success": True, "data": {"risk_level": "low", "score": 0.2}}
        )
        tools.get_hrv_analysis = MagicMock(return_value={"rmssd": 35.0, "trend": "stable"})
        tools.get_fatigue_score = MagicMock(return_value={"score": 3, "level": "low"})
        tools.get_recovery_status = MagicMock(return_value={"status": "good", "readiness": 85})
        tools.get_hr_drift_analysis = MagicMock(return_value={"drift_percent": 5.0})
        tools._load_subagent_memory = MagicMock(return_value={"user_goal": "marathon"})
        tools._get_plan_status_safe = MagicMock(return_value={"plan_id": "plan_001"})
        return tools


class TestSpawnCoachIntegration:
    """教练角色端到端集成测试"""

    def test_spawn_coach_returns_success(
        self, runner_tools_with_mocks: RunnerTools
    ):
        result = runner_tools_with_mocks.spawn_subagent(
            subagent_type="coach", user_request="帮我分析近期训练"
        )
        assert result["success"] is True
        assert result["data"]["subagent_type"] == "coach"
        assert "result" in result["data"]

    def test_spawn_coach_task_contains_coach_prompt(
        self, runner_tools_with_mocks: RunnerTools
    ):
        result = runner_tools_with_mocks.spawn_subagent(
            subagent_type="coach", user_request="分析训练"
        )
        task_preview = result["data"].get("task_preview", "")
        assert "教练" in task_preview or "教练" in str(result["data"])

    def test_spawn_coach_task_contains_vdot_data(
        self, runner_tools_with_mocks: RunnerTools
    ):
        """task 应包含预查询的 VDOT 数据"""
        result = runner_tools_with_mocks.spawn_subagent(
            subagent_type="coach", user_request="分析训练"
        )
        # task_preview 或 result 应包含 vdot 数据
        data_str = str(result["data"])
        assert "45.2" in data_str or "vdot" in data_str.lower()

    def test_spawn_coach_context_size_under_8000(
        self, runner_tools_with_mocks: RunnerTools
    ):
        """上下文大小应小于 8000 字符"""
        result = runner_tools_with_mocks.spawn_subagent(
            subagent_type="coach", user_request="分析训练"
        )
        assert result["data"]["context_size"] <= 8000


class TestSpawnInjuryPreventionIntegration:
    """伤病预防师角色端到端集成测试"""

    def test_spawn_injury_returns_success(
        self, runner_tools_with_mocks: RunnerTools
    ):
        result = runner_tools_with_mocks.spawn_subagent(
            subagent_type="injury_prevention", user_request="评估伤病风险"
        )
        assert result["success"] is True
        assert result["data"]["subagent_type"] == "injury_prevention"

    def test_spawn_injury_task_contains_risk_data(
        self, runner_tools_with_mocks: RunnerTools
    ):
        """task 应包含伤病风险预测数据"""
        result = runner_tools_with_mocks.spawn_subagent(
            subagent_type="injury_prevention", user_request="评估风险"
        )
        data_str = str(result["data"])
        assert "risk_level" in data_str or "low" in data_str

    def test_spawn_injury_task_contains_injury_prompt(
        self, runner_tools_with_mocks: RunnerTools
    ):
        result = runner_tools_with_mocks.spawn_subagent(
            subagent_type="injury_prevention", user_request="评估风险"
        )
        task_preview = result["data"].get("task_preview", "")
        assert "伤病" in task_preview or "伤病" in str(result["data"])


class TestSpawnUnknownRoleIntegration:
    """未知角色应返回 error"""

    def test_spawn_unknown_returns_error(
        self, runner_tools_with_mocks: RunnerTools
    ):
        result = runner_tools_with_mocks.spawn_subagent(
            subagent_type="unknown_role", user_request="请求"
        )
        # 未知角色走 _invoke_subagent 的 error 分支
        # spawn_subagent 仍返回 success=True（因为预查询成功），
        # 但 result 中会包含 error 状态
        # 检查 _invoke_subagent 返回的 status
        invoke_result = result["data"]["result"]
        assert invoke_result["status"] == "error"


class TestSpawnBackwardCompatIntegration:
    """旧角色向后兼容"""

    def test_spawn_data_analyst_still_works(
        self, runner_tools_with_mocks: RunnerTools
    ):
        result = runner_tools_with_mocks.spawn_subagent(
            subagent_type="data_analyst", user_request="分析数据"
        )
        assert result["success"] is True
        assert result["data"]["subagent_type"] == "data_analyst"

    def test_spawn_report_writer_still_works(
        self, runner_tools_with_mocks: RunnerTools
    ):
        result = runner_tools_with_mocks.spawn_subagent(
            subagent_type="report_writer", user_request="生成周报", report_type="weekly"
        )
        assert result["success"] is True
        assert result["data"]["subagent_type"] == "report_writer"
```

- [ ] **Step 2: 运行集成测试**

Run: `uv run pytest tests/integration/agents/test_spawn_subagent_new_roles.py -v`
Expected: 9 passed

- [ ] **Step 3: 运行全量测试确保无回归**

Run: `uv run pytest tests/unit/agents/ tests/integration/agents/ -v`
Expected: 全部 PASS

- [ ] **Step 4: 代码质量检查**

Run: `uv run ruff check src/agents/subagent_roles.py src/agents/tools.py src/agents/tools_twin.py`
Expected: 无错误

Run: `uv run ruff format --check src/agents/subagent_roles.py src/agents/tools.py src/agents/tools_twin.py`
Expected: 格式正确

- [ ] **Step 5: 提交**

```bash
git add tests/integration/agents/test_spawn_subagent_new_roles.py
git commit -m "test(agents): 新增 spawn_subagent 新角色集成测试"
```

---

### Task 8: 文档更新

**Files:**
- Modify: `AGENTS.md`（§3.1 代码库结构，subagent 相关段落）
- Modify: `docs/architecture/架构设计说明书.md`（subagent 段落，若存在）

**Interfaces:**
- Consumes: Task 1-7 的实现成果
- Produces: 文档反映新增的 subagent 角色

- [ ] **Step 1: 更新 AGENTS.md §3.1 代码库结构**

在 `AGENTS.md` 的代码库结构中，`src/agents/` 部分新增 `subagent_roles.py`：

```markdown
├── agents/
│   ├── tools.py                # Agent 工具集
│   ├── tools_evolution.py      # 进化模块Agent工具 (v0.23.0-v0.25.0)
│   └── subagent_roles.py       # Subagent 角色定义 (v0.33.0)
```

- [ ] **Step 2: 在 AGENTS.md 业务术语表新增 subagent 角色术语**

在 `AGENTS.md` §8 业务术语表中新增：

```markdown
| **Subagent 角色** | 专业 AI 代理，按领域划分 | coach(教练) / injury_prevention(伤病预防师) |
```

- [ ] **Step 3: 运行文档检查（若有 lint）**

Run: `uv run pytest tests/ -k "doc" --collect-only 2>&1 | head -5`
Expected: 无文档相关测试失败（或无测试可收集）

- [ ] **Step 4: 提交**

```bash
git add AGENTS.md docs/architecture/架构设计说明书.md
git commit -m "docs: 更新 AGENTS.md 与架构文档反映 subagent 新角色"
```

---

## Self-Review 检查

**1. Spec coverage（设计文档覆盖检查）**：

| 设计文档章节 | 对应 Task |
|-------------|----------|
| §2.2 改动范围 - subagent_roles.py | Task 1 |
| §2.2 改动范围 - tools.py spawn_subagent 扩展 | Task 3, 4 |
| §2.2 改动范围 - tools_twin.py 枚举扩展 | Task 5 |
| §3.1 教练角色 prompt + 预查询 | Task 1（prompt）+ Task 3（预查询） |
| §3.2 伤病预防师 prompt + 预查询 | Task 1（prompt）+ Task 3（预查询） |
| §3.3 协作模式 | 由主 Agent 自行编排，无需代码（设计约束） |
| §4.1 _prepare_subagent_context 扩展 | Task 3 |
| §4.2 build_task 拼装 | Task 1（SubagentRole.build_task）+ Task 4（集成到 spawn_subagent） |
| §4.3 上下文预算 | 复用现有 _truncate_context，无需新代码（Task 3 验证） |
| §4.4 工具枚举扩展 | Task 5 |
| §5.1-5.3 记忆机制 | Task 2（读）+ Task 6（写） |
| §6 错误处理与降级 | Task 2（容错方法）+ Task 3（复用现有降级） |
| §7 测试策略 | Task 1-7 均含测试 |
| §8 任务清单 10 项 | 本计划 8 个 Task 覆盖全部（合并了相关任务） |

**2. Placeholder scan**：无 TBD/TODO，所有步骤含完整代码。

**3. Type consistency**：
- `SubagentRole.build_task(user_request: str, context_data: dict) -> str` — Task 1 定义，Task 4 调用 ✓
- `RunnerTools._load_subagent_memory(role: str) -> dict` — Task 2 定义，Task 3 调用 ✓
- `RunnerTools._get_plan_status_safe() -> dict | None` — Task 2 定义，Task 3 调用 ✓
- `RunnerTools._update_subagent_memory(role, key, value) -> dict` — Task 6 定义并调用 ✓
- `predict_injury_risk(days=21)` — 现有方法，Task 3 调用 ✓
- `get_fatigue_score()` / `get_recovery_status()` / `get_hr_drift_analysis()` — 现有方法，Task 3 调用 ✓

全部一致。
