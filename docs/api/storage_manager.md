# StorageManager API 参考

## 概述

`StorageManager` 是 Nanobot Runner 的 Parquet 存储管理器，负责跑步数据的持久化存储。提供高性能的数据读写、查询和管理功能。

## 类定义

### `StorageManager`

```python
class StorageManager:
    def __init__(self, data_dir: Optional[Path] = None) -> None
```

**参数：**

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `data_dir` | `Optional[Path]` | `~/.nanobot-runner/data` | 数据目录路径 |

**异常：** `StorageError` - 当无法创建数据目录时

---

## 数据保存

### `save_to_parquet(dataframe: pl.DataFrame, year: int, allow_empty: bool = False) -> bool`

将 DataFrame 保存到 Parquet 文件。

**参数：**

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `dataframe` | `pl.DataFrame` | - | 要保存的数据 |
| `year` | `int` | - | 年份（2000-2100） |
| `allow_empty` | `bool` | False | 是否允许保存空数据 |

**返回值：** `bool` - 保存成功返回 True

**异常：** `ValidationError` - 数据为空或年份无效；`StorageError` - 保存失败

**文件命名规则：** `activities_{year}.parquet`

---

### `save_activities(dataframe: pl.DataFrame, year: int = None) -> dict`

保存活动数据，自动推断年份。

**参数：**

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `dataframe` | `pl.DataFrame` | - | 活动数据 |
| `year` | `int` | None | 年份，None 时自动推断 |

**返回值：** `dict` - 包含 `success`, `records`, `year`, `file`

---

## 数据读取

### `read_parquet(years: Optional[List[int]] = None) -> pl.LazyFrame`

读取 Parquet 数据，返回 LazyFrame。

**参数：**

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `years` | `Optional[List[int]]` | None | 年份列表，None 表示所有年份 |

**返回值：** `pl.LazyFrame` - 延迟执行的 DataFrame

**性能说明：** 使用 LazyFrame 实现延迟执行，支持谓词下推优化

---

### `read_activities(year: Optional[int] = None) -> pl.DataFrame`

读取活动数据（向后兼容方法）。

**参数：**

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `year` | `Optional[int]` | None | 年份筛选 |

**返回值：** `pl.DataFrame` - 活动数据

---

## 数据查询

### `query_activities(filters: Dict[str, Any]) -> pl.DataFrame`

根据条件查询活动数据。

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `filters` | `Dict[str, Any]` | 查询条件 |

**支持的过滤条件：**
- `start_date`: 开始日期（datetime）
- `end_date`: 结束日期（datetime）
- `min_distance`: 最小距离（米）
- `max_distance`: 最大距离（米）
- `min_duration`: 最小时长（秒）
- `max_duration`: 最大时长（秒）

**返回值：** `pl.DataFrame` - 符合条件的活动数据

---

## 数据管理

### `get_available_years() -> List[int]`

获取可用的年份列表。

**返回值：** `List[int]` - 有数据的年份列表

---

### `delete_activities(activity_ids: List[str]) -> int`

删除指定的活动记录。

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `activity_ids` | `List[str]` | 要删除的活动 ID 列表 |

**返回值：** `int` - 删除的记录数

---

### `compact_year(year: int) -> bool`

压缩指定年份的数据文件（去除重复和碎片）。

**返回值：** `bool` - 压缩成功返回 True

---

## 辅助方法

### `get_data_dir() -> Path`

获取数据目录路径。

**返回值：** `Path` - 数据目录路径

---

### `get_file_size(year: int) -> int`

获取指定年份数据文件的大小（字节）。

**返回值：** `int` - 文件大小（字节），文件不存在返回 0

---

## 数据格式

### 标准活动数据字段

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `activity_id` | `str` | 活动唯一标识（必填） |
| `timestamp` | `datetime` | 活动时间戳（必填） |
| `filename` | `str` | 原始文件名（必填） |
| `source_file` | `str` | 源文件路径（必填） |
| `total_distance` | `float` | 总距离（米）（必填） |
| `total_timer_time` | `int` | 总时长（秒）（必填） |
| `avg_heart_rate` | `float` | 平均心率 |
| `max_heart_rate` | `float` | 最大心率 |
| `avg_speed` | `float` | 平均速度（米/秒） |
| `max_speed` | `float` | 最大速度（米/秒） |
| `total_calories` | `float` | 总消耗卡路里 |

---

## 异常处理

| 异常类型 | 说明 | 处理建议 |
|----------|------|----------|
| `StorageError` | 存储操作失败 | 检查磁盘空间和权限 |
| `ValidationError` | 数据验证失败 | 检查数据格式和范围 |
| `FileNotFoundError` | 文件不存在 | 确认年份和数据存在 |

---

## 性能优化

### 写入优化
- **批量写入**: 一次性写入多条记录
- **压缩**: 使用 Snappy 压缩算法
- **分区**: 按年份分区存储

### 读取优化
- **LazyFrame**: 延迟执行，优化查询计划
- **列裁剪**: 只读取需要的列
- **谓词下推**: 过滤条件下推到存储层

### 存储优化
- **去重**: 基于 activity_id 自动去重
- **压缩比**: 典型压缩比 3:1 到 5:1

---

## 相关文档

- [AnalyticsEngine API](./analytics_engine.md) - 数据分析引擎
- [RunnerTools API](./runner_tools.md) - Agent 工具集
- [CLI 用户指南](../guides/cli_usage.md) - 命令行使用指南

---

*文档版本: v0.4.1*
*更新时间: 2026-03-30*
