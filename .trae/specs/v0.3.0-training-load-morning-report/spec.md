# v0.3.0 迭代训练负荷与晨报功能 Spec

## Why

T001 已完成，现在需要继续实现训练负荷计算（ATL/CTL/TSB）、训练负荷趋势分析和晨报内容生成功能，为用户提供科学化的体能状态评估和每日训练建议。

## What Changes

- **T002**: 实现 ATL/CTL/TSB 计算 - 新增/完善 `get_training_load()` 方法
- **T003**: 实现训练负荷趋势分析 - 新增 `get_training_load_trend()` 方法
- **T004**: 实现晨报内容生成 - 新增 `generate_daily_report()` 方法

## Impact

- Affected specs: `src/core/analytics.py` 扩展
- Affected code: 
  - `src/core/analytics.py` - 新增/完善训练负荷方法
  - `src/notify/feishu.py` - 晨报推送支持
  - `tests/unit/test_analytics.py` - 新增单元测试

## ADDED Requirements

### Requirement: ATL/CTL/TSB 计算 (T002)

系统 SHALL 提供训练负荷计算功能，使用指数加权移动平均 (EWMA) 算法计算 ATL、CTL、TSB。

#### Scenario: 正常训练负荷计算

- **WHEN** 用户请求训练负荷分析
- **THEN** 系统返回 ATL（急性负荷）、CTL（慢性负荷）、TSB（训练压力平衡）

#### Scenario: 数据不足

- **WHEN** 训练数据不足时
- **THEN** 系统返回友好提示信息

#### Scenario: 性能要求

- **WHEN** 处理 1000 条记录
- **THEN** 计算时间 < 2 秒

**算法规格**:
```
ATL = EWMA(TSS, 时间窗口=7天)
CTL = EWMA(TSS, 时间窗口=42天)
TSB = CTL - ATL
```

---

### Requirement: 训练负荷趋势分析 (T003)

系统 SHALL 提供训练负荷趋势数据获取功能，支持可视化图表展示。

#### Scenario: 正常趋势分析

- **WHEN** 用户请求训练负荷趋势
- **THEN** 系统返回每日训练负荷数据列表

#### Scenario: 包含体能状态评估

- **WHEN** 返回趋势数据
- **THEN** 包含体能状态评估和训练建议

#### Scenario: 性能要求

- **WHEN** 处理 90 天数据
- **THEN** 计算时间 < 3 秒

---

### Requirement: 晨报内容生成 (T004)

系统 SHALL 提供每日晨报内容自动生成功能。

#### Scenario: 正常晨报生成

- **WHEN** 系统生成每日晨报
- **THEN** 晨报内容完整，包含训练负荷、体能状态、训练建议

#### Scenario: 训练建议生成

- **WHEN** 基于训练负荷数据
- **THEN** 自动生成个性化训练建议

#### Scenario: 性能要求

- **WHEN** 生成晨报
- **THEN** 生成时间 < 1 秒

**晨报内容结构**:
- 日期和问候语
- 昨日训练摘要（如有）
- 当前体能状态（ATL/CTL/TSB）
- 训练建议
- 本周训练计划预览

## MODIFIED Requirements

无（新增功能）

## REMOVED Requirements

无

## 任务依赖关系

```
T001 (TSS 计算) ✅ 已完成
    ↓
T002 (ATL/CTL/TSB 计算) ← 当前执行
    ↓
    ├── T003 (训练负荷趋势分析) ← 可并行
    └── T004 (晨报内容生成) ← 可并行
```

**执行顺序**:
1. 先执行 T002
2. T002 完成后，并行执行 T003 和 T004
