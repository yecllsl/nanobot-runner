---
alwaysApply: true
description: 业务规则、审查维度、智能体协作核心约束。与 AGENTS.md（技术栈/命令/架构）配合使用。
---
# Project Rules

## 业务规则
**计算**: VDOT(Powers公式,距离>=1500m) | TSS(时长×IF²×100) | 心率漂移(相关性<-0.7)
**存储**: Parquet按年分片 | SHA256去重 | 必填: activity_id, timestamp, source_file, filename, total_distance, total_timer_time

## 审查维度
**必检**: 功能正确性 | 边界处理(None vs异常) | Polars LazyFrame | 类型注解 | 单元测试
**命名**: 类PascalCase, 函数snake_case, 常量UPPER_SNAKE_CASE
**CI**: black→isort→mypy→bandit→pytest

## 输出格式
**CLI**: 时长HH:MM:SS | 配速M'SS"/km
**Agent**: JSON含success/data/message或error/details

## 质量门禁
**覆盖率**: core≥80% | agents≥70% | cli≥60%
**禁止**: ❌硬编码敏感信息 | ❌print调试(用logger) | ❌测试未通过合并
**Commit**: `<type>(<scope>): <subject>`

## 智能体协作
**角色**: 架构师(需求/架构/任务)→开发(开发/测试/调试)→架构师(评审)→测试(策略/用例/测试/Bug)→开发(修复)→测试(回归/评估)→运维(CICD/发布/监控)
**时效**: P0/P1 Bug 2h响应4h修复 | CICD失败1h排查2h修复 | 高危漏洞立即暂停
**准入**: 开发(需求/架构/任务确认) | 测试(交付报告+覆盖率≥80%+评审通过) | 发布(上线结论+Bug清零+CICD通过)
**交付物**: `角色缩写_指令_版本号.md` → docs/{requirement,architecture,planning,development,test,devops}/

## 详细规范
- 执行指令: `.trae/智能体标准化执行指令手册_v1.2.0.md`
- 协作流程: `.trae/版本迭代开发最佳实践协作链路_v1.2.0.md`
