# v0.27.0 测试策略与规范

> **版本**: v0.27.0
> **主题**: WebUI 基础 -- 配置驱动启用 nanobot-ai 内置 WebUI
> **制定日期**: 2026-05-27
> **制定人**: 测试工程师
> **需求基线**: 需求规格说明书 v12.1 §5.3
> **架构基线**: 架构设计说明书 v16.0.0 §10
> **代码评审基线**: 代码评审报告_v0.27.0.md (有条件通过)

---

## 1. 测试范围

### 1.1 需求覆盖矩阵

| 需求编号 | 需求名称 | 优先级 | 测试层级 | 覆盖方式 |
|----------|---------|--------|---------|---------|
| REQ-D-11 | WebUI 启动 | P0 | 单元 + 集成 + E2E | 自动化 |
| REQ-D-12 | 工具调用 | P0 | 集成 + E2E | 自动化 + 手工 |
| REQ-D-13 | 流式输出 | P0 | 集成 + E2E | 自动化 + 手工 |
| REQ-D-14 | 多会话管理 | P1 | E2E | 手工 |
| REQ-D-15 | 基础设置 | P1 | E2E | 手工 |
| REQ-D-16 | 品牌自定义 | P2 | 单元 + 集成 | 自动化 |
| REQ-D-17 | WebSocket 通道配置 | P0 | 单元 + 集成 | 自动化 |
| REQ-D-18 | 安全认证 | P0 | 单元 + 集成 + E2E | 自动化 + 手工 |
| REQ-D-19 | Gateway 命令增强 | P1 | 单元 + 集成 | 自动化 |
| REQ-D-20 | 统一会话模式 | P2 | 单元 | 自动化 |
| NFR-D-11 | WebUI 首屏加载 < 3s | P1 | 性能测试 | 手工 |
| NFR-D-12 | WebSocket 连接延迟 < 100ms | P1 | 性能测试 | 自动化 |
| NFR-D-13 | 流式输出延迟 < 200ms | P1 | 性能测试 | 手工 |
| NFR-D-14 | 工具调用兼容性 >= 99% | P1 | 集成 | 自动化 |
| NFR-D-15 | 安全默认 | P0 | 单元 + 集成 | 自动化 |
| NFR-D-16 | 向后兼容 | P0 | 单元 + 集成 + 回归 | 自动化 |

### 1.2 模块变更覆盖矩阵

| 变更文件 | 变更类型 | 测试入口 | 风险等级 |
|----------|---------|---------|---------|
| `src/core/config/manager.py` | 新增 get_websocket_config() | 单元测试 | 低 |
| `src/core/provider_adapter.py` | 新增 webui_enabled 参数 + _build_websocket_channel_config() | 单元 + 集成 | 中 |
| `src/cli/commands/gateway.py` | 新增 --webui 标志 + 启动信息 | 单元 + 集成 | 中 |
| `config.example.json` | 新增 websocket 配置节 | 文档校验 | 低 |

### 1.3 不做测试的范围

- nanobot-ai 原生 WebUI SPA 前端代码（由上游维护，RunFlowAgent 不修改）
- nanobot-ai WebSocketChannel 内部实现（由上游维护）
- nanobot-ai ChannelManager.discover_all() 的飞书通道发现逻辑（不在 v0.27.0 变更范围内）
- Agent 工具逻辑（v0.27.0 不修改 Agent 工具，变更范围外的回归由 v0.26.0 基线覆盖）

---

## 2. 测试层级

### 2.1 测试金字塔总览

| 层级 | 数量 | 主责 | 验收标准 |
|------|------|------|----------|
| 单元测试 | 44 个 (25 + 19) | 开发工程师主责，测试工程师校验 | 100% 通过 |
| 集成测试 | 25 个 | 测试工程师主责 | 100% 通过 (nanobot-ai 环境) |
| E2E 测试 | 5 个场景 | 测试工程师主责 | P0 场景 100% 通过 |
| 回归测试 | 全量现有测试 | 测试工程师主责 | 无新增失败 |

### 2.2 单元测试详情

#### 2.2.1 ConfigManager WebSocket 配置读取 (test_websocket_config.py, 25 个)

| 分类 | 用例数 | 覆盖场景 |
|------|--------|---------|
| 配置文件读取 | 8 | 配置节存在/不存在/非法类型(非dict/list/None)/空dict/部分字段/额外字段/浅拷贝验证 |
| 环境变量覆盖 | 10 | NANOBOT_WS_ENABLED(true/yes/1/false/大小写) + HOST/PORT(含非法值)/TOKEN/TOKEN_SECRET 覆盖 + 无配置节时生效 + 全量覆盖 + 优先级验证 |
| 默认值与边界 | 5 | 无配置无环境变量 / 部分配置无环境变量 / 环境变量为部分配置补充字段 |
| --- | --- | --- |
| **合计** | **25** | **已执行，全部通过 (68 passed in 7.65s)** |

#### 2.2.2 ProviderAdapter WebSocket 配置构建 (test_provider_adapter.py, 19 个新增)

| 分类 | 用例数 | 覆盖场景 |
|------|--------|---------|
| WebSocket 通道配置构建 | 11 | webui_enabled + 空配置 / webui_disabled + config未启用 / webui_disabled + config启用 / webui_enabled + config启用 / 自定义配置值 / 安全配置默认值 / 安全配置自定义 / SSL默认值 / allow_from默认值 / 不影响已有通道 / 品牌字段默认值 |
| 完整构建链路 | 8 | 品牌字段自定义 + webui_enabled通道构建 + disabled不构建 + config启用时构建 + 安全配置传递 + 飞书通道不受影响 + model字段正确 + 缓存验证 |

**单元测试总计**: 44 个，全部通过。

### 2.3 集成测试详情

#### 2.3.1 WebUI 启动集成测试 (test_webui_startup.py, 25 个)

| 层级 | 用例数 | 覆盖场景 |
|------|--------|---------|
| 配置注入链路 | 6 | webui_enabled 生成 WebSocket 配置 / disabled 不生成 / host:port 从配置读取 / 默认值 / agents.defaults 品牌字段(自定义+默认) |
| ChannelManager 初始化 | 5 | 通道发现 / 类型验证 / 配置解析 / disabled 不包含 / 完整注入链路(RunnerProviderAdapter -> Config -> ChannelManager) |
| WebSocket 服务启动 | 6 | 端口监听 / HTTP GET 返回 WebUI SPA / token 认证连接 / 无 token 被拒绝 / 开放模式连接 / token 签发端点 |
| Agent 消息响应 | 4 | ready 事件 / 消息发布到 bus / envelope 格式消息 / new_chat 创建新会话 |
| 端到端链路 | 4 | CLI --webui 到 Adapter / Adapter 到 ChannelManager / 不带 --webui 不启用 / 完整 e2e (配置->连接->ready) |

**执行条件**: 需要 nanobot-ai + websockets + httpx 依赖，CI 中的 nanobot-ai 环境满足依赖但集成测试通过 `@pytest.mark.skipif` 条件跳过。本地开发环境可执行。

### 2.4 E2E 测试场景

| 编号 | 场景 | 对应需求 | 优先级 | 类型 |
|------|------|---------|--------|------|
| E2E-01 | 用户启动 `gateway start --webui` -> 浏览器访问 WebUI -> 发送对话 -> 收到流式回复 | REQ-D-11, REQ-D-13 | P0 | 手工 |
| E2E-02 | 用户在 WebUI 中调用 Agent 工具（如 `analysis vdot`）-> 工具正常执行 -> 结果在 WebUI 中展示 | REQ-D-12 | P0 | 手工 |
| E2E-03 | 用户配置 token 认证 -> 浏览器访问 -> 通过 token 连接 -> 对话正常 | REQ-D-18 | P0 | 手工 |
| E2E-04 | 用户在 WebUI 中创建/切换/删除会话 -> 会话管理正常 | REQ-D-14 | P1 | 手工 |
| E2E-05 | 用户在 WebUI 设置面板中切换 Model Presets -> 模型切换生效 | REQ-D-15 | P1 | 手工 |

**E2E 执行前提**：
1. 单元测试全部通过
2. 集成测试全部通过（nanobot-ai 环境）
3. I-01 (ruff format) 已修复
4. `nanobotrun gateway start --webui` 可正常启动

---

## 3. 准入准出标准

### 3.1 版本准入标准（进入测试阶段）

| 编号 | 准入条件 | 当前状态 | 验证方式 |
|------|---------|---------|---------|
| A-01 | 需求规格说明书 v12.1 已确认 | 已满足 | 文档已定稿 |
| A-02 | 架构设计说明书 v16.0.0 已确认 | 已满足 | 文档已定稿 |
| A-03 | 代码评审 "有条件通过" | 已满足 | 评审报告已有 |
| A-04 | 代码评审 I-01 (ruff format) 已修复 | 待修复 | `uv run ruff format --check` |
| A-05 | v0.26.0 底座升级已确认稳定 | 已满足 | v0.26.0 已发布 |
| A-06 | 开发自测通过 (单元测试 100% 通过) | 待验证 | `uv run pytest tests/unit/` |
| A-07 | mypy 类型检查通过 | 待验证 | `uv run mypy src/ --ignore-missing-imports` |
| A-08 | ruff check 通过 | 待验证 | `uv run ruff check src/ tests/` |

### 3.2 版本准出标准（放行进入发布环节）

| 编号 | 准出条件 | 量化指标 | 当前状态 |
|------|---------|---------|---------|
| B-01 | P0 级用例 100% 通过 | 44/44 单元 + 25/25 集成 | 单元已通过，集成待验证 |
| B-02 | P1 级用例 100% 通过 | 品牌字段 + Gateway 命令 + 向后兼容 | 单元已通过 |
| B-03 | 无致命/严重 bug | 致命=0, 严重=0 | 代码评审无 Critical |
| B-04 | 一般 bug 修复率 >= 90% | 代码评审 I-01 + I-02 已处理 | I-01 待修复 |
| B-05 | 核心业务流程全量闭环 | WebUI 启动 -> 连接 -> 对话 -> 工具调用 | 待 E2E 验证 |
| B-06 | 向后兼容零回归 | 不带 --webui 时现有功能完全不变 | 集成测试已覆盖 |
| B-07 | 安全默认验证通过 | 127.0.0.1 + token 认证默认启用 | 单元测试已覆盖 |
| B-08 | 全量回归测试通过 | 全量现有测试无新增失败 | 待执行 |

### 3.3 准出判定规则

准出必须同时满足 B-01 至 B-08 全部条件。任一条件不满足，测试报告标记为"**不通过**"，禁止放行进入发布环节，并明确告知用户与运维智能体。

**当前核心阻塞项**: 代码评审 I-01 (ruff format) 待修复。此问题修复后即可启动正式测试流程。

---

## 4. 测试用例清单（需求编号映射）

### 4.1 REQ-D-11: WebUI 启动 (P0)

| 用例ID | 用例名称 | 优先级 | 用例类型 | 所在文件 | 状态 |
|--------|---------|--------|---------|---------|------|
| UT-CM-01 | webui_enabled=True 时构建 WebSocket 通道配置 | P0 | 单元 | test_provider_adapter.py::test_webui_enabled_with_empty_config | 通过 |
| UT-CM-02 | webui_enabled=True + config enabled=True 双重启用 | P0 | 单元 | test_provider_adapter.py::test_webui_enabled_and_config_enabled | 通过 |
| IT-CI-01 | webui_enabled=True 时 Config 包含 websocket 通道 | P0 | 集成 | test_webui_startup.py::test_webui_enabled_produces_websocket_channel_config | 条件跳过 |
| IT-CM-01 | ChannelManager 发现 WebSocket 通道 | P0 | 集成 | test_webui_startup.py::test_channel_manager_discovers_websocket | 条件跳过 |
| IT-CM-02 | WebSocket 通道实例类型正确 | P0 | 集成 | test_webui_startup.py::test_channel_manager_websocket_is_correct_type | 条件跳过 |
| IT-WS-01 | WebSocket 服务在配置端口监听 | P0 | 集成 | test_webui_startup.py::test_websocket_server_listens_on_port | 条件跳过 |
| IT-WS-02 | HTTP GET 返回 WebUI SPA 页面 | P0 | 集成 | test_webui_startup.py::test_http_get_returns_webui_spa | 条件跳过 |
| IT-E2E-04 | 完整 e2e: 配置到 WebSocket 连接 ready | P0 | 集成 | test_webui_startup.py::test_full_e2e_webui_startup | 条件跳过 |
| E2E-01 | 手工: gateway start --webui -> 浏览器对话 | P0 | E2E | 手工执行 | 待执行 |

**小计**: 9 个测试用例 (8 自动化 + 1 手工)

### 4.2 REQ-D-12: 工具调用 (P0)

| 用例ID | 用例名称 | 优先级 | 用例类型 | 所在文件 | 状态 |
|--------|---------|--------|---------|---------|------|
| IT-AG-01 | WebSocket 连接后收到 ready 事件 (含 chat_id) | P0 | 集成 | test_webui_startup.py::test_websocket_receives_ready_event | 条件跳过 |
| IT-AG-02 | WebSocket 消息发布到 MessageBus | P0 | 集成 | test_webui_startup.py::test_websocket_message_published_to_bus | 条件跳过 |
| IT-AG-03 | envelope 消息格式 | P0 | 集成 | test_webui_startup.py::test_websocket_envelope_message | 条件跳过 |
| IT-AG-04 | new_chat envelope 创建新会话 | P0 | 集成 | test_webui_startup.py::test_websocket_new_chat_envelope | 条件跳过 |
| E2E-02 | 手工: WebUI 中调用 Agent 工具 | P0 | E2E | 手工执行 | 待执行 |

**小计**: 5 个测试用例 (4 自动化 + 1 手工)

### 4.3 REQ-D-13: 流式输出 (P0)

| 用例ID | 用例名称 | 优先级 | 用例类型 | 所在文件 | 状态 |
|--------|---------|--------|---------|---------|------|
| UT-CM-07 | streaming 默认值为 True | P0 | 单元 | test_provider_adapter.py::test_webui_enabled_with_empty_config (含 streaming=True 断言) | 通过 |
| UT-CM-08 | 自定义 streaming=False | P0 | 单元 | test_provider_adapter.py::test_custom_ws_config_values | 通过 |
| E2E-01 | 手工: WebUI 对话验证流式逐字展示 | P0 | E2E | 手工执行 (含在 E2E-01 中) | 待执行 |

**小计**: 3 个测试用例 (2 自动化 + 1 手工，手工合并在 E2E-01)

### 4.4 REQ-D-14: 多会话管理 (P1)

| 用例ID | 用例名称 | 优先级 | 用例类型 | 所在文件 | 状态 |
|--------|---------|--------|---------|---------|------|
| E2E-04 | 手工: WebUI 中创建/切换/删除会话 | P1 | E2E | 手工执行 | 待执行 |

**小计**: 1 个测试用例 (1 手工)

### 4.5 REQ-D-15: 基础设置 (P1)

| 用例ID | 用例名称 | 优先级 | 用例类型 | 所在文件 | 状态 |
|--------|---------|--------|---------|---------|------|
| E2E-05 | 手工: WebUI 设置面板中切换 Model Presets | P1 | E2E | 手工执行 | 待执行 |

**小计**: 1 个测试用例 (1 手工)

### 4.6 REQ-D-16: 品牌自定义 (P2)

| 用例ID | 用例名称 | 优先级 | 用例类型 | 所在文件 | 状态 |
|--------|---------|--------|---------|---------|------|
| UT-BR-01 | 品牌字段默认值 (bot_name/bot_icon) | P2 | 单元 | test_provider_adapter.py::test_brand_fields_default_values | 通过 |
| UT-BR-02 | 品牌字段自定义值 | P2 | 单元 | test_provider_adapter.py::test_brand_fields_custom_values | 通过 |
| IT-CI-05 | agents.defaults 品牌字段自定义 | P2 | 集成 | test_webui_startup.py::test_agents_defaults_contain_brand_fields | 条件跳过 |
| IT-CI-06 | agents.defaults 品牌字段默认值 | P2 | 集成 | test_webui_startup.py::test_agents_defaults_default_brand | 条件跳过 |

**小计**: 4 个测试用例 (4 自动化)

### 4.7 REQ-D-17: WebSocket 通道配置 (P0)

| 用例ID | 用例名称 | 优先级 | 用例类型 | 所在文件 | 状态 |
|--------|---------|--------|---------|---------|------|
| UT-WS-01 | websocket 配置节存在时正确读取 | P0 | 单元 | test_websocket_config.py::test_config_section_exists_with_values | 通过 |
| UT-WS-02 | 配置节不存在返回空 dict | P0 | 单元 | test_websocket_config.py::test_config_section_not_exists | 通过 |
| UT-WS-03 | 配置节为非 dict 类型防御 | P0 | 单元 | test_websocket_config.py::test_config_section_is_not_dict | 通过 |
| UT-WS-04 | 配置节为 list 类型防御 | P0 | 单元 | test_websocket_config.py::test_config_section_is_list | 通过 |
| UT-WS-05 | 配置节为 None 返回空 dict | P0 | 单元 | test_websocket_config.py::test_config_section_is_none | 通过 |
| UT-WS-06 | 配置节为空 dict 返回空 dict | P0 | 单元 | test_websocket_config.py::test_config_section_is_empty_dict | 通过 |
| UT-WS-07 | 部分配置只返回已配置字段 | P0 | 单元 | test_websocket_config.py::test_partial_websocket_config | 通过 |
| UT-WS-08 | 额外字段一并返回 | P0 | 单元 | test_websocket_config.py::test_websocket_config_with_extra_fields | 通过 |
| UT-WS-09 | 返回浅拷贝 | P0 | 单元 | test_websocket_config.py::test_returns_shallow_copy | 通过 |
| UT-CM-03 | 自定义配置值正确写入 | P0 | 单元 | test_provider_adapter.py::test_custom_ws_config_values | 通过 |
| IT-CI-02 | webui_enabled=False 时无 WebSocket 通道 | P0 | 集成 | test_webui_startup.py::test_webui_disabled_no_websocket_channel | 条件跳过 |
| IT-CI-03 | host/port 从 config.json 读取 | P0 | 集成 | test_webui_startup.py::test_websocket_config_host_port_from_runner_config | 条件跳过 |
| IT-CI-04 | 默认 host=127.0.0.1, port=8765 | P0 | 集成 | test_webui_startup.py::test_websocket_default_host_port | 条件跳过 |
| IT-CM-03 | WebSocketConfig 从 dict 配置正确解析 | P0 | 集成 | test_webui_startup.py::test_websocket_config_parsed_correctly | 条件跳过 |

**小计**: 14 个测试用例 (14 自动化)

### 4.8 REQ-D-18: 安全认证 (P0)

| 用例ID | 用例名称 | 优先级 | 用例类型 | 所在文件 | 状态 |
|--------|---------|--------|---------|---------|------|
| UT-SC-01 | 安全配置默认值 (token="" / requires_token=True) | P0 | 单元 | test_provider_adapter.py::test_security_config_defaults | 通过 |
| UT-SC-02 | 自定义安全配置 | P0 | 单元 | test_provider_adapter.py::test_security_config_custom_token | 通过 |
| UT-SC-03 | SSL 默认值为空字符串 | P0 | 单元 | test_provider_adapter.py::test_ssl_config_defaults | 通过 |
| UT-SC-04 | allow_from 默认值 ["*"] | P0 | 单元 | test_provider_adapter.py::test_allow_from_default | 通过 |
| UT-SC-05 | 安全配置传递到完整构建链路 | P0 | 单元 | test_provider_adapter.py::test_security_config_passed_to_websocket_channel | 通过 |
| IT-WS-03 | token 认证连接 | P0 | 集成 | test_webui_startup.py::test_websocket_connection_with_token | 条件跳过 |
| IT-WS-04 | 无 token 被拒绝 | P0 | 集成 | test_webui_startup.py::test_websocket_connection_without_token_rejected | 条件跳过 |
| IT-WS-05 | 开放模式无 token 连接 | P0 | 集成 | test_webui_startup.py::test_websocket_open_connection | 条件跳过 |
| IT-WS-06 | token 签发端点 | P0 | 集成 | test_webui_startup.py::test_token_issue_endpoint | 条件跳过 |
| IT-CM-04 | disabled 时 ChannelManager 不包含 WebSocket | P0 | 集成 | test_webui_startup.py::test_no_websocket_when_disabled | 条件跳过 |
| E2E-03 | 手工: token 认证配置 -> 浏览器连接 -> 对话 | P0 | E2E | 手工执行 | 待执行 |

**小计**: 11 个测试用例 (10 自动化 + 1 手工)

### 4.9 REQ-D-19: Gateway 命令增强 (P1)

| 用例ID | 用例名称 | 优先级 | 用例类型 | 所在文件 | 状态 |
|--------|---------|--------|---------|---------|------|
| UT-CM-04 | webui_enabled=False 且 config 未启用不构建 | P1 | 单元 | test_provider_adapter.py::test_webui_disabled_config_not_enabled | 通过 |
| UT-CM-05 | webui_enabled=False 但 config 启用仍构建 | P1 | 单元 | test_provider_adapter.py::test_webui_disabled_but_config_enabled | 通过 |
| IT-E2E-01 | --webui 标志传递到 Adapter | P1 | 集成 | test_webui_startup.py::test_cli_webui_flag_to_adapter_config | 条件跳过 |
| IT-E2E-02 | Adapter Config 到 ChannelManager | P1 | 集成 | test_webui_startup.py::test_adapter_config_to_channel_manager | 条件跳过 |
| IT-E2E-03 | 不带 --webui 不启用 WebSocket | P1 | 集成 | test_webui_startup.py::test_gateway_start_without_webui_no_websocket | 条件跳过 |

**小计**: 5 个测试用例 (5 自动化)

### 4.10 REQ-D-20: 统一会话模式 (P2)

| 用例ID | 用例名称 | 优先级 | 用例类型 | 所在文件 | 状态 |
|--------|---------|--------|---------|---------|------|
| UT-BR-03 | unified_session 默认 False | P2 | 单元 | test_provider_adapter.py::test_brand_fields_default_values | 通过 |
| UT-BR-04 | unified_session 自定义 True | P2 | 单元 | test_provider_adapter.py::test_brand_fields_custom_values | 通过 |

**小计**: 2 个测试用例 (2 自动化)

### 4.11 测试用例总览

| 统计项 | 数值 |
|--------|------|
| 自动化用例总数 | 55 (44 单元 + 25 集成，部分集成与单元有交叉覆盖) |
| 手工 E2E 场景 | 5 |
| P0 级别用例 | 39 |
| P1 级别用例 | 10 |
| P2 级别用例 | 6 |
| 已通过 (单元) | 44/44 (100%) |
| 待执行 (集成 + E2E) | 25 集成 (条件跳过) + 5 E2E |

---

## 5. 非功能需求测试方案

### 5.1 NFR-D-11: WebUI 首屏加载 < 3s

| 测试方法 | 详细步骤 |
|----------|---------|
| 测量工具 | 浏览器 DevTools Network 面板 + Performance API |
| 测试步骤 | 1. 启动 `gateway start --webui` 2. 打开浏览器无痕模式 3. 访问 `http://127.0.0.1:8765` 4. 记录 DOMContentLoaded 和 Load 事件时间 |
| 通过标准 | 首屏加载时间 < 3s (本地网络，冷启动) |
| 执行环境 | 本地开发机，nanobot-ai wheel 包内置 WebUI SPA |
| 风险 | WebUI SPA 随 wheel 本地分发，无网络延迟，预期远 < 3s |

### 5.2 NFR-D-12: WebSocket 连接延迟 < 100ms

| 测试方法 | 详细步骤 |
|----------|---------|
| 测量工具 | Python time.monotonic() 或 pytest-benchmark |
| 测试步骤 | 在 `test_websocket_connection_with_token` 中增加计时：从 `websockets.connect()` 调用开始到收到 `ready` 事件结束 |
| 通过标准 | 连接建立延迟 < 100ms (本地回环) |
| 自动化 | 可在集成测试中增加 `@pytest.mark.benchmark` 装饰器 |
| 风险 | 本地 127.0.0.1 回环延迟极低，预期 < 10ms |

### 5.3 NFR-D-13: 流式输出延迟 < 200ms

| 测试方法 | 详细步骤 |
|----------|---------|
| 测量工具 | 浏览器 DevTools WebSocket 帧时间戳 |
| 测试步骤 | 1. WebUI 中发送消息 2. 在 Network -> WS 面板记录每个 delta 帧的时间戳 3. 计算相邻 delta 帧的最大间隔 |
| 通过标准 | 最大 delta 间隔 < 200ms |
| 执行方式 | 手工测试，浏览器 DevTools 直接观察 |
| 风险 | 取决于 LLM Provider 响应速度，本地 WebSocket 转发开销极低 |

### 5.4 NFR-D-14: 工具调用兼容性 >= 99%

| 测试方法 | 详细步骤 |
|----------|---------|
| 测试策略 | WebUI 中逐一调用所有 Agent 工具，验证返回结果与 CLI 一致 |
| 工具清单 | data import/stats, analysis vdot/load/hrv, plan create/status, evolution history/status, model list 等 |
| 通过标准 | 所有工具正常调用，结果与 CLI 一致，成功率 >= 99% |
| 执行方式 | 手工 (E2E-02) + 自动化回归 (复用现有工具测试) |
| 原理 | WebSocket 通道共享同一 AgentLoop，工具注册机制不变，理论上 100% 兼容 |

### 5.5 NFR-D-15: 安全默认

| 测试方法 | 详细步骤 |
|----------|---------|
| 验证项 | 1. host 默认值 127.0.0.1 (仅本地) 2. token 认证默认启用 (websocket_requires_token=True) 3. 无 token 时连接被拒绝 |
| 通过标准 | 三项全部满足 |
| 自动化 | UT-SC-01 已覆盖默认值断言 + IT-WS-04 覆盖无 token 拒绝 |
| 状态 | 已通过 |

### 5.6 NFR-D-16: 向后兼容

| 测试方法 | 详细步骤 |
|----------|---------|
| 验证项 | 1. 不带 --webui 时行为与 v0.26.0 一致 2. config.json 无 websocket 节时不影响现有功能 3. 飞书通道不受影响 4. 现有 CLI 命令不受影响 |
| 通过标准 | 四项全部满足 |
| 自动化 | UT-CM-09(不影响飞书) + IT-E2E-03(不带--webui) + UT-CM-02(无websocket节) |
| 全量回归 | 必须执行 `uv run pytest tests/` 全量测试 |
| 状态 | 单元测试已通过，全量回归待执行 |

---

## 6. 风险评估

### 6.1 测试覆盖风险

| 编号 | 风险 | 等级 | 影响 | 缓解措施 |
|------|------|------|------|----------|
| R-01 | **集成测试条件跳过** | 中 | 25 个集成测试依赖 nanobot-ai 运行时，CI 环境可能跳过 | 本地开发环境必须执行集成测试；CI 配置 `uv sync --all-extras` 包含 nanobot-ai |
| R-02 | **E2E 测试依赖真实 LLM** | 中 | 手工 E2E 需要真实 LLM API 调用，受网络/费用影响 | 可与单元测试并行执行；提前准备测试用 API key |
| R-03 | **Gateway CLI 变更未经端到端验证** | 低 | `gateway start --webui` 的整体启动流程仅 unit/integration mock 覆盖 | 额外执行一次真实 `gateway start --webui` 的手工验证 |
| R-04 | **代码评审 I-01 ruff format 未修复** | 高 | 阻塞合并，代码格式不符合项目规范 | 运行 `uv run ruff format` 一键修复 |
| R-05 | **AppConfig Schema 未包含 websocket 字段** | 低 | 配置验证不完整，用户错误类型不会被捕获 | nanobot-ai 的 WebSocketConfig 最终会校验，实际风险可控；建议后续迭代补充 |
| R-06 | **token_issue_path 默认值与架构设计不一致** | 低 | 架构设计为 "/token"，实现可能为空字符串 "" | 代码评审 M-03 已标注，修复方式为将默认值改为 "/token" |

### 6.2 架构风险

| 编号 | 风险 | 等级 | 影响 | 缓解措施 |
|------|------|------|------|----------|
| R-07 | **WebSocket 通道与飞书通道资源竞争** | 低 | 两个通道同时运行时 Agent 资源争用 | nanobot-ai AgentLoop 天然支持多通道；单用户场景下并发极低 |
| R-08 | **上游 WebUI 版本变更** | 低 | nanobot-ai WebUI 更新影响 RunFlowAgent | 锁定 nanobot-ai 版本；v0.27.0 仅配置驱动，不修改前端 |
| R-09 | **WebSocket 通道安全配置不当** | 中 | 未配置 token 时存在未授权访问风险 | 默认仅监听 127.0.0.1；token 认证默认启用；非本地访问强制要求 token |

### 6.3 需额外关注的测试场景

1. **环境变量覆盖与 config.json 的双重控制冲突**: `NANOBOT_WS_ENABLED=true` 与 config.json `enabled: false` 的交互 -- 已通过 UT-WS 环境变量覆盖测试覆盖
2. **端口占用场景**: WebSocket 端口 (8765) 已被占用时 `gateway start --webui` 的报错行为 -- 当前测试未覆盖，建议手工验证
3. **config.json websocket 配置节部分字段异常类型**: 如 `port: "not_a_number"` -- 单元测试已覆盖非法值回退，但集成层未验证 nanobot WebSocketConfig 对此的处理
4. **大数据量工具调用**: WebUI 中调用返回大量数据（如 `analysis load --days 365`），验证 `max_message_bytes` (36MB) 限制是否合理 -- 边界场景，建议手工验证
5. **非本地访问安全警告**: 配置 `host: "0.0.0.0"` 时 CLI 启动信息是否显示安全警告 -- 代码评审已验证 gateway.py 有此逻辑，集成测试未专门覆盖

---

## 7. 测试环境要求

### 7.1 软件依赖

| 依赖 | 版本要求 | 用途 |
|------|---------|------|
| Python | >= 3.11, < 3.13 | 运行环境 |
| nanobot-ai | latest (wheel 包) | WebUI / WebSocket Channel 运行时 |
| websockets | latest | 集成测试 WebSocket 客户端 |
| httpx | latest | 集成测试 HTTP 客户端 (WebUI SPA 请求) |
| pytest | latest | 测试框架 |
| pytest-asyncio | latest | 异步集成测试 |
| ruff | latest | 代码格式与 lint 检查 |
| mypy | latest | 类型检查 |
| uv | latest | 包管理器 |

### 7.2 配置文件准备

```json
// config.json 新增 websocket 配置节（测试用最小配置）
{
  "websocket": {
    "enabled": true,
    "host": "127.0.0.1",
    "port": 8765,
    "token": "",
    "token_issue_path": "/token",
    "websocket_requires_token": false,
    "streaming": true,
    "allow_from": ["*"]
  }
}
```

### 7.3 测试数据准备

| 数据项 | 说明 |
|--------|------|
| FIT 测试文件 | 用于工具调用测试，与现有测试数据一致 |
| LLM API Key | 用于 E2E 手工测试的真实 API key (环境变量 NANOBOT_LLM_API_KEY) |
| 测试端口 | 18765 (集成测试专用，避免与开发环境 8765 冲突) |

### 7.4 测试执行命令

```bash
# 1. 代码格式化 (修复 I-01)
uv run ruff format src/core/config/manager.py src/core/provider_adapter.py src/cli/commands/gateway.py

# 2. Lint 检查
uv run ruff check src/ tests/

# 3. 类型检查
uv run mypy src/ --ignore-missing-imports

# 4. 单元测试
uv run pytest tests/unit/config/test_websocket_config.py tests/unit/core/test_provider_adapter.py -v

# 5. 集成测试 (需要 nanobot-ai + websockets + httpx)
uv run pytest tests/integration/test_webui_startup.py -v

# 6. 全量回归测试
uv run pytest tests/ -v

# 7. 手工 E2E
nanobotrun gateway start --webui
# 浏览器访问 http://127.0.0.1:8765
```

---

## 8. 测试执行计划

### 8.1 阶段划分

| 阶段 | 任务 | 预估工时 | 状态 |
|------|------|---------|------|
| 第1步 | 修复 I-01 (ruff format) | 0.1h | 待执行 |
| 第2步 | 执行 lint + type check 验证 | 0.1h | 待执行 |
| 第3步 | 执行单元测试 (44 个) | 0.1h | 已通过 |
| 第4步 | 执行集成测试 (25 个) | 0.5h | 待执行 |
| 第5步 | 执行全量回归测试 | 0.5h | 待执行 |
| 第6步 | 执行手工 E2E (5 个场景) | 1.5h | 待执行 |
| 第7步 | bug 修复 + 回归验证 | 视情况 | 待定 |
| 第8步 | 输出测试报告 | 0.5h | 待执行 |

### 8.2 执行顺序

```
I-01修复 -> lint/typecheck -> 单元测试 -> 集成测试 -> 全量回归 -> 手工E2E -> 测试报告
```

---

## 9. 测试规范引用

| 规范 | 路径 | 适用场景 |
|------|------|---------|
| 单元测试示例 | `docs/test/test_templates/单元测试示例.md` | 新增单元测试编写 |
| 集成测试示例 | `docs/test/test_templates/集成测试示例.md` | 新增集成测试编写 |
| E2E 测试示例 | `docs/test/test_templates/E2E测试示例.md` | E2E 测试编写 |
| Bug 提交模板 | `docs/test/test_templates/Bug提交模板.md` | Bug 报告提交 |
| 轮次测试报告模板 | `docs/test/test_templates/轮次测试报告模板.md` | 测试报告输出 |
| 测试命令参考 | `docs/test/test_templates/测试命令参考.md` | 常用测试命令 |

---

## 附录A：代码评审问题状态追踪

| 编号 | 问题 | 严重级别 | 修复状态 | 验证方式 |
|------|------|---------|---------|---------|
| I-01 | ruff format 格式化未通过 | Important | **待修复** | `uv run ruff format --check` |
| I-02 | AppConfig Schema 未包含 websocket 字段 | Important | 已知，后续迭代 | - |
| M-01 | WebSocket 环境变量覆盖逻辑重复 | Minor | 已知 | - |
| M-02 | gateway.py 重复调用 get_websocket_config() | Minor | 已知 | - |
| M-03 | token_issue_path 默认值与架构设计不一致 | Minor | 已知 | - |
| M-04 | config.example.json 使用 _comment 后缀 | Minor | 已知 | - |
| M-05 | gateway.py 条件判断过长 | Minor | 已知 | - |

---

## 附录B：变更记录

| 版本 | 日期 | 变更内容 |
|------|------|---------|
| v1.0 | 2026-05-27 | 初始版本: 基于需求 v12.1 §5.3 + 架构 v16.0.0 §10 + 代码评审报告 + 现有 69 个测试用例分析制定 |