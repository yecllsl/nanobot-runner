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

### 3.2 类型注解示例

```python
from typing import TYPE_CHECKING, Any, Optional, Union, Callable, TypeAlias
from datetime import datetime

def calculate_vdot(distance_m: float, time_s: float) -> float:
    """计算VDOT值"""
    if distance_m <= 0 or time_s <= 0:
        raise ValueError("距离和时间必须为正数")
    return (distance_m / time_s) * 3.5

ActivityRecord: TypeAlias = dict[str, Union[str, int, float, datetime]]

class AnalyticsEngine:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
    
    def get_stats(self, year: Optional[int] = None) -> dict[str, Any]:
        ...
```

---

## 4. 代码风格

### 4.1 导入顺序 (isort profile=black)

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
| 代码格式化 | black | 零警告 |
| 导入排序 | isort | 零警告 |
| 类型检查 | mypy | 警告可接受 |
| 安全扫描 | bandit | 高危漏洞=0 |
| 单元测试 | pytest | 通过率100% |
| 代码覆盖率 | pytest-cov | core≥80%, agents≥70%, cli≥60% |

---

## 6. 本地验证命令

```bash
# 格式检查
uv run black --check src/ tests/
uv run isort --check-only src/ tests/

# 类型检查
uv run mypy src/ --ignore-missing-imports

# 安全扫描
uv run bandit -r src/ -s B101,B601

# 单元测试
uv run pytest tests/unit/ --cov=src --cov-fail-under=80
```

---

*文档版本: v1.0.0 | 更新日期: 2026-04-01*
