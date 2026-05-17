# Bug修复报告 v0.22.0

> **修复日期**: 2026-05-15
> **修复者**: 开发工程师
> **版本**: v0.22.0
> **状态**: 已完成

---

## 修复概览

| Bug ID | 严重等级 | 模块 | 状态 | 修复文件数 | 新增测试数 |
|--------|---------|------|------|-----------|-----------|
| BUG-2201 | 严重 | 配置/Cron | ✅ 已修复 | 1 | 3 |
| BUG-2202 | 严重 | 身体信号 | ✅ 已修复 | 2 | 4 |
| BUG-2203 | 严重 | 数字孪生 | ✅ 已修复 | 1 | 3 |

**合计**: 修复 3 个严重 Bug，修改 4 个源文件，新增 10 个回归测试用例

---

## BUG-2201: ConfigManager.get() 未读取环境变量

### 根因

`ConfigManager.get()` 方法调用 `self.load_config()`，仅从 `config.json` 读取配置。
虽然 `load_config_with_env_override()` 方法已存在且正确映射了 `ENV_KEY_MAPPING`，
但 `get()` 未使用它，导致所有通过 `get()` 读取的配置项无法被环境变量覆盖。

### 修复方案

**文件**: `src/core/config/manager.py`

将 `get()` 方法中的 `self.load_config()` 改为 `self.load_config_with_env_override()`，
使配置读取优先级变为：环境变量 > 配置文件 > 默认值。

### 回归测试

| 测试用例 | 验证内容 | 结果 |
|---------|---------|------|
| `test_get_reads_env_override` | 环境变量覆盖配置文件值 | ✅ 通过 |
| `test_get_env_override_bool_type` | 布尔类型环境变量转换 | ✅ 通过 |
| `test_get_env_override_falls_back_to_file` | 无环境变量时回退到配置文件 | ✅ 通过 |

---

## BUG-2202: fatigue/recovery 传入空DataFrame导致"暂无数据"

### 根因

`FatigueAssessor.assess_fatigue()` 和 `RecoveryMonitor.get_recovery_status()` 都传入
`pl.DataFrame()`（空DataFrame），导致 `calculate_training_load_from_dataframe()` 返回
`runs_count=0`，判断为"暂无训练数据"。

### 修复方案

**文件1**: `src/core/body_signal/fatigue_assessor.py`

从 `self.session_repo.storage.read_parquet()` 读取实际数据，传入
`calculate_training_load_from_dataframe()`。异常时回退到空DataFrame。

**文件2**: `src/core/body_signal/recovery_monitor.py`

同上，从 `self.session_repo.storage.read_parquet()` 读取实际数据。

### 回归测试

| 测试用例 | 验证内容 | 结果 |
|---------|---------|------|
| `test_assess_fatigue_reads_session_data` | fatigue从session_repo读取数据 | ✅ 通过 |
| `test_assess_fatigue_read_parquet_exception` | read_parquet异常时回退 | ✅ 通过 |
| `test_get_recovery_status_reads_session_data` | recovery从session_repo读取数据 | ✅ 通过 |
| `test_get_recovery_status_read_parquet_exception` | read_parquet异常时回退 | ✅ 通过 |

---

## BUG-2203: StateVectorBuilder.build_load() 传入空列表导致CTL/ATL=0

### 根因

`StateVectorBuilder.build_load()` 调用 `calculate_atl_ctl([])` 传入空列表，
导致返回 `{"atl": 0.0, "ctl": 0.0}`，数字孪生快照中CTL/ATL始终为0。

### 修复方案

**文件**: `src/core/twin/state_vector_builder.py`

当 `session_repo` 可用时，从 Parquet 读取数据并调用
`calculate_training_load_from_dataframe()`；否则回退到 `calculate_atl_ctl([])`。
同时新增 `import polars as pl`。

### 回归测试

| 测试用例 | 验证内容 | 结果 |
|---------|---------|------|
| `test_build_load_with_session_data` | 从session_repo读取数据计算CTL/ATL | ✅ 通过 |
| `test_build_load_without_session_repo` | 无session_repo时回退到calculate_atl_ctl | ✅ 通过 |
| `test_build_load_read_parquet_exception` | read_parquet异常时回退到空DataFrame | ✅ 通过 |

---

## 验证结果

### 单元测试

```
uv run pytest tests/unit/core/config/test_manager.py tests/unit/core/body_signal/ tests/unit/core/twin/test_state_vector_builder.py -v --no-cov
结果: 66 passed, 0 failed
```

### 全量单元测试

```
uv run pytest tests/unit/ -v --no-cov
结果: 3353 passed, 1 skipped
注: 1个失败(test_uses_memory_cache_on_second_call)为预存问题，与本次修复无关
```

### Lint检查

```
uv run ruff check src/core/config/manager.py src/core/body_signal/ src/core/twin/state_vector_builder.py
结果: All checks passed!
```

### 类型检查

```
uv run mypy src/core/config/manager.py src/core/body_signal/ src/core/twin/state_vector_builder.py --ignore-missing-imports
结果: Success: no issues found in 4 source files
```

---

## 修改文件清单

| 文件 | 修改类型 | 说明 |
|------|---------|------|
| `src/core/config/manager.py` | 修改 | get()改用load_config_with_env_override() |
| `src/core/body_signal/fatigue_assessor.py` | 修改 | assess_fatigue()从session_repo读取数据 |
| `src/core/body_signal/recovery_monitor.py` | 修改 | get_recovery_status()从session_repo读取数据 |
| `src/core/twin/state_vector_builder.py` | 修改 | build_load()从session_repo读取数据 |
| `tests/unit/core/config/test_manager.py` | 新增测试 | 3个BUG-2201回归测试 |
| `tests/unit/core/body_signal/test_fatigue_assessor.py` | 新增测试 | 2个BUG-2202回归测试 |
| `tests/unit/core/body_signal/test_recovery_monitor.py` | 新增测试 | 2个BUG-2202回归测试 |
| `tests/unit/core/twin/test_state_vector_builder.py` | 修改+新增 | 更新mock + 3个BUG-2203回归测试 |

---

## 已知问题

1. **test_uses_memory_cache_on_second_call 预存失败**: `test_digital_twin_engine.py` 中 `_make_state()` 的 `snapshot_date="2026-05-12"` 已过期，导致缓存失效。此问题在本次修复前已存在，建议后续修复。
