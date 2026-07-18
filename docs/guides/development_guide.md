# 开发指南

本文档详细描述 Nanobot Runner 的技术栈约束、代码风格和开发规范。

---

## 1. Polars 严格限制

> ⚠️ **警告**：严禁在非必要情况下调用 `.collect()` 将 LazyFrame 转换为 DataFrame！

所有数据转换必须在 LazyFrame 状态下完成，仅在最终输出或写入 Parquet 时调用 `.collect()`，以防内存溢出（OOM）。

### 1.1 正确示例

```python
import polars as pl

# ✅ 正确：保持 LazyFrame 直到最终输出
df = pl.scan_parquet(path)
result = df.filter(pl.col("distance") > 5000).group_by("date").agg(pl.len())
output = result.collect()  # 仅在最终输出时 collect

# ✅ 正确：写入 Parquet 时 collect
df = pl.scan_parquet(path)
df.filter(pl.col("year") == 2024).collect().write_parquet(output_path, compression='snappy')
```

### 1.2 错误示例

```python
# ❌ 错误：过早 collect
df = pl.scan_parquet(path).collect()  # 禁止！
result = df.filter(...)  # 这时已经是 DataFrame，内存风险

# ❌ 错误：在循环中 collect
for file in files:
    df = pl.scan_parquet(file).collect()  # 禁止！每次循环都加载到内存
```

### 1.3 其他 Polars 规范

| 操作 | 规范 |
|------|------|
| 读取 | `pl.scan_parquet()` → LazyFrame |
| 写入 | `.collect().write_parquet(path, compression='snappy')` |
| 合并 | 使用 `pl.concat()` |
| 类型转换 | Object → String 以兼容 Parquet |

---

## 2. 异常处理规范

> ⚠️ **禁止抛出内置的 `Exception` 或 `ValueError`**，必须使用自定义异常并附带 `recovery_suggestion`。

### 2.1 可用异常类

```python
from src.core.exceptions import (
    NanobotRunnerError,  # 基类
    StorageError,        # 存储相关错误
    ParseError,          # 解析相关错误
    ConfigError,         # 配置相关错误
    ValidationError,     # 数据验证错误
)
```

### 2.2 自定义异常示例

```python
from dataclasses import dataclass
from src.core.exceptions import NanobotRunnerError

@dataclass
class TrainingPlanError(NanobotRunnerError):
    """训练计划相关错误"""
    error_code: str = "TRAINING_PLAN_ERROR"
    recovery_suggestion: str = "请检查训练计划参数是否正确"
```

### 2.3 工具层异常处理

```python
from src.core.decorators import handle_tool_errors

@handle_tool_errors(default_response={"error": "操作失败"})
async def execute(self, **kwargs) -> dict:
    # 业务逻辑
    return {"success": True, "data": ...}
```

---

## 3. 类型注解强制要求

### 3.1 基本要求

- 新代码必须添加类型注解
- 核心模块类型覆盖率 ≥ 80%
- 工具函数必须标注参数和返回值类型
- **禁止返回 `dict[str, Any]`**：对于字典形式的返回数据，优先使用 `TypedDict` 或 `dataclass` 提供类型安全

### 3.2 类型注解示例

```python
from typing import TYPE_CHECKING, Any, Optional, Union, Callable, TypeAlias, TypedDict
from datetime import datetime

def calculate_vdot(distance_m: float, time_s: float) -> float:
    """计算VDOT值"""
    if distance_m <= 0 or time_s <= 0:
        raise ValueError("距离和时间必须为正数")
    return (distance_m / time_s) * 3.5

# ✅ 推荐：使用 TypedDict 定义结构化字典返回类型（v0.30.0+）
class TrainingLoadResult(TypedDict, total=False):
    """训练负荷分析结果"""
    atl: float
    ctl: float
    tsb: float
    fitness_status: str

# ✅ 替代方案：使用 dataclass 定义返回类型
@dataclass
class SessionSummary:
    total_distance: float
    avg_heart_rate: float

# ❌ 禁止：返回无类型约束的 dict[str, Any]
def get_stats(self, year: Optional[int] = None) -> dict[str, Any]:  # 禁止！
    ...

# ✅ 正确：返回 TypedDict 类型
def get_training_load(self, days: int = 42) -> TrainingLoadResult:
    return {"atl": 50.0, "ctl": 65.0, "tsb": 15.0, "fitness_status": "良好"}
```

---

## 4. 代码风格

### 4.1 导入顺序

使用ruff的isort规则自动排序导入：

```python
# 1. 标准库
import logging
from typing import TYPE_CHECKING, Any, Optional
from pathlib import Path

# 2. 第三方库
import polars as pl
from rich.console import Console

# 3. 本地模块 (src.*)
from src.core.storage import StorageManager
from src.core.exceptions import StorageError
```

### 4.2 命名约定

| 类型 | 约定 | 示例 |
|------|------|------|
| 类名 | PascalCase | `StorageManager` |
| 函数/变量 | snake_case | `calculate_vdot` |
| 常量 | UPPER_SNAKE_CASE | `VDOT_COEFFICIENT` |
| 私有成员 | `_leading_underscore` | `_internal_helper` |
| 测试类 | `Test{ClassName}` | `TestStorageManager` |
| 测试函数 | `test_{action}_{case}` | `test_save_to_parquet_success` |

### 4.3 文档字符串

```python
def calculate_vdot(distance_m: float, time_s: float) -> float:
    """计算VDOT值（跑力值）。
    
    基于 Jack Daniels 的 VDOT 计算公式。
    
    Args:
        distance_m: 跑步距离（米）
        time_s: 完成时间（秒）
    
    Returns:
        VDOT 值
    
    Raises:
        ValueError: 当距离或时间非正时
    """
    ...
```

---

## 5. 质量门禁

| 检查项 | 工具 | 门禁要求 |
|--------|------|----------|
| 代码格式化 | ruff format | 零警告 |
| 代码质量 | ruff check | 零警告 |
| 类型检查 | mypy | 警告可接受 |
| 安全扫描 | bandit | 高危漏洞=0 |
| 单元测试 | pytest | 通过率100% |
| 代码覆盖率 | pytest-cov | core≥80%, agents≥70%, cli≥60% |

---

## 6. 依赖注入规范（v0.9.0新增）

> ⚠️ **禁止直接实例化核心组件**，必须通过 `AppContext` 获取依赖。

### 6.1 正确示例

```python
from src.core.base.context import get_context

def some_function():
    # ✅ 正确：通过上下文获取依赖
    context = get_context()
    storage = context.storage
    analytics = context.analytics
    session_repo = context.session_repo
    
    # 使用依赖
    stats = session_repo.get_session_summary(session_id)
```

### 6.2 错误示例

```python
from src.core.storage import StorageManager

def some_function():
    # ❌ 错误：直接实例化
    storage = StorageManager()  # 禁止！
```

### 6.3 测试时注入Mock

```python
from unittest.mock import Mock
from src.core.base.context import set_context, reset_context, AppContext

def test_with_mock():
    # 创建Mock对象
    mock_storage = Mock()
    mock_analytics = Mock()
    
    # 注入Mock上下文
    mock_context = AppContext(
        storage=mock_storage,
        analytics=mock_analytics,
        ...
    )
    set_context(mock_context)
    
    try:
        # 测试代码
        ...
    finally:
        # 重置上下文
        reset_context()
```

---

## 7. SessionRepository 使用规范（v0.9.0新增）

> ⚠️ **禁止返回 `Dict[str, Any]`**，必须使用类型安全的数据类。

### 7.1 正确示例

```python
from src.core.base.context import get_context

context = get_context()
session_repo = context.session_repo

# ✅ 正确：使用类型安全的返回值
summary: SessionSummary = session_repo.get_session_summary(session_id)
detail: SessionDetail = session_repo.get_session_detail(session_id)

# 访问类型安全的属性
print(f"总距离: {summary.total_distance}米")
print(f"平均心率: {detail.avg_heart_rate}bpm")
```

### 7.2 错误示例

```python
# ❌ 错误：返回 Dict[str, Any]
result: Dict[str, Any] = session_repo.get_session_summary(session_id)  # 禁止！
```

### 7.3 LazyFrame 保持规范

```python
# ✅ 正确：保持 LazyFrame 直到最终输出
def get_sessions_lazy(self, start_date: date, end_date: date) -> pl.LazyFrame:
    df = pl.scan_parquet(self.data_path)
    return df.filter(
        (pl.col("timestamp").dt.date() >= start_date) &
        (pl.col("timestamp").dt.date() <= end_date)
    )

# 仅在最终输出时 collect
sessions = session_repo.get_sessions_lazy(start, end).collect()
```

---

## 8. 本地验证命令

```bash
# 代码格式化
uv run ruff format src/ tests/

# 代码质量检查
uv run ruff check src/ tests/

# 自动修复问题
uv run ruff check --fix src/ tests/

# 类型检查
uv run mypy src/ --ignore-missing-imports

# 安全扫描
uv run bandit -r src/ -s B101,B601

# 单元测试
uv run pytest tests/unit/ --cov=src --cov-fail-under=80
```

## 9. SDK 编程式调用指南（v0.32.0 新增）

nanobot-ai 0.2.2 提供了正式的 SDK API，通过 `SDKAdapter` 封装使用。

### 9.1 基本用法

```python
from src.core.sdk_adapter import SDKAdapter

# 创建适配器
adapter = SDKAdapter(config_path=Path("~/.nanobot-runner/config.json"))

# 非流式调用
result = await adapter.run(
    message="分析今日训练负荷",
    session_key="session-001",
)
print(result.content)

# 流式调用
async for event in adapter.stream(
    message="生成本周报告",
    session_key="session-001",
):
    if event.delta:
        print(event.delta, end="", flush=True)
```

### 9.2 配置注入

```python
from src.core.config_injector import ConfigInjector

injector = ConfigInjector(config_path=Path("~/.nanobot-runner/config.json"))
nanobot_config = injector.build_nanobot_config(runner_config)
# nanobot_config 是 nanobot Config Pydantic 模型，传给 Nanobot.from_config()
```

## 10. 运行时事件订阅指南（v0.32.0 新增）

通过 `RuntimeEventHook` 订阅 nanobot 运行时事件总线，事件通过 WebUI SSE 端点推送。

### 10.1 事件类型

| 事件 | 方法 | 触发时机 |
|------|------|---------|
| turn_completed | RuntimeEventPublisher.turn_completed | Agent turn 完成 |
| session_turn_started | RuntimeEventPublisher.session_turn_started | 会话 turn 开始 |
| run_status_changed | RuntimeEventPublisher.run_status_changed | 运行状态变更 |

### 10.2 WebUI SSE 订阅

```bash
# 通过 SSE 端点订阅运行时事件
curl -N -H "Authorization: Bearer <token>" \
  http://127.0.0.1:8766/api/runtime-events
```

### 10.3 自定义 Provider 注册

```python
from src.core.provider_adapter import DynamicProviderRegistry

# 注册自定义 Provider
DynamicProviderRegistry.register_custom_provider(
    name="my-provider",
    api_base="https://api.example.com/v1",
    api_key="sk-xxx",
    default_model="example-model",
)
```

---

*文档版本: v0.32.0 | 更新日期: 2026-07-13*
