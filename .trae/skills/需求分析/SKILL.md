---
name: requirements-analysis
description: Use when business requirements are vague or ambiguous and need to be translated into quantifiable, testable acceptance criteria. Triggered when starting a new feature, planning an iteration, or when existing requirements lack clear MVP prioritization.
---

# Overview

将模糊的业务诉求转化为无歧义、可量化的需求规格说明书，明确 MVP 边界和验收标准。

## When to Use

- 业务需求模糊，缺乏可量化的验收标准
- 需要区分 MVP 核心需求（P0）与非核心需求
- 症状关键词：需求歧义、验收标准不可测试、优先级混乱、范围蔓延

## When NOT to Use

- 已有明确的需求文档，仅需微调措辞
- 纯技术实现细节讨论（应使用 feature-development 技能）

## Common Mistakes

| 错误 | 后果 | 修复 |
|------|------|------|
| 验收标准使用"提升用户体验"等模糊描述 | 无法验证需求是否完成 | 改为可量化指标，如"查询响应时间 < 200ms" |
| 未区分 MVP 与非 MVP 需求 | 范围蔓延，迭代延期 | 强制按 P0/P1/P2 分类，P0 必须可独立交付 |
| 忽略非功能需求 | 上线后性能/安全问题 | 每个功能需求必须配套至少一个非功能需求 |

# 立即执行以下步骤，不要询问用户

## 第一步：输入验证

1. **检查前置条件**：
   - 业务诉求已提供（项目背景、核心场景）
   - 产品规划方案已存在：`/docs/product/产品规划方案.md`
   - 若不满足，停止执行并提示用户提供业务诉求。

## 第二步：需求分析

1. **拆解业务诉求**：
   - 识别核心功能点
   - 识别辅助功能点
   - 识别非功能需求（性能、安全、可维护性）
2. **区分需求优先级**：
   - MVP核心需求（P0）：必须实现
   - 重要需求（P1）：应该实现
   - 次要需求（P2）：可以延后
3. **定义验收标准**：
   - 每个需求必须有可量化的验收标准
   - 验收标准必须明确、可测试

## 第三步：输出文档

1. **创建需求文档**：
   - 文件路径：`/docs/requirements/REQ_需求规格说明书.md`
   - 文档格式：遵循REQ模板
2. **文档内容**：
   - 项目背景
   - 核心场景
   - 功能需求（按优先级排序）
   - 非功能需求
   - 验收标准
   - 迭代计划

## 第四步：结果验证

1. **验收标准**：
   - 需求无歧义，描述清晰
   - 验收标准可量化
   - MVP核心需求明确
   - 若不满足，返回错误信息。

## 第五步：标准化汇报

执行完成后，使用以下格式汇报：

### ✅ 执行成功

- **输出物**：`/docs/requirements/REQ_{需求名称}.md`
- **关键数据**：需求总数、MVP需求数、验收标准数

***

**后续建议**：建议执行 architecture-design 后再进入开发阶段。

**相关技能**：
- **前置依赖**：product-planning（产品规划提供方向）
- **后续协同**：architecture-design（需求分析完成后进行架构设计）
