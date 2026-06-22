# Ponytail-Audit 全局过度工程审计报告

> **项目**: nanobot-runner v0.30.0
> **审计日期**: 2026-06-22
> **审计范围**: `src/`、`tests/`、`scripts/`、`pyproject.toml`
> **审计方法**: 全量源码扫描，按 ponytail-review 标签分类

---

## 总览

| 标签 | 数量 | 说明 |
|------|------|------|
| `delete` | 18 | 死代码/未使用/投机抽象 |
| `stdlib` | 4 | 手写标准库已有之物 |
| `native` | 3 | 依赖/代码做了平台/框架已做的事 |
| `yagni` | 28 | 单实现接口/薄包装/多余间接层 |
| `shrink` | 19 | 相同逻辑可更少行数实现 |
| **合计** | **72** | |

**预估净削减: ~5000 行代码, ~7 个依赖可移除/替换**

---

## 一、delete — 死代码/未使用/投机抽象

### 1.1 核心模块死代码

| # | 发现 | 替代 | 路径 |
|---|------|------|------|
| 1 | DecisionLogger 是 EvolutionStore 的纯委托包装，所有方法直接转发到 store | 调用方直接使用 EvolutionStore | `src/core/evolution/decision_logger.py` |
| 2 | AppContextFactory.create_for_testing() 与 create() 实现完全相同 | 统一使用 create() | `src/core/base/context.py` |
| 3 | AIStatusDashboard._calculate_evolution_level 与 TrainingInsightReport._calculate_level 逻辑完全重复 | 提取为共享函数 | `src/core/transparency/ai_status_dashboard.py`, `src/core/transparency/training_insight_report.py` |
| 4 | diagnosis/models.py 与 validate/models.py 概念重叠（DiagnosisSeverity vs ErrorLevel, ValidationResult vs ValidationError） | 合并为单一验证模型 | `src/core/diagnosis/models.py`, `src/core/validate/models.py` |
| 5 | SelfDiagnosis._default_parameter_rules 和 _default_execution_rules 返回恒真规则 | 删除空规则集 | `src/core/diagnosis/self_diagnosis.py` |
| 6 | PlanAdjustmentValidator._check_race_taper 恒返回 True，无实际校验逻辑 | 删除此规则 | `src/core/plan/plan_adjustment_validator.py` |
| 7 | ask_user_confirm.py 底部 4 个便捷函数每次都 new 一个 Manager | 删除便捷函数 | `src/core/plan/ask_user_confirm.py` |
| 8 | tools/models.py 中的 ToolResult 与 base/result.py 中的 ToolResult 功能重叠 | 统一使用 base/result.py | `src/core/tools/models.py` |
| 9 | init/models.py 中的 ValidationResult 与 validate/models.py 中的 ValidationResult 概念重叠 | 复用 validate/models.py | `src/core/init/models.py` |
| 10 | WeatherService 是 Mock 实现，永远返回相同数据，check_extreme_weather 阈值与实际数据脱节 | 待接入真实 API 时再实现 | `src/core/plan/notify_tool.py` |
| 11 | llm_timeout.py 整个文件（267 行）无任何外部引用 | 删除整个文件 | `src/core/llm_timeout.py` |
| 12 | FeishuCalendarSync.check_conflicts 方法体中 events 列表始终为空，整个方法不会返回任何冲突 | 删除死代码 | `src/notify/feishu_calendar.py:718-766` |
| 13 | FeishuBot.test_connection = verify_connection 向后兼容别名，无外部引用 | 删除别名 | `src/notify/feishu.py:608` |
| 14 | MyToolIntegration 类在 src/ 中无任何外部调用者 | 删除死代码模块 | `src/core/diagnosis/mytool_integration.py` |

### 1.2 CLI 模块死代码

| # | 发现 | 替代 | 路径 |
|---|------|------|------|
| 15 | CLIStreamingManager 类及 stream_agent_response 函数，项目中零导入 | agent chat 用 console.status() | `src/cli/streaming.py` |
| 16 | sync_custom_templates 函数，项目中零导入 | gateway 用 nanobot 自带 sync_workspace_templates | `src/cli/utils.py` |
| 17 | DataHandler._filter_lazy_by_date_range 方法，从未被调用 | 删除死方法 | `src/cli/handlers/data_handler.py:118-146` |
| 18 | handlers/__init__.py 的 __all__ 只导出 2/9 个 handler | 删除无意义的集中导出 | `src/cli/handlers/__init__.py` |

---

## 二、stdlib — 手写标准库已有之物

| # | 发现 | 替代 | 路径 |
|---|------|------|------|
| 19 | 全项目 50+ 个 frozen dataclass 手写 to_dict() 方法，逐字段构造 dict | `dataclasses.asdict()`（Enum 需后处理） | `src/core/evolution/models.py`, `src/core/transparency/models.py`, `src/core/prediction/models.py`, `src/core/twin/models.py`, `src/core/diagnosis/models.py`, `src/core/personality/models.py`, `src/core/memory/models.py`, `src/core/config/schema.py` 等 |
| 20 | AppConfig.to_dict() 手写逐字段映射 | `dataclasses.asdict()` | `src/core/config/schema.py` |
| 21 | AppConfig.FIELD_TYPES 手写类型映射字典 | `dataclasses.fields()` 反射获取 | `src/core/config/schema.py` |
| 22 | AppConfig._is_valid_version 用 re.match 校验版本号格式 | `from packaging.version import Version` | `src/core/config/schema.py` |

---

## 三、native — 依赖/代码做了平台/框架已做的事

| # | 发现 | 替代 | 路径 |
|---|------|------|------|
| 23 | AppConfig.validate() 手写必填字段+类型校验 | pydantic BaseModel（项目已通过 fastapi 间接引入 pydantic） | `src/core/config/schema.py` |
| 24 | ChannelManager 手写 dict 包装+add/remove/get/enable/disable 方法 | FastAPI 依赖注入+Pydantic model | `src/core/config/channels.py` |
| 25 | CLIError 的 path_not_found/import_failed/config_missing 等方法 | Typer 原生 `typer.BadParameter` | `src/cli/common.py:15-54` |

---

## 四、yagni — 单实现接口/薄包装/多余间接层

### 4.1 核心模块

| # | 发现 | 替代 | 路径 |
|---|------|------|------|
| 26 | EvolutionEngine 是纯委托层，所有方法转发到子组件 | 调用方直接使用子组件 | `src/core/evolution/evolution_engine.py` |
| 27 | EvolutionController 中 5 个 Protocol 类仅用于类型标注 | TYPE_CHECKING + 直接导入 | `src/core/evolution/evolution_controller.py` |
| 28 | ExportEngine 的 DataExporter Protocol 只有 3 个内部实现且硬编码注册 | 删除 Protocol，直接调用具体 exporter | `src/core/export/engine.py` |
| 29 | PredictionEngine 是薄缓存+委托层，每个 predict_xxx 只做缓存检查+调用子组件 | 缓存逻辑移入各 predictor 内部 | `src/core/prediction/prediction_engine.py` |
| 30 | PromptTemplateEngine 只有 2 个硬编码模板，add_template/remove_template 从未被调用 | 字符串常量 + str.format() | `src/core/plan/prompt_template_engine.py` |
| 31 | ChannelManager 支持多通道但实际只使用 Feishu，EmailChannelConfig 和 WebhookChannelConfig 无真实实现 | 删除未使用的通道配置类 | `src/core/config/channels.py` |
| 32 | FeedbackLoop 是 PreferenceLearner 的薄包装 | 合并到 PreferenceLearner | `src/core/personality/feedback_loop.py` |
| 33 | PlanExecutionRepository.validate_execution_feedback 与 PlanManager._validate_record_params 验证逻辑重复 | 由 PlanManager 统一负责 | `src/core/plan/plan_execution_repository.py` |
| 34 | PredictionEvaluator 独立类，evaluate_prediction_accuracy 只是 abs/relative 计算 | 合并为模块级函数 | `src/core/plan/goal_prediction_engine.py` |
| 35 | ProviderAdapter Protocol 仅有 RunnerProviderAdapter 一个实现 | 删除 Protocol，直接用 RunnerProviderAdapter | `src/core/provider_adapter.py:81-123` |
| 36 | AgentDefaults dataclass 仅在 RunnerProviderAdapter.get_agent_defaults() 中构造 | 直接返回 dict 或内联构造 | `src/core/provider_adapter.py:60-78` |
| 37 | UserProfileManager 仅是 ProfileStorageManager 的薄包装 | 4 个调用方直接用 ProfileStorageManager | `src/core/user_profile_manager.py:37-133` |
| 38 | TrainingPlanEngine 与 src/core/plan/ 模块功能重叠 | 迁移引用后删除此文件 | `src/core/training_plan.py` |
| 39 | analytics.py 中 7 个 `_` 前缀委托方法转发到子模块 | 外部直接 import 子模块函数 | `src/core/analytics.py:586-1004` |
| 40 | analytics.py 的 `__all__` re-exports 了子模块全部公开函数 | 删除多余中间层 | `src/core/analytics.py:1289-1314` |
| 41 | VerifyManager 的 generate_report 只是组合调用 verify_files + verify_config | 删除不必要的包装层 | `src/core/verify_manager.py` |
| 42 | HealthCheckResponse 和 TokenResponse 两个 TypedDict 仅在 app.py 内部用作单次返回类型注解 | `dict[str, str]` | `src/core/webui/app.py:27-38` |
| 43 | get_app() 全局访问器仅在 auth.py 内部使用 | 通过 FastAPI Request 依赖注入获取 app.state | `src/core/webui/app.py:42-51` |
| 44 | server.py 整个文件仅 52 行，只做 create_app() + uvicorn.Config + uvicorn.Server | 内联到 app.py 的一个函数 | `src/core/webui/server.py` |
| 45 | FeishuAuth + FeishuMessageAPI + FeishuBot 三层类可合并 | 合并为 FeishuBot 一个类 | `src/notify/feishu.py:20-278` |
| 46 | FeishuCalendarAPI._get_access_token 与 FeishuAuth._get_access_token 完全重复 | 复用 FeishuAuth | `src/notify/feishu_calendar.py:74-115` |
| 47 | FeishuCalendarAPI._request 与 FeishuMessageAPI._request 逻辑完全重复 | 复用而非复制 | `src/notify/feishu_calendar.py:125-169` |
| 48 | CalendarSyncConfig 中 app_id/app_secret 与 FeishuAuth 职责重叠 | 直接复用 FeishuAuth | `src/notify/feishu_calendar.py:21-31` |
| 49 | SyncResult 和 CalendarEventCreateRequest 过度拆分 | 用项目已有的 OperationResult 和 dict | `src/notify/feishu_calendar.py:33-52` |

### 4.2 CLI Handler 层

| # | 发现 | 替代 | 路径 |
|---|------|------|------|
| 50 | ExportHandler 两个方法各一行纯转发 | command 直接调 context.export_engine | `src/cli/handlers/export_handler.py` |
| 51 | PredictionHandler 7 个方法全是三行模板 | command 直接调 context.prediction_engine | `src/cli/handlers/prediction_handler.py` |
| 52 | StatusHandler 两个方法各两行纯转发 | command 直接调 context.body_signal_engine | `src/cli/handlers/status_handler.py` |
| 53 | TwinHandler 5 个方法全是三行模板 | command 直接调 context.twin_engine | `src/cli/handlers/twin_handler.py` |
| 54 | ModelHandler 唯一方法逻辑 5 行可写在 command 里 | 内联到 command | `src/cli/handlers/model_handler.py` |
| 55 | EvolutionHandler 10 个方法中 6 个纯转发，2 个日期/枚举转换该在 core 层，2 个 JSON 包装该在 command 层 | Handler 层没有自己的职责 | `src/cli/handlers/evolution_handler.py` |
| 56 | AnalysisHandler 7 个方法中部分绕过自身 engine 调 RunnerTools，其余纯转发 | Handler 层没有自己的职责 | `src/cli/handlers/analysis_handler.py` |
| 57 | **整个 Handler 层**: 9 个 handler 文件，7 个是纯转发无附加逻辑 | 仅保留 DataHandler（进度条/目录遍历）和 VizHandler（降级渲染），其余删除 | `src/cli/handlers/` |

---

## 五、shrink — 相同逻辑可更少行数实现

### 5.1 核心模块

| # | 发现 | 替代 | 路径 |
|---|------|------|------|
| 58 | 7 个异常类结构完全相同，仅 error_code 和 recovery_suggestion 默认值不同 | 合并为 NanobotRunnerError(error_code=..., recovery_suggestion=...) | `src/core/base/exceptions.py` |
| 59 | PlanManager 的 activate_plan/pause_plan/complete_plan/cancel_plan 四个方法结构完全相同 | 提取 _transition_plan(plan_id, target_status, timestamp_field) | `src/core/plan/plan_manager.py` |
| 60 | HardValidator 的 6 个 _validate_xxx 方法结构完全相同 | 提取 _validate_rule(plan, check_fn, rule_id, rule_name, limit_value, msg_template) | `src/core/plan/hard_validator.py` |
| 61 | tool_handler 和 handle_errors 装饰器功能高度重叠 | 合并为单一装饰器 | `src/core/base/decorators.py` |
| 62 | ExportEngine.export_sessions/export_summary 大量重复验证和错误处理 | 提取 _validate_and_export(export_type, ...) | `src/core/export/engine.py` |
| 63 | ProfileStorageManager.sync_dual_storage 的 3 个方向实现重复 | 提取 _sync_direction(source, target) | `src/core/base/profile_storage.py` |
| 64 | PreferenceLearner._category_to_field 映射在两处重复定义 | 提取为类常量 | `src/core/personality/preference_learner.py` |
| 65 | GoalPredictionEngine._calculate_achievement_probability 和 estimate_weeks_to_achieve 中 effective_improvement 计算逻辑几乎相同 | 提取 _compute_effective_improvement() | `src/core/plan/goal_prediction_engine.py` |
| 66 | SmartAdviceEngine 的 4 个 _generate_xxx_advice 方法结构相同 | 提取 _add_advice(advices, type, content, priority, ...) | `src/core/plan/smart_advice_engine.py` |
| 67 | PlanAnalyzer 的 4 个 _generate_xxx_suggestions 方法都是遍历 issues 做关键词匹配 | 提取 _match_suggestions(issues, pattern_map) | `src/core/plan/plan_analyzer.py` |
| 68 | provider_adapter.py 的 _parse_env_file 手写 .env 解析器 | 复用项目已有的 EnvManager | `src/core/provider_adapter.py:629-655` |

### 5.2 CLI 模块

| # | 发现 | 替代 | 路径 |
|---|------|------|------|
| 69 | status.py 的 today() 和 weekly() 几乎完全相同（复制粘贴） | 合并为一个带 --period 参数的命令 | `src/cli/commands/status.py` |
| 70 | report.py 的训练负荷表格渲染逻辑在 3 个函数中重复 | 提取 _render_load_table(load_data) | `src/cli/commands/report.py` |
| 71 | report.py 的 _display_weekly_report 和 _display_monthly_report 几乎完全相同 | 合并为 _display_period_report(data, period_label) | `src/cli/commands/report.py:411-591` |
| 72 | gateway.py 的 5 个 _format_xxx 函数与 formatter.py 和 common.py 功能重复 | 复用 formatter.py 的 format_distance/format_duration/format_pace | `src/cli/commands/gateway.py:62-168` |
| 73 | formatter.py 的 _format_duration 和 _format_pace 仅对核心函数加 try/except | 在调用处做异常处理，或让核心函数本身容错 | `src/cli/formatter.py:155-173` |
| 74 | print_status 函数用 colors 字典映射 | Rich 的 console.print(f"[green]{msg}[/green]") 一行即可 | `src/cli/common.py:77-91` |

### 5.3 WebUI 模块

| # | 发现 | 替代 | 路径 |
|---|------|------|------|
| 75 | routes/body_signal.py 的 3 个同步包装函数各只调用一行 | 直接在 async handler 内 run_in_threadpool(lambda: ...) | `src/core/webui/routes/body_signal.py:21-51` |
| 76 | routes/dashboard.py 的 _get_dashboard_data 仅两行调用 | 直接内联 | `src/core/webui/routes/dashboard.py:21-36` |
| 77 | routes/training_load.py 的两个函数各仅一行委托 | 直接内联 | `src/core/webui/routes/training_load.py:18-35` |
| 78 | routes/vdot.py 的 _get_vdot_trend 仅 3 行有效逻辑 | 直接内联 | `src/core/webui/routes/vdot.py:18-30` |
| 79 | routes/settings.py 的 3 个同步包装函数逻辑简单 | 直接内联 | `src/core/webui/routes/settings.py:34-93` |
| 80 | auth.py 的 app is None 和 secret is empty 两个 500 错误分支在生产中不可能触发 | 删除防御性过度代码 | `src/core/webui/auth.py:71-82` |

---

## 六、依赖审计

### 6.1 可删除的依赖

| 依赖 | 原因 | 影响 |
|------|------|------|
| **numba** | 完全未使用，零 import | 减少约 100MB+ 安装体积 |
| **pydantic-settings** | 完全未使用，零 import | 减少约 5MB 安装体积 |
| **psutil** | 仅在 2 个 e2e 测试中用做内存监控，非生产代码依赖 | 移至 test 依赖 |

### 6.2 可替换的依赖

| 依赖 | 替代方案 | 影响 |
|------|---------|------|
| **shap** | 仅 1 处使用且已自带降级逻辑，移除后降级路径自动生效 | 减少约 50MB+ 安装体积 |
| **dulwich** | 仅 1 处使用（init Git 仓库），可用 `subprocess.run(["git", "init"])` 一行替代 | 减少约 10MB 安装体积 |
| **questionary** | 仅 1 处使用（init 向导），可用 typer 自带 prompt/confirm 替代 | 减少约 3MB 安装体积 |
| **pyyaml** | 仅 1 处使用（skill_manager），可用 tomllib/json 替代 | 减少约 2MB 安装体积 |

---

## 七、测试结构审计

### 7.1 可合并的测试文件

| 发现 | 路径 |
|------|------|
| test_health_agent_tool.py 和 test_health_agent_tool_integration.py 高度重叠 | `tests/integration/module/` |
| test_plan_cli_integration.py + _bug001.py + _v0110.py 测试同一 CLI 命令组 | `tests/integration/module/` |
| test_migration_flow.py 和 test_migrate_flow.py 测试同一迁移流程 | `tests/integration/module/` |
| tests/e2e/test_performance.py 与 tests/performance/ 功能重叠 | `tests/e2e/`, `tests/performance/` |
| tests/integration/scene/ 与 module/ 边界模糊，同一功能分散在两处 | `tests/integration/` |
| tests/unit/core/prediction/ 中 6 对 test_X.py + test_X_extended.py | `tests/unit/core/prediction/` |
| tests/unit/core/plan/ 中按版本号拆分的测试文件 | `tests/unit/core/plan/` |
| tests/unit/core/evolution/ 中扩展功能测试可合并到主测试文件 | `tests/unit/core/evolution/` |

### 7.2 可删除的空测试目录

- `tests/unit/core/migrate/`（仅 `__init__.py`）
- `tests/unit/core/models/`（仅 `__init__.py`）
- `tests/unit/core/validate/`（仅 `__init__.py`）
- `tests/unit/core/workspace/`（仅 `__init__.py`）
- `tests/unit/cli/commands/`（仅 `__init__.py`）

### 7.3 可删除的测试脚本/文件

| 发现 | 路径 |
|------|------|
| generate_test_data.py 生成伪 FIT 文件，实际 E2E 测试未引用 | `tests/scripts/generate_test_data.py` |
| run_all_tests.py 仅是 pytest 命令的 shell 包装 | `tests/scripts/run_all_tests.py` |
| test_mytool_integration.py 测试的是死代码 | `tests/unit/core/diagnosis/test_mytool_integration.py` |

---

## 八、脚本审计

| 脚本 | 判定 | 原因 |
|------|------|------|
| scripts/measure_baseline.py | **删除** | Phase C 一次性脚本，无外部调用 |
| scripts/generate_historical_predictions.py | **删除** | 与 measure_baseline.py 互引形成孤岛 |
| scripts/install.sh | **删除** | Linux/macOS 脚本，项目开发环境为 Windows，无 CI/CD 引用 |
| scripts/check_version_consistency.py | **保留** | 被 release.yml 第 60 行调用 |
| scripts/pre-commit-check.py | **审查** | 未被 git-hooks/pre-commit 调用，功能与 `uv run ruff check && uv run mypy && uv run pytest` 重复 |

---

## 九、Top 10 最大收益项（按影响排序）

| 排名 | 发现 | 预估节省 | 风险 |
|------|------|---------|------|
| 1 | 删除 llm_timeout.py | -267 行 | 零（零引用） |
| 2 | 50+ 个手写 to_dict() 改用 asdict() | ~800 行 | 低（Enum 需后处理） |
| 3 | 删除 7 个纯转发 Handler 文件 | ~600 行 | 低（command 直接调 core） |
| 4 | 删除 3 个纯委托层（DecisionLogger/EvolutionEngine/PredictionEngine） | ~600 行 | 中（需调整调用方） |
| 5 | 合并 feishu.py 三层类 + feishu_calendar.py 复用 | ~230 行 | 低 |
| 6 | 删除 UserProfileManager 薄包装 | ~100 行 | 低（4 个调用方） |
| 7 | 合并 7 个异常类为 1 个 | ~100 行 | 低 |
| 8 | 删除未使用依赖（numba/pydantic-settings/psutil/shap/dulwich/questionary/pyyaml） | ~170MB 安装体积 | 低 |
| 9 | 合并 PlanManager 4 个状态转换方法 + HardValidator 6 个验证方法 | ~180 行 | 低 |
| 10 | 内联 WebUI routes 同步包装函数 + 删除 server.py | ~120 行 | 低 |

---

**net: ~5000 lines, ~7 deps possible.**
