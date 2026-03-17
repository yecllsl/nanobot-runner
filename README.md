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
uv run nanobotrun import /path/to/activity.fit

# 导入整个目录
uv run nanobotrun import /path/to/activities/
```

### 查看统计

```bash
# 查看所有统计
uv run nanobotrun stats

# 查看指定年份
uv run nanobotrun stats --year 2024
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
| **VDOT** | 跑力值评估（Powers 公式） |
| **TSS** | 训练压力分数 |
| **ATL/CTL** | 急/慢性训练负荷 |
| **TSB** | 训练压力平衡 |
| **心率漂移** | 有氧能力评估 |
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
  "feishu": {
    "enabled": true,
    "webhook_url": "https://open.feishu.cn/open-apis/bot/v2/hook/xxx"
  }
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
│   ├── api/               # API 参考文档
│   └── guides/            # 用户指南
├── data/                  # 本地数据目录
├── pyproject.toml         # 项目配置
└── README.md              # 项目说明
```

## 文档

### API 参考

- [AnalyticsEngine API](./docs/api/analytics_engine.md) - 数据分析引擎
- [StorageManager API](./docs/api/storage_manager.md) - 存储管理器
- [RunnerTools API](./docs/api/runner_tools.md) - Agent 工具集

### 用户指南

- [CLI 使用指南](./docs/guides/cli_usage.md) - 完整命令行使用说明

## 开发

### 运行测试

```bash
# 运行所有测试
uv run pytest

# 运行测试并生成覆盖率报告
uv run pytest --cov=src --cov-report=term-missing --cov-report=html

# 运行特定测试
uv run pytest tests/unit/test_analytics.py -v
```

### 代码质量

```bash
# 格式化代码
uv run black src tests
uv run isort src tests

# 类型检查
uv run mypy src

# 安全检查
uv run bandit -r src
```

### 测试覆盖率

| 模块 | 覆盖率 | 状态 |
|------|--------|------|
| `src/core/analytics.py` | 92% | ✅ |
| `src/core/decorators.py` | 100% | ✅ |
| `src/core/exceptions.py` | 100% | ✅ |
| `src/core/logger.py` | 100% | ✅ |
| `src/core/parser.py` | 99% | ✅ |
| `src/core/storage.py` | 95% | ✅ |
| `src/agents/tools.py` | 94% | ✅ |
| **总体** | **90%** | ✅ |

## 数据隐私

- 所有数据存储在本地 `~/.nanobot-runner/` 目录
- 默认零外联，不上传任何原始数据
- 仅在配置飞书推送时发送摘要消息
- 支持数据导出和备份

## 路线图

### v0.3.0

- ✅ FIT 文件导入与解析
- ✅ Parquet 存储与去重
- ✅ VDOT/TSS/心率漂移分析
- ✅ 训练负荷计算 (ATL/CTL/TSB)
- ✅ Agent 自然语言交互
- ✅ 飞书推送集成
- ✅ 结构化日志系统
- ✅ Polars LazyFrame 优化

### v0.4.0 (规划中)

- 📊 数据可视化图表
- 📅 每日晨报自动生成
- 🏃 训练计划建议
- 📈 更多分析指标
- 🌐 Web 界面

## 常见问题

### 1. uv 安装依赖失败

```bash
# 清理缓存后重试
uv cache clean
uv sync --reinstall
```

### 2. 虚拟环境激活失败（Windows）

```powershell
# 设置执行策略
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.venv\Scripts\Activate.ps1
```

### 3. 导入 FIT 文件失败

- 确认文件为有效的 FIT 格式
- 检查文件是否损坏
- 查看日志：`~/.nanobot-runner/logs/nanobot-runner.log`

更多问题请查看 [CLI 用户指南](./docs/guides/cli_usage.md#故障排查)。

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License

---

*Made with ❤️ for runners*
