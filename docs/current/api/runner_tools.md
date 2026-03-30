# RunnerTools API 参考

## 概述

`RunnerTools` 是 Nanobot Runner 的 Agent 工具集，封装为 nanobot-ai 可识别的工具格式。提供自然语言交互接口，支持跑步数据的查询和分析。

## 类定义

### `RunnerTools`

```python
class RunnerTools:
    def __init__(self, storage_manager: Optional[StorageManager] = None) -> None
```

**参数：**

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `storage_manager` | `Optional[StorageManager]` | None | StorageManager 实例 |

---

## 工具列表

### `get_running_stats(year: Optional[int] = None) -> str`

获取跑步统计数据。

**参数：**

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `year` | `Optional[int]` | None | 年份，None 表示全部 |

**返回值：** `str` - JSON 格式的统计结果

**返回字段：**

```json
{
  "total_runs": 100,
  "total_distance": 500000,
  "total_duration": 180000,
  "avg_distance": 5000,
  "avg_duration": 1800,
  "max_distance": 42195,
  "avg_heart_rate": 145
}
```

**自然语言示例：** "我今年跑了多少次？"、"查看2024年的跑步统计"

---

### `get_recent_runs(limit: int = 10) -> str`

获取最近的跑步记录。

**参数：**

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `limit` | `int` | 10 | 返回记录数量 |

**返回值：** `str` - JSON 格式的跑步记录列表

**自然语言示例：** "我最近跑了哪些步？"、"显示最近5次跑步"

---

### `calculate_vdot_for_run(distance_km: float, time_minutes: float) -> str`

计算单次跑步的 VDOT 值。距离需 >= 1.5km。

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `distance_km` | `float` | 距离（公里） |
| `time_minutes` | `float` | 用时（分钟） |

**返回值：** `str` - JSON 格式的 VDOT 计算结果

**自然语言示例：** "5公里25分钟的VDOT是多少？"

---

### `get_vdot_trend(days: int = 30) -> str`

获取 VDOT 趋势数据。

**参数：**

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `days` | `int` | 30 | 统计天数 |

**返回值：** `str` - JSON 格式的 VDOT 趋势数据

**自然语言示例：** "我的VDOT趋势如何？"

---

### `get_hr_drift_analysis(activity_id: Optional[str] = None) -> str`

获取心率漂移分析。相关性 < -0.7 判定为漂移。

**参数：**

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `activity_id` | `Optional[str]` | None | 活动ID，None 表示最近一次 |

**返回值：** `str` - JSON 格式的心率漂移分析结果

**自然语言示例：** "分析这次跑步的心率漂移"

---

### `get_training_load(days: int = 42) -> str`

获取训练负荷数据。

**参数：**

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `days` | `int` | 42 | 分析天数 |

**返回值：** `str` - JSON 格式的训练负荷数据

**返回字段：**

```json
{
  "atl": 65.5,
  "ctl": 58.2,
  "tsb": -7.3,
  "fitness_status": "疲劳积累",
  "training_advice": "建议适当降低训练强度",
  "days_analyzed": 42,
  "runs_count": 28
}
```

**自然语言示例：** "我的训练负荷如何？"

---

### `get_training_load_trend(days: int = 30) -> str`

获取训练负荷趋势。

**返回值：** `str` - JSON 格式的训练负荷趋势数据

**自然语言示例：** "最近一个月的训练趋势"

---

### `query_by_date_range(start_date: str, end_date: str) -> str`

按日期范围查询跑步记录。

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `start_date` | `str` | 开始日期（YYYY-MM-DD） |
| `end_date` | `str` | 结束日期（YYYY-MM-DD） |

**自然语言示例：** "1月份跑了哪些步？"

---

### `query_by_distance(min_distance: float, max_distance: Optional[float] = None) -> str`

按距离范围查询跑步记录。

**参数：**

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `min_distance` | `float` | - | 最小距离（公里） |
| `max_distance` | `Optional[float]` | None | 最大距离（公里） |

**自然语言示例：** "我跑过哪些半马？"

---

## 工具调用方式

### 同步调用

```python
from src.agents.tools import RunnerTools

tools = RunnerTools()
result = tools.get_running_stats(year=2024)
print(result)
```

### 通过 Agent 调用

```python
from nanobot_ai import Agent
from src.agents.tools import RunnerTools

tools = RunnerTools()
agent = Agent(
    tools=tools.get_tool_schemas(),
    system_prompt="你是一个专业的跑步数据分析助手"
)
response = agent.chat("我今年跑了多少次？")
```

---

## 工具 Schema 格式

工具使用 OpenAI Function Calling 格式：

```json
{
  "type": "function",
  "function": {
    "name": "get_running_stats",
    "description": "获取跑步统计数据",
    "parameters": {
      "type": "object",
      "properties": {
        "year": {
          "type": "integer",
          "description": "年份"
        }
      }
    }
  }
}
```

---

## 错误处理

所有工具方法返回 JSON 字符串，错误信息包含在返回结果中：

```json
{
  "error": "错误描述",
  "recovery_suggestion": "恢复建议"
}
```

---

## 相关文档

- [AnalyticsEngine API](./analytics_engine.md) - 数据分析引擎
- [StorageManager API](./storage_manager.md) - 存储管理器
- [CLI 用户指南](../guides/cli_usage.md) - 命令行使用指南

---

*文档版本: v0.4.1*
*更新时间: 2026-03-30*
