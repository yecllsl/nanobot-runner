# v0.32.0 测试策略

> **版本**: v0.32.0
> **制定日期**: 2026-07-14
> **测试负责人**: sp-test-engineer
> **状态**: 已批准

---

## 1. 测试范围

### 1.1 核心变更清单

| 变更类型 | 变更内容 | 影响模块 | 测试优先级 |
|---------|---------|---------|-----------|
| **底座升级** | nanobot-ai 0.2.1 → 0.2.2 | 全局 | P0 |
| **配置分离** | config.json → nanobot_config.json | 配置管理、Provider、Gateway | P0 |
| **技术债清偿** | 移除 4 项 monkey-patch | provider_adapter、gateway | P0 |
| **新增组件** | ConfigInjector、AgentLoopAdapter、SDKAdapter、RuntimeEventHook、DynamicProviderRegistry | 核心模块 | P0 |
| **新功能** | SDK 编程式调用、运行时事件 SSE、自定义 Provider、语音转录配置 | WebUI、Agent | P1 |

### 1.2 测试范围界定

**在测试范围内**：
- 配置分离正确性（nanobot_config.json 作为唯一来源）
- 旧配置迁移完整性（config.json → nanobot_config.json）
- Provider 适配器配置读取
- WebUI 启动链路（Gateway + WebUI）
- 运行时事件 SSE 端点
- SDK 编程式调用
- 自定义 Provider 注册
- Hook 生命周期兼容性
- Dream 集成适配
- Cron 会话绑定

**不在测试范围内**：
- nanobot-ai 内部实现（由上游项目负责）
- 前端 UI 交互细节（由 E2E 测试覆盖）
- 性能基线对比（独立性能测试覆盖）

---

## 2. 测试类型与策略

### 2.1 单元测试

**目标**：验证新增组件和改造后组件的独立功能正确性

**覆盖范围**：
| 模块 | 测试文件 | 覆盖率目标 |
|------|---------|-----------|
| ConfigInjector | `tests/unit/core/test_config_injector.py` | ≥85% |
| AgentLoopAdapter | `tests/unit/core/test_agent_loop_adapter.py` | ≥85% |
| SDKAdapter | `tests/unit/core/test_sdk_adapter.py` | ≥85% |
| RuntimeEventHook | `tests/unit/core/transparency/test_runtime_event_hook.py` | ≥85% |
| DynamicProviderRegistry | `tests/unit/core/test_dynamic_provider_registry.py` | ≥85% |
| ConfigManager（改造后） | `tests/unit/core/config/test_manager.py` | ≥80% |
| RunnerProviderAdapter（改造后） | `tests/unit/core/test_provider_adapter.py` | ≥80% |
| MCP 配置读取 | `tests/unit/core/test_mcp_connector.py` | ≥80% |
| 初始化向导 | `tests/unit/core/test_init_*.py` | ≥75% |
| 配置迁移 | `tests/unit/core/test_migrate_engine.py` | ≥85% |

**Mock 策略**：
- nanobot-ai 内部组件使用 Mock
- 文件系统操作使用 `tmp_path` fixture
- 环境变量使用 `monkeypatch` 或 `patch.dict`

### 2.2 集成测试

**目标**：验证跨模块交互和全流程闭环

**覆盖范围**：
| 场景 | 测试文件 | 验证点 |
|------|---------|--------|
| 配置注入全流程 | `tests/integration/test_config_injection_flow.py` | ConfigInjector → RunnerProviderAdapter → AgentLoop |
| SDK 编程式调用 | `tests/integration/test_sdk_programmatic_call.py` | SDKAdapter → NanobotSDK → AgentLoop |
| 运行时事件订阅 | `tests/integration/test_runtime_event_flow.py` | RuntimeEventHook → SSE → WebUI |
| Cron 会话绑定 | `tests/integration/test_cron_session_binding.py` | CronCallbackHandler → AgentLoopAdapter |
| 自定义 Provider | `tests/integration/test_dynamic_provider.py` | DynamicProviderRegistry → Provider 创建 |
| Dream 适配 | `tests/integration/test_dream_adaptation.py` | DreamIntegration cron + process_direct |
| Hook 生命周期 | `tests/integration/test_hook_lifecycle.py` | 5 个 AgentHook 接入 run-level |
| 双路径共存 | `tests/integration/test_dual_path_coexistence.py` | Gateway 模式 + SDK 模式 |
| nanobot API 契约 | `tests/integration/test_nanobot_api_contract.py` | 锁定公开 API 签名 |
| 破坏性变更验证 | `tests/integration/test_nanobot_compatibility.py` | 7 项破坏性变更影响 |
| WebUI 启动 | `tests/integration/test_webui_startup.py` | Gateway + WebUI 完整启动 |

### 2.3 E2E 测试

**目标**：验证真实用户场景的全链路

**覆盖范围**：
| 场景 | 验证点 |
|------|--------|
| 初始化向导 | init → 生成双文件 + .gitignore → gateway start |
| 配置迁移 | 旧 config.json → migrate → nanobot_config.json → gateway start |
| WebUI 数据可视化 | 10 大页面加载正常 |
| 运行时事件 SSE | WebUI 实时接收事件 |
| 自定义 Provider UI | WebUI 设置中心添加 Provider |

---

## 3. 门禁规则

### 3.1 准入规则

测试启动前必须满足：

| 序号 | 准入条件 | 验证方式 |
|------|---------|---------|
| 1 | 所有新增组件代码已提交 | `git status` 无未提交文件 |
| 2 | 代码静态检查通过 | `uv run ruff check src/ tests/` 无错误 |
| 3 | 类型检查通过 | `uv run mypy src/ --ignore-missing-imports` 无错误 |
| 4 | 单元测试代码已编写 | 测试文件存在且可执行 |
| 5 | 依赖版本正确 | `nanobot-ai>=0.2.2,<0.3.0` |

### 3.2 准出规则

测试通过后必须满足：

| 序号 | 准出条件 | 量化指标 | 严重等级 |
|------|---------|---------|---------|
| 1 | 单元测试通过率 | ≥95% | 阻断发布 |
| 2 | 集成测试通过率 | ≥90% | 阻断发布 |
| 3 | 核心模块覆盖率 | src/core/ ≥80% | 阻断发布 |
| 4 | 新增组件覆盖率 | ≥85% | 阻断发布 |
| 5 | P0 级 Bug | 0 个 | 阻断发布 |
| 6 | P1 级 Bug | 0 个 | 阻断发布 |
| 7 | P2 级 Bug 修复率 | ≥90% | 条件发布 |
| 8 | 配置分离全流程闭环 | 100% 通过 | 阻断发布 |
| 9 | WebUI 启动链路正常 | 100% 通过 | 阻断发布 |
| 10 | nanobot API 契约测试 | 100% 通过 | 阻断发布 |

### 3.3 上线门禁

**同时满足以下条件方可发布**：
1. 单元测试通过率 ≥95%
2. 集成测试通过率 ≥90%
3. 核心模块覆盖率 ≥80%
4. 无 P0/P1 级 Bug
5. 配置分离全流程闭环验证通过
6. WebUI 启动链路验证通过
7. nanobot API 契约测试全部通过

---

## 4. 测试用例清单

### 4.1 配置分离正确性（P0）

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 |
|--------|---------|---------|---------|---------|
| TC-CS-001 | nanobot_config.json 作为唯一来源 | 存在 nanobot_config.json | 读取 LLM 配置 | 从 nanobot_config.json 读取 |
| TC-CS-002 | config.json 精简后仅含 5 字段 | 迁移完成 | 读取 config.json | 仅含 version/data_dir/timezone/auto_push_feishu/user_id |
| TC-CS-003 | nanobot_config.json 不存在时降级 | 删除 nanobot_config.json | 检查 has_llm_config() | 返回 False |
| TC-CS-004 | nanobot_config.json JSON 格式错误 | 写入非法 JSON | 加载配置 | 抛出 ConfigError |
| TC-CS-005 | providers.default 指向不存在的 provider | 配置 default="unknown" | 创建 Provider | 抛出 LLMError |
| TC-CS-006 | apiKey 为空时降级 | provider 存在但 apiKey="" | 检查 has_llm_config() | 返回 False |

### 4.2 旧配置迁移完整性（P0）

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 |
|--------|---------|---------|---------|---------|
| TC-MG-001 | 完整字段映射 | 旧 config.json 含所有字段 | 执行 migrate-config | nanobot_config.json 含正确映射 |
| TC-MG-002 | API Key 从 .env.local 迁移 | .env.local 含 NANOBOT_LLM_API_KEY | 执行迁移 | apiKey 写入 providers |
| TC-MG-003 | 飞书凭证迁移 | .env.local 含飞书凭证 | 执行迁移 | channels.feishu 含凭证 |
| TC-MG-004 | 备份旧配置 | 旧 config.json 存在 | 执行迁移 | config.json.bak 存在 |
| TC-MG-005 | 迁移失败回滚 | 模拟写入失败 | 执行迁移 | config.json 恢复，nanobot_config.json 删除 |
| TC-MG-006 | .gitignore 排除 nanobot_config.json | 迁移完成 | 检查 .gitignore | 含 nanobot_config.json 条目 |

### 4.3 Provider 适配器配置读取（P0）

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 |
|--------|---------|---------|---------|---------|
| TC-PA-001 | get_llm_config 从 nanobot_config.json 读取 | nanobot_config.json 存在 | 调用 get_llm_config() | 返回正确 LLMConfig |
| TC-PA-002 | get_agent_defaults 读取 | nanobot_config.json 存在 | 调用 get_agent_defaults() | 返回正确 AgentDefaults |
| TC-PA-003 | _resolve_fallback_presets 读取 | fallbackModels 配置 | 调用方法 | 返回 ModelPresetConfig 列表 |
| TC-PA-004 | is_available 检查 | nanobot_config.json 有效 | 调用 is_available() | 返回 True |
| TC-PA-005 | 无配置时抛出 LLMError | nanobot_config.json 不存在 | 调用 get_llm_config() | 抛出 LLMError |

### 4.4 WebUI 启动链路（P0）

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 |
|--------|---------|---------|---------|---------|
| TC-WUI-001 | Gateway 正常启动 | nanobot_config.json 存在 | gateway start --webui | 启动成功，无报错 |
| TC-WUI-002 | ChannelManager 从 nanobot_config.json 加载 | nanobot_config.json 存在 | 启动 Gateway | ChannelManager 正确初始化 |
| TC-WUI-003 | MCP 配置从 nanobot_config.json 读取 | tools.mcpServers 配置 | 启动 Gateway | MCP 服务器正确连接 |
| TC-WUI-004 | WebUI dist 目录解析 | webui/dist 存在 | 启动 Gateway | 正确解析 dist 目录 |
| TC-WUI-005 | 无 LLM 配置时提示 | nanobot_config.json 不存在 | 启动 Gateway | 提示"请运行 nanobotrun system init" |

### 4.5 运行时事件 SSE（P1）

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 |
|--------|---------|---------|---------|---------|
| TC-SSE-001 | SSE 端点可访问 | Gateway 启动 | GET /api/runtime-events/stream | 返回 200，SSE 流 |
| TC-SSE-002 | 事件订阅回调 | RuntimeEventHook 注册 | 发布事件 | 回调被调用 |
| TC-SSE-003 | 多订阅者支持 | 注册多个回调 | 发布事件 | 所有回调被调用 |
| TC-SSE-004 | 回调异常静默降级 | 回调抛出异常 | 发布事件 | 不影响其他回调 |

### 4.6 SDK 编程式调用（P1）

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 |
|--------|---------|---------|---------|---------|
| TC-SDK-001 | 创建 SDK 会话 | Config 有效 | create_session() | 返回 NanobotSDK 实例 |
| TC-SDK-002 | 流式查询 | SDK 会话存在 | stream_query() | 返回异步迭代器 |
| TC-SDK-003 | 同步查询 | SDK 会话存在 | query() | 返回完整响应 |
| TC-SDK-004 | SDK 不可用降级 | SDK 初始化失败 | query() | 抛出 SDKUnavailableError |

### 4.7 自定义 Provider 注册（P1）

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 |
|--------|---------|---------|---------|---------|
| TC-DPR-001 | 注册自定义 Provider | 无冲突名称 | register_custom_provider() | 注册成功 |
| TC-DPR-002 | 名称冲突拒绝 | 名称为 "openai" | register_custom_provider() | 拒绝注册，日志警告 |
| TC-DPR-003 | 列出已注册 Provider | 已注册多个 | list_custom_providers() | 返回名称列表 |

### 4.8 Hook 生命周期兼容性（P1）

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 |
|--------|---------|---------|---------|---------|
| TC-HOOK-001 | before_iteration 签名兼容 | AgentLoop 存在 | 调用 Hook | 无异常 |
| TC-HOOK-002 | after_iteration 签名兼容 | AgentLoop 存在 | 调用 Hook | 无异常 |
| TC-HOOK-003 | before_execute_tools 签名兼容 | AgentLoop 存在 | 调用 Hook | 无异常 |
| TC-HOOK-004 | run-level hook 接入 | 0.2.2 环境 | 注册 before_run/after_run | Hook 被调用 |

### 4.9 边界条件测试

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 |
|--------|---------|---------|---------|---------|
| TC-EDGE-001 | nanobot_config.json 空文件 | 文件存在但为空 | 加载配置 | 返回空 dict |
| TC-EDGE-002 | providers 为空对象 | providers: {} | 检查 has_llm_config() | 返回 False |
| TC-EDGE-003 | agents.defaults 缺失 | 无 agents 节 | 读取 agent_defaults | 使用默认值 |
| TC-EDGE-004 | timezone 双写一致性 | config.json 和 nanobot_config.json 各有时区 | 读取两处 | 各自独立，不冲突 |

### 4.10 异常场景测试

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 |
|--------|---------|---------|---------|---------|
| TC-EX-001 | 配置文件权限不足 | 文件只读 | 写入配置 | 抛出 ConfigError |
| TC-EX-002 | 磁盘空间不足 | 磁盘满 | 写入配置 | 抛出 ConfigError |
| TC-EX-003 | nanobot-ai 版本不兼容 | 安装 0.2.1 | 导入模块 | 版本检查失败 |
| TC-EX-004 | 私有 API 变更 | nanobot 内部变更 | 调用 AgentLoopAdapter | 抛出 AdapterError |

---

## 5. 测试环境

### 5.1 环境配置

| 项目 | 配置 |
|------|------|
| Python | 3.11+ |
| nanobot-ai | 0.2.2 |
| 操作系统 | Windows 10/11 |
| 测试框架 | pytest 7.0+ |
| 覆盖率工具 | pytest-cov |
| Mock 工具 | pytest-mock |

### 5.2 测试数据

| 数据类型 | 来源 | 用途 |
|---------|------|------|
| 旧版 config.json | 手动构造 | 迁移测试 |
| nanobot_config.json | 手动构造 | 配置读取测试 |
| .env.local | 手动构造 | API Key 迁移测试 |
| FIT 文件 | 现有测试数据 | 回归测试 |

---

## 6. 测试进度计划

| 阶段 | 任务 | 预计工时 | 负责人 |
|------|------|---------|--------|
| 阶段 1 | 单元测试执行 | 2h | sp-test-engineer |
| 阶段 2 | 集成测试执行 | 3h | sp-test-engineer |
| 阶段 3 | 覆盖率分析 | 1h | sp-test-engineer |
| 阶段 4 | Bug 提交与跟踪 | 2h | sp-test-engineer |
| 阶段 5 | 回归测试 | 2h | sp-test-engineer |
| 阶段 6 | 测试报告输出 | 1h | sp-test-engineer |

**总计**：11h

---

## 7. 风险与应对

| 风险 | 影响 | 概率 | 应对措施 |
|------|------|------|---------|
| nanobot-ai 私有 API 变更 | AgentLoopAdapter 调用失败 | 中 | 提前验证 API 签名，准备回滚方案 |
| 配置迁移数据丢失 | 用户配置丢失 | 低 | 迁移前备份，迁移失败回滚 |
| WebUI 启动失败 | 用户无法使用 WebUI | 中 | 详细日志，快速定位问题 |
| 测试覆盖率不达标 | 质量风险 | 低 | 补充测试用例 |

---

## 8. 交付物

| 交付物 | 路径 | 说明 |
|--------|------|------|
| 测试策略 | `docs/test/strategy_v0.32.0.md` | 本文档 |
| 测试报告 | `docs/test/reports/测试报告_v0.32.0.md` | 测试执行结果 |
| Bug 清单 | `docs/test/reports/Bug清单_v0.32.0.md` | 发现的缺陷 |
| 覆盖率报告 | 终端输出 | pytest-cov 生成 |

---

## 9. 验收标准

测试策略验收标准：
1. 测试范围覆盖所有核心变更 ✅
2. 门禁规则可量化 ✅
3. 测试用例覆盖核心场景 ✅
4. 风险识别完整 ✅

---

**文档结束**
