# Nanobot Runner

桌面端私人AI跑步助理

## 项目简介

Nanobot Runner 是一款基于 nanobot-ai 底座的本地化 AI 跑步助理。核心目标是解决数据隐私与深度分析的矛盾，通过 Parquet 列式存储与 Polars 高性能计算引擎，为技术型跑者提供企业级 BI 能力。

## 核心功能

- **FIT文件解析**: 底层解析 .fit 格式，提取心率、步频、功率、轨迹等元数据
- **高效存储**: 采用 Parquet 列式存储格式，高压缩比，适配OLAP分析场景
- **去重导入**: 基于文件指纹的智能去重机制，确保幂等性
- **CLI控制台**: 命令行界面，支持数据导入、统计查询
- **Polars分析引擎**: 基于 Polars 的高性能数据分析引擎
- **Agent交互**: 支持自然语言查询
- **飞书推送**: 支持消息推送和通知

## 技术栈

- **核心底座**: nanobot-ai
- **开发语言**: Python 3.10+
- **CLI框架**: Typer + Rich
- **数据存储**: Apache Parquet (via pyarrow)
- **计算引擎**: Polars
- **数据解析**: fitparse

## 安装

### 使用 uv 安装（推荐）

本项目使用 [uv](https://github.com/astral-sh/uv) 作为依赖管理工具，提供快速、可靠的依赖解析和虚拟环境管理。

#### 安装 uv

如果尚未安装 uv，请访问 [uv 官网](https://github.com/astral-sh/uv) 获取安装方法。

#### 创建虚拟环境

```bash
# 使用 uv 创建虚拟环境
uv venv

# 激活虚拟环境（Windows PowerShell）
.venv\Scripts\Activate.ps1

# 激活虚拟环境（Windows CMD）
.venv\Scripts\activate.bat

# 激活虚拟环境（Linux/macOS）
source .venv/bin/activate
```

#### 安装依赖

```bash
# 同步所有依赖（包括可选依赖）
uv sync

# 或者安装开发依赖
uv sync --all-extras
```

#### 运行项目

```bash
# 使用 uv run 运行命令
uv run nanobotrun --help
uv run nanobotrun import /path/to/fit/file.fit
uv run nanobotrun stats
uv run nanobotrun chat
```

#### 运行测试

```bash
# 运行所有测试
uv run pytest

# 运行测试并生成覆盖率报告
uv run pytest --cov=src

# 运行特定测试文件
uv run pytest tests/unit/test_storage.py
```

### 传统 pip 安装（不推荐）

```bash
# 克隆项目
git clone <repository-url>
cd nanobot-runner

# 创建虚拟环境（可选但推荐）
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
pip install -e .

# 安装测试依赖
pip install -e .[test]
```

## 使用

### 使用 uv 运行（推荐）

```bash
# 查看帮助
uv run nanobotrun --help

# 导入FIT文件
uv run nanobotrun import /path/to/fit/file.fit

# 导入目录
uv run nanobotrun import /path/to/activities/

# 查看统计
uv run nanobotrun stats

# 启动Agent交互
uv run nanobotrun chat
```

### 使用 pip 运行（不推荐）

```bash
# 激活虚拟环境
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 查看帮助
nanobotrun --help

# 导入FIT文件
nanobotrun import /path/to/fit/file.fit

# 导入目录
nanobotrun import /path/to/activities/

# 查看统计
nanobotrun stats

# 启动Agent交互
nanobotrun chat
```

## 项目结构

```
nanobot-runner/
├── .venv/                 # uv 虚拟环境（自动生成）
├── src/
│   ├── core/              # 核心业务逻辑
│   │   ├── parser.py      # FIT解析封装
│   │   ├── storage.py     # Parquet读写管理
│   │   ├── indexer.py     # 去重索引管理
│   │   ├── importer.py    # 数据导入服务
│   │   └── analytics.py   # 分析引擎
│   ├── agents/            # Agent 定义
│   │   └── tools.py       # Agent 可调用的工具集
│   ├── notify/            # 通知模块
│   │   └── feishu.py      # 飞书推送集成
│   └── cli.py             # CLI 入口
├── tests/                 # 测试
│   ├── unit/              # 单元测试
│   └── integration/       # 集成测试
├── data/                  # 本地数据目录
├── docs/                  # 文档
├── pyproject.toml         # 项目配置与依赖定义
└── README.md              # 项目说明文档
```

## 开发

### 使用 uv 开发（推荐）

```bash
# 安装开发依赖
uv sync --all-extras

# 运行测试
uv run pytest

# 运行测试并生成覆盖率报告
uv run pytest --cov=src --cov-report=term-missing --cov-report=html

# 运行特定测试
uv run pytest tests/unit/test_storage.py -v
```

### 传统 pip 开发（不推荐）

```bash
# 安装开发依赖
pip install -e .[test]

# 运行测试
pytest

# 运行测试并生成覆盖率报告
pytest --cov=src
```

## 数据隐私

- 所有数据存储在本地 `~/.nanobot-runner/` 目录
- 默认零外联，不上传任何原始数据
- 仅在配置飞书推送时发送摘要消息

## 常见问题

### 1. uv 安装依赖失败

**问题**: `No solution found when resolving dependencies`

**解决方案**:
- 确保 Python 版本 >= 3.11（nanobot-ai 要求）
- 检查 `pyproject.toml` 中的 `requires-python` 设置
- 清理缓存后重试：`uv cache clean && uv sync`

### 2. 虚拟环境激活失败（Windows）

**问题**: `Activate.ps1 cannot be loaded`

**解决方案**:
```powershell
# 设置执行策略
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 然后激活
.venv\Scripts\Activate.ps1
```

### 3. 依赖版本冲突

**问题**: 多个包版本不兼容

**解决方案**:
```bash
# 清理缓存
uv cache clean

# 重新同步
uv sync --reinstall

# 或者指定版本
uv add package-name==x.y.z
```

### 4. pytest 运行失败

**问题**: `pytest: command not found`

**解决方案**:
```bash
# 确保已安装测试依赖
uv sync --all-extras

# 或者使用 uv run
uv run pytest
```

## 许可证

MIT License
