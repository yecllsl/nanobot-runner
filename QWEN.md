# QWEN.md - 项目上下文指南

## 项目概述

**Nanobot Runner** 是一款基于 nanobot-ai 底座的本地化 AI 跑步助理。核心目标是通过 Parquet 列式存储与 Polars 高性能计算引擎，为技术型跑者提供企业级 BI 能力，同时保证数据隐私。

### 核心技术栈

| 类别 | 技术 |
|------|------|
| **开发语言** | Python 3.11+ |
| **核心底座** | nanobot-ai (>=0.1.4) |
| **CLI 框架** | Typer + Rich |
| **数据存储** | Apache Parquet (via pyarrow) |
| **计算引擎** | Polars (>=0.20.0) |
| **数据解析** | fitparse (>=1.1.0) |

### 核心功能

- **FIT 文件解析**: 底层解析 .fit 格式，提取心率、步频、功率、轨迹等元数据
- **高效存储**: Parquet 列式存储，按年份分片，snappy 压缩
- **去重导入**: 基于文件指纹 (SHA256) 的智能去重机制
- **CLI 控制台**: 支持数据导入、统计查询、Agent 交互
- **Polars 分析引擎**: 高性能数据分析（VDOT、心率漂移等）
- **飞书推送**: 支持消息推送和通知

---

## 项目结构

```
RunFlowAgent/
├── src/
│   ├── core/              # 核心业务逻辑
│   │   ├── parser.py      # FitParser - FIT 文件解析
│   │   ├── storage.py     # StorageManager - Parquet 存储管理
│   │   ├── indexer.py     # IndexManager - 去重索引管理
│   │   ├── importer.py    # ImportService - 数据导入编排
│   │   ├── analytics.py   # AnalyticsEngine - 分析引擎
│   │   └── config.py      # ConfigManager - 配置管理
│   ├── agents/
│   │   ├── __init__.py
│   │   └── tools.py       # RunnerTools - Agent 工具集
│   ├── notify/
│   │   ├── __init__.py
│   │   └── feishu.py      # FeishuBot - 飞书推送
│   ├── __init__.py
│   └── cli.py             # CLI 入口 (Typer 应用)
├── tests/
│   ├── unit/              # 单元测试
│   ├── integration/       # 集成测试
│   ├── e2e/               # 端到端测试
│   └── data/fixtures/     # 测试数据
├── data/                  # 本地数据目录
├── docs/                  # 文档
├── pyproject.toml         # 项目配置
└── README.md              # 项目说明
```

---

## 架构设计

### 数据流

```
FIT 文件 → FitParser 解析 → IndexManager 指纹去重 → StorageManager 存储到 Parquet
                                           ↓
Agent 查询 ← RunnerTools 封装 ← AnalyticsEngine 分析 ← StorageManager 读取
```

### 核心组件关系

| 组件 | 职责 | 依赖 |
|------|------|------|
| `ImportService` | 编排数据导入流程 | `FitParser`, `IndexManager`, `StorageManager` |
| `FitParser` | 解析 FIT 文件 | `fitparse`, `polars` |
| `IndexManager` | 管理去重索引 | 基于文件元数据的 SHA256 指纹 |
| `StorageManager` | Parquet 读写 | `polars`, `pyarrow` |
| `AnalyticsEngine` | 数据分析计算 | `StorageManager`, `polars` |
| `RunnerTools` | Agent 工具层 | `AnalyticsEngine`, `StorageManager` |
| `FeishuBot` | 飞书消息推送 | - |

### 数据存储规范

- **数据目录**: `~/.nanobot-runner/data/`
- **文件命名**: `activities_{year}.parquet`（按年份分片）
- **压缩方式**: `snappy`
- **读取方式**: `LazyFrame` 延迟加载（优化大文件性能）
- **去重索引**: `index.json`（存储文件指纹）

---

## 常用命令

### 依赖管理（使用 uv）

```bash
# 创建虚拟环境
uv venv

# 激活虚拟环境（Windows PowerShell）
.venv\Scripts\Activate.ps1

# 同步所有依赖（包括开发依赖）
uv sync --all-extras

# 清理缓存并重新安装
uv cache clean && uv sync --reinstall
```

### 运行项目

```bash
# 查看帮助
uv run nanobotrun --help

# 导入 FIT 文件
uv run nanobotrun import /path/to/file.fit

# 导入目录
uv run nanobotrun import /path/to/activities/

# 查看统计
uv run nanobotrun stats

# 启动 Agent 交互
uv run nanobotrun chat
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
```

---

## 开发注意事项

### Python 版本要求

项目要求 **Python >= 3.11**，因为 nanobot-ai 依赖此版本。

### Polars 使用规范

```python
# ✅ 推荐：使用 LazyFrame 进行延迟加载
lf = pl.scan_parquet(filepath)
df = lf.collect()

# ✅ 推荐：写入时使用 snappy 压缩
df.write_parquet(filepath, compression='snappy')

# ✅ 推荐：DataFrame 合并使用 pl.concat()
combined = pl.concat([df1, df2])

# ❌ 避免：直接读取大文件
df = pl.read_parquet(filepath)  # 仅用于小文件
```

### FIT 文件处理

FIT 文件来自 Garmin 等运动设备，包含：
- 心率 (heart_rate)
- 步频 (cadence)
- 功率 (power)
- 轨迹 (position)
- 距离 (distance)
- 时长 (duration)

使用 `fitparse` 库解析，通过 `FitParser` 类封装。

### Agent 工具定义

`RunnerTools` 类定义了 Agent 可调用的工具。添加新工具时：

1. 在 `RunnerTools` 类中添加方法
2. 在 `TOOL_DESCRIPTIONS` 字典中添加描述

```python
# src/agents/tools.py
class RunnerTools:
    def new_tool(self, param: str) -> Dict[str, Any]:
        """新工具实现"""
        pass

TOOL_DESCRIPTIONS = {
    "new_tool": {
        "description": "工具描述",
        "parameters": {"param": "参数说明"}
    }
}
```

---

## 测试规范

### 测试目录结构

```
tests/
├── unit/              # 单元测试（每个核心模块对应一个测试文件）
│   ├── test_parser.py
│   ├── test_storage.py
│   ├── test_indexer.py
│   ├── test_importer.py
│   ├── test_analytics.py
│   ├── test_tools.py
│   └── test_cli.py
├── integration/       # 集成测试
│   └── module/        # 模块间集成测试
├── e2e/               # 端到端测试
└── data/fixtures/     # 测试用 FIT 文件
```

### 测试编写规范

- 使用 `pytest` 框架
- 测试函数命名：`test_*`
- 测试文件命名：`test_*.py`
- 使用 `conftest.py` 共享 fixtures（如需要）
- 单元测试应独立，不依赖外部资源

---

## 代码风格

### 格式化规范

- **行宽**: 88 字符（Black 默认）
- **导入排序**: isort with Black profile
- **类型注解**: 使用 Python 3.10+ 语法

### 命名规范

```python
# 类名：大驼峰
class StorageManager:
    pass

# 函数/方法：小写 + 下划线
def save_to_parquet(self, dataframe: pl.DataFrame) -> bool:
    pass

# 常量：全大写
DEFAULT_YEAR = 2024

# 私有方法：单下划线前缀
def _internal_process(self):
    pass
```

### 文档字符串

```python
def method(self, param: str) -> int:
    """
    方法简短描述

    Args:
        param: 参数说明

    Returns:
        返回值说明
    """
    pass
```

---

## 常见问题

### 1. uv 安装依赖失败

**问题**: `No solution found when resolving dependencies`

**解决方案**:
```bash
# 确保 Python 版本 >= 3.11
python --version

# 清理缓存后重试
uv cache clean && uv sync
```

### 2. Windows 虚拟环境激活失败

**问题**: `Activate.ps1 cannot be loaded`

**解决方案**:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.venv\Scripts\Activate.ps1
```

### 3. pytest 运行失败

**问题**: `pytest: command not found`

**解决方案**:
```bash
# 确保已安装测试依赖
uv sync --all-extras

# 使用 uv run
uv run pytest
```

---

## 数据隐私

- 所有数据存储在本地 `~/.nanobot-runner/` 目录
- 默认零外联，不上传任何原始数据
- 仅在配置飞书推送时发送摘要消息

---

## 相关文件

- `README.md` - 项目说明文档
- `AGENTS.md` - Agent 开发指南
- `pyproject.toml` - 项目配置与依赖定义
