# AGENTS.md

This file provides guidance to Agents when working with code in this repository.

## 项目概述

Nanobot Runner 是一款基于 nanobot-ai 底座的本地化 AI 跑步助理。核心目标是解决数据隐私与深度分析的矛盾，通过 Parquet 列式存储与 Polars 高性能计算引擎，为技术型跑者提供企业级 BI 能力。

**核心技术栈**: Python 3.11+, nanobot-ai, Typer + Rich (CLI), Polars (计算引擎), Apache Parquet (存储), fitparse (FIT解析)

## 常用命令

### 依赖管理（使用 uv）

```bash
# 创建虚拟环境
uv venv

# 激活虚拟环境（Windows PowerShell）
.venv\Scripts\Activate.ps1

# 激活虚拟环境（Windows CMD）
.venv\Scripts\activate.bat

# 激活虚拟环境（Linux/macOS）
source .venv/bin/activate

# 同步依赖（包括开发依赖）
uv sync --all-extras

# 清理缓存并重新安装
uv cache clean; if($?) { uv sync --reinstall }
```

### 运行项目

```bash
# 查看帮助
uv run nanobotrun --help

# 导入FIT文件
uv run nanobotrun import /path/to/file.fit

# 导入目录
uv run nanobotrun import /path/to/activities/

# 强制导入（跳过去重）
uv run nanobotrun import /path/to/file.fit --force

# 查看统计
uv run nanobotrun stats

# 启动Agent交互
uv run nanobotrun chat

# 查看版本
uv run nanobotrun version
```

### 测试

```bash
# 运行所有测试
uv run pytest

# 运行特定测试文件
uv run pytest tests/unit/test_storage.py

# 运行特定测试（使用 -k 匹配）
uv run pytest tests/unit/test_analytics.py -k "vdot"

# 详细输出
uv run pytest -v

# 带覆盖率报告
uv run pytest --cov=src --cov-report=term-missing --cov-report=html

# 运行单元测试
uv run pytest tests/unit/

# 运行集成测试
uv run pytest tests/integration/

# 运行端到端测试
uv run pytest tests/e2e/
```

### 代码质量工具

```bash
# 格式化代码
uv run black src tests

# 导入排序
uv run isort src tests

# 类型检查
uv run mypy src

# 安全检查
uv run bandit -r src

# 依赖安全检查
uv run safety check
```

### 构建与发布

```bash
# 构建包
uv build

# 构建产物位于 dist/ 目录
```

## 架构概述

### 目录结构

```
src/
├── core/           # 核心业务逻辑
│   ├── parser.py   # FIT文件解析器 (FitParser)
│   ├── storage.py  # Parquet存储管理 (StorageManager)
│   ├── indexer.py  # 去重索引管理 (IndexManager)
│   ├── importer.py # 数据导入服务编排 (ImportService)
│   ├── analytics.py# 数据分析引擎 (AnalyticsEngine)
│   └── config.py   # 配置管理 (ConfigManager)
├── agents/
│   └── tools.py    # Agent工具集 (RunnerTools) - 封装为nanobot-ai可识别的工具
├── notify/
│   └── feishu.py   # 飞书推送集成 (FeishuBot)
└── cli.py          # CLI入口 (Typer应用)

tests/
├── unit/           # 单元测试
├── integration/    # 集成测试
│   └── module/     # 模块集成测试
├── e2e/            # 端到端测试
├── scripts/        # 测试脚本
├── cases/          # 测试用例文档
└── data/           # 测试数据
    ├── fixtures/   # FIT测试文件
    └── validation/ # 验证数据

docs/               # 项目文档
├── architecture/   # 架构设计
├── development/    # 开发报告
├── devops/         # DevOps文档
├── planning/       # 开发计划
├── requirement/    # 需求文档
└── test/           # 测试文档
```

### 数据流

1. **导入流程**: FIT文件 → `FitParser` 解析 → `IndexManager` 指纹去重 → `StorageManager` 按年份存储到 Parquet
2. **查询流程**: `StorageManager` 读取 Parquet → `AnalyticsEngine` 分析计算 → `RunnerTools` 封装结果供 Agent 使用
3. **通知流程**: 分析结果 → `FeishuBot` 推送到飞书

### 核心组件关系

- `ImportService` 编排 `FitParser`、`IndexManager`、`StorageManager` 完成数据导入
- `AnalyticsEngine` 依赖 `StorageManager` 进行数据分析
- `RunnerTools` 作为 Agent 工具层，调用 `AnalyticsEngine` 和 `StorageManager`
- `ConfigManager` 管理全局配置和数据目录
- `FeishuBot` 负责消息推送到飞书

### 数据存储

- 数据目录: `~/.nanobot-runner/data/`
- 配置文件: `~/.nanobot-runner/config.json`
- Parquet 文件按年份分片: `activities_{year}.parquet`
- 去重索引: `index.json`（基于文件元数据的 SHA256 指纹）

## 核心功能模块

### AnalyticsEngine 分析引擎

提供以下核心分析功能：

- **VDOT计算**: 使用 Powers 公式计算跑力值
- **TSS计算**: 训练压力分数计算
- **跑步摘要统计**: 总次数、距离、时长、平均心率等
- **心率漂移分析**: 检测心率漂移拐点和相关性
- **训练负荷计算**: ATL（急性负荷）/ CTL（慢性负荷）

### RunnerTools Agent工具集

为 Agent 提供的可调用工具：

| 工具名称 | 功能描述 |
|---------|---------|
| `get_running_stats` | 获取跑步统计数据 |
| `get_recent_runs` | 获取最近跑步记录 |
| `calculate_vdot_for_run` | 计算单次VDOT值 |
| `get_vdot_trend` | 获取VDOT趋势变化 |
| `get_hr_drift_analysis` | 分析心率漂移情况 |
| `get_training_load` | 获取训练负荷（ATL/CTL） |

### FeishuBot 飞书推送

支持的消息类型：

- 文本消息 (`send_text`)
- 卡片消息 (`send_card`)
- 导入通知 (`send_import_notification`)
- 每日晨报 (`send_daily_report`)

## 开发注意事项

### Python 版本

项目要求 Python >= 3.11，因为 nanobot-ai 依赖此版本。

### Windows 兼容性

项目运行在 Windows 环境，注意以下事项：

- PowerShell 5.1 不支持 `&&` 或 `||` 命令链接
- 使用 `; if($?) { cmd }` 替代 `&&`
- 使用 `; if(-not $?) { cmd }` 替代 `||`
- 使用 `dir` 替代 `ls`，`type` 替代 `cat`

### Polars 使用

- 存储读取使用 `LazyFrame` (`scan_parquet`) 进行延迟加载，优化大文件性能
- 写入使用 `write_parquet` 配合 `compression='snappy'`
- DataFrame 合并使用 `pl.concat()`
- Polars 1.x 使用 `pl.corr()` 或 DataFrame 方法计算相关性

### FIT 文件处理

FIT 文件来自 Garmin 等运动设备，包含心率、步频、功率、轨迹等元数据。使用 fitparse 库解析。

测试数据位于 `tests/data/fixtures/`，包含：
- easy_run: 轻松跑
- tempo_run: 节奏跑
- long_run: 长跑
- interval: 间歇跑
- 边界情况: empty_file, corrupted_file, large_file

### Agent 工具定义

`RunnerTools` 类的方法和 `TOOL_DESCRIPTIONS` 字典定义了 Agent 可调用的工具。添加新工具时需要同时更新这两处。

### 配置管理

`ConfigManager` 负责管理项目配置：

- 默认配置包括：版本号、数据目录、飞书推送开关、Webhook地址
- 配置文件存储在 `~/.nanobot-runner/config.json`

## CI/CD 流程

项目使用 GitHub Actions 进行持续集成和部署：

1. **code-quality**: 代码格式检查、类型检查、安全扫描
2. **test**: 单元测试、集成测试、端到端测试（支持 Python 3.11/3.12）
3. **performance**: 性能测试
4. **build**: 构建打包
5. **release**: 发布到 GitHub Releases
6. **security**: 安全扫描报告
7. **documentation**: 文档生成

## 常见问题处理

### 依赖安装失败

```bash
# 清理缓存后重试
uv cache clean
uv sync --reinstall
```

### Windows 虚拟环境激活失败

```powershell
# 设置执行策略
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 测试运行失败

确保已安装所有测试依赖：

```bash
uv sync --all-extras
```

## 待实现功能

- [ ] Agent 自然语言交互功能集成（nanobot-ai）
- [ ] 训练负荷（TSS/ATL/CTL）完整计算
- [ ] 每日晨报内容生成
- [ ] 更多分析指标和可视化