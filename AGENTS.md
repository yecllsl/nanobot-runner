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

#### 基本要求

- **新代码必须**添加类型注解，这是v0.4.1版本后的强制要求
- **核心模块**（core/、agents/）类型覆盖率目标≥80%
- **工具函数**必须标注参数类型和返回值类型
- Polars类型：`pl.Series`, `pl.DataFrame`, `pl.LazyFrame`
- 循环引用处理：使用 `TYPE_CHECKING` 块 + 字符串类型注解

#### 类型注解规范

```python
# 标准库导入
from typing import TYPE_CHECKING, Any, Optional, Union, Callable

# 函数类型注解示例
def calculate_vdot(distance_m: float, time_s: float) -> float:
    """计算VDOT值
    
    Args:
        distance_m: 距离（米），必须为正数
        time_s: 用时（秒），必须为正数
        
    Returns:
        float: VDOT值
        
    Raises:
        ValueError: 当距离或时间为非正数
    """
    if distance_m <= 0 or time_s <= 0:
        raise ValueError("距离和时间必须为正数")
    return (distance_m / time_s) * 3.5  # 简化公式

# 类方法类型注解示例
class StorageManager:
    def __init__(self, data_dir: Path, compression: str = "snappy") -> None:
        self.data_dir = data_dir
        self.compression = compression
    
    def read_parquet(
        self, 
        year: int, 
        columns: Optional[list[str]] = None
    ) -> pl.LazyFrame:
        """读取Parquet文件
        
        Args:
            year: 年份
            columns: 可选的列筛选列表
            
        Returns:
            pl.LazyFrame: 懒加载数据框
        """
        path = self.data_dir / f"activities_{year}.parquet"
        return pl.scan_parquet(path, columns=columns)
    
    def save_records(
        self, 
        records: list[dict[str, Any]], 
        year: int
    ) -> tuple[bool, str]:
        """保存记录到Parquet
        
        Args:
            records: 记录列表
            year: 年份
            
        Returns:
            tuple[bool, str]: (成功状态, 消息)
        """
        try:
            df = pl.DataFrame(records)
            path = self.data_dir / f"activities_{year}.parquet"
            df.write_parquet(path, compression=self.compression)
            return True, f"已保存 {len(records)} 条记录"
        except Exception as e:
            return False, str(e)

# 复杂类型别名
from typing import TypeAlias

ActivityRecord: TypeAlias = dict[str, Union[str, int, float, datetime]]
ConfigDict: TypeAlias = dict[str, Any]
HandlerFunc: TypeAlias = Callable[[str], bool]

# 泛型使用
from typing import TypeVar

T = TypeVar('T')

def first_or_default(items: list[T], default: T) -> T:
    """获取列表第一个元素，或默认值"""
    return items[0] if items else default
```

#### mypy配置说明

项目使用宽松的mypy配置（见pyproject.toml），但新代码应尽可能完整注解：

```toml
[tool.mypy]
python_version = "3.11"
warn_return_any = false          # 暂时关闭Any返回警告
disallow_untyped_defs = false    # 暂时允许无类型定义（新代码应添加）
check_untyped_defs = false       # 暂时关闭无类型定义检查
```

**目标**：逐步收紧配置，最终达到 `disallow_untyped_defs = true`

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

### Pipeline流程

1. **code-quality**: black, isort, mypy, bandit
2. **test**: pytest (Python 3.11/3.12 矩阵)
3. **build**: 构建 wheel/sdist
4. **release**: main 分支打 tag → GitHub Release

### 质量门禁（v0.4.1强化）

#### 代码质量门禁

| 检查项 | 工具 | 门禁要求 | 失败处理 |
|--------|------|----------|----------|
| 代码格式化 | black | 零警告 | 阻断合并 |
| 导入排序 | isort | 零警告 | 阻断合并 |
| 类型检查 | mypy | 警告可接受 | 非阻断（逐步收紧） |
| 安全扫描 | bandit | 高危漏洞=0 | 阻断合并 |

#### 测试质量门禁

| 检查项 | 要求 | 失败处理 |
|--------|------|----------|
| 单元测试通过率 | 100% | 阻断合并 |
| 集成测试通过率 | 100% | 阻断合并 |
| 代码覆盖率 | core≥80%, agents≥70%, cli≥60% | 阻断合并 |
| 测试执行时间 | 单测试<30秒 | 标记慢测试 |

#### 本地预检查（推荐）

提交前在本地执行质量检查，避免CI失败：

```bash
# 完整预检查脚本
uv run black --check src/ tests/                      # 格式化检查
uv run isort --check-only src/ tests/                 # 导入排序检查
uv run mypy src/ --ignore-missing-imports             # 类型检查
uv run bandit -r src/ -s B101,B601                    # 安全扫描
uv run pytest tests/unit/ --cov=src --cov-fail-under=80  # 单元测试+覆盖率
```

#### CI环境差异处理

v0.4.1版本发现CI环境与本地环境差异问题，解决方案：

```bash
# 1. 确保types-requests已安装
pip install types-requests

# 2. 清理缓存（遇到奇怪问题时）
uv cache clean; uv sync --reinstall

# 3. CI配置使用--no-cache-dir避免缓存污染
pip install -e .[dev,test] --no-cache-dir
```

### 发布流程

```bash
# 1. 确保所有检查通过
uv run pytest
uv run black src tests
uv run isort src tests

# 2. 更新版本号（pyproject.toml）
# version = "x.y.z"

# 3. 创建tag并推送
git tag -a vx.y.z -m "Release version x.y.z"
git push origin vx.y.z

# 4. GitHub Actions自动执行发布
```

## 依赖管理（统一使用uv）

### uv安装与配置

```bash
# 安装uv (Windows)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# 验证安装
uv --version
```

### 常用uv命令

```bash
# 环境管理
uv venv                                          # 创建虚拟环境
.venv\Scripts\activate                           # Windows激活
source .venv/bin/activate                        # Linux/Mac激活

# 依赖同步
uv sync                                          # 同步基础依赖
uv sync --all-extras                             # 同步所有依赖（含dev/test）
uv sync --extra dev                              # 仅同步开发依赖
uv sync --extra test                             # 仅同步测试依赖

# 依赖维护
uv cache clean                                   # 清理缓存
uv cache clean; if($?) { uv sync --reinstall }   # 清理重装 (Windows)
uv pip list                                      # 查看已安装包

# 运行命令
uv run python script.py                          # 在虚拟环境中运行
uv run pytest                                    # 运行测试
uv run nanobotrun --help                         # 运行CLI
```

### pyproject.toml依赖配置

```toml
[project]
dependencies = [
    "nanobot-ai>=0.1.4",
    "typer[all]>=0.12.0",
    "rich>=13.0.0",
    "polars>=0.20.0",
]

[project.optional-dependencies]
test = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
]
dev = [
    "black>=23.0.0,<24.0.0",
    "isort>=5.12.0,<6.0.0",
    "mypy>=1.0.0,<2.0.0",
]
```

### 依赖问题解决

```bash
# 问题1: 依赖冲突
uv cache clean; uv sync --reinstall

# 问题2: 类型存根缺失（CI常见）
pip install types-requests types-setuptools

# 问题3: Windows执行策略
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 问题4: Windows多命令链
# 用 "; if($?) { cmd }" 替代 "&&"
uv cache clean; if($?) { uv sync --reinstall }
```

## 常见问题

```bash
# 依赖问题
uv cache clean; uv sync --reinstall

# Windows PowerShell激活
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Windows多命令链: 用 "; if($?) { cmd }" 替代 "&&"
```
