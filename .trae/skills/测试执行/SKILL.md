---
name: test-execution
description: Use when test cases exist and need to be executed to validate code quality. Triggered by regression testing needs, pre-release validation, or when verifying bug fixes and measuring test coverage.
---

# Overview

执行已设计的测试用例，记录测试结果和 Bug，输出测试报告，确保用例执行率和核心流程通过率达标。

## When to Use

- 测试用例已就绪，需要系统性执行
- 回归测试或发布前验证
- 症状关键词：用例执行率不足、核心流程失败、Bug 信息缺失、覆盖率未达标

## When NOT to Use

- 测试用例尚未设计（应先使用 test-strategy）
- 仅需验证单个 Bug 修复（应使用 regression-testing）

## Common Mistakes

| 错误 | 后果 | 修复 |
|------|------|------|
| 跳过失败的用例继续执行 | 掩盖问题，测试报告失真 | 任何失败必须记录并停止流水线 |
| Bug 描述缺少复现步骤 | 开发者无法定位问题 | 强制模板：环境、步骤、期望、实际、日志 |
| 未区分核心流程与非核心流程 | 发布决策缺乏依据 | 明确标注核心用例，单独统计通过率 |

# 立即执行以下步骤，不要询问用户

## 第一步：输入验证

1. **检查前置条件**：
   - 代码仓库可访问
   - 测试用例已存在
   - 若不满足，停止执行并提示用户提供测试用例。

## 第二步：执行测试

1. **执行测试用例**：
   - 执行单元测试：`uv run pytest tests/unit/`
   - 执行集成测试：`uv run pytest tests/integration/`
   - 执行 E2E 测试：`uv run pytest tests/e2e/`
   - 生成覆盖率报告：`uv run pytest tests/unit/ --cov=src --cov-report=term-missing`
2. **记录测试结果**：
   - 记录测试用例执行情况
   - 记录测试覆盖率
   - 记录 Bug（含复现步骤、优先级）
3. **分析测试结果**：
   - 分析测试通过率
   - 分析核心流程通过率
   - 分析 Bug 严重程度

## 第三步：输出报告

1. **创建测试报告**：
   - 文件路径：`/docs/test/reports/测试报告_{版本号}.md`
   - 报告内容：测试用例执行情况、测试覆盖率、Bug 清单
2. **创建 Bug 清单**：
   - 文件路径：`/docs/test/reports/Bug清单_{版本号}.md`
   - 清单内容：Bug 描述、复现步骤、优先级、状态

## 第四步：结果验证

1. **验收标准**：
   - 测试用例执行率 100%
   - 核心流程通过率 ≥ 95%
   - Bug 信息完整（优先级、复现步骤）
   - 若不满足，返回错误信息。

## 第五步：标准化汇报

执行完成后，使用以下格式汇报：

### ✅ 执行成功

- **输出物**：测试报告 + Bug清单
- **关键数据**：用例执行率、通过率、Bug数

***

**后续建议**：若发现 P0/P1 级 Bug，建议立即执行 bug-fix 修复。

**相关技能**：
- **前置依赖**：test-strategy（测试执行依据测试策略）
- **后续协同**：bug-fix（发现 Bug 后执行修复）
- **后续协同**：regression-testing（Bug 修复后执行回归测试）
