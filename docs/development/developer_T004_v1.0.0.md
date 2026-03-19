# T004 - 训练计划引擎开发交付报告

## 开发概述

**任务编号**: T004  
**任务名称**: 训练计划引擎  
**开发时间**: 2026-03-19  
**开发人员**: 开发工程师  
**版本**: v1.0.0

---

## 一、开发完成的模块与功能点

### 1.1 核心数据结构

✅ **TrainingPlan** - 训练计划数据类
- 计划 ID、用户 ID、计划类型、体能水平
- 开始/结束日期、目标距离、目标比赛日期
- 周计划列表、创建/更新时间、备注

✅ **WeeklySchedule** - 周训练计划数据类
- 周数、开始/结束日期、每日计划列表
- 周跑量、周训练时长、本周重点、备注

✅ **DailyPlan** - 单日训练计划数据类
- 日期、训练类型、距离、时长
- 目标配速、目标心率区间、训练说明
- 完成情况、实际数据、主观疲劳度、心率漂移

### 1.2 枚举类型

✅ **PlanType** - 训练阶段类型
- BASE（基础期）、BUILD（进展期）、PEAK（巅峰期）
- RACE（比赛期）、RECOVERY（恢复期）

✅ **WorkoutType** - 训练课类型
- EASY（轻松跑）、LONG（长距离跑）、TEMPO（节奏跑）
- INTERVAL（间歇跑）、RECOVERY（恢复跑）、REST（休息）、CROSS（交叉训练）

✅ **FitnessLevel** - 体能水平
- BEGINNER（初学者）、INTERMEDIATE（中级）、ADVANCED（进阶）、ELITE（精英）

### 1.3 阶段配置

✅ **PHASE_CONFIG** - 阶段划分配置字典
- 定义各训练阶段的持续时间、训练类型比例、强度系数、周跑量增长率
- 支持根据体能水平动态调整

### 1.4 核心方法

✅ **generate_plan()** - 生成训练计划
- 基于用户画像和目标自动生成个性化训练计划
- 支持参数验证（目标距离、日期、VDOT、年龄、静息心率）
- 自动划分训练阶段（基础期→进展期→巅峰期→比赛期）
- 遵循 10% 原则（周跑量增长不超过 10%）

✅ **adjust_plan()** - 调整训练计划
- 支持心率漂移参数（>5% 触发降低负荷）
- 支持主观疲劳度参数（RPE 1-10 分）
- 支持完成情况参数（未完成率>50% 触发降低）
- 多维度综合调整算法

✅ **get_daily_workout()** - 获取当日训练内容
- 支持指定日期查询
- 默认查询今日训练
- 返回 DailyPlan 对象或 None

✅ **get_phase_config_by_fitness_level()** - 动态阶段配置
- 根据体能水平调整训练强度和比例
- 初学者：降低强度 20%，增加轻松跑比例
- 精英：提高强度 20%，增加专项训练比例

✅ **get_plan_summary()** - 获取计划摘要
- 汇总总跑量、总时长、训练分布
- 返回结构化字典数据

---

## 二、单元测试覆盖率

### 2.1 测试文件

- **文件路径**: `tests/unit/core/test_training_plan.py`
- **测试类数量**: 11 个
- **测试方法数量**: 48 个

### 2.2 覆盖率统计

| 指标 | 数值 | 要求 | 状态 |
|------|------|------|------|
| 语句覆盖率 | **97%** | ≥80% | ✅ 通过 |
| 测试通过数 | **48/48** | 100% | ✅ 通过 |

### 2.3 测试覆盖详情

**数据类测试** (7 个测试):
- DailyPlan 创建、字典转换、数值舍入、可选字段
- WeeklySchedule 创建、每日计划管理、字典转换
- TrainingPlan 创建、字典转换

**枚举测试** (3 个测试):
- FitnessLevel、PlanType、WorkoutType 枚举值验证

**配置测试** (2 个测试):
- PHASE_CONFIG 结构验证、基础期配置验证

**核心引擎测试** (31 个测试):
- 初始化、阶段配置动态调整
- 体能水平判定、阶段分配
- 目标配速计算、周计划生成
- 计划生成（成功 + 异常场景）
- 计划调整（心率漂移、RPE、组合因素）
- 每日训练查询、计划摘要

**集成测试** (5 个测试):
- 完整工作流（生成→调整→查询→摘要）
- 不同体能水平对比
- 不同目标距离对比
- 计划序列化验证

---

## 三、代码质量检查

### 3.1 Black 格式化

```bash
uv run black src/core/training_plan.py
```
✅ **通过**: 1 file reformatted

### 3.2 Isort 导入排序

```bash
uv run isort src/core/training_plan.py
```
✅ **通过**: 导入排序正确

### 3.3 Mypy 类型检查

```bash
uv run mypy src/core/training_plan.py
```
✅ **通过**: Success: no issues found in 1 source file

### 3.4 Bandit 安全检查

```bash
uv run bandit -r src/core/training_plan.py
```
✅ **通过**: No issues identified

**安全扫描结果**:
- 总代码行数：663 行
- 安全问题：0 个
- 安全跳过：0 个

---

## 四、依赖说明

本项目无需新增依赖，使用项目现有依赖：
- Python >= 3.11
- 标准库：dataclass, datetime, timedelta, Enum, typing

---

## 五、本地构建验证

### 5.1 测试执行

```bash
uv run pytest tests/unit/core/test_training_plan.py -v
```
✅ **结果**: 48 passed in 1.01s

### 5.2 全量单元测试

```bash
uv run pytest tests/unit/core/ -v
```
✅ **结果**: 167 passed, 1 skipped in 2.09s

### 5.3 代码质量全检

```bash
uv run black src; uv run isort src; uv run mypy src; uv run bandit -r src
```
✅ **结果**: 全部通过

---

## 六、启动方式

训练计划引擎为库模块，无需独立启动。使用示例：

```python
from src.core.training_plan import TrainingPlanEngine

# 创建引擎
engine = TrainingPlanEngine()

# 生成训练计划
plan = engine.generate_plan(
    user_id="user_123",
    goal_distance_km=21.0975,
    goal_date="2024-06-01",
    current_vdot=42,
    current_weekly_distance_km=35,
    age=30,
    resting_hr=60,
)

# 获取当日训练
today_workout = engine.get_daily_workout(plan)

# 调整计划（基于心率漂移和疲劳度）
adjusted_plan = engine.adjust_plan(
    plan=plan,
    week_number=1,
    hr_drift=6.5,
    rpe=7,
)

# 获取计划摘要
summary = engine.get_plan_summary(plan)
```

---

## 七、注意事项

### 7.1 设计亮点

1. **运动科学原理**: 基于 Powers 公式和训练周期理论
2. **动态调整**: 支持心率漂移、主观疲劳度等多维度参数
3. **个性化**: 根据体能水平自动调整训练强度和比例
4. **类型安全**: 完整的类型注解，通过 mypy 严格检查
5. **测试完备**: 48 个测试用例，覆盖率 97%

### 7.2 使用建议

1. **目标日期**: 建议至少提前 4 周设置目标比赛日期
2. **心率漂移**: 正常范围<5%，>10% 需大幅降低训练负荷
3. **主观疲劳度**: RPE 1-10 分，>7 分建议降低训练量
4. **周跑量增长**: 遵循 10% 原则，避免突增导致伤病

### 7.3 已知限制

1. 配速计算使用简化版 Powers 公式，专业场景可优化
2. 阶段分配策略可进一步细化（基于历史数据）
3. 未考虑天气、地形等外部因素

---

## 八、交付产物清单

✅ **源代码文件**:
- `src/core/training_plan.py` (322 行，97% 覆盖率)

✅ **测试文件**:
- `tests/unit/core/test_training_plan.py` (48 个测试用例)

✅ **文档文件**:
- `docs/development/developer_T004_v1.0.0.md` (本交付报告)

---

## 九、质量门禁验证

| 检查项 | 要求 | 实际 | 状态 |
|--------|------|------|------|
| 单元测试覆盖率 | ≥80% | 97% | ✅ |
| 测试通过率 | 100% | 100% | ✅ |
| Black 格式化 | 通过 | 通过 | ✅ |
| Isort 导入 | 通过 | 通过 | ✅ |
| Mypy 类型 | 通过 | 通过 | ✅ |
| Bandit 安全 | 通过 | 通过 | ✅ |
| 类型注解 | 完整 | 完整 | ✅ |
| 代码注释 | 完整 | 完整 | ✅ |

**整体评估**: ✅ **所有质量门禁均已通过**

---

## 十、下一步建议

1. **集成到 Agent 工具集**: 将训练计划引擎添加到 RunnerTools
2. **持久化存储**: 实现训练计划的保存和加载
3. **执行跟踪**: 记录每日训练完成情况，自动调整后续计划
4. **可视化**: 生成训练计划图表和趋势分析
5. **智能推荐**: 基于历史数据优化阶段分配和训练配速

---

**交付时间**: 2026-03-19 12:25  
**交付状态**: ✅ 已完成  
**交付人员**: 开发工程师
