# Nanobot Runner

桌面端私人AI跑步助理

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Code Coverage](https://img.shields.io/badge/coverage-85%25-brightgreen.svg)](./coverage.xml)
[![Tests](https://img.shields.io/badge/tests-2570%20passed-brightgreen.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **最新版本**: v0.15.0 - 新增AI决策透明化模块（决策追踪+状态仪表盘+训练洞察报告）+ 报告导出功能

## 项目简介

Nanobot Runner 是一款基于 nanobot-ai 底座的本地化 AI 跑步助理。核心目标是解决数据隐私与深度分析的矛盾，通过 Parquet 列式存储与 Polars 高性能计算引擎，为技术型跑者提供企业级 BI 能力。

### 核心特性

- 🔒 **数据隐私**: 本地存储，零外联设计，数据完全用户可控
- 🚀 **高性能**: Polars LazyFrame 优化，查询性能提升 ≥ 20%
- 🤖 **AI 助手**: 自然语言交互，智能分析跑步数据
- 📊 **专业分析**: VDOT、TSS、心率漂移、训练负荷等专业指标
- 📱 **飞书推送**: 支持周报/月报自动推送
- ⚙️ **配置管理**: 交互式初始化向导，支持配置备份和迁移 (v0.9.4)
- 🏃 **智能跑步计划**: 数据感知层+智能调整层+预测规划层 (v0.10.0~v0.12.0)
- 🔧 **智能技能生态**: MCP工具管理，支持天气/地图/健康数据接入 (v0.13.0)
- 🔍 **AI决策透明化**: 决策追踪+状态仪表盘+训练洞察报告 (v0.15.0)
- 📄 **报告导出**: 周报/月报支持导出为Markdown文件 (v0.15.0)
- 🛠️ **开发者友好**: 完善的 API 文档和 CLI 工具

## 快速开始

### 安装

#### 方式一：一键安装（推荐）

```bash
# 一键安装
curl -fsSL https://raw.githubusercontent.com/yecllsl/nanobot-runner/main/scripts/install.sh | bash

# 指定版本安装
curl -fsSL https://raw.githubusercontent.com/yecllsl/nanobot-runner/main/scripts/install.sh | bash -s -- --version v0.15.0

# 指定安装目录
curl -fsSL https://raw.githubusercontent.com/yecllsl/nanobot-runner/main/scripts/install.sh | bash -s -- --dir ~/my-runner
```

安装脚本会自动完成：Python 环境检测 → 安装 uv → 克隆仓库 → 安装依赖 → 初始化配置目录。

> **安全提示**: 建议先下载脚本审查后再执行：
> ```bash
> curl -fsSL -o install.sh https://raw.githubusercontent.com/yecllsl/nanobot-runner/main/scripts/install.sh
> less install.sh  # 审查脚本内容
> bash install.sh
> ```

#### 方式二：手动安装

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
# 导入 FIT 文件
uv run nanobotrun data import /path/to/activity.fit

# 导入整个目录
uv run nanobotrun data import /path/to/activities/

# 强制重新导入（跳过去重）
uv run nanobotrun data import /path/to/activity.fit --force
```

### 查看统计

```bash
# 查看当前年份统计
uv run nanobotrun data stats

# 查看指定年份
uv run nanobotrun data stats --year 2024

# 查看日期范围
uv run nanobotrun data stats --start 2024-01-01 --end 2024-12-31
```

### 数据分析

```bash
# 查看 VDOT 趋势
uv run nanobotrun analysis vdot

# 查看训练负荷
uv run nanobotrun analysis load

# 分析心率漂移
uv run nanobotrun analysis hr-drift
```

### 初始化配置 (v0.9.4)

```bash
# 交互式初始化（推荐新用户使用）
uv run nanobotrun init

# 从旧版本迁移
uv run nanobotrun init --mode migrate

# 验证配置
uv run nanobotrun system validate
```

### 智能跑步计划 (v0.10.0~v0.12.0)

**三层架构设计**：数据感知层 + 智能调整层 + 预测规划层

```bash
# 创建训练计划
uv run nanobotrun plan create 42.195 2026-06-15 --vdot 42.0 --volume 35

# 记录训练反馈
uv run nanobotrun plan log <plan_id> 2024-01-15 --completion 0.8 --effort 6 --notes "体感良好"

# 查看计划统计
uv run nanobotrun plan stats <plan_id>

# 调整训练计划 (v0.11.0)
uv run nanobotrun plan adjust <plan_id> --action reduce --reason "疲劳恢复"

# 获取调整建议 (v0.11.0)
uv run nanobotrun plan suggest <plan_id>

# 目标达成评估 (v0.12.0)
uv run nanobotrun plan evaluate <plan_id>

# 生成长期规划 (v0.12.0)
uv run nanobotrun plan long-term 42.195 2026-10-15 --vdot 45.0 --volume 40 --cycles 3

# 获取智能训练建议 (v0.12.0)
uv run nanobotrun plan advice <plan_id>
```

### 工具管理 (v0.13.0)

```bash
# 列出所有已配置的工具
uv run nanobotrun tools list

# 添加 MCP 服务器
uv run nanobotrun tools add weather --command npx --args '["-y","@h1deya/mcp-server-weather"]'

# 启用/禁用工具
uv run nanobotrun tools enable weather
uv run nanobotrun tools disable weather

# 导入 Claude Desktop 配置
uv run nanobotrun tools import-claude

# 验证工具配置
uv run nanobotrun tools validate
```

### AI 交互

```bash
# 启动 AI 助手
uv run nanobotrun agent chat
```

示例对话：
```
> 我今年跑了多少次？
📊 2024年您共跑了 156 次，总距离 1,250.5 km

> 我的 VDOT 趋势如何？
📈 当前 VDOT: 45.2，呈上升趋势 (+0.5/月)

> 查看最近5次跑步
📋 [显示最近5次跑步记录]

> 生成全马破4的训练计划
🏃 已为您生成16周全马训练计划，目标完赛时间3:59:59

> 调整下周计划，减量30%
✅ 已调整下周计划，跑量从60km减少至42km

> 评估我全马破4的概率
📊 基于当前训练数据，预测完赛时间4:05:23，达成概率65%
```

## 核心功能

### 1. FIT 文件解析

底层解析 .fit 格式，提取心率、步频、功率、轨迹等元数据。支持 Garmin、Wahoo 等设备导出的文件。

### 2. 高效存储

采用 Apache Parquet 列式存储格式：
- 高压缩比（典型 3:1 ~ 5:1）
- 适配 OLAP 分析场景
- 按年份分区，高效查询

### 3. 智能去重

基于文件 SHA256 指纹的智能去重机制，确保幂等性导入。

### 4. 数据分析引擎

基于 Polars 的高性能数据分析引擎，支持：

| 指标 | 说明 |
|------|------|
| **VDOT** | 跑力值评估（Powers 公式，距离≥1500m） |
| **TSS** | 训练压力分数（时长×IF²×100） |
| **ATL/CTL** | 急/慢性训练负荷（7天/42天 EWMA） |
| **TSB** | 训练压力平衡 |
| **心率漂移** | 有氧能力评估（相关性<-0.7判定为漂移） |
| **配速分布** | 训练强度区间分析 |

### 5. Agent 交互

支持自然语言查询：
- "我今年跑了多少次？"
- "我的 VDOT 趋势如何？"
- "查看最近10次跑步"
- "分析这次跑步的心率漂移"

### 6. 飞书推送

支持周报/月报自动推送到飞书，使用飞书应用机器人：

```json
{
  "feishu_app_id": "your_app_id",
  "feishu_app_secret": "your_app_secret",
  "feishu_receive_id": "your_user_id"
}
```

## 技术栈

- **核心底座**: nanobot-ai
- **开发语言**: Python 3.11+
- **CLI 框架**: Typer + Rich
- **数据存储**: Apache Parquet (via pyarrow)
- **计算引擎**: Polars (LazyFrame 优化)
- **数据解析**: fitparse

## 项目结构

```
nanobot-runner/
├── src/
│   ├── core/              # 核心业务逻辑
│   │   ├── analytics/     # 数据分析引擎（v0.9.0 拆分）
│   │   ├── storage/       # 存储管理（含 SessionRepository）
│   │   ├── context.py     # 应用上下文（依赖注入）
│   │   ├── importer.py    # 数据导入服务
│   │   ├── parser.py      # FIT 解析封装
│   │   ├── logger.py      # 结构化日志
│   │   ├── exceptions.py  # 异常处理
│   │   └── decorators.py  # 装饰器
│   ├── cli/               # CLI 模块（v0.9.0 拆分）
│   │   ├── app.py         # CLI 入口
│   │   ├── commands/      # 命令定义
│   │   │   ├── data.py    # 数据管理命令
│   │   │   ├── analysis.py # 数据分析命令
│   │   │   ├── agent.py   # Agent 交互命令
│   │   │   ├── report.py  # 报告生成命令
│   │   │   ├── system.py  # 系统管理命令
│   │   │   └── gateway.py # 网关服务命令
│   │   ├── handlers/      # 业务逻辑调用层
│   │   └── common.py      # CLI 公共组件
│   ├── agents/            # Agent 定义
│   │   └── tools.py       # Agent 工具集
│   ├── notify/            # 通知模块
│   │   └── feishu.py      # 飞书推送集成
│   └── cli/               # CLI 模块
│       └── formatter.py   # CLI 格式化（v0.9.0 迁移）
├── tests/                 # 测试
│   ├── unit/              # 单元测试
│   ├── integration/       # 集成测试
│   ├── e2e/               # 端到端测试
│   └── performance/       # 性能测试
├── docs/                  # 文档
│   └── current/           # 当前版本文档
├── data/                  # 本地数据目录
├── pyproject.toml         # 项目配置
├── CHANGELOG.md           # 更新日志
└── README.md              # 项目说明
```

## 文档

### API 参考

- [AnalyticsEngine API](./docs/api/analytics_engine.md) - 数据分析引擎
- [StorageManager API](./docs/api/storage_manager.md) - 存储管理器
- [RunnerTools API](./docs/api/runner_tools.md) - Agent 工具集
- [API Reference](./docs/api/api_reference.md) - 完整 API 参考

### 用户指南

- [CLI 使用指南](./docs/guides/cli_usage.md) - 完整命令行使用说明
- [Agent 配置指南](./docs/guides/agent_config_guide.md) - Agent 配置说明

### 架构与流程

- [架构设计说明书](./docs/architecture/架构设计说明书.md) - 系统架构设计
- [需求规格说明书](./docs/requirements/REQ_需求规格说明书.md) - 功能需求说明

### DevOps

- [发布检查清单](./docs/devops/release_checklist.md) - 发布流程检查
- [分支管理与发布流程规范](./docs/devops/分支管理与发布流程规范.md) - Git 工作流

## 开发

### 依赖注入（v0.9.0 新增）

Nanobot Runner v0.9.0 引入了依赖注入机制，便于测试和扩展：

```python
from src.core.context import AppContextFactory

# 创建应用上下文
ctx = AppContextFactory.create()

# 获取核心组件
storage = ctx.storage
config = ctx.config
analytics = ctx.analytics

# 自定义依赖注入（用于测试）
from unittest.mock import Mock

mock_storage = Mock()
ctx = AppContextFactory.create(storage=mock_storage)
```

### 运行测试

```bash
# 运行所有测试
uv run pytest

# 运行测试并生成覆盖率报告
uv run pytest --cov=src --cov-report=term-missing --cov-report=html

# 运行特定测试
uv run pytest tests/unit/test_analytics.py -v

# 运行单元测试（覆盖率要求80%）
uv run pytest tests/unit/ --cov=src --cov-fail-under=80
```

### 代码质量

```bash
# 代码格式化
uv run ruff format src/ tests/

# 代码质量检查
uv run ruff check src/ tests/

# 自动修复问题
uv run ruff check --fix src/ tests/

# 类型检查
uv run mypy src/ --ignore-missing-imports

# 安全扫描
uv run bandit -r src/ -s B101,B601
```

### 质量门禁

| 检查项 | 工具 | 门禁要求 |
|--------|------|----------|
| 代码格式化 | ruff format | 零警告 |
| 代码质量 | ruff check | 零警告 |
| 类型检查 | mypy | 警告可接受 |
| 安全扫描 | bandit | 高危漏洞=0 |
| 单元测试 | pytest | 通过率100% |
| 代码覆盖率 | pytest-cov | core≥80%, agents≥70%, cli≥60% |

## 数据存储

### 目录结构

```
~/.nanobot-runner/
├── data/                    # 业务数据存储
│   ├── activities_*.parquet # 运动数据（按年分片）
│   ├── profile.json         # 结构化画像数据
│   └── index.json           # 去重索引
├── memory/                  # 记忆系统
│   ├── MEMORY.md            # 长期记忆/用户画像
│   └── HISTORY.md           # 事件日志
├── sessions/                # 会话历史
├── AGENTS.md                # Agent行为准则
├── SOUL.md                  # 人格设定
├── USER.md                  # 用户画像
└── config.json              # 应用配置
```

### 配置分离

| 类型 | 位置 | 说明 |
|------|------|------|
| LLM Provider | `~/.nanobot/config.json` | 框架级配置 |
| 飞书通道 | `~/.nanobot/config.json` | 框架级配置 |
| 跑步数据 | `~/.nanobot-runner/data/` | 业务数据 |
| Agent记忆 | `~/.nanobot-runner/memory/` | 业务数据 |

## 常见问题

### Windows PowerShell 执行策略

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 依赖问题解决

```bash
# 清理缓存并重新安装
uv cache clean; if($?) { uv sync --reinstall }  # Windows
uv cache clean && uv sync --reinstall           # Linux/macOS
```

## 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

---

**版本**: v0.12.0
**最后更新**: 2026-04-19
