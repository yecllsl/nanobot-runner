---
name: regression-testing
description: Use when bug fixes have been committed and release readiness must be validated. Triggered before go-live decisions, after critical bug fixes, or when verifying no new bugs were introduced.
---

# Overview

验证 Bug 修复的有效性，评估发布风险，输出明确的上线/不上线结论。

## When to Use

- Bug 修复已提交，需要验证发布 readiness
- 发布前需要确认 P0/P1 Bug 已全部修复
- 症状关键词：Bug 修复未验证、新 Bug 引入、上线决策缺乏依据、回归范围不清

## When NOT to Use

- 尚未有 Bug 修复报告（应先使用 bug-fix）
- 仅需执行常规测试用例（应使用 test-execution）

## Common Mistakes

| 错误 | 后果 | 修复 |
|------|------|------|
| 仅验证修复点，忽略关联功能 | 修复引发周边功能故障 | 必须评估并测试受影响的功能范围 |
| 上线结论模糊 | 发布决策拖延或冒险 | 结论必须明确：建议上线 / 不建议上线 / 条件上线 |
| 未发现的新 Bug 未记录 | 遗漏问题，影响用户信任 | 任何新发现的问题必须记入 Bug 清单 |

# 立即执行以下步骤，不要询问用户

## 第一步：输入验证
1. **检查前置条件**：
    *   Bug 修复报告已存在：`/docs/development/Bug修复报告_*.md`
    *   修复代码已提交
    *   若不满足，停止执行并提示用户提供 Bug 修复报告。

## 第二步：回归测试
1. **分析 Bug 修复报告**：
    *   阅读 Bug 修复报告，理解修复方案
    *   识别修复的 Bug 列表
    *   识别修复的代码范围
2. **执行回归测试**：
    *   执行 Bug 相关测试用例
    *   执行受影响功能的测试用例
    *   执行完整测试套件（可选）
3. **验证 Bug 修复**：
    *   验证 P0/P1 Bug 100% 修复
    *   验证无新 Bug 引入
    *   记录验证结果

## 第三步：输出报告
1. **创建回归报告**：
    *   文件路径：`/docs/test/reports/回归报告_{版本号}.md`
    *   报告内容：Bug 修复验证情况、测试结果、新 Bug 清单
2. **给出上线结论**：
    *   若 P0/P1 Bug 100% 修复且无新 Bug：建议上线
    *   若存在 P0/P1 Bug 未修复：不建议上线
    *   若发现新 Bug：建议修复后再上线

## 第四步：结果验证
1. **验收标准**：
    *   P0/P1 Bug 100% 修复验证
    *   回归测试执行完整
    *   上线结论明确
    *   若不满足，返回错误信息。

## 第五步：标准化汇报
执行完成后，使用以下格式汇报：

### ✅ 执行成功
*   **输出物**：回归报告 + 上线结论
*   **关键数据**：Bug 修复率、测试通过率、上线结论

---

**后续建议**：若建议上线，可执行 solo-auto-release 发布版本。

**相关技能**：
- **前置依赖**：bug-fix（回归测试验证 Bug 修复）
- **前置依赖**：test-execution（全量测试通过后方可回归）
- **后续协同**：solo-auto-release（回归通过后执行发布）
