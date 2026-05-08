---
name: fix-ci
description: Use when GitHub Actions workflow fails and the error appears to be configuration-related rather than business logic. Triggered by YAML syntax errors, missing actions, permission issues, or environment setup failures.
---

# Overview

自动诊断 GitHub Actions workflow 的配置型错误（非业务逻辑错误），并实施最小化修复。

## When to Use

- GitHub Actions 构建失败，报错指向配置问题
- YAML 语法错误、Action 版本缺失、权限或环境设置问题
- 症状关键词：workflow 配置错误、YAML 语法错误、Action 未找到、权限拒绝、环境缺失

## When NOT to Use

- 业务逻辑或单元测试失败（应使用 bug-fix）
- 非 GitHub Actions 的 CI 系统（如 Jenkins、GitLab CI）

## Common Mistakes

| 错误 | 后果 | 修复 |
|------|------|------|
| 将业务逻辑错误误判为配置错误 | 修改 workflow 无效，浪费时间 | 严格区分：配置错误 = YAML/Action/权限；业务错误 = 测试失败/编译错误 |
| 使用 `@master` 等不稳定 Action 版本 | 流水线因上游变更突然失败 | 优先使用带版本号的稳定标签，如 `@v4` |
| 修复后未在本地验证 YAML 语法 | 提交后再次触发失败 | 使用 `actionlint` 或在线 YAML 校验工具预检 |

# 立即执行以下步骤，不要询问用户

## 第一步：环境与权限检查
1.  **检测工具**：确认系统已安装 GitHub CLI (`gh`)。若未安装，停止执行并提示用户安装。
2.  **检查鉴权**：执行 `gh auth status`。
    *   若未登录，引导用户运行 `gh auth login` 并终止当前技能。
    *   若已登录，继续下一步。
## 第二步：抓取日志
获取最近一次失败的 CI 运行记录：
*   **主命令**：
    ```bash
    gh run view $(gh run list --limit 1 --status failure --json databaseId --jq '.[0].databaseId') --log
    ```
*   **容错机制**：若主命令报错（如无失败记录或 JSON 解析失败），执行备选方案：
    1. 列出最近运行：`gh run list --limit 5`
    2. 选择最近一个状态为 `failure` 的 ID。
    3. 查看日志：`gh run view <ID> --log`。
## 第三步：智能诊断
1.  **日志分析**：完整阅读日志，定位 `Error`、`Fail` 或 `Exception` 关键字所在的行。
2.  **根因定位**：
    *   读取 `.github/workflows/` 目录下的相关 YAML 文件。
    *   **判断错误类型**：
        *   **配置型错误**（本技能处理范围）：语法错误、路径错误、Action 版本不存在、环境变量缺失、权限不足、依赖未安装导致脚本中断。
        *   **代码型错误**（仅汇报不修复）：业务逻辑报错、单元测试失败、编译错误。
3.  **决策**：如果是配置型错误，进入修复步骤；如果是代码型错误，生成诊断报告后停止，提示用户需修复业务代码。
## 第四步：执行修复
针对配置型错误，直接修改文件：
*   **原则**：
    *   最小改动原则：只修复导致报错的具体配置项，不重构 workflow 结构。
    *   兼容性原则：优先使用稳定的 Action 版本，避免使用 `@master` 等不稳定标签。
*   **操作**：直接写入修改后的文件内容。
## 第五步：标准化汇报
修复完成后（或判断无法修复时），使用以下格式汇报：
### 🚑 CI 急救报告
*   **诊断对象**：[Run ID] - [Commit Message/Hash]
*   **错误类型**：[Workflow 配置错误 / 业务代码错误]
*   **根本原因**：
    > 简要描述日志中的关键报错信息（例如：Step 'Build' 中缺少依赖安装步骤）。
*   **修复动作**：
    *   📄 **文件**：`.github/workflows/ci.yml`
    *   ✏️ **位置**：第 28 行
    *   🛠️ **改动**：增加 `- run: npm install` 步骤。
---
**后续建议**：请检查业务代码逻辑后重新提交。

**相关技能**：
- **前置触发**：cicd-verification（CI 验证发现失败后执行修复）
- **区分使用**：bug-fix（业务逻辑错误应使用 bug-fix，而非 fix-ci）

