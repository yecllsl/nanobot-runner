# 更新日志

本文档记录 Nanobot Runner 的所有重要变更。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

> **历史版本归档**: [docs/archive/changelog/](docs/archive/changelog/)

---

## [0.16.1] - 2026-04-29

### Bug修复

#### 测试目录结构重构
- 重构测试目录结构以对齐源码结构
- 测试文件路径从 `tests/unit/{模块}/` 迁移到 `tests/unit/core/{模块}/`
- 提升代码可维护性和可读性

### 版本更新
- `pyproject.toml`: 0.16.0 → 0.16.1

---

## [0.16.0] - 2026-04-29

### 架构重构

#### Core 模块化重构
- **base/**: 基础设施模块 - 异常体系、日志管理、装饰器、结果模型、数据校验模式、上下文管理、用户档案
- **calculators/**: 计算器模块 - VDOT计算、比赛预测、心率分析、训练负荷分析、训练历史分析、伤病风险分析、统计聚合
- **config/**: 配置模块 - 配置管理、配置模式、LLM配置、环境变量管理、备份管理、配置同步
- **storage/**: 存储模块 - Parquet存储管理、会话仓库、索引管理、FIT解析、导入服务
- **report/**: 报告模块 - 报告生成、报告服务、异常数据过滤
- **models/**: 模型模块 - 用户档案模型、训练计划模型、分析相关模型（从1200+行大文件拆分）

#### 向后兼容
- 所有 `__init__.py` 提供完整的公共 API 重导出
- 模块间导入路径已正确更新
- 无破坏性变更

### 测试覆盖
- 单元测试 2749 个，通过率 100%
- 集成测试 272 个，通过率 100%
- E2E测试 80 个，通过率 100%
- 整体覆盖率 82%

### 质量门禁
- ruff format/check 通过
- mypy 类型检查 0 错误
- bandit 安全扫描通过（15个低风险历史遗留告警）

---

## [0.15.0] - 2026-04-28

### 新增功能

#### AI 决策透明化模块
- **透明化引擎**: 决策过程追踪、工具调用追踪、决策链路可视化
- **可观测性管理器**: AI 状态仪表盘、训练洞察报告、性能指标采集
- **追踪日志器**: 结构化决策树日志、多层级嵌套追踪、日志持久化
- **透明化展示**: Rich 表格展示、Markdown 洞察报告、时间线展示

#### 报告导出功能增强
- `report generate --output` 支持周报/月报导出为 Markdown 文件

#### 核心解析器增强
- 新增 Mock 文件检测，提升 FIT 解析健壮性

### CLI 命令扩展
- `nanobotrun transparency trace` - 查看 AI 决策追踪日志
- `nanobotrun transparency status` - 查看 AI 状态仪表盘
- `nanobotrun transparency insight` - 生成训练洞察报告
- `nanobotrun report generate --type weekly/monthly --output` - 导出报告

### 架构改进
- 新增 `src/core/transparency/` 模块，通过 Hook 机制无侵入式接入 AI 决策流程

### 测试覆盖
- 新增 73 个测试用例，整体通过率 100%
- 透明化引擎覆盖率 92%，可观测性管理器 80%

### CI/CD 修复
- 修复清华镜像源 403 错误（设为非默认源）
- 修复 ANSI 转义码导致测试失败问题
- 修复 Python 3.12 测试依赖安装失败问题

---

## [0.13.0] - 2026-04-27

### 新增功能

#### 智能技能生态版
- **MCP 工具管理基础设施**: ToolManager、MCPConfigHelper、自动发现/注册
- **天气 Agent 工具**: 自然语言天气查询、训练计划集成
- **地图 Agent 工具**: 路线规划、路线分析
- **健康数据 Agent 工具**: COROS 睡眠/HRV 数据同步与分析

#### CLI 工具管理命令
- `tools list/add/remove/enable/disable/import-claude/validate`

### 测试覆盖
- 新增 102+ 单元测试，工具管理器覆盖率 95%

---

## [0.12.0] - 2026-04-19

### 新增功能

#### 预测规划层
- **目标达成评估引擎**: 全马/半马完赛时间预测、置信区间、风险提示
- **长期周期规划引擎**: 多周期训练计划（基础期→进展期→巅峰期→比赛期→恢复期）
- **智能建议引擎**: 训练不足/过量风险识别、有氧基础检测、个性化建议

#### Agent 工具扩展
- GenerateLongTermPlanTool、EvaluateGoalAchievementTool、GetSmartAdviceTool

### 测试覆盖
- 新增 50+ 单元测试，目标预测引擎覆盖率 100%

---

## 历史版本

| 版本 | 日期 | 核心内容 |
|------|------|---------|
| [0.11.0](docs/archive/changelog/CHANGELOG_v0.11.0_and_older.md#0110---2026-04-19) | 2026-04-19 | 智能调整层、计划调整校验器、Prompt 模板引擎 |
| [0.10.0](docs/archive/changelog/CHANGELOG_v0.11.0_and_older.md#0100---2026-04-19) | 2026-04-19 | 数据感知层、训练响应分析器、计划执行仓储 |
| [0.9.5](docs/archive/changelog/CHANGELOG_v0.11.0_and_older.md#095---2026-04-20) | 2026-04-20 | Gateway 服务增强、智谱 AI 支持、数据查询优化 |
| [0.9.4](docs/archive/changelog/CHANGELOG_v0.11.0_and_older.md#094---2026-04-18) | 2026-04-18 | 配置管理基础设施、初始化向导、数据迁移引擎 |
| [0.9.3](docs/archive/changelog/CHANGELOG_v0.11.0_and_older.md#093---2026-04-15) | 2026-04-15 | 报告生成、飞书 Gateway 重构、领域模型统一 |
| [0.9.2](docs/archive/changelog/CHANGELOG_v0.11.0_and_older.md#092---2026-04-11) | 2026-04-11 | AGENTS.md 重构、CI/CD 优化 |
| [0.9.1](docs/archive/changelog/CHANGELOG_v0.11.0_and_older.md#091---2026-04-10) | 2026-04-10 | nanobot-ai 升级至 0.1.5 |
| [0.9.0](docs/archive/changelog/CHANGELOG_v0.11.0_and_older.md#090---2026-04-09) | 2026-04-09 | 依赖注入机制、SessionRepository 仓储层、CLI 架构重构 |

---

**完整历史版本详情**: [docs/archive/changelog/CHANGELOG_v0.11.0_and_older.md](docs/archive/changelog/CHANGELOG_v0.11.0_and_older.md)
