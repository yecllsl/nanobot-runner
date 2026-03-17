# 项目Bug清单

## Bug统计

| 严重等级 | 数量 | 状态 |
|---------|------|------|
| 致命 | 0 | - |
| 严重 | 1 | 待修复 |
| 一般 | 0 | - |
| 优化 | 0 | - |

---

## Bug详情

### Bug #1: _validate_data_quality 时间间隔计算错误

**基本信息**
- **Bug ID**: PARSER-001
- **所属模块**: src/core/parser.py
- **严重等级**: 严重
- **优先级**: P0
- **发现时间**: 2026-03-17
- **发现者**: 测试工程师智能体
- **状态**: 待修复
- **出现版本**: v0.3.0

**问题描述**

在 `_validate_data_quality` 方法中,当DataFrame包含多条时间戳记录时,计算时间间隔(time_gaps)会抛出TypeError异常。

**复现步骤**

1. 创建包含多条时间戳记录的DataFrame:
```python
import polars as pl
from datetime import datetime

timestamps = [
    datetime(2024, 1, 1, 12, 0, 0),
    datetime(2024, 1, 1, 12, 1, 0),
    datetime(2024, 1, 1, 12, 2, 0),
    datetime(2024, 1, 1, 12, 10, 0),
]

df = pl.DataFrame({
    "timestamp": timestamps,
    "distance": [100.0, 200.0, 300.0, 400.0],
    "heart_rate": [140, 145, 150, 155],
})
```

2. 调用 `_validate_data_quality` 方法:
```python
parser = FitParser()
result = parser._validate_data_quality(df)
```

**实际结果**

```
ParseError: 数据质量验证失败: Series constructor called with unsupported type 'Expr' for the `values` parameter
```

**预期结果**

应正确计算时间间隔,返回包含time_gaps数量的质量评估结果。

**根因分析**

**问题代码位置**: [parser.py:235](file:///d:/yecll/Documents/LocalCode/RunFlowAgent/src/core/parser.py#L235)

```python
time_gaps = time_diffs.filter(
    pl.col("timestamp") > avg_gap * 2
).len()
```

**问题原因**:
1. `time_diffs` 是 `Series` 类型(通过 `timestamps.diff()` 获得)
2. Series的 `filter()` 方法期望接收一个Series作为谓词,而不是Expr
3. `pl.col("timestamp")` 返回的是Expr类型,导致类型不匹配

**错误堆栈**:
```
polars/series/series.py:3356: in filter
    predicate = Series("", predicate)
polars/series/series.py:385: TypeError
    raise TypeError(msg)
TypeError: Series constructor called with unsupported type 'Expr' for the `values` parameter
```

**修复建议**

**方案1: 使用Series直接比较** (推荐)
```python
# 修改 parser.py 第235行
time_gaps = time_diffs.filter(time_diffs > avg_gap * 2).len()
```

**方案2: 转换为DataFrame后使用filter**
```python
# 修改 parser.py 第235行
time_gaps = (
    time_diffs.to_frame()
    .filter(pl.col("timestamp") > avg_gap * 2)
    .height
)
```

**方案3: 使用布尔索引**
```python
# 修改 parser.py 第235行
mask = time_diffs > avg_gap * 2
time_gaps = time_diffs.filter(mask).len()
```

**影响范围**
- 所有包含多条记录的FIT文件解析
- 数据质量评估功能
- VDOT计算、TSS计算等依赖数据质量的功能

**测试验证**

已编写测试用例 `test_validate_data_quality_time_gaps` 验证该bug,测试期望抛出ParseError异常。

**修复后验证步骤**
1. 修复代码后,运行单元测试:
```bash
uv run pytest tests/unit/test_parser.py::TestFitParserDataQuality::test_validate_data_quality_time_gaps -v
```

2. 验证应返回正确的time_gaps数量,而非抛出异常

**修复优先级**: P0 (核心功能缺陷,影响所有多记录FIT文件解析)

**预计修复时间**: 0.5小时

**修复负责人**: 待分配

---

## Bug修复跟踪

| Bug ID | 修复版本 | 修复人 | 验证人 | 验证结果 | 关闭时间 |
|--------|---------|--------|--------|---------|---------|
| PARSER-001 | - | - | - | - | - |

---

**最后更新时间**: 2026-03-17
**维护人**: 测试工程师智能体
