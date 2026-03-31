# Nanobot Runner API 参考文档

本文档描述 Nanobot Runner 的核心 API 接口。

## 目录

- [运行环境与初始化](#运行环境与初始化)
- [Core 模块](#core-模块)
  - [AnalyticsEngine](#analyticsengine)
  - [StorageManager](#storagemanager)
  - [FitParser](#fitparser)
  - [ImportService](#importservice)
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

### AnalyticsEngine

数据分析引擎，提供跑步数据的统计和分析功能。

#### 初始化

```python
from src.core.analytics import AnalyticsEngine
from src.core.storage import StorageManager

storage = StorageManager()
engine = AnalyticsEngine(storage)
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

storage = StorageManager(data_dir="~/.nanobot-runner/data")
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

storage = StorageManager()
indexer = IndexManager()
importer = ImportService(storage, indexer)
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

tools = RunnerTools()
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

## 相关文档

- [AnalyticsEngine API](./analytics_engine.md) - 详细 API 文档
- [StorageManager API](./storage_manager.md) - 存储管理器详细文档
- [RunnerTools API](./runner_tools.md) - Agent 工具集详细文档
- [CLI 用户指南](../guides/cli_usage.md) - 命令行使用指南

---

*文档版本: v0.4.1*
*更新时间: 2026-03-30*
