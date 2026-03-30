# AGENTS.md

Agent 工作指南 - Nanobot Runner (桌面端私人AI跑步助理)

**核心栈**: Python 3.11+, nanobot-ai, Typer+Rich CLI, Polars, Parquet, fitparse

## 常用命令

```bash
# 依赖管理
uv venv                                          # 创建虚拟环境
uv sync --all-extras                             # 同步依赖
uv cache clean; if($?) { uv sync --reinstall }   # 清理重装 (Windows)

# 运行
uv run nanobotrun --help
uv run nanobotrun import <path> [--force]        # 导入FIT
uv run nanobotrun stats [--year YYYY | --start DATE --end DATE]
uv run nanobotrun chat                           # Agent交互

# 测试
uv run pytest                                    # 全部测试
uv run pytest tests/unit/                        # 单元测试
uv run pytest tests/integration/                 # 集成测试
uv run pytest -k "test_calculate_vdot"           # 按关键字匹配
uv run pytest --no-cov                           # 无覆盖率

# 代码质量
uv run black src tests                           # 格式化
uv run isort src tests                           # 导入排序
uv run mypy src                                  # 类型检查
uv run bandit -r src -s B101,B601                # 安全扫描

# 构建
uv build                                         # 产物在 dist/
```

## 代码风格

### 导入顺序 (isort profile=black)

```python
# 1. 标准库  2. 第三方库  3. 本地 (src.*)
import logging
from typing import TYPE_CHECKING, Any, Optional

import polars as pl
from rich.console import Console

from src.core.storage import StorageManager
```

### 命名约定

类名 PascalCase (`StorageManager`)；函数/变量 snake_case (`calculate_vdot`)；常量 UPPER_SNAKE_CASE (`VDOT_COEFFICIENT`)；私有 `_leading_underscore`；测试类 `Test{ClassName}`；测试函数 `test_{action}_{case}`

### 类型注解

**基本要求**: 新代码必须添加类型注解；核心模块类型覆盖率≥80%；工具函数必须标注参数和返回值类型。

```python
from typing import TYPE_CHECKING, Any, Optional, Union, Callable, TypeAlias

def calculate_vdot(distance_m: float, time_s: float) -> float:
    """计算VDOT值"""
    if distance_m <= 0 or time_s <= 0:
        raise ValueError("距离和时间必须为正数")
    return (distance_m / time_s) * 3.5

ActivityRecord: TypeAlias = dict[str, Union[str, int, float, datetime]]
```

### 错误处理

```python
# 自定义异常继承 NanobotRunnerError (含 error_code + recovery_suggestion)
@dataclass
class StorageError(NanobotRunnerError):
    error_code: str = "STORAGE_ERROR"

# 工具层: @handle_tool_errors 装饰器
@handle_tool_errors(default_response={"error": "操作失败"})
async def execute(self, **kwargs): ...
```

### Polars

- 读取：`pl.scan_parquet()` → LazyFrame；写入：`.collect().write_parquet(path, compression='snappy')`
- 合并用 `pl.concat()`；类型 Object → String 以兼容 Parquet

## 项目架构

```
src/
├── core/            # parser, storage, indexer, importer, analytics, profile, config, schema, exceptions, decorators
├── agents/tools.py  # BaseTool + RunnerTools (Agent工具集)
├── notify/feishu.py # FeishuBot (飞书推送)
├── cli.py           # Typer CLI 入口
└── cli_formatter.py # Rich 格式化输出
```

### 数据流

- **导入**: FIT → `FitParser.parse_file()` → `IndexManager`(SHA256去重) → `StorageManager.save_to_parquet()`(按年分片)
- **查询**: `StorageManager.read_parquet()` → LazyFrame → `AnalyticsEngine` → `RunnerTools`

### 新增 Agent 工具

1. 继承 `BaseTool`，实现 `name`、`description`、`parameters`、`execute()`
2. `parameters` 用 OpenAI function calling schema
3. 在 `RunnerTools` 中注册，更新 `TOOL_DESCRIPTIONS`

## 数据存储

### 目录结构

**nanobot-ai 框架配置** (`~/.nanobot/`): `config.json` (LLM Provider、飞书通道等)

**nanobotrun 业务配置** (`~/.nanobot-runner/` 作为 workspace):
- `config.json` - 业务配置
- `data/` - 跑步数据（Parquet文件、画像等）
- `memory/` - Agent 记忆文件（MEMORY.md）
- `AGENTS.md`, `SOUL.md`, `USER.md` - Agent 配置文件

### 配置分离原则

| 类型 | 位置 | 说明 |
|------|------|------|
| LLM Provider | `~/.nanobot/config.json` | 框架级配置 |
| 飞书通道 | `~/.nanobot/config.json` | 框架级配置 |
| 跑步数据 | `~/.nanobot-runner/data/` | 业务数据 |
| Agent记忆 | `~/.nanobot-runner/memory/` | 业务数据 |

### 数据文件

`~/.nanobot-runner/data/activities_{year}.parquet` (snappy, 按年分片)
`~/.nanobot-runner/data/index.json` (SHA256去重)

Schema 必填: `activity_id`, `timestamp`, `source_file`, `filename`, `total_distance`, `total_timer_time`

## CI/CD

### Pipeline流程

1. **code-quality**: black, isort, mypy, bandit
2. **test**: pytest (Python 3.11/3.12 矩阵)
3. **build**: 构建 wheel/sdist
4. **release**: main 分支打 tag → GitHub Release

### 质量门禁

| 检查项 | 工具 | 门禁要求 |
|--------|------|----------|
| 代码格式化 | black | 零警告 |
| 导入排序 | isort | 零警告 |
| 类型检查 | mypy | 警告可接受 |
| 安全扫描 | bandit | 高危漏洞=0 |
| 单元测试 | pytest | 通过率100% |
| 代码覆盖率 | pytest-cov | core≥80%, agents≥70%, cli≥60% |

### 本地预检查

```bash
uv run black --check src/ tests/
uv run isort --check-only src/ tests/
uv run mypy src/ --ignore-missing-imports
uv run bandit -r src/ -s B101,B601
uv run pytest tests/unit/ --cov=src --cov-fail-under=80
```

## 依赖管理

```bash
# 环境管理
uv venv                                          # 创建虚拟环境
uv sync --all-extras                             # 同步所有依赖

# 依赖维护
uv cache clean                                   # 清理缓存
uv cache clean; if($?) { uv sync --reinstall }   # 清理重装 (Windows)

# 运行命令
uv run python script.py                          # 在虚拟环境中运行
uv run pytest                                    # 运行测试
```

## 常见问题

```bash
# 依赖问题
uv cache clean; uv sync --reinstall

# Windows PowerShell激活
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Windows多命令链: 用 "; if($?) { cmd }" 替代 "&&"
```
