# 测试指南

本文档描述 Nanobot Runner 的测试策略、Mock 方法和隐私红线。

---

## 1. 测试数据来源

项目包含 `tests/data/fixtures/` 目录下的样本 FIT 文件，请使用该样本进行测试。

```python
from pathlib import Path

FIXTURE_DIR = Path(__file__).parent.parent / "data" / "fixtures"
SAMPLE_FIT_PATH = FIXTURE_DIR / "easy_run_20240101.fit"
```

### 1.1 可用测试文件

| 文件 | 类型 | 用途 |
|------|------|------|
| `easy_run_*.fit` | 轻松跑 | 正常数据测试 |
| `tempo_run_*.fit` | 节奏跑 | 正常数据测试 |
| `long_run_*.fit` | 长距离跑 | 正常数据测试 |
| `interval_*.fit` | 间歇跑 | 正常数据测试 |
| `empty_file.fit` | 空文件 | 边界测试 |
| `corrupted_file.fit` | 损坏文件 | 异常测试 |
| `large_file.fit` | 大文件 | 性能测试 |

---

## 2. Mock 策略

> ⚠️ **不要尝试在测试中生成伪造的 FIT 文件**（过于复杂），而应使用 Mock 隔离 `FitParser`。

### 2.1 Mock FitParser

```python
from unittest.mock import AsyncMock, patch
from src.core.parser import FitParser

@patch("src.core.parser.FitParser.parse_file")
async def test_import_data(mock_parse):
    mock_parse.return_value = {
        "activity_id": "test_123",
        "timestamp": "2024-01-01T08:00:00",
        "total_distance": 5000.0,
        "total_timer_time": 1800.0
    }
    # 测试逻辑
```

### 2.2 构造 Polars DataFrame 进行单测

```python
import polars as pl

def create_mock_dataframe():
    return pl.DataFrame({
        "activity_id": ["test_001", "test_002"],
        "distance_km": [5.0, 10.0],
        "duration_min": [30, 60],
        "avg_pace_min_per_km": [6.0, 6.0],
        "avg_heart_rate": [150, 155],
        "timestamp": ["2024-01-01", "2024-01-02"]
    })

def test_analytics_engine():
    df = create_mock_dataframe()
    engine = AnalyticsEngine(data_dir=Path("/tmp/test"))
    # 使用 df 进行测试
```

### 2.3 Mock 异步工具

```python
from unittest.mock import AsyncMock, MagicMock

async def test_runner_tools():
    tools = RunnerTools()
    tools.storage_manager = MagicMock()
    tools.storage_manager.get_stats = AsyncMock(return_value={
        "total_runs": 10,
        "total_distance": 50000
    })
    
    result = await tools.get_running_stats()
    assert result["total_runs"] == 10
```

---

## 3. 测试命令

```bash
# 全部测试
uv run pytest

# 仅单元测试
uv run pytest tests/unit/

# 仅集成测试
uv run pytest tests/integration/

# 按关键字匹配
uv run pytest -k "test_calculate_vdot"

# 无覆盖率
uv run pytest --no-cov

# 带覆盖率
uv run pytest tests/unit/ --cov=src --cov-fail-under=80

# 详细输出
uv run pytest -v tests/unit/test_storage.py
```

---

## 4. 隐私与安全红线

> ⚠️ **测试用例中严禁包含真实用户的 GPS 轨迹、心率数据或个人信息。**

### 4.1 正确做法

```python
# ✅ 正确：虚构数据
mock_data = {
    "distance_km": 5.0,      # 虚构距离
    "duration_min": 30,      # 虚构时长
    "avg_hr": 150            # 虚构心率
}

# ✅ 正确：使用测试样本文件
sample_path = FIXTURE_DIR / "easy_run_20240101.fit"
```

### 4.2 错误做法

```python
# ❌ 错误：真实用户数据
real_data = {
    "distance_km": 10.532,   # 真实 GPS 数据
    "route": [(31.2304, 121.4737), ...],  # 真实轨迹
    "hr_data": [142, 145, 148, ...]       # 真实心率
}

# ❌ 错误：真实用户姓名
user_info = {
    "name": "张三",  # 真实姓名
    "email": "zhangsan@example.com"  # 真实邮箱
}
```

---

## 5. 测试命名约定

| 类型 | 约定 | 示例 |
|------|------|------|
| 测试类 | `Test{ClassName}` | `TestStorageManager` |
| 测试函数 | `test_{action}_{case}` | `test_save_to_parquet_success` |
| 测试文件 | `test_{module}.py` | `test_storage.py` |

### 5.1 测试函数命名模式

```python
# 成功场景
def test_save_to_parquet_success():
    ...

# 失败场景
def test_save_to_parquet_invalid_path():
    ...

# 边界场景
def test_save_to_parquet_empty_dataframe():
    ...
```

---

## 6. 覆盖率要求

| 模块 | 最低覆盖率 |
|------|-----------|
| `src/core/` | 80% |
| `src/agents/` | 70% |
| `src/cli.py` | 60% |

```bash
# 检查覆盖率
uv run pytest tests/unit/ --cov=src --cov-report=term-missing
```

---

*文档版本: v1.0.0 | 更新日期: 2026-04-01*
