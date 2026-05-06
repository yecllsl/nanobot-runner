# Nanobot Runner API 参考文档

本文档描述 Nanobot Runner 的核心 API 接口。

> **文档版本**: v0.19.0 | **更新日期**: 2026-05-06
> **当前基线**: v0.18.0 | **规划版本**: v0.19.0
> **提示**: 详细参数说明和完整代码示例参见 [docs/api/api_reference_detailed.md](api_reference_detailed.md)
> **v0.18.0 重要变更**: 新增数据可视化模块(terminal charts)、数据导出模块(multi-format export)
> **v0.19.0 规划变更**: 新增身体信号分析模块(HRV/疲劳度/恢复评估)

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
| `get_training_load(days)` | 分析天数 | `Dict` (含 atl/ctl/tsb) |
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
