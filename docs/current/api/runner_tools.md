# RunnerTools API 参考

## 概述

`RunnerTools` 是 Nanobot Runner 的 Agent 工具集，封装为 nanobot-ai 可识别的工具格式。提供自然语言交互接口，支持跑步数据的查询和分析。

## 类定义

### `RunnerTools`

Agent 工具集管理类，管理所有可用的工具。

```python
class RunnerTools:
    def __init__(self, storage_manager: Optional[StorageManager] = None) -> None
```

**参数：**

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `storage_manager` | `Optional[StorageManager]` | None | StorageManager 实例 |

**示例：**

```python
from src.agents.tools import RunnerTools

# 使用默认存储管理器
tools = RunnerTools()

# 使用自定义存储管理器
tools = RunnerTools(storage_manager=custom_storage)
```

---

## 工具列表

### `get_running_stats(year: Optional[int] = None) -> str`

获取跑步统计数据。

**参数：**

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `year` | `Optional[int]` | None | 年份，None 表示全部 |

**返回值：**

- `str`: JSON 格式的统计结果

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

**示例：**

```python
result = tools.get_running_stats(year=2024)
print(result)
```

**自然语言示例：**

- "我今年跑了多少次？"
- "查看2024年的跑步统计"
- "总共跑了多少公里？"

---

### `get_recent_runs(limit: int = 10) -> str`

获取最近的跑步记录。

**参数：**

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `limit` | `int` | 10 | 返回记录数量 |

**返回值：**

- `str`: JSON 格式的跑步记录列表

**返回字段：**

```json
[
  {
    "date": "2024-03-15",
    "distance": 5000,
    "duration": 1800,
    "pace": "6'00\"",
    "heart_rate": 145
  }
]
```

**示例：**

```python
result = tools.get_recent_runs(limit=5)
print(result)
```

**自然语言示例：**

- "我最近跑了哪些步？"
- "显示最近5次跑步"
- "上周的跑步记录"

---

### `calculate_vdot_for_run(distance_km: float, time_minutes: float) -> str`

计算单次跑步的 VDOT 值。

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `distance_km` | `float` | 距离（公里） |
| `time_minutes` | `float` | 用时（分钟） |

**返回值：**

- `str`: JSON 格式的 VDOT 计算结果

**返回字段：**

```json
{
  "vdot": 45.23,
  "distance": 5000,
  "duration": 1800,
  "pace": "6'00\"",
  "level": "中等水平"
}
```

**示例：**

```python
result = tools.calculate_vdot_for_run(distance_km=5.0, time_minutes=25.0)
print(result)
```

**自然语言示例：**

- "5公里25分钟的VDOT是多少？"
- "计算这次跑步的跑力值"
- "我的跑步水平如何？"

---

### `get_vdot_trend(days: int = 30) -> str`

获取 VDOT 趋势数据。

**参数：**

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `days` | `int` | 30 | 统计天数 |

**返回值：**

- `str`: JSON 格式的 VDOT 趋势数据

**返回字段：**

```json
[
  {
    "date": "2024-03-01",
    "vdot": 43.5,
    "distance": 5000,
    "duration": 1850
  },
  {
    "date": "2024-03-15",
    "vdot": 45.2,
    "distance": 5000,
    "duration": 1800
  }
]
```

**示例：**

```python
result = tools.get_vdot_trend(days=30)
print(result)
```

**自然语言示例：**

- "我的VDOT趋势如何？"
- "最近一个月的跑力变化"
- "查看跑步能力提升情况"

---

### `get_hr_drift_analysis(activity_id: Optional[str] = None) -> str`

获取心率漂移分析。

**参数：**

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `activity_id` | `Optional[str]` | None | 活动ID，None 表示最近一次 |

**返回值：**

- `str`: JSON 格式的心率漂移分析结果

**返回字段：**

```json
{
  "drift_percentage": 5.2,
  "first_half_hr": 140,
  "second_half_hr": 147,
  "analysis": "心率漂移正常，有氧能力良好",
  "status": "good"
}
```

**示例：**

```python
result = tools.get_hr_drift_analysis(activity_id="run_001")
print(result)
```

**自然语言示例：**

- "分析这次跑步的心率漂移"
- "我的心率控制如何？"
- "有氧能力评估"

---

### `get_training_load(days: int = 42) -> str`

获取训练负荷数据。

**参数：**

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `days` | `int` | 42 | 分析天数 |

**返回值：**

- `str`: JSON 格式的训练负荷数据

**返回字段：**

```json
{
  "atl": 65.5,
  "ctl": 58.2,
  "tsb": -7.3,
  "fitness_status": "疲劳积累",
  "training_advice": "建议适当降低训练强度，增加恢复时间",
  "days_analyzed": 42,
  "runs_count": 28
}
```

**示例：**

```python
result = tools.get_training_load(days=42)
print(result)
```

**自然语言示例：**

- "我的训练负荷如何？"
- "当前体能状态评估"
- "是否需要休息？"

---

### `get_training_load_trend(days: int = 30) -> str`

获取训练负荷趋势。

**参数：**

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `days` | `int` | 30 | 统计天数 |

**返回值：**

- `str`: JSON 格式的训练负荷趋势数据

**返回字段：**

```json
{
  "trend_data": [
    {
      "date": "2024-03-01",
      "tss": 85,
      "atl": 55.2,
      "ctl": 52.1,
      "tsb": -3.1,
      "status": "正常训练"
    }
  ],
  "summary": {
    "current_atl": 65.5,
    "current_ctl": 58.2,
    "current_tsb": -7.3,
    "status": "疲劳积累",
    "recommendation": "建议适当降低训练强度"
  }
}
```

**示例：**

```python
result = tools.get_training_load_trend(days=30)
print(result)
```

**自然语言示例：**

- "最近一个月的训练趋势"
- "ATL和CTL变化情况"
- "训练压力平衡分析"

---

### `query_by_date_range(start_date: str, end_date: str) -> str`

按日期范围查询跑步记录。

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `start_date` | `str` | 开始日期（YYYY-MM-DD） |
| `end_date` | `str` | 结束日期（YYYY-MM-DD） |

**返回值：**

- `str`: JSON 格式的跑步记录列表

**示例：**

```python
result = tools.query_by_date_range("2024-01-01", "2024-01-31")
print(result)
```

**自然语言示例：**

- "1月份跑了哪些步？"
- "查询2024年第一季度的记录"
- "上周的跑步情况"

---

### `query_by_distance(min_distance: float, max_distance: Optional[float] = None) -> str`

按距离范围查询跑步记录。

**参数：**

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `min_distance` | `float` | - | 最小距离（公里） |
| `max_distance` | `Optional[float]` | None | 最大距离（公里） |

**返回值：**

- `str`: JSON 格式的跑步记录列表

**示例：**

```python
# 查询10公里以上的跑步
result = tools.query_by_distance(min_distance=10.0)

# 查询5-10公里的跑步
result = tools.query_by_distance(min_distance=5.0, max_distance=10.0)
```

**自然语言示例：**

- "我跑过哪些半马？"
- "查询10公里以上的记录"
- "5-10公里的跑步有哪些？"

---

## 工具调用方式

### 同步调用

```python
from src.agents.tools import RunnerTools

tools = RunnerTools()

# 直接调用工具方法
result = tools.get_running_stats(year=2024)
print(result)
```

### 异步调用

```python
import asyncio
from src.agents.tools import RunnerTools

async def main():
    tools = RunnerTools()
    
    # 异步调用
    result = await tools.get_running_stats_async(year=2024)
    print(result)

asyncio.run(main())
```

### 通过 Agent 调用

```python
from nanobot_ai import Agent
from src.agents.tools import RunnerTools

# 创建工具集
tools = RunnerTools()

# 创建 Agent
agent = Agent(
    tools=tools.get_tool_schemas(),
    system_prompt="你是一个专业的跑步数据分析助手"
)

# Agent 自动选择和调用工具
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

**常见错误：**

| 错误类型 | 说明 | 处理建议 |
|----------|------|----------|
| `NO_DATA` | 无数据 | 先导入跑步数据 |
| `INVALID_PARAM` | 参数无效 | 检查参数格式和范围 |
| `CALC_ERROR` | 计算错误 | 检查数据完整性 |

---

## 性能说明

- **查询优化**: 使用 Polars LazyFrame 延迟执行
- **缓存机制**: 热点数据自动缓存
- **批量处理**: 大数据集分批返回

---

## 相关文档

- [AnalyticsEngine API](./analytics_engine.md) - 数据分析引擎
- [StorageManager API](./storage_manager.md) - 存储管理器
- [Agent 使用指南](../guides/agent_usage.md) - Agent 交互指南

---

*文档版本: v0.3.0*
*更新时间: 2026-03-17*
