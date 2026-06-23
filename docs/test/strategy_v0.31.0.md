# 回归测试策略文档 v0.31.0

> **版本**: v0.31.0（质量提升专项版本）
> **文档版本**: v1.0
> **制定日期**: 2026-06-23
> **当前基线**: v0.30.0（4669 用例通过，覆盖率 83%）
> **测试类型**: 全方位回归测试
> **覆盖范围**: v0.5 - v0.31.0 全版本功能模块

---

## 1. 文档目的与范围

### 1.1 目的

本文档为 v0.31.0 质量提升专项版本制定**全方位回归测试策略**，旨在：
- 验证 v0.31.0 代码重构（死代码清理/依赖移除/Handler 删除/代码内联）未引入功能回归
- **全量回归验证 v0.5 - v0.30.0 所有已交付功能模块的完整性**
- 确保非功能性指标（性能/覆盖率/类型安全/代码规范）达标
- 为版本发布提供量化质量门禁依据

### 1.2 测试范围界定

#### 1.2.1 全功能模块覆盖矩阵

| 模块 | 版本 | 核心功能 | 测试优先级 | 回归风险 |
|------|------|----------|-----------|---------|
| **数据管理** | v0.5+ | FIT 解析、SHA256 去重、Parquet 按年分片 | P0 | 低 |
| **数据分析** | v0.8+ | VDOT、TSS/ATL/CTL/TSB、心率漂移 | P0 | 低 |
| **Agent 交互** | v0.8+ | 自然语言查询、智能建议 | P1 | 中 |
| **CLI 框架** | v0.9+ | 分层架构、Rich 格式化 | P0 | **中**（Handler 删除） |
| **依赖注入** | v0.9+ | AppContext、get_context() | P0 | 低 |
| **智能跑步计划** | v0.10-0.12 | 计划生成、LLM 调整、目标预测 | P0 | 低 |
| **工具生态** | v0.13 | MCP 协议、ToolManager | P1 | 低 |
| **AI 决策透明化** | v0.15 | TransparencyEngine、TraceLogger | P1 | 低 |
| **Core 模块化** | v0.16 | diagnosis/memory/personality/skills/validate/tools | P1 | 低 |
| **AI 底座激活** | v0.17 | Hook 系统、Subagent、异步确认、Cron 提醒 | P1 | 低 |
| **可视化与导出** | v0.18 | PlotextRenderer、CSV/JSON/Parquet 导出 | P0 | **中**（Handler 删除） |
| **飞书通知** | v0.9+ | GatewayServer、FeishuAuth、FeishuNotifier | P1 | 低 |
| **身体信号分析** | v0.19 | HRV、疲劳度、恢复状态、身体信号解读 | P0 | 低 |
| **ML 增强预测** | v0.20 | VDOT/比赛/伤病预测、模型管理 | P0 | **中**（shap 移除） |
| **数字孪生引擎** | v0.21 | 5 维状态向量、What-If 推演、计划对比 | P0 | 低 |
| **进化引擎** | v0.23-0.25 | 决策追踪、个性化学习、自适应进化 | P0 | 低 |
| **底座升级+新特性** | v0.26 | GoalState、推理可见化、Model Presets | P1 | 低 |
| **WebUI 基础** | v0.27 | AI 对话、WebSocket、token 认证 | P1 | **中**（server.py 内联） |
| **WebUI 数据可视化** | v0.28 | 6 大页面、10 个 API 端点 | P1 | 低 |
| **WebUI 管理控制台** | v0.29 | 计划管理、进化控制台、设置中心 | P1 | 低 |
| **v0.31.0 重构变更** | v0.31 | 死代码清理、依赖移除、Handler 删除、asdict() | P0 | **高** |

#### 1.2.2 测试排除范围

- LLM 模型输出内容的不确定性验证（非确定性逻辑）
- nanobot-ai 框架内部实现测试（由框架方负责）
- 前端 React 组件单元测试（由前端构建流程覆盖）
- CI/CD 流水线配置验证（由 DevOps 负责）

### 1.3 v0.31.0 变更影响分析

| 变更类别 | 涉及模块 | 影响范围 | 回归测试重点 |
|---------|---------|---------|------------|
| **死代码删除** | llm_timeout, streaming, cli/utils | 无功能影响 | 验证零残留引用 |
| **Handler 删除** | export/prediction/status | CLI 命令调用链 | 直接调用 Engine 的正确性 |
| **依赖移除** | numba, pydantic-settings, shap, dulwich, questionary | 降级路径 | ImportError 降级验证 |
| **代码内联** | server.py → app.py | WebUI 启动 | create_server() 完整性 |
| **配置简化** | AppConfig.to_dict() | 配置序列化 | Enum 字段处理正确性 |

---

## 2. 测试类型规划

### 2.1 测试类型总览

```
┌─────────────────────────────────────────────────────────┐
│                    测试金字塔                             │
├─────────────────────────────────────────────────────────┤
│                                                         │
│                    /\  E2E 测试                          │
│                   /  \  (用户旅程、全链路)                │
│                  /----\                                  │
│                 /      \  集成测试                        │
│                /        \  (模块间交互)                   │
│               /----------\                               │
│              /            \  单元测试                     │
│             /              \  (函数/方法级)               │
│            /________________\                            │
│                                                         │
│   辅助测试: 性能测试 | 降级测试 | 兼容性测试 | 验收测试    │
└─────────────────────────────────────────────────────────┘
```

### 2.2 单元测试（Unit Tests）

**目标**：验证最小可测试单元（函数/方法）的正确性

**覆盖模块与用例预估**：

| 模块 | 测试文件 | 用例数（基线） | v0.31.0 增量 | 优先级 |
|------|---------|------------|------------|--------|
| base/ | test_context, test_schema, test_logger, test_decorators, test_profile | ~150 | +5 | P0 |
| storage/ | test_parser, test_importer, test_indexer, test_parquet_manager, test_session_repository | ~200 | 0 | P0 |
| calculators/ | test_vdot, test_training_load, test_heart_rate, test_statistics | ~300 | 0 | P0 |
| config/ | test_manager, test_schema, test_env, test_backup, test_channels | ~180 | +10 | P0 |
| plan/ | test_plan_generator, test_plan_manager, test_goal_prediction, test_calendar, test_cron | ~350 | 0 | P0 |
| prediction/ | test_vdot_predictor, test_race_predictor, test_injury_predictor, test_model_manager | ~400 | +15 | P0 |
| twin/ | test_digital_twin, test_state_vector, test_whatif_simulator | ~150 | 0 | P0 |
| evolution/ | test_decision_logger, test_evolution_engine, test_calibration, test_prompt_tuner | ~350 | 0 | P0 |
| body_signal/ | test_hrv, test_fatigue, test_recovery, test_body_signal_engine | ~200 | 0 | P0 |
| transparency/ | test_transparency, test_streaming_hook, test_error_classifier | ~180 | 0 | P1 |
| export/ | test_csv, test_json, test_parquet, test_engine | ~120 | +10 | P0 |
| visualization/ | test_renderer, test_plotext_renderer, test_models | ~80 | 0 | P1 |
| webui/ | test_app, test_auth, test_routes_* | ~300 | +10 | P1 |
| cli/ | test_cli, test_formatter, test_commands | ~250 | +20 | P0 |
| agents/ | test_tools, test_tools_evolution, test_tools_body_signal | ~200 | 0 | P1 |
| notify/ | test_feishu, test_feishu_calendar, test_feishu_report | ~150 | 0 | P1 |
| init/ | test_wizard, test_generator, test_migrate | ~100 | 0 | P1 |
| skills/ | test_skill_manager | ~80 | 0 | P1 |
| memory/ | test_memory_manager, test_dream | ~60 | 0 | P1 |
| personality/ | test_personalization, test_feedback_loop | ~80 | 0 | P1 |
| **合计** | — | **~4180** | **+70** | — |

**单元测试准入条件**：
- 代码已通过 `ruff check` 和 `mypy`
- 新增/修改代码有对应单元测试
- Mock 规范：外部 API（飞书、LLM）必须 Mock，内部业务逻辑禁止 Mock

### 2.3 集成测试（Integration Tests）

**目标**：验证模块间交互的正确性

| 测试场景 | 测试文件 | 用例数 | 优先级 |
|---------|---------|--------|--------|
| 数据导入全链路 | test_import_flow | 5 | P0 |
| 数据分析集成 | test_analytics_flow | 5 | P0 |
| 计划生成集成 | test_plan_cli_integration | 8 | P0 |
| 预测模块集成 | test_prediction_integration | 5 | P0 |
| 进化引擎集成 | test_evolution_integration | 8 | P0 |
| 进化控制器 Hook | test_evolution_controller_hook | 5 | P0 |
| 进化报告链 | test_evolution_reporter_chain | 4 | P1 |
| 提示调优链 | test_prompt_tuner_chain | 4 | P1 |
| WebUI 启动 | test_webui_startup | 9 | P0 |
| WebUI v0.29 路由 | test_webui_v0290_routes | 5 | P1 |
| 数据契约 | test_data_contract | 5 | P0 |
| CLI 契约 | test_cli_contract | 5 | P0 |
| 导出 E2E | test_export_e2e | 4 | P0 |
| 可视化 E2E | test_viz_e2e | 3 | P1 |
| Gateway 消息流 | test_gateway_message_flow | 5 | P0 |
| 框架兼容性 | test_nanobot_compatibility | 5 | P0 |
| 框架集成 | test_framework_integration | 5 | P1 |
| 统计集成 | test_stats_integration | 3 | P1 |
| 场景：真实工作流 | test_real_workflow | 5 | P1 |
| 场景：Sprint3 E2E | test_sprint3_e2e | 5 | P1 |
| 场景：天气 Agent | test_weather_agent_natural_language | 3 | P2 |
| 场景：记忆+人格 | test_v0140_memory_personality | 3 | P2 |
| 场景：计划日历 | test_plan_calendar_integration | 3 | P1 |
| 模块：子 Agent 流 | test_subagent_flow | 3 | P2 |
| 模块：健康 Agent | test_health_agent_tool | 3 | P2 |
| 模块：知识 Agent | test_knowledge_agent_tool | 3 | P2 |
| 模块：地图 Agent | test_map_agent_tool | 3 | P2 |
| 模块：Coros Agent | test_coros_agent_tool | 3 | P2 |
| 模块：天气 Agent 工具 | test_weather_agent_tool | 3 | P2 |
| 模块：工作区流 | test_workspace_flow | 3 | P2 |
| 模块：验证流 | test_validate_flow | 3 | P2 |
| 模块：透明化集成 | test_transparency_integration | 3 | P2 |
| 模块：迁移流 | test_migration_flow, test_migrate_flow | 6 | P2 |
| 模块：初始化流 | test_init_flow | 3 | P2 |
| 模块：配置注入 | test_config_injection | 3 | P2 |
| **合计** | — | ~140 | — |

### 2.4 E2E 测试（End-to-End Tests）

**目标**：验证完整用户流程和系统行为

| 测试场景 | 测试文件 | 用例数 | 优先级 |
|---------|---------|--------|--------|
| Gateway 命令结构 | test_gateway_command | 3 | P0 |
| CLI 命令结构 | test_cli_command | 7 | P0 |
| 性能 E2E | test_performance_e2e | 7 | P0 |
| 训练计划 E2E | test_training_plan_e2e | 4 | P0 |
| 透明化 E2E | test_transparency_e2e | 5 | P1 |
| 用户旅程 | test_user_journey | 5 | P0 |
| WebUI 可视化 | test_webui_visualization | 10 | P1 |
| WebUI 设置 | test_webui_settings | 5 | P1 |
| WebUI 计划 | test_webui_plan | 5 | P1 |
| **合计** | — | ~51 | — |

### 2.5 性能测试（Performance Tests）

**目标**：验证系统性能无回归

| 测试场景 | 测试文件 | 性能基线 | 优先级 |
|---------|---------|---------|--------|
| 查询性能 | test_query_performance | < 1s | P0 |
| LazyFrame 性能 | test_lazyframe_performance | 无过早 collect | P0 |
| 报告生成性能 | test_report_performance | < 5s | P1 |
| 进化引擎性能 | test_evolution_performance | Hook 延迟 < 100ms | P1 |

### 2.6 降级测试（v0.31.0 专项）

**目标**：验证依赖移除后的降级路径

| 测试场景 | 依赖 | 降级行为 | 优先级 |
|---------|------|---------|--------|
| shap 缺失降级 | shap | 使用 sklearn feature_importances_ | P0 |
| dulwich 缺失降级 | dulwich | 跳过 Git 初始化 | P0 |
| questionary 缺失降级 | questionary | 使用默认配置 | P1 |
| numba 缺失验证 | numba | 纯 Python 执行 | P1 |
| pydantic-settings 缺失验证 | pydantic-settings | 使用 dataclass 配置 | P1 |

### 2.7 验收测试（Acceptance Tests）

**目标**：基于 UAT 用例验证用户场景

参考 `docs/test/uat_test_cases/` 下 100 个 UAT 用例，覆盖：
- UAT-001 ~ UAT-008：数据导入与查询
- UAT-009 ~ UAT-014：数据分析
- UAT-015 ~ UAT-020：训练计划与报告
- UAT-021 ~ UAT-027：系统管理与性能
- UAT-028 ~ UAT-042：MCP 工具与 Gateway
- UAT-043 ~ UAT-047：Cron 训练提醒
- UAT-048 ~ UAT-051：AI 透明化
- UAT-052 ~ UAT-055：偏好管理
- UAT-056 ~ UAT-060：技能管理
- UAT-061 ~ UAT-065：数据可视化
- UAT-066 ~ UAT-070：数据导出
- UAT-071 ~ UAT-080：身体信号分析
- UAT-081 ~ UAT-091：ML 智能预测
- UAT-092 ~ UAT-100：数字孪生

---

## 3. 测试环境配置

### 3.1 基础环境

| 组件 | 版本 | 说明 |
|------|------|------|
| Python | 3.11.x | 项目要求 ≥3.11,<3.13 |
| OS | Windows 10/11 | 主要开发环境 |
| 包管理 | uv (latest) | 统一依赖管理 |
| Agent 底座 | nanobot-ai ≥0.2.1 | 已验证兼容版本 |
| CLI 框架 | Typer + Rich | Latest |
| 数据引擎 | Polars 0.20+ | LazyFrame 优先 |
| 存储 | Apache Parquet (pyarrow) | 按年分片 |
| WebUI 后端 | FastAPI + uvicorn | ≥0.115 / ≥0.30 |
| WebUI 前端 | React + TypeScript + Recharts | via webui/ |

### 3.2 测试依赖

```toml
[project.optional-dependencies]
test = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "pytest-mock>=3.0.0",
    "pytest-timeout>=2.2.0",
    "pytest-asyncio>=0.23.0",
    "httpx>=0.27.0",
]
```

### 3.3 环境隔离

| 隔离维度 | 方式 | 说明 |
|---------|------|------|
| 配置目录 | `NANOBOT_CONFIG_DIR` | 测试配置与生产配置分离 |
| 数据目录 | `NANOBOT_DATA_DIR` | 测试数据与生产数据分离 |
| Workspace | 独立目录 | 测试工作区独立 |

### 3.4 降级测试环境（v0.31.0 专项）

为验证移除依赖后的降级路径，需准备**最小依赖环境**：

```bash
# 创建最小依赖虚拟环境（不安装 shap/dulwich/questionary）
uv venv .venv-minimal
uv pip install -e ".[test]" --no-deps
uv pip install nanobot-ai typer rich polars pyarrow fitparse numpy plotext scikit-learn scipy joblib fastapi uvicorn PyJWT
```

### 3.5 快速环境准备（PowerShell）

```powershell
# 1. 清理并创建测试目录
if (Test-Path ".nanobot-runner-test") { Remove-Item -Recurse -Force ".nanobot-runner-test" }
New-Item -ItemType Directory -Path ".nanobot-runner-test\test-data" -Force
New-Item -ItemType Directory -Path ".nanobot-runner-test\data" -Force

# 2. 设置环境变量
$env:NANOBOT_CONFIG_DIR = ".nanobot-runner-test"
$env:NANOBOT_DATA_DIR = ".nanobot-runner-test\data"

# 3. 初始化测试环境
uv run nanobotrun system init

# 4. 导入测试数据
uv run nanobotrun data import "<测试FIT文件目录>"
```

---

## 4. 门禁规则

### 4.1 准入规则（Entry Criteria）

测试执行前必须满足以下条件：

| 编号 | 准入条件 | 验证命令 | 通过标准 |
|------|---------|---------|---------|
| ENTRY-01 | 代码规范检查 | `uv run ruff check src/ tests/` | 0 error |
| ENTRY-02 | 代码格式检查 | `uv run ruff format --check src/ tests/` | 0 diff |
| ENTRY-03 | 类型检查 | `uv run mypy src/ --ignore-missing-imports` | 0 error |
| ENTRY-04 | 代码已提交 | `git status` | clean working tree |
| ENTRY-05 | v0.31.0 重构完成 | 对比重构报告 | 14 项任务已完成 |
| ENTRY-06 | 单元测试存在 | 检查 tests/ 目录 | 新增代码有对应测试 |

### 4.2 准出规则（Exit Criteria）

版本发布前必须满足以下条件：

| 编号 | 准出条件 | 验证命令 | 通过标准 |
|------|---------|---------|---------|
| EXIT-01 | 单元测试通过率 | `uv run pytest tests/unit/ -q` | 100% passed |
| EXIT-02 | 集成测试通过率 | `uv run pytest tests/integration/ -q` | 100% passed |
| EXIT-03 | E2E 测试通过率 | `uv run pytest tests/e2e/ -q` | ≥ 98% passed |
| EXIT-04 | 性能测试通过率 | `uv run pytest tests/performance/ -q` | 100% passed |
| EXIT-05 | core 覆盖率 | `uv run pytest tests/ --cov=src/core` | ≥ 80% |
| EXIT-06 | agents 覆盖率 | `uv run pytest tests/ --cov=src/agents` | ≥ 70% |
| EXIT-07 | cli 覆盖率 | `uv run pytest tests/ --cov=src/cli` | ≥ 60% |
| EXIT-08 | 总覆盖率 | `uv run pytest tests/ --cov=src` | ≥ 83%（v0.30.0 基线） |
| EXIT-09 | P0 Bug 数 | Bug 跟踪 | 0 |
| EXIT-10 | P1 Bug 数 | Bug 跟踪 | 0 |
| EXIT-11 | 性能无回归 | 对比 v0.30.0 基线 | 退化 < 20% |
| EXIT-12 | 降级路径验证 | 最小依赖环境测试 | 全部通过 |
| EXIT-13 | 死代码零残留 | Grep 扫描 | 零匹配 |

### 4.3 覆盖率要求（分层门禁）

| 模块 | 覆盖率要求 | 说明 |
|------|----------|------|
| `src/core/` | ≥ 80% | 核心业务逻辑，最高要求 |
| `src/agents/` | ≥ 70% | Agent 工具层 |
| `src/cli/` | ≥ 60% | CLI 命令层 |
| `src/notify/` | ≥ 70% | 通知模块 |
| **总覆盖率** | ≥ 83% | 对齐 v0.30.0 基线 |

---

## 5. 测试用例设计标准

### 5.1 命名规范

```python
def test_<模块>_<场景>_<预期结果>():
    """
    测试描述：验证XXX在YYY条件下的ZZZ行为
    """
```

**示例**：
```python
def test_vdot_calculator_with_valid_distance_returns_correct_value():
    """验证 VDOT 计算器在有效距离输入下返回正确值"""
```

### 5.2 结构规范（AAA 模式）

```python
def test_config_asdict_with_enum():
    # Arrange - 准备
    config = AppConfig(version="1.0", log_level=LogLevel.INFO)
    
    # Act - 执行
    result = config.to_dict()
    
    # Assert - 断言
    assert result["log_level"] == "INFO"
    assert result["version"] == "1.0"
```

### 5.3 用例覆盖要求

| 用例类型 | 覆盖要求 | 示例 |
|---------|---------|------|
| **正常路径** | 必须覆盖 | 有效输入→预期输出 |
| **边界条件** | 必须覆盖 | 空值、极值、临界值 |
| **异常路径** | 必须覆盖 | 无效输入、异常抛出 |
| **降级路径** | 可选依赖必须覆盖 | ImportError 降级 |
| **并发场景** | WebUI/API 必须覆盖 | run_in_threadpool |

### 5.4 Mock 规范

| 对象 | Mock 策略 |
|------|----------|
| 外部 API（飞书、LLM、天气） | **必须 Mock** |
| 文件系统 | 可 Mock 或使用临时目录 |
| 内部业务逻辑 | **禁止 Mock**（保持测试真实性） |
| 数据库查询 | 使用测试数据，禁止 Mock LazyFrame |

---

## 6. 全功能模块测试用例清单

### 6.1 数据管理模块（v0.5+）

| 用例 ID | 测试场景 | 预期结果 | 优先级 |
|---------|---------|---------|--------|
| TC-DM-001 | 单文件 FIT 导入 | 导入成功，数据写入 Parquet | P0 |
| TC-DM-002 | 批量 FIT 导入（≥10 文件） | 全部导入成功，显示统计 | P0 |
| TC-DM-003 | 重复文件导入（SHA256 去重） | 跳过重复文件 | P0 |
| TC-DM-004 | 无效 FIT 文件导入 | 报错且不影响其他文件 | P0 |
| TC-DM-005 | 数据统计查询 | 返回正确统计信息 | P0 |
| TC-DM-006 | 按年份过滤查询 | 返回指定年份数据 | P0 |
| TC-DM-007 | 按日期范围过滤查询 | 返回指定范围数据 | P0 |
| TC-DM-008 | 空数据库查询 | 优雅返回空结果 | P1 |
| TC-DM-009 | Parquet 按年分片验证 | 数据正确分片存储 | P1 |

### 6.2 数据分析模块（v0.8+）

| 用例 ID | 测试场景 | 预期结果 | 优先级 |
|---------|---------|---------|--------|
| TC-DA-001 | VDOT 计算（距离≥1500m） | 返回正确 VDOT 值 | P0 |
| TC-DA-002 | TSS 计算（时长×IF²×100） | 返回正确 TSS 值 | P0 |
| TC-DA-003 | ATL 计算（7 天 EWMA） | 返回正确 ATL 值 | P0 |
| TC-DA-004 | CTL 计算（42 天 EWMA） | 返回正确 CTL 值 | P0 |
| TC-DA-005 | TSB 计算（CTL - ATL） | 返回正确 TSB 值 | P0 |
| TC-DA-006 | 心率漂移分析 | 返回正确漂移率 | P0 |
| TC-DA-007 | 训练负荷趋势分析 | 返回正确趋势 | P0 |
| TC-DA-008 | 数据不足时降级 | 优雅降级，不阻塞 | P1 |
| TC-DA-009 | 时长格式化（HH:MM:SS） | 输出正确格式 | P1 |
| TC-DA-010 | 配速格式化（M'SS"/km） | 输出正确格式 | P1 |

### 6.3 智能跑步计划模块（v0.10-0.12）

| 用例 ID | 测试场景 | 预期结果 | 优先级 |
|---------|---------|---------|--------|
| TC-PL-001 | 计划创建（全马破4） | 生成完整训练计划 | P0 |
| TC-PL-002 | 计划状态查询 | 返回正确状态信息 | P0 |
| TC-PL-003 | 目标达成预测（<3s） | 3 秒内返回预测 | P0 |
| TC-PL-004 | LLM 计划调整 | 调整成功且合理 | P0 |
| TC-PL-005 | 计划执行记录 | 正确记录执行情况 | P0 |
| TC-PL-006 | 计划反馈提交 | 反馈记录成功 | P1 |
| TC-PL-007 | 长期规划生成 | 生成合理长期计划 | P1 |
| TC-PL-008 | 计划分析 | 返回正确分析结果 | P1 |

### 6.4 身体信号分析模块（v0.19）

| 用例 ID | 测试场景 | 预期结果 | 优先级 |
|---------|---------|---------|--------|
| TC-BS-001 | HRV 分析（RMSSD/SDNN） | 返回正确 HRV 指标 | P0 |
| TC-BS-002 | 疲劳度评估 | 返回正确疲劳等级 | P0 |
| TC-BS-003 | 恢复状态监测 | 返回正确恢复状态 | P0 |
| TC-BS-004 | 静息心率突增>10%预警 | 触发预警 | P0 |
| TC-BS-005 | TSB 截断[-50,50] | 正确截断 | P0 |
| TC-BS-006 | RPE 三级输入路径 | 正确处理 RPE | P0 |
| TC-BS-007 | DataQuality 三级降级 | 优雅降级 | P0 |
| TC-BS-008 | 身体信号综合解读 | 返回正确解读 | P1 |
| TC-BS-009 | 同日缓存机制 | 缓存命中正确 | P1 |
| TC-BS-010 | 数据不足降级 | 降级不阻塞 | P1 |

### 6.5 ML 增强预测模块（v0.20）

| 用例 ID | 测试场景 | 预期结果 | 优先级 |
|---------|---------|---------|--------|
| TC-PR-001 | VDOT 趋势预测 | 误差 < 5% | P0 |
| TC-PR-002 | 比赛成绩预测（全马） | 误差 < 8 分钟 | P0 |
| TC-PR-003 | 伤病风险预测 | 召回率 > 75% | P0 |
| TC-PR-004 | 分位数回归（p10/p50/p90） | 返回正确分位数 | P0 |
| TC-PR-005 | 伤病 GBDT 集成（4:6 加权） | 正确加权预测 | P0 |
| TC-PR-006 | 三层降级（ML→参数化→基础） | 降级路径正确 | P0 |
| TC-PR-007 | **shap 缺失降级到 sklearn** | **使用 feature_importances_** | **P0** |
| TC-PR-008 | 模型管理（训练/回滚） | 正确管理模型生命周期 | P0 |
| TC-PR-009 | 特征矩阵缓存 | 缓存命中正确 | P1 |
| TC-PR-010 | 同日缓存机制 | 缓存命中正确 | P1 |
| TC-PR-011 | 不确定性量化 | 标注置信区间 | P1 |
| TC-PR-012 | ML 推理延迟 < 100ms | 满足性能要求 | P1 |

### 6.6 数字孪生引擎模块（v0.21）

| 用例 ID | 测试场景 | 预期结果 | 优先级 |
|---------|---------|---------|--------|
| TC-TW-001 | 5 维状态向量构建 | 正确构建状态向量 | P0 |
| TC-TW-002 | 状态向量 TTL=24h | 过期后重新构建 | P0 |
| TC-TW-003 | What-If 推演（4 周） | 误差 < 8% | P0 |
| TC-TW-004 | 三层推演降级（5%/8%/12%） | 降级路径正确 | P0 |
| TC-TW-005 | 计划对比评分 | 评分合理（VDOT40%+伤病35%+恢复25%） | P0 |
| TC-TW-006 | 单计划 4 周推演 < 10s | 满足性能要求 | P0 |
| TC-TW-007 | 推演结果不确定性标注 | 标注置信区间 | P1 |

### 6.7 进化引擎模块（v0.23-0.25）

| 用例 ID | 测试场景 | 预期结果 | 优先级 |
|---------|---------|---------|--------|
| TC-EV-001 | 决策自动记录（100%） | 所有决策被记录 | P0 |
| TC-EV-002 | 结果回填 | 正确回填执行结果 | P0 |
| TC-EV-003 | 忠实度计算（可计算率>80%） | 正确计算忠实度 | P0 |
| TC-EV-004 | Hook 接入延迟 < 100ms | 满足性能要求 | P0 |
| TC-EV-005 | 训练响应性分析 | 分析结果正确 | P0 |
| TC-EV-006 | 预测校准（MAE 降低≥15%） | 校准有效 | P0 |
| TC-EV-007 | 线性修正（corrected=raw×scale） | 修正正确 | P0 |
| TC-EV-008 | EMA 更新（α=0.7，幅度±10%） | 更新正确 | P0 |
| TC-EV-009 | 进化触发器（4 条规则） | 触发条件正确 | P0 |
| TC-EV-010 | 提示调优（4 维参数空间） | 调优正确 | P0 |
| TC-EV-011 | 月度进化报告 | 报告生成正确 | P1 |
| TC-EV-012 | 闭环自动运行率 > 90% | 满足自动化要求 | P1 |
| TC-EV-013 | 用户反馈记录 | 反馈记录成功 | P1 |
| TC-EV-014 | 预测准确度查询 | 返回正确准确度 | P1 |

### 6.8 底座升级+新特性模块（v0.26）

| 用例 ID | 测试场景 | 预期结果 | 优先级 |
|---------|---------|---------|--------|
| TC-BS-001 | nanobot-ai 兼容性 | 零回归 | P0 |
| TC-BS-002 | GoalState 适配（SOUL.md 注入） | 正确注入使用指导 | P1 |
| TC-BS-003 | 推理可见化（emit_reasoning） | 推理片段写入 DecisionLog | P1 |
| TC-BS-004 | Model Presets 查看 | `model list` 正确显示 | P1 |
| TC-BS-005 | CLI 核心命令性能退化 < 20% | 满足性能要求 | P1 |

### 6.9 WebUI 基础模块（v0.27）

| 用例 ID | 测试场景 | 预期结果 | 优先级 |
|---------|---------|---------|--------|
| TC-WU-001 | WebUI 启动（--webui 标志） | 端口 8765 监听成功 | P0 |
| TC-WU-002 | **create_server() 从 app.py 导入** | **正常返回 uvicorn.Server** | **P0** |
| TC-WU-003 | WebSocket 配置加载 | 配置正确加载 | P0 |
| TC-WU-004 | token 认证默认启用 | 未授权访问被拒 | P0 |
| TC-WU-005 | WebUI 首屏加载 < 3s | 满足性能要求 | P1 |
| TC-WU-006 | WebSocket 握手 < 100ms | 满足性能要求 | P1 |
| TC-WU-007 | 流式输出延迟 < 200ms | 满足性能要求 | P1 |
| TC-WU-008 | 工具调用成功率 ≥ 99% | 满足兼容性要求 | P1 |
| TC-WU-009 | 向后兼容（不启用 WebUI） | 飞书/CLI 不受影响 | P0 |

### 6.10 WebUI 数据可视化模块（v0.28）

| 用例 ID | 测试场景 | 预期结果 | 优先级 |
|---------|---------|---------|--------|
| TC-WV-001 | 仪表盘页面加载 | 首屏 < 2s | P0 |
| TC-WV-002 | VDOT 趋势页面 | 图表渲染 < 1s | P0 |
| TC-WV-003 | 训练负荷页面 | 图表渲染 < 1s | P0 |
| TC-WV-004 | 活动列表页面 | 分页响应 < 500ms | P0 |
| TC-WV-005 | 活动详情页面 | 正确显示详情 | P0 |
| TC-WV-006 | 身体信号页面 | 正确显示信号 | P0 |
| TC-WV-007 | API 响应时间 < 500ms | 满足性能要求 | P0 |
| TC-WV-008 | 数据一致性（误差<0.1%） | 与 CLI 输出一致 | P0 |
| TC-WV-009 | Token 认证 | 未授权访问被拒 | P0 |
| TC-WV-010 | 向后兼容 | 不影响 CLI/飞书 | P0 |

### 6.11 WebUI 管理控制台模块（v0.29）

| 用例 ID | 测试场景 | 预期结果 | 优先级 |
|---------|---------|---------|--------|
| TC-WM-001 | 训练计划日历视图 | 正确渲染训练日 | P0 |
| TC-WM-002 | 训练计划列表视图 | 正确展示计划列表 | P0 |
| TC-WM-003 | 计划执行进度 | 完成率/忠实度正确 | P0 |
| TC-WM-004 | 进化状态面板 | 4 条触发条件正确 | P0 |
| TC-WM-005 | 计划调整-AI 模式 | 跳转 nanobot-ai WebUI | P1 |
| TC-WM-006 | 计划调整-手工模式 | 编辑保存成功 | P1 |
| TC-WM-007 | 提示参数调优 | 4 维滑块正确 | P1 |
| TC-WM-008 | 月度进化报告 | 报告列表+详情正确 | P1 |
| TC-WM-009 | 设置中心 | 个人资料/偏好/连接/系统 | P2 |
| TC-WM-010 | 日历渲染性能（100 日 < 500ms） | 满足性能要求 | P1 |

### 6.12 v0.31.0 重构变更专项

| 用例 ID | 测试场景 | 预期结果 | 优先级 |
|---------|---------|---------|--------|
| TC-RF-001 | Grep 搜索 llm_timeout 引用 | 零匹配 | P0 |
| TC-RF-002 | Grep 搜索 CLIStreamingManager 引用 | 零匹配 | P0 |
| TC-RF-003 | Grep 搜索 sync_custom_templates 引用 | 零匹配 | P0 |
| TC-RF-004 | `nanobotrun export sessions` 直接调用 ExportEngine | 导出成功 | P0 |
| TC-RF-005 | `nanobotrun predict vdot` 直接调用 PredictionEngine | 预测成功 | P0 |
| TC-RF-006 | `nanobotrun status today` 直接调用 BodySignalEngine | 状态查询成功 | P0 |
| TC-RF-007 | create_server() 从 app.py 导入 | 正常返回 uvicorn.Server | P0 |
| TC-RF-008 | AppConfig.to_dict() 包含 Enum 字段 | Enum 正确序列化 | P0 |
| TC-RF-009 | shap 缺失时 VDOT 预测降级 | 使用 sklearn feature_importances_ | P0 |
| TC-RF-010 | dulwich 缺失时 Git 初始化降级 | 跳过 Git 操作，不阻塞 | P0 |
| TC-RF-011 | questionary 缺失时交互降级 | 使用默认配置，不阻塞 | P1 |
| TC-RF-012 | numba 缺失验证 | 纯 Python 执行正常 | P1 |
| TC-RF-013 | pydantic-settings 缺失验证 | dataclass 配置正常 | P1 |

### 6.13 非功能性测试

| 用例 ID | 测试场景 | 预期结果 | 优先级 |
|---------|---------|---------|--------|
| TC-NF-001 | 单元测试耗时 | < 30s | P0 |
| TC-NF-002 | 集成测试耗时 | < 60s | P0 |
| TC-NF-003 | E2E 测试耗时 | < 300s | P0 |
| TC-NF-004 | 查询性能 | < 1s | P0 |
| TC-NF-005 | 报告生成性能 | < 5s | P1 |
| TC-NF-006 | Hook 接入延迟 | < 100ms | P0 |
| TC-NF-007 | ML 推理延迟 | < 100ms | P0 |
| TC-NF-008 | 预测响应时间 | < 5s | P0 |
| TC-NF-009 | 内存占用无泄漏 | 长时间运行稳定 | P1 |
| TC-NF-010 | 本地存储零外联 | 所有数据本地存储 | P0 |

---

## 7. 缺陷等级定义与管理流程

### 7.1 缺陷等级

| 等级 | 定义 | 修复时限 | 示例 |
|------|------|---------|------|
| **P0 - 阻塞** | 核心功能不可用，无绕过方案 | 立即修复 | 数据导入失败、CLI 命令全部失败、预测引擎崩溃 |
| **P1 - 严重** | 核心功能受损，但有绕过方案 | 24h 内 | 某 Engine 调用失败但其他可用、WebUI 页面加载失败 |
| **P2 - 一般** | 非核心功能异常 | 版本发布前 | 降级路径未触发预期日志、格式化错误 |
| **P3 - 建议** | 代码质量/可维护性问题 | 下个版本 | 命名不规范、注释缺失、性能优化建议 |

### 7.2 缺陷管理流程

```
发现 → 记录（Bug 模板） → 分级（P0-P3） → 分配 → 修复 → 验证 → 关闭
                                    ↓
                              修复时限监控
```

### 7.3 Bug 提交模板

参考 `docs/test/test_templates/Bug提交模板.md`：

```markdown
## Bug 标题
- **Bug ID**: BUG-XXX
- **等级**: P0/P1/P2/P3
- **模块**: xxx
- **发现阶段**: 单元/集成/E2E/验收
- **复现步骤**:
  1. ...
  2. ...
- **预期结果**: ...
- **实际结果**: ...
- **环境**: Windows 10, Python 3.11, v0.31.0
- **附件**: 日志/截图
```

### 7.4 缺陷统计要求

| 统计项 | 要求 |
|--------|------|
| 缺陷总数 | 记录所有发现的缺陷 |
| P0/P1 修复率 | 100%（发布前） |
| 缺陷密度 | 每千行代码缺陷数 |
| 缺陷趋势 | 按日统计新增/修复/关闭 |
| 回归缺陷 | 修复后重新打开的缺陷数 |

---

## 8. 测试执行计划与进度安排

### 8.1 阶段划分

| 阶段 | 内容 | 准入条件 | 准出条件 | 预估耗时 |
|------|------|---------|---------|---------|
| **T0: 准入验证** | ruff/mypy/格式检查 | 代码提交完成 | 全部通过 | 0.5h |
| **T1: 单元测试** | 全量单元测试 + 覆盖率 | T0 通过 | 通过率 100%，覆盖率达标 | 2h |
| **T2: 集成测试** | 模块间交互测试 | T1 通过 | 通过率 100% | 1h |
| **T3: E2E 测试** | 端到端流程测试 | T2 通过 | 通过率 ≥ 98% | 3h |
| **T4: 性能测试** | 性能基线对比 | T3 通过 | 无性能回归 | 1h |
| **T5: 降级测试** | 依赖移除降级验证 | T4 通过 | 全部通过 | 1h |
| **T6: 验收测试** | UAT 用例验证 | T5 通过 | P0 用例 100% 通过 | 2h |
| **T7: 评审发布** | 质量指标评审 | T6 通过 | 所有指标达标 | 0.5h |

### 8.2 执行顺序

```
T0 准入验证
    ↓
T1 单元测试（全量）→ 修复失败用例 → 确认覆盖率
    ↓
T2 集成测试 → 修复失败用例
    ↓
T3 E2E 测试 → 修复失败用例
    ↓
T4 性能测试 → 对比 v0.30.0 基线
    ↓
T5 降级测试（最小依赖环境）→ 验证降级路径
    ↓
T6 验收测试（UAT 用例）→ 用户场景验证
    ↓
T7 评审发布 → 生成测试报告 → 发布决策
```

### 8.3 测试执行命令

```bash
# T0: 准入验证
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/ --ignore-missing-imports

# T1: 单元测试 + 覆盖率
uv run pytest tests/unit/ -v --cov=src --cov-report=term-missing

# T2: 集成测试
uv run pytest tests/integration/ -v

# T3: E2E 测试
uv run pytest tests/e2e/ -v --tb=short

# T4: 性能测试
uv run pytest tests/performance/ -v

# T5: 降级测试（需先创建最小依赖环境）
uv run --isolated pytest tests/unit/core/prediction/ -k "shap or dulwich or questionary"

# T6: 验收测试（参考 UAT 用例手动执行）
# 参考 docs/test/uat_test_cases/ 下的用例

# 全量测试（一键执行）
uv run pytest tests/ -v --tb=short
```

### 8.4 里程碑与交付物

| 里程碑 | 交付物 | 负责人 |
|--------|--------|--------|
| T1 完成 | 单元测试报告 + 覆盖率报告 | AI Agent |
| T3 完成 | E2E 测试报告 | AI Agent |
| T5 完成 | 降级测试报告 | AI Agent |
| T7 完成 | 测试报告_v0.31.0.md + 回归报告_v0.31.0.md | AI Agent |

---

## 9. 质量评估指标与通过标准

### 9.1 量化指标

| 指标 | 目标值 | v0.30.0 基线 | 测量方式 |
|------|--------|------------|---------|
| 单元测试通过率 | 100% | 100% (4226) | pytest |
| 集成测试通过率 | 100% | 100% (25) | pytest |
| E2E 测试通过率 | ≥ 98% | 100% (418) | pytest |
| 性能测试通过率 | 100% | 100% | pytest |
| core 覆盖率 | ≥ 80% | 84% | pytest-cov |
| agents 覆盖率 | ≥ 70% | — | pytest-cov |
| cli 覆盖率 | ≥ 60% | — | pytest-cov |
| 总覆盖率 | ≥ 83% | 83% | pytest-cov |
| ruff check | 0 error | 0 error | ruff |
| mypy | 0 error | 0 error | mypy |
| P0 Bug 数 | 0 | 0 | Bug 跟踪 |
| P1 Bug 数 | 0 | 0 | Bug 跟踪 |
| 单元测试耗时 | < 30s | 15.23s | pytest |
| 集成测试耗时 | < 60s | 23.18s | pytest |
| E2E 测试耗时 | < 300s | 144.04s | pytest |
| 代码净减少 | ~2000 行 | — | wc -l 对比 |
| 依赖净减少 | 5 个 | — | pyproject.toml 对比 |

### 9.2 通过标准（发布门禁）

**必须全部满足**方可发布：

- [ ] **ENTRY-01~06**: 准入条件全部满足
- [ ] **EXIT-01**: 单元测试通过率 100%
- [ ] **EXIT-02**: 集成测试通过率 100%
- [ ] **EXIT-03**: E2E 测试通过率 ≥ 98%
- [ ] **EXIT-04**: 性能测试通过率 100%
- [ ] **EXIT-05~08**: 覆盖率达标（core≥80%, agents≥70%, cli≥60%, 总≥83%）
- [ ] **EXIT-09~10**: P0/P1 Bug 数为 0
- [ ] **EXIT-11**: 性能无回归（退化 < 20%）
- [ ] **EXIT-12**: 降级路径验证通过
- [ ] **EXIT-13**: 死代码零残留

### 9.3 质量评估维度

| 维度 | 评估项 | 标准 |
|------|--------|------|
| **功能完整性** | 全模块功能回归 | 所有 P0 用例通过 |
| **代码质量** | 规范/类型/格式 | ruff/mypy 零错误 |
| **测试覆盖** | 覆盖率达标 | 分层门禁达标 |
| **性能稳定** | 无性能回归 | 退化 < 20% |
| **兼容性** | 降级路径有效 | 依赖缺失时优雅降级 |
| **安全性** | 认证机制有效 | WebUI token 认证默认启用 |
| **可维护性** | 死代码清理 | 零残留引用 |

---

## 10. 测试资源分配

### 10.1 人力分配

| 角色 | 职责 | 预估投入 |
|------|------|---------|
| 测试负责人 | 测试计划、用例设计、报告生成 | 0.5 人日 |
| 开发工程师 | Bug 修复、测试辅助 | 0.5 人日 |
| AI Agent | 自动化测试执行、覆盖率分析、降级测试 | 持续 |

### 10.2 工具链

| 工具 | 用途 | 版本 |
|------|------|------|
| pytest | 测试执行框架 | ≥7.0.0 |
| pytest-cov | 覆盖率统计 | ≥4.0.0 |
| pytest-mock | Mock 外部依赖 | ≥3.0.0 |
| pytest-timeout | 超时控制 | ≥2.2.0 |
| pytest-asyncio | 异步测试支持 | ≥0.23.0 |
| httpx | HTTP 客户端测试 | ≥0.27.0 |
| ruff | 代码规范检查 | Latest |
| mypy | 类型检查 | Latest |
| uv | 包管理 | Latest |

### 10.3 测试数据

| 数据类型 | 来源 | 说明 |
|---------|------|------|
| FIT 测试文件 | `tests/fixtures/` | 预置测试数据 |
| 测试数据生成 | `tests/scripts/generate_test_data.py` | 自动生成 |
| Parquet 测试数据 | 测试环境生成 | 隔离环境 |

---

## 11. 风险评估与应对措施

### 11.1 风险清单

| 风险 ID | 风险描述 | 概率 | 影响 | 风险等级 | 应对措施 |
|---------|---------|------|------|---------|---------|
| RISK-01 | 依赖移除导致隐性功能丢失 | 低 | 高 | 中 | 准备最小依赖环境，逐一验证降级路径 |
| RISK-02 | Handler 删除后 CLI 参数传递异常 | 中 | 中 | 中 | 针对每个 CLI 命令编写直接调用 Engine 的测试 |
| RISK-03 | asdict() Enum 序列化不兼容 | 中 | 中 | 中 | 编写 Enum 字段专项测试，必要时自定义 encoder |
| RISK-04 | 测试覆盖率下降 | 低 | 中 | 低 | 监控覆盖率报告，新增代码必须配套测试 |
| RISK-05 | 性能回归 | 低 | 低 | 低 | 对比 v0.30.0 性能基线，设置告警阈值 |
| RISK-06 | WebUI 启动失败（server.py 内联） | 低 | 中 | 低 | 验证 create_server() 导入路径和功能完整性 |
| RISK-07 | 进化引擎数据迁移问题 | 低 | 高 | 中 | 验证 Parquet 按月分片读写正确性 |
| RISK-08 | 飞书通知通道异常 | 低 | 中 | 低 | Mock 飞书 API 进行集成测试 |
| RISK-09 | 大数据量查询性能退化 | 低 | 中 | 低 | 性能测试覆盖大数据量场景 |
| RISK-10 | 测试环境不一致导致误报 | 中 | 低 | 低 | 统一环境隔离策略，使用 NANOBOT_CONFIG_DIR |

### 11.2 应急预案

| 场景 | 应急措施 |
|------|---------|
| 降级路径失效 | 临时恢复依赖，记录为 P2 Bug 后续修复 |
| CLI 调用失败 | 回滚 Handler 删除，重新评估内联方案 |
| 覆盖率不达标 | 补充针对性测试用例，优先覆盖核心路径 |
| 性能严重回归 | 回滚相关变更，定位性能瓶颈 |
| WebUI 启动失败 | 检查 server.py 内联代码，恢复独立文件 |
| P0 Bug 阻塞 | 立即修复，阻塞发布直到修复验证通过 |

### 11.3 风险监控

| 监控项 | 频率 | 预警阈值 | 升级条件 |
|--------|------|---------|---------|
| 测试通过率 | 每次执行 | < 100% | P0 用例失败 |
| 覆盖率 | 每次执行 | < 80% | core 覆盖率 < 80% |
| 性能指标 | 每次执行 | 退化 > 20% | 核心命令退化 > 20% |
| Bug 数 | 每日 | P0 > 0 | P0 Bug 未在 24h 内修复 |

---

## 12. 交付物清单

| 交付物 | 路径 | 说明 |
|--------|------|------|
| 测试策略文档 | `docs/test/strategy_v0.31.0.md` | 本文档 |
| 测试执行报告 | `docs/test/reports/测试报告_v0.31.0.md` | 测试执行结果 |
| 回归测试报告 | `docs/test/reports/回归报告_v0.31.0.md` | 回归验证结果 |
| 覆盖率报告 | pytest-cov 输出 | 各模块覆盖率 |
| Bug 列表 | Bug 跟踪系统 | 缺陷记录 |
| 降级测试报告 | `docs/test/reports/降级测试报告_v0.31.0.md` | 降级路径验证 |

---

## 13. 附录

### 13.1 相关文档

| 文档 | 路径 | 说明 |
|------|------|------|
| 需求规格说明书 | `docs/requirements/REQ_需求规格说明书.md` | 功能需求 |
| 架构设计说明书 | `docs/architecture/架构设计说明书.md` | 系统架构 |
| ponytail 修复与重构报告 | `docs/development/ponytail修复与重构报告_v0.31.0.md` | v0.31.0 变更 |
| ponytail 审查复审报告 | `docs/review/ponytail-audit-review_v0.30.0.md` | 审查依据 |
| 测试报告 v0.30.0 | `docs/test/reports/测试报告_v0.30.0.md` | 基线数据 |
| 回归报告 v0.30.0 | `docs/test/reports/回归报告_v0.30.0.md` | 基线数据 |
| UAT 测试指南 | `docs/test/用户验收测试指南.md` | 验收测试参考 |
| UAT 测试用例 | `docs/test/uat_test_cases/` | 100 个 UAT 用例 |
| 测试命令参考 | `docs/test/test_templates/测试命令参考.md` | 命令速查 |
| 质量规则 | `.trae/rules/quality-rules.md` | 质量标准 |

### 13.2 测试命令速查

```bash
# === 准入验证 ===
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/ --ignore-missing-imports

# === 单元测试 ===
uv run pytest tests/unit/ -v --cov=src --cov-report=term-missing

# === 集成测试 ===
uv run pytest tests/integration/ -v

# === E2E 测试 ===
uv run pytest tests/e2e/ -v --tb=short

# === 性能测试 ===
uv run pytest tests/performance/ -v

# === 全量测试 ===
uv run pytest tests/ -v --tb=short

# === 按模块执行 ===
uv run pytest tests/unit/core/ -v           # 核心模块
uv run pytest tests/unit/core/prediction/ -v  # 预测模块
uv run pytest tests/unit/core/evolution/ -v    # 进化模块
uv run pytest tests/unit/core/twin/ -v        # 孪生模块
uv run pytest tests/integration/scene/ -v     # 场景测试

# === 降级测试（需先创建最小依赖环境）===
uv run --isolated pytest tests/unit/core/prediction/ -k "shap or dulwich or questionary"

# === 死代码残留验证 ===
# 使用 Grep 工具搜索以下关键词，预期零匹配：
# llm_timeout, CLIStreamingManager, sync_custom_templates

# === 覆盖率报告 ===
uv run pytest tests/ --cov=src --cov-report=html
```

### 13.3 环境变量配置

```powershell
# 测试环境隔离
$env:NANOBOT_CONFIG_DIR = ".nanobot-runner-test"
$env:NANOBOT_DATA_DIR = ".nanobot-runner-test\data"

# WebSocket 配置（WebUI 测试）
$env:NANOBOT_WS_ENABLED = "true"
$env:NANOBOT_WS_HOST = "127.0.0.1"
$env:NANOBOT_WS_PORT = "8765"
```

---

## 14. 版本历史

| 版本 | 日期 | 变更内容 |
|------|------|---------|
| v1.0 | 2026-06-23 | 初始版本，全方位回归测试策略 |

---

**制定人**: AI Agent  
**制定日期**: 2026-06-23  
**版本**: v1.0  
**状态**: 待评审
