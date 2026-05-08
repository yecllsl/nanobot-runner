---
name: task-breakdown
description: Use when an architecture design exists and development tasks need to be decomposed into actionable items. Triggered before sprint planning, when estimating workloads, or identifying task dependencies.
---

# Overview

将架构设计转化为可执行的开发任务清单，明确优先级、依赖关系和工作量，确保任务粒度适配迭代周期。

## When to Use

- 架构设计已就绪，需要进入开发阶段
- 需要评估工作量和识别任务依赖
- 症状关键词：任务粒度过大、依赖关系混乱、工作量估算偏差、迭代周期不匹配

## When NOT to Use

- 架构设计尚未完成（应先使用 architecture-design）
- 仅需调整单个任务的排期

## Common Mistakes

| 错误 | 后果 | 修复 |
|------|------|------|
| 任务粒度过大（超过 3 天） | 进度不可控，风险集中 | 拆分为 1-3 天可完成的子任务 |
| 未识别任务间依赖 | 并行开发时出现阻塞 | 绘制依赖图，确保无闭环 |
| 工作量估算过于乐观 | 迭代延期，士气下降 | 采用历史数据或三点估算法 |

# 立即执行以下步骤，不要询问用户

## 第一步：输入验证
1. **检查前置条件**：
    *   架构设计方案已存在：`/docs/architecture/架构设计说明书.md`
    *   若不满足，停止执行并提示用户先完成架构设计。

## 第二步：任务拆解
1. **识别开发任务**：
    *   按模块拆解任务
    *   按功能点拆解任务
    *   按优先级排序任务（P0/P1/P2）
2. **定义任务属性**：
    *   任务描述
    *   任务优先级
    *   任务依赖关系
    *   工作量估算（小时）
    *   验收标准
3. **检查依赖关系**：
    *   确保依赖关系无闭环
    *   确保任务粒度适配迭代周期（1-3天）

## 第三步：输出文档
1. **创建任务清单**：
    *   文件路径：`/docs/planning/task_list_{版本号}.md`
    *   文档格式：遵循任务清单模板
2. **文档内容**：
    *   任务列表（按优先级排序）
    *   任务属性（描述、优先级、依赖、工作量、验收标准）
    *   依赖关系图
    *   迭代计划

## 第四步：结果验证
1. **验收标准**：
    *   任务粒度适配迭代周期（1-3天）
    *   依赖关系无闭环
    *   工作量估算合理
    *   若不满足，返回错误信息。

## 第五步：标准化汇报
执行完成后，使用以下格式汇报：

### ✅ 执行成功
*   **输出物**：`/docs/planning/task_list_{版本号}.md`
*   **关键数据**：任务总数、P0任务数、总工作量（小时）

---

**后续建议**：建议执行 feature-development 开始实施任务。

**相关技能**：
- **前置依赖**：architecture-design（架构设计指导任务拆解）
- **后续协同**：feature-development（任务拆解完成后进入开发）
