# v0.3.0 迭代性能测试与覆盖率提升 Spec

## Why

T001-T006 已完成核心功能开发，现在需要补充性能测试确保系统性能满足架构设计要求，并提升测试覆盖率确保代码质量。

## What Changes

- **T007**: 补充性能测试 - 新增 `tests/performance/` 目录，实现性能基准测试
- **T008**: 提升测试覆盖率 - 补充单元测试和集成测试，确保覆盖率 ≥ 80%

## Impact

- Affected specs: `tests/performance/`, `tests/unit/`, `tests/integration/`
- Affected code: 
  - `tests/performance/test_query_performance.py` - 查询性能测试
  - `tests/performance/test_analytics_performance.py` - 分析性能测试
  - `tests/performance/test_report_performance.py` - 晨报性能测试
  - `tests/unit/` - 补充单元测试

## ADDED Requirements

### Requirement: 性能基准测试 (T007)

系统 SHALL 提供性能基准测试，确保查询响应时间满足架构设计要求。

#### Scenario: 查询性能测试

- **WHEN** 执行日期范围查询
- **THEN** 响应时间 < 3 秒

#### Scenario: VDOT 趋势查询性能测试

- **WHEN** 查询 90 天 VDOT 趋势
- **THEN** 响应时间 < 3 秒

#### Scenario: 训练负荷计算性能测试

- **WHEN** 计算 1000 条记录的 ATL/CTL/TSB
- **THEN** 计算时间 < 2 秒

#### Scenario: 晨报生成性能测试

- **WHEN** 生成每日晨报
- **THEN** 生成时间 < 1 秒

---

### Requirement: 测试覆盖率提升 (T008)

系统 SHALL 确保测试覆盖率满足架构设计要求。

#### Scenario: 核心模块覆盖率

- **WHEN** 运行单元测试
- **THEN** `src/core/analytics.py` 覆盖率 ≥ 85%

#### Scenario: 工具模块覆盖率

- **WHEN** 运行单元测试
- **THEN** `src/agents/tools.py` 覆盖率 ≥ 85%

#### Scenario: 通知模块覆盖率

- **WHEN** 运行单元测试
- **THEN** `src/notify/feishu.py` 覆盖率 ≥ 80%

#### Scenario: 总体覆盖率

- **WHEN** 运行所有测试
- **THEN** 总体覆盖率 ≥ 80%

## MODIFIED Requirements

无（新增功能）

## REMOVED Requirements

无

## 任务依赖关系

```
T001-T006 ✅ 已完成
    ↓
    ├── T007 (性能测试) ← 可并行
    └── T008 (覆盖率提升) ← 可并行
```

**执行顺序**: T007 和 T008 可并行执行

## 性能测试指标

| 测试项 | 性能要求 | 测试数据量 |
|-------|---------|-----------|
| 日期范围查询 | < 3 秒 | 1000 条记录 |
| 距离范围查询 | < 3 秒 | 1000 条记录 |
| VDOT 趋势查询 | < 3 秒 | 90 天数据 |
| 训练负荷计算 | < 2 秒 | 1000 条记录 |
| 晨报生成 | < 1 秒 | 单次生成 |
| 心率区间分析 | < 2 秒 | 10000 条记录 |
| 配速分布分析 | < 2 秒 | 1000 条记录 |

## 覆盖率目标

| 模块 | 当前覆盖率 | 目标覆盖率 |
|------|-----------|-----------|
| `src/core/analytics.py` | 94% | ≥ 85% ✅ |
| `src/agents/tools.py` | 86% | ≥ 85% ✅ |
| `src/notify/feishu.py` | 96% | ≥ 80% ✅ |
| `src/cli_formatter.py` | 91% | ≥ 80% ✅ |
| `src/core/report_service.py` | 94% | ≥ 80% ✅ |
| **总体覆盖率** | - | ≥ 80% |
