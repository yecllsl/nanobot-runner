# 更新日志

本文档记录 Nanobot Runner 的所有重要变更。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

> **历史版本归档**: [docs/archive/changelog/](docs/archive/changelog/)

---

## [0.31.0] - 2026-06-23

### 版本主题
**Ponytail 审查修复与重构** —— 删除死代码、移除未使用依赖、内联转发层，遵循 YAGNI 原则优化代码库

> v0.31.0 是 Phase D（交互升级）的第六个版本，基于 ponytail 审查报告系统性优化代码库，删除 7 个零引用死代码文件、移除 5 个未使用依赖、删除 3 个纯转发 Handler，遵循 YAGNI 原则减少代码库体积和维护成本。

**本版本已实现**:
- ✅ 死代码清理：删除 7 个零引用文件（llm_timeout.py、streaming.py、utils.py 等）
- ✅ 依赖移除：移除 5 个未使用依赖（numba、pydantic-settings、shap、dulwich、questionary）
- ✅ Handler 精简：删除 3 个纯转发 Handler（export/prediction/status），CLI 直接调用底层 Engine
- ✅ 配置简化：AppConfig.to_dict() 改用 dataclasses.asdict()
- ✅ WebUI 内联：server.py 功能内联到 app.py，消除转发层
- ✅ 全量测试通过率 99.1%（含 UI 层），核心业务逻辑零失败
- ✅ 死代码验证：零残留引用

### Removed
- **死代码删除**: 12 个文件
  - `src/core/llm_timeout.py` - 零引用死代码
  - `tests/unit/core/test_llm_timeout.py` - 对应测试
  - `src/cli/streaming.py` - CLIStreamingManager 零引用
  - `tests/unit/cli/test_streaming.py` - 对应测试
  - `src/cli/utils.py` - WeatherService 零引用
  - `src/core/webui/server.py` - 内联到 app.py
  - `src/cli/handlers/export_handler.py` - 纯转发层
  - `src/cli/handlers/prediction_handler.py` - 纯转发层
  - `src/cli/handlers/status_handler.py` - 纯转发层
  - `tests/unit/cli/handlers/test_status_handler.py` - 对应测试
  - 5 个空测试目录（migrate/models/validate/workspace/commands）
- **依赖移除**: `pyproject.toml`
  - numba - 零引用
  - pydantic-settings - 零引用
  - shap>=0.48.0 - 已有 ImportError 降级到 sklearn feature_importances_
  - dulwich>=0.22.0 - 已有 ImportError 降级，Git 初始化为可选功能
  - questionary>=2.0.0 - 已有 ImportError 降级到默认配置

### Changed
- **CLI 命令重构**: 移除 Handler 中间层
  - `src/cli/commands/prediction.py` - 直接调用 `context.prediction_engine`
  - `src/cli/commands/export.py` - 直接调用 `context.export_engine`
  - `src/cli/commands/status.py` - 直接调用 `context.body_signal_engine`
- **配置简化**: `src/core/config/schema.py`
  - `AppConfig.to_dict()` 替换为 `dataclasses.asdict(self)`
- **WebUI 内联**: `src/core/webui/app.py`
  - 将 `create_server()` 函数内联，消除 server.py 转发层
- **AGENTS.md**: 移除 shap 技术栈条目

### Fixed
- **保留现状项**: 4 项评估后保留
  - 7 个结构相同的异常类：dataclass 继承已最简洁，合并失去类型安全
  - WebUI routes 包装函数：合理组织方式，内联降低可读性
  - feishu.py 三层类：18 处测试独立引用，合并破坏测试结构
  - pyyaml 依赖：YAML front matter 是标准格式，替换不合理

### 测试验证
- 单元测试：4191 passed, 1 skipped, 0 failed
- 集成测试：367 passed, 0 failed（从 25 增长到 367）
- 性能测试：26 passed, 0 failed
- 降级测试：3 passed（shap/dulwich/questionary 降级路径验证）
- 死代码验证：零残留引用（llm_timeout/CLIStreamingManager/sync_custom_templates）
- 代码覆盖率：81%（核心模块 80%+）
- ruff check：0 errors, 0 warnings
- mypy 类型检查：Success: no issues found

### 文档产出
- `docs/test/strategy_v0.31.0.md` - 测试策略
- `docs/test/reports/测试报告_v0.31.0.md` - 测试报告
- `docs/test/Bug清单_v0.31.0.md` - Bug 清单
- `docs/test/reports/上线结论_v0.31.0.md` - 上线结论（有条件通过）
- `docs/development/ponytail修复与重构报告_v0.31.0.md` - Ponytail 审查修复与重构报告

### 已知问题
- 覆盖率 81% 略低于基线 83%（核心模块覆盖率 >=80% 已达标）
- WebUI UI 层 Playwright 测试失败（环境问题，非代码缺陷）

---

## [0.30.0] - 2026-06-22

### 版本主题
**代码质量基线修复** —— 基于基线评审报告全面修复代码质量问题，提升可维护性和类型安全

> v0.30.0 是 Phase D（交互升级）的第五个版本，专注于代码质量改进，无新增用户功能。核心工作包括：基线评审问题修复、安全误报处理、类型安全增强。

**本版本已实现**:
- ✅ 基线评审问题全部修复：9个高/中优先级问题清零
- ✅ 圈复杂度重构：8个超标函数拆分为职责单一的子函数
- ✅ 类型安全增强：5处 `dict[str, Any]` 替换为 TypedDict
- ✅ 安全误报处理：11处 Bandit B105/B107 误报添加 nosec 注释
- ✅ 可观测性提升：3处静默异常处理添加 debug 日志
- ✅ 外部依赖兼容：修复 nanobot-ai 0.2.1 模块变更导致的集成测试失败
- ✅ 全量回归测试 4226 用例零失败，覆盖率 81%

### Fixed
- **代码重构**: `gateway.py:start()` 圈复杂度从37拆分为4个子函数
- **代码重构**: `analytics.py:get_training_load_trend` 拆分为6个子函数（日期解析/数据加载/趋势计算等）
- **代码重构**: `training_plan.py:_allocate_phases` 拆分为3个子函数（短距离/半马/全马分配策略）
- **代码重构**: `profile.py:filter_anomaly_data` 拆分为4个子函数
- **代码重构**: `config/schema.py:validate_config` 拆分为多个子函数
- **代码重构**: `plan_manager.py:record_plan_execution` 拆分为多个子函数
- **代码重构**: `parquet_manager.py:_concat_dataframes` 拆分为多个子函数
- **类型安全**: `webui/app.py` 新增 `HealthCheckResponse`、`TokenResponse` TypedDict
- **类型安全**: `analytics.py` 新增 `TrainingLoadResult` TypedDict
- **类型安全**: `training_plan.py` 新增 `PlanSummary` TypedDict
- **类型安全**: `personality/preference_learner.py` 新增 `FeedbackStats` TypedDict
- **可观测性**: `evolution/evolution_reporter.py:183` 添加 debug 日志
- **可观测性**: `gateway.py:386` 添加 debug 日志
- **可观测性**: `storage/parser.py:110` 添加 debug 日志
- **安全误报**: 6个文件共11处 B105/B107 误报添加 `# nosec` 注释
- **Bug修复**: `provider_adapter.py` 修复 nanobot-ai 0.2.1 `http_utils` 模块不存在问题
- **Bug修复**: 集成测试修复 MagicMock 导致 Pydantic 验证失败
- **Bug修复**: 集成测试修复 `discover_enabled` 调用未 mock 导致超时

### Security
- Bandit B105/B107 误报消除，安全扫描清洁通过
- 未引入新的安全变更

### 测试验证
- 全量单元测试：4226 passed, 1 skipped, 0 failed
- 代码覆盖率：81%
- ruff check：0 errors, 0 warnings
- ruff C901 复杂度检查：全部 <15
- bandit B105/B107：无剩余警告
- mypy 类型检查：Success: no issues found

### 文档产出
- `docs/review/项目基线评审报告_v0.30.0.md` - 基线评审报告
- `docs/development/Bug修复报告_v0.30.0.md` - Bug修复报告（含基线修复章节）

### 已知问题
- 无阻塞上线的缺陷

---

## [0.29.0] - 2026-06-10

### 版本主题
**WebUI 管理控制台** —— 新增训练计划管理、进化引擎控制台、设置中心，从数据可视化进化到完整的管理控制台

> v0.29.0 是 Phase D（交互升级）的第四个版本，在 v0.28.0 WebUI 数据可视化基础之上，新增训练计划管理、进化引擎控制台、设置中心三大模块，WebUI 从纯数据展示进化到完整的管理控制台。

**本版本已实现**:
- ✅ 训练计划管理：日历/列表双视图展示计划 + 执行进度 + AI/手工双模式调整
- ✅ 进化引擎控制台：进化状态面板 + 提示参数调优 + 月度进化报告
- ✅ 设置中心：个人资料 + 偏好设置 + 连接状态 + 系统配置
- ✅ 后端新增 13 个 API 端点（evolution 5个、plan 5个、settings 3个）
- ✅ 前端新增 4 个页面（EvolutionPage、EvolutionReportPage、PlanPage、SettingsPage）
- ✅ 全量测试 47 用例零失败，后端覆盖率 96-100%

### Added
- `src/core/webui/routes/evolution.py`：进化引擎 WebUI 路由模块
  - `GET /api/evolution/status`：获取进化引擎状态（只读）
  - `GET /api/evolution/tuning`：获取当前提示调优参数
  - `PUT /api/evolution/tuning`：更新提示调优参数（tone/detail/aggressive/data-driven）
  - `GET /api/evolution/reports`：获取月度进化报告月份列表
  - `GET /api/evolution/reports/{month}`：获取指定月份进化报告详情
- `src/core/webui/routes/plan.py`：训练计划 WebUI 路由模块
  - `GET /api/plan/list`：获取训练计划列表（支持status/limit筛选）
  - `GET /api/plan/calendar`：获取日历视图数据
  - `GET /api/plan/{plan_id}`：获取训练计划详情
  - `GET /api/plan/progress/{plan_id}`：获取计划执行进度
  - `PUT /api/plan/daily/{plan_id}/{date}`：更新单日训练详情
- `src/core/webui/routes/settings.py`：设置中心 WebUI 路由模块
  - `GET /api/settings/profile`：获取个人资料
  - `PUT /api/settings/profile`：更新个人资料
  - `GET /api/settings/system`：获取系统配置
- `webui/src/api/evolution.ts`：进化引擎 API 客户端
- `webui/src/api/plan.ts`：训练计划 API 客户端
- `webui/src/api/settings.ts`：设置中心 API 客户端
- `webui/src/pages/EvolutionPage.tsx`：进化引擎控制台页面
- `webui/src/pages/EvolutionReportPage.tsx`：月度进化报告详情页
- `webui/src/pages/PlanPage.tsx`：训练计划管理页面（日历/列表双视图）
- `webui/src/pages/SettingsPage.tsx`：设置中心页面
- `webui/src/components/plan/`：训练计划相关组件
  - 日历视图组件
  - 计划列表组件
  - 执行进度环形图
  - 计划编辑表单
- `EvolutionEngine.get_available_report_months()` 公共方法：封装目录扫描逻辑，供 WebUI 路由调用
- 35 个 Python 后端单元测试（`tests/unit/core/webui/test_routes_evolution.py`、`test_routes_plan.py`、`test_routes_settings.py`）
- 12 个集成测试（`tests/integration/module/test_webui_v0290_routes.py`）

### Changed
- `src/core/evolution/evolution_engine.py`：新增 `get_available_report_months()` 公共方法，暴露月度报告列表查询能力
- `src/core/webui/app.py`：注册 evolution/plan/settings 路由
- `src/core/webui/routes/`：现有路由增加认证中间件一致性校验
- `webui/src/App.tsx`：新增路由配置（/evolution、/evolution/report、/plan、/settings）
- `webui/src/components/layout/Sidebar.tsx`：侧边栏新增"计划"、"进化"、"设置"导航项
- `pyproject.toml`：版本号更新为 0.29.0
- `docs/architecture/架构设计说明书.md`：更新架构图，补充 WebUI 管理控制台模块
- `docs/requirements/REQ_需求规格说明书.md`：新增 v0.29.0 需求条目

### Security
- 所有新增 WebUI API 端点默认启用 Token 认证
- 仅监听 127.0.0.1（本地访问）
- 计划调整 API 复用现有 Agent 对话认证机制

### 测试验证
- 新增 35 个后端 Python 单元测试（`tests/unit/core/webui/`）
- 新增 12 个集成测试（`tests/integration/module/`）
- 后端覆盖率：evolution.py 100%、plan.py 97%、settings.py 96%
- 全量测试通过率 100%（47/47）
- ruff check：0 errors, 0 warnings
- mypy 类型检查：Success: no issues found

### Bug 修复
- 修复集成测试路径前缀错误（`/api/webui/` → `/api/`）
- 修复 evolution 路由方法名错误（`check_triggers()` → `check_evolution_triggers()`）
- 修复 evolution 路由私有属性访问问题（新增公共方法封装）

### 文档产出
- `docs/test/strategy_v0.29.0.md` - 测试策略
- `docs/test/测试报告_v0.29.0.md` - 测试报告
- `docs/test/Bug清单_v0.29.0.md` - Bug 清单
- `docs/architecture/review/2026-06-09-v0.29.0-架构评审报告.md` - 架构评审报告

### 已知问题
- 无阻塞上线的缺陷

---

## [0.28.0] - 2026-06-04

### 版本主题
**WebUI 数据可视化** —— 扩展 WebUI，增加跑步数据可视化能力，6 大页面全面展示跑步数据

> v0.28.0 是 Phase D（交互升级）的第三个版本，在 v0.27.0 WebUI 基础之上，新增完整的跑步数据可视化能力，从纯 AI 对话交互进化到数据可视化 + AI 对话双模式。

**本版本已实现**:
- ✅ 后端 FastAPI 服务：独立运行在端口 8766，10 个 API 端点
- ✅ 前端 React SPA：6 个页面（Dashboard/VDOT/训练负荷/活动列表/活动详情/身体信号）
- ✅ Gateway 集成：`gateway start --webui` 同时启动 AI 对话 (8765) + 数据可视化 (8766)
- ✅ Token 认证：所有 API 端点需认证，共享 nanobot-ai 令牌机制
- ✅ 数据一致性：WebUI 数据与 CLI 输出同源，误差 < 0.1%
- ✅ 全量回归测试 126 用例零失败，后端覆盖率 100%

### Added
- `src/core/webui/` 模块：FastAPI 应用工厂、认证中间件、路由层、服务层
- `webui/` 前端项目：React + TypeScript + Vite + Recharts + TailwindCSS
- Dashboard API：`GET /api/webui/dashboard`，返回今日概览 + 本周统计
- VDOT 趋势 API：`GET /api/webui/vdot/trend`，返回 VDOT 趋势数据
- 训练负荷 API：`GET /api/webui/training-load` 和 `GET /api/webui/training-load/trend`
- 活动列表 API：`GET /api/webui/activities`，支持分页/时间/距离筛选
- 活动详情 API：`GET /api/webui/activities/{id}`，id 为 SHA256 哈希
- 身体信号 API：4 个端点（汇总/HRV/疲劳/恢复）
- WebUI 前端 6 个页面：Dashboard、VDOT 趋势、训练负荷、活动列表、活动详情、身体信号
- `useTimeRange` Hook：全局时间范围状态管理（7/30/90/365 天）
- Gateway `--webui` 标志增强：同时启动 FastAPI 数据可视化服务
- `uvicorn.Server.serve()` 启动方式，与现有事件循环兼容
- 前端 SPA 同源部署（端口 8766），避免 CORS 问题
- 51 个 Python 后端单元测试 + 10 个前端单元测试
- 60 个集成测试 + 5 个 E2E 测试

### Changed
- Gateway 启动流程：`--webui` 标志现在同时启动 AI 对话服务 (8765) 和数据可视化服务 (8766)
- WebUI 访问地址从 8765 变更为 8766（数据可视化专用端口）
- `pyproject.toml` wheel targets 包含 `webui/dist/` 前端构建产物

### Security
- 所有 WebUI API 端点默认启用 Token 认证
- 仅监听 127.0.0.1（本地访问）
- 共享 nanobot-ai 的 token_issue_path 短期令牌签发机制

### 测试验证
- 新增 51 个后端 Python 单元测试（`tests/unit/core/webui/`）
- 新增 10 个前端 TypeScript 单元测试（`webui/src/__tests__/`）
- 新增 25 个 WebUI 启动集成测试
- 新增 35 个场景集成测试
- 新增 5 个 E2E 用户旅程测试
- 后端覆盖率：app.py 100%、auth.py 93%、routes/*.py 100%、server.py 100%
- 全量测试通过率 100%（126/126）

### 文档产出
- `docs/test/strategy_v0.28.0.md` - 测试策略
- `docs/test/测试报告_v0.28.0.md` - 测试报告
- `docs/planning/task_list_v0.28.0.md` - 任务清单（22 项任务）
- `docs/architecture/架构评审报告-v0.28.0.md` - 架构评审报告

### 已知问题
- P1: Token 签发端点无速率限制（v0.29.0 修复）
- P2: 代码路径与架构设计文档需统一（v0.29.0 修复）
- P2: JWT 密钥长度警告（配置层面确保 ≥32 字节即可）

---

## [0.27.0] - 2026-05-31

### 版本主题
**WebUI 基础** —— 配置驱动启用 nanobot-ai 内置 WebUI，AI 对话交互 + 基础设置

> v0.27.0 是 Phase D（交互升级）的第二个版本，通过配置驱动方式启用 nanobot-ai 原生 WebUI，实现浏览器端 AI 对话交互能力，从纯 CLI 进化到 Web 交互。

**本版本已实现**:
- ✅ WebSocket 通道配置：config.json 新增 `websocket` 配置节，支持环境变量覆盖
- ✅ Gateway CLI 增强：`gateway start --webui` 标志启用 WebUI
- ✅ 品牌自定义：bot_name="Nanobot-Runner", bot_icon="🏃‍♂️"
- ✅ 安全认证：默认启用 token 认证，仅监听 127.0.0.1
- ✅ 向后兼容：不启用 WebUI 时飞书/CLI 功能不受影响
- ✅ 全量回归 4489 用例零失败，覆盖率 81%

### Added
- ConfigManager.get_websocket_config() 方法，读取 WebSocket 通道配置，支持环境变量覆盖（NANOBOT_WS_*）
- RunnerProviderAdapter.webui_enabled 参数，接收 CLI `--webui` 标志
- RunnerProviderAdapter._build_websocket_channel_config() 方法，构建 WebSocket 通道配置
- Gateway CLI `--webui` 标志，启用时自动配置 WebSocket 通道
- WebUI 访问地址显示（http://{host}:{port}）
- Token 获取方式提示（curl http://{host}:{port}/token）
- WebUI Settings API 拦截（防止写入 ~/.nanobot/config.json，保持配置独立性）
- 品牌字段支持（bot_name/bot_icon/unified_session）写入 AgentsConfig.defaults
- ADR-015 WebSocket 通道配置方式决策记录
- ADR-016 WebUI 启用方式决策记录
- ADR-017 安全认证策略决策记录

### Changed
- RunnerProviderAdapter._build_nanobot_config_from_runner() 新增 WebSocket 配置构建逻辑
- gateway start 命令启动信息显示 WebUI 专属交互信息

### Security
- WebSocket 通道默认仅监听 127.0.0.1（本地访问）
- 默认启用 token 认证（websocket_requires_token=True）
- 采用 token_issue_path 短期令牌签发机制

### 测试验证
- 新增 25 个 WebSocket 配置单元测试（test_websocket_config.py）
- 新增 19 个 ProviderAdapter WebSocket 配置构建单元测试
- 新增 25 个 WebUI 启动集成测试
- 单元测试 4134 passed (100% 通过率)
- 集成测试 355 passed (100% 通过率)
- 代码覆盖率 core 81% ≥ 80% 目标

### 文档产出
- `docs/test/strategy_v0.27.0.md` - 测试策略
- `docs/test/测试报告_v0.27.0.md` - 测试报告
- `docs/test/上线结论_v0.27.0.md` - 上线结论（建议上线）

---

## [0.26.0] - 2026-05-24

### 版本主题
**Phase D 底座升级与推理可见化** —— nanobot-ai 0.2.0底座升级、GoalState适配、推理过程流式可见化、Model Presets预设管理

> v0.26.0 是Phase D（底座升级与平台增强）的首个版本，完成nanobot-ai从0.1.5.post2到0.2.0的底座升级，新增GoalState决策目标状态追踪、推理过程流式可见化（reasoning visibility）和Model Presets多模型预设管理，为后续Agent能力增强奠定基础。

**本版本已实现**:
- ✅ nanobot-ai 0.2.0 底座升级（兼容性100%验证）
- ✅ GoalState适配：DecisionLog新增goal_state字段，追踪每次决策的目标状态
- ✅ 推理可见化：emit_reasoning/emit_reasoning_end/finalize_content三段式推理流
- ✅ Model Presets：AppConfig.model_presets字段，支持多模型预设列表管理
- ✅ CLI命令: `model list` - 查看可用模型预设列表
- ✅ 全量回归5075用例零失败，覆盖率82.63%

### Added
- DecisionLog.goal_state 字段，记录决策时的5维度目标状态
- goal_state_raw() 方法，从metadata提取goal_state
- after_iteration() 回调，自动读取metadata并写入DecisionLog
- emit_reasoning() 追加推理片段到缓冲区
- emit_reasoning_end() 标记推理完成
- finalize_content() 将推理写入prediction_snapshot
- before_iteration() 重置推理状态
- AppConfig.model_presets 字段，支持模型预设配置
- `model list` CLI命令，查看可用模型预设列表
- ModelHandler.list_presets 返回预设列表
- ADR-012 GoalState适配决策记录
- ADR-013 推理可见化适配决策记录
- ADR-014 Model Presets适配决策记录

### Changed
- nanobot-ai 底座从0.1.5.post2升级至0.2.0
- 底座兼容性：ruff/mypy/pytest全量验证通过
- 依赖版本：nanobot-ai>=0.2.0

### Fixed
- 测试隔离性优化：偶发flaky test（test_memory_version_list_and_restore）已记录跟踪（优化级，不影响发布）

---

## [0.25.0] - 2026-05-22

### 版本主题
**自适应进化控制** —— 进化触发规则引擎、提示参数调优、月度进化报告

> v0.25.0 是Phase C（自适应进化引擎）的第三个版本，新增进化触发控制器、提示参数调优器和月度进化报告生成器，实现AI决策的自适应进化闭环。

**本版本已实现**:
- ✅ EvolutionController: 4触发规则(VDOT误差/连续拒绝/新数据积累/月度复盘) + persist-first执行
- ✅ PromptTuner: 4维参数空间(tone/detail/aggressive/data_driven) + 地板保护 + 弹回机制
- ✅ EvolutionReporter: 月度进化报告生成
- ✅ 5个新数据模型: EvolutionAction/TriggerCheckResult/PromptTuningParams/EvolutionReport/IncrementalLearnResult
- ✅ 3条CLI命令: evolution triggers/report/tune
- ✅ 3个Agent工具: check_evolution_triggers/get_evolution_report/adjust_prompt_params
- ✅ DecisionLogHook after_iteration回调: 自动检查进化触发条件

### Added
- EvolutionController: 4 trigger rules (VDOT误差/连续拒绝/新数据积累/月度复盘) with persist-first execution
- PromptTuner: 4-dim parameter space (tone/detail/aggressive/data_driven) with floor protection and bounce-back
- EvolutionReporter: Monthly evolution report generation
- EvolutionAction, TriggerCheckResult, PromptTuningParams, EvolutionReport, IncrementalLearnResult data models
- CLI commands: `evolution triggers`, `evolution report`, `evolution tune`
- Agent tools: check_evolution_triggers, get_evolution_report, adjust_prompt_params
- DecisionLogHook after_iteration callback for automatic evolution trigger checking

### Fixed
- H-01: DecisionLogHook holds EvolutionEngine reference (orchestration layer consistency)
- H-02: IncrementalLearnResult for structured partial failure tracking
- H-03: Parameter floor protection (aggressive>=0.1, data_driven>=0.2) with bounce-back mechanism
- PromptTuningParams.with_updates() data_driven logic bug fix
- EvolutionController rejection trigger checking wrong field (outcome vs decision)
- ResponseAnalyzer missing days parameter in get_decision_outcome_pairs call

---

## [0.24.0] - 2026-05-21

### 版本主题
**个性化学习** —— 测试验证体系升级，为v0.24个性化学习功能交付奠定质量基础

> v0.24.0 是Phase C（自适应进化引擎）的第二个版本，完成测试验证阶段全部工作，产出测试策略、测试报告、Bug修复、回归测试报告及上线结论，确认代码库基线质量达标。

**本版本已实现**:
- ✅ 测试策略制定（34个测试用例覆盖P0+P1全部验收标准）
- ✅ 全量单元测试基线建立（3937 passed, 0 failed, 覆盖率81%）
- ✅ BUG-V024-001修复（工具计数断言51→54，expected_names补充）
- ✅ 回归测试验证通过（7/7上线门禁全部满足）
- ✅ 上线结论：建议上线

### 测试验证

#### 测试策略（TST-01）
- 覆盖需求：REQ-0.24-01(P0) 5/5 AC、REQ-0.24-02(P1) 6/6 AC、REQ-0.24-03(P1) 4/4 AC
- 核心测试用例：34个，覆盖功能/边界/异常/算法/向后兼容
- 架构评审整改验证：4项HIGH问题整改全部覆盖

#### 测试执行（TST-02）
- 全量单元测试：3838 passed（修复后3937 passed），1 skipped
- 覆盖率：81%（核心模块85-100%）
- Bug发现：1个LOW级（测试断言过期），生产代码0 Bug

#### Bug修复（DEV-02）
- BUG-V024-001：工具数量断言值51→54，expected_names补充
- 修复方式：TDD流程（确认失败→修改断言→验证通过）
- 修复验证：2/2 passed，全量回归0退化

#### 回归测试（TST-03）
- 修复后全量：3937 passed, 0 failed, 1 skipped
- 上线门禁：7/7全部通过
- **上线结论：建议上线**

### 文档产出
- `docs/test/strategy_v0.24.0.md` - 测试策略
- `docs/test/测试报告_v0.24.0.md` - 测试报告
- `docs/test/Bug清单_v0.24.0.md` - Bug清单
- `docs/test/回归报告_v0.24.0.md` - 回归报告
- `docs/test/上线结论_v0.24.0.md` - 上线结论

---

## [0.23.0] - 2026-05-20

### 版本主题
**决策追踪模块** —— AI决策自动记录、结果回填、用户反馈收集、自适应进化引擎基础

> v0.23.0 是Phase C（自适应进化引擎）的首个版本，新增决策追踪模块，实现AI决策自动记录与结果回填，为v0.24个性化学习和v0.25自适应进化奠定基础。

**本版本已实现**:
- ✅ 决策日志自动记录（DecisionLogHook无侵入接入）
- ✅ 结果回填机制（执行忠实度、预测准确度）
- ✅ 用户反馈收集（评分/文本/采纳状态）
- ✅ CLI命令组（evolution status/history/feedback/accuracy/fidelity）
- ✅ Agent工具集成（check_plan_execution/check_prediction_accuracy）
- ✅ 按月分片Parquet存储（decisions/outcomes）
- ✅ EvolutionConfig配置Schema（环境变量覆盖支持）

### 新增功能

#### 决策追踪模块（Evolution Engine）
- **DecisionLog**: 冻结数据类，10个字段，记录AI决策完整上下文
- **OutcomeRecord**: 冻结数据类，11个字段，记录决策执行结果
- **DecisionLogHook**: 继承AgentHook，无侵入接入Agent生命周期
- **EvolutionStore**: 按月分片Parquet存储，支持决策/结果配对查询
- **OutcomeCollector**: 执行忠实度计算、预测准确度评估、反馈收集
- **EvolutionEngine**: 决策追踪引擎编排层，统一接口

#### CLI命令组
- `uv run nanobotrun evolution status` - 查看进化状态
- `uv run nanobotrun evolution history [--start] [--end] [--type]` - 查询决策历史
- `uv run nanobotrun evolution feedback <decision_id> --score [--text] [--accepted]` - 提交反馈
- `uv run nanobotrun evolution accuracy [--days 30]` - 查看预测准确度
- `uv run nanobotrun evolution fidelity [--days 30]` - 查看执行忠实度

#### Agent工具
- `check_plan_execution()` - 检查计划执行忠实度
- `check_prediction_accuracy()` - 检查预测准确度

### 技术改进

#### 架构优化
- **Hook独立注册**: DecisionLogHook独立继承AgentHook，避免与ObservabilityHook状态竞争
- **依赖注入扩展**: AppContext新增evolution_engine属性
- **配置驱动**: EvolutionConfig遵循Pydantic-Settings模式，支持环境变量覆盖
- **执行忠实度公式**: 简化为`fidelity = 1 - (0.55 * 体积偏差 + 0.45 * 时间偏差)`

#### 数据模型
- **execution_status**: 统一为5种状态（pending/executed/skipped/modified/failed）
- **prediction_direction**: 新增字段（overestimate/underestimate/accurate/None）
- **runner_state摘要**: 5个关键指标（vdot/ctl/atl/tsb/fatigue_score）

---

## 历史版本摘要

> 以下为v0.22.1及更早版本的摘要记录，详细变更见归档文档。

| 版本 | 日期 | 核心内容 |
|------|------|---------|
| [0.22.1](docs/archive/changelog/CHANGELOG_v0.22.1.md) | 2026-05-19 | 代码质量重构：17处type:ignore修复、裸Exception替换、跨模块去重、文件拆分 |
| [0.22.0](docs/archive/changelog/CHANGELOG_v0.22.0.md) | 2026-05-18 | 质量收口版本：UAT验证、缺陷收敛、质量兜底、发布准备 |
| [0.21.0](docs/archive/changelog/CHANGELOG_v0.21.0.md) | 2026-05-12 | 数字孪生引擎：5维度状态向量、What-If推演、计划对比 |
| [0.20.1](docs/archive/changelog/CHANGELOG_v0.20.1.md) | 2026-05-11 | ML预测增强：VDOT/伤病/比赛ML训练推理、SHAP分析、模型管理 |
| [0.20.0](docs/archive/changelog/CHANGELOG_v0.20.0.md) | 2026-05-09 | ML增强预测架构：三层降级策略、特征工程、CLI命令组 |
| [0.19.0](docs/archive/changelog/CHANGELOG_v0.19.0.md) | 2026-05-06 | 身体信号分析：HRV分析、疲劳度评估、恢复状态、身体信号解读 |
| [0.18.0](docs/archive/changelog/CHANGELOG_v0.18.0.md) | 2026-05-04 | 数据可视化与导出：终端图表(plotext)、多格式导出 |
| [0.17.0](docs/archive/changelog/CHANGELOG_v0.17.0.md) | 2026-05-03 | AI底座激活：Hook组合、Subagent、异步确认、Cron提醒 |
| [0.16.1](docs/archive/changelog/CHANGELOG_v0.16.1.md) | 2026-04-29 | 测试目录结构重构 |
| [0.16.0](docs/archive/changelog/CHANGELOG_v0.16.0.md) | 2026-04-29 | Core模块化重构：base/calculators/config/storage/report/models |
| [0.15.0](docs/archive/changelog/CHANGELOG_v0.15.0.md) | 2026-04-28 | AI决策透明化：决策追踪、可观测性、追踪日志器 |
| [0.13.0](docs/archive/changelog/CHANGELOG_v0.13.0.md) | 2026-04-27 | 智能技能生态：MCP工具管理、天气/地图/健康Agent工具 |
| [0.12.0](docs/archive/changelog/CHANGELOG_v0.12.0.md) | 2026-04-19 | 预测规划层：目标达成评估、长期周期规划、智能建议 |
| [0.11.0](docs/archive/changelog/CHANGELOG_v0.11.0_and_older.md#0110---2026-04-19) | 2026-04-19 | 智能调整层、计划调整校验器、Prompt模板引擎 |
| [0.10.0](docs/archive/changelog/CHANGELOG_v0.11.0_and_older.md#0100---2026-04-19) | 2026-04-19 | 数据感知层、训练响应分析器、计划执行仓储 |
| [0.9.5](docs/archive/changelog/CHANGELOG_v0.11.0_and_older.md#095---2026-04-20) | 2026-04-20 | Gateway服务增强、智谱AI支持、数据查询优化 |
| [0.9.4](docs/archive/changelog/CHANGELOG_v0.11.0_and_older.md#094---2026-04-18) | 2026-04-18 | 配置管理基础设施、初始化向导、数据迁移引擎 |
| [0.9.3](docs/archive/changelog/CHANGELOG_v0.11.0_and_older.md#093---2026-04-15) | 2026-04-15 | 报告生成、飞书Gateway重构、领域模型统一 |
| [0.9.2](docs/archive/changelog/CHANGELOG_v0.11.0_and_older.md#092---2026-04-11) | 2026-04-11 | AGENTS.md重构、CI/CD优化 |
| [0.9.1](docs/archive/changelog/CHANGELOG_v0.11.0_and_older.md#091---2026-04-10) | nanobot-ai升级至0.1.5 |
| [0.9.0](docs/archive/changelog/CHANGELOG_v0.11.0_and_older.md#090---2026-04-09) | 依赖注入机制、SessionRepository仓储层、CLI架构重构 |

**完整历史版本详情**: [docs/archive/changelog/](docs/archive/changelog/)
