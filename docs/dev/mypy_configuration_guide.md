# MyPy类型检查配置指南

## 概述

本文档详细说明 Nanobot Runner 项目中 mypy 类型检查工具的配置和使用方法，基于 v0.4.1 版本的实践经验。

## 当前配置

### pyproject.toml配置

```toml
[tool.mypy]
python_version = "3.11"
warn_return_any = false          # 暂时关闭Any返回警告
warn_unused_configs = true
disallow_untyped_defs = false    # 暂时允许无类型定义（新代码应添加）
check_untyped_defs = false       # 暂时关闭无类型定义检查
disallow_incomplete_defs = false # 暂时允许不完整定义
disallow_untyped_decorators = false  # 暂时允许无类型装饰器
no_implicit_optional = false     # 暂时关闭隐式Optional检查
warn_redundant_casts = false     # 暂时关闭冗余转换警告
warn_unused_ignores = false      # 暂时关闭未使用忽略警告
warn_no_return = false           # 暂时关闭无返回警告
```

### 配置说明

| 配置项 | 当前值 | 说明 | 目标值 |
|--------|--------|------|--------|
| `python_version` | "3.11" | Python目标版本 | "3.11" |
| `warn_return_any` | false | Any返回警告 | true (v0.5.0) |
| `disallow_untyped_defs` | false | 禁止无类型定义 | true (v0.5.0) |
| `check_untyped_defs` | false | 检查无类型定义 | true (v0.4.2) |
| `disallow_incomplete_defs` | false | 禁止不完整定义 | true (v0.4.2) |
| `no_implicit_optional` | false | 禁止隐式Optional | true (v0.4.2) |

## 配置演进计划

### 阶段1: v0.4.1（当前）- 建立基线

**目标**: 允许现有代码通过，新代码建议添加类型注解

```toml
[tool.mypy]
python_version = "3.11"
warn_return_any = false
disallow_untyped_defs = false
check_untyped_defs = false
disallow_incomplete_defs = false
```

**要求**:
- 新代码建议添加类型注解
- 核心模块（core/、agents/）优先添加
- 允许使用 `# type: ignore` 标记已知问题

### 阶段2: v0.4.2 - 收紧配置

**目标**: 核心模块类型覆盖率≥80%

```toml
[tool.mypy]
python_version = "3.11"
warn_return_any = true
disallow_untyped_defs = false  # 仍允许，但警告
check_untyped_defs = true      # 开始检查无类型定义
disallow_incomplete_defs = true
no_implicit_optional = true
```

**要求**:
- 核心模块必须完整类型注解
- 新增代码必须有类型注解
- 逐步修复 `# type: ignore`

### 阶段3: v0.5.0 - 严格模式

**目标**: 全模块类型覆盖率≥80%

```toml
[tool.mypy]
python_version = "3.11"
strict = true  # 启用所有严格检查
```

或等效配置：

```toml
[tool.mypy]
python_version = "3.11"
warn_return_any = true
disallow_untyped_defs = true
check_untyped_defs = true
disallow_incomplete_defs = true
disallow_untyped_decorators = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
```

## 类型注解最佳实践

### 基础类型

```python
# 基本类型
from typing import Optional, Union, Any, Callable

def process_data(
    name: str,
    count: int,
    ratio: float,
    enabled: bool
) -> dict[str, Any]:
    """处理数据并返回结果字典"""
    return {"name": name, "count": count}

# Optional表示可空
def find_user(user_id: str) -> Optional[dict[str, Any]]:
    """查找用户，可能返回None"""
    return None

# Union表示多类型（Python 3.10+可用 | 语法）
def parse_value(value: Union[str, int]) -> str:
    """解析值，接受字符串或整数"""
    return str(value)

# Python 3.10+ 简化语法
def parse_value_modern(value: str | int) -> str:
    """解析值，使用现代语法"""
    return str(value)
```

### 复杂类型

```python
from typing import TypeVar, Generic, TypeAlias
from collections.abc import Iterator, Generator

# 类型别名
UserData: TypeAlias = dict[str, Union[str, int, float]]
HandlerFunc: TypeAlias = Callable[[str], bool]

# 泛型
T = TypeVar('T')
K = TypeVar('K')
V = TypeVar('V')

def first_or_default(items: list[T], default: T) -> T:
    """获取列表第一个元素或默认值"""
    return items[0] if items else default

# 生成器类型
def generate_numbers(n: int) -> Iterator[int]:
    """生成数字序列"""
    for i in range(n):
        yield i
```

### 类类型注解

```python
from pathlib import Path

class DataProcessor:
    """数据处理器"""
    
    # 类变量注解
    DEFAULT_CHUNK_SIZE: int = 1000
    
    def __init__(self, data_dir: Path, chunk_size: int | None = None) -> None:
        self.data_dir = data_dir
        self.chunk_size = chunk_size or self.DEFAULT_CHUNK_SIZE
        self._cache: dict[str, Any] = {}
    
    def process_file(
        self, 
        filename: str,
        options: dict[str, Any] | None = None
    ) -> tuple[bool, str]:
        """处理单个文件"""
        try:
            return True, f"成功处理 {filename}"
        except Exception as e:
            return False, str(e)
```

### 循环引用处理

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.storage import StorageManager
    from src.core.analytics import AnalyticsEngine

class DataService:
    def __init__(self, storage: "StorageManager") -> None:
        self.storage = storage
    
    def get_analytics(self) -> "AnalyticsEngine":
        from src.core.analytics import AnalyticsEngine
        return AnalyticsEngine(self.storage)
```

## 常见类型检查错误及解决

### 错误1: 缺少返回类型注解

```python
# 错误
def calculate_vdot(distance, time):
    return distance / time

# 正确
def calculate_vdot(distance: float, time: float) -> float:
    return distance / time
```

### 错误2: Optional处理不当

```python
# 错误
user = find_user("123")
print(user["name"])  # error: Item "None" of "Optional[dict[str, Any]]" has no member "__getitem__"

# 正确
user = find_user("123")
if user is not None:
    print(user["name"])

# 或使用类型断言（确定不为None时）
user = find_user("123")
assert user is not None
print(user["name"])
```

### 错误3: 列表/字典类型不明确

```python
# 错误
data = []  # error: Need type annotation for "data"
data.append("item")

# 正确
from typing import List
data: list[str] = []
data.append("item")

# 或
data = []  # type: list[str]
data.append("item")
```

### 错误4: 第三方库缺少类型存根

```python
# 错误
import fitparse  # error: Skipping analyzing "fitparse": module is installed, but missing library stubs or py.typed marker

# 解决方案1: 安装类型存根
# pip install types-fitparse  # 如果存在

# 解决方案2: 添加忽略注释
import fitparse  # type: ignore[import]

# 解决方案3: 在mypy配置中忽略
# pyproject.toml
# [[tool.mypy.overrides]]
# module = "fitparse"
# ignore_missing_imports = true
```

## 使用 # type: ignore

### 使用原则

1. **尽量避免** - 优先修复类型问题
2. **必须注释原因** - 说明为什么需要忽略
3. **定期清理** - 随着配置收紧，逐步移除

### 正确示例

```python
# 正确: 说明原因
import fitparse  # type: ignore[import] # fitparse没有类型存根

# 正确: 特定错误码
result = some_function()  # type: ignore[return-value] # 第三方库返回类型不准确

# 错误: 无说明
result = some_function()  # type: ignore
```

## CI环境配置

### GitHub Actions配置

```yaml
- name: Type checking with mypy
  run: |
    echo "开始类型检查..."
    pip install types-requests  # 显式安装类型存根
    python -m mypy src/ --ignore-missing-imports --install-types --non-interactive || echo "mypy检查完成，有警告"
  continue-on-error: true  # v0.4.1阶段不阻断
```

### 本地检查命令

```bash
# 基础检查
uv run mypy src/

# 忽略缺失导入
uv run mypy src/ --ignore-missing-imports

# 安装类型存根
uv run mypy src/ --install-types --non-interactive

# 显示错误码（便于添加ignore）
uv run mypy src/ --show-error-codes

# 生成报告
uv run mypy src/ --ignore-missing-imports --linecount-report reports/
```

## 类型覆盖率检查

### 使用mypy覆盖率工具

```bash
# 安装
pip install mypy-coverage

# 运行
mypy-coverage src/
```

### 手动检查脚本

```python
# scripts/check_type_coverage.py
import subprocess
import sys

def check_type_coverage():
    """检查类型覆盖率"""
    result = subprocess.run(
        ["mypy", "src/", "--ignore-missing-imports", "--linecount-report", "/tmp/mypy_report"],
        capture_output=True,
        text=True
    )
    
    # 解析报告
    # ...
    
    return result.returncode == 0

if __name__ == "__main__":
    if check_type_coverage():
        print("✓ 类型检查通过")
        sys.exit(0)
    else:
        print("✗ 类型检查失败")
        sys.exit(1)
```

## 迁移指南

### 为现有代码添加类型注解

1. **从公共API开始** - 优先处理对外暴露的函数
2. **使用工具辅助** - `monkeytype` 或 `pyannotate`
3. **逐步推进** - 按模块逐个处理

```bash
# 安装工具
pip install monkeytype

# 运行测试收集类型
monkeytype run -m pytest tests/unit/

# 为特定模块应用类型
monkeytype apply src.core.storage
```

### 类型注解检查清单

- [ ] 函数参数有类型注解
- [ ] 函数返回值有类型注解
- [ ] 类属性有类型注解
- [ ] 复杂类型使用TypeAlias
- [ ] Optional参数正确处理None
- [ ] 循环引用使用TYPE_CHECKING
- [ ] 第三方库缺失类型存根已处理

---

*文档版本: 1.0*  
*适用版本: v0.4.1+*  
*最后更新: 2026-03-29*
