# Subagent 扩展设计：教练 + 伤病预防师

> **文档版本**: v1.0
> **创建日期**: 2026-07-23
> **当前基线**: v0.32.0
> **目标**: MVP 引入 2 个专业 subagent（教练、伤病预防师），验证多 subagent 自动编排可行性
> **方案**: 方案 A — 扩展现有 `spawn_subagent` 模式，复用 nanobot-ai 0.2.2 原生 `SpawnTool`

---

## 1. 背景与动机

### 1.1 现状

项目 v0.17.0 已引入 subagent 基础设施，模式为"主 Agent 预查询 + 数据上下文传入"：

- `spawn_subagent` 工具（[tools_twin.py:385](file:///d:/yecll/Documents/LocalCode/RunFlowAgent/src/agents/tools_twin.py#L385)）
- 现有 2 种子类型：`data_analyst`（数据分析）、`report_writer`（报告撰写）
- 通过 nanobot-ai 底座 `SpawnTool` 调用，上下文限制 8000 字符
- 支持降级（fallback）：失败时返回预查询数据供主 Agent 自己处理

### 1.2 动机

v1.0.0 愿景为"私人 AI 教练"，需要从单一通用 Agent 进化为多专业角色协作。本次 MVP 引入 2 个跑步领域专业 subagent，验证自动编排可行性。

### 1.3 nanobot-ai 0.2.2 原生能力边界

| 能力 | 原生支持 | 说明 |
|------|---------|------|
| 后台异步 spawn | ✅ | `SpawnTool` 通过 `SubagentManager.spawn()` 创建 asyncio.Task |
| 结果回注主会话 | ✅ | 通过 MessageBus 注入系统消息（`session_key_override` 路由） |
| 并发限制 | ✅ | `max_concurrent_subagents` |
| 隔离工具注册表 | ✅ | subagent 独立 ToolRegistry，scope="subagent" 过滤 |
| 通用系统提示 | ✅ | `subagent_system.md` 模板（无角色概念） |
| 取消机制 | ✅ | `cancel_by_session()` |
| **专业角色 prompt** | ❌ | 无 subagent_type 参数，只有通用 task 描述 |
| **持久记忆** | ❌ | 每次 spawn 是新会话，无跨次记忆 |
| **业务工具访问** | ⚠️ | subagent scope 默认只加载通用工具（exec/web/file） |
| 多 subagent 协调 | ❌ | 无原生编排器 |

**关键约束**：不引入编排器/会诊仲裁器。主 Agent 自身承担编排，通过反复调用 `spawn` + 在 task 描述中注入角色指令和数据上下文实现。

---

## 2. 架构概览

### 2.1 核心思路

复用 v0.17.0 的 `spawn_subagent` 模式，扩展 `subagent_type` 枚举新增 `coach`（教练）和 `injury_prevention`（伤病预防师）。不引入新模块、不开发协调器。

### 2.2 改动范围（最小化）

```
src/agents/
├── tools.py              # spawn_subagent() 扩展 2 个角色分支
├── tools_twin.py         # SpawnSubagentTool.parameters 枚举扩展
└── subagent_roles.py     # 新增：角色定义（纯数据，无抽象）
    ├── SubagentRole      # 角色数据类
    ├── ROLES             # 角色注册表
    ├── COACH_PROMPT      # 教练系统提示片段
    └── INJURY_PROMPT     # 伤病预防师系统提示片段

~/.nanobot-runner/memory/subagents/
├── coach.json            # 教练记忆
└── injury_prevention.json # 伤病预防师记忆
```

### 2.3 不改动

- nanobot-ai 底座的 `SpawnTool` / `SubagentManager`（原生能力够用）
- 现有 `data_analyst` / `report_writer`（向后兼容）
- evolution 引擎、DecisionLog（MVP 不强制对接）

### 2.4 调用链

```
用户消息 → 主 Agent 识别意图 → 调用 spawn_subagent(subagent_type="coach")
    → RunnerTools._prepare_subagent_context("coach")  # 预查询 + 读记忆
    → SubagentRole.build_task(prompt, data, memory)   # 拼装 task
    → SpawnSubagentTool → nanobot SpawnTool → SubagentManager.spawn()
    → 后台执行 → 结果通过 MessageBus 回注主会话
    → 主 Agent 收到结果 → 可选写入记忆文档
```

---

## 3. 角色定义

### 3.1 教练（coach）

**职责边界**：训练计划调整、配速策略、训练负荷建议、目标赛事备战。

**不涉及**：伤病诊断（交给伤病预防师）、营养建议（未来营养师）、装备选择。

**系统 prompt 片段**（注入 task 开头）：

```
你是资深跑步教练，专精于基于 VDOT 和训练负荷数据的训练计划制定。
你的职责：
- 分析近期训练数据，给出配速和训练量建议
- 基于数字孪生推演结果，推荐训练方案
- 调整训练计划以逼近用户目标赛事
你不负责伤病诊断、营养建议、装备选择。
输出格式：结构化建议 + 理由 + 可执行动作。
```

**预查询数据集**（复用现有 RunnerTools 方法）：

| 方法 | 用途 |
|------|------|
| `get_vdot_trend(limit=20)` | VDOT 趋势 |
| `get_training_load(days=42)` | 6 周训练负荷（ATL/CTL/TSB） |
| `get_recent_runs(limit=10)` | 近 10 次跑步 |
| `_get_plan_status_safe()` | 当前训练计划状态（容错） |
| `_load_subagent_memory("coach")` | 教练记忆 |

### 3.2 伤病预防师（injury_prevention）

**职责边界**：伤病风险预警、恢复建议、训练负荷红线、异常身体信号解读。

**不涉及**：具体训练计划调整（交给教练）、医疗诊断。

**系统 prompt 片段**：

```
你是运动医学背景的伤病预防师，基于伤病风险预测模型和身体信号数据工作。
你的职责：
- 解读伤病风险预测结果（ML/参数化/规则三层降级）
- 识别急性负荷过高、HRV 异常、心率漂移过大等风险信号
- 给出恢复建议（休息/减量/交叉训练）
- 标记需要停止训练的红线信号
你不负责训练计划制定、营养建议。
输出格式：风险等级 + 风险因素 + 恢复建议 + 红线警告（如有）。
```

**预查询数据集**：

| 方法 | 用途 |
|------|------|
| `_get_injury_risk_safe(days=21)` | 21 天伤病风险预测（复用 InjuryPredictor，容错） |
| `get_hrv_analysis(days=30)` | HRV 趋势 |
| `get_fatigue_assessment()` | 疲劳度评估 |
| `get_hr_drift_analysis()` | 心率漂移 |
| `get_training_load(days=42)` | 训练负荷（与教练共享，视角不同） |
| `_load_subagent_memory("injury_prevention")` | 伤病预防师记忆 |

### 3.3 两角色协作模式（自动编排）

主 Agent 识别意图后自行决定调用顺序，**不引入协调器**：

| 用户意图 | 主 Agent 行为 |
|---------|--------------|
| "最近训练怎么样" | 单独 spawn coach |
| "膝盖有点不舒服" | 单独 spawn injury_prevention |
| "帮我安排下周训练" | **串行**：先 spawn injury_prevention 评估风险 → 结果回注 → 主 Agent 再 spawn coach 带上风险结论制定计划 |
| "全面评估我的状态" | **并行**：同时 spawn 两个，主 Agent 汇总两份结果 |

串行/并行由主 Agent 在 task 描述中自行决策，完全落在 nanobot-ai `SpawnTool` 原生能力内。

---

## 4. 数据流细节

### 4.1 `spawn_subagent` 扩展点

`_prepare_subagent_context()`（[tools.py:1525](file:///d:/yecll/Documents/LocalCode/RunFlowAgent/src/agents/tools.py#L1525)）新增两个分支：

```python
if subagent_type == "coach":
    context["vdot_trend"] = self.get_vdot_trend(limit=20)
    context["training_load"] = self.get_training_load(days=42)
    context["recent_runs"] = self.get_recent_runs(limit=10)
    context["plan_status"] = self._get_plan_status_safe()
    context["memory"] = self._load_subagent_memory("coach")
    context["user_request"] = user_request

elif subagent_type == "injury_prevention":
    context["injury_risk"] = self._get_injury_risk_safe(days=21)
    context["hrv_analysis"] = self.get_hrv_analysis(days=30)
    context["fatigue"] = self.get_fatigue_assessment()
    context["hr_drift"] = self.get_hr_drift_analysis()
    context["training_load"] = self.get_training_load(days=42)
    context["memory"] = self._load_subagent_memory("injury_prevention")
    context["user_request"] = user_request
```

### 4.2 task 拼装（新文件 subagent_roles.py）

```python
@dataclass(frozen=True)
class SubagentRole:
    name: str
    prompt: str
    context_builders: tuple[str, ...]  # 预查询方法名（文档性，MVP 不做反射调用）

    def build_task(self, user_request: str, context_data: dict) -> str:
        """拼装 task：角色 prompt + 数据上下文 + 记忆摘要"""
        return (
            f"{self.prompt}\n\n"
            f"用户请求：{user_request}\n"
            f"{CONTEXT_SEPARATOR}"
            f"{json.dumps(context_data, ensure_ascii=False, default=str, indent=2)}"
            f"{CONTEXT_END}"
        )

ROLES: dict[str, SubagentRole] = {
    "coach": SubagentRole("coach", COACH_PROMPT, (...)),
    "injury_prevention": SubagentRole("injury_prevention", INJURY_PROMPT, (...)),
}
```

### 4.3 上下文预算（8000 字符限制）

现有 `MAX_CONTEXT_LENGTH=8000`。新增角色后预算分配：

| 组成 | 教练 | 伤病预防师 |
|------|------|-----------|
| 角色 prompt | ~300 字符 | ~350 字符 |
| 用户请求 | ~200 | ~200 |
| 记忆摘要 | ~500 | ~500 |
| 数据上下文 | ~7000 | ~6950 |
| **总计** | <8000 | <8000 |

`_truncate_context()` 已有截断逻辑，超限时保留 prompt + 用户请求，截断数据上下文。无需改动。

### 4.4 工具枚举扩展

[tools_twin.py:429](file:///d:/yecll/Documents/LocalCode/RunFlowAgent/src/agents/tools_twin.py#L429)：

```python
"subagent_type": {
    "type": "string",
    "description": "Subagent类型: coach(教练) / injury_prevention(伤病预防师) / data_analyst(数据分析) / report_writer(报告撰写)",
    "enum": ["coach", "injury_prevention", "data_analyst", "report_writer"],
},
```

同步更新 [tools.py:1700](file:///d:/yecll/Documents/LocalCode/RunFlowAgent/src/agents/tools.py#L1700) `valid_types` 列表和 [tools.py:2865](file:///d:/yecll/Documents/LocalCode/RunFlowAgent/src/agents/tools.py#L2865) `TOOL_DESCRIPTIONS`。

---

## 5. 记忆机制

### 5.1 存储位置

`~/.nanobot-runner/memory/subagents/{role}.json`，通过 `ConfigManager.base_dir / "memory" / "subagents"` 定位。惰性创建：首次写入时创建目录。

### 5.2 记忆 Schema（按角色）

```python
# coach.json
{
    "last_advice_summary": str,        # 上次建议摘要（<=200字）
    "user_goal": str,                   # 用户目标赛事/成绩
    "preferred_training_style": str,    # 偏好（如"低强度高跑量"/"高强度间歇"）
    "last_updated": "ISO时间戳",
    "history": [                        # 最近 5 次决策（滚动）
        {"date": "YYYY-MM-DD", "advice": str, "outcome": str|None}
    ]
}

# injury_prevention.json
{
    "injury_history": [                 # 伤病史
        {"body_part": str, "date": "YYYY-MM", "recovery_status": str}
    ],
    "personalized_thresholds": {        # 个性化红线（覆盖默认值）
        "max_acute_load_ratio": 1.5,
        "min_hrv_rmssd": 20.0,
        "max_hr_drift_percent": 10.0
    },
    "last_alert_level": str,            # 上次风险等级
    "last_updated": "ISO时间戳"
}
```

### 5.3 记忆读写

- **读**：`_load_subagent_memory(role)` 在 `_prepare_subagent_context` 中调用，返回 dict（文件不存在返回 `{}`）
- **写**：主 Agent 收到 subagent 结果后，**可选**调用新增工具 `update_subagent_memory(role, key, value)` 更新记忆。MVP 阶段不强制 Agent 调用，靠 prompt 引导。

> ponytail: 记忆写入不做自动摘要（避免引入 LLM 二次调用），由主 Agent 在 task 结果中决定写什么。上限：MVP 不做 schema 强校验，宽容读取。

---

## 6. 错误处理与降级

复用现有 `_prepare_fallback_response` 模式（[tools.py:1728](file:///d:/yecll/Documents/LocalCode/RunFlowAgent/src/agents/tools.py#L1728)），新增角色自动继承：

| 失败场景 | 降级行为 |
|---------|---------|
| 预查询某方法抛 `NanobotRunnerError` | 该字段置为 `{"error": str(e)}`，其余字段正常，subagent 仍 spawn |
| `InjuryPredictor` 无足够数据（<100 条） | 返回规则基线结果（predictor 内部已三层降级），不抛异常 |
| 记忆文件损坏/JSON 解析失败 | 日志 warning，返回 `{}`，subagent 正常 spawn |
| subagent 调用失败（nanobot 底座异常） | 走现有 `_prepare_fallback_response`，返回预查询数据给主 Agent 自行处理 |
| 上下文超 8000 字符 | 走现有 `_truncate_context`，保留 prompt + 请求，截断数据 |

新增容错方法（私有，不暴露为工具）：

- `_get_plan_status_safe()` — try/except 包裹，无计划返回 None
- `_get_injury_risk_safe(days)` — try/except 包裹，失败返回 `{"error": "...", "fallback": "rule_baseline"}`

---

## 7. 测试策略

遵循 ponytail 铁律："非平凡逻辑留一个可运行检查"。

### 7.1 单元测试（`tests/unit/agents/test_subagent_roles.py` 新文件）

| 测试用例 | 验证点 |
|---------|--------|
| `test_role_build_task_contains_prompt` | build_task 输出包含角色 prompt 片段 |
| `test_role_build_task_under_8000` | 正常数据量下 task < 8000 字符 |
| `test_role_build_task_truncation` | 超大数据触发截断，仍保留 prompt |
| `test_roles_registry_contains_coach_and_injury` | ROLES 注册表含两个新角色 |
| `test_load_memory_missing_file_returns_empty` | 记忆文件不存在返回 `{}` |
| `test_load_memory_corrupt_json_returns_empty` | 损坏 JSON 返回 `{}` |
| `test_get_injury_risk_safe_fallback` | predictor 失败时返回 error dict 而非抛异常 |

### 7.2 集成测试（`tests/integration/agents/test_spawn_subagent_new_roles.py` 新文件）

| 测试用例 | 验证点 |
|---------|--------|
| `test_spawn_coach_returns_success` | Mock RunnerTools 方法，验证 spawn_subagent("coach") 返回 success=True |
| `test_spawn_injury_prevention_context_contains_risk` | 验证 context 含 injury_risk 字段 |
| `test_spawn_unknown_role_returns_error` | 未知类型返回 error（走现有 `_invoke_subagent` 逻辑） |

### 7.3 不做 E2E

MVP 阶段不跑完整 nanobot spawn 链路 E2E（依赖 LLM 调用，不稳定）。集成测试 Mock 到 `SubagentManager.spawn` 边界即可。

---

## 8. 实施任务清单

| # | 任务 | 文件 | 依赖 |
|---|------|------|------|
| 1 | 新建 `subagent_roles.py`，定义 `SubagentRole` + `ROLES` + 两个 prompt | `src/agents/subagent_roles.py` | 无 |
| 2 | `RunnerTools` 新增 `_load_subagent_memory` / `_get_plan_status_safe` / `_get_injury_risk_safe` 私有方法 | `src/agents/tools.py` | 1 |
| 3 | `_prepare_subagent_context` 新增 coach / injury_prevention 分支 | `src/agents/tools.py` | 2 |
| 4 | `_invoke_subagent` 扩展 `valid_types` | `src/agents/tools.py` | 1 |
| 5 | `SpawnSubagentTool.parameters` 枚举扩展 | `src/agents/tools_twin.py` | 1 |
| 6 | `TOOL_DESCRIPTIONS["spawn_subagent"]` 更新描述 | `src/agents/tools.py` | 5 |
| 7 | 新增 `UpdateSubagentMemoryTool` 工具 | `src/agents/tools_body.py` 或 `tools.py` | 2 |
| 8 | 单元测试 | `tests/unit/agents/test_subagent_roles.py` | 1-7 |
| 9 | 集成测试 | `tests/integration/agents/test_spawn_subagent_new_roles.py` | 1-7 |
| 10 | 文档更新（AGENTS.md / 架构设计说明书 subagent 段落） | `AGENTS.md`, `docs/architecture/` | 1-9 |

---

## 9. 风险与缓解

| 风险 | 等级 | 缓解措施 |
|------|------|---------|
| 8000 字符上下文不足以容纳全部预查询数据 | 中 | `_truncate_context` 已有截断；记忆摘要限制 500 字符 |
| subagent 无业务工具访问权限（scope 限制） | 低 | MVP 不要求 subagent 自主调用业务工具，数据由主 Agent 预查询注入 |
| 主 Agent 编排决策不稳定（该调哪个 subagent） | 中 | 通过 `spawn_subagent` 工具 description 明确角色边界；MVP 后通过 evolution 记录编排决策 |
| 记忆 schema 漂移（未来字段变更） | 低 | MVP 宽容读取，无 schema 强校验；后续可引入 pydantic 模型 |
| `InjuryPredictor` 数据不足导致预测无意义 | 低 | predictor 内部三层降级，规则基线总能返回结果 |

---

## 10. 验收标准

1. `spawn_subagent(subagent_type="coach")` 返回 `success=True`，task 包含教练 prompt + VDOT/负荷/计划数据
2. `spawn_subagent(subagent_type="injury_prevention")` 返回 `success=True`，task 包含伤病预防师 prompt + injury_risk/HRV/疲劳数据
3. 记忆文件不存在时，subagent 仍正常 spawn（降级为空记忆）
4. `InjuryPredictor` 失败时，`_get_injury_risk_safe` 返回 error dict 而非抛异常
5. 单元测试 + 集成测试全部通过
6. 现有 `data_analyst` / `report_writer` 功能不受影响（向后兼容）

---

## 11. 未来扩展（不在 MVP 范围）

- 营养师、装备/赛事顾问、心理辅导员等角色（同模式扩展 ROLES）
- 记忆 schema 强校验（pydantic 模型）
- subagent 决策写入 DecisionLog，与 evolution 引擎联动
- subagent 自主调用业务工具（需研究 nanobot-ai scope 扩展机制）
- WebUI subagent 状态可视化（运行中/完成/失败）
