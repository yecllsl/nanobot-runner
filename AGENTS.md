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

```
src/
├── core/            # 核心模块: parser, storage, indexer, analytics, profile, config, exceptions...
├── agents/tools.py  # Agent 工具集: BaseTool + RunnerTools
├── notify/          # 飞书通知: feishu.py, feishu_calendar.py
├── cli.py           # CLI 入口
└── cli_formatter.py # Rich 格式化输出
```

---

## 3. 核心数据流

```
FIT文件 → FitParser → IndexManager(SHA256去重) → StorageManager → Parquet(按年分片)
                                                    ↓
用户查询 ← RunnerTools ← AnalyticsEngine ← LazyFrame ← read_parquet
```

---

## 4. 开发规范速查

| 规范 | 要求 |
|------|------|
| **Polars** | 保持 LazyFrame，仅最终输出时调用 `.collect()`，详见 `docs/guides/development_guide.md` |
| **异常处理** | 使用 `from src.core.exceptions import ...` 自定义异常，禁止裸 `Exception` |
| **类型注解** | 必须添加，核心模块覆盖率 ≥ 80% |
| **命名约定** | 类名 PascalCase，函数/变量 snake_case，常量 UPPER_SNAKE_CASE |

---

## 5. 常用命令

```bash
# 依赖管理
uv venv                                          # 创建虚拟环境
uv sync --all-extras                             # 同步依赖
uv cache clean; if($?) { uv sync --reinstall }   # 清理重装 (Windows)

# 运行
uv run nanobotrun --help
uv run nanobotrun import-data <path> [--force]
uv run nanobotrun stats [--year YYYY]
uv run nanobotrun chat

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

*文档版本: v3.0.0 | 更新日期: 2026-04-01*
