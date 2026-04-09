# AGENTS.md

> Agent 工作指南 - Nanobot Runner

**核心栈**: Python 3.11+, nanobot-ai, Typer+Rich CLI, Polars, Parquet, fitparse

---

## 1. 项目定义与角色

> **Nanobot Runner** 是一个处理个人跑步数据（主要是 FIT 文件）的桌面端 CLI 工具，核心价值是将枯燥的跑表数据转化为可分析的洞察，并通过 Agent 提供交互式问答。
>
> **你的角色**：精通 Python 数据工程（Polars/Parquet）和 CLI 开发的资深工程师。你在修改代码时，始终将**数据一致性**和**执行性能**放在首位。

**业务边界**：仅处理单用户本地跑步数据，不支持多租户、Web UI、云端存储、实时流处理。

---

## 2. 项目结构

**v0.9.0 架构重构**：CLI按领域拆分，引入依赖注入机制。

```
src/
├── core/                       # 核心模块
│   ├── context.py              # 应用上下文 (v0.9.0新增)
│   ├── session_repository.py   # Session仓储层 (v0.9.0新增)
│   ├── parser.py               # FIT文件解析
│   ├── storage.py              # Parquet存储管理
│   ├── indexer.py              # SHA256去重索引
│   ├── analytics.py            # 数据分析引擎
│   ├── profile.py              # 用户画像管理
│   ├── config.py               # 配置管理
│   └── exceptions.py           # 自定义异常
├── agents/tools.py             # Agent 工具集: BaseTool + RunnerTools
├── notify/                     # 飞书通知
│   ├── feishu.py
│   └── feishu_calendar.py
├── cli/                        # CLI 模块 (v0.9.0重构)
│   ├── commands/               # 命令模块
│   │   ├── data.py             # 数据管理命令
│   │   ├── analysis.py         # 数据分析命令
│   │   ├── agent.py            # Agent交互命令
│   │   ├── report.py           # 报告生成命令
│   │   ├── system.py           # 系统管理命令
│   │   └── gateway.py          # Gateway服务命令
│   ├── handlers/               # 业务逻辑调用层
│   │   ├── data_handler.py
│   │   └── analysis_handler.py
│   ├── app.py                  # CLI 应用入口
│   ├── common.py               # CLI公共组件
│   └── __main__.py             # 模块入口
└── cli_formatter.py            # Rich 格式化输出
```

---

## 3. 核心数据流

### 3.1 数据导入流程

```
FIT文件 → FitParser → IndexManager(SHA256去重) → StorageManager → Parquet(按年分片)
```

### 3.2 数据查询流程

```
用户查询 ← RunnerTools ← AnalyticsEngine ← LazyFrame ← read_parquet
```

### 3.3 依赖注入流程 (v0.9.0新增)

```
AppContextFactory.create_context()
    ↓
AppContext
    ├── storage: StorageManager
    ├── analytics: AnalyticsEngine
    ├── profile: ProfileEngine
    └── session_repo: SessionRepository
    ↓
CLI Handlers / Agent Tools
```

**使用示例**:
```python
from src.core.context import get_context

# 获取应用上下文
context = get_context()

# 访问依赖组件
storage = context.storage
analytics = context.analytics
session_repo = context.session_repo
```

---

## 4. 开发规范速查

| 规范 | 要求 |
|------|------|
| **Polars** | 保持 LazyFrame，仅最终输出时调用 `.collect()`，详见 `docs/guides/development_guide.md` |
| **依赖注入** | 使用 `get_context()` 获取应用上下文，禁止直接实例化核心组件 (v0.9.0新增) |
| **SessionRepository** | 使用类型安全的数据类（SessionSummary/SessionDetail），禁止返回 Dict[str, Any] (v0.9.0新增) |
| **异常处理** | 使用 `from src.core.exceptions import ...` 自定义异常，禁止裸 `Exception` |
| **类型注解** | 必须添加，核心模块覆盖率 ≥ 80% |
| **命名约定** | 类名 PascalCase，函数/变量 snake_case，常量 UPPER_SNAKE_CASE |

### 4.1 依赖注入规范 (v0.9.0新增)

**正确做法**:
```python
from src.core.context import get_context

def some_function():
    context = get_context()
    storage = context.storage  # ✅ 通过上下文获取
    analytics = context.analytics
```

**错误做法**:
```python
from src.core.storage import StorageManager

def some_function():
    storage = StorageManager()  # ❌ 禁止直接实例化
```

### 4.2 SessionRepository 使用规范 (v0.9.0新增)

**正确做法**:
```python
from src.core.context import get_context

context = get_context()
session_repo = context.session_repo

# 使用类型安全的返回值
summary: SessionSummary = session_repo.get_session_summary(session_id)
detail: SessionDetail = session_repo.get_session_detail(session_id)
```

**错误做法**:
```python
# 禁止返回 Dict[str, Any]
result: Dict[str, Any] = session_repo.get_session_summary(session_id)  # ❌
```

---

## 5. 常用命令

**v0.9.0 CLI分层**：命令按领域分组，格式为 `nanobotrun <domain> <command>`。

```bash
# 依赖管理
uv venv                                          # 创建虚拟环境
uv sync --all-extras                             # 同步依赖
uv cache clean; if($?) { uv sync --reinstall }   # 清理重装 (Windows)

# 数据管理
uv run nanobotrun data import-data <path> [--force]  # 导入FIT文件
uv run nanobotrun data stats [--year YYYY]           # 查看统计
uv run nanobotrun data stats --start 2024-01-01 --end 2024-12-31  # 日期范围

# 数据分析
uv run nanobotrun analysis vdot      # VDOT趋势分析
uv run nanobotrun analysis load      # 训练负荷分析
uv run nanobotrun analysis hr-drift  # 心率漂移分析

# Agent交互
uv run nanobotrun agent chat         # 启动AI助手

# 报告生成
uv run nanobotrun report weekly      # 生成周报
uv run nanobotrun report monthly     # 生成月报

# 系统管理
uv run nanobotrun system config      # 查看配置
uv run nanobotrun system version     # 查看版本

# 测试
uv run pytest tests/unit/                        # 单元测试
uv run pytest -k "test_calculate_vdot"           # 按关键字

# 代码质量
uv run black --check src/ tests/                 # 格式检查
uv run mypy src/ --ignore-missing-imports        # 类型检查
```

> **Windows PowerShell 注意**：多命令链用 `; if($?) { cmd }` 替代 `&&`

---

## 6. 详细文档索引

| 文档 | 路径 | 内容 |
|------|------|------|
| 架构设计 | `docs/architecture/架构设计说明书.md` | 系统架构、模块设计、数据流 |
| API 参考 | `docs/api/api_reference.md` | 核心类和方法签名 |
| CLI 使用 | `docs/guides/cli_usage.md` | 命令详解、参数说明 |
| Agent 配置 | `docs/guides/agent_config_guide.md` | 配置文件、路径说明 |
| 开发指南 | `docs/guides/development_guide.md` | Polars 规范、异常处理、类型注解 |
| Agent 工具扩展 | `docs/guides/agent_tools_guide.md` | 新增工具步骤、TOOL_DESCRIPTIONS |
| 测试指南 | `docs/guides/testing_guide.md` | Mock 策略、测试数据、隐私红线 |

---

## 7. 路径速查

| 类型 | 路径 |
|------|------|
| 框架配置 | `~/.nanobot/config.json` |
| 业务配置 | `~/.nanobot-runner/config.json` |
| 跑步数据 | `~/.nanobot-runner/data/activities_*.parquet` |
| 用户画像 | `~/.nanobot-runner/data/profile.json` |
| Agent 记忆 | `~/.nanobot-runner/memory/MEMORY.md` |
| 测试样本 | `tests/data/fixtures/*.fit` |

---

## 8. 提交前 Checklist

- [ ] `uv run black --check src/ tests/` 零警告
- [ ] `uv run isort --check-only src/ tests/` 零警告
- [ ] `uv run mypy src/` 无新增错误
- [ ] `uv run pytest tests/unit/` 通过率 100%
- [ ] 新增字段/工具 → 更新 Schema/TOOL_DESCRIPTIONS

---

*文档版本: v4.0.0 | 更新日期: 2026-04-09*
