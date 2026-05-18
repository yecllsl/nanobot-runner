# 代码评审整改实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 基于代码评审报告，按5层治理策略全量修复死代码、重复代码、安全审计和代码质量问题

**Architecture:** 按层推进——异常治理→类型治理→去重统一→大文件拆分→清理收尾，每层独立可验证，采用重新导出模式保持导入兼容性

**Tech Stack:** Python 3.11+, Polars, Typer/Rich, ruff, mypy, pytest

---

## 文件结构变更总览

### 新建文件

| 文件 | 职责 |
|------|------|
| `src/core/models/anomaly_schema.py` | AnomalyFilterRule + ANOMALY_FILTER_RULES 统一定义 |
| `src/core/base/formatters.py` | format_pace/format_duration 纯函数 |
| `src/core/constants.py` | 业务常量集中管理 |
| `src/core/base/profile_storage.py` | ProfileStorageManager |
| `src/core/base/profile_schema.py` | RunnerProfile 数据类 |
| `src/core/analytics_effects.py` | 训练效果计算 |
| `src/core/analytics_reports.py` | 报告生成方法 |
| `src/agents/tools_stats.py` | 统计分析工具类 |
| `src/agents/tools_plan.py` | 训练计划工具类 |
| `src/agents/tools_body.py` | 身体状态工具类 |
| `src/agents/tools_twin.py` | 数字孪生工具类 |
| `src/agents/tools_data.py` | 数据管理工具类 |

### 修改文件

| 文件 | 修改内容 |
|------|----------|
| `src/core/base/exceptions.py` | ImportError → DataImportError |
| `src/core/base/__init__.py` | 更新导出名 |
| `src/core/base/profile.py` | 拆分后保留 ProfileEngine + 重新导出 |
| `src/core/analytics.py` | 拆分后保留 AnalyticsEngine + 重新导出 |
| `src/agents/tools.py` | 拆分后保留 BaseTool + RunnerTools + 重新导出 |
| `src/core/report/anomaly_filter.py` | 删除本地定义，从 anomaly_schema 导入 |
| `src/core/calculators/statistics_aggregator.py` | 删除私有格式化方法，从 formatters 导入 |
| `src/core/prediction/race_predictor.py` | 删除私有格式化方法，从 formatters 导入 |
| `src/cli/formatter.py` | 改为调用 base/formatters.py 底层函数 |
| `src/cli/common.py` | 统一 Console 实例来源 |
| `src/cli/handlers/viz_handler.py` | 从 common.py 导入 console |
| `src/core/user_profile_manager.py` | RunnerProfile 改从 profile_schema 导入 |
| `src/core/transparency/error_classifier.py` | ImportError → DataImportError |
| 87 个含 `except Exception` 的文件 | 替换为 `except NanobotRunnerError` |
| 11 个含 `# type: ignore` 的文件 | 修正类型注解 |

---

## 第1层：异常治理

### Task 1: 重命名 ImportError → DataImportError

**Files:**
- Modify: `src/core/base/exceptions.py:69`
- Modify: `src/core/base/__init__.py:17,55`
- Modify: `src/core/transparency/error_classifier.py:13,67`

- [ ] **Step 1: 修改 exceptions.py 中的类名**

将 `class ImportError(NanobotRunnerError):` 改为 `class DataImportError(NanobotRunnerError):`，同时更新 docstring 和 error_code。

```python
@dataclass
class DataImportError(NanobotRunnerError):
    """数据导入相关错误"""

    error_code: str = "IMPORT_ERROR"
    recovery_suggestion: str | None = "请检查文件路径和文件格式"
```

- [ ] **Step 2: 修改 __init__.py 导出**

`src/core/base/__init__.py` 中将 `ImportError` 改为 `DataImportError`：

```python
from src.core.base.exceptions import (
    ...
    DataImportError,
    ...
)

__all__ = [
    ...
    "DataImportError",
    ...
]
```

- [ ] **Step 3: 修改 error_classifier.py**

`src/core/transparency/error_classifier.py` 中更新引用：

```python
from src.core.base.exceptions import (
    ...
    DataImportError,
    ...
)

# 第67行
DataImportError: ErrorCategory.TOOL,
```

- [ ] **Step 4: 验证无其他自定义 ImportError 引用**

Run: `grep -r "from.*exceptions import.*ImportError" src/`
Expected: 0 结果（所有自定义 ImportError 引用已替换）

Run: `grep -rn "class ImportError" src/`
Expected: 0 结果

- [ ] **Step 5: 运行测试验证**

Run: `uv run pytest tests/unit/ -x -q`
Expected: 全部通过

- [ ] **Step 6: 提交**

```bash
git add src/core/base/exceptions.py src/core/base/__init__.py src/core/transparency/error_classifier.py
git commit -m "refactor: rename ImportError to DataImportError to avoid builtin conflict"
```

---

### Task 2: 批量替换 except Exception → except NanobotRunnerError（core/storage 模块）

**Files:**
- Modify: `src/core/storage/importer.py` (2处)
- Modify: `src/core/storage/indexer.py` (1处)
- Modify: `src/core/storage/parquet_manager.py` (17处)
- Modify: `src/core/storage/parser.py` (10处)

- [ ] **Step 1: 确认各文件已导入 NanobotRunnerError**

检查每个文件头部是否已有 `from src.core.base.exceptions import ...` 导入。如没有，添加 `NanobotRunnerError` 到导入列表。对于已有具体异常导入的文件（如 `importer.py` 已导入 `ParseError`），追加 `NanobotRunnerError`。

- [ ] **Step 2: 逐文件替换 except Exception**

对每个文件执行：将 `except Exception` 替换为 `except NanobotRunnerError`。

**importer.py** — 2处（约第90行、第137行）
**indexer.py** — 1处
**parquet_manager.py** — 17处（最密集的存储文件）
**parser.py** — 10处

替换规则：
- `except Exception as e:` → `except NanobotRunnerError as e:`
- `except Exception:` → `except NanobotRunnerError:`
- 保留 except 块体不变

- [ ] **Step 3: 运行测试验证**

Run: `uv run pytest tests/unit/ -x -q -k "storage or importer or parser or parquet"`
Expected: 全部通过

- [ ] **Step 4: 提交**

```bash
git add src/core/storage/
git commit -m "refactor: replace except Exception with NanobotRunnerError in storage module"
```

---

### Task 3: 批量替换 except Exception（core/base + core/config 模块）

**Files:**
- Modify: `src/core/base/profile.py` (21处)
- Modify: `src/core/base/decorators.py` (2处)
- Modify: `src/core/config/manager.py` (4处)
- Modify: `src/core/config/sync.py` (2处)

- [ ] **Step 1: 确认各文件已导入 NanobotRunnerError**

- [ ] **Step 2: 逐文件替换 except Exception → except NanobotRunnerError**

**profile.py** — 21处（最密集的 base 文件）
**decorators.py** — 2处
**manager.py** — 4处
**sync.py** — 2处

- [ ] **Step 3: 运行测试验证**

Run: `uv run pytest tests/unit/ -x -q -k "profile or config or decorator"`
Expected: 全部通过

- [ ] **Step 4: 提交**

```bash
git add src/core/base/ src/core/config/
git commit -m "refactor: replace except Exception with NanobotRunnerError in base and config modules"
```

---

### Task 4: 批量替换 except Exception（core/prediction 模块）

**Files:**
- Modify: `src/core/prediction/vdot_predictor.py` (11处)
- Modify: `src/core/prediction/race_predictor.py` (4处)
- Modify: `src/core/prediction/training_response_predictor.py` (2处)
- Modify: `src/core/prediction/feature_engine.py` (10处)
- Modify: `src/core/prediction/injury_predictor.py` (14处)
- Modify: `src/core/prediction/model_manager.py` (4处)
- Modify: `src/core/prediction/prediction_engine.py` (1处)
- Modify: `src/core/prediction/data_assessor.py` (1处)
- Modify: `src/core/prediction/baselines/banister_ir.py` (1处)

- [ ] **Step 1: 确认各文件已导入 NanobotRunnerError**

- [ ] **Step 2: 逐文件替换 except Exception → except NanobotRunnerError**

注意：`model_manager.py` 中有 `except ImportError:` 捕获 Python 内置 ImportError（检测 joblib 是否安装），这些**不要替换**，它们是合法的内置异常捕获。仅替换 `except Exception` 的实例。

- [ ] **Step 3: 运行测试验证**

Run: `uv run pytest tests/unit/ -x -q -k "prediction or vdot or injury or race_predictor or feature_engine"`
Expected: 全部通过

- [ ] **Step 4: 提交**

```bash
git add src/core/prediction/
git commit -m "refactor: replace except Exception with NanobotRunnerError in prediction module"
```

---

### Task 5: 批量替换 except Exception（core/plan 模块）

**Files:**
- Modify: `src/core/plan/gateway_integration.py` (3处)
- Modify: `src/core/plan/hard_validator.py` (1处)
- Modify: `src/core/plan/heartbeat_tasks.py` (2处)
- Modify: `src/core/plan/training_reminder_manager.py` (7处)
- Modify: `src/core/plan/cron_callback.py` (1处)
- Modify: `src/core/plan/plan_manager.py` (5处)
- Modify: `src/core/plan/plan_generator.py` (2处)
- Modify: `src/core/plan/plan_adjustment_validator.py` (1处)
- Modify: `src/core/plan/long_term_plan_generator.py` (1处)
- Modify: `src/core/plan/calendar_tool.py` (9处)
- Modify: `src/core/plan/goal_prediction_engine.py` (1处)
- Modify: `src/core/plan/notify_tool.py` (1处)
- Modify: `src/core/plan/training_response_analyzer.py` (1处)

- [ ] **Step 1: 确认各文件已导入 NanobotRunnerError**

- [ ] **Step 2: 逐文件替换 except Exception → except NanobotRunnerError**

- [ ] **Step 3: 运行测试验证**

Run: `uv run pytest tests/unit/ -x -q -k "plan"`
Expected: 全部通过

- [ ] **Step 4: 提交**

```bash
git add src/core/plan/
git commit -m "refactor: replace except Exception with NanobotRunnerError in plan module"
```

---

### Task 6: 批量替换 except Exception（core/report + core/export + core/calculators 模块）

**Files:**
- Modify: `src/core/report/generator.py` (5处)
- Modify: `src/core/report/service.py` (16处)
- Modify: `src/core/report/anomaly_filter.py` (2处)
- Modify: `src/core/export/parquet_exporter.py` (2处)
- Modify: `src/core/export/engine.py` (3处)
- Modify: `src/core/calculators/training_load_analyzer.py` (2处)
- Modify: `src/core/calculators/heart_rate_analyzer.py` (3处)
- Modify: `src/core/calculators/race_prediction.py` (2处)
- Modify: `src/core/calculators/statistics_aggregator.py` (7处)
- Modify: `src/core/calculators/training_history_analyzer.py` (7处)

- [ ] **Step 1: 确认各文件已导入 NanobotRunnerError**

- [ ] **Step 2: 逐文件替换 except Exception → except NanobotRunnerError**

- [ ] **Step 3: 运行测试验证**

Run: `uv run pytest tests/unit/ -x -q -k "report or export or calculator or aggregator or analyzer"`
Expected: 全部通过

- [ ] **Step 4: 提交**

```bash
git add src/core/report/ src/core/export/ src/core/calculators/
git commit -m "refactor: replace except Exception with NanobotRunnerError in report, export, calculators modules"
```

---

### Task 7: 批量替换 except Exception（core/twin + core/body_signal + core/其余模块）

**Files:**
- Modify: `src/core/twin/state_vector_builder.py` (5处)
- Modify: `src/core/twin/digital_twin_engine.py` (2处)
- Modify: `src/core/twin/whatif_simulator.py` (2处)
- Modify: `src/core/body_signal/recovery_monitor.py` (1处)
- Modify: `src/core/body_signal/fatigue_assessor.py` (1处)
- Modify: `src/core/analytics.py` (5处)
- Modify: `src/core/provider_adapter.py` (3处)
- Modify: `src/core/user_profile_manager.py` (4处)
- Modify: `src/core/validate/validator.py` (5处)
- Modify: `src/core/verify_manager.py` (2处)
- Modify: `src/core/init/wizard.py` (2处)
- Modify: `src/core/init/generator.py` (1处)
- Modify: `src/core/init/migrate.py` (2处)
- Modify: `src/core/llm_timeout.py` (2处)
- Modify: `src/core/transparency/error_handling_hook.py` (1处)
- Modify: `src/core/transparency/streaming_hook.py` (1处)
- Modify: `src/core/transparency/trace_logger.py` (1处)
- Modify: `src/core/diagnosis/self_diagnosis.py` (1处)
- Modify: `src/core/diagnosis/mytool_integration.py` (1处)
- Modify: `src/core/memory/dream_integration.py` (1处)
- Modify: `src/core/memory/memory_manager.py` (11处)
- Modify: `src/core/tools/mcp_connector.py` (1处)
- Modify: `src/core/skills/skill_manager.py` (7处)
- Modify: `src/core/migrate/engine.py` (1处)

- [ ] **Step 1: 确认各文件已导入 NanobotRunnerError**

- [ ] **Step 2: 逐文件替换 except Exception → except NanobotRunnerError**

注意：`provider_adapter.py` 中有 `except (ImportError, Exception) as e:` 和 `except (ImportError, FileNotFoundError, ValueError) as e:`，这些是捕获 Python 内置异常的组合，需要特殊处理：
- `except (ImportError, Exception) as e:` → `except (ImportError, NanobotRunnerError) as e:`（此处 ImportError 是 Python 内置的）
- `except (ImportError, FileNotFoundError, ValueError) as e:` 保持不变（都是 Python 内置异常）

- [ ] **Step 3: 运行测试验证**

Run: `uv run pytest tests/unit/ -x -q`
Expected: 全部通过

- [ ] **Step 4: 提交**

```bash
git add src/core/twin/ src/core/body_signal/ src/core/analytics.py src/core/provider_adapter.py src/core/user_profile_manager.py src/core/validate/ src/core/verify_manager.py src/core/init/ src/core/llm_timeout.py src/core/transparency/ src/core/diagnosis/ src/core/memory/ src/core/tools/ src/core/skills/ src/core/migrate/
git commit -m "refactor: replace except Exception with NanobotRunnerError in remaining core modules"
```

---

### Task 8: 批量替换 except Exception（agents + cli + notify 模块）

**Files:**
- Modify: `src/agents/tools.py` (45处)
- Modify: `src/cli/commands/plan.py` (8处)
- Modify: `src/cli/commands/prediction.py` (10处)
- Modify: `src/cli/commands/data.py` (3处)
- Modify: `src/cli/commands/gateway.py` (2处)
- Modify: `src/cli/commands/agent.py` (4处)
- Modify: `src/cli/commands/twin.py` (3处)
- Modify: `src/cli/commands/analysis.py` (8处)
- Modify: `src/cli/commands/status.py` (2处)
- Modify: `src/cli/commands/viz.py` (3处)
- Modify: `src/cli/commands/export.py` (2处)
- Modify: `src/cli/commands/cron.py` (5处)
- Modify: `src/cli/commands/report.py` (5处)
- Modify: `src/cli/commands/skill.py` (5处)
- Modify: `src/cli/commands/system.py` (2处)
- Modify: `src/cli/commands/tools.py` (7处)
- Modify: `src/cli/commands/preference.py` (7处)
- Modify: `src/cli/handlers/viz_handler.py` (4处)
- Modify: `src/cli/streaming.py` (1处)
- Modify: `src/cli/utils.py` (1处)
- Modify: `src/notify/feishu.py` (2处)
- Modify: `src/notify/feishu_calendar.py` (6处)
- Modify: `src/__init__.py` (1处)

- [ ] **Step 1: 确认各文件已导入 NanobotRunnerError**

对于 cli/commands/ 下的文件，通常需要添加：
```python
from src.core.base.exceptions import NanobotRunnerError
```

对于 `agents/tools.py`，确认是否已有导入。

- [ ] **Step 2: 逐文件替换 except Exception → except NanobotRunnerError**

- [ ] **Step 3: 运行测试验证**

Run: `uv run pytest tests/unit/ -x -q`
Expected: 全部通过

- [ ] **Step 4: 全局验证裸 Exception 清零**

Run: `grep -r "except Exception" src/`
Expected: 0 结果

Run: `grep -rc "except NanobotRunnerError" src/ | grep -v ":0$" | wc -l`
Expected: 接近 87 个文件

- [ ] **Step 5: 提交**

```bash
git add src/agents/ src/cli/ src/notify/ src/__init__.py
git commit -m "refactor: replace except Exception with NanobotRunnerError in agents, cli, notify modules"
```

---

### Task 9: 第1层整体验证

- [ ] **Step 1: 运行全量单元测试**

Run: `uv run pytest tests/unit/ -x -q`
Expected: 全部通过

- [ ] **Step 2: 运行 ruff 检查**

Run: `uv run ruff check src/`
Expected: 无新增错误

- [ ] **Step 3: 运行 mypy 检查**

Run: `uv run mypy src/ --ignore-missing-imports`
Expected: 无新增错误

- [ ] **Step 4: 确认裸 Exception 清零**

Run: `grep -r "except Exception" src/`
Expected: 0 结果

---

## 第2层：类型治理

### Task 10: 消除 profile.py 中的 type:ignore（9处）

**Files:**
- Modify: `src/core/base/profile.py:333,339,340,341,662,1132,1194,1195,1347`

- [ ] **Step 1: 修复 arg-type 类型不匹配（第333,339,340,341行）**

这些行在构造函数调用中传入的类型与参数声明不匹配。使用 `cast()` 修正：

```python
from typing import cast

# 第333行
fitness_level=cast(str, fitness_level),

# 第339-341行
avg_heart_rate=cast(float | None, profile_data.get("avg_heart_rate")),
max_heart_rate=cast(float | None, profile_data.get("max_heart_rate")),
resting_heart_rate=cast(float | None, profile_data.get("resting_heart_rate")),
```

- [ ] **Step 2: 修复 no-redef（第662行）**

`class RunnerProfile:  # type: ignore[no-redef]` — 此问题将在第4层通过 `profile_schema.py` 根治。当前先保留此行，但将裸 `# type: ignore[no-redef]` 补充为具体规则编号（已是具体编号，无需修改）。

- [ ] **Step 3: 修复 assignment 类型（第1132行）**

```python
profile.fitness_level = cast(str, self.get_fitness_level(profile.avg_vdot))
```

- [ ] **Step 4: 修复 arg-type,assignment（第1194,1195行）**

```python
profile.avg_heart_rate = cast(float | None, float(avg_hr) if avg_hr is not None else None)
profile.max_heart_rate = cast(float | None, float(max_hr) if max_hr is not None else None)
```

- [ ] **Step 5: 修复 arg-type（第1347行）**

```python
std_dev = cast(float, float(std_dev_value) if std_dev_value is not None else 0.0)
```

- [ ] **Step 6: 运行 mypy 验证**

Run: `uv run mypy src/core/base/profile.py --ignore-missing-imports`
Expected: 无 type:ignore 相关错误

- [ ] **Step 7: 提交**

```bash
git add src/core/base/profile.py
git commit -m "refactor: fix type annotations in profile.py, remove type:ignore"
```

---

### Task 11: 消除 context.py 中的裸 type:ignore（4处）

**Files:**
- Modify: `src/core/base/context.py:540,542,545,546`

- [ ] **Step 1: 修复裸 # type: ignore**

这4处是在 `AppContext` 构造时传入 `None` 作为占位符。修正方式：使用 `cast()` 或 `Optional` 类型：

```python
from typing import cast
from src.core.storage.importer import FitImporter
from src.core.base.profile import ProfileEngine
from src.core.report.service import ReportService
from src.core.plan.plan_manager import PlanManager

importer=cast(FitImporter | None, None),
profile_engine=cast(ProfileEngine | None, None),
report_service=cast(ReportService | None, None),
plan_manager=cast(PlanManager | None, None),
```

- [ ] **Step 2: 运行 mypy 验证**

Run: `uv run mypy src/core/base/context.py --ignore-missing-imports`
Expected: 无 type:ignore 相关错误

- [ ] **Step 3: 提交**

```bash
git add src/core/base/context.py
git commit -m "refactor: fix bare type:ignore in context.py with proper type annotations"
```

---

### Task 12: 消除其余文件中的 type:ignore（12处）

**Files:**
- Modify: `src/core/calculators/training_load_analyzer.py:49` (arg-type)
- Modify: `src/core/report/service.py:1177` (assignment)
- Modify: `src/notify/feishu_calendar.py:204` (assignment)
- Modify: `src/core/storage/parquet_manager.py:210` (裸 ignore)
- Modify: `src/core/storage/parser.py:20,377` (no-untyped-def, operator)
- Modify: `src/core/config/schema.py:91` (arg-type)
- Modify: `src/core/calculators/heart_rate_analyzer.py:131,132,136` (arg-type)
- Modify: `src/core/calculators/statistics_aggregator.py:184` (arg-type)
- Modify: `src/core/personality/preference_learner.py:307` (arg-type)

- [ ] **Step 1: 修复 training_load_analyzer.py**

```python
avg_hr: float = float(cast(float, heart_rate_data.mean()))
```

- [ ] **Step 2: 修复 report/service.py**

```python
report_dict = cast(dict[str, Any], report_data)
```

- [ ] **Step 3: 修复 feishu_calendar.py**

```python
payload["reminders"] = cast(list[dict[str, Any]], event.reminders)
```

- [ ] **Step 4: 修复 parquet_manager.py**

```python
all_schemas[col_name] = cast(pl.DataType, pl.Utf8)
```

- [ ] **Step 5: 修复 parser.py**

第20行 — 添加类型注解：
```python
def _patched_parse_definition_message(self, header: Any) -> None:
```

第377行：
```python
threshold = cast(float, avg_gap * 2.0 if avg_gap is not None else 0.0)
```

- [ ] **Step 6: 修复 config/schema.py**

```python
t.__name__ if hasattr(t, "__name__") else cast(str, str(t))
```

- [ ] **Step 7: 修复 heart_rate_analyzer.py（3处）**

```python
first_half_mean = float(cast(float, first_half_hr.mean()))
second_half_mean = float(cast(float, second_half_hr.mean()))
overall_mean = float(cast(float, hr_series.mean()))
```

- [ ] **Step 8: 修复 statistics_aggregator.py**

```python
float(cast(float, avg_heart_rate_result))
```

- [ ] **Step 9: 修复 preference_learner.py**

```python
winner = max(votes, key=cast(Callable[[str], int], votes.get))
```

- [ ] **Step 10: 运行 mypy 全量验证**

Run: `uv run mypy src/ --ignore-missing-imports`
Expected: 无新增错误

- [ ] **Step 11: 确认 type:ignore 清零**

Run: `grep -r "# type: ignore" src/`
Expected: 0 结果（第662行的 no-redef 在第4层根治前暂时保留，但应已通过 profile_schema.py 消除）

- [ ] **Step 12: 提交**

```bash
git add src/core/calculators/ src/core/report/ src/notify/ src/core/storage/ src/core/config/ src/core/personality/
git commit -m "refactor: fix all type:ignore annotations across codebase"
```

---

### Task 13: 第2层整体验证

- [ ] **Step 1: 运行全量单元测试**

Run: `uv run pytest tests/unit/ -x -q`
Expected: 全部通过

- [ ] **Step 2: 运行 ruff + mypy**

Run: `uv run ruff check src/ && uv run mypy src/ --ignore-missing-imports`
Expected: 无新增错误

---

## 第3层：去重统一

### Task 14: 统一 AnomalyFilterRule + ANOMALY_FILTER_RULES

**Files:**
- Create: `src/core/models/anomaly_schema.py`
- Modify: `src/core/base/profile.py` (删除本地 AnomalyFilterRule 和 ANOMALY_FILTER_RULES 定义)
- Modify: `src/core/report/anomaly_filter.py` (删除本地定义，从 anomaly_schema 导入)

- [ ] **Step 1: 创建 anomaly_schema.py**

读取 `src/core/base/profile.py` 中完整的 `AnomalyFilterRule`（含 `clip_value`）和 `ANOMALY_FILTER_RULES`（13条规则），将它们迁移到新文件：

```python
from dataclasses import dataclass

@dataclass
class AnomalyFilterRule:
    field_name: str
    condition: str
    threshold: float
    action: str
    clip_value: float | None = None
    description: str | None = None

ANOMALY_FILTER_RULES: list[AnomalyFilterRule] = [
    AnomalyFilterRule(
        field_name="avg_heart_rate", condition="<", threshold=30,
        action="filter", description="过滤平均心率过低的数据（< 30 bpm）",
    ),
    AnomalyFilterRule(
        field_name="avg_heart_rate", condition=">", threshold=220,
        action="filter", description="过滤平均心率过高的数据（> 220 bpm）",
    ),
    AnomalyFilterRule(
        field_name="max_heart_rate", condition="<", threshold=50,
        action="filter", description="过滤最大心率过低的数据（< 50 bpm）",
    ),
    AnomalyFilterRule(
        field_name="max_heart_rate", condition=">", threshold=250,
        action="filter", description="过滤最大心率过高的数据（> 250 bpm）",
    ),
    AnomalyFilterRule(
        field_name="total_distance", condition="<", threshold=100,
        action="filter", description="过滤距离过短的数据（< 100 米）",
    ),
    AnomalyFilterRule(
        field_name="total_distance", condition=">", threshold=100000,
        action="filter", description="过滤距离过长的数据（> 100 公里）",
    ),
    AnomalyFilterRule(
        field_name="total_timer_time", condition="<", threshold=60,
        action="filter", description="过滤时长过短的数据（< 1 分钟）",
    ),
    AnomalyFilterRule(
        field_name="total_timer_time", condition=">", threshold=28800,
        action="filter", description="过滤时长过长的数据（> 8 小时）",
    ),
    AnomalyFilterRule(
        field_name="pace_min_per_km", condition=">", threshold=20,
        action="filter", clip_value=20.0,
        description="过滤配速过慢的数据（> 20 min/km）",
    ),
    AnomalyFilterRule(
        field_name="vdot", condition="<", threshold=20,
        action="filter", description="过滤 VDOT 过低的数据（< 20）",
    ),
    AnomalyFilterRule(
        field_name="vdot", condition=">", threshold=85,
        action="filter", description="过滤 VDOT 过高的数据（> 85）",
    ),
]
```

- [ ] **Step 2: 修改 profile.py — 删除本地定义，改为导入**

删除 profile.py 中的 `AnomalyFilterRule` 类定义和 `ANOMALY_FILTER_RULES` 列表定义，添加：

```python
from src.core.models.anomaly_schema import AnomalyFilterRule, ANOMALY_FILTER_RULES
```

- [ ] **Step 3: 修改 anomaly_filter.py — 删除本地定义，改为导入**

删除 anomaly_filter.py 中的 `AnomalyFilterRule` 类定义和 `ANOMALY_FILTER_RULES` 列表定义，添加：

```python
from src.core.models.anomaly_schema import AnomalyFilterRule, ANOMALY_FILTER_RULES
```

- [ ] **Step 4: 运行测试验证**

Run: `uv run pytest tests/unit/ -x -q -k "anomaly or profile"`
Expected: 全部通过

- [ ] **Step 5: 提交**

```bash
git add src/core/models/anomaly_schema.py src/core/base/profile.py src/core/report/anomaly_filter.py
git commit -m "refactor: unify AnomalyFilterRule and ANOMALY_FILTER_RULES into anomaly_schema.py"
```

---

### Task 15: 统一 format_pace / format_duration

**Files:**
- Create: `src/core/base/formatters.py`
- Modify: `src/cli/formatter.py`
- Modify: `src/core/calculators/statistics_aggregator.py`
- Modify: `src/core/prediction/race_predictor.py`

- [ ] **Step 1: 创建 formatters.py**

读取 `src/cli/formatter.py` 和 `src/core/calculators/statistics_aggregator.py` 中的格式化函数，提取纯逻辑到新文件：

```python
def format_pace(seconds_per_km: float) -> str:
    """将秒/公里转换为 M'SS"/km 格式"""
    if seconds_per_km <= 0 or not math.isfinite(seconds_per_km):
        return "--'--\""
    minutes = int(seconds_per_km // 60)
    seconds = int(seconds_per_km % 60)
    return f"{minutes}'{seconds:02d}\"/km"

def format_duration(total_seconds: float) -> str:
    """将秒转换为 HH:MM:SS 格式"""
    if total_seconds <= 0 or not math.isfinite(total_seconds):
        return "00:00:00"
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
```

- [ ] **Step 2: 修改 cli/formatter.py — 委托调用**

将 `format_pace` 和 `format_duration` 改为从 `formatters.py` 导入并可能增强：

```python
from src.core.base.formatters import format_pace as _format_pace, format_duration as _format_duration

def format_pace(seconds_per_km: float) -> str:
    return _format_pace(seconds_per_km)

def format_duration(total_seconds: float) -> str:
    return _format_duration(total_seconds)
```

- [ ] **Step 3: 修改 statistics_aggregator.py — 删除私有方法**

删除 `_format_pace` 和 `_format_duration` 私有方法，添加导入：

```python
from src.core.base.formatters import format_pace, format_duration
```

将所有 `self._format_pace(...)` 替换为 `format_pace(...)`，`self._format_duration(...)` 替换为 `format_duration(...)`。

- [ ] **Step 4: 修改 race_predictor.py — 删除静态方法**

删除 `_format_pace` 静态方法，添加导入：

```python
from src.core.base.formatters import format_pace
```

将所有 `self._format_pace(...)` 或 `RacePredictor._format_pace(...)` 替换为 `format_pace(...)`。

- [ ] **Step 5: 运行测试验证**

Run: `uv run pytest tests/unit/ -x -q -k "formatter or aggregator or race_predictor"`
Expected: 全部通过

- [ ] **Step 6: 提交**

```bash
git add src/core/base/formatters.py src/cli/formatter.py src/core/calculators/statistics_aggregator.py src/core/prediction/race_predictor.py
git commit -m "refactor: unify format_pace/format_duration into base/formatters.py"
```

---

### Task 16: 统一 Console 实例

**Files:**
- Modify: `src/cli/common.py`
- Modify: `src/cli/formatter.py`
- Modify: `src/cli/handlers/viz_handler.py`

- [ ] **Step 1: 确认 common.py 中的 Console 实例**

`src/cli/common.py` 已有 `console = Console()`，保持不变。

- [ ] **Step 2: 修改 formatter.py — 从 common.py 导入**

删除 `console = Console()` 行，添加：

```python
from src.cli.common import console
```

- [ ] **Step 3: 修改 viz_handler.py — 从 common.py 导入**

删除 `console = Console(force_terminal=True, width=_get_terminal_width(None))` 行，添加：

```python
from src.cli.common import console
```

如果 viz_handler 需要特殊 Console 配置，创建局部变量：

```python
from src.cli.common import console as _default_console

# 在需要 force_terminal 的方法中
viz_console = Console(force_terminal=True, width=_get_terminal_width(None))
```

- [ ] **Step 4: 运行测试验证**

Run: `uv run pytest tests/unit/ -x -q`
Expected: 全部通过

- [ ] **Step 5: 提交**

```bash
git add src/cli/common.py src/cli/formatter.py src/cli/handlers/viz_handler.py
git commit -m "refactor: unify Console instance to cli/common.py"
```

---

### Task 17: 提取训练效果通用计算方法

**Files:**
- Modify: `src/core/analytics.py`

- [ ] **Step 1: 添加通用 _calculate_training_effect 方法**

在 `AnalyticsEngine` 类中添加：

```python
@staticmethod
def _calculate_training_effect(
    total_duration: float,
    zone_times: dict[str, float],
    weights: dict[str, float],
    scale: float,
) -> float:
    if total_duration == 0:
        return 1.0
    weighted_time = sum(zone_times.get(z, 0) * w for z, w in weights.items())
    ratio = weighted_time / total_duration
    effect = 1.0 + ratio * scale
    return round(min(max(effect, 1.0), 5.0), 1)
```

- [ ] **Step 2: 重构 _calculate_aerobic_effect**

```python
def _calculate_aerobic_effect(self, zone_time: dict[str, int], total_duration: int) -> float:
    aerobic_weights = {"zone2": 0.8, "zone3": 1.0}
    return self._calculate_training_effect(float(total_duration), {k: float(v) for k, v in zone_time.items()}, aerobic_weights, 4.0)
```

- [ ] **Step 3: 重构 _calculate_anaerobic_effect**

```python
def _calculate_anaerobic_effect(self, zone_time: dict[str, int], total_duration: int) -> float:
    anaerobic_weights = {"zone4": 0.8, "zone5": 1.2}
    return self._calculate_training_effect(float(total_duration), {k: float(v) for k, v in zone_time.items()}, anaerobic_weights, 6.67)
```

注意：有氧效果 scale=4.0（ratio 0.0→1.0, 0.5→3.0, 1.0→5.0），无氧效果 scale=6.67（ratio 0.0→1.0, 0.3→3.0, 0.6→5.0）。这些值从原方法中精确提取。

- [ ] **Step 4: 运行测试验证**

Run: `uv run pytest tests/unit/ -x -q -k "analytics or training_effect"`
Expected: 全部通过

- [ ] **Step 5: 提交**

```bash
git add src/core/analytics.py
git commit -m "refactor: extract _calculate_training_effect common method in analytics"
```

---

### Task 18: 第3层整体验证

- [ ] **Step 1: 运行全量单元测试**

Run: `uv run pytest tests/unit/ -x -q`
Expected: 全部通过

- [ ] **Step 2: 运行 ruff + mypy**

Run: `uv run ruff check src/ && uv run mypy src/ --ignore-missing-imports`
Expected: 无新增错误

- [ ] **Step 3: 验证去重结果**

Run: `grep -rn "class AnomalyFilterRule" src/`
Expected: 仅 `src/core/models/anomaly_schema.py` 一处

Run: `grep -rn "ANOMALY_FILTER_RULES" src/ | grep -v "import\|from"`
Expected: 仅 `src/core/models/anomaly_schema.py` 一处定义

---

## 第4层：大文件拆分

### Task 19: 拆分 tools.py（4364行 → 5个模块）

**Files:**
- Create: `src/agents/tools_stats.py`
- Create: `src/agents/tools_plan.py`
- Create: `src/agents/tools_body.py`
- Create: `src/agents/tools_twin.py`
- Create: `src/agents/tools_data.py`
- Modify: `src/agents/tools.py`

- [ ] **Step 1: 分析 tools.py 中的工具类清单**

读取 tools.py，按业务域将 47 个工具类分组：

**tools_stats.py** — 统计分析工具（8个）：
- GetRunningStatsTool, GetRecentRunsTool, CalculateVdotForRunTool, GetVdotTrendTool
- GetHrDriftAnalysisTool, GetTrainingLoadTool, QueryByDateRangeTool, QueryByDistanceTool

**tools_plan.py** — 训练计划工具（9个）：
- GenerateTrainingPlanTool, RecordPlanExecutionTool, GetPlanExecutionStatsTool
- AnalyzeTrainingResponseTool, AdjustPlanTool, GetPlanAdjustmentSuggestionsTool
- EvaluateGoalAchievementTool, CreateLongTermPlanTool, GetSmartTrainingAdviceTool
- GetWeatherTrainingAdviceTool

**tools_body.py** — 身体状态工具（8个）：
- GetHrvAnalysisTool, GetHrRecoveryTool, GetFatigueScoreTool, GetRecoveryStatusTool
- GetBodySignalSummaryTool, CompareTrainingPeriodsTool, ReportInjuryTool
- AskUserConfirmTool, ParseUserConfirmTool

**tools_twin.py** — 数字孪生 + 预测工具（10个）：
- GetTwinSnapshotTool, SimulateTwinTool, CompareTwinPlansTool
- PredictVdotTrendTool, PredictRaceResultTool, PredictInjuryRiskTool
- PredictTrainingResponseTool, CheckPredictionStatusTool, ManagePredictionModelTool
- SpawnSubagentTool

**tools_data.py** — 数据管理 + 透明化 + 偏好工具（12个）：
- UpdateMemoryTool, DiagnoseSuggestionTool, DiagnoseErrorTool
- GetPersonalizedSuggestionTool, RecordFeedbackTool
- GetUserPreferencesTool, UpdateUserPreferencesTool
- ExplainDecisionTool, TraceDataSourcesTool, GetTransparencyInsightTool

- [ ] **Step 2: 创建 tools_stats.py**

将统计分析相关工具类迁移到 `tools_stats.py`，保持每个类的完整代码。文件头部添加必要导入。

- [ ] **Step 3: 创建 tools_plan.py**

将训练计划相关工具类迁移。

- [ ] **Step 4: 创建 tools_body.py**

将身体状态相关工具类迁移。

- [ ] **Step 5: 创建 tools_twin.py**

将数字孪生相关工具类迁移。

- [ ] **Step 6: 创建 tools_data.py**

将数据管理相关工具类迁移。

- [ ] **Step 7: 重写 tools.py 为聚合入口**

```python
from src.agents.tools_stats import ...
from src.agents.tools_plan import ...
from src.agents.tools_body import ...
from src.agents.tools_twin import ...
from src.agents.tools_data import ...

# BaseTool 和 RunnerTools 保留在此文件
class BaseTool:
    ...

class RunnerTools:
    ...

__all__ = [...]
```

- [ ] **Step 8: 运行测试验证**

Run: `uv run pytest tests/unit/ -x -q`
Expected: 全部通过

- [ ] **Step 9: 验证导入兼容性**

Run: `python -c "from src.agents.tools import RunnerTools; print('OK')"`
Expected: OK

- [ ] **Step 10: 提交**

```bash
git add src/agents/
git commit -m "refactor: split tools.py into domain-specific modules (stats, plan, body, twin, data)"
```

---

### Task 20: 拆分 profile.py（1594行 → 3个模块）

**Files:**
- Create: `src/core/base/profile_storage.py`
- Create: `src/core/base/profile_schema.py`
- Modify: `src/core/base/profile.py`
- Modify: `src/core/user_profile_manager.py`

- [ ] **Step 1: 创建 profile_schema.py**

将 `RunnerProfile` 数据类定义迁移到 `profile_schema.py`。确保包含所有字段和类型注解，消除 `# type: ignore[no-redef]`。

- [ ] **Step 2: 创建 profile_storage.py**

将 `ProfileStorageManager` 类迁移到 `profile_storage.py`。

- [ ] **Step 3: 重写 profile.py 为聚合入口**

保留 `ProfileEngine` 类 + 重新导出：

```python
from src.core.base.profile_schema import RunnerProfile
from src.core.base.profile_storage import ProfileStorageManager
from src.core.models.anomaly_schema import AnomalyFilterRule, ANOMALY_FILTER_RULES

class ProfileEngine:
    ...

__all__ = ["ProfileEngine", "RunnerProfile", "ProfileStorageManager", "AnomalyFilterRule", "ANOMALY_FILTER_RULES"]
```

- [ ] **Step 4: 修改 user_profile_manager.py**

将 `RunnerProfile` 的导入改为从 `profile_schema.py`：

```python
from src.core.base.profile_schema import RunnerProfile
```

- [ ] **Step 5: 运行测试验证**

Run: `uv run pytest tests/unit/ -x -q -k "profile"`
Expected: 全部通过

- [ ] **Step 6: 验证 no-redef 消除**

Run: `grep -n "no-redef" src/core/base/profile.py`
Expected: 0 结果

- [ ] **Step 7: 提交**

```bash
git add src/core/base/profile.py src/core/base/profile_schema.py src/core/base/profile_storage.py src/core/user_profile_manager.py
git commit -m "refactor: split profile.py into profile_engine, profile_storage, profile_schema"
```

---

### Task 21: 拆分 analytics.py（1585行 → 3个模块）

**Files:**
- Create: `src/core/analytics_effects.py`
- Create: `src/core/analytics_reports.py`
- Modify: `src/core/analytics.py`

- [ ] **Step 1: 创建 analytics_effects.py**

将训练效果计算相关方法迁移：
- `_calculate_training_effect`（通用方法）
- `_calculate_aerobic_effect`
- `_calculate_anaerobic_effect`

导出为模块级函数，`AnalyticsEngine` 通过组合调用。

- [ ] **Step 2: 创建 analytics_reports.py**

将报告生成相关方法迁移：
- `generate_daily_report`
- `_generate_morning_report`
- `_generate_weekly_report`
- 其他 `generate_*` / `_generate_*` 方法

导出为模块级函数。

- [ ] **Step 3: 重写 analytics.py 为聚合入口**

保留 `AnalyticsEngine` 类 + 重新导出：

```python
from src.core.analytics_effects import (
    calculate_training_effect,
    calculate_aerobic_effect,
    calculate_anaerobic_effect,
)
from src.core.analytics_reports import (
    generate_daily_report,
    generate_morning_report,
    generate_weekly_report,
)

class AnalyticsEngine:
    ...

__all__ = ["AnalyticsEngine", ...]
```

- [ ] **Step 4: 运行测试验证**

Run: `uv run pytest tests/unit/ -x -q -k "analytics"`
Expected: 全部通过

- [ ] **Step 5: 提交**

```bash
git add src/core/analytics.py src/core/analytics_effects.py src/core/analytics_reports.py
git commit -m "refactor: split analytics.py into analytics_engine, analytics_effects, analytics_reports"
```

---

### Task 22: 第4层整体验证

- [ ] **Step 1: 运行全量单元测试**

Run: `uv run pytest tests/unit/ -x -q`
Expected: 全部通过

- [ ] **Step 2: 运行 ruff + mypy**

Run: `uv run ruff check src/ && uv run mypy src/ --ignore-missing-imports`
Expected: 无新增错误

- [ ] **Step 3: 验证文件行数**

Run: `wc -l src/agents/tools.py src/core/base/profile.py src/core/analytics.py`
Expected: 每个文件 < 500 行

- [ ] **Step 4: 验证导入兼容性**

```bash
python -c "from src.agents.tools import RunnerTools; print('tools OK')"
python -c "from src.core.base.profile import ProfileEngine; print('profile OK')"
python -c "from src.core.analytics import AnalyticsEngine; print('analytics OK')"
```
Expected: 全部 OK

---

## 第5层：清理收尾

### Task 23: 重构配速计算方法

**Files:**
- Modify: `src/core/analytics.py`

- [ ] **Step 1: 确认 _calculate_avg_pace_from_values 为底层纯函数**

确保 `_calculate_avg_pace_from_values(total_distance, total_duration)` 是纯函数，不依赖 self 状态。

- [ ] **Step 2: 重构 _calculate_avg_pace 委托调用**

将 `_calculate_avg_pace` 改为从 DataFrame 提取数值后调用底层函数：

```python
def _calculate_avg_pace(self, df: pl.DataFrame) -> str:
    total_distance = df["distance"].sum()
    total_duration = df["duration"].sum()
    return self._calculate_avg_pace_from_values(total_distance, total_duration)
```

- [ ] **Step 3: 运行测试验证**

Run: `uv run pytest tests/unit/ -x -q -k "analytics or pace"`
Expected: 全部通过

- [ ] **Step 4: 提交**

```bash
git add src/core/analytics.py
git commit -m "refactor: deduplicate pace calculation methods in analytics"
```

---

### Task 24: 集中业务常量

**Files:**
- Create: `src/core/constants.py`
- Modify: `src/core/analytics.py`

- [ ] **Step 1: 创建 constants.py**

从 `analytics.py` 顶部提取业务常量：

```python
# VDOT 常量
VDOT_COEFFICIENT: float = ...
VDOT_DISTANCE_EXPONENT: float = ...

# TSS/ATL/CTL 常量
ATL_TIME_CONSTANT: int = 7
CTL_TIME_CONSTANT: int = 42
DEFAULT_LTHR: float = ...

# 心率常量
DEFAULT_MAX_HR: int = 190
```

- [ ] **Step 2: 修改 analytics.py 导入常量**

```python
from src.core.constants import (
    VDOT_COEFFICIENT,
    VDOT_DISTANCE_EXPONENT,
    ATL_TIME_CONSTANT,
    CTL_TIME_CONSTANT,
    DEFAULT_LTHR,
)
```

删除 analytics.py 顶部的常量定义。

- [ ] **Step 3: 运行测试验证**

Run: `uv run pytest tests/unit/ -x -q`
Expected: 全部通过

- [ ] **Step 4: 提交**

```bash
git add src/core/constants.py src/core/analytics.py
git commit -m "refactor: extract business constants to core/constants.py"
```

---

### Task 25: 合并冗余测试文件

**Files:**
- Modify/删除: `tests/unit/` 下的成对测试文件

- [ ] **Step 1: 审查成对测试文件覆盖范围**

检查以下成对测试的覆盖范围是否重叠：
- `test_heart_rate_analyzer.py` vs `test_heart_rate_analyzer_core.py`
- `test_statistics_aggregator.py` vs `test_statistics_aggregator_core.py`
- `test_training_load_analyzer.py` vs `test_training_load_analyzer_core.py`
- `test_vdot_calculator.py` vs `test_vdot_calculator_core.py`

- [ ] **Step 2: 合并重叠测试**

对于覆盖范围重叠的成对文件：
1. 将 `_core.py` 中独有的测试用例合并到主测试文件
2. 删除 `_core.py` 文件
3. 确保合并后测试覆盖不下降

- [ ] **Step 3: 处理 test_analytics.py 重复**

确认 `tests/unit/test_analytics.py` 与 `tests/unit/core/test_analytics.py` 的覆盖范围，合并或删除冗余文件。

- [ ] **Step 4: 运行全量测试验证**

Run: `uv run pytest tests/unit/ -x -q`
Expected: 全部通过

- [ ] **Step 5: 提交**

```bash
git add tests/unit/
git commit -m "refactor: merge redundant test files"
```

---

### Task 26: 最终全量验证

- [ ] **Step 1: 裸 Exception 清零验证**

Run: `grep -r "except Exception" src/`
Expected: 0 结果

- [ ] **Step 2: type:ignore 清零验证**

Run: `grep -r "# type: ignore" src/`
Expected: 0 结果

- [ ] **Step 3: Ruff 检查**

Run: `uv run ruff check src/ tests/`
Expected: 0 错误

- [ ] **Step 4: Ruff 格式化检查**

Run: `uv run ruff format --check src/ tests/`
Expected: 无格式问题

- [ ] **Step 5: Mypy 检查**

Run: `uv run mypy src/ --ignore-missing-imports`
Expected: 无新增错误

- [ ] **Step 6: 全量单元测试**

Run: `uv run pytest tests/unit/ -v`
Expected: 全部通过

- [ ] **Step 7: 集成测试（如有）**

Run: `uv run pytest tests/integration/ -v`
Expected: 全部通过

- [ ] **Step 8: 最终提交**

```bash
git add -A
git commit -m "chore: code review remediation complete - all 16 issues resolved"
```
