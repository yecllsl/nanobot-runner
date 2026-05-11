# Nanobot Runner 产品演进设计：数字孪生跑者 → 自适应进化引擎

> **文档版本**: v1.0
> **创建日期**: 2026-05-07
> **状态**: 待审核
> **覆盖版本**: v0.20 - v0.25

---

## 1. 背景与动机

### 1.1 当前状态（v0.19.0）

Nanobot Runner 已构建了完整的跑步数据分析与 AI 教练功能栈：

| 能力层 | 已实现功能 |
|--------|-----------|
| 数据层 | FIT 解析、Parquet 存储、会话仓储、索引管理 |
| 计算层 | VDOT 计算、训练负荷（CTL/ATL/TSB）、心率分析、HRV 分析、疲劳度评估、恢复监控 |
| 智能层 | LLM 驱动的训练计划生成/调整、Subagent 架构（data_analyst/report_writer）、透明化引擎 |
| 交互层 | CLI 命令集、Gateway 服务、可视化（plotext）、数据导出（CSV/JSON/Parquet） |
| 扩展层 | MCP 工具管理、天气/地图/健康数据工具、Cron 训练提醒、Hook 组合系统 |

### 1.2 核心痛点

| 痛点 | 描述 | 当前状态 |
|------|------|---------|
| 训练计划不够个性化 | 计划基于规则和 LLM 推理，缺乏数据驱动的个体化预测 | 无法推演不同训练方案的效果差异 |
| 缺乏预测性健康预警 | 身体信号分析仅做事后评估，无法预测未来风险 | 只有"你现在怎样"，没有"未来会怎样" |
| 决策视角单一 | 单 Agent 模式，无法从教练/医生等不同角度博弈推演 | 缺乏多视角交叉验证 |
| 缺乏自我进化能力 | 系统无法从用户反馈和训练结果中学习优化 | 每次决策都是"从零开始" |

### 1.3 市场机遇

- 全球跑步 App 市场：2024 年 $0.64B → 2033 年 $2.12B（CAGR 14.2%）
- AI 健身教练市场：2025 年 $4.8B → 2034 年 $22.6B（CAGR 18.7%）
- 72% 用户需求个性化教练功能，68% 开发者投资 AI 驱动特性
- 竞品空白：目前没有开源跑步 App 实现数字孪生 + 自适应进化能力

### 1.4 竞品分析

| 竞品 | 核心能力 | 局限性 |
|------|---------|--------|
| Strava | 社交 + 基础分析 + AI 路线规划 | 训练计划泛化，缺乏深度个性化 |
| TrainingPeaks | 教练-运动员协作 + TSS/IF 指标 | 需人工教练，AI 能力弱 |
| Garmin Coach | 设备数据驱动自适应训练计划 | 绑定硬件，模型不透明 |
| TriDot | AI 个性化训练 | 闭源，不可定制，价格高 |
| **Nanobot Runner 差异化** | **数字孪生推演 + 自适应进化 + 开源可定制** | **市场空白** |

---

## 2. 产品愿景与战略方向

### 2.1 愿景

**从"记录跑步"到"预测跑步"再到"进化跑步"**

- **当前（v0.19）**：记录 + 分析 + 规则化建议 → "你的跑步数据管家"
- **Phase A（v0.20-v0.22）**：预测 + 推演 + 风险预警 → "你的数字孪生跑者"
- **Phase C（v0.23-v0.25）**：学习 + 进化 + 个性化 → "越用越懂你的私人教练"

### 2.2 战略选择

经过三种方向评估后，选择 **"先 A 后 C"** 路线：

| 方向 | 核心思想 | 评估 |
|------|---------|------|
| A: 数字孪生跑者 | 预测优先，构建可推演的生理模型 | **Phase A 采用** — 立即可感知的价值 |
| B: 多智能体教练委员会 | 博弈优先，多 Agent 辩论决策 | 条件性推进 — 依赖底座 Subagent 能力 |
| C: 自适应进化引擎 | 学习优先，从每次训练中进化 | **Phase C 采用** — 在预测数据基础上有机生长 |

### 2.3 设计原则

1. **LLM 优先 + ML 辅助** — ML 模型作为 LLM 的"确定性锚点"，LLM 负责解读和决策
2. **本地优先 + 可选云增强** — 所有模型和数据默认本地存储，云端仅作为可选增强
3. **全谱系覆盖** — 入门跑者感受"越来越懂我"，进阶跑者看到"预测越来越准"
4. **渐进式复杂度** — 每个版本在前一个版本基础上构建，风险可控
5. **与现有架构兼容** — 新模块通过 Hook 系统无侵入接入，ML 模型作为增强计算器

---

## 3. 架构设计

### 3.1 分层架构

```
┌─────────────────────────────────────────────────────┐
│                     交互层                            │
│   CLI / Gateway / (未来) Mobile / Web                │
├─────────────────────────────────────────────────────┤
│                   LLM 决策层                          │
│   AgentLoop + Tools + Prompt Engine                  │
│   ┌─────────────────────────────────────────────┐    │
│   │  Subagent 层（条件性，视底座能力）             │    │
│   │  Coach / Doctor / Analyst                    │    │
│   └─────────────────────────────────────────────┘    │
├─────────────────────────────────────────────────────┤
│                智能计算层（新增）                       │
│   ┌──────────┐  ┌──────────┐  ┌──────────────┐      │
│   │ 预测引擎  │  │ 孪生引擎  │  │  进化引擎     │      │
│   │Predictive│  │  Twin    │  │ Evolutionary │      │
│   └──────────┘  └──────────┘  └──────────────┘      │
├─────────────────────────────────────────────────────┤
│               确定性计算层（现有）                      │
│   VDOT / TrainingLoad / HRV / Fatigue / Recovery     │
├─────────────────────────────────────────────────────┤
│              数据层（现有 + 扩展）                      │
│   Parquet Storage / Decision Log / Model Store       │
└─────────────────────────────────────────────────────┘
```

### 3.2 模块依赖关系

```
进化引擎 ──依赖──→ 孪生引擎 ──依赖──→ 预测引擎 ──依赖──→ 确定性计算层
    │                  │                  │
    │                  │                  └──→ ModelStore
    │                  └──→ RunnerStateVector
    └──→ DecisionLog
```

- 预测引擎不依赖 LLM，可独立测试
- 孪生引擎不依赖进化引擎，可独立测试
- 进化引擎依赖前两者的输出

### 3.3 新增目录结构

```
src/core/
├── predictive/                    # 新增：预测引擎
│   ├── __init__.py
│   ├── performance_predictor.py   # 性能预测模型
│   ├── injury_risk_predictor.py   # 伤病风险模型
│   ├── training_response.py       # 训练响应模型（Banister IR）
│   ├── model_manager.py           # 模型生命周期管理
│   └── feature_engine.py          # 特征工程
├── twin/                          # 新增：数字孪生引擎
│   ├── __init__.py
│   ├── runner_state_vector.py     # 跑者状态向量
│   ├── twin_engine.py             # What-If 推演引擎
│   └── plan_comparator.py         # 计划对比器
├── evolution/                     # 新增：自适应进化引擎
│   ├── __init__.py
│   ├── decision_tracker.py        # 决策-结果追踪
│   ├── outcome_tracker.py         # 结果回填
│   ├── personalization.py         # 个性化学习
│   ├── calibrator.py              # 预测校准
│   ├── prompt_optimizer.py        # 提示策略优化
│   └── evolution_trigger.py       # 进化触发器
└── (现有模块不变)
```

---

## 4. Phase A：数字孪生跑者（v0.20-v0.22）

### 4.1 v0.20：预测智能模块

#### 4.1.1 性能预测模型（PerformancePredictor）

**策略：双轨制——参数化基线 + ML 增强**

**轨道一：参数化基线（冷启动，数据 < 200 条时使用）**

基于 Banister Impulse-Response Model 扩展：

```
VDOT(t) = VDOT_base + Σ[w_i × exp(-(t-t_i)/τ_fitness)] - Σ[v_i × exp(-(t-t_i)/τ_fatigue)]
```

- `w_i`：第 i 次训练的正向刺激量（基于 TRIMP/HR_zone 计算）
- `v_i`：第 i 次训练的疲劳量
- `τ_fitness`：体能衰减时间常数（默认 42 天，可个体化校准）
- `τ_fatigue`：疲劳衰减时间常数（默认 7-12 天，可个体化校准）

参数拟合：`scipy.optimize.minimize`（L-BFGS-B），目标函数为预测 VDOT 与实际 VDOT 的 MSE。

**轨道二：ML 增强（数据 ≥ 200 条时启用）**

特征矩阵（21 维）：

| 特征组 | 特征名 | 维度 |
|--------|--------|------|
| 体能状态 | current_vdot, vdot_trend_30d, ctl, atl, tsb | 5 |
| 训练负荷模式 | weekly_volume_km, weekly_volume_trend, intensity_ratio_z345, long_run_ratio, training_monotony, training_strain | 6 |
| 恢复状态 | fatigue_score, recovery_status_encoded, resting_hr_deviation, hrv_deviation | 4 |
| 目标信息 | weeks_to_goal, target_distance_encoded, goal_type_encoded | 3 |
| 历史响应 | avg_vdot_delta_per_week, load_response_ratio, plan_adherence_rate | 3 |

模型配置：

```python
lgb.LGBMRegressor(
    n_estimators=100,
    max_depth=4,
    learning_rate=0.05,
    min_child_samples=20,
    subsample=0.8,
    colsample_bytree=0.8,
    reg_alpha=0.1,
    reg_lambda=1.0,
)
```

训练时间估计：200 条数据，21 维特征 < 2 秒。模型大小 < 500KB。推理时间 < 1ms。

**不确定性量化**：分位数回归，训练三个模型分别预测 p10/p50/p90，输出置信区间。

```python
for alpha in [0.1, 0.5, 0.9]:
    model = lgb.LGBMRegressor(
        objective='quantile', alpha=alpha,
        n_estimators=100, max_depth=4,
    )
```

#### 4.1.2 伤病风险模型（InjuryRiskPredictor）

**策略：规则基线 + 逻辑回归 + GBDT 集成**

**规则基线（冷启动）**：

| 规则 | 条件 | 风险等级 |
|------|------|---------|
| 急慢性负荷比过高 | ACWR > 1.5 | 高 |
| 训练单调性过高 | monotony > 2.0 | 中 |
| 连续高强度训练 | consecutive_hard_days > 3 | 中 |
| 静息心率异常 | resting_hr_deviation > 10% | 中 |

**逻辑回归层（数据 ≥ 100 条）**：

核心特征（8 维）：

| 特征 | 描述 |
|------|------|
| acwr | 急慢性负荷比 |
| training_monotony | 负荷单调性 |
| training_strain | 负荷应变 |
| consecutive_hard_days | 连续高强度天数 |
| fatigue_score | 疲劳评分 |
| resting_hr_deviation_pct | 静息心率偏离 |
| weekly_volume_change_pct | 周跑量变化率 |
| hrv_deviation_pct | HRV 偏离 |

```python
LogisticRegression(
    penalty='l2', C=0.1,
    class_weight='balanced',
    max_iter=1000
)
CalibratedClassifierCV(model, method='isotonic', cv=3)
```

**GBDT 增强层（数据 ≥ 300 条）**：

```python
lgb.LGBMClassifier(
    n_estimators=50,
    max_depth=3,
    learning_rate=0.05,
    min_child_samples=30,
    scale_pos_weight=10,
    is_unbalance=True
)
```

集成策略：逻辑回归概率 × 0.4 + GBDT 概率 × 0.6，权重通过交叉验证确定。

**伤病标签来源**：

| 标签类型 | 来源 | 可信度 |
|---------|------|--------|
| confirmed | 用户通过 InjuryReportTool 报告 | 高 |
| suspected | 训练中断 > 7 天 + 疲劳评分 > 70 | 中 |
| unconfirmed | 其他异常模式 | 低 |

#### 4.1.3 训练响应模型（TrainingResponsePredictor）

**策略：纯参数化模型 + 个体化校准**

```python
class BanisterIRModel:
    def __init__(self):
        self.tau_fitness = 42.0
        self.tau_fatigue = 10.0
        self.k_fitness = 1.0
        self.k_fatigue = 2.0
        self.vdot_base = 0.0

    def fit(self, training_history, vdot_history):
        from scipy.optimize import minimize
        result = minimize(
            objective,
            x0=[42.0, 10.0, 1.0, 2.0],
            bounds=[(20, 60), (5, 20), (0.1, 3.0), (0.5, 5.0)],
            method='L-BFGS-B'
        )

    def predict_training_impulse(self, session, current_state):
        trimp = self._calculate_trimp(session)
        return TrainingResponse(
            vdot_delta=fitness_impulse - fatigue_impulse,
            ctl_delta=fitness_impulse,
            atl_delta=fatigue_impulse,
            recovery_hours=self._estimate_recovery(session, current_state),
            fatigue_delta=fatigue_impulse / self.k_fatigue * 100
        )
```

训练时间 < 1 秒。这是三个模型中最确定性的，运动科学有成熟理论框架。

#### 4.1.4 新增 Agent 工具

| 工具名 | 功能 | 版本 |
|--------|------|------|
| PredictPerformanceTool | 预测 N 周后的 VDOT 和完赛时间 | v0.20 |
| PredictInjuryRiskTool | 评估当前训练方案的伤病风险 | v0.20 |
| PredictTrainingResponseTool | 预测单次训练对体能的影响 | v0.20 |
| ReportInjuryTool | 用户报告伤病事件，为伤病风险模型提供标签 | v0.20 |

#### 4.1.5 模型生命周期管理

```python
class ModelManager:
    def should_retrain(self, model_name: str) -> bool:
        # 条件1：新增数据超过阈值
        # 条件2：上次训练超过 N 天
        # 条件3：预测误差超过阈值

    def train(self, model_name: str) -> TrainResult:
        # 1. 从 Parquet 加载训练数据
        # 2. 特征工程
        # 3. 时间序列交叉验证（避免数据泄露）
        # 4. 训练 + 评估
        # 5. 保存模型 + 训练报告

    def evaluate(self, model_name: str) -> EvalReport:
        # 使用 TimeSeriesSplit 交叉验证
        # 输出：MAE, RMSE, 校准误差
```

重训练策略：

| 触发条件 | 动作 |
|---------|------|
| 首次数据 ≥ 100 条 | 自动训练 |
| 新增 50 条记录 | 自动重训练 |
| 距上次训练 > 30 天 | 自动重训练 |
| 用户手动触发 | `nanobotrun model train --name performance` |
| 训练失败 | 回退到参数化基线模型 |

训练时间预算：单模型 < 5 分钟。

#### 4.1.6 存储扩展

```
~/.nanobot-runner/
├── models/                        # 新增：ML 模型存储
│   ├── performance_v1.pkl
│   ├── injury_risk_v1.pkl
│   └── training_response_v1.pkl
├── predictions/                   # 新增：预测记录
│   └── {date}_prediction.json
└── (现有存储结构不变)
```

### 4.2 v0.21：数字孪生引擎

#### 4.2.1 跑者状态向量（RunnerStateVector）

```python
@dataclass
class RunnerStateVector:
    timestamp: datetime

    # 体能维度
    vdot: float
    vdot_trend: float
    vo2max_estimate: float

    # 负荷维度
    ctl: float
    atl: float
    tsb: float
    acwr: float

    # 身体信号维度
    fatigue_score: float
    recovery_status: str
    resting_hr: float
    hrv_rmssd: float

    # 风险维度
    injury_risk_7d: float
    injury_risk_28d: float
    overtraining_risk: float

    # 训练模式维度
    weekly_volume_km: float
    intensity_distribution: dict
    long_run_frequency: float
```

#### 4.2.2 What-If 推演引擎

```python
class TwinEngine:
    def simulate_plan(
        self,
        current_state: RunnerStateVector,
        plan: TrainingPlan,
        weeks: int = 4
    ) -> list[RunnerStateVector]:
        """模拟执行训练计划后的状态演变"""

    def compare_plans(
        self,
        current_state: RunnerStateVector,
        plans: list[TrainingPlan],
        weeks: int = 4
    ) -> PlanComparison:
        """比较多个训练计划的预测效果"""

    def find_optimal_plan(
        self,
        current_state: RunnerStateVector,
        goal: TrainingGoal,
        constraints: PlanConstraints
    ) -> TrainingPlan:
        """搜索满足约束的最优训练计划"""
```

PlanComparison 输出示例：

```
计划对比（4周推演）：
┌──────────┬──────────┬──────────┬──────────┐
│ 指标      │ 计划A     │ 计划B     │ 计划C     │
├──────────┼──────────┼──────────┼──────────┤
│ VDOT预测  │ 42.3→43.1│ 42.3→42.8│ 42.3→43.3│
│ 伤病风险  │ 12%      │ 8%       │ 18%      │
│ 过度训练  │ 低       │ 极低      │ 中       │
│ 恢复余量  │ 充足     │ 充足      │ 紧张     │
│ 综合推荐  │ ⭐⭐⭐   │ ⭐⭐     │ ⭐       │
└──────────┴──────────┴──────────┴──────────┘
```

#### 4.2.3 新增 Agent 工具

| 工具名 | 功能 |
|--------|------|
| GetRunnerStateTool | 获取当前跑者状态向量 |
| SimulatePlanTool | 模拟训练计划效果 |
| ComparePlansTool | 对比多个计划 |
| FindOptimalPlanTool | 搜索最优计划 |

### 4.3 v0.22：多视角决策验证（条件性）

**触发条件**：nanobot-ai 的 SubagentManager 支持稳定的后台执行 + 结果回注

**如果底座支持**：实现 Coach Agent + Doctor Agent 双视角审查

- Coach Agent：从训练效果最大化角度审查计划
- Doctor Agent：从健康风险最小化角度审查计划
- 冲突时：LLM 作为"仲裁者"权衡双方论据

**如果底座不支持**：在单 Agent 内实现"角色切换"

- LLM 先以教练视角生成计划
- 再以医生视角审查计划
- 最后综合两个视角的结论

**注意**：v0.22 为条件性版本。如果底座不支持且角色切换方案在 v0.21 验证中效果不佳，可跳过 v0.22 直接进入 v0.23。v0.23 的决策追踪系统不依赖 v0.22 的多视角能力。

---

## 5. Phase C：自适应进化引擎（v0.23-v0.25）

### 5.1 v0.23：决策-结果追踪系统

#### 5.1.1 决策日志（DecisionLog）

```python
@dataclass
class DecisionRecord:
    decision_id: str
    timestamp: datetime

    runner_state: RunnerStateVector
    decision_type: str
    input_context: dict

    decision_summary: str
    tools_called: list[ToolCallRecord]
    prediction_made: PredictionSnapshot | None

    executed: bool | None = None
    execution_fidelity: float | None = None
    actual_outcome: OutcomeRecord | None = None
    user_feedback: str | None = None

    prediction_error: float | None = None
    decision_quality: float | None = None
```

#### 5.1.2 追踪接入方式

通过现有 Hook 系统无侵入接入：

```python
class DecisionTrackingHook(AgentHook):
    def before_iteration(self, context: dict) -> dict:
        self._current_state = self._capture_runner_state()
        self._tools_called = []
        return context

    def before_execute_tools(self, tools: list, context: dict) -> list:
        self._tools_called.extend(tools)
        return tools

    def after_iteration(self, result: str, context: dict) -> str:
        record = DecisionRecord(
            runner_state=self._current_state,
            tools_called=self._tools_called,
            decision_summary=result[:500],
        )
        self._decision_store.save(record)
        return result
```

#### 5.1.3 结果回填机制

```python
class OutcomeTracker:
    def check_plan_execution(self, plan_id: str) -> ExecutionReport:
        """对比计划训练 vs 实际训练，计算 execution_fidelity"""

    def check_prediction_accuracy(self, prediction_id: str) -> AccuracyReport:
        """对比预测 VDOT vs 实际 VDOT，对比预测伤病风险 vs 实际伤病事件"""

    def generate_feedback_prompt(self, decision_id: str) -> str:
        """生成用户反馈收集提示"""
```

#### 5.1.4 存储设计

```
~/.nanobot-runner/
├── decisions/                     # 新增：决策日志
│   └── 2026-05/
│       ├── 2026-05-07_decisions.parquet
│       └── ...
├── outcomes/                      # 新增：结果记录
│   └── 2026-05/
│       ├── 2026-05-07_outcomes.parquet
│       └── ...
├── models/                        # 已有
└── (现有存储结构不变)
```

### 5.2 v0.24：个性化进化模型

#### 5.2.1 个体化参数学习

```python
class PersonalizationEngine:
    def learn_from_decisions(self, decisions: pl.LazyFrame) -> PersonalizationProfile:
        # 1. 学习训练响应特征
        #    - 这位跑者对高强度间歇的响应比持续跑好？
        #    - 恢复时间需要比模型预测的更长？
        response_profile = self._learn_response_profile(decisions)

        # 2. 学习决策偏好
        #    - 用户更倾向于执行哪种类型的建议？
        #    - 哪种表达方式用户接受度更高？
        preference_profile = self._learn_preference_profile(decisions)

        # 3. 学习预测校准参数
        #    - 系统对这位跑者的预测是系统性偏高还是偏低？
        #    - 哪些特征的预测误差最大？
        calibration_profile = self._learn_calibration_profile(decisions)

        return PersonalizationProfile(
            response=response_profile,
            preference=preference_profile,
            calibration=calibration_profile
        )
```

#### 5.2.2 预测校准层

```python
class PredictionCalibrator:
    def calibrate(self, prediction: Prediction, history: pl.LazyFrame) -> Prediction:
        bias = self._estimate_systematic_bias(history)
        uncertainty_adjustment = self._estimate_uncertainty_adjustment(history)

        return Prediction(
            value=prediction.value * (1 - bias),
            lower_bound=prediction.value * (1 - bias) - uncertainty_adjustment,
            upper_bound=prediction.value * (1 - bias) + uncertainty_adjustment,
            confidence=prediction.confidence * self._reliability_score(history)
        )
```

#### 5.2.3 LLM 提示策略优化

```python
class PromptStrategyOptimizer:
    def optimize_plan_prompt(self, decisions: pl.LazyFrame) -> dict:
        # 策略维度：
        #   - 建议语气：直接/温和/数据驱动
        #   - 信息密度：简洁/详细
        #   - 决策风格：保守/激进/平衡
        #   - 解释深度：结论/推理过程/数据支撑
        return {
            "preferred_tone": "data_driven",
            "optimal_detail_level": "moderate",
            "best_decision_style": "balanced",
            "explanation_depth": "with_evidence"
        }
```

### 5.3 v0.25：进化闭环

#### 5.3.1 自进化循环

```
决策 → 执行 → 结果追踪 → 误差分析 → 模型校准 → 提示优化 → 更好的决策
  ↑                                                        │
  └────────────────────────────────────────────────────────┘
```

#### 5.3.2 自动化进化触发器

```python
class EvolutionTrigger:
    def check_and_evolve(self) -> EvolutionReport:
        # 触发条件1：预测误差持续偏高
        if self._prediction_error_trend() > 0.15:
            self._trigger_model_retrain()

        # 触发条件2：决策接受率下降
        if self._decision_acceptance_rate() < 0.6:
            self._trigger_prompt_optimization()

        # 触发条件3：新数据积累
        if self._new_data_count() > 50:
            self._trigger_incremental_learning()

        # 触发条件4：季节/目标变化
        if self._detected_goal_change():
            self._trigger_strategy_reset()
```

#### 5.3.3 进化仪表盘

```bash
$ nanobotrun evolution status

🧬 进化引擎状态
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 决策记录：1,247 条（最近30天：89 条）
🎯 预测准确率：87.3%（↑2.1% vs 上月）
✅ 决策接受率：78.5%（↑5.3% vs 上月）
🔧 模型版本：performance_v3, injury_risk_v2
📈 个性化程度：高（已学习 89 个个体化参数）
🔄 上次进化：2026-05-05（模型重训练）
⏭ 下次计划：2026-05-20（策略优化检查）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 6. 多智能体路线图（条件性）

基于 nanobot-ai 底座的 Subagent 能力演进：

| 底座能力 | Runner 可实现 | 版本 |
|---------|-------------|------|
| Subagent 稳定执行 + 结果回注 | Coach + Doctor 双视角审查 | v0.22 |
| Subagent 间消息传递 | 多 Agent 辩论协议 | v0.24+ |
| Subagent 工具共享 | 共享预测引擎和孪生引擎 | v0.24+ |
| Subagent 动态创建 | 按需创建专项 Agent（如赛前策略师） | v0.25+ |

**关键原则**：多智能体是增强手段而非核心依赖。即使底座不支持，单 Agent + 角色切换也能实现 80% 的价值。

---

## 7. ML 技术选型

### 7.1 约束条件

| 约束 | 典型值 |
|------|--------|
| CPU | 4-8 核，无 GPU |
| 内存 | 8-16 GB |
| 模型文件大小 | < 50MB |
| 单次训练时间 | < 5 分钟 |
| 推理时间 | < 100ms |
| 典型数据量 | 100-2000 条训练记录 |
| 特征维度 | 20-50 维 |

### 7.2 依赖选择

| 需求 | 方案 | 理由 |
|------|------|------|
| ML 框架 | scikit-learn | 轻量（~30MB）、CPU 优化、模型序列化成熟 |
| 梯度提升 | LightGBM (CPU 版) | 比 XGBoost 更快、内存更少、模型文件小 |
| 概率校准 | scikit-learn CalibratedClassifierCV | 内置，无需额外依赖 |
| 贝叶斯推断 | scipy.optimize + 自定义 | Banister 模型参数少，scipy 足够 |
| 模型序列化 | joblib (scikit-learn 内置) | 高效处理 numpy 数组 |
| 特征工程 | polars (已有) + numpy (已有) | 零新增依赖 |

**不引入的依赖**：PyTorch、TensorFlow、XGBoost、PyMC、Stan

**新增依赖总计约 45MB**（scikit-learn ~30MB + LightGBM ~15MB），与现有依赖（polars ~80MB, pyarrow ~100MB）相比可接受。

### 7.3 模型选型决策树

```
数据量 < 200 条？
├── 是 → 参数化运动科学模型 + 统计校准
│   ├── Banister IR Model（训练响应 + 性能预测冷启动）
│   └── 专家规则 + 概率校准（伤病风险）
└── 否 → 传统 ML 模型
    ├── LightGBM（性能预测、伤病风险增强）
    ├── 逻辑回归 + 特征工程（伤病风险基线）
    └── 参数化模型 + ML 校准层（训练响应）
```

### 7.4 防过拟合策略

| 策略 | 实施方式 |
|------|---------|
| 浅树 | LightGBM max_depth=3-4 |
| 强正则化 | L1/L2 正则化，C=0.1 |
| 叶节点最小样本 | min_child_samples=20-30 |
| 时间序列交叉验证 | TimeSeriesSplit，不用随机 CV |
| 分位数回归 | 输出置信区间而非点估计 |
| 集成多模型 | 逻辑回归 + GBDT 加权平均 |
| 冷启动回退 | 数据不足时使用参数化基线 |

---

## 8. 新增 CLI 命令

| 命令 | 功能 | 版本 |
|------|------|------|
| `nanobotrun model train --name <model>` | 手动训练/重训练模型 | v0.20 |
| `nanobotrun model status` | 查看模型状态和性能指标 | v0.20 |
| `nanobotrun predict performance --weeks 4` | 预测未来性能 | v0.20 |
| `nanobotrun predict injury-risk` | 评估当前伤病风险 | v0.20 |
| `nanobotrun predict training-response --distance 10k --pace 5:30` | 预测训练响应 | v0.20 |
| `nanobotrun twin simulate --plan <plan_id> --weeks 4` | 模拟训练计划效果 | v0.21 |
| `nanobotrun twin compare --plans <id1,id2,id3>` | 对比多个计划 | v0.21 |
| `nanobotrun twin state` | 查看当前跑者状态向量 | v0.21 |
| `nanobotrun evolution status` | 查看进化引擎状态 | v0.25 |
| `nanobotrun evolution trigger` | 手动触发进化检查 | v0.25 |

---

## 9. 版本路线图

```
v0.19 (当前) ─── v0.20 ─── v0.21 ─── v0.22 ─── v0.23 ─── v0.24 ─── v0.25
  身体信号      预测智能   数字孪生   多视角     决策追踪   个性化     进化闭环
  HRV/疲劳     三大模型   状态向量   决策验证   结果回填   参数学习   自进化循环
  恢复监控     Agent工具  What-If   (条件性)   Hook接入   校准层     仪表盘
```

| 版本 | 核心交付 | 依赖变更 |
|------|---------|---------|
| v0.20 | 预测引擎 + 3 个 ML 模型 + 4 个 Agent 工具（含 ReportInjuryTool） | +scikit-learn, +lightgbm |
| v0.21 | 孪生引擎 + 状态向量 + What-If 推演 + 计划对比 + SimulatePlanTool | 无新依赖 |
| v0.22 | 多视角决策验证（条件性） | 无新依赖 |
| v0.23 | 决策追踪 Hook + 结果回填 + 决策日志存储 | 无新依赖 |
| v0.24 | 个性化引擎 + 预测校准 + 提示策略优化 | 无新依赖 |
| v0.25 | 进化触发器 + 进化仪表盘 + 自进化循环 | 无新依赖 |

---

## 10. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 数据不足导致 ML 模型无效 | 预测不准确 | 双轨制：参数化基线兜底，ML 增强可选 |
| 本地计算资源限制 | 训练时间过长 | 严格控制模型复杂度，训练时间预算 5 分钟 |
| 伤病事件稀少 | 伤病风险模型欠拟合 | 规则基线 + 强正则化 + 类别权重平衡 |
| LLM 对预测结果的误读 | 错误决策 | 预测输出包含置信区间 + 使用建议，LLM 必须参考 |
| Subagent 底座不支持 | 多视角决策无法实现 | 单 Agent 角色切换作为降级方案 |
| 预测过度自信 | 用户过度依赖 | 输出校准概率 + 置信区间 + 明确不确定性声明 |
| 冷启动期用户体验平淡 | 用户流失 | 参数化基线立即可用，展示"系统正在学习你的特征"进度 |

---

## 11. 成功指标

| 指标 | v0.20 目标 | v0.23 目标 | v0.25 目标 |
|------|-----------|-----------|-----------|
| VDOT 预测 MAE | < 1.0 | < 0.8 | < 0.5（个体化校准后） |
| 伤病风险 AUC | > 0.70 | > 0.75 | > 0.80 |
| 训练计划接受率 | 基线测量 | +10% | +20% |
| 预测校准误差 | < 15% | < 10% | < 5% |
| 模型训练时间 | < 5 分钟 | < 5 分钟 | < 5 分钟 |
| 推理延迟 | < 100ms | < 100ms | < 100ms |
