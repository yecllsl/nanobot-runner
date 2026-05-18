# v0.22.0 Bug修复报告

> **修复日期**: 2026-05-18
> **修复版本**: v0.22.0
> **修复人员**: AI Agent（开发工程师 + 测试工程师协调）

---

## 1. 修复概览

| 缺陷ID | 严重等级 | 优先级 | 模块 | 状态 | 修复类型 |
|--------|----------|--------|------|------|---------|
| BUG-2201 | 严重 | P0 | Cron提醒 | ✅ 已修复 | 代码修复 |
| BUG-2202 | 严重 | P0 | 身体信号 | ✅ 已修复 | 代码修复 |
| BUG-2203 | 严重 | P0 | 数字孪生 | ✅ 已修复 | 代码修复 |
| BUG-2204 | 一般 | P1 | 偏好管理 | ⏳ 待修复 | 需进一步分析 |
| BUG-2205 | 一般 | P1 | 身体信号 | ✅ 已修复 | 代码修复 |
| BUG-2206 | 一般 | P1 | ML预测 | ✅ 已修复 | 文档更新 |
| BUG-2207 | 一般 | P2 | 性能 | ⏳ 待修复 | 需性能优化 |
| BUG-TEST-001 | 一般 | P2 | 测试用例 | ✅ 已修复 | 测试数据 |

---

## 2. BUG-2201: Cron飞书凭证读取失败

### 2.1 问题描述

- **症状**: 配置飞书凭证到.env.local后，`cron status`显示"未配置飞书应用凭证"
- **影响**: 飞书通知功能完全不可用
- **复现率**: 100%

### 2.2 根因分析

`FeishuAuth.__init__`通过`self.config.get("feishu_app_id")`读取凭证，`ConfigManager.get()`内部调用`load_config_with_env_override()`会检查`os.getenv("NANOBOT_FEISHU_APP_ID")`。但`.env.local`文件中的环境变量只有在`EnvManager.load_env()`被调用后才会写入`os.environ`。

`AppContextFactory.create()`会加载`.env.local`，但`FeishuBot()`直接创建`ConfigManager()`时，`.env.local`可能还没被加载到进程环境变量中。

### 2.3 修复方案

**文件**: `src/notify/feishu.py`

在`FeishuAuth.__init__`中增加`.env.local`自动加载逻辑：

```python
def __init__(self, config, app_id=None, app_secret=None):
    self.config = config or ConfigManager()
    self.app_id = app_id or self.config.get("feishu_app_id")
    self.app_secret = app_secret or self.config.get("feishu_app_secret")

    # BUG-2201修复：当凭证缺失时，尝试从.env.local加载
    if not self.app_id or not self.app_secret:
        self._try_load_env_local()
        self.app_id = self.app_id or self.config.get("feishu_app_id")
        self.app_secret = self.app_secret or self.config.get("feishu_app_secret")

def _try_load_env_local(self) -> None:
    """尝试从.env.local加载飞书凭证环境变量"""
    try:
        from src.core.config.env_manager import EnvManager
        env_file = self.config.base_dir / ".env.local"
        if env_file.exists():
            env_manager = EnvManager(env_file=env_file)
            env_manager.load_env()
    except Exception as e:
        logger.debug(f"加载.env.local失败: {e}")
```

### 2.4 验证结果

- **回归测试**: `test_auto_load_env_local_when_config_empty` ✅
- **回归测试**: `test_is_configured_after_env_local_load` ✅
- **状态**: ✅ 通过

---

## 3. BUG-2202: fatigue/recovery未读取已导入数据

### 3.1 问题描述

- **症状**: 导入637条跑步数据后，`analysis fatigue`显示"暂无训练数据"
- **影响**: 疲劳度评估和恢复状态功能完全不可用
- **复现率**: 100%

### 3.2 根因分析

`FatigueAssessor.assess_fatigue()`和`RecoveryMonitor.get_recovery_status()`中，当`calculate_training_load_from_dataframe()`返回`runs_count=0`时，直接判定为`DataQuality.EMPTY`，返回"暂无训练数据"。

但`runs_count=0`有两种情况：
1. 真正没有数据（session_df为空）
2. 有数据但缺少心率信息，导致TSS计算结果全部为0

原代码未区分这两种情况，统一返回"暂无训练数据"，误导用户。

### 3.3 修复方案

**文件**: `src/core/body_signal/fatigue_assessor.py`、`src/core/body_signal/recovery_monitor.py`

在`runs_count == 0`时，检查`session_df`是否真的为空：

```python
if runs_count == 0:
    if session_df.is_empty():
        # 真正没有数据
        return FatigueResult(
            recommendation="暂无训练数据",
            data_quality=DataQuality.EMPTY,
        )
    else:
        # 有数据但缺少心率信息
        return FatigueResult(
            recommendation="训练数据缺少心率信息，无法计算训练负荷，建议使用带有心率监测的设备记录训练",
            data_quality=DataQuality.INSUFFICIENT,
        )
```

### 3.4 验证结果

- **回归测试**: `test_fatigue_with_data_but_no_hr_not_empty` ✅
- **回归测试**: `test_fatigue_with_data_but_no_hr_has_meaningful_message` ✅
- **回归测试**: `test_recovery_with_data_but_no_hr_not_empty` ✅
- **回归测试**: `test_recovery_with_data_but_no_hr_has_meaningful_message` ✅
- **状态**: ✅ 通过

---

## 4. BUG-2203: twin snapshot CTL/ATL与analysis load不一致

### 4.1 问题描述

- **症状**: `analysis load`显示CTL=64.6，但`twin snapshot`显示CTL=0.0
- **影响**: 数字孪生引擎的负荷维度数据不准确
- **复现率**: 100%

### 4.2 根因分析

两个模块使用不同的TSS计算方法：

| 模块 | 方法 | 无心率时行为 |
|------|------|------------|
| `AnalyticsEngine` | `calculate_tss_for_run()` | 基于配速估算IF，返回非零TSS |
| `StateVectorBuilder` | `calculate_tss_batch()` | 无心率时TSS=0，valid_tss为空 |

`calculate_tss_batch()`的原始实现要求心率数据存在才计算TSS，而`calculate_tss_for_run()`在无心率时会基于配速估算intensity factor。

### 4.3 修复方案

**文件**: `src/core/calculators/training_load_analyzer.py`

在`calculate_tss_batch()`中增加无心率时的配速估算逻辑，与`calculate_tss_for_run()`保持一致：

```python
# 原逻辑：无心率时TSS=0
# 修复后：无心率时基于配速估算IF
pace_min_per_km = (pl.col(duration_col) / 60) / (pl.col(distance_col) / 1000)
pace_based_if = 0.8 + (6.0 / pace_min_per_km) * 0.1
hr_based_if = ((pl.col(hr_col) - rest_hr).clip(lower_bound=0) / (max_hr - rest_hr)).clip(upper_bound=1.5)
has_valid_hr = (pl.col(hr_col).is_not_null()) & (pl.col(hr_col) > 0)
intensity_factor = pl.when(has_valid_hr).then(hr_based_if).otherwise(pace_based_if)
```

### 4.4 验证结果

- **回归测试**: `test_build_load_with_hr_data_nonzero` ✅
- **回归测试**: `test_build_load_consistent_with_training_load_analyzer` ✅
- **回归测试**: `test_build_load_without_hr_data_indicates_insufficient` ✅
- **状态**: ✅ 通过

---

## 5. BUG-2205: HRV分析PerformanceWarning

### 5.1 问题描述

- **症状**: 执行`analysis hrv`时输出Polars PerformanceWarning
- **影响**: 用户看到警告信息，体验不佳
- **复现率**: 100%

### 5.2 根因分析

`hrv_analyzer.py`、`fatigue_assessor.py`、`recovery_monitor.py`中使用`lf.columns`触发Polars LazyFrame schema解析警告。

### 5.3 修复方案

**文件**: `src/core/body_signal/hrv_analyzer.py`、`src/core/body_signal/fatigue_assessor.py`、`src/core/body_signal/recovery_monitor.py`

将所有`lf.columns`替换为`lf.collect_schema().names()`：

```python
# 修改前
columns = lf.columns

# 修改后
columns = lf.collect_schema().names()
```

共替换6处：
- `hrv_analyzer.py`: 4处
- `fatigue_assessor.py`: 1处
- `recovery_monitor.py`: 1处

### 5.4 验证结果

- **回归测试**: `test_hrv_analyzer_no_lf_columns_warning` ✅
- **回归测试**: `test_fatigue_assessor_no_lf_columns_warning` ✅
- **回归测试**: `test_recovery_monitor_no_lf_columns_warning` ✅
- **状态**: ✅ 通过

---

## 6. BUG-2206: CLI命令名与文档不一致

### 6.1 问题描述

- **症状**: 文档中写`nanobotrun prediction`，但CLI命令为`nanobotrun predict`
- **影响**: 用户按文档操作报错
- **复现率**: 100%

### 6.2 根因分析

文档编写时未与CLI实现同步。CLI命令注册为`predict`（`src/cli/commands/prediction.py`），但部分文档中写为`prediction`。

### 6.3 修复方案

更新AGENTS.md和相关文档中的命令名为`predict`。此为文档问题，不涉及代码修改。

### 6.4 验证结果

- **CLI验证**: `nanobotrun predict --help` ✅
- **状态**: ✅ 通过

---

## 7. BUG-2204: 训练时段推断不准（待修复）

### 7.1 问题描述

- **症状**: 晚间19:00训练为主，但`preference show`显示"训练时段: 早晨"
- **影响**: 偏好推断不准确

### 7.2 根因分析（初步）

`_analyze_running_time_preference`方法中，当morning和evening计数相等时默认返回"morning"，且`except`分支也默认返回"morning"。更关键的是，`preference show`可能显示的是缓存的旧值，而非实时推断结果。

### 7.3 修复建议

1. 修改推断逻辑：当计数相等时，不默认返回morning，而是返回"数据不足"
2. 确保`preference show`触发实时推断，而非仅读取缓存值
3. 此Bug需进一步分析偏好推断的完整流程，建议下个迭代修复

---

## 8. BUG-2207: 部分命令响应偏慢（待修复）

### 8.1 问题描述

- **症状**: `data stats`耗时20.17s，`twin snapshot`耗时16.36s
- **影响**: 用户体验差

### 8.2 根因分析（初步）

可能存在多次Parquet文件读取或未优化的查询逻辑。前一轮已优化了部分查询（PERF-001/PERF-002），但仍需进一步优化。

### 8.3 修复建议

1. 优化`data stats`的查询逻辑，减少重复文件读取
2. 优化`twin snapshot`的缓存策略，避免每次重新计算
3. 此Bug需性能分析工具辅助定位，建议下个迭代修复

---

## 9. BUG-TEST-001: 测试用例日期过期

### 9.1 问题描述

- **症状**: `test_plan_create_with_options`失败，exit_code=2
- **影响**: 集成测试无法通过

### 9.2 根因分析

测试用例中使用的目标日期`2026-05-01`已过期（当前日期2026-05-18），CLI验证逻辑拒绝了过去日期。

### 9.3 修复方案

**文件**: `tests/integration/module/test_plan_cli_integration_bug001.py`

将过期日期`2026-05-01`更新为`2026-12-01`。

### 9.4 验证结果

- **状态**: ✅ 通过

---

## 10. 回归测试结果

### 10.1 Bug专项回归测试

| 测试文件 | 用例数 | 通过 | 失败 | 状态 |
|---------|--------|------|------|------|
| test_bug2201_feishu_env_fallback.py | 2 | 2 | 0 | ✅ |
| test_bug2202_no_hr_data.py | 4 | 4 | 0 | ✅ |
| test_bug2203_load_consistency.py | 3 | 3 | 0 | ✅ |
| test_bug2205_performance_warning.py | 3 | 3 | 0 | ✅ |

### 10.2 全量单元测试

- **测试命令**: `uv run pytest tests/unit/ --ignore=tests/e2e`
- **结果**: 3736 passed, 1 skipped, 5 warnings
- **状态**: ✅ 全部通过

### 10.3 代码质量检查

| 检查项 | 结果 |
|--------|------|
| ruff check | ✅ All checks passed |
| mypy | ✅ Success: no issues found |

---

## 11. 修复统计

| 严重等级 | 总数 | 已修复 | 待修复 | 修复率 |
|---------|------|--------|--------|--------|
| 严重(P0) | 3 | 3 | 0 | 100% |
| 一般(P1) | 3 | 2 | 1 | 67% |
| 一般(P2) | 2 | 1 | 1 | 50% |
| **合计** | **8** | **6** | **2** | **75%** |

---

## 12. 遗留风险

1. **BUG-2204（训练时段推断不准）**: P1级，需进一步分析偏好推断完整流程，建议下个迭代修复
2. **BUG-2207（命令响应偏慢）**: P2级，需性能分析工具辅助，建议下个迭代优化
3. **BUG-2203修复的副作用**: `calculate_tss_batch()`行为变更（无心率时返回非零TSS），已更新相关测试用例，但需关注线上表现

---

**报告生成时间**: 2026-05-18
**报告状态**: 终版
