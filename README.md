# Nanobot Runner

桌面端私人AI跑步助理 —— 记录跑步、预测跑步、进化跑步

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Code Coverage](https://img.shields.io/badge/coverage-81%25-brightgreen.svg)](./coverage.xml)
[![Tests](https://img.shields.io/badge/tests-3937%20passed-brightgreen.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **最新版本**: v0.25.0 - 自适应进化控制，进化触发规则引擎、提示参数调优、月度进化报告

## 项目简介

Nanobot Runner 是一款基于 nanobot-ai 底座的本地化 AI 跑步助理。核心目标是解决数据隐私与深度分析的矛盾，通过 Parquet 列式存储与 Polars 高性能计算引擎，为技术型跑者提供企业级 BI 能力。

### 核心特性

| 阶段 | 特性 | 版本 |
|------|------|------|
| 🔒 **隐私可控** | 本地存储，零外联设计，数据完全用户可控 | v0.5+ |
| 📊 **专业分析** | VDOT、TSS/ATL/CTL/TSB、心率漂移、训练负荷 | v0.8+ |
| 🤖 **AI 助手** | 自然语言交互，智能分析跑步数据 | v0.8+ |
| 🏃 **智能计划** | 数据感知+智能调整+预测规划三层架构 | v0.10-v0.12 |
| 🔍 **决策透明化** | 决策追踪+状态仪表盘+训练洞察报告 | v0.15 |
| 📊 **身体信号** | HRV分析、疲劳度评估、恢复状态监控 | v0.19 |
| 🔮 **ML增强预测** | VDOT/比赛/伤病预测，三层降级架构 | v0.20 |
| 🧬 **数字孪生** | 5维度状态向量、What-If推演、计划对比 | v0.21 |
| 🧬 **自适应进化** | 决策追踪→个性化学习→自适应进化闭环 | v0.23-v0.25 |

## 快速开始

### 安装

```bash
# 克隆项目
git clone https://github.com/yecllsl/nanobot-runner.git
cd nanobot-runner

# 使用 uv 安装
uv venv
uv sync --all-extras

# 激活虚拟环境
# Windows PowerShell
.venv\Scripts\Activate.ps1
# Linux/macOS
source .venv/bin/activate
```

### 导入数据

```bash
uv run nanobotrun data import /path/to/activity.fit
uv run nanobotrun data import /path/to/activities/       # 导入整个目录
uv run nanobotrun data import /path/to/activity.fit --force  # 强制重新导入
```

### 常用命令

```bash
# 数据统计
uv run nanobotrun data stats [--year YYYY]

# 数据分析
uv run nanobotrun analysis vdot
uv run nanobotrun analysis load
uv run nanobotrun analysis hr-drift
uv run nanobotrun analysis hrv [--days 30]
uv run nanobotrun analysis fatigue

# 身体状态
uv run nanobotrun status today
uv run nanobotrun status weekly

# 数据可视化
uv run nanobotrun viz vdot [--days 30]
uv run nanobotrun viz load [--days 90]
uv run nanobotrun viz hr-zones --start YYYY-MM-DD --end YYYY-MM-DD

# 数据导出
uv run nanobotrun export sessions --format csv/json/parquet

# 报告与计划
uv run nanobotrun report weekly
uv run nanobotrun plan create --goal "全马破4" --race-date 2024-12-01

# ML预测
uv run nanobotrun predict vdot
uv run nanobotrun predict race --distance 42.195
uv run nanobotrun predict injury-risk

# 数字孪生
uv run nanobotrun twin status
uv run nanobotrun twin simulate --plan-id <id>
uv run nanobotrun twin compare --plan-ids <id1,id2>

# 自适应进化
uv run nanobotrun evolution status
uv run nanobotrun evolution history [--days 30]
uv run nanobotrun evolution feedback <id> --score 4
uv run nanobotrun evolution accuracy [--days 30]
uv run nanobotrun evolution fidelity [--days 30]
uv run nanobotrun evolution calibration
uv run nanobotrun evolution response [--months 6]
uv run nanobotrun evolution triggers
uv run nanobotrun evolution report [--month YYYY-MM]
uv run nanobotrun evolution tune [--tone 0.7] [--detail 0.5] [--aggressive 0.3] [--data-driven 0.5]

# 系统管理
uv run nanobotrun system init
uv run nanobotrun system config
uv run nanobotrun system backup

# AI 交互
uv run nanobotrun agent chat
```

## 项目结构

```
src/
├── core/                       # 核心模块
│   ├── base/                   # 基础设施模块
│   ├── calculators/            # 计算器模块
│   ├── config/                 # 配置模块
│   ├── storage/                # 存储模块
│   ├── report/                 # 报告模块
│   ├── models/                 # 模型模块
│   ├── transparency/           # AI决策透明化模块
│   ├── plan/                   # 智能跑步计划模块
│   ├── export/                 # 数据导出模块
│   ├── visualization/          # 数据可视化模块
│   ├── analysis/               # 身体信号分析模块
│   ├── prediction/             # ML预测模块
│   ├── twin/                   # 数字孪生引擎
│   └── evolution/              # 自适应进化引擎
├── agents/                     # Agent定义与工具
├── notify/                     # 飞书通知
└── cli/                        # CLI模块
    ├── commands/               # 命令定义
    ├── handlers/               # 业务逻辑调用层
    └── app.py                  # CLI应用入口
```

## 数据存储

```
~/.nanobot-runner/
├── data/                     # 运动数据(Parquet按年分片)
├── models/                   # ML模型存储(joblib)
├── twin/                     # 孪生缓存(state_vector.json)
├── decisions/                # 决策日志(Parquet按月分片)
├── outcomes/                 # 结果记录(Parquet按月分片)
├── calibrations/             # 校准配置(JSON)
├── tuning/                   # 提示调优参数(JSON)
├── memory/                   # 记忆系统
├── sessions/                 # 会话历史
└── config.json               # 应用配置
```

## 技术栈

| 类别 | 技术 | 版本 |
|------|------|------|
| 核心底座 | nanobot-ai | Latest |
| 开发语言 | Python | 3.11+ |
| CLI框架 | Typer + Rich | Latest |
| 数据存储 | Apache Parquet | via pyarrow |
| 计算引擎 | Polars | 0.20+ |
| ML框架 | scikit-learn | 1.5+ |
| 科学计算 | scipy | 1.10+ |
| 模型解释 | shap | 0.48+ |
| 数据解析 | fitparse | Latest |
| 包管理 | uv | Latest |

## 开发

### 运行测试

```bash
uv run pytest                                    # 运行所有测试
uv run pytest tests/unit/                        # 运行单元测试
uv run pytest --cov=src --cov-report=term-missing # 覆盖率报告
```

### 代码质量

```bash
uv run ruff format src/ tests/                   # 代码格式化
uv run ruff check src/ tests/                    # 代码质量检查
uv run mypy src/ --ignore-missing-imports        # 类型检查
```

### 质量门禁

| 检查项 | 工具 | 门禁要求 |
|--------|------|----------|
| 代码格式化 | ruff format | 零警告 |
| 代码质量 | ruff check | 零警告 |
| 类型检查 | mypy | 警告可接受 |
| 单元测试 | pytest | 通过率100% |
| 代码覆盖率 | pytest-cov | core≥80% |

## 文档

| 文档 | 路径 | 内容 |
|------|------|------|
| 架构设计 | `docs/architecture/架构设计说明书.md` | 系统架构、模块设计、技术选型 |
| 需求规格 | `docs/requirements/REQ_需求规格说明书.md` | 功能需求、验收标准 |
| 产品规划 | `docs/product/产品规划方案.md` | 路线图、版本规划 |
| CLI使用 | `docs/guides/cli_usage.md` | 完整命令参考 |
| 开发指南 | `docs/guides/development_guide.md` | 编码规范、类型注解 |
| API参考 | `docs/api/api_reference.md` | API接口文档 |
| 更新日志 | `CHANGELOG.md` | 版本变更记录 |

## 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

---

**版本**: v0.25.0 | **最后更新**: 2026-05-23
