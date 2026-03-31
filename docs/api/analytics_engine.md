# AnalyticsEngine API 参考

## 概述

`AnalyticsEngine` 是 Nanobot Runner 的核心数据分析引擎，基于 Polars 实现高性能数据分析算法。提供跑步数据的统计、分析和计算功能。

## 类定义

### `AnalyticsEngine`

```python
class AnalyticsEngine:
    def __init__(self, storage_manager: StorageManager) -> None
```

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `storage_manager` | `StorageManager` | StorageManager 实例 |

---

## VDOT 计算

### `calculate_vdot(distance_m: float, time_s: float) -> float`

计算 VDOT 值（跑力值），基于 Powers 公式。距离需 >= 1500m。

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `distance_m` | `float` | 距离（米） |
| `time_s` | `float` | 用时（秒） |

**返回值：** `float` - VDOT 值，保留 2 位小数

**异常：** `ValueError` - 当距离或时间为负数或零时

**示例：**

```python
engine = AnalyticsEngine(storage)
vdot = engine.calculate_vdot(distance_m=5000, time_s=1200)
print(f"VDOT: {vdot}")  # VDOT: 45.23
```

---

## TSS 计算

### `calculate_tss(heart_rate_data: pl.Series, duration_s: float, ftp: int = 200) -> float`

计算训练压力分数（TSS）。

**参数：**

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `heart_rate_data` | `pl.Series` | - | 心率数据序列 |
| `duration_s` | `float` | - | 时长（秒） |
| `ftp` | `int` | 200 | 功能阈值功率 |

**返回值：** `float` - TSS 值

**计算公式：** `TSS = IF² × (时长/3600) × 100`

---

## 跑步摘要统计

### `get_running_summary(start_date: Optional[str] = None, end_date: Optional[str] = None) -> pl.DataFrame`

获取跑步摘要统计信息。

**参数：**

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `start_date` | `Optional[str]` | None | 开始日期，格式：YYYY-MM-DD |
| `end_date` | `Optional[str]` | None | 结束日期，格式：YYYY-MM-DD |

**返回值：** `pl.DataFrame` - 包含 `total_runs`, `total_distance`, `total_duration`, `avg_distance`, `avg_duration`, `max_distance`, `avg_heart_rate` 列

---

## 跑步统计

### `get_running_stats(year: Optional[int] = None) -> Dict[str, Any]`

获取指定年份或全部的跑步统计数据。

**参数：**

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `year` | `Optional[int]` | None | 年份，None 表示全部年份 |

**返回值：** `Dict[str, Any]` - 包含 `total_runs`, `total_distance`, `total_duration`, `avg_heart_rate` 键

---

## VDOT 趋势

### `get_vdot_trend(days: int = 30) -> List[Dict[str, Any]]`

获取最近 N 天的 VDOT 趋势数据。

**返回值：** `List[Dict[str, Any]]` - 每个元素包含 `date`, `vdot`, `distance`, `duration`

---

## 训练负荷

### `get_training_load(days: int = 42) -> Dict[str, Any]`

获取训练负荷（ATL/CTL/TSB）及体能状态评估。

**参数：**

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `days` | `int` | 42 | 分析天数（建议至少 42 天） |

**返回值：** `Dict[str, Any]` - 包含 `atl`, `ctl`, `tsb`, `fitness_status`, `training_advice`, `days_analyzed`, `runs_count`

**计算说明：**
- **ATL**: 7天指数加权移动平均，反映短期疲劳
- **CTL**: 42天指数加权移动平均，反映长期体能
- **TSB**: CTL - ATL，反映当前状态

---

## 训练负荷趋势

### `get_training_load_trend(start_date: Optional[str] = None, end_date: Optional[str] = None, days: Optional[int] = None) -> Dict[str, Any]`

获取训练负荷趋势数据（每日 TSS、ATL、CTL、TSB）。

**返回值：** `Dict[str, Any]` - 包含 `trend_data`（每日数据列表）和 `summary`（汇总信息）

---

## 配速分布

### `get_pace_distribution(year: Optional[int] = None) -> Dict[str, Any]`

获取配速分布统计。

**返回值：** `Dict[str, Any]` - 包含 `zones`（配速区间分布）、`trend`、`total_runs`、`total_distance`

**配速区间：**
- Z1: 恢复区（慢于 6:00/km）
- Z2: 有氧区（5:00-6:00/km）
- Z3: 节奏区（4:30-5:00/km）
- Z4: 阈值区（4:00-4:30/km）
- Z5: 无氧区（快于 4:00/km）

---

## 心率漂移分析

### `analyze_hr_drift(activity_id: str) -> Dict[str, Any]`

分析单次跑步的心率漂移。相关性 < -0.7 判定为漂移。

**返回值：** `Dict[str, Any]` - 包含 `drift_percentage`, `first_half_hr`, `second_half_hr`, `analysis`

---

## ATL/CTL 计算

### `calculate_atl(tss_values: List[float]) -> float`

计算急性训练负荷（ATL）。

### `calculate_ctl(tss_values: List[float]) -> float`

计算慢性训练负荷（CTL）。

---

## 异常处理

| 异常类型 | 说明 | 处理建议 |
|----------|------|----------|
| `ValueError` | 参数无效 | 检查输入参数范围 |
| `RuntimeError` | 计算失败 | 查看错误消息，检查数据 |

---

## 性能优化

使用 Polars LazyFrame 进行查询优化：
- **延迟执行**: 查询计划优化后才执行
- **谓词下推**: 过滤条件尽早应用
- **内存优化**: 大数据集分批处理

**性能提升：** 查询性能提升 ≥ 20%，内存使用减少 ≥ 15%

---

## 相关文档

- [StorageManager API](./storage_manager.md)
- [RunnerTools API](./runner_tools.md)
- [CLI 用户指南](../guides/cli_usage.md)

---

*文档版本: v0.4.1*
*更新时间: 2026-03-30*
