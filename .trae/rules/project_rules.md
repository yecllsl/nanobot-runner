---
alwaysApply: true
description: 业务规则、审查维度、智能体协作核心约束。与 AGENTS.md 配合使用。
---
# Project Rules
## 业务规则
**计算**: VDOT(Powers,距离>=1500m) | TSS(时长×IF²×100) | 心率漂移(相关性<-0.7)
**存储**: Parquet按年分片 | SHA256去重 | 必填: activity_id, timestamp, source_file, filename, total_distance, total_timer_time
## 配置分离
**框架** (`~/.nanobot/`): LLM Provider、飞书通道、Gateway、定时任务
**业务** (`~/.nanobot-runner/`): 跑步数据、画像、记忆、会话
## 审查维度
**必检**: 功能正确性 | 边界处理 | Polars LazyFrame | 类型注解 | 单元测试
**命名**: 类PascalCase, 函数snake_case, 常量UPPER_SNAKE_CASE
**CI**: black→isort→mypy→bandit→pytest
## 输出格式
**CLI**: 时长HH:MM:SS | 配速M'SS"/km
**Agent**: JSON含success/data/message或error/details
## 质量门禁
**覆盖率**: core≥80% | agents≥70% | cli≥60%
**禁止**: ❌硬编码敏感信息 | ❌print调试 | ❌测试未通过合并
**Commit**: `<type>(<scope>): <subject>`
## 智能体协作
**角色**: 架构师→开发→评审→测试→修复→回归→运维
**准入**: 开发(需求确认) | 测试(覆盖率≥80%+评审) | 发布(Bug清零+CICD)
**交付物**: `角色_指令_版本.md` → docs/
## 规范文档
- 执行指令: `.trae/指令手册.md`
- 协作流程: `.trae/协作链路.md`
