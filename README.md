# Nanobot Runner

桌面端私人AI跑步助理

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Code Coverage](https://img.shields.io/badge/coverage-90%25-brightgreen.svg)](./coverage.xml)
[![Tests](https://img.shields.io/badge/tests-702%20passed-brightgreen.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 项目简介

Nanobot Runner 是一款基于 nanobot-ai 底座的本地化 AI 跑步助理。核心目标是解决数据隐私与深度分析的矛盾，通过 Parquet 列式存储与 Polars 高性能计算引擎，为技术型跑者提供企业级 BI 能力。

### 核心特性

- 🔒 **数据隐私**: 本地存储，零外联设计，数据完全用户可控
- 🚀 **高性能**: Polars LazyFrame 优化，查询性能提升 ≥ 20%
- 🤖 **AI 助手**: 自然语言交互，智能分析跑步数据
- 📊 **专业分析**: VDOT、TSS、心率漂移、训练负荷等专业指标
- 📱 **飞书推送**: 支持周报/月报自动推送
- 🛠️ **开发者友好**: 完善的 API 文档和 CLI 工具

## 快速开始

### 安装

```bash
# 克隆项目
git clone <repository-url>
cd nanobot-runner

# 使用 uv 安装（推荐）
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
uv run nanobotrun import-data /path/to/activity.fit

# 导入整个目录
uv run nanobotrun import-data /path/to/activities/

# 强制重新导入（跳过去重）
uv run nanobotrun import-data /path/to/activity.fit --force
```

### 查看统计

```bash
# 查看当前年份统计
uv run nanobotrun stats

# 查看指定年份
uv run nanobotrun stats --year 2024

# 查看日期范围
uv run nanobotrun stats --start 2024-01-01 --end 2024-12-31
```

### AI 交互

```bash
# 启动 AI 助手
uv run nanobotrun chat
```

示例对话：
```
> 我今年跑了多少次？
📊 2024年您共跑了 156 次，总距离 1,250.5 km

> 我的 VDOT 趋势如何？
📈 当前 VDOT: 45.2，呈上升趋势 (+0.5/月)

> 查看最近5次跑步
📋 [显示最近5次跑步记录]
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

支持周报/月报自动推送到飞书，配置简单：

```json
{
  "feishu_webhook": "https://open.feishu.cn/open-apis/bot/v2/hook/xxx"
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
│   │   ├── analytics.py   # 数据分析引擎
│   │   ├── storage.py     # Parquet 存储管理
│   │   ├── indexer.py     # 去重索引管理
│   │   ├── importer.py    # 数据导入服务
│   │   ├── parser.py      # FIT 解析封装
│   │   ├── logger.py      # 结构化日志
│   │   ├── exceptions.py  # 异常处理
│   │   └── decorators.py  # 装饰器
│   ├── agents/            # Agent 定义
│   │   └── tools.py       # Agent 工具集
│   ├── notify/            # 通知模块
│   │   └── feishu.py      # 飞书推送集成
│   ├── cli.py             # CLI 入口
│   └── cli_formatter.py   # CLI 格式化
├── tests/                 # 测试
│   ├── unit/              # 单元测试
│   ├── integration/       # 集成测试
│   ├── e2e/               # 端到端测试
│   └── performance/       # 性能测试
├── docs/                  # 文档
│   └── current/           # 当前版本文档
├── data/                  # 本地数据目录
├── pyproject.toml         # 项目配置
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
# 格式化代码
uv run black src/ tests/

# 导入排序
uv run isort src/ tests/

# 类型检查
uv run mypy src/ --ignore-missing-imports

# 安全扫描
uv run bandit -r src/ -s B101,B601
```

### 质量门禁

| 检查项 | 工具 | 门禁要求 |
|--------|------|----------|
| 代码格式化 | black | 零警告 |
| 导入排序 | isort | 零警告 |
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

**版本**: v0.4.1  
**最后更新**: 2026-03-30
