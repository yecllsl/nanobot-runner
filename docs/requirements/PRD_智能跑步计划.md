# 智能跑步计划需求规格说明书

> **文档版本**: v1.0  
> **创建日期**: 2026-04-18  
> **文档状态**: 正式发布  
> **适用范围**: v0.10.0 - v0.12.0 智能跑步计划功能

---

## 1. 项目背景

### 1.1 业务背景

Nanobot Runner 已完成核心功能构建（FIT解析、数据存储、基础分析），并在v0.9.x完成了架构重构和测试覆盖达标。现在需要进入下一个阶段：构建数据驱动的自适应智能跑步计划系统。

### 1.2 核心场景

**目标用户**: 技术型严肃跑者，希望通过数据驱动的训练计划提升跑步表现

**核心痛点**:
1. 训练计划执行后缺乏反馈记录机制
2. 计划调整依赖人工经验，缺乏数据支撑
3. 无法评估目标达成的可能性
4. 缺乏长期训练规划能力

**解决方案**: 构建三层递进的智能跑步计划系统：
- **v0.10.0 数据感知层**: 收集训练执行反馈，建立数据基础
- **v0.11.0 智能调整层**: LLM驱动的计划调整和自然语言交互
- **v0.12.0 预测规划层**: 目标评估和长期规划

---

## 2. 功能需求

### 2.1 v0.10.0 数据感知版（P0 - MVP核心）

#### 2.1.1 训练执行反馈收集

**需求描述**: 支持用户记录每次训练的执行情况，包括完成度、体感评分、备注等

**功能点**:
- CLI命令：`nanobotrun plan log --plan-id <id> --date <date> --completion <rate> --effort <score>`
- Agent工具：`RecordPlanExecutionTool`
- 数据存储：扩展现有DailyPlan模型（已存在字段：completed, actual_distance_km, actual_duration_min, actual_avg_hr, rpe, hr_drift）
- 新增字段：completion_rate（完成度0.0-1.0）、effort_score（体感评分1-10）、notes（备注）

**验收标准**:
- [ ] CLI命令支持记录完成度、体感评分、备注
- [ ] Agent工具支持自然语言记录（如"今天跑了8公里，感觉有点累"）
- [ ] 数据持久化到training_plans.json
- [ ] 支持查询历史执行记录

**优先级**: P0（MVP核心）

**技术依赖**:
- 数据模型：DailyPlan已存在，需扩展字段
- 存储层：PlanManager已存在，需扩展方法
- Agent工具：需新增RecordPlanExecutionTool

#### 2.1.2 计划完成度跟踪

**需求描述**: 支持查询任意训练计划的执行统计，包括完成率、平均体感、训练负荷等

**功能点**:
- CLI命令：`nanobotrun plan stats --plan-id <id>`
- Agent工具：`GetPlanExecutionStatsTool`
- 统计指标：完成率、平均体感、总跑量、总时长、平均心率、心率漂移

**验收标准**:
- [ ] CLI命令支持查询计划执行统计
- [ ] Agent工具支持自然语言查询（如"我的计划执行得怎么样"）
- [ ] 返回结构化统计数据（PlanExecutionStats数据类）
- [ ] 查询响应时间 < 500ms

**优先级**: P0（MVP核心）

**技术依赖**:
- 数据源：training_plans.json
- 计算引擎：AnalyticsEngine（已存在）
- 数据类：需新增PlanExecutionStats

#### 2.1.3 历史响应模式分析

**需求描述**: 分析用户对不同训练类型的响应模式，识别最佳训练策略

**功能点**:
- Agent工具：`AnalyzeTrainingResponseTool`
- 分析维度：训练类型 vs 完成率、体感评分、心率漂移
- 输出：训练响应模式报告

**验收标准**:
- [ ] 支持分析不同训练类型的响应模式
- [ ] 识别用户最适应的训练类型
- [ ] 识别用户最不适应的训练类型
- [ ] 输出训练响应模式报告

**优先级**: P1（重要功能）

**技术依赖**:
- 数据源：training_plans.json + activities_*.parquet
- 分析引擎：需新增TrainingResponseAnalyzer
- 数据类：需新增TrainingResponsePattern

---

### 2.2 v0.11.0 智能调整版（P0 - MVP核心）

#### 2.2.1 LLM驱动的计划调整

**需求描述**: 通过LLM实现智能计划调整，符合运动科学原则

**功能点**:
- Agent工具：`AdjustPlanTool`
- 调整类型：跑量调整、强度调整、训练类型调整、日期调整
- 约束条件：10%规则、阶段特点、用户偏好
- 输出：调整后的训练计划

**验收标准**:
- [ ] 支持自然语言调整指令（如"下周减量"）
- [ ] 调整建议符合运动科学原则
- [ ] 调整建议考虑用户历史执行数据
- [ ] 调整建议采纳率 > 70%

**优先级**: P0（MVP核心）

**技术依赖**:
- LLM底座：nanobot-ai（已集成）
- 数据源：v0.10.0收集的执行反馈数据
- Prompt工程：需设计调整Prompt模板
- 规则引擎：需新增PlanAdjustmentValidator

#### 2.2.2 自然语言计划修改

**需求描述**: 支持通过自然语言对话修改训练计划

**功能点**:
- Agent多轮对话：支持上下文感知的对话
- 修改类型：单日修改、周计划修改、整体计划修改
- 确认机制：修改前确认，修改后反馈

**验收标准**:
- [ ] 支持"下周减量"等自然语言指令
- [ ] 支持"把周三的间歇跑改成轻松跑"等具体修改
- [ ] 支持多轮对话澄清需求
- [ ] 自然语言指令理解准确率 > 85%

**优先级**: P0（MVP核心）

**技术依赖**:
- Agent框架：nanobot-ai（已集成）
- 对话管理：需新增PlanModificationDialogManager
- 意图识别：LLM驱动

#### 2.2.3 上下文感知建议

**需求描述**: 基于用户历史偏好和当前状态，给出个性化建议

**功能点**:
- Agent工具：`GetPlanAdjustmentSuggestionsTool`
- 上下文：用户画像、历史执行数据、当前训练负荷、天气等
- 输出：个性化调整建议

**验收标准**:
- [ ] 建议考虑用户历史偏好
- [ ] 建议考虑当前训练负荷
- [ ] 建议考虑用户体能水平
- [ ] 建议合理性评分 > 4.0/5.0

**优先级**: P1（重要功能）

**技术依赖**:
- 数据源：用户画像、执行反馈、训练负荷
- 推荐引擎：需新增PlanSuggestionEngine
- 数据类：需新增PlanSuggestion

---

### 2.3 v0.12.0 预测与规划版（P0 - MVP核心）

#### 2.3.1 目标达成评估

**需求描述**: 评估目标达成的可能性和关键风险

**功能点**:
- Agent工具：`EvaluateGoalAchievementTool`
- 评估维度：当前VDOT、训练基础、剩余时间、训练负荷
- 输出：达成概率、关键风险、改进建议

**验收标准**:
- [ ] 支持评估目标达成概率
- [ ] 识别关键风险因素
- [ ] 给出改进建议
- [ ] 目标达成预测准确率 > 75%

**优先级**: P0（MVP核心）

**技术依赖**:
- 数据源：VDOT趋势、训练负荷、历史数据
- 预测模型：LLM推理 + 规则引擎
- 数据类：需新增GoalAchievementEvaluation

#### 2.3.2 长期周期规划

**需求描述**: 支持年度/赛季多周期训练规划

**功能点**:
- Agent工具：`CreateLongTermPlanTool`
- 规划类型：年度规划、赛季规划、多周期规划
- 周期划分：基础期、进展期、巅峰期、比赛期、恢复期
- 输出：长期训练计划

**验收标准**:
- [ ] 支持创建年度训练规划
- [ ] 支持创建赛季训练规划
- [ ] 支持多周期规划
- [ ] 长期规划合理性评分 > 4.0/5.0

**优先级**: P1（重要功能）

**技术依赖**:
- 数据源：用户画像、历史数据、目标
- 规划引擎：需新增LongTermPlanGenerator
- 数据类：需新增LongTermPlan

#### 2.3.3 智能训练建议

**需求描述**: 每次对话都能给出上下文感知的实时建议

**功能点**:
- Agent工具：`GetSmartTrainingAdviceTool`
- 建议类型：训练建议、恢复建议、营养建议、伤病预防建议
- 上下文：当前训练状态、历史数据、用户画像
- 输出：个性化训练建议

**验收标准**:
- [ ] 建议考虑当前训练状态
- [ ] 建议考虑历史数据
- [ ] 建议考虑用户画像
- [ ] 建议实用性评分 > 4.0/5.0

**优先级**: P1（重要功能）

**技术依赖**:
- 数据源：训练数据、用户画像、执行反馈
- 建议引擎：LLM驱动
- 数据类：需新增SmartTrainingAdvice

---

## 3. 非功能需求

### 3.1 性能需求

| 指标 | 目标值 | 版本 |
|------|--------|------|
| 计划执行反馈记录成功率 | 100% | v0.10.0 |
| 计划执行统计查询响应时间 | < 500ms | v0.10.0 |
| 计划调整建议采纳率 | > 70% | v0.11.0 |
| 自然语言指令理解准确率 | > 85% | v0.11.0 |
| 目标达成预测准确率 | > 75% | v0.12.0 |
| 长期规划合理性评分 | > 4.0/5.0 | v0.12.0 |

### 3.2 质量需求

| 指标 | 目标值 | 版本 |
|------|--------|------|
| 核心模块测试覆盖率 | ≥ 80% | 所有版本 |
| mypy类型错误 | 0 | 所有版本 |
| ruff代码质量警告 | 0 | 所有版本 |

### 3.3 安全需求

- 所有敏感数据（API密钥、用户数据）不得硬编码
- 使用config模块管理配置
- 数据存储在本地，零外联设计

### 3.4 可维护性需求

- 遵循项目架构规范（依赖注入、类型安全）
- 遵循AGENTS.md开发规范
- 所有新增Agent工具必须更新TOOL_DESCRIPTIONS

---

## 4. 验收标准

### 4.1 v0.10.0 验收标准

**功能验收**:
- [ ] CLI命令支持记录训练执行反馈
- [ ] Agent工具支持自然语言记录训练执行反馈
- [ ] CLI命令支持查询计划执行统计
- [ ] Agent工具支持自然语言查询计划执行统计
- [ ] Agent工具支持分析训练响应模式

**质量验收**:
- [ ] 核心模块测试覆盖率 ≥ 80%
- [ ] mypy类型错误 = 0
- [ ] ruff代码质量警告 = 0
- [ ] 所有测试通过率 = 100%

**性能验收**:
- [ ] 计划执行反馈记录成功率 = 100%
- [ ] 计划执行统计查询响应时间 < 500ms

### 4.2 v0.11.0 验收标准

**功能验收**:
- [ ] Agent工具支持LLM驱动的计划调整
- [ ] Agent工具支持自然语言计划修改
- [ ] Agent工具支持上下文感知建议

**质量验收**:
- [ ] 核心模块测试覆盖率 ≥ 80%
- [ ] mypy类型错误 = 0
- [ ] ruff代码质量警告 = 0
- [ ] 所有测试通过率 = 100%

**性能验收**:
- [ ] 计划调整建议采纳率 > 70%
- [ ] 自然语言指令理解准确率 > 85%

### 4.3 v0.12.0 验收标准

**功能验收**:
- [ ] Agent工具支持目标达成评估
- [ ] Agent工具支持长期周期规划
- [ ] Agent工具支持智能训练建议

**质量验收**:
- [ ] 核心模块测试覆盖率 ≥ 80%
- [ ] mypy类型错误 = 0
- [ ] ruff代码质量警告 = 0
- [ ] 所有测试通过率 = 100%

**性能验收**:
- [ ] 目标达成预测准确率 > 75%
- [ ] 长期规划合理性评分 > 4.0/5.0

---

## 5. 迭代计划

### 5.1 v0.10.0 数据感知版（2026-04-20 ~ 2026-05-05）

**工期**: 2周

**关键里程碑**:
- Week 1: 数据模型扩展 + CLI命令开发
- Week 2: Agent工具开发 + 测试覆盖

**交付物**:
- 扩展的DailyPlan数据模型
- RecordPlanExecutionTool
- GetPlanExecutionStatsTool
- AnalyzeTrainingResponseTool
- CLI命令：`nanobotrun plan log`、`nanobotrun plan stats`
- 单元测试覆盖率 ≥ 80%

### 5.2 v0.11.0 智能调整版（2026-05-05 ~ 2026-05-25）

**工期**: 3周

**关键里程碑**:
- Week 1: Prompt工程 + 规则引擎开发
- Week 2: Agent工具开发 + 对话管理
- Week 3: 测试覆盖 + 效果验证

**交付物**:
- AdjustPlanTool
- GetPlanAdjustmentSuggestionsTool
- PlanAdjustmentValidator
- PlanModificationDialogManager
- 单元测试覆盖率 ≥ 80%

### 5.3 v0.12.0 预测与规划版（2026-05-25 ~ 2026-06-15）

**工期**: 3周

**关键里程碑**:
- Week 1: 预测模型开发 + 评估引擎
- Week 2: 规划引擎开发 + Agent工具
- Week 3: 测试覆盖 + 效果验证

**交付物**:
- EvaluateGoalAchievementTool
- CreateLongTermPlanTool
- GetSmartTrainingAdviceTool
- LongTermPlanGenerator
- 单元测试覆盖率 ≥ 80%

---

## 6. 风险评估

### 6.1 技术风险

| 风险 | 概率 | 影响 | 应对策略 |
|------|------|------|----------|
| Prompt效果不稳定 | 高 | 高 | 规则引擎兜底，多轮测试优化 |
| LLM响应延迟 | 中 | 中 | 异步处理，缓存机制 |
| 数据模型扩展不兼容 | 低 | 高 | 充分设计，向后兼容 |
| 测试覆盖率不达标 | 中 | 高 | 测试驱动开发，优先核心模块 |

### 6.2 业务风险

| 风险 | 概率 | 影响 | 应对策略 |
|------|------|------|----------|
| 用户需求不明确 | 中 | 高 | 快速迭代验证，用户反馈 |
| 调整建议不合理 | 中 | 高 | 运动科学专家评审，规则约束 |
| 预测准确率低 | 中 | 中 | 持续优化模型，增加数据维度 |

---

## 7. 附录

### 7.1 数据模型扩展

#### DailyPlan扩展字段

```python
@dataclass
class DailyPlan:
    # 现有字段
    date: str
    workout_type: TrainingType
    distance_km: float
    duration_min: int
    target_pace_min_per_km: float | None = None
    target_hr_zone: int | None = None
    notes: str = ""
    completed: bool = False
    actual_distance_km: float | None = None
    actual_duration_min: int | None = None
    actual_avg_hr: int | None = None
    rpe: int | None = None
    hr_drift: float | None = None
    event_id: str | None = None
    
    # v0.10.0 新增字段
    completion_rate: float | None = None  # 完成度 0.0-1.0
    effort_score: int | None = None  # 体感评分 1-10
    feedback_notes: str = ""  # 反馈备注
```

#### 新增数据类

```python
@dataclass
class PlanExecutionStats:
    """计划执行统计"""
    plan_id: str
    total_planned_days: int
    completed_days: int
    completion_rate: float
    avg_effort_score: float
    total_distance_km: float
    total_duration_min: int
    avg_hr: int | None
    avg_hr_drift: float | None

@dataclass
class TrainingResponsePattern:
    """训练响应模式"""
    workout_type: TrainingType
    avg_completion_rate: float
    avg_effort_score: float
    avg_hr_drift: float
    sample_count: int
    recommendation: str

@dataclass
class PlanAdjustment:
    """计划调整"""
    adjustment_type: str  # volume, intensity, type, date
    original_value: Any
    adjusted_value: Any
    reason: str
    confidence: float  # 0.0-1.0

@dataclass
class GoalAchievementEvaluation:
    """目标达成评估"""
    goal_description: str
    achievement_probability: float  # 0.0-1.0
    key_risks: list[str]
    improvement_suggestions: list[str]
    current_vdot: float
    required_vdot: float
    time_remaining_weeks: int

@dataclass
class LongTermPlan:
    """长期训练计划"""
    plan_id: str
    plan_name: str
    start_date: str
    end_date: str
    goal_description: str
    cycles: list[TrainingCycle]
    created_at: datetime

@dataclass
class TrainingCycle:
    """训练周期"""
    cycle_type: PlanType
    start_date: str
    end_date: str
    weeks: list[WeeklySchedule]
    focus: str
    notes: str

@dataclass
class SmartTrainingAdvice:
    """智能训练建议"""
    advice_type: str  # training, recovery, nutrition, injury_prevention
    advice_content: str
    priority: str  # high, medium, low
    context: str
    created_at: datetime
```

### 7.2 Agent工具清单

| 工具名称 | 版本 | 功能描述 |
|----------|------|----------|
| RecordPlanExecutionTool | v0.10.0 | 记录计划执行情况 |
| GetPlanExecutionStatsTool | v0.10.0 | 获取计划执行统计 |
| AnalyzeTrainingResponseTool | v0.10.0 | 分析训练响应模式 |
| AdjustPlanTool | v0.11.0 | 调整训练计划 |
| GetPlanAdjustmentSuggestionsTool | v0.11.0 | 获取计划调整建议 |
| EvaluateGoalAchievementTool | v0.12.0 | 评估目标达成概率 |
| CreateLongTermPlanTool | v0.12.0 | 创建长期训练规划 |
| GetSmartTrainingAdviceTool | v0.12.0 | 获取智能训练建议 |

### 7.3 CLI命令清单

| 命令 | 版本 | 功能描述 |
|------|------|----------|
| `nanobotrun plan log` | v0.10.0 | 记录训练执行反馈 |
| `nanobotrun plan stats` | v0.10.0 | 查询计划执行统计 |

---

## 8. 变更记录

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|----------|------|
| v1.0 | 2026-04-18 | 初始版本 | 产品经理 |

---

*本文档遵循需求规格说明书规范，定期 review 和更新*
