# AnalyticsEngine API 参考

## 概述

`AnalyticsEngine` 是 Nanobot Runner 的核心数据分析引擎，基于 Polars 实现高性能数据分析算法。提供跑步数据的统计、分析和计算功能。

## 类定义

### `AnalyticsEngine`

数据分析引擎类，封装所有数据分析算法。

```python
class AnalyticsEngine:
    def __init__(self, storage_manager: StorageManager) -> None
```

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `storage_manager` | `StorageManager` | StorageManager 实例，用于数据存取 |

---

## VDOT 计算

### `calculate_vdot(distance_m: float, time_s: float) -> float`

计算 VDOT 值（跑力值），基于 Powers 公式。

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `distance_m` | `float` | 距离（米） |
| `time_s` | `float` | 用时（秒） |

**返回值：**

- `float`: VDOT 值，保留 2 位小数

**异常：**

- `ValueError`: 当距离或时间为负数或零时

**示例：**

```python
engine = AnalyticsEngine(storage)
vdot = engine.calculate_vdot(distance_m=5000, time_s=1200)  # 5公里，20分钟
print(f"VDOT: {vdot}")  # VDOT: 45.23
```

**公式说明：**

```
VDOT = (0.0001 × distance^1.06 × 24.6) / time^0.43
```

---

## TSS 计算

### `calculate_tss(heart_rate_data: pl.Series, duration_s: float, ftp: int = 200) -> float`

计算训练压力分数（TSS - Training Stress Score）。

**参数：**

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `heart_rate_data` | `pl.Series` | - | 心率数据序列 |
| `duration_s` | `float` | - | 时长（秒） |
| `ftp` | `int` | 200 | 功能阈值功率 |

**返回值：**

- `float`: TSS 值，保留 2 位小数

**异常：**

- `ValueError`: 当心率数据为空或时长无效时

**示例：**

```python
import polars as pl

hr_data = pl.Series([140, 145, 150, 148, 152])
tss = engine.calculate_tss(hr_data, duration_s=3600)  # 1小时训练
print(f"TSS: {tss}")
```

**计算公式：**

```
Intensity Factor = 平均心率 / 180
TSS = IF² × (时长/3600) × 100
```

---

## 跑步摘要统计

### `get_running_summary(start_date: Optional[str] = None, end_date: Optional[str] = None) -> pl.DataFrame`

获取跑步摘要统计信息。

**参数：**

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `start_date` | `Optional[str]` | None | 开始日期，格式：YYYY-MM-DD |
| `end_date` | `Optional[str]` | None | 结束日期，格式：YYYY-MM-DD |

**返回值：**

- `pl.DataFrame`: 包含以下列的 DataFrame：
  - `total_runs`: 总次数
  - `total_distance`: 总距离（米）
  - `total_duration`: 总时长（秒）
  - `avg_distance`: 平均距离（米）
  - `avg_duration`: 平均时长（秒）
  - `max_distance`: 最大距离（米）
  - `avg_heart_rate`: 平均心率

**示例：**

```python
# 获取所有时间的摘要
summary = engine.get_running_summary()

# 获取特定日期范围的摘要
summary = engine.get_running_summary(
    start_date="2024-01-01",
    end_date="2024-12-31"
)

print(f"总跑步次数: {summary['total_runs'][0]}")
print(f"总距离: {summary['total_distance'][0] / 1000:.2f} km")
```

---

## 跑步统计

### `get_running_stats(year: Optional[int] = None) -> Dict[str, Any]`

获取指定年份或全部的跑步统计数据。

**参数：**

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `year` | `Optional[int]` | None | 年份，如 2024。None 表示全部年份 |

**返回值：**

- `Dict[str, Any]`: 包含以下键的字典：
  - `total_runs`: 总次数
  - `total_distance`: 总距离（米）
  - `total_duration`: 总时长（秒）
  - `avg_heart_rate`: 平均心率

**示例：**

```python
# 获取2024年统计
stats_2024 = engine.get_running_stats(year=2024)

# 获取全部统计
all_stats = engine.get_running_stats()

print(f"总次数: {all_stats['total_runs']}")
print(f"总距离: {all_stats['total_distance'] / 1000:.1f} km")
print(f"总时长: {all_stats['total_duration'] / 3600:.1f} 小时")
```

---

## VDOT 趋势

### `get_vdot_trend(days: int = 30) -> List[Dict[str, Any]]`

获取最近 N 天的 VDOT 趋势数据。

**参数：**

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `days` | `int` | 30 | 统计天数 |

**返回值：**

- `List[Dict[str, Any]]`: VDOT 趋势数据列表，每个元素包含：
  - `date`: 日期（YYYY-MM-DD）
  - `vdot`: VDOT 值
  - `distance`: 距离（米）
  - `duration`: 时长（秒）

**示例：**

```python
trend = engine.get_vdot_trend(days=30)

for record in trend:
    print(f"{record['date']}: VDOT={record['vdot']}, "
          f"距离={record['distance']/1000:.1f}km")
```

---

## 训练负荷

### `get_training_load(days: int = 42) -> Dict[str, Any]`

获取训练负荷（ATL/CTL/TSB）及体能状态评估。

**参数：**

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `days` | `int` | 42 | 分析天数（建议至少 42 天以获得准确的 CTL） |

**返回值：**

- `Dict[str, Any]`: 训练负荷数据，包含：
  - `atl`: 急性训练负荷（7天 EWMA）
  - `ctl`: 慢性训练负荷（42天 EWMA）
  - `tsb`: 训练压力平衡（CTL - ATL）
  - `fitness_status`: 体能状态评估
  - `training_advice`: 训练建议
  - `days_analyzed`: 分析天数
  - `runs_count`: 跑步次数
  - `message`: 提示信息（数据不足时）

**计算说明：**

- **ATL (Acute Training Load)**: 7天指数加权移动平均，反映短期疲劳
- **CTL (Chronic Training Load)**: 42天指数加权移动平均，反映长期体能
- **TSB (Training Stress Balance)**: CTL - ATL，反映当前状态

**示例：**

```python
load = engine.get_training_load(days=42)

print(f"ATL: {load['atl']:.1f}")
print(f"CTL: {load['ctl']:.1f}")
print(f"TSB: {load['tsb']:.1f}")
print(f"状态: {load['fitness_status']}")
print(f"建议: {load['training_advice']}")
```

---

## 训练负荷趋势

### `get_training_load_trend(start_date: Optional[str] = None, end_date: Optional[str] = None, days: Optional[int] = None) -> Dict[str, Any]`

获取训练负荷趋势数据（每日 TSS、ATL、CTL、TSB）。

**参数：**

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `start_date` | `Optional[str]` | None | 开始日期（YYYY-MM-DD） |
| `end_date` | `Optional[str]` | None | 结束日期（YYYY-MM-DD） |
| `days` | `Optional[int]` | None | 最近 N 天，优先级高于日期范围 |

**返回值：**

- `Dict[str, Any]`: 包含：
  - `trend_data`: 每日训练负荷数据列表
    - `date`: 日期
    - `tss`: 当日 TSS 总和
    - `atl`: 急性训练负荷
    - `ctl`: 慢性训练负荷
    - `tsb`: 训练压力平衡
    - `status`: 体能状态
  - `summary`: 汇总信息
    - `current_atl`: 当前 ATL
    - `current_ctl`: 当前 CTL
    - `current_tsb`: 当前 TSB
    - `status`: 当前体能状态
    - `recommendation`: 训练建议

**示例：**

```python
# 获取最近30天趋势
trend = engine.get_training_load_trend(days=30)

# 打印每日数据
for day in trend['trend_data']:
    print(f"{day['date']}: TSS={day['tss']:.0f}, "
          f"ATL={day['atl']:.1f}, CTL={day['ctl']:.1f}, "
          f"TSB={day['tsb']:.1f}")

# 打印汇总
summary = trend['summary']
print(f"当前状态: {summary['status']}")
print(f"建议: {summary['recommendation']}")
```

---

## 配速分布

### `get_pace_distribution(year: Optional[int] = None) -> Dict[str, Any]`

获取配速分布统计。

**参数：**

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `year` | `Optional[int]` | None | 年份筛选 |

**返回值：**

- `Dict[str, Any]`: 配速分布数据，包含：
  - `zones`: 配速区间分布
    - `Z1`: 恢复区（慢于 6:00/km）
    - `Z2`: 有氧区（5:00-6:00/km）
    - `Z3`: 节奏区（4:30-5:00/km）
    - `Z4`: 阈值区（4:00-4:30/km）
    - `Z5`: 无氧区（快于 4:00/km）
  - `trend`: 配速趋势数据
  - `total_runs`: 总跑步次数
  - `total_distance`: 总距离

**示例：**

```python
distribution = engine.get_pace_distribution(year=2024)

print("配速分布:")
for zone, data in distribution['zones'].items():
    print(f"  {zone}: {data['count']}次, {data['percentage']:.1f}%")

print(f"\n总次数: {distribution['total_runs']}")
print(f"总距离: {distribution['total_distance'] / 1000:.1f} km")
```

---

## 心率漂移分析

### `analyze_hr_drift(activity_id: str) -> Dict[str, Any]`

分析单次跑步的心率漂移。

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `activity_id` | `str` | 活动 ID |

**返回值：**

- `Dict[str, Any]`: 心率漂移分析结果，包含：
  - `drift_percentage`: 心率漂移百分比
  - `first_half_hr`: 前半程平均心率
  - `second_half_hr`: 后半程平均心率
  - `analysis`: 分析结论

**示例：**

```python
analysis = engine.analyze_hr_drift("activity_001")

print(f"心率漂移: {analysis['drift_percentage']:.1f}%")
print(f"前半程心率: {analysis['first_half_hr']:.0f} bpm")
print(f"后半程心率: {analysis['second_half_hr']:.0f} bpm")
print(f"分析: {analysis['analysis']}")
```

---

## ATL/CTL 计算

### `calculate_atl(tss_values: List[float]) -> float`

计算急性训练负荷（ATL）。

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `tss_values` | `List[float]` | TSS 值列表 |

**返回值：**

- `float`: ATL 值

**示例：**

```python
tss_history = [50, 60, 55, 70, 65, 80, 75]  # 最近7天
atl = engine.calculate_atl(tss_history)
print(f"ATL: {atl:.1f}")
```

### `calculate_ctl(tss_values: List[float]) -> float`

计算慢性训练负荷（CTL）。

**参数：**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `tss_values` | `List[float]` | TSS 值列表 |

**返回值：**

- `float`: CTL 值

**示例：**

```python
tss_history = [50] * 42  # 42天稳定训练
ctl = engine.calculate_ctl(tss_history)
print(f"CTL: {ctl:.1f}")
```

---

## 异常处理

所有方法都可能抛出以下异常：

| 异常类型 | 说明 | 处理建议 |
|----------|------|----------|
| `ValueError` | 参数无效 | 检查输入参数范围 |
| `RuntimeError` | 计算失败 | 查看错误消息，检查数据 |

---

## 性能优化

从 v0.3.0 开始，`AnalyticsEngine` 使用 Polars LazyFrame 进行查询优化：

- **延迟执行**: 查询计划优化后才执行
- **谓词下推**: 过滤条件尽早应用
- **内存优化**: 大数据集分批处理

**性能提升指标：**

- 查询性能提升 ≥ 20%
- 内存使用减少 ≥ 15%

---

## 相关文档

- [StorageManager API](./storage_manager.md) - 存储管理器接口
- [RunnerTools API](./runner_tools.md) - Agent 工具集
- [CLI 用户指南](../guides/cli_usage.md) - 命令行使用指南

---

*文档版本: v0.3.0*
*更新时间: 2026-03-17*
