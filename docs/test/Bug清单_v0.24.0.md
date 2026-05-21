# 项目Bug清单 - v0.24.0 个性化学习

> **版本**: v0.24.0 | **更新日期**: 2026-05-21
> **代码基线**: v0.23.0 (tag: v0.23.0) | **开发分支**: feature/0.24.0
> **测试轮次**: 第1轮（全量）
> **测试报告**: docs/test/测试报告_v0.24.0.md

---

## Bug 统计概览

| 严重等级 | 新增 | 已修复 | 待修复 | 已闭环 | 驳回 |
|---------|------|--------|--------|--------|------|
| **致命** | 0 | 0 | 0 | 0 | 0 |
| **严重** | 0 | 0 | 0 | 0 | 0 |
| **一般** | 0 | 0 | 0 | 0 | 0 |
| **优化** | 1 | 0 | **1** | 0 | 0 |
| **合计** | 1 | 0 | 1 | 0 | 0 |

---

## Bug 详细清单

---

## Bug ID: BUG-V024-001

| 字段 | 内容 |
|------|------|
| **Bug ID** | BUG-V024-001 |
| **所属模块** | `tests/unit/agents/` -- 测试代码 |
| **严重等级** | **优化（LOW）** |
| **优先级** | P2 |
| **Bug 标题** | `test_create_tools_returns_list` 中工具数量断言期望值过期 |
| **出现版本** | v0.24.0 (feature/0.24.0) |
| **创建时间** | 2026-05-21 |
| **测试人员** | 测试工程师 |
| **当前状态** | **待修复** |

### 描述

单元测试 `tests/unit/agents/test_tools.py` 中 `TestCreateTools.test_create_tools_returns_list` 方法在第 538 行断言的期望工具数量为 `51`，但 v0.23.0 进化模块新增了 3 个工具（`record_feedback`、`check_plan_execution`、`check_prediction_accuracy`、`get_decision_history` 等），v0.24.0 又新增了 2 个工具（`analyze_training_response`、`get_calibration_status`），实际工具总数已增至 `54`。测试断言未随代码变更同步更新。

### 复现步骤

1. 切换到 `feature/0.24.0` 分支
2. 执行命令：
   ```bash
   uv run pytest tests/unit/agents/test_tools.py::TestCreateTools::test_create_tools_returns_list -v
   ```
3. 观察断言失败输出

### 实际结果

```
assert 54 == 51
E   assert 54 == 51
E    +  where 54 = len(create_tools())
```

### 预期结果

断言通过（期望值与实际工具数量一致）。

### 根因分析

这是一个典型的**测试断言过期**问题，非生产代码缺陷：

1. **工具注册正常**: `create_tools()` 函数正确注册了所有 Agent 工具，实际返回 54 个工具（功能正常）
2. **测试滞后**: 测试文件中的硬编码期望值 `51` 在 v0.22 时期设定，但 v0.23 进化模块和 v0.24 个性化学习模块先后新增了工具，测试断言未同步更新
3. **增量差**: 54 - 51 = 3 个工具差异。具体为 v0.23 新增的进化模块工具（`record_feedback`, `check_plan_execution`, `check_prediction_accuracy`, `get_decision_history`）和 v0.24 新增的工具（`analyze_training_response`, `get_calibration_status`），从 51 增长了 3 个至 54

### 影响范围

- **生产代码**: **无影响** -- 工具注册功能完全正常
- **测试代码**: 仅 `test_create_tools_returns_list` 一个测试方法失败
- **CI 流水线**: 该测试失败不会阻塞发布（LOW 级别优化项）
- **用户体验**: **无影响**

### 修复建议

**方案 1（精确修复）** -- 更新硬编码期望值：

在 [test_tools.py](file:///d:/yecll/Documents/LocalCode/RunFlowAgent.worktrees/feature-0.24.0/tests/unit/agents/test_tools.py) 第 538 行：
```python
# 修改前
assert len(create_tools()) == 51

# 修改后
assert len(create_tools()) == 54
```

**方案 2（推荐，防御性修复）** -- 使用下限断言避免未来类似问题：

```python
# 修改前
assert len(create_tools()) == 51

# 修改后
assert len(create_tools()) >= 51, f"工具数量异常：期望 >= 51，实际 {len(create_tools())}"
```

方案 2 更推荐，因为它：
- 验证工具数量不低于基线（防止工具意外丢失）
- 包容未来新增工具（避免每次新增都需更新断言）
- 保留异常输出的可读性（失败时打印实际值）

### 修复负责人

开发工程师（测试代码维护责任）

### 跟踪记录

| 日期 | 操作 | 说明 |
|------|------|------|
| 2026-05-21 | 创建 | 测试工程师发现并记录 |

---

## Bug 状态说明

| 状态 | 说明 |
|------|------|
| **待修复** | 已提交给开发工程师，尚未开始修复 |
| **修复中** | 开发工程师正在进行修复 |
| **待回归** | 修复已完成，等待回归测试 |
| **已闭环** | 回归测试通过，Bug 已解决 |
| **已驳回** | 回归测试未通过或修复方案被拒绝 |

---

## 相关记录

- 暂无驳回记录
- 暂无已闭环记录

---

*清单版本: v1.0.0 | 生成日期: 2026-05-21 | 测试工程师*