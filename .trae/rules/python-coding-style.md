---
alwaysApply: false
description: Python 编码风格
globs: *.py,*.pyi
---
# Python 编码风格

> 本文件在 [common/coding-style.md](../common/coding-style.md) 的基础上扩展了 Python 特定的内容。

## 标准

* 遵循 **PEP 8** 规范
* 在所有函数签名上使用 **类型注解**

## 不变性

优先使用不可变数据结构：

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class User:
    name: str
    email: str

from typing import NamedTuple

class Point(NamedTuple):
    x: float
    y: float
```

## 格式化

* 使用 **ruff format** 进行代码格式化
* 使用 **ruff check** 进行代码质量检查（包含导入排序）
* 使用 **mypy** 进行类型检查

## 参考

查看技能：`python-patterns` 以获取全面的 Python 惯用法和模式。
