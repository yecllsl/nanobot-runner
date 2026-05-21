# AGENTS.md - Nanobot Runner AI开发快速参考

> **版本**: v5.16.0 | **更新日期**: 2026-05-21
> **当前基线**: v0.24.0
> **说明**: 本文档为AI Agent快速参考，详细内容请查阅对应专门文档。

---

## 1. 角色与目标

### 你的角色

你是一位精通 **Python 数据工程** 和 **CLI 开发** 的高级工程师。熟悉 Polars/Parquet 数据处理、Typer/Rich CLI 开发。

### 核心目标

在保证 **数据一致性** 和 **执行性能** 的前提下，高效完成需求。每一次代码修改必须：
- 保持数据的完整性和准确性
- 不引入性能退化
- 符合项目架构规范

### 业务边界

**仅处理单用户本地跑步数据**，明确不支持：
- 多租户系统
- Web UI
- 云端存储
- 实时流处理

---

## 2. 技术栈与版本

| 类别 | 技术 | 版本要求 |
|------|------|----------|
| **核心底座** | nanobot-ai | Latest |
| **开发语言** | Python | 3.11+ |
| **CLI框架** | Typer + Rich | Latest |
| **数据存储** | Apache Parquet | via pyarrow |
| **计算引擎** | Polars | 0.20+ |
| **ML框架** | scikit-learn | 1.5+ |
| **科学计算** | scipy | 1.10+ |
| **模型解释** | shap | 0.48+ |
| **模型序列化** | joblib | 1.3+ |
| **数据解析** | fitparse | Latest |
| **包管理** | uv | Latest |

> 详细架构设计见：[架构设计说明书](docs/architecture/架构设计说明书.md)

---

## 3. 项目架构

### 3.1 代码库结构

```
src/
├── core/                       # 核心模块
│   ├── base/                   # 基础设施模块
│   ├── calculators/            # 计算器模块
│   ├── config/                 # 配置模块
│   ├── storage/                # 存储模块
│   ├── report/                 # 报告模块
│   ├── models/                 # 模型模块
│   ├── transparency/           # AI决策透明化模块
│   ├── plan/                   # 智能跑步计划模块
│   ├── export/                 # 数据导出模块 (v0.18.0)
│   ├── visualization/          # 数据可视化模块 (v0.18.0)
│   ├── analysis/               # 身体信号分析模块 (v0.19.0)
│   │   ├── hrv.py              # 心率变异分析
│   │   ├── fatigue.py          # 疲劳度评估
│   │   └── body_signals.py     # 身体信号解读
│   ├── prediction/             # ML预测模块 (v0.20.0)
│   │   ├── models.py           # 预测数据模型
│   │   ├── vdot_predictor.py   # VDOT趋势预测
│   │   ├── race_predictor.py   # 比赛成绩预测
│   │   ├── injury_predictor.py # 伤病风险预测
│   │   └── model_manager.py    # 模型生命周期管理
│   ├── twin/                   # 数字孪生引擎 (v0.21.0)
│   │   ├── models.py           # 状态向量数据模型
│   │   ├── twin_engine.py      # 数字孪生引擎编排层
│   │   ├── state_vector_builder.py # 5维度状态向量构建器
│   │   └── whatif_simulator.py # What-If推演器
│   └── evolution/              # 自适应进化引擎 (v0.23.0)
│       ├── models.py           # 决策/结果数据模型
│       ├── config.py           # 进化配置Schema
│       ├── evolution_store.py  # 决策/结果存储层
│       ├── decision_logger.py  # 决策记录器
│       ├── outcome_collector.py # 结果收集器
│       ├── evolution_engine.py # 进化引擎编排层
│       └── decision_log_hook.py # Agent生命周期钩子
├── agents/
│   ├── tools.py                # Agent 工具集
│   └── tools_evolution.py      # 进化模块Agent工具 (v0.23.0)
├── notify/                     # 飞书通知
└── cli/                        # CLI 模块
    ├── commands/               # 命令模块
    ├── handlers/               # 业务逻辑调用层
    └── app.py                  # CLI 应用入口
```

### 3.2 核心数据流

```
FIT文件 → FitParser → IndexManager(SHA256去重) → StorageManager → Parquet(按年分片)
```

### 3.3 依赖注入流程

```
AppContextFactory.create_context()
    ↓
AppContext
    ├── storage: StorageManager
    ├── analytics: AnalyticsEngine
    ├── profile: ProfileEngine
    ├── session_repo: SessionRepository
    ├── config: ConfigManager
    ├── plan_manager: PlanManager
    ├── evolution_engine: EvolutionEngine  # v0.23.0新增
    └── ... (其他组件)
    ↓
CLI Handlers / Agent Tools
```

> 详细模块设计见：[架构设计说明书](docs/architecture/架构设计说明书.md)

---

## 4. 开发工作流

### 4.1 思考协议

在给出任何代码之前，必须在 `<thinking>` 标签中输出：

```
<thinking>
1. 用户的真实意图是什么？
2. 涉及到哪些文件？
3. 可能的副作用是什么？
4. 是否有现成的工具/函数可以复用？
</thinking>
```

### 4.2 工作流程

1. **思考与计划**：输出修改计划，等待用户确认
2. **阅读上下文**：使用工具阅读相关文件，不凭空想象
3. **最小化修改**：只修改完成需求所必需的代码
4. **自检**：检查 lint、类型、测试、编码规范

### 4.3 全局方法论嵌入（铁律）

以下全局方法论嵌入在所有开发步骤中，不可跳过。详细决策矩阵与铁律见 [Skills协作.md](.trae/Skills协作.md)。

| 方法论 | 嵌入位置 | 铁律 |
|--------|---------|------|
| **TDD** | 编写任何功能代码或修复代码时 | 没有失败测试，不写生产代码（RED→GREEN→REFACTOR） |
| **systematic-debugging** | Bug根因不明或测试失败时 | 没有根因调查，不提任何修复方案 |
| **verification-before-completion** | 声称完成、修复、通过之前 | 没有新鲜验证证据，不做完成声称 |
| **brainstorming** | 需求不明确或新功能设计时 | 不经设计批准，不写任何代码 |

**嵌入执行示例**：

```
功能开发 {
    步骤1: 输入验证（检查任务清单、架构方案）
    步骤2: TDD循环（先写失败测试 → 写最少实现 → 重构优化）
    步骤3: verification（运行 lint/test/typecheck，拿证据）
    步骤4: 输出交付物（代码 + 测试 + 交付报告）
}
```

**违反后果**：跳过TDD直接编码 = 测试覆盖不足；跳过verification声称完成 = 虚假完成。

---

## 5. 编码规范与铁律

### 5.1 绝对禁止

- 禁止直接实例化核心组件：必须通过 `get_context()` 获取应用上下文
- 禁止在代码中硬编码任何密钥或敏感信息：必须使用 `config` 模块
- 禁止使用 `# type: ignore`：必须写出正确的类型注解
- 禁止擅自安装新的依赖：如果需要，必须先向用户请示
- 禁止返回 `Dict[str, Any]`：必须使用类型安全的数据类
- 禁止在 LazyFrame 中过早调用 `.collect()`：仅最终输出时调用
- 禁止使用裸 `Exception`：必须使用自定义异常
- 禁止引入复杂设计模式：保持代码简单直白

### 5.2 必须遵守

- 所有数据库查询必须使用 LazyFrame
- 错误处理必须使用项目统一的异常类
- 类名使用 PascalCase，函数/变量使用 snake_case，常量使用 UPPER_SNAKE_CASE
- 核心模块类型注解覆盖率 ≥ 80%
- 编写新功能前，先搜索 `src/core/` 和 `src/utils/` 目录，复用现有函数
- 所有新增字段/工具，必须更新 Schema/TOOL_DESCRIPTIONS

### 5.3 依赖注入规范

```python
from src.core.context import get_context

def some_function():
    context = get_context()
    storage = context.storage
    analytics = context.analytics
```

> 详细规范与代码示例见：[开发指南](docs/guides/development_guide.md)

---

## 6. 常用命令

### 数据管理

```bash
uv run nanobotrun data import <path> [--force]
uv run nanobotrun data stats [--year YYYY]
```

### 数据分析

```bash
uv run nanobotrun analysis vdot
uv run nanobotrun analysis load
uv run nanobotrun analysis hr-drift

# v0.19.0 - 身体信号分析
uv run nanobotrun analysis hrv [--days 7/30/90]
uv run nanobotrun analysis hr-recovery
uv run nanobotrun analysis fatigue
uv run nanobotrun analysis recovery
```

### 数据可视化

```bash
uv run nanobotrun viz vdot [--days 7/30/90/365]
uv run nanobotrun viz load [--days 30/90/180]
uv run nanobotrun viz hr-zones --start YYYY-MM-DD --end YYYY-MM-DD [--age 30]
```

### 数据导出

```bash
uv run nanobotrun export sessions --format csv/json/parquet [--start YYYY-MM-DD] [--end YYYY-MM-DD]
```

### 报告与计划

```bash
uv run nanobotrun report weekly
uv run nanobotrun report monthly
uv run nanobotrun plan create --goal "全马破4" --race-date 2024-12-01
uv run nanobotrun plan status --plan-id <plan_id>
```

### 身体状态查看 (v0.19.0)

```bash
uv run nanobotrun status today      # 今日身体状态
uv run nanobotrun status weekly     # 本周身体状态摘要
```

### 自适应进化 (v0.23.0+)

```bash
uv run nanobotrun evolution status                      # 查看进化状态
uv run nanobotrun evolution history [--days 30]         # 查询决策历史
uv run nanobotrun evolution feedback <id> --score 4     # 提交用户反馈
uv run nanobotrun evolution accuracy [--days 30]        # 查看预测准确度
uv run nanobotrun evolution fidelity [--days 30]        # 查看执行忠实度

# v0.24.0 - 个性化学习
uv run nanobotrun evolution calibration [--model-type TYPE]  # 查看校准状态
uv run nanobotrun evolution response [--months 6]            # 训练响应性分析
```

### 系统管理

```bash
uv run nanobotrun system init
uv run nanobotrun system config
uv run nanobotrun system backup
```

### 代码质量

```bash
uv run ruff format src/ tests/
uv run ruff check src/ tests/
uv run mypy src/ --ignore-missing-imports
uv run pytest tests/unit/
```

> 完整命令参考见：[CLI使用指南](docs/guides/cli_usage.md)

---

## 7. 测试策略

- **必须编写单元测试**：核心业务逻辑（`src/core/`）
- **必须编写集成测试**：模块间交互（`tests/integration/`）
- **必须 Mock 外部 API 调用**：飞书通知、LLM 调用
- **禁止 Mock 内部业务逻辑**：保持测试真实性
- **禁止使用真实用户数据**：必须使用脱敏数据

> 详细测试规范见：[测试指南](docs/guides/testing_guide.md)

---

## 8. 业务术语

| 术语 | 定义 | 示例 |
|------|------|------|
| **Session** | 一次完整的跑步活动记录 | 2024-01-15 的晨跑记录 |
| **VDOT** | 跑力值，衡量跑者有氧能力的指标 | VDOT 45.2 表示中等水平 |
| **TSS** | 训练压力分数，衡量单次训练强度 | TSS 150 表示高强度训练 |
| **ATL** | 急性训练负荷，7天EWMA | ATL 50 表示近期训练负荷较高 |
| **CTL** | 慢性训练负荷，42天EWMA | CTL 65 表示体能基础扎实 |
| **TSB** | 训练压力平衡，CTL - ATL | TSB +10 表示体能充沛 |
| **RPE** | 主观疲劳度，1-10分 | RPE 7 表示较累 |
| **DecisionLog** | AI决策日志记录 | 包含决策类型、建议、执行状态等 |
| **OutcomeRecord** | 决策执行结果记录 | 包含忠实度、预测误差、用户反馈等 |
| **Execution Fidelity** | 执行忠实度(0-1) | 衡量计划执行与AI建议的匹配程度 |
| **Prediction MAE** | 预测平均绝对误差 | 衡量AI预测准确度 |

> 完整术语表与数据结构定义见：[API文档](docs/api/api_reference.md) 和源码 Docstring

---

## 9. 详细文档索引

| 文档 | 路径 | 内容 |
|------|------|------|
| 指令手册 | `.trae/指令手册.md` | 六类角色指令定义/输入输出/验收标准（查表型速查） |
| 协作链路 | `.trae/协作链路.md` | 版本迭代全流程/准入准出/异常处理/单人裁剪（流程型操作） |
| Skills协作 | `.trae/Skills协作.md` | 全局Skill与项目Skill协作规范/决策矩阵/铁律（决策型方法论） |
| 架构设计 | `docs/architecture/架构设计说明书.md` | 系统架构、模块设计、技术选型 |
| 开发指南 | `docs/guides/development_guide.md` | 编码规范、Polars约束、异常处理、类型注解 |
| CLI使用 | `docs/guides/cli_usage.md` | 完整命令参考、安装配置 |
| 测试指南 | `docs/guides/testing_guide.md` | 测试策略、Mock方法、测试数据 |
| Agent工具 | `docs/guides/agent_tools_guide.md` | 工具扩展指南 |
| API参考 | `docs/api/api_reference.md` | API接口文档 |
| 需求规格 | `docs/requirements/REQ_需求规格说明书.md` | 功能需求、验收标准 |
| 产品规划 | `docs/product/产品规划方案.md` | 路线图、版本规划 |
