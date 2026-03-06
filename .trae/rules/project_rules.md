---
alwaysApply: false
description: 业务规则、审查维度、输出格式规范。与 AGENTS.md（AI操作说明）配合使用。
---
# Project Rules - Nanobot Runner

## 业务规则

**计算**: VDOT(Powers公式,距离>=1500m) | TSS(时长×IF²×100) | 心率漂移(相关性<-0.7) | ATL/CTL(指数加权)

**存储**: Parquet按年分片 | SHA256去重 | 必填: activity_id, timestamp, source_file, filename, total_distance, total_timer_time

## 审查维度

**必检**: 功能正确性 | 边界处理(None vs异常) | Polars LazyFrame | 类型注解 | 单元测试

**命名**: 类PascalCase, 函数snake_case, 常量UPPER_SNAKE_CASE

**CI**: black→isort→mypy→bandit→pytest

## 输出格式
**CLI**: 时长HH:MM:SS | 配速M'SS"/km | 📊统计 ✅成功 ❌错误

**Agent**: JSON含success/data/message或error/details

## 技术约束
**Windows**: 禁用&&/||, 用`cmd1; if($?) {cmd2}` | 禁用ls/cat/grep, 用dir/type/findstr

**Polars**: 读取用scan_parquet(LazyFrame) | 写入用compression="snappy"

## 禁止项
❌硬编码敏感信息 | ❌print调试(用logger) | ❌修改已存储Parquet | ❌测试未通过合并

## 覆盖率
core≥80% | agents≥70% | cli≥60%

## Commit格式
`<type>(<scope>): <subject>` (feat/fix/docs/refactor/test/chore)