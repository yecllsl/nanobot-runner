---
name: bug-fix
description: Use when a bug list exists with reproduction steps and code fixes are required. Triggered by failed regression tests, user-reported defects, or when P0/P1 bugs block release.
---

# Overview

基于 Bug 清单定位根因，修复问题并补充回归测试，确保 Bug 可复现验证且无新 Bug 引入。

## When to Use

- Bug 清单已存在，包含复现步骤和优先级
- 回归测试失败或用户报告缺陷
- 症状关键词：P0/P1 Bug 阻塞发布、复现步骤缺失、修复后无测试覆盖、引入回归

## When NOT to Use

- 仅优化代码结构而非修复缺陷（应使用 code-optimization）
- Bug 信息不完整，无法复现

## Common Mistakes

| 错误 | 后果 | 修复 |
|------|------|------|
| 未复现 Bug 直接修改代码 | 修复的是表象而非根因 | 严格按复现步骤验证后再动手 |
| 修复后未新增回归测试 | 同一 Bug 后续反复出现 | 每个 Bug 修复必须配套一个回归用例 |
| 只修复当前分支，未检查其他分支 | 多版本重复出现同一 Bug | 评估是否需要 cherry-pick 到其他维护分支 |

# 立即执行以下步骤，不要询问用户

## 第一步：输入验证

1. **检查前置条件**：
   - Bug 清单已存在：`/docs/test/reports/Bug清单_*.md`
   - 代码仓库可访问
   - 若不满足，停止执行并提示用户提供 Bug 清单。

## 第二步：Bug 分析与修复

1. **分析 Bug**：
   - 阅读 Bug 清单，理解 Bug 描述
   - 复现 Bug（按复现步骤）
   - 定位 Bug 根因
2. **修复 Bug**：
   - 修改代码，修复 Bug
   - 更新或新增测试用例，覆盖 Bug 场景
   - 执行测试，验证 Bug 修复
3. **验证无新 Bug**：
   - 执行完整测试套件
   - 确保无新 Bug 引入

## 第三步：输出交付物

1. **提交代码**：
   - 提交至 Git 分支
   - 提交信息遵循规范：`fix(scope): <subject>`
2. **创建修复报告**：
   - 文件路径：`/docs/development/Bug修复报告_{版本号}.md`
   - 报告内容：Bug 描述、根因分析、修复方案、测试结果

## 第四步：结果验证

1. **验收标准**：
   - Bug 复现验证通过
   - 测试用例覆盖 Bug 场景
   - 无新 Bug 引入
   - 若不满足，返回错误信息。

## 第五步：标准化汇报

执行完成后，使用以下格式汇报：

### ✅ 执行成功

- **输出物**：修复代码 + 更新测试 + 修复报告
- **关键数据**：修复 Bug 数、测试通过率

***

**后续建议**：建议执行 regression-testing 验证 Bug 修复。

**相关技能**：
- **前置依赖**：test-execution（测试执行发现 Bug）
- **后续协同**：regression-testing（修复后执行回归测试）
