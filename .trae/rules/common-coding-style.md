---
alwaysApply: false
description: 通用编码风格指南   
---
# 编码风格

## 不可变性（关键）

始终创建新对象，绝不改变现有对象：

```
// Pseudocode
WRONG:  modify(original, field, value) → changes original in-place
CORRECT: update(original, field, value) → returns new copy with change
```

理由：不可变数据可以防止隐藏的副作用，使调试更容易，并支持安全的并发。

## 文件组织

多个小文件 > 少数大文件：

* 高内聚，低耦合
* 通常 200-400 行，最多 800 行
* 从大型模块中提取实用工具
* 按功能/领域组织，而不是按类型组织

## 错误处理

始终全面处理错误：

* 在每个层级明确处理错误
* 在面向用户的代码中提供用户友好的错误消息
* 在服务器端记录详细的错误上下文
* 绝不默默地忽略错误

## 输入验证

始终在系统边界处进行验证：

* 在处理前验证所有用户输入
* 在可用时使用基于模式的验证
* 快速失败并提供清晰的错误消息
* 绝不信任外部数据（API 响应、用户输入、文件内容）

## 类型注解规范（Python）

### 基本要求

- **新代码必须**添加完整的类型注解（v0.4.1+强制要求）
- 核心模块类型覆盖率目标≥80%
- 所有公共函数必须标注参数类型和返回值类型
- 使用Python 3.11+的现代类型语法

### 基础类型注解

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

### 复杂类型注解

```python
from typing import TypeVar, Generic, TypeAlias

# 列表和字典
def process_items(items: list[str]) -> dict[str, int]:
    """处理字符串列表，返回计数字典"""
    return {item: len(item) for item in items}

# 元组（固定长度）
def get_dimensions() -> tuple[int, int, int]:
    """返回三维尺寸"""
    return 1920, 1080, 60

# 类型别名
UserData: TypeAlias = dict[str, Union[str, int, float]]
HandlerFunc: TypeAlias = Callable[[str], bool]

def process_users(users: list[UserData]) -> None:
    """处理用户数据列表"""
    pass

# 泛型
T = TypeVar('T')

def first_or_default(items: list[T], default: T) -> T:
    """获取列表第一个元素或默认值"""
    return items[0] if items else default
```

### 类类型注解

```python
from pathlib import Path

class DataProcessor:
    """数据处理器"""
    
    # 类变量注解
    DEFAULT_CHUNK_SIZE: int = 1000
    
    def __init__(self, data_dir: Path, chunk_size: int | None = None) -> None:
        """初始化处理器
        
        Args:
            data_dir: 数据目录路径
            chunk_size: 分块大小，默认使用类默认值
        """
        self.data_dir = data_dir
        self.chunk_size = chunk_size or self.DEFAULT_CHUNK_SIZE
        self._cache: dict[str, Any] = {}
    
    def process_file(
        self, 
        filename: str,
        options: dict[str, Any] | None = None
    ) -> tuple[bool, str]:
        """处理单个文件
        
        Args:
            filename: 文件名
            options: 处理选项
            
        Returns:
            tuple[bool, str]: (成功状态, 消息)
        """
        try:
            # 处理逻辑
            return True, f"成功处理 {filename}"
        except Exception as e:
            return False, str(e)
    
    @property
    def cache_size(self) -> int:
        """获取缓存大小"""
        return len(self._cache)
```

### 循环引用处理

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # 仅在类型检查时导入，避免循环引用
    from src.core.storage import StorageManager
    from src.core.analytics import AnalyticsEngine

class DataService:
    def __init__(self, storage: "StorageManager") -> None:
        self.storage = storage
    
    def get_analytics(self) -> "AnalyticsEngine":
        from src.core.analytics import AnalyticsEngine
        return AnalyticsEngine(self.storage)
```

### 特殊类型注解

```python
from collections.abc import Iterator, Generator, AsyncIterator
from contextlib import contextmanager

# 生成器类型
def generate_numbers(n: int) -> Iterator[int]:
    """生成数字序列"""
    for i in range(n):
        yield i

# 上下文管理器
@contextmanager
def temporary_file(prefix: str) -> Generator[Path, None, None]:
    """临时文件上下文管理器"""
    path = Path(f"{prefix}_temp.txt")
    try:
        yield path
    finally:
        if path.exists():
            path.unlink()

# 异步函数
async def fetch_data(url: str) -> dict[str, Any]:
    """异步获取数据"""
    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()
```

### 类型注解检查清单

在标记工作完成之前：

* [ ] 所有公共函数有参数类型注解
* [ ] 所有函数有返回值类型注解
* [ ] 复杂数据结构使用TypeAlias
* [ ] 可选参数使用Optional或 | None
* [ ] 循环引用使用TYPE_CHECKING处理
* [ ] 类方法包含self参数类型（无需注解）但返回值已注解
* [ ] 泛型函数使用TypeVar

## 代码质量检查清单

在标记工作完成之前：

* [ ] 代码可读且命名良好
* [ ] 函数短小（<50 行）
* [ ] 文件专注（<800 行）
* [ ] 没有深度嵌套（>4 层）
* [ ] 正确的错误处理
* [ ] 没有硬编码的值（使用常量或配置）
* [ ] 没有突变（使用不可变模式）
* [ ] **类型注解完整**（v0.4.1+新增）
