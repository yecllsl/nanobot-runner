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
uv run nanobotrun import <path> [--force]         # 导入FIT
uv run nanobotrun stats [--year YYYY | --start DATE --end DATE]
uv run nanobotrun chat                            # Agent交互

# 测试
uv run pytest                                     # 全部测试（默认 --cov）
uv run pytest tests/unit/                         # 单元测试
uv run pytest tests/integration/                  # 集成测试
uv run pytest tests/e2e/                          # 端到端
uv run pytest tests/performance/                  # 性能测试
uv run pytest -k "test_calculate_vdot"            # 按关键字匹配
uv run pytest tests/unit/test_analytics.py::TestAnalyticsEngine::test_calculate_vdot_success  # 单个测试函数
uv run pytest -m "not slow"                       # 排除慢速测试
uv run pytest --no-cov                            # 无覆盖率

# 代码质量（CI 强制执行）
uv run black src tests                            # 格式化 (line-length=88)
uv run isort src tests                            # 导入排序 (profile=black)
uv run mypy src                                   # 类型检查
uv run bandit -r src                              # 安全扫描 (跳过 B101, B601)

# 构建
uv build                                          # 产物在 dist/
```

## 代码风格

### 导入顺序 (isort profile=black)

```python
# 1. 标准库    2. 第三方库    3. 本地 (src.*)
import logging
from typing import TYPE_CHECKING, Any, Optional

import polars as pl
from rich.console import Console

from src.core.storage import StorageManager

# 循环导入: TYPE_CHECKING 块 + 字符串类型注解
if TYPE_CHECKING:
    from src.core.storage import StorageManager
```

### 命名约定

类名 PascalCase (`StorageManager`)；函数/变量 snake_case (`calculate_vdot`)；常量 UPPER_SNAKE_CASE (`VDOT_COEFFICIENT`)；私有 `_leading_underscore`；测试类 `Test{ClassName}`；测试函数 `test_{action}_{case}`

### 类型注解

- mypy 宽松：`warn_return_any=false`, `disallow_untyped_defs=false`；新代码建议加注解
- Polars：`pl.Series`, `pl.DataFrame`, `pl.LazyFrame`；循环引用用 `TYPE_CHECKING` + 字符串注解

### 错误处理

```python
# 自定义异常继承 NanobotRunnerError (dataclass, 含 error_code + recovery_suggestion)
@dataclass
class StorageError(NanobotRunnerError):
    error_code: str = "STORAGE_ERROR"

# 核心逻辑: raise ... from e
raise ValueError("距离和时间必须为正数")

# 工具层: @handle_tool_errors 装饰器 (返回 dict)
@handle_tool_errors(default_response={"error": "操作失败"})
async def execute(self, **kwargs): ...
```

### Docstring

```python
def method(self, distance_m: float, time_s: float) -> float:
    """计算VDOT值

    Args:  distance_m: 距离（米）   time_s: 用时（秒）
    Returns: float: VDOT值
    Raises:  ValueError: 当距离或时间为非正数
    """
```

### Polars

- 读取：`pl.scan_parquet()` → LazyFrame；写入：`.collect().write_parquet(path, compression='snappy')`
- 合并用 `pl.concat()`；类型 Object → String 以兼容 Parquet；常量提取为模块级变量

## 项目架构

```
src/
├── core/            # parser, storage, indexer, importer, analytics, profile, config, schema, exceptions, decorators
├── agents/tools.py  # BaseTool + RunnerTools (Agent工具集)
├── notify/feishu.py # FeishuBot (飞书推送)
├── cli.py           # Typer CLI 入口
└── cli_formatter.py # Rich 格式化输出

tests/
├── unit/            # 单元测试
├── integration/     # 集成测试 (module/, scene/)
├── e2e/             # 端到端测试
└── performance/     # 性能测试
```

### 数据流

- **导入**: FIT → `FitParser.parse_file()` → `IndexManager`(SHA256去重) → `StorageManager.save_to_parquet()`(按年分片)
- **查询**: `StorageManager.read_parquet()` → LazyFrame → `AnalyticsEngine` → `RunnerTools`

### 新增 Agent 工具

1. 继承 `BaseTool`，实现 `name`、`description`、`parameters`、`execute()`
2. `parameters` 用 OpenAI function calling schema
3. 在 `RunnerTools` 中注册，更新 `TOOL_DESCRIPTIONS`

### 装饰器

`@handle_tool_errors`（异常→dict）、`@handle_errors`（统一错误）、`@require_storage`（存储初始化）、`@handle_empty_data`（空数据兜底）

## 数据存储

### 目录结构

**nanobot-ai 框架配置** (`~/.nanobot/`):
- `config.json` - LLM Provider、飞书通道、Gateway 等框架配置
- `cron/` - 定时任务存储（框架功能）
- `bridge/` - 通道桥接数据
- `history/` - 框架历史记录

**nanobotrun 业务配置** (`~/.nanobot-runner/` 作为 workspace):
- `config.json` - 业务配置（数据目录、飞书Webhook等）
- `data/` - 跑步数据（Parquet文件、画像等）
- `memory/` - Agent 记忆文件（MEMORY.md）
- `sessions/` - 会话记录
- `AGENTS.md`, `SOUL.md`, `USER.md` - Agent 配置文件

### 配置分离原则

| 类型 | 位置 | 说明 |
|------|------|------|
| LLM Provider | `~/.nanobot/config.json` | 框架级配置 |
| 飞书通道 | `~/.nanobot/config.json` | 框架级配置 |
| Gateway | `~/.nanobot/config.json` | 框架级配置 |
| 定时任务 | `~/.nanobot/cron/` | 框架功能 |
| 跑步数据 | `~/.nanobot-runner/data/` | 业务数据 |
| 用户画像 | `~/.nanobot-runner/data/` | 业务数据 |
| Agent记忆 | `~/.nanobot-runner/memory/` | 业务数据 |

**重要**: `~/.nanobot-runner` 作为 nanobot-ai 的 workspace，存储业务相关数据和配置；框架级配置必须在 `~/.nanobot/` 中。

### 数据文件

`~/.nanobot-runner/data/activities_{year}.parquet` (snappy, 按年分片)
`~/.nanobot-runner/data/index.json` (SHA256去重)
`~/.nanobot-runner/config.json` (业务配置)

Schema 必填: `activity_id`, `timestamp`, `source_file`, `filename`, `total_distance`, `total_timer_time`

## CI/CD

1. **code-quality**: black, isort, mypy, bandit
2. **test**: pytest (Python 3.11/3.12 矩阵)
3. **build**: 构建 wheel/sdist
4. **release**: main 分支打 tag → GitHub Release

## 常见问题

```bash
uv cache clean; uv sync --reinstall               # 依赖问题
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser  # Win PS激活
# Windows 多命令: 用 "; if($?) { cmd }" 替代 "&&"
```
