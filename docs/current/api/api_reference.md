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

Nanobot Runner 使用 `~/.nanobot-runner` 作为 nanobot workspace，遵循 nanobot-ai 标准结构：

```
~/.nanobot-runner/
├── data/                    # 业务数据存储（本项目扩展）
│   ├── activities_*.parquet # 运动数据（按年分片）
│   ├── profile.json         # 结构化画像数据
│   ├── plans/               # 训练计划存储
│   └── index.json           # 去重索引
├── memory/                  # 记忆系统（nanobot标准）
│   ├── MEMORY.md            # 长期记忆/用户画像
│   └── HISTORY.md           # 事件日志
├── sessions/                # 会话历史（nanobot标准）
├── skills/                  # 技能扩展（nanobot标准）
├── AGENTS.md                # Agent行为准则
├── SOUL.md                  # 人格设定
├── USER.md                  # 用户画像
├── HEARTBEAT.md             # 定时任务
└── config.json              # 应用配置
```

### 自动初始化机制

> ⚠️ **重要**：workspace 目录结构由 nanobot-ai 框架自动初始化，无需自定义实现。

当启动应用时，nanobot-ai 框架会自动检测并创建缺失的标准结构：

| 自动创建的文件/目录 | 说明 |
|-------------------|------|
| `AGENTS.md` | Agent 行为准则模板 |
| `SOUL.md` | 人格、价值观、语气风格 |
| `USER.md` | 用户画像模板 |
| `memory/MEMORY.md` | 长期记忆初始文件 |
| `memory/HISTORY.md` | 事件日志初始文件 |
| `skills/` | 技能目录 |

**应用需自行创建的目录**：`data/`、`data/plans/`、`logs/`

**设计原则**：完全复用 nanobot 的初始化逻辑，避免重复实现。

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

**返回:**
- `pl.DataFrame`: 包含统计信息的 DataFrame

**示例:**
```python
summary = engine.get_running_summary(start_date="2024-01-01", end_date="2024-12-31")
print(f"总跑步次数: {summary.height}")
```

---

##### `get_running_stats(year=None) -> Dict[str, Any]`

获取年度或总体跑步统计。

**参数:**
- `year` (int, optional): 年份，如 2024。为 None 时返回总体统计

**返回:**
- `Dict[str, Any]`: 统计信息字典
  - `total_runs`: 总跑步次数
  - `total_distance`: 总距离（米）
  - `total_duration`: 总时长（秒）
  - `avg_heart_rate`: 平均心率

**示例:**
```python
stats = engine.get_running_stats(year=2024)
print(f"2024年跑步 {stats['total_runs']} 次，总计 {stats['total_distance']/1000:.1f} km")
```

---

##### `calculate_vdot(distance_m, duration_s) -> float`

计算 VDOT 值（基于 Jack Daniels 公式）。

**参数:**
- `distance_m` (float): 距离（米）
- `duration_s` (float): 时长（秒）

**返回:**
- `float`: VDOT 值

**示例:**
```python
vdot = engine.calculate_vdot(distance_m=5000, duration_s=1200)
print(f"VDOT: {vdot:.1f}")
```

---

##### `get_vdot_trend(days=30) -> List[Dict[str, Any]]`

获取 VDOT 趋势数据。

**参数:**
- `days` (int): 统计天数，默认 30

**返回:**
- `List[Dict[str, Any]]`: VDOT 趋势数据列表
  - `date`: 日期
  - `vdot`: VDOT 值
  - `distance`: 距离
  - `duration`: 时长

---

##### `get_training_load(days=42) -> Dict[str, Any]`

获取训练负荷（ATL/CTL/TSB）及体能状态评估。

**参数:**
- `days` (int): 分析天数，建议至少 42 天，默认 42

**返回:**
- `Dict[str, Any]`: 训练负荷数据
  - `atl`: 急性训练负荷（7天 EWMA）
  - `ctl`: 慢性训练负荷（42天 EWMA）
  - `tsb`: 训练压力平衡（CTL - ATL）
  - `fitness_status`: 体能状态评估
  - `training_advice`: 训练建议
  - `days_analyzed`: 分析天数
  - `runs_count`: 跑步次数
  - `message`: 提示信息（数据不足时）

---

##### `get_training_load_trend(start_date=None, end_date=None, days=None) -> Dict[str, Any]`

获取训练负荷趋势数据（每日 TSS、ATL、CTL、TSB）。

**参数:**
- `start_date` (str, optional): 开始日期，格式 "YYYY-MM-DD"
- `end_date` (str, optional): 结束日期，格式 "YYYY-MM-DD"
- `days` (int, optional): 最近 N 天，优先级高于 start_date/end_date

**返回:**
- `Dict[str, Any]`: 训练负荷趋势数据
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

---

##### `get_pace_distribution(year=None) -> Dict[str, Any]`

获取配速分布统计。

**参数:**
- `year` (int, optional): 年份筛选

**返回:**
- `Dict[str, Any]`: 配速分布数据
  - `zones`: 配速区间统计
  - `trend`: 配速趋势
  - `total_runs`: 总跑步次数
  - `total_distance`: 总距离

---

##### `analyze_hr_drift(records) -> Dict[str, Any]`

分析心率漂移。

**参数:**
- `records` (List[Dict]): 跑步记录列表

**返回:**
- `Dict[str, Any]`: 心率漂移分析结果
  - `drift_percentage`: 漂移百分比
  - `correlation`: 相关性系数
  - `is_valid`: 是否有效
  - `message`: 分析信息

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

**返回:**
- `pl.LazyFrame`: 延迟执行的 DataFrame

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

**返回:**
- `Dict[str, Any]`: 解析后的活动数据

---

##### `parse_directory(directory) -> List[Dict[str, Any]]`

解析目录中的所有 FIT 文件。

**参数:**
- `directory` (str): 目录路径

**返回:**
- `List[Dict[str, Any]]`: 活动数据列表

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

##### `import