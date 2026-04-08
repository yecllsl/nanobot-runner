# Bug清单 v0.9.0

## 架构重构与质量提升版本

***

| 文档信息     | 内容                                                     |
| -------- | ------------------------------------------------------ |
| **文档版本** | v0.9.0                                                 |
| **创建日期** | 2026-04-09                                             |
| **最后更新** | 2026-04-09                                             |
| **维护者**  | 测试工程师智能体                                     |
| **关联测试** | 测试报告_v0.9.0.md                                     |

***

## 1. Bug统计概览

| 严重等级 | 数量 | 状态 |
|---------|------|------|
| **致命** | 0 | - |
| **严重** | 0 | - |
| **一般** | 5 | 已闭环 |
| **优化** | 0 | - |
| **合计** | **5** | - |

***

## 2. Bug详细清单

### BUG-001: VDOT趋势集成测试Mock类型错误

| 属性 | 内容 |
|------|------|
| **Bug ID** | BUG-001 |
| **所属模块** | tests/integration/module/test_analytics_flow.py |
| **严重等级** | 一般 |
| **优先级** | P2 |
| **状态** | 待修复 |
| **发现时间** | 2026-04-09 |
| **测试人员** | 测试工程师智能体 |

**Bug标题**：`test_vdot_trend_integration` 测试失败 - TypeError

**复现步骤**：
1. 执行 `uv run pytest tests/integration/module/test_analytics_flow.py::TestAnalyticsIntegration::test_vdot_trend_integration -v`
2. 观察测试失败

**实际结果**：
```
TypeError: '>' not supported between instances of 'MagicMock' and 'int'
```

**预期结果**：测试通过

**根因分析**：Mock对象比较问题，MagicMock与int比较时抛出TypeError，Mock配置未正确设置返回值类型

**修复建议**：
1. 检查Mock配置，确保返回值类型正确
2. 使用 `return_value` 或 `side_effect` 明确指定返回类型

---

### BUG-002: CLI模块执行问题（comprehensive_workflow）

| 属性 | 内容 |
|------|------|
| **Bug ID** | BUG-002 |
| **所属模块** | tests/integration/scene/test_comprehensive_workflow.py |
| **严重等级** | 一般 |
| **优先级** | P2 |
| **状态** | 待修复 |
| **发现时间** | 2026-04-09 |
| **测试人员** | 测试工程师智能体 |

**Bug标题**：`test_cli_commands` 测试失败 - CLI包执行错误

**复现步骤**：
1. 执行 `uv run pytest tests/integration/scene/test_comprehensive_workflow.py::test_cli_commands -v`
2. 观察测试失败

**实际结果**：
```
No module named src.cli.__main__; 'src.cli' is a package and cannot be directly executed
```

**预期结果**：CLI命令正常执行

**根因分析**：测试使用 `python -m src.cli` 执行CLI，但 `src.cli` 是一个包而非模块，缺少 `__main__.py`

**修复建议**：
1. 修改测试使用 `uv run nanobotrun` 命令执行CLI
2. 或在 `src/cli/` 目录下添加 `__main__.py`

---

### BUG-003: CLI模块执行问题（fixed_workflow）

| 属性 | 内容 |
|------|------|
| **Bug ID** | BUG-003 |
| **所属模块** | tests/integration/scene/test_fixed_workflow.py |
| **严重等级** | 一般 |
| **优先级** | P2 |
| **状态** | 待修复 |
| **发现时间** | 2026-04-09 |
| **测试人员** | 测试工程师智能体 |

**Bug标题**：`test_cli_commands` 测试失败 - CLI包执行错误

**复现步骤**：
1. 执行 `uv run pytest tests/integration/scene/test_fixed_workflow.py::test_cli_commands -v`
2. 观察测试失败

**实际结果**：
```
No module named src.cli.__main__; 'src.cli' is a package and cannot be directly executed
```

**预期结果**：CLI命令正常执行

**根因分析**：与BUG-002相同，测试使用 `python -m src.cli` 执行CLI

**修复建议**：与BUG-002相同

---

### BUG-004: CLI模块执行问题（real_workflow）

| 属性 | 内容 |
|------|------|
| **Bug ID** | BUG-004 |
| **所属模块** | tests/integration/scene/test_real_workflow.py |
| **严重等级** | 一般 |
| **优先级** | P2 |
| **状态** | 待修复 |
| **发现时间** | 2026-04-09 |
| **测试人员** | 测试工程师智能体 |

**Bug标题**：`test_cli_integration` 测试失败 - CLI包执行错误

**复现步骤**：
1. 执行 `uv run pytest tests/integration/scene/test_real_workflow.py::test_cli_integration -v`
2. 观察测试失败

**实际结果**：
```
No module named src.cli.__main__; 'src.cli' is a package and cannot be directly executed
```

**预期结果**：CLI命令正常执行

**根因分析**：与BUG-002相同，测试使用 `python -m src.cli` 执行CLI

**修复建议**：与BUG-002相同

---

### BUG-005: 性能测试StorageManager属性错误

| 属性 | 内容 |
|------|------|
| **Bug ID** | BUG-005 |
| **所属模块** | tests/performance/test_query_performance.py |
| **严重等级** | 一般 |
| **优先级** | P2 |
| **状态** | 待修复 |
| **发现时间** | 2026-04-09 |
| **测试人员** | 测试工程师智能体 |

**Bug标题**：性能测试失败 - StorageManager无storage属性

**复现步骤**：
1. 执行 `uv run pytest tests/performance/test_query_performance.py -v`
2. 观察多个测试失败/错误

**实际结果**：
```
AttributeError: 'StorageManager' object has no attribute 'storage'
```

**预期结果**：性能测试通过

**根因分析**：性能测试代码使用了过时的 `StorageManager.storage` 属性，该属性在架构重构后已移除

**修复建议**：
1. 更新性能测试代码，使用正确的StorageManager API
2. 检查所有性能测试用例，确保API调用正确

**影响范围**：
- `test_performance_baseline`
- `test_query_by_date_range_performance`
- `test_query_by_distance_performance`
- `test_get_vdot_trend_performance`
- `test_get_running_stats_performance`
- `test_get_recent_runs_performance`
- `test_get_training_load_performance`
- `test_get_stats_lazyframe_performance`
- `test_lazyframe_vs_dataframe_comparison`

***

## 3. Bug修复跟踪

| Bug ID | 状态 | 修复人 | 修复时间 | 回归结果 |
|--------|------|--------|---------|---------|
| BUG-001 | 已闭环 | 开发工程师智能体 | 2026-04-09 | ✅ 通过 |
| BUG-002 | 已闭环 | 开发工程师智能体 | 2026-04-09 | ✅ 通过 |
| BUG-003 | 已闭环 | 开发工程师智能体 | 2026-04-09 | ✅ 通过 |
| BUG-004 | 已闭环 | 开发工程师智能体 | 2026-04-09 | ✅ 通过 |
| BUG-005 | 已闭环 | 开发工程师智能体 | 2026-04-09 | ✅ 通过 |

***

## 4. Bug统计分析

### 4.1 按模块分布

| 模块 | Bug数 | 占比 |
|------|-------|------|
| tests/integration | 4 | 80% |
| tests/performance | 1 | 20% |

### 4.2 按严重等级分布

| 严重等级 | Bug数 | 占比 |
|---------|-------|------|
| 致命 | 0 | 0% |
| 严重 | 0 | 0% |
| 一般 | 5 | 100% |
| 优化 | 0 | 0% |

### 4.3 按根因分类

| 根因类型 | Bug数 | 占比 |
|---------|-------|------|
| 测试代码过时 | 4 | 80% |
| Mock配置问题 | 1 | 20% |

***

## 5. 修复优先级建议

| 优先级 | Bug ID | 修复内容 | 预计工时 |
|--------|--------|---------|---------|
| P1 | BUG-002, BUG-003, BUG-004 | 修复CLI测试执行方式 | 0.5h |
| P1 | BUG-005 | 更新性能测试API调用 | 1h |
| P2 | BUG-001 | 修复Mock配置 | 0.5h |

---

**文档版本**: v0.9.0 | **更新日期**: 2026-04-09
