# Nanobot Runner API 参考文档

本文档描述 Nanobot Runner 的核心 API 接口。

> **文档版本**: v0.30.0 | **更新日期**: 2026-06-22
> **当前基线**: v0.30.0 | **规划版本**: v1.0.0
> **提示**: 详细参数说明和完整代码示例参见 [docs/api/api_reference_detailed.md](api_reference_detailed.md)
> **v0.19.0 重要变更**: 新增身体信号分析模块(HRV/疲劳度/恢复评估)
> **v0.20.0 重要变更**: 新增ML增强预测模块(VDOT/比赛成绩/伤病风险预测)
> **v0.21.0 重要变更**: 新增数字孪生引擎(What-If推演/计划对比)
> **v0.23.0 重要变更**: 新增自适应进化引擎(决策追踪/结果回填/用户反馈)
> **v0.24.0 重要变更**: 完成测试验证体系升级，全量测试3937 cases通过，覆盖率81%
> **v0.28.0 重要变更**: 新增WebUI数据可视化后端，10个FastAPI端点，6大页面
> **v0.29.0 重要变更**: 新增WebUI管理控制台，13个FastAPI端点，训练计划管理/进化引擎控制台/设置中心

---

## 目录

- [运行环境与初始化](#运行环境与初始化)
- [Core 模块](#core-模块)
- [Agents 模块](#agents-模块)
- [Notify 模块](#notify-模块)
- [智能跑步计划模块](#智能跑步计划模块)
- [工具生态模块](#工具生态模块)

---

## 运行环境与初始化

### nanobot Workspace 结构

```
~/.nanobot-runner/
├── data/                    # 业务数据存储（Parquet 按年分片）
├── memory/                  # 记忆系统（MEMORY.md / HISTORY.md）
├── sessions/                # 会话历史
├── skills/                  # 技能扩展
├── AGENTS.md                # Agent 行为准则
├── SOUL.md                  # 人格设定
├── USER.md                  # 用户画像
└── config.json              # 应用配置
```

**自动创建**: `AGENTS.md`, `SOUL.md`, `USER.md`, `memory/`, `skills/`

**应用创建**: `data/`, `logs/`

---

## Core 模块

### AppContext

应用上下文，集中管理所有核心组件实例，支持依赖注入。

> **v0.9.0 新增**

```python
from src.core.base import AppContextFactory
# 或: from src.core.base.context import AppContextFactory

# 创建默认上下文
ctx = AppContextFactory.create()

# 自定义依赖注入（用于测试）
from unittest.mock import Mock
ctx = AppContextFactory.create(storage=Mock())
```

**核心属性**: `config`, `storage`, `indexer`, `parser`, `importer`, `analytics`, `profile_engine`

---

### SessionRepository

Session 数据仓储层，封装 Session 级别的数据聚合查询，保持 LazyFrame 链式操作。

> **v0.9.0 新增** | **v0.16.0 迁移** 从 `src.core.session_repository` 迁移到 `src.core.storage`

```python
from src.core.storage import SessionRepository
# 或: from src.core.storage.session_repository import SessionRepository

repo = SessionRepository(storage)

# 获取 Session 聚合数据（LazyFrame 链式操作）
df = repo.get_sessions(start_date=..., end_date=..., limit=100)

# 获取最近 Session 详情
sessions = repo.get_recent_sessions(limit=10)

# 获取 VDOT 计算所需数据
vdot_sessions = repo.get_sessions_for_vdot(limit=50)
```

**数据类**: `SessionSummary`, `SessionDetail`, `SessionVdot`

**核心方法**:

| 方法 | 说明 |
|------|------|
| `get_sessions(...)` | 获取 Session 聚合数据，返回 `pl.DataFrame` |
| `get_recent_sessions(limit)` | 获取最近 Session 详情 |
| `get_sessions_for_vdot(limit)` | 获取 VDOT 计算所需数据 |
| `get_session_count(...)` | 获取 Session 数量 |
| `get_total_distance(...)` | 获取总距离（米） |
| `get_total_duration(...)` | 获取总时长（秒） |

---

### AnalyticsEngine

数据分析引擎，提供跑步数据的统计和分析功能。

```python
from src.core.base import AppContextFactory
# 或: from src.core.base.context import AppContextFactory

ctx = AppContextFactory.create()
engine = ctx.analytics
```

# 跑步摘要统计
summary = engine.get_running_summary(start_date="2024-01-01", end_date="2024-12-31")

# 年度统计
stats = engine.get_running_stats(year=2024)

# VDOT 趋势（距离 >= 1500m）
vdot_trend = engine.get_vdot_trend(days=30)

# 训练负荷（ATL/CTL/TSB）
load = engine.get_training_load(days=42)

# 心率漂移分析（相关性 < -0.7 判定为漂移）
drift = engine.analyze_hr_drift(records)
```

**核心方法**:

| 方法 | 参数 | 返回 |
|------|------|------|
| `get_running_summary(start, end)` | 日期范围 | `pl.DataFrame` |
| `get_running_stats(year)` | 年份 | `Dict[str, Any]` |
| `calculate_vdot(distance_m, duration_s)` | 距离(米), 时长(秒) | `float` |
| `get_vdot_trend(days)` | 统计天数 | `List[Dict]` |
| `get_training_load(days)` | 分析天数 | `TrainingLoadResult` TypedDict (含 atl/ctl/tsb/fitness_status) |
| `analyze_hr_drift(records)` | 记录列表 | `Dict` (含 correlation) |

---

### StorageManager

Parquet 存储管理器，负责数据的读写和查询。

```python
from src.core.base import AppContextFactory
# 或: from src.core.base.context import AppContextFactory

ctx = AppContextFactory.create()
storage = ctx.storage
```

# 读取 Parquet（返回 LazyFrame）
lf = storage.read_parquet(years=[2024, 2025])

# 追加活动数据
storage.append_activities(activities)
```

**核心方法**: `read_parquet(years)`, `write_parquet(df, year)`, `append_activities(activities)`

---

### FitParser

FIT 文件解析器。

```python
from src.core.storage import FitParser
# 或: from src.core.storage.parser import FitParser

parser = FitParser()

# 解析单个文件
activity = parser.parse_file("path/to/file.fit")

# 解析目录
activities = parser.parse_directory("path/to/fit/files/")
```

---

### ImportService

数据导入服务，协调解析、去重和存储。

```python
from src.core.base import AppContextFactory
# 或: from src.core.base.context import AppContextFactory

ctx = AppContextFactory.create()
importer = ctx.importer
```

# 导入单个文件
result = importer.import_file("path/to/file.fit", force=False)

# 导入目录
result = importer.import_directory("path/to/fit/files/", force=False)
```

**返回结果**: `{"success": N, "skipped": N, "failed": N, "errors": [...]}`

---

## Agents 模块

### RunnerTools

Agent 工具集，封装为 nanobot-ai 可识别的工具格式。

```python
from src.agents.tools import RunnerTools
from src.core.base import AppContextFactory
# 或: from src.core.base.context import AppContextFactory

ctx = AppContextFactory.create()
tools = RunnerTools(ctx)
```

**工具列表**:

| 工具名称 | 说明 |
|---------|------|
| `get_running_stats` | 获取跑步统计数据 |
| `get_recent_runs` | 获取最近跑步记录 |
| `calculate_vdot_for_run` | 计算单次跑步 VDOT 值 |
| `get_vdot_trend` | 获取 VDOT 趋势 |
| `get_hr_drift_analysis` | 分析心率漂移 |
| `get_training_load` | 获取训练负荷（ATL/CTL/TSB） |
| `query_by_date_range` | 按日期范围查询 |
| `query_by_distance` | 按距离范围查询 |

**返回格式**:

```json
// 成功
{"success": true, "data": {...}, "message": "操作成功"}

// 失败
{"error": "错误描述", "recovery_suggestion": "恢复建议"}
```

---

## Notify 模块

### FeishuBot

飞书消息推送。

```python
from src.notify.feishu import FeishuBot

bot = FeishuBot(webhook_url="https://open.feishu.cn/...")

# 发送文本消息
bot.send_message("训练完成！")

# 发送富文本卡片
bot.send_card(card_data)
```

---

## 智能跑步计划模块

**v0.10.0~v0.12.0 新增**: 三层架构设计（数据感知层 + 智能调整层 + 预测规划层）

### GoalPredictionEngine (v0.12.0)

目标达成评估引擎，预测全马/半马完赛时间。

```python
from src.core.plan.goal_prediction_engine import GoalPredictionEngine

engine = GoalPredictionEngine()
prediction = engine.predict_goal_achievement(
    user_id="default",
    target_distance_km=42.195,
    target_date="2026-06-15",
    current_vdot=42.0,
    training_history=history_data
)
# 返回: predicted_time, confidence_interval, achievement_probability, risk_factors
```

---

### LongTermPlanGenerator (v0.12.0)

长期周期规划引擎，生成多周期训练计划。

```python
from src.core.plan.long_term_plan_generator import LongTermPlanGenerator

generator = LongTermPlanGenerator()
plan = generator.generate_long_term_plan(
    user_id="default",
    goal_distance_km=42.195,
    goal_date="2026-10-15",
    current_vdot=45.0,
    current_weekly_distance_km=40.0,
    cycles=3
)
```

**周期类型**: 基础期 → 进展期 → 巅峰期 → 比赛期 → 恢复期

---

### SmartAdviceEngine (v0.12.0)

智能建议引擎，基于数据分析提供训练建议。

```python
from src.core.plan.smart_advice_engine import SmartAdviceEngine

engine = SmartAdviceEngine()
advice = engine.get_training_advice(
    user_id="default",
    plan_id="plan_20240101",
    focus_area="aerobic"  # aerobic, speed, endurance, recovery
)
```

**建议类型**: 训练不足/过量风险、有氧基础薄弱、强度分布不均衡、恢复不足

---

### PlanAdjustmentValidator (v0.11.0)

计划调整校验器，规则引擎验证调整合理性。

```python
from src.core.plan.plan_adjustment_validator import PlanAdjustmentValidator

validator = PlanAdjustmentValidator()
result = validator.validate_adjustment(
    plan_id="plan_20240101",
    adjustment_type="reduce",
    adjustment_params={"week": 5, "percentage": 20}
)
```

**硬性规则**: 周跑量上限保护、周增量不超过10%、连续高强度限制

**软性规则**: 有氧比例建议、长距离比例建议、恢复日安排

---

### PlanExecutionRepository (v0.10.0)

计划执行仓储，支持计划完成度跟踪和训练反馈记录。

```python
from src.core.plan.plan_execution_repository import PlanExecutionRepository

repo = PlanExecutionRepository()

# 记录执行反馈
repo.record_execution(
    plan_id="plan_20240101",
    date="2024-01-15",
    completion_rate=0.8,
    effort_score=6,
    notes="体感良好"
)

# 获取执行统计
stats = repo.get_plan_execution_stats("plan_20240101")
```

---

## 工具生态模块

**v0.13.0 新增**: 智能技能生态版，支持 MCP 工具管理和外部服务接入。

### ToolManager (v0.13.0)

工具管理器，统一管理 MCP 服务器的生命周期和配置。

```python
from src.core.tools.tool_manager import ToolManager
from pathlib import Path

manager = ToolManager(Path("~/.nanobot-runner/config.json"))

# 列出所有工具
tools = manager.list_tools()

# 启用/禁用工具
manager.enable_tool("weather", "get_forecast")
manager.disable_tool("weather", "get_forecast")

# 服务器管理
manager.add_server("osm", mcp_server_config)
manager.remove_server("osm")
```

**核心方法**:

| 方法 | 说明 |
|------|------|
| `list_tools()` | 列出所有可用工具 |
| `get_tool_status(server, tool)` | 查询工具状态 |
| `enable_tool(server, tool)` | 启用指定工具 |
| `disable_tool(server, tool)` | 禁用指定工具 |
| `discover_tools()` | 发现所有已启用的工具 |
| `add_server(name, config)` | 添加服务器配置 |
| `remove_server(name)` | 移除服务器配置 |

---

### MCPConfigHelper (v0.13.0)

MCP 配置辅助类，提供配置的加载、验证、导入导出功能。

```python
from src.core.tools.mcp_config_helper import MCPConfigHelper

helper = MCPConfigHelper(Path("~/.nanobot-runner/config.json"))

# 加载配置
config = helper.load_tools_config()

# 验证配置
is_valid = helper.validate_mcp_config()
```

---

## 身体信号分析模块 (v0.19.0)

**v0.19.0 新增**: 身体信号分析模块，提供心率变异(HRV)、疲劳度、恢复状态等深度分析能力。

### HRVAnalyzer

心率变异分析引擎，基于现有心率数据提供HRV相关指标分析。

```python
from src.core.analysis.hrv import HRVAnalyzer

analyzer = HRVAnalyzer()

# 分析HRV趋势
result = analyzer.analyze_hrv_trend(days=30)

# 分析单次跑步的心率恢复
recovery = analyzer.analyze_hr_recovery(activity_id="activity_123")

# 获取静息心率趋势
resting_hr = analyzer.get_resting_hr_trend(days=30)
```

**数据类**:

```python
@dataclass(frozen=True)
class HRVAnalysisResult:
    resting_hr_trend: list[RestingHRPoint]  # 静息心率趋势
    hr_recovery_1min: float | None           # 1分钟恢复率(%)
    hr_recovery_3min: float | None           # 3分钟恢复率(%)
    estimated_rmssd: float | None            # 估算RMSSD(ms)
    estimated_sdnn: float | None             # 估算SDNN(ms)
    drift_alert: bool                        # 漂移预警
    assessment: str                          # 综合评估

@dataclass(frozen=True)
class RestingHRPoint:
    date: str
    resting_hr: float
    deviation_pct: float  # 与30天均值偏差百分比
```

---

### FatigueAnalyzer

疲劳度评估引擎，综合训练负荷、心率指标、主观感受量化疲劳状态。

```python
from src.core.analysis.fatigue import FatigueAnalyzer

analyzer = FatigueAnalyzer()

# 计算综合疲劳度评分
score = analyzer.calculate_fatigue_score()

# 获取恢复状态
recovery = analyzer.get_recovery_status()

# 分析连续训练日
consecutive = analyzer.analyze_consecutive_training(days=7)

# 评估休息日效果
rest_effect = analyzer.evaluate_rest_day_effect(rest_date="2024-01-14")
```

**数据类**:

```python
@dataclass(frozen=True)
class FatigueAssessment:
    score: int                    # 0-100分
    level: str                    # 轻度/中等/重度
    status: str                   # 绿/黄/红
    components: dict              # 各维度得分
    recommendation: str           # 训练建议

@dataclass(frozen=True)
class RecoveryStatus:
    status: str                   # 绿/黄/红
    tsb: float                    # 训练压力平衡
    atl: float                    # 急性训练负荷
    ctl: float                    # 慢性训练负荷
    readiness_score: int          # 准备度评分
```

---

### BodySignalInterpreter

身体信号解读引擎，提供异常预警和智能建议。

```python
from src.core.analysis.body_signals import BodySignalInterpreter

interpreter = BodySignalInterpreter()

# 检查异常信号
alerts = interpreter.check_abnormal_signals()

# 生成训练建议
advice = interpreter.generate_training_advice()

# 获取身体信号摘要
summary = interpreter.get_body_signal_summary(period="daily")
```

**Agent工具扩展** (v0.19.0):

| 工具名称 | 说明 |
|---------|------|
| `get_hrv_analysis` | 获取HRV分析报告 |
| `get_hr_recovery` | 获取心率恢复分析 |
| `get_fatigue_assessment` | 获取疲劳度评估 |
| `get_recovery_status` | 获取恢复状态 |
| `check_body_signals` | 检查身体异常信号 |
| `get_training_readiness` | 获取训练准备度评估 |
```

---

## 自适应进化引擎模块 (v0.23.0)

### DecisionLog

决策日志数据模型，记录AI决策完整上下文。

```python
from src.core.evolution.models import DecisionLog
from src.core.transparency import DecisionType

# 创建决策日志
log = DecisionLog(
    decision_id="abc123...",
    timestamp=datetime.now(),
    runner_state={"vdot": 45.2, "ctl": 58, "atl": 65, "tsb": -7, "fatigue_score": 42},
    decision_type=DecisionType.PLAN_ADJUSTMENT,
    tool_call_chain=[{"tool": "check_plan_execution", "output": "..."}],
    prediction_snapshot={"vdot_trend": "+0.3", "injury_risk": "28%"},
    recommendation_text="减少本周跑量10%，注意休息",
    execution_status="pending",
    recommendation_accepted=None,
    session_key="session_001"
)

# 序列化为dict
data = log.to_dict()

# 从dict反序列化
log = DecisionLog.from_dict(data)
```

**字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `decision_id` | str | 决策唯一ID (UUID4) |
| `timestamp` | datetime | 决策时间 |
| `runner_state` | dict | 跑者状态摘要 (5维度) |
| `decision_type` | DecisionType | 决策类型枚举 |
| `tool_call_chain` | list | 工具调用链 |
| `prediction_snapshot` | dict | 预测快照 |
| `recommendation_text` | str | 建议文本 |
| `execution_status` | str | 执行状态 (pending/executed/skipped/modified/failed) |
| `recommendation_accepted` | bool \| None | 是否采纳 |
| `session_key` | str | 会话标识 |

---

### OutcomeRecord

结果记录数据模型，记录决策执行结果。

```python
from src.core.evolution.models import OutcomeRecord

# 创建结果记录
outcome = OutcomeRecord(
    outcome_id="out_001",
    decision_id="abc123...",
    outcome_timestamp=datetime.now(),
    actual_vdot=45.5,
    actual_injury=False,
    execution_fidelity=0.82,
    user_feedback_score=4,
    user_feedback_text="建议很实用",
    prediction_error=3.2,
    prediction_direction="accurate",
    session_id="session_001"
)
```

**字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `outcome_id` | str | 结果唯一ID |
| `decision_id` | str | 关联决策ID |
| `outcome_timestamp` | datetime | 结果记录时间 |
| `actual_vdot` | float | 实际VDOT值 |
| `actual_injury` | bool | 是否发生伤病 |
| `execution_fidelity` | float | 执行忠实度 (0-1) |
| `user_feedback_score` | int | 用户评分 (1-5) |
| `user_feedback_text` | str | 用户文本反馈 |
| `prediction_error` | float | 预测误差百分比 |
| `prediction_direction` | str | 偏差方向 (overestimate/underestimate/accurate/None) |
| `session_id` | str | 会话标识 |

---

### EvolutionConfig

进化模块配置Schema。

```python
from src.core.evolution.config import EvolutionConfig

# 使用默认配置
config = EvolutionConfig()

# 自定义配置
config = EvolutionConfig(
    data_dir="~/.nanobot-runner",
    async_write_enabled=False,
    runner_state_fields=["vdot", "ctl", "atl", "tsb", "fatigue_score"]
)
```

**配置项说明**:

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `data_dir` | str | ~/.nanobot-runner | 数据存储路径 |
| `async_write_enabled` | bool | False | 是否启用异步写入 |
| `async_write_queue_size` | int | 100 | 异步写入队列容量 |
| `async_write_max_retries` | int | 3 | 最大重试次数 |
| `async_write_retry_backoff` | float | 1.0 | 重试退避时间(秒) |
| `feedback_prompt_frequency` | int | 5 | 反馈提示频率 |
| `runner_state_fields` | list | [vdot,ctl,atl,tsb,fatigue_score] | 状态摘要字段 |

---

### EvolutionStore

决策与结果存储层。

```python
from src.core.evolution.evolution_store import EvolutionStore
from src.core.evolution.config import EvolutionConfig

# 创建存储实例
store = EvolutionStore(config=EvolutionConfig())

# 保存决策日志
store.save_decision(decision_log)

# 保存结果记录
store.save_outcome(outcome_record)

# 查询决策历史
decisions = store.query_decisions(start_date="2026-04-01", end_date="2026-05-01")

# 查询结果记录
outcomes = store.query_outcomes(decision_ids=["abc123"])

# 获取决策-结果配对数据
pairs = store.get_decision_outcome_pairs(days=30)
```

**核心方法**:

| 方法 | 说明 |
|------|------|
| `save_decision(decision)` | 保存决策日志到按月分片Parquet |
| `save_outcome(outcome)` | 保存结果记录到按月分片Parquet |
| `query_decisions(...)` | 按日期/类型过滤查询决策 |
| `query_outcomes(...)` | 按decision_id查询结果 |
| `get_decision_by_id(id)` | 按ID精确查询单条决策 |
| `get_decision_outcome_pairs(...)` | 获取决策-结果配对数据 |

---

### EvolutionEngine

进化引擎编排层。

```python
from src.core.evolution import EvolutionEngine
from src.core.base import get_context

# 通过依赖注入获取
context = get_context()
engine = context.evolution_engine

# 获取进化状态
status = engine.get_evolution_status()

# 查询决策历史
history = engine.query_history(days=30)

# 提交用户反馈
engine.submit_feedback(decision_id, score=4, text="很好", accepted=True)
```

**核心方法**:

| 方法 | 说明 |
|------|------|
| `get_evolution_status()` | 获取进化状态摘要 |
| `query_history(...)` | 查询决策历史 |
| `submit_feedback(...)` | 提交用户反馈 |
| `get_accuracy_stats(...)` | 获取预测准确度统计 |
| `get_fidelity_stats(...)` | 获取执行忠实度统计 |

---

### DecisionLogHook

Agent生命周期钩子，无侵入接入决策记录。

```python
from src.core.evolution.decision_log_hook import DecisionLogHook
from src.core.evolution.evolution_store import EvolutionStore
from src.core.evolution.config import EvolutionConfig

# 创建Hook实例
hook = DecisionLogHook(
    store=EvolutionStore(),
    config=EvolutionConfig()
)

# 钩子方法（由Agent自动调用）
hook.before_iteration(runner_state)  # 捕获状态快照
hook.before_execute_tools(tool_name, tool_output)  # 记录工具调用
hook.finalize_content(decision, content)  # 完成决策日志记录
```

**钩子方法**:

| 方法 | 说明 |
|------|------|
| `before_iteration(state)` | 捕获runner_state摘要 |
| `before_execute_tools(name, output)` | 记录工具调用链 |
| `finalize_content(decision, content)` | 完成决策日志写入 |

---

### Agent工具 (v0.23.0)

| 工具名称 | 说明 |
|---------|------|
| `check_plan_execution` | 检查计划执行忠实度 |
| `check_prediction_accuracy` | 检查预测准确度 |

---

## WebUI 数据可视化 API (v0.28.0)

**v0.28.0 新增**: FastAPI 数据可视化后端，独立运行在端口 8766，为 WebUI 前端提供 REST API。

### 应用工厂

```python
from src.core.webui.app import create_webui_app

# 创建 WebUI 应用
app = create_webui_app()

# 健康检查
# GET /api/health → {"status": "ok", "version": "0.28.0"}
```

### 认证中间件

所有 `/api/webui/*` 端点（除 `/api/health`）需携带有效 Token：

```
Authorization: Bearer <token>
```

Token 通过 nanobot-ai 的 `token_issue_path` 签发：
```bash
curl http://127.0.0.1:8765/token
# → {"token": "eyJ...", "expires_in": 300}
```

### Dashboard API

```python
# GET /api/webui/dashboard?days=7
# 返回: 今日概览 + 本周统计
```

**响应 Schema**:
```json
{
  "today": {
    "distance_km": 5.2,
    "duration_s": 1800,
    "avg_pace_min_km": 5.77,
    "avg_hr": 152,
    "is_rest_day": false
  },
  "week": {
    "total_distance_km": 35.8,
    "total_duration_s": 12600,
    "total_tss": 450,
    "run_count": 4
  }
}
```

### VDOT 趋势 API

```python
# GET /api/webui/vdot/trend?days=90
# 返回: VDOT 趋势数据列表
```

**响应 Schema**:
```json
{
  "items": [
    {"date": "2026-05-01", "vdot": 45.2, "distance": 5000, "duration": 1500}
  ],
  "days": 90
}
```

### 训练负荷 API

```python
# GET /api/webui/training-load?days=42
# 返回: 当日 ATL/CTL/TSB 数据

# GET /api/webui/training-load/trend?days=42
# 返回: 训练负荷趋势数据列表
```

**响应 Schema**:
```json
{
  "items": [
    {"date": "2026-05-01", "atl": 65, "ctl": 58, "tsb": -7, "fitness_status": "optimal"}
  ],
  "days": 42
}
```

`fitness_status` 取值: `fresh`(>15) / `optimal`(0~15) / `fatigued`(-30~0) / `overtrained`(<-30)

### 活动列表 API

```python
# GET /api/webui/activities?page=1&size=20&start_date=2026-01-01&end_date=2026-12-31&min_distance=5000
```

**响应 Schema**:
```json
{
  "total": 150,
  "page": 1,
  "size": 20,
  "items": [
    {
      "id": "sha256_hash",
      "date": "2026-05-01",
      "distance_km": 10.5,
      "duration": "0:52:30",
      "avg_pace": "5'00\"",
      "avg_hr": 155
    }
  ]
}
```

### 活动详情 API

```python
# GET /api/webui/activities/{sha256_hash}
# 返回: 单次跑步完整数据
```

**响应 Schema**:
```json
{
  "id": "sha256_hash",
  "date": "2026-05-01",
  "distance_km": 10.5,
  "duration_s": 3150,
  "avg_pace_min_km": 5.0,
  "avg_hr": 155,
  "max_hr": 178,
  "vdot": 45.2,
  "tss": 85,
  "calories": 650
}
```

### 身体信号 API

```python
# GET /api/webui/body-signals          # 汇总
# GET /api/webui/body-signals/hrv       # HRV 分析
# GET /api/webui/body-signals/fatigue   # 疲劳度
# GET /api/webui/body-signals/recovery  # 恢复状态
```

**HRV 响应**:
```json
{
  "resting_hr_trend": [{"date": "2026-05-01", "resting_hr": 52}],
  "estimated_rmssd": 45.2,
  "estimated_sdnn": 52.8,
  "assessment": "恢复良好"
}
```

**疲劳响应**:
```json
{
  "score": 45,
  "level": "中等",
  "status": "yellow",
  "recommendation": "适合轻松跑"
}
```

### Server 封装

```python
from src.core.webui.server import WebUIServer

# 启动 WebUI 服务
server = WebUIServer(app=app, host="127.0.0.1", port=8766)
server.start()
```

**数据一致性**: 所有 WebUI API 与 CLI 使用相同数据源（AnalyticsEngine + SessionRepository），保证数值误差 < 0.1%。

**性能**: 所有同步调用使用 `run_in_threadpool()` 包装，避免阻塞 asyncio 事件循环。

