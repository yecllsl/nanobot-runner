# Phase C 基线测量脚本设计

> **设计日期**: 2026-05-19
> **基线版本**: v0.22.0
> **执行时机**: v0.22发布后、v0.23启动前

## 1. 背景与目标

Phase C（v0.23-v0.25）的核心目标是让系统从用户反馈和训练结果中持续学习。为衡量进化效果，需要在v0.22结束时建立基线指标。

**目标**：开发独立Python脚本，对现有数据进行回溯预测和基线测量，生成《Phase C 基线测量报告》。

## 2. 整体架构

### 数据流

```
历史训练数据(Parquet)
       │
       ▼
┌──────────────────────────────────┐
│ 阶段1: generate_historical_      │
│        predictions.py            │
│                                  │
│  遍历历史时间点 → 调用预测引擎   │
│  → 写入 PredictionRecord         │
│       (predictions.parquet)      │
└──────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────┐
│ 阶段2: measure_baseline.py       │
│                                  │
│  读取 PredictionRecord           │
│  读取 InjuryReport               │
│  计算5项指标                     │
│  → 输出基线测量报告(Markdown)    │
└──────────────────────────────────┘
```

### 关键设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 脚本形式 | 独立Python脚本 | 不集成到CLI，手动执行 |
| 历史预测时间粒度 | 每周一个预测点 | 平衡计算量和数据密度 |
| 预测回溯范围 | 最近6个月 | 覆盖足够数据，避免过旧数据干扰 |
| 实际值回填 | 利用现有 `check_and_update_actual()` | 复用已有机制 |
| 报告输出格式 | Markdown | 与项目文档风格一致 |
| 待补充指标 | 标注为"待v0.23补充" | 满意度和采纳率无数据源 |

## 3. 阶段1：历史预测生成脚本

### 文件：`scripts/generate_historical_predictions.py`

### 核心逻辑

1. 初始化应用上下文（`get_context()`）
2. 获取历史训练数据时间范围
3. 按周生成时间点（最近6个月，约26个点）
4. 对每个时间点：
   - VDOT预测：调用 `vdot_predictor.predict(days=7)`
   - 比赛成绩预测：调用 `race_predictor.predict(distance_km=42.195)`
   - 伤病风险预测：调用 `injury_predictor.predict(days=21)`
   - 将预测结果转为 `PredictionRecord` 并持久化
5. 调用 `model_manager.check_and_update_actual()` 回填实际值
6. 输出统计摘要

### 命令行接口

```bash
# 生成最近6个月的历史预测（默认）
uv run python scripts/generate_historical_predictions.py

# 指定时间范围
uv run python scripts/generate_historical_predictions.py --start 2025-11-01 --end 2026-05-18

# 只生成特定类型
uv run python scripts/generate_historical_predictions.py --type vdot
uv run python scripts/generate_historical_predictions.py --type race
uv run python scripts/generate_historical_predictions.py --type injury

# 清除已有预测记录并重新生成
uv run python scripts/generate_historical_predictions.py --reset
```

### PredictionRecord 映射

| 预测类型 | prediction_type | predicted_value | predicted_unit | actual_value来源 |
|----------|----------------|-----------------|----------------|------------------|
| VDOT预测 | `vdot_trend` | 预测VDOT值 | `vdot` | 7天后实际VDOT |
| 全马预测 | `race_marathon` | 预测成绩(秒) | `seconds` | 比赛实际成绩 |
| 伤病预测 | `injury_risk` | 风险分数(0-100) | `score` | 3周内是否实际伤病 |

### 关键注意点

- 使用 `get_context()` 获取应用上下文，不直接实例化组件
- VDOT实际值通过 `check_and_update_actual()` 自动回填
- 全马预测实际值需要用户有比赛记录，可能为空
- 伤病预测实际值需要对比 `InjuryReport` 时间戳

## 4. 阶段2：基线测量脚本

### 文件：`scripts/measure_baseline.py`

### 核心逻辑

1. 初始化应用上下文
2. 读取 `PredictionRecord` 数据
3. 读取 `InjuryReport` 数据
4. 计算5项指标（3项可计算，2项标注待补充）
5. 生成《Phase C 基线测量报告》Markdown
6. 输出到 `docs/product/Phase_C_基线测量报告.md`

### 5项指标计算逻辑

| 指标 | 计算方式 | 数据来源 |
|------|---------|---------|
| VDOT预测误差(MAE) | 筛选 `prediction_type='vdot_trend'` 且 `actual_value` 非空，计算 `abs(predicted - actual) / actual` 均值 | `predictions.parquet` |
| 全马成绩预测误差 | 筛选 `prediction_type='race_marathon'` 且 `actual_value` 非空，计算 `abs(predicted - actual)` 均值 | `predictions.parquet` |
| 用户主观满意度 | **标注：待v0.23实现数据收集机制后补充** | 无数据源 |
| 系统推荐采纳率 | **标注：待v0.23实现DecisionLog后补充** | 无数据源 |
| 伤病预警召回率 | 对比 `InjuryRiskPrediction`(score≥60为预警) 与 `InjuryReport` 时间戳，3周内预警命中 / 实际伤病事件总数 | `predictions.parquet` + `injury_labels/*.json` |

### 伤病预警召回率计算细节

```
对每条 InjuryReport（实际伤病事件）：
  检查伤病日期前21天内是否存在 InjuryRiskPrediction 且 risk_score ≥ 60
  如果存在 → 命中
  如果不存在 → 漏报

召回率 = 命中数 / 实际伤病事件总数
误报率 = 预警但未发生伤病数 / 总预警数
```

### 命令行接口

```bash
# 执行基线测量并生成报告
uv run python scripts/measure_baseline.py

# 指定报告输出路径
uv run python scripts/measure_baseline.py --output docs/product/Phase_C_基线测量报告.md

# 只显示指标，不生成报告文件
uv run python scripts/measure_baseline.py --dry-run
```

### 报告输出格式

```markdown
# Phase C 基线测量报告

> 测量时间: YYYY-MM-DD
> 数据范围: YYYY-MM-DD ~ YYYY-MM-DD
> 基线版本: v0.22.0

## 基线指标

| 指标 | 基线值 | 样本量 | 状态 |
|------|--------|--------|------|
| VDOT预测误差(MAE) | X.X% | N | ✅ 已测量 |
| 全马成绩预测误差 | N秒 | N | ✅ 已测量 |
| 用户主观满意度 | — | 0 | ⏳ 待v0.23补充 |
| 系统推荐采纳率 | — | 0 | ⏳ 待v0.23补充 |
| 伤病预警召回率 | X% | N | ✅ 已测量 |
| 伤病预警误报率 | X% | N | ✅ 已测量 |

## 版本迭代目标

| 指标 | 基线值 | v0.23目标 | v0.24目标 | v0.25目标 |
|------|--------|-----------|-----------|-----------|
| VDOT预测误差(MAE) | X.X% | 下降≥5% | 下降≥5% | 下降≥5% |
| 全马成绩预测误差 | N秒 | 下降≥5% | 下降≥5% | 下降≥5% |
| 用户主观满意度 | — | ≥4.0 | +0.1 | +0.1 |
| 系统推荐采纳率 | — | >60% | +3% | +3% |
| 伤病预警召回率 | X% | ≥75% | ≥75% | ≥75% |
| 伤病预警误报率 | X% | -3% | -3% | -3% |

## 数据质量说明
- 预测记录总数: N
- 实际值回填率: X%
- 伤病报告总数: N
```

## 5. 依赖与约束

### 现有依赖（无需新增）

- `src.core.base.context.get_context()` — 应用上下文
- `src.core.prediction.model_manager.ModelManager` — 预测记录存储/查询
- `src.core.prediction.prediction_engine.PredictionEngine` — 预测引擎
- `src.core.prediction.models.PredictionRecord` — 预测记录数据模型
- `src.core.prediction.injury_predictor.InjuryPredictor` — 伤病预测器

### 数据存储位置

| 数据 | 路径 |
|------|------|
| 预测记录 | `~/.nanobot-runner/models/predictions/predictions_{year}.parquet` |
| 伤病报告 | `~/.nanobot-runner/injury_labels/{injury_id}.json` |
| 基线报告 | `docs/product/Phase_C_基线测量报告.md` |

### 约束

- 脚本必须在项目根目录下通过 `uv run python scripts/xxx.py` 执行
- 不修改任何现有代码，仅新增脚本文件
- 不新增任何依赖
