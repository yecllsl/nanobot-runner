# 代码评审整改设计文档

> **日期**: 2026-05-18
> **基线报告**: `docs/review/code-review-report-20260518.md`
> **方案**: 按层治理（方案 A）
> **范围**: 报告 ISSUE + 扩展同类问题全量治理

---

## 一、整改总览

### 1.1 治理策略

采用 **按层治理** 方案，按问题类型分层推进，每层独立可验证：

| 层级 | 内容 | 风险 | 依赖 |
|------|------|------|------|
| 第1层 | 异常治理 | 低 | 无 |
| 第2层 | 类型治理 | 中 | 第1层 |
| 第3层 | 去重统一 | 中 | 第1层 |
| 第4层 | 大文件拆分 | 高 | 第1-3层 |
| 第5层 | 清理收尾 | 低 | 第1-4层 |

### 1.2 ISSUE 覆盖矩阵

| ISSUE | 层级 | 处理方式 |
|-------|------|----------|
| ISSUE-010 裸 Exception (390处) | 第1层 | 统一替换为 `NanobotRunnerError` |
| ISSUE-012 ImportError 同名冲突 | 第1层 | 重命名为 `DataImportError` |
| ISSUE-011 type:ignore (25处) | 第2层 | 修正类型注解或使用 `cast()` |
| ISSUE-003 AnomalyFilterRule 重复定义 | 第3层 | 统一到 `models/anomaly_schema.py` |
| ISSUE-006 ANOMALY_FILTER_RULES 重复 | 第3层 | 统一到 `models/anomaly_schema.py` |
| ISSUE-007 format_pace/format_duration 重复 | 第3层 | 统一到 `base/formatters.py` |
| ISSUE-004 Console 实例重复 | 第3层 | 统一到 `cli/common.py` |
| ISSUE-009 训练效果计算模式重复 | 第3层 | 提取通用 `_calculate_training_effect` |
| ISSUE-013 tools.py 超大文件 | 第4层 | 拆分为 5 个模块 |
| ISSUE-013 profile.py 超大文件 | 第4层 | 拆分为 3 个模块 |
| ISSUE-013 analytics.py 超大文件 | 第4层 | 拆分为 3 个模块 |
| ISSUE-005 RunnerProfile no-redef | 第4层 | 统一到 `profile_schema.py` |
| ISSUE-001 _evaluate_fitness_status | 第5层 | **保留**（经验证非死代码） |
| ISSUE-002 配速计算方法重叠 | 第5层 | 保留 `_calculate_avg_pace_from_values` 为底层，`_calculate_avg_pace` 委托调用 |
| ISSUE-008 Tool.execute() 样板重复 | 第5层 | 评估工厂函数/装饰器可行性 |
| ISSUE-014 成对测试冗余 | 第5层 | 审查并合并重叠测试 |
| ISSUE-015 test_analytics.py 两份 | 第5层 | 确认冗余后合并 |
| ISSUE-016 业务常量分散 | 第5层 | 集中到 `core/constants.py` |

---

## 二、第1层：异常治理

### 2.1 ImportError 重命名

**当前**: `src/core/base/exceptions.py:69` — `class ImportError(NanobotRunnerError)`

**改为**: `class DataImportError(NanobotRunnerError)`

**影响范围**: 全局搜索所有 `from ... import ImportError` 和 `except ImportError` 的引用点，替换为 `DataImportError`。需区分 Python 内置 `ImportError` 的正常使用场景。

### 2.2 裸 except Exception 全量替换

**当前**: 390 处 / 87 个文件

**策略**:
1. 统一替换 `except Exception` → `except NanobotRunnerError`
2. 保留原有 except 块体逻辑不变
3. 对确实需要捕获更广异常的场景（如外部库调用），使用具体异常组合：`except (NanobotRunnerError, OSError)`
4. 补充缺失的异常子类：

```python
class StorageError(NanobotRunnerError):
    error_code = "STORAGE_ERROR"

class ParseError(NanobotRunnerError):
    error_code = "PARSE_ERROR"

class ConfigError(NanobotRunnerError):
    error_code = "CONFIG_ERROR"
```

### 2.3 验证标准

- `grep -r "except Exception" src/` 返回 0 结果
- `grep -r "except NanobotRunnerError" src/` 覆盖所有原位置
- 全部单元测试通过
- `mypy src/ --ignore-missing-imports` 无新增错误

---

## 三、第2层：类型治理

### 3.1 # type: ignore 全量消除

**当前**: 25 处 / 11 个文件

**按原因分类处理**:

| ignore 原因 | 数量 | 处理方式 |
|-------------|------|----------|
| `arg-type` | 10 | 使用 `cast()` 或添加类型守卫 |
| `assignment` | 5 | 修正变量类型注解或使用 `cast()` |
| `no-redef` | 1 | 消除重定义（第4层处理） |
| 裸 `# type: ignore` | 4 | 补充具体规则编号或修正类型 |
| `no-untyped-def` / `operator` | 2 | 添加类型注解 |
| 其他 | 3 | 逐处分析修正 |

### 3.2 重点文件

**profile.py**（9处）: 6处 `arg-type` + 2处 `assignment` + 1处 `no-redef`。`no-redef` 由 RunnerProfile 重定义引起，第4层根治；其余通过 `cast()` + 类型守卫修正。

**context.py**（4处裸 ignore）: 补充具体忽略规则编号，尽可能修正为正确类型注解。

### 3.3 验证标准

- `grep -r "# type: ignore" src/` 返回 0 结果
- `mypy src/ --ignore-missing-imports` 无新增错误
- 全部单元测试通过

---

## 四、第3层：去重统一

### 4.1 AnomalyFilterRule + ANOMALY_FILTER_RULES 统一

**方案**:
1. 创建 `src/core/models/anomaly_schema.py`，统一定义 `AnomalyFilterRule`（含 `clip_value` 字段，向后兼容）
2. 将完整 13 条 `ANOMALY_FILTER_RULES` 定义在此文件
3. `profile.py` 和 `anomaly_filter.py` 均从 `anomaly_schema.py` 导入
4. `anomaly_filter.py` 中缺失的 5 条配速/VDOT规则自动补齐

### 4.2 format_pace / format_duration 统一

**方案**:
1. 创建 `src/core/base/formatters.py`，定义纯函数 `format_pace()` 和 `format_duration()`
2. `cli/formatter.py` 中的同名函数改为调用底层函数（保持 Rich 增强逻辑）
3. `statistics_aggregator.py` 和 `race_predictor.py` 删除私有方法，从 `formatters.py` 导入

### 4.3 Console 实例统一

**方案**:
1. `src/cli/common.py` 作为唯一 Console 实例来源
2. `formatter.py` 和 `viz_handler.py` 从 `common.py` 导入 `console`
3. `viz_handler.py` 中带参数的 Console 实例保留，但改为从 `common.py` 导入基础配置后增强

### 4.4 训练效果计算去重

**方案**: 提取通用方法：

```python
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

`_calculate_aerobic_effect` 和 `_calculate_anaerobic_effect` 传入不同权重和缩放因子调用此方法。

### 4.5 验证标准

- `AnomalyFilterRule` 只有一个定义点
- `ANOMALY_FILTER_RULES` 只有一个定义点
- `format_pace` / `format_duration` 只在 `formatters.py` 中有核心实现
- `console` 只在 `common.py` 中实例化
- 全部单元测试通过

---

## 五、第4层：大文件拆分

### 5.1 tools.py 拆分（4364行 → 5个模块）

```
src/agents/
├── tools.py            # BaseTool + RunnerTools（聚合入口）+ 重新导出
├── tools_stats.py      # 统计分析工具（VDOT/TSS/配速/心率等）
├── tools_plan.py       # 训练计划工具（创建/查询/调整计划）
├── tools_body.py       # 身体状态工具（HRV/疲劳/恢复/晨报）
├── tools_twin.py       # 数字孪生工具（状态查询/What-If推演）
└── tools_data.py       # 数据管理工具（导入/导出/查询/配置）
```

**关键设计**:
- `RunnerTools` 保留在 `tools.py` 中，作为所有工具的聚合入口
- 每个拆分文件中的工具类通过 `from .tools_xxx import ...` 在 `tools.py` 中重新导出
- 对外导入路径不变：`from src.agents.tools import XxxTool` 仍然有效

### 5.2 profile.py 拆分（1594行 → 3个模块）

```
src/core/base/
├── profile.py          # ProfileEngine（核心编排）+ 重新导出
├── profile_storage.py  # ProfileStorageManager（存储层）
└── profile_schema.py   # RunnerProfile 数据类定义（消除 no-redef）
```

**关键设计**:
- `RunnerProfile` 统一定义在 `profile_schema.py`
- `user_profile_manager.py` 中的旧 `RunnerProfile` 改为从 `profile_schema.py` 导入
- `ProfileEngine` 通过组合引用 `ProfileStorageManager`

### 5.3 analytics.py 拆分（1585行 → 3个模块）

```
src/core/
├── analytics.py            # AnalyticsEngine（核心编排）+ 重新导出
├── analytics_effects.py    # 训练效果计算（有氧/无氧/通用方法）
└── analytics_reports.py    # 报告生成（晨报/周报/日报的 generate_* 方法）
```

**关键设计**:
- `AnalyticsEngine` 通过组合引用子模块函数
- 原有公共方法签名不变，内部委托到子模块
- `_evaluate_fitness_status` 保留（经验证非死代码）

### 5.4 导入兼容性保障

所有拆分采用重新导出模式：

```python
# tools.py 示例
from .tools_stats import VdotTool, LoadTool, PaceTool
from .tools_plan import CreatePlanTool, QueryPlanTool

__all__ = ["VdotTool", "LoadTool", "PaceTool", "CreatePlanTool", ...]
```

### 5.5 验证标准

- `tools.py` < 500 行
- `profile.py` < 500 行
- `analytics.py` < 500 行
- 所有外部导入路径不变
- 全部单元测试通过
- `mypy src/ --ignore-missing-imports` 无新增错误

---

## 六、第5层：清理收尾

### 6.1 死代码与重叠方法

| 项目 | 处理 |
|------|------|
| `_evaluate_fitness_status` | 保留（非死代码，第1531/1548行有调用） |
| `_calculate_avg_pace` / `_calculate_avg_pace_from_values` | 保留 `_calculate_avg_pace_from_values` 为底层纯函数，`_calculate_avg_pace` 委托调用 |
| Tool.execute() 样板 | 评估工厂函数/装饰器可行性，如风险高则留技术债务 |
| RunnerProfile no-redef | 已在第4层根治 |

### 6.2 测试文件合并

1. 审查 `test_calculator_X.py` + `test_calculator_X_core.py` 成对测试的覆盖范围
2. 合并重叠部分，保留覆盖更完整的文件
3. 确认 `tests/unit/test_analytics.py` 与 `tests/unit/core/test_analytics.py` 是否冗余，合并或删除

### 6.3 业务常量集中

1. 创建 `src/core/constants.py`
2. 按域分组：VDOT 常量、TSS/ATL/CTL 常量、心率常量
3. 原文件改为从 `constants.py` 导入

### 6.4 验证标准

- 无冗余测试文件
- 业务常量只在 `constants.py` 中定义
- 全部单元测试 + 集成测试通过

---

## 七、整体验证清单

| 检查项 | 命令 | 期望 |
|--------|------|------|
| 裸 Exception 清零 | `grep -r "except Exception" src/` | 0 结果 |
| type:ignore 清零 | `grep -r "# type: ignore" src/` | 0 结果 |
| Ruff 检查 | `uv run ruff check src/ tests/` | 0 错误 |
| Mypy 检查 | `uv run mypy src/ --ignore-missing-imports` | 无新增错误 |
| 单元测试 | `uv run pytest tests/unit/` | 全部通过 |
| 导入兼容 | 手动验证关键导入路径 | 无破坏性变更 |

---

## 八、风险与缓解

| 风险 | 缓解措施 |
|------|----------|
| 390处异常替换引入逻辑错误 | 每层完成后运行全量测试，逐文件提交 |
| 大文件拆分破坏导入关系 | 采用重新导出模式，保持外部接口不变 |
| type:ignore 修正引入 mypy 新错误 | 逐处修正后立即运行 mypy 验证 |
| 测试合并丢失覆盖 | 合并前对比覆盖率，合并后验证无下降 |

---

> *设计文档生成时间: 2026-05-18*
> *基于代码评审报告: code-review-report-20260518.md*
