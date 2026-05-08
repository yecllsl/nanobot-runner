---
name: document-update
description: Use when version changes require synchronizing user-facing documentation and project baseline docs. Triggered after feature completion, before release, or when CLI commands, APIs, or configurations change.
---

# Overview

同步更新用户文档和项目基线文档，确保所有文档与代码版本保持一致、可发布。

## When to Use

- 功能开发完成，版本即将发布
- CLI 命令、API 或配置发生变更
- 症状关键词：文档与代码不一致、版本号错位、命令示例失效、API 签名过期

## When NOT to Use

- 仅修复文档错别字（直接编辑即可）
- 版本尚未冻结，功能仍在开发中

## Common Mistakes

| 错误 | 后果 | 修复 |
|------|------|------|
| 只更新用户文档，忽略 AGENTS.md 等基线文档 | 开发者参考过期规范 | 建立文档更新清单，强制检查基线文档 |
| 命令示例未实际执行验证 | 用户复制命令后报错 | 所有 CLI 示例必须在更新后实际运行 |
| 遗漏配置文件示例更新 | 用户无法正确配置 | 将 config.example.json 纳入必检清单 |

# 立即执行以下步骤，不要询问用户

## 第一步：收集版本变更信息

1. **获取版本号**：从用户输入或 `pyproject.toml` 中获取版本号。
2. **获取变更内容**：从 `CHANGELOG.md` 或用户提供的信息中获取变更内容。
3. **识别变更类型**：
   - **功能新增**：需要更新用户手册、API文档、README
   - **架构重构**：需要更新架构设计说明书、AGENTS.md、REQ\_需求规格说明书、产品规划方案
   - **接口变更**：需要更新api/目录下文档、更新guides/目录下指南文档
   - **配置变更**：需要更新配置文件示例、Agent配置指南

## 第二步：更新用户文档（随版本发布）

| 文档 | 位置 | 更新要点 | 验收标准 |
|------|------|----------|----------|
| CHANGELOG.md | `/CHANGELOG.md` | 记录变更、区分类型、提供升级指南 | 内容完整、版本号/日期正确 |
| README.md | `/README.md` | 快速开始、特性列表、安装说明 | 指南可执行、特性与版本一致 |
| CLI使用指南 | `docs/guides/cli_usage.md` | 命令格式、参数、示例 | 格式与代码一致、示例可执行 |
| API参考 | `docs/api/api_reference.md` | 类/方法签名、新增API、废弃标记 | 签名与代码一致、新增已记录 |
| Agent配置指南 | `docs/guides/agent_config_guide.md` | 配置示例、配置项说明 | 示例可执行、说明准确 |
| 配置文件示例 | `config.example.json` | 版本号、新增配置项、默认值 | 版本号正确、配置项完整 |

## 第三步：更新全局指路文档（项目基线）

| 文档 | 位置 | 更新要点 | 验收标准 |
|------|------|----------|----------|
| AGENTS.md | `/AGENTS.md` | 项目定义、结构、数据流、规范、命令 | 反映当前架构、命令可执行 |
| 架构设计说明书 | `docs/architecture/架构设计说明书.md` | 架构图、模块设计、技术栈 | 架构图准确、技术栈版本正确 |
| 需求规格说明书 | `docs/requirements/REQ_需求规格说明书.md` | 需求状态、新增需求 | 状态准确、新增已记录 |
| 协作链路 | `.trae/协作链路.md` | 协作流程、准入准出规则 | 流程准确、规则清晰 |
| 指令手册 | `.trae/指令手册.md` | 指令定义、新增指令 | 定义准确、新增已记录 |
| 分支管理与发布流程 | `docs/devops/分支管理与发布流程规范.md` | 分支策略、发布流程 | 策略准确、流程可执行 |
| 发布检查清单 | `docs/devops/release_checklist.md` | 检查项、命令参考 | 检查项完整、命令准确 |

## 第四步：验证文档一致性

1. **文档与代码一致性**：
   - 确认API签名与代码一致
   - 确认CLI命令与代码一致
   - 确认配置项与代码一致
2. **文档与版本一致性**：
   - 确认CHANGELOG与版本变更一致
   - 确认README与版本特性一致
   - 确认架构设计与版本架构一致
3. **用户文档可发布性**：
   - 确认用户文档可随版本发布
   - 确认文档无敏感信息
   - 确认文档格式正确

## 第五步：标准化汇报

更新完成后，使用以下格式汇报：

### 📝 文档更新报告

- **版本号**：\[版本号]
- **更新类型**：\[功能新增 / 架构重构 / 接口变更 / 配置变更]
- **更新内容**：
  > 简要描述更新的主要内容（例如：更新了CLI使用指南以反映v0.9.0的CLI分层重构）。
- **更新文件列表**：用户文档（CHANGELOG.md, README.md, cli_usage.md, api_reference.md, agent_config_guide.md, config.example.json）+ 全局指路文档（AGENTS.md, 架构设计说明书, REQ_需求规格说明书, 协作链路, 指令手册, 分支管理与发布流程规范, release_checklist.md）
- **验证结果**：
  - ✅ 文档与代码一致
  - ✅ 文档与版本一致
  - ✅ 用户文档可发布

***

**后续建议**：请在版本发布前确认所有文档已更新完成。

## 相关技能

- **文档归档** (document-archive)：版本发布后，归档版本特定文档
- **单人自动化发布** (solo-auto-release)：版本发布完整流程
- **CICD验证** (cicd-verification)：发布前验证 CI/CD 流水线状态
- **回归测试** (regression-testing)：发布前验证测试通过
