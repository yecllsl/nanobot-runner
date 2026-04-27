# Nanobot Runner API 参考文档

本文档描述 Nanobot Runner 的核心 API 接口。

## 目录

- [运行环境与初始化](#运行环境与初始化)
- [Core 模块](#core-模块)
  - [AppContext](#appcontext) (v0.9.0 新增)
  - [AppContextFactory](#appcontextfactory) (v0.9.0 新增)
  - [SessionRepository](#sessionrepository) (v0.9.0 新增)
  - [AnalyticsEngine](#analyticsengine)
  - [StorageManager](#storagemanager)
  - [FitParser](#fitparser)
  - [ImportService](#importservice)
  - [智能跑步计划模块](#智能跑步计划模块) (v0.10.0~v0.12.0 新增)
    - [GoalPredictionEngine](#goalpredictionengine) (v0.12.0)
    - [LongTermPlanGenerator](#longtermplangenerator) (v0.12.0)
    - [SmartAdviceEngine](#smartadviceengine) (v0.12.0)
    - [PlanAdjustmentValidator](#planadjustmentvalidator) (v0.11.0)
    - [PlanExecutionRepository](#planexecutionrepository) (v0.10.0)
  - [工具生态模块](#工具生态模块) (v0.13.0 新增)
    - [ToolManager](#toolmanager) (v0.13.0)
    - [MCPConfigHelper](#mcpconfighelper) (v0.13.0)
    - [MCPConnector](#mcpconnector) (v0.13.0)
- [Agents 模块](#agents-模块)
  - [RunnerTools](#runnertools)
- [Notify 模块](#notify-模块)
  - [FeishuBot](#feishubot)

---

## 运行环境与初始化

### nanobot Workspace 结构

Nanobot Runner 使用 `~/.nanobot-runner` 作为 nanobot workspace：

```
~/.nanobot-runner/
├── data/                    # 业务数据存储
│   ├── activities_*.parquet # 运动数据（按年分片）
│   ├── profile.json         # 结构化画像数据
│   └── index.json           # 去重索引
├── memory/                  # 记忆系统
│   ├── MEMORY.md            # 长期记忆/用户画像
│   └── HISTORY.md           # 事件日志
├── sessions/                # 会话历史
├── skills/                  # 技能扩展
├── AGENTS.md                # Agent行为准则
├── SOUL.md                  # 人格设定
├── USER.md                  # 用户画像
└── config.json              # 应用配置
```

### 自动初始化机制

> ⚠️ **重要**：workspace 目录结构由 nanobot-ai 框架自动初始化，无需自定义实现。

**自动创建的文件/目录**：`AGENTS.md`, `SOUL.md`, `USER.md`, `memory/MEMORY.md`, `memory/HISTORY.md`, `skills/`

**应用需自行创建的目录**：`data/`, `logs/`

---

## Core 模块

### AppContext

应用上下文，集中管理所有核心组件的实例，支持依赖注入和测试。

> **v0.9.0 新增**

#### 初始化

```python
from src.core.context import AppContext, AppContextFactory

# 通过工厂创建（推荐）
ctx = AppContextFactory.create()

# 直接初始化（不推荐，用于特殊场景）
from src.core.config import ConfigManager
from src.core.storage import StorageManager

config = ConfigManager()
storage = StorageManager(config.data_dir)
ctx = AppContext(
    config=config,
    storage=storage,
    # ... 其他组件
)
```

#### 属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `config` | ConfigManager | 配置管理器 |
| `storage` | StorageManager | 存储管理器 |
| `indexer` | IndexManager | 索引管理器 |
| `parser` | FitParser | FIT 文件解析器 |
| `importer` | ImportService | 导入服务 |
| `analytics` | AnalyticsEngine | 分析引擎 |
| `profile_engine` | ProfileEngine | 用户画像引擎 |
| `profile_storage` | ProfileStorageManager | 用户画像存储管理器 |

#### 方法

##### `get_extension(name: str) -> Optional[Any]`

获取扩展组件。

**参数:**
- `name` (str): 扩展组件名称

**返回:** `Optional[Any]` - 扩展组件实例，不存在则返回 None

---

##### `set_extension(name: str, instance: Any) -> None`

设置扩展组件。

**参数:**
- `name` (str): 扩展组件名称
- `instance` (Any): 扩展组件实例

---

### AppContextFactory

应用上下文工厂，负责创建和配置 AppContext 实例，支持自定义依赖注入。

> **v0.9.0 新增**

#### 静态方法

##### `create(...) -> AppContext`

创建应用上下文，支持依赖注入，未提供的组件将自动创建默认实例。

**参数:**
- `config` (ConfigManager, optional): 配置管理器
- `storage` (StorageManager, optional): 存储管理器
- `indexer` (IndexManager, optional): 索引管理器
- `parser` (FitParser, optional): FIT 文件解析器
- `importer` (ImportService, optional): 导入服务
- `analytics` (AnalyticsEngine, optional): 分析引擎
- `profile_engine` (ProfileEngine, optional): 用户画像引擎
- `profile_storage` (ProfileStorageManager, optional): 用户画像存储管理器

**返回:** `AppContext` - 配置好的 AppContext 实例

**示例:**

```python
from src.core.context import AppContextFactory

# 创建默认上下文
ctx = AppContextFactory.create()

# 自定义依赖注入（用于测试）
from unittest.mock import Mock

mock_storage = Mock()
ctx = AppContextFactory.create(storage=mock_storage)
```

---

##### `create_for_testing(...) -> AppContext`

创建用于测试的应用上下文，与 `create()` 方法相同，但明确表示用于测试场景。

**参数:** 同 `create()`

**返回:** `AppContext` - 配置好的 AppContext 实例

---

### SessionRepository

Session 数据仓储层，封装 Session 级别的数据聚合查询，保持 LazyFrame 链式操作。

> **v0.9.0 新增**

#### 初始化

```python
from src.core.session_repository import SessionRepository
from src.core.storage import StorageManager

storage = StorageManager()
repo = SessionRepository(storage)
```

#### 数据类

##### `SessionSummary`

Session 摘要数据类，替代 Dict[str, Any] 提升类型安全。

**属性:**
- `timestamp` (str): 时间戳
- `distance_km` (float): 距离（公里）
- `duration_min` (float): 时长（分钟）
- `avg_pace_sec_km` (Optional[float]): 平均配速（秒/公里）
- `avg_heart_rate` (Optional[float]): 平均心率

---

##### `SessionDetail`

Session 详情数据类，包含完整字段。

**继承:** SessionSummary

**额外属性:**
- `distance_m` (float): 距离（米）
- `duration_s` (float): 时长（秒）
- `max_heart_rate` (Optional[float]): 最大心率
- `calories` (Optional[float]): 消耗卡路里

---

##### `SessionVdot`

VDOT 计算所需的 Session 数据。

**属性:**
- `timestamp` (str): 时间戳
- `distance_m` (float): 距离（米）
- `duration_s` (float): 时长（秒）
- `avg_heart_rate` (Optional[float]): 平均心率

---

#### 方法

##### `get_sessions(...) -> pl.DataFrame`

获取 Session 聚合数据，保持 LazyFrame 链式操作，仅在最终返回前 collect()。

**参数:**
- `start_date` (datetime, optional): 开始日期
- `end_date` (datetime, optional): 结束日期
- `min_distance` (float, optional): 最小距离（米）
- `max_distance` (float, optional): 最大距离（米）
- `limit` (int, optional): 返回数量限制
- `descending` (bool): 是否按时间降序，默认 True

**返回:** `pl.DataFrame` - Session 聚合结果

---

##### `get_recent_sessions(limit: int = 10) -> List[SessionDetail]`

获取最近的 Session 详情。

**参数:**
- `limit` (int): 返回数量限制，默认 10

**返回:** `List[SessionDetail]` - Session 详情列表

---

##### `get_sessions_for_vdot(limit: Optional[int] = None) -> List[SessionVdot]`

获取 VDOT 计算所需的 Session 数据。

**参数:**
- `limit` (int, optional): 返回数量限制

**返回:** `List[SessionVdot]` - VDOT 计算所需的 Session 列表

---

##### `get_sessions_by_date_range(start_date: datetime, end_date: datetime) -> List[SessionSummary]`

按日期范围获取 Session 摘要。

**参数:**
- `start_date` (datetime): 开始日期
- `end_date` (datetime): 结束日期

**返回:** `List[SessionSummary]` - Session 摘要列表

---

##### `get_sessions_by_distance(min_meters: float, max_meters: Optional[float] = None) -> List[SessionSummary]`

按距离范围获取 Session 摘要。

**参数:**
- `min_meters` (float): 最小距离（米）
- `max_meters` (float, optional): 最大距离（米）

**返回:** `List[SessionSummary]` - Session 摘要列表

---

##### `get_session_count(start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> int`

获取 Session 数量。

**参数:**
- `start_date` (datetime, optional): 开始日期
- `end_date` (datetime, optional): 结束日期

**返回:** `int` - Session 数量

---

##### `get_total_distance(start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> float`

获取总距离。

**参数:**
- `start_date` (datetime, optional): 开始日期
- `end_date` (datetime, optional): 结束日期

**返回:** `float` - 总距离（米）

---

##### `get_total_duration(start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> float`

获取总时长。

**参数:**
- `start_date` (datetime, optional): 开始日期
- `end_date` (datetime, optional): 结束日期

**返回:** `float` - 总时长（秒）

---

### AnalyticsEngine

数据分析引擎，提供跑步数据的统计和分析功能。

#### 初始化

```python
from src.core.analytics import AnalyticsEngine
from src.core.storage import StorageManager

# 旧方式（已废弃）
storage = StorageManager()
engine = AnalyticsEngine(storage)

# 新方式（v0.9.0 推荐）
from src.core.context import AppContextFactory

ctx = AppContextFactory.create()
engine = ctx.analytics
```

#### 方法

##### `get_running_summary(start_date=None, end_date=None) -> pl.DataFrame`

获取跑步摘要统计。

**参数:**
- `start_date` (str, optional): 开始日期，格式 "YYYY-MM-DD"
- `end_date` (str, optional): 结束日期，格式 "YYYY-MM-DD"

**返回:** `pl.DataFrame` - 包含统计信息的 DataFrame

---

##### `get_running_stats(year=None) -> Dict[str, Any]`

获取年度或总体跑步统计。

**参数:**
- `year` (int, optional): 年份，为 None 时返回总体统计

**返回:** `Dict[str, Any]` - 包含 `total_runs`, `total_distance`, `total_duration`, `avg_heart_rate`

---

##### `calculate_vdot(distance_m, duration_s) -> float`

计算 VDOT 值（基于 Jack Daniels 公式，距离 >= 1500m）。

**参数:**
- `distance_m` (float): 距离（米）
- `duration_s` (float): 时长（秒）

**返回:** `float` - VDOT 值

---

##### `get_vdot_trend(days=30) -> List[Dict[str, Any]]`

获取 VDOT 趋势数据。

**参数:**
- `days` (int): 统计天数，默认 30

**返回:** `List[Dict[str, Any]]` - 包含 `date`, `vdot`, `distance`, `duration`

---

##### `get_training_load(days=42) -> Dict[str, Any]`

获取训练负荷（ATL/CTL/TSB）及体能状态评估。

**参数:**
- `days` (int): 分析天数，建议至少 42 天

**返回:** `Dict[str, Any]` - 包含 `atl`, `ctl`, `tsb`, `fitness_status`, `training_advice`

---

##### `get_training_load_trend(start_date=None, end_date=None, days=None) -> Dict[str, Any]`

获取训练负荷趋势数据（每日 TSS、ATL、CTL、TSB）。

**参数:**
- `start_date` (str, optional): 开始日期
- `end_date` (str, optional): 结束日期
- `days` (int, optional): 最近 N 天，优先级高于日期范围

**返回:** `Dict[str, Any]` - 包含 `trend_data` 和 `summary`

---

##### `get_pace_distribution(year=None) -> Dict[str, Any]`

获取配速分布统计。

**参数:**
- `year` (int, optional): 年份筛选

**返回:** `Dict[str, Any]` - 包含 `zones`, `trend`, `total_runs`, `total_distance`

---

##### `analyze_hr_drift(records) -> Dict[str, Any]`

分析心率漂移。相关性 < -0.7 判定为漂移。

**参数:**
- `records` (List[Dict]): 跑步记录列表

**返回:** `Dict[str, Any]` - 包含 `drift_percentage`, `correlation`, `is_valid`, `message`

---

### StorageManager

Parquet 存储管理器，负责数据的读写和查询。

#### 初始化

```python
from src.core.storage import StorageManager

# 旧方式（已废弃）
storage = StorageManager(data_dir="~/.nanobot-runner/data")

# 新方式（v0.9.0 推荐）
from src.core.context import AppContextFactory

ctx = AppContextFactory.create()
storage = ctx.storage
```

#### 方法

##### `read_parquet(years=None) -> pl.LazyFrame`

读取 Parquet 文件，返回 LazyFrame。

**参数:**
- `years` (List[int], optional): 年份列表，为 None 时读取所有年份

**返回:** `pl.LazyFrame` - 延迟执行的 DataFrame

---

##### `write_parquet(df, year) -> None`

写入 DataFrame 到 Parquet 文件。

**参数:**
- `df` (pl.DataFrame): 要写入的数据
- `year` (int): 年份

---

##### `append_activities(activities) -> None`

追加活动数据到存储。

**参数:**
- `activities` (List[Dict]): 活动数据列表

---

### FitParser

FIT 文件解析器。

#### 初始化

```python
from src.core.parser import FitParser

parser = FitParser()
```

#### 方法

##### `parse_file(file_path) -> Dict[str, Any]`

解析单个 FIT 文件。

**参数:**
- `file_path` (str): FIT 文件路径

**返回:** `Dict[str, Any]` - 解析后的活动数据

---

##### `parse_directory(directory) -> List[Dict[str, Any]]`

解析目录中的所有 FIT 文件。

**参数:**
- `directory` (str): 目录路径

**返回:** `List[Dict[str, Any]]` - 活动数据列表

---

### ImportService

数据导入服务，协调解析、去重和存储。

#### 初始化

```python
from src.core.importer import ImportService
from src.core.storage import StorageManager
from src.core.indexer import IndexManager

# 旧方式（已废弃）
storage = StorageManager()
indexer = IndexManager()
parser = FitParser()
importer = ImportService(parser, storage, indexer)

# 新方式（v0.9.0 推荐）
from src.core.context import AppContextFactory

ctx = AppContextFactory.create()
importer = ctx.importer
```

#### 方法

##### `import_file(file_path, force=False) -> Dict[str, Any]`

导入单个 FIT 文件。

**参数:**
- `file_path` (str): FIT 文件路径
- `force` (bool): 强制导入，忽略去重

**返回:** `Dict[str, Any]` - 导入结果

---

##### `import_directory(directory, force=False) -> Dict[str, Any]`

导入目录中的所有 FIT 文件。

**参数:**
- `directory` (str): 目录路径
- `force` (bool): 强制导入

**返回:** `Dict[str, Any]` - 导入结果汇总

---

## Agents 模块

### RunnerTools

Agent 工具集，封装为 nanobot-ai 可识别的工具格式。

#### 初始化

```python
from src.agents.tools import RunnerTools

# 旧方式（已废弃）
tools = RunnerTools()

# 新方式（v0.9.0 推荐）
from src.core.context import AppContextFactory

ctx = AppContextFactory.create()
tools = RunnerTools(ctx)
```

#### 工具列表

| 工具名称 | 说明 |
|---------|------|
| `get_running_stats` | 获取跑步统计数据 |
| `get_recent_runs` | 获取最近跑步记录 |
| `calculate_vdot_for_run` | 计算单次跑步VDOT值 |
| `get_vdot_trend` | 获取VDOT趋势 |
| `get_hr_drift_analysis` | 分析心率漂移 |
| `get_training_load` | 获取训练负荷（ATL/CTL/TSB） |
| `query_by_date_range` | 按日期范围查询 |
| `query_by_distance` | 按距离范围查询 |

#### 返回格式

所有工具返回 JSON 字符串，格式：

```json
{
  "success": true,
  "data": { ... },
  "message": "操作成功"
}
```

或错误时：

```json
{
  "error": "错误描述",
  "recovery_suggestion": "恢复建议"
}
```

---

## Notify 模块

### FeishuBot

飞书消息推送。

#### 初始化

```python
from src.notify.feishu import FeishuBot

bot = FeishuBot(webhook_url="https://open.feishu.cn/...")
```

#### 方法

##### `send_message(message) -> bool`

发送文本消息。

**参数:**
- `message` (str): 消息内容

**返回:** `bool` - 发送成功返回 True

---

##### `send_card(card_data) -> bool`

发送富文本卡片。

**参数:**
- `card_data` (Dict): 卡片数据

**返回:** `bool` - 发送成功返回 True

---

### 智能跑步计划模块

**v0.10.0~v0.12.0 新增**: 三层架构设计（数据感知层 + 智能调整层 + 预测规划层）

#### GoalPredictionEngine (v0.12.0)

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
```

**返回结果:**
- `predicted_time`: 预测完赛时间
- `confidence_interval`: 置信区间
- `achievement_probability`: 达成概率
- `risk_factors`: 风险因素列表

#### LongTermPlanGenerator (v0.12.0)

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

**周期类型:**
- 基础期 (Base): 建立有氧基础
- 进展期 (Build): 提升专项能力
- 巅峰期 (Peak): 达到最佳状态
- 比赛期 (Race): 赛前调整
- 恢复期 (Recovery): 赛后恢复

#### SmartAdviceEngine (v0.12.0)

智能建议引擎，基于数据分析提供训练建议。

```python
from src.core.plan.smart_advice_engine import SmartAdviceEngine

engine = SmartAdviceEngine()
advice = engine.get_training_advice(
    user_id="default",
    plan_id="plan_20240101",
    focus_area="aerobic"  # 可选: aerobic, speed, endurance, recovery
)
```

**建议类型:**
- 训练不足/过量风险
- 有氧基础薄弱
- 强度分布不均衡
- 恢复不足

#### PlanAdjustmentValidator (v0.11.0)

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

**硬性规则:**
- 周跑量上限保护
- 周增量不超过10%
- 连续高强度限制

**软性规则:**
- 有氧比例建议
- 长距离比例建议
- 恢复日安排

#### PlanExecutionRepository (v0.10.0)

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

### 工具生态模块

**v0.13.0 新增**: 智能技能生态版，支持 MCP 工具管理和外部服务接入。

#### ToolManager (v0.13.0)

工具管理器，统一管理 MCP 服务器的生命周期和配置。

```python
from src.core.tools.tool_manager import ToolManager
from pathlib import Path

manager = ToolManager(Path("~/.nanobot-runner/config.json"))

# 列出所有工具
tools = manager.list_tools()

# 获取工具状态
status = manager.get_tool_status("weather", "get_forecast")

# 启用/禁用工具
manager.enable_tool("weather", "get_forecast")
manager.disable_tool("weather", "get_forecast")

# 服务器管理
manager.add_server("osm", mcp_server_config)
manager.remove_server("osm")
manager.enable_server("osm")
manager.disable_server("osm")
```

**核心方法:**
- `list_tools() -> List[ToolInfo]`: 列出所有可用工具
- `get_tool_status(server_name, tool_name) -> ToolStatus`: 查询工具状态
- `enable_tool(server_name, tool_name)`: 启用指定工具
- `disable_tool(server_name, tool_name)`: 禁用指定工具
- `discover_tools() -> List[ToolInfo]`: 发现所有已启用的工具
- `list_servers() -> List[str]`: 列出所有服务器名称
- `add_server(name, config)`: 添加服务器配置
- `remove_server(name)`: 移除服务器配置
- `enable_server(name)`: 启用服务器
- `disable_server(name)`: 禁用服务器

#### MCPConfigHelper (v0.13.0)

MCP 配置辅助类，提供配置的加载、验证、导入导出功能。

```python
from src.core.tools.mcp_config_helper import MCPConfigHelper

helper = MCPConfigHelper(Path("~/.nanobot-runner/config.json"))

# 加载配置
config = helper.load_tools_config()

# 验证配置
is_valid = helper.validate_mcp_config()

# 添加服务器
helper.add_mcp_server(
    name="weather",
    command="npx",
    args=["-y", "@h1deya/mcp-server-weather"],
    transport_type="stdio"
)

# 导入 Claude Desktop 配置
helper.import_claude_desktop_config()
```

**核心方法:**
- `load_tools_config() -> ToolsConfig`: 从 config.json 加载工具配置
- `save_tools_config(config)`: 保存工具配置到 config.json
- `validate_mcp_config() -> bool`: 验证 MCP 配置完整性
- `list_mcp_tools() -> List[str]`: 列出所有 MCP 工具名称
- `add_mcp_server(...)`: 添加 MCP 服务器配置
- `remove_mcp_server(name)`: 移除 MCP 服务器配置
- `update_mcp_server(name, ...)`: 更新 MCP 服务器配置
- `import_claude_desktop_config()`: 导入 Claude Desktop 配置

#### MCPConnector (v0.13.0)

MCP 连接器，负责与 MCP 服务器建立连接和工具发现。

```python
from src.core.tools.mcp_connector import MCPConnector

connector = MCPConnector()

# 连接 MCP 服务器
tools = await connector.connect_mcp_server(
    server_name="weather",
    config=mcp_server_config
)

# 断开连接
await connector.disconnect_mcp_server("weather")

# 获取工具模式
tool_schemas = connector.get_tool_schemas("weather")
```

**核心方法:**
- `connect_mcp_server(name, config) -> List[Tool]`: 连接 MCP 服务器
- `disconnect_mcp_server(name)`: 断开 MCP 服务器连接
- `get_tool_schemas(server_name) -> List[dict]`: 获取工具 JSON Schema
- `is_server_connected(name) -> bool`: 检查服务器连接状态

## 相关文档

- [AnalyticsEngine API](./analytics_engine.md) - 详细 API 文档
- [StorageManager API](./storage_manager.md) - 存储管理器详细文档
- [RunnerTools API](./runner_tools.md) - Agent 工具集详细文档
- [CLI 用户指南](../guides/cli_usage.md) - 命令行使用指南
- [架构设计说明书](../architecture/架构设计说明书.md) - 智能跑步计划架构设计

---

*文档版本: v0.13.0*
*更新时间: 2026-04-27*
