---
name: architecture-design
description: Use when requirements are finalized and a system architecture blueprint is needed before development. Triggered when selecting technology stacks, designing module boundaries, or defining API contracts and data flows.
---

# Overview

基于已确定的需求规格，设计技术栈选型、模块边界、接口规范和数据流，输出可落地的架构蓝图。

## When to Use

- 需求已冻结，需要技术方案指导开发
- 技术栈选型存在争议或需要变更
- 症状关键词：模块职责不清、接口缺失、数据流混乱、技术债务累积

## When NOT to Use

- 需求尚未明确（应先执行 requirements-analysis）
- 仅做代码级重构，不涉及模块边界调整（应使用 code-optimization）

## Common Mistakes

| 错误 | 后果 | 修复 |
|------|------|------|
| 过度设计，引入不必要的抽象层 | 代码复杂度上升，维护困难 | 遵循 YAGNI，只解决当前已知问题 |
| 模块间循环依赖 | 构建失败，测试难以隔离 | 引入依赖注入或事件总线解耦 |
| 接口规范缺少版本策略 | 后续变更破坏兼容性 | 所有 API 必须标注版本和弃用策略 |

# 立即执行以下步骤，不要询问用户

## 第一步：输入验证
1. **检查前置条件**：
    *   需求规格说明书已存在：`/docs/requirements/REQ_*.md`
    *   若不满足，停止执行并提示用户先完成需求分析。

## 第二步：架构设计
1. **技术栈选择**：
    *   分析需求的技术要求
    *   选择合适的技术栈（语言、框架、数据库）
    *   确保技术栈适配项目特点
2. **模块划分**：
    *   识别核心模块
    *   定义模块职责
    *   确定模块依赖关系
3. **接口设计**：
    *   定义模块间接口
    *   定义数据流
    *   定义API规范

## 第三步：输出文档
1. **创建架构文档**：
    *   文件路径：`/docs/architecture/架构设计说明书.md`
    *   文档格式：遵循架构设计模板
2. **文档内容**：
    *   技术栈选型
    *   系统架构图
    *   模块划分
    *   接口规范
    *   数据流设计
    *   部署架构

## 第四步：结果验证
1. **验收标准**：
    *   技术栈适配项目特点
    *   模块划分清晰，职责明确
    *   接口规范完整
    *   若不满足，返回错误信息。

## 第五步：标准化汇报
执行完成后，使用以下格式汇报：

### ✅ 执行成功
*   **输出物**：`/docs/architecture/架构设计说明书.md`
*   **关键数据**：模块数、接口数、技术栈组件数

---

**后续建议**：建议执行 task-breakdown 后再进入开发阶段。

**相关技能**：
- **前置依赖**：requirements-analysis（需求分析提供输入）
- **后续协同**：architecture-review（架构设计完成后进行评审）
- **后续协同**：task-breakdown（架构设计完成后拆解任务）
