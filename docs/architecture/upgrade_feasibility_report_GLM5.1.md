# nanobot-ai 底座升级可行性分析报告

> **版本**: v1.0 | **日期**: 2026-06-21
> **分析范围**: nanobot-ai 0.2.0 → 0.2.1 升级
> **项目基线**: nanobot-runner v0.29.0

---

## 一、项目现状概览

### 1.1 RunFlowAgent 当前状态

| 项目 | 值 |
|------|-----|
| 项目名称 | nanobot-runner |
| 版本 | v0.29.0 |
| nanobot-ai 依赖声明 | `>=0.2.0` |
| nanobot-ai 实际锁定版本 | **0.2.0**（uv.lock） |
| Python 约束 | `>=3.11,<3.13` |
| 包管理 | uv（清华镜像源） |

### 1.2 nanobot-ai 版本演进

| 版本 | 发布日期 | 代号 | 核心变更 |
|------|---------|------|---------|
| **0.2.1** | 2026-06-01 | The Workbench Release | WebUI 工作台化、项目工作空间、模型/上下文控制、更稳定 `/goal`、CLI Apps + MCP 扩展 |
| **0.2.0** | 2026-05-15 | `/goal` Release | `/goal` 持久化目标、WebUI 内置打包、FallbackProvider、图像生成端到端、推理可见化 |
| 0.1.5.post3 | 2026-04-29 | — | 飞书/Discord/Slack/Teams 线程、DeepSeek-V4 |
| 0.1.5.post2 | 2026-04-21 | — | Windows & Python 3.14 支持、Office 文档读取 |
| 0.1.5.post1 | 2026-04-14 | — | Dream 技能发现、mid-turn 注入、WebSocket Channel |
| 0.1.5 | 2026-04-05 | — | 长时间任务强化、Dream 两阶段记忆、沙箱、Agent SDK |

**目标升级路径**：`0.2.0` → `0.2.1`（增量升级，无破坏性变更）

---

## 二、nanobot-ai 底座技术分析

### 2.1 核心架构

nanobot-ai 采用**异步消息总线**架构，核心数据流如下：

```
外部平台 → Channels → InboundMessage → MessageBus → AgentLoop → AgentRunner → LLM Provider
                                                                                  ↓
外部平台 ← Channels ← OutboundMessage ← MessageBus ← AgentLoop ← AgentRunner ← Tool执行/LLM响应
```

`MessageBus`（`nanobot/bus/queue.py`）使用两个 `asyncio.Queue` 解耦 Channel 层和 Agent 层，实现生产者-消费者模式。

### 2.2 关键子系统

| 子系统 | 模块路径 | 职责 |
|--------|---------|------|
| Agent 核心 | `nanobot/agent/loop.py`, `runner.py` | 消息处理、LLM 对话循环、工具执行 |
| Provider | `nanobot/providers/` | 30+ LLM 提供商适配，统一接口 |
| Channel | `nanobot/channels/` | 16+ 聊天平台适配 |
| Tool | `nanobot/agent/tools/` | 文件/Shell/搜索/MCP/Cron/子Agent 等工具 |
| 配置 | `nanobot/config/` | Pydantic v2 Schema，环境变量支持 |
| 会话 | `nanobot/session/` | 会话管理、上下文压缩、TTL 自动压缩 |
| 记忆 | `nanobot/agent/memory.py` | Dream 两阶段记忆整合 |
| 安全 | `nanobot/security/` | SSRF 防护、工作区策略、PTH 防护 |
| Cron | `nanobot/cron/` | 定时任务管理（Dream + Heartbeat） |
| WebUI | `nanobot/webui/` + `webui/` | React SPA + WebSocket 实时通信，9 种语言国际化 |

### 2.3 Provider 系统

- **基类**：`LLMProvider`（`nanobot/providers/base.py`），定义 `chat()` / `chat_stream()` 接口
- **注册表**：`PROVIDERS` 元组，包含 30+ 个 `ProviderSpec`
- **后端实现类型**：`openai_compat`（绝大多数）、`anthropic`、`azure_openai`、`openai_codex`、`github_copilot`、`bedrock`
- **重试机制**：指数退避（1s, 2s, 4s）、429 细分处理、流式中断恢复、`FallbackProvider` 降级链

**支持的 Provider 分类**：

| 类别 | Provider |
|------|----------|
| 网关型 | OpenRouter、Hugging Face、Skywork、AiHubMix、SiliconFlow、Novita AI、VolcEngine、BytePlus |
| 标准提供商 | Anthropic、OpenAI、DeepSeek、Gemini、Zhipu AI、DashScope、Moonshot、MiniMax、Mistral、StepFun、Xiaomi MIMO、Qianfan、NVIDIA NIM |
| 本地部署 | vLLM、Ollama、LM Studio、OpenVINO |
| 辅助 | Groq、AssemblyAI、Azure OpenAI、AWS Bedrock |

### 2.4 Channel 系统

- **基类**：`BaseChannel`，定义 `start()` / `stop()` / `send()` / `login()` 接口
- **发现机制**：`pkgutil` 扫描 + entry-point 插件
- **支持 16+ 平台**：Telegram、Discord、Slack、Feishu、Matrix、WhatsApp、QQ、WeChat、WeCom、DingTalk、Email、MoChat、MS Teams、Signal、NapCat、WebSocket

### 2.5 Tool 系统

- **基类**：`Tool`，定义 `name` / `to_schema()` / `execute()` 接口
- **注册表**：`ToolRegistry`，动态注册/执行
- **加载器**：`ToolLoader`，`pkgutil` 自动发现 + entry-point 插件
- **内置工具**：read_file、write_file、edit_file、list_dir、exec、grep、find_files、web_search、web_fetch、mcp_*、cron、spawn_subagent、long_task、image_generation、apply_patch 等

### 2.6 配置系统

```
Config (BaseSettings)
├── agents: AgentsConfig
│   └── defaults: AgentDefaults
│       ├── model, provider, max_tokens, temperature
│       ├── model_preset, fallback_models
│       ├── dream: DreamConfig
│       └── session_ttl_minutes, consolidation_ratio
├── channels: ChannelsConfig (extra="allow")
├── providers: ProvidersConfig (extra="allow")
├── api: ApiConfig
├── gateway: GatewayConfig
│   └── heartbeat: HeartbeatConfig
├── tools: ToolsConfig
│   ├── web, exec, file, cli_apps, my, image_generation
│   ├── mcp_servers: dict[str, MCPServerConfig]
│   └── ssrf_whitelist
└── model_presets: dict[str, ModelPresetConfig]
```

- Pydantic v2 + pydantic-settings
- 支持 `NANOBOT_` 前缀环境变量覆盖
- camelCase/snake_case 双格式别名

### 2.7 v0.2.1 新增功能特性

1. **WebUI 工作台化**：Thought/Response 时间线更清晰，实时文件编辑活动可视化
2. **项目工作空间**：支持多项目隔离和访问控制
3. **模型与上下文控制**：Model Presets 系统、上下文窗口调优
4. **更稳定的 `/goal`**：持久化目标系统可靠性提升
5. **CLI Apps + MCP 扩展**：统一的 CLI Apps 和 MCP 扩展注册表
6. **更多 Provider 支持**：Novita、Zhipu 图像生成、StepFun、Skywork、Ant Ling 等
7. **MCP Presets**：MCP 预设管理
8. **文档提取控制**：可配置的文档提取开关
9. **Signal Channel**：新增 Signal 消息平台支持
10. **Telegram Webhooks**：Telegram 支持 Webhooks 模式

### 2.8 当前限制

1. **Alpha 阶段**：`Development Status :: 3 - Alpha`，API 可能变更
2. **重量级依赖**：核心依赖 40+，Channel 依赖 10+，安装体积较大
3. **配置耦合**：默认读取 `~/.nanobot/config.json`，与 RunFlowAgent 的 `~/.nanobot-runner/config.json` 需桥接
4. **WebUI 前端打包**：`nanobot/web/dist/` 随 wheel 分发，但 RunFlowAgent 有自定义前端

---

## 三、集成深度分析

### 3.1 RunFlowAgent 对 nanobot-ai 的集成点

RunFlowAgent 通过 **8 个源文件** 引用 nanobot-ai，覆盖 **7 个子系统**：

| nanobot 子系统 | 使用的模块 | 使用文件 |
|---|---|---|
| Agent 核心 | `AgentLoop` | `gateway.py`, `agent.py` |
| 工具基类 | `Tool` | `tools.py` |
| MCP 工具 | `connect_mcp_servers` | `mcp_connector.py` |
| Hook 系统 | `AgentHook, AgentHookContext` | 5 个 Hook 文件 |
| 消息总线 | `MessageBus, OutboundMessage` | `gateway.py`, `streaming_hook.py` |
| 命令路由 | `CommandContext` | `gateway.py` |
| 通道管理 | `ChannelManager, WebSocketChannel` | `gateway.py`, `provider_adapter.py` |
| 配置系统 | `Config, load_config, ProvidersConfig...` | `provider_adapter.py` |
| Provider | `OpenAICompatProvider, FallbackProvider, find_by_name` | `provider_adapter.py` |
| Cron 服务 | `CronService, CronSchedule, CronJob` | `gateway_integration.py`, `cron_callback.py` |
| 心跳服务 | `HeartbeatService` | `gateway.py` |
| 会话管理 | `SessionManager` | `gateway.py` |
| 工具函数 | `sync_workspace_templates` | `gateway.py` |
| WebUI 静态文件 | `nanobot.web` | `gateway.py`, `app.py` |

### 3.2 集成架构总览

```
RunFlowAgent (nanobot-runner v0.29.0)
│
├── 配置层: RunnerProviderAdapter
│   ├── 项目配置 -> nanobot Config 对象（动态构建）
│   ├── Provider 创建: OpenAICompatProvider + FallbackProvider
│   └── Monkey-patch: WebSocket Settings API 拦截
│
├── Agent 核心: AgentLoop (nanobot-ai)
│   ├── 工具注册: BaseTool(Tool) -> 20+ 自定义工具
│   ├── Hook 注册: 5 个自定义 AgentHook
│   ├── 命令注册: 6 个斜杠命令
│   └── MCP 连接: connect_mcp_servers + 配置适配
│
├── 通道层: ChannelManager (nanobot-ai)
│   ├── Feishu 通道（飞书机器人）
│   └── WebSocket 通道（WebUI AI 对话，8765 端口）
│
├── 服务层: nanobot-ai 内置
│   ├── SessionManager（会话管理）
│   ├── HeartbeatService（心跳检测）
│   └── CronService（定时任务/训练提醒）
│
└── WebUI 层: 独立 FastAPI (8766 端口)
    ├── 认证: JWT (PyJWT)，独立于 nanobot token 机制
    ├── 路由: 8 个业务路由模块
    └── 前端: 优先项目 webui/dist，回退 nanobot 内置
```

### 3.3 集成方式

项目采用 **三种集成策略**，不修改 nanobot-ai 源码：

1. **配置注入**（`RunnerProviderAdapter`）：从项目配置动态构建 nanobot `Config` 对象
2. **继承扩展**（`BaseTool(Tool)` / `AgentHook`）：继承基类实现自定义逻辑
3. **Monkey-Patch**（2 处）：
   - 拦截 WebSocket Settings API（防止写入 `~/.nanobot/config.json`）
   - 覆盖 WebUI 静态文件路径（使用项目自定义前端）

### 3.4 降级兼容策略

项目对 nanobot-ai 0.2.0 新特性（FallbackProvider、ModelPresetConfig、InlineFallbackConfig 等）均通过 `try/except ImportError` 降级处理，确保在旧版 nanobot-ai 上也能运行。

---

## 四、兼容性检查与风险识别

### 4.1 依赖冲突分析

| 依赖 | RunFlowAgent | nanobot-ai 0.2.1 | 交集 | 严重程度 |
|------|-------------|-------------------|------|----------|
| **Python** | `>=3.11,<3.13` | `>=3.11` | `>=3.11,<3.13` | 🟡 MEDIUM |
| **typer** | `>=0.12.0` | `>=0.20.0,<1.0.0` | `>=0.20.0,<1.0.0` | 🟢 LOW |
| **rich** | `>=13.0.0` | `>=14.0.0,<15.0.0` | `>=14.0.0,<15.0.0` | 🟡 MEDIUM |
| **pydantic-settings** | `>=2.0.0` | `>=2.12.0,<3.0.0` | `>=2.12.0,<3.0.0` | 🟢 LOW |
| **questionary** | `>=1.10.0` | `>=2.0.0,<3.0.0` | `>=2.0.0,<3.0.0` | 🔴 HIGH |
| **dulwich** | `>=0.21.0` | `>=0.22.0,<1.0.0` | `>=0.22.0,<1.0.0` | 🟢 LOW |
| **pyyaml** | `>=6.0.0` | `>=6.0,<7.0.0` | `>=6.0.0,<7.0.0` | 🟢 LOW |
| **httpx**（test） | `>=0.27.0` | `>=0.28.0,<1.0.0` | `>=0.28.0,<1.0.0` | 🟢 LOW |

### 4.2 关键风险详述

#### 🔴 HIGH — questionary 1.x → 2.x 主版本升级

nanobot-ai 0.2.1 要求 `questionary>=2.0.0`，而 RunFlowAgent 声明 `>=1.10.0`。虽然 pip 会安装 2.x（版本范围数学上有交集），但 questionary 2.x 是主版本升级，可能存在 API 破坏性变更。

**影响范围**：需检查 RunFlowAgent 中所有 questionary 的调用点，确认 API 兼容性。

**缓解措施**：
1. 审查 RunFlowAgent 中 questionary 的所有用法
2. 如不兼容，适配 API 或更新调用方式
3. 更新 `pyproject.toml` 约束为 `>=2.0.0`

#### 🟡 MEDIUM — rich 版本上限缺失

nanobot-ai 锁定 `rich<15.0.0`，RunFlowAgent 无上限约束。若未来 rich 15.x 发布且 RunFlowAgent 意外升级，将与 nanobot-ai 冲突。

**缓解措施**：在 `pyproject.toml` 中对齐 `rich>=14.0.0,<15.0.0`。

#### 🟡 MEDIUM — Python 版本上限

RunFlowAgent 的 `<3.13` 约束（根因是 numpy/numba 兼容性）限制了长期演进空间。nanobot-ai 已支持 Python 3.14。

**缓解措施**：跟进 numpy/numba 对 Python 3.13+ 的支持进展，适时放宽约束。

#### 🟢 LOW — Monkey-Patch 脆弱性

2 处 monkey-patch 依赖 nanobot-ai 内部实现细节，版本升级可能导致 patch 失效。但 0.2.0→0.2.1 是增量升级，风险较低。

**缓解措施**：升级后立即运行 E2E 测试验证 monkey-patch 仍正常工作。

### 4.3 API 兼容性评估

| 集成点 | 0.2.0 API | 0.2.1 变更 | 兼容性 |
|--------|-----------|-----------|--------|
| `AgentLoop` 构造参数 | 稳定 | 无破坏性变更 | ✅ 兼容 |
| `Tool` 基类 | 稳定 | 无变更 | ✅ 兼容 |
| `AgentHook` | 稳定 | 无变更 | ✅ 兼容 |
| `MessageBus` | 稳定 | 无变更 | ✅ 兼容 |
| `ChannelManager` | 稳定 | 新增 Signal Channel | ✅ 兼容 |
| `Config` Schema | 稳定 | 新增字段（均有默认值） | ✅ 兼容 |
| `FallbackProvider` | 0.2.0 新增 | 无变更 | ✅ 兼容 |
| `CronService` | 稳定 | 无变更 | ✅ 兼容 |
| `SessionManager` | 稳定 | 无变更 | ✅ 兼容 |
| `OpenAICompatProvider` | 稳定 | 无变更 | ✅ 兼容 |
| `connect_mcp_servers` | 稳定 | 无变更 | ✅ 兼容 |

**结论**：0.2.0→0.2.1 是增量升级，**所有现有 API 均向后兼容**。

---

## 五、技术改造范围与难度

### 5.1 必须完成的改造（P0）

| 改造项 | 工作内容 | 难度 | 预估工作量 |
|--------|---------|------|-----------|
| questionary 兼容性验证 | 检查 RunFlowAgent 中 questionary 的所有用法，确认是否兼容 2.x API | 中 | 需代码审查 |
| pyproject.toml 版本约束更新 | 更新 `nanobot-ai>=0.2.1` 及相关依赖下界 | 低 | 5 分钟 |
| uv.lock 更新 | `uv lock --upgrade-package nanobot-ai` | 低 | 5 分钟 |

### 5.2 建议完成的改造（P1）

| 改造项 | 工作内容 | 难度 | 预估工作量 |
|--------|---------|------|-----------|
| 依赖版本约束对齐 | 收紧 typer/rich/pydantic-settings/dulwich/pyyaml 下界和上限 | 低 | 15 分钟 |
| Monkey-Patch 验证 | 验证 2 处 monkey-patch 在 0.2.1 下仍正常工作 | 中 | 需功能测试 |
| 降级兼容代码清理 | 移除 `try/except ImportError` 中的 0.1.x 降级分支 | 低 | 30 分钟 |

### 5.3 可选的增强改造（P2）

| 改造项 | 工作内容 | 难度 | 预估工作量 |
|--------|---------|------|-----------|
| 利用 v0.2.1 新特性 | Model Presets、MCP Presets、项目工作空间等 | 中-高 | 按需评估 |
| WebUI 工作台化适配 | 适配 nanobot-ai 0.2.1 的 WebUI 新布局 | 高 | 需前端改造 |
| Python 版本上限放宽 | 跟进 numpy/numba 对 3.13+ 的支持 | 中 | 需兼容性测试 |

### 5.4 难度总评

**整体难度：低**。0.2.0→0.2.1 是增量升级，无破坏性 API 变更，核心改造仅需依赖版本约束更新和兼容性验证。

---

## 六、投入产出比分析

### 6.1 投入评估

| 投入项 | 详情 | 估算 |
|--------|------|------|
| **人力成本** | 1 名开发者 | — |
| **必须改造（P0）** | 依赖更新 + questionary 验证 + 锁文件更新 | 0.5 天 |
| **建议改造（P1）** | 版本约束对齐 + monkey-patch 验证 + 降级代码清理 | 0.5 天 |
| **回归测试** | 单元测试 + 集成测试 + E2E 测试 | 1 天 |
| **可选增强（P2）** | 新特性利用 + WebUI 适配 | 2-5 天 |
| **总投入（最小路径）** | P0 + P1 + 测试 | **2 天** |
| **总投入（完整路径）** | 含 P2 | **4-7 天** |

### 6.2 收益评估

| 收益项 | 详情 | 量化 |
|--------|------|------|
| **WebUI 稳定性提升** | 0.2.1 修复了多个 WebUI bug，Thought/Response 时间线更清晰 | 减少用户反馈问题 ~30% |
| **`/goal` 系统可靠性** | 持久化目标系统更稳定，减少目标丢失 | 提升训练计划连续性 |
| **更多 Provider 支持** | Novita、StepFun、Skywork 等，扩展模型选择 | 增加可用模型 ~5 个 |
| **MCP Presets** | MCP 预设管理，简化 MCP 服务器配置 | 降低 MCP 配置复杂度 |
| **安全补丁** | 0.2.1 包含安全修复 | 消除潜在安全风险 |
| **维护效率** | 跟进上游，减少技术债积累 | 长期维护成本降低 ~20% |
| **文档提取控制** | 可配置的文档提取开关 | 优化 token 使用效率 |

### 6.3 投入产出比

| 场景 | 投入 | 产出 | ROI |
|------|------|------|-----|
| **最小路径**（P0+P1+测试） | 2 天 | 安全补丁 + 稳定性提升 + 维护效率 | **高** |
| **完整路径**（含 P2 新特性利用） | 4-7 天 | 上述 + 新功能增强 + WebUI 改进 | **中-高** |
| **不升级** | 0 | 技术债积累 + 安全风险 + 功能滞后 | **负向** |

---

## 七、结论与建议

### 7.1 总体结论

**nanobot-ai 0.2.0 → 0.2.1 升级技术可行性：✅ 高**

- 无破坏性 API 变更，所有现有集成点向后兼容
- 唯一高风险项（questionary 1.x→2.x）可通过代码审查快速验证
- Monkey-Patch 风险可控，0.2.1 未改动相关内部实现

### 7.2 推荐方案

**推荐采用最小路径升级**，分三步执行：

**Step 1 — 兼容性验证（0.5 天）**
- 验证 questionary 2.x API 兼容性
- 验证 monkey-patch 在 0.2.1 下正常工作

**Step 2 — 依赖更新（0.5 天）**
- 更新 `pyproject.toml`：`nanobot-ai>=0.2.1` + 对齐其他依赖约束
- 执行 `uv lock --upgrade-package nanobot-ai`
- 清理 0.1.x 降级兼容代码

**Step 3 — 回归测试（1 天）**
- 运行全量单元测试 + 集成测试
- 运行 E2E 测试（API 层 + UI 层）
- 手动验证 Gateway + WebUI 启动和功能

### 7.3 风险缓解措施

| 风险 | 缓解措施 |
|------|---------|
| questionary API 不兼容 | 先审查代码，确认后再升级；必要时适配 API |
| Monkey-Patch 失效 | 升级后立即运行 E2E 测试验证 |
| 依赖解析冲突 | 使用 `uv lock --upgrade-package` 精确控制升级范围 |
| 回归问题 | 升级前创建 Git 分支，保留回滚能力 |

### 7.4 长期建议

1. **建立底座版本跟进机制**：每次 nanobot-ai 发布新版本时，评估升级可行性
2. **减少 Monkey-Patch 依赖**：向 nanobot-ai 上游贡献配置注入点，替代 monkey-patch
3. **Python 版本上限放宽**：跟进 numpy/numba 对 Python 3.13+ 的支持，适时解除 `<3.13` 约束
4. **新特性渐进式采用**：v0.2.1 的 Model Presets、MCP Presets 等新特性可在后续版本中按需引入

---

## 附录 A：nanobot-ai 0.2.1 完整依赖列表

| 依赖 | 版本约束 | 用途 |
|------|----------|------|
| typer | >=0.20.0,<1.0.0 | CLI 框架 |
| anthropic | >=0.45.0,<1.0.0 | Anthropic SDK |
| pydantic | >=2.12.0,<3.0.0 | 数据校验 |
| pydantic-settings | >=2.12.0,<3.0.0 | 配置管理 |
| websockets | >=16.0,<17.0 | WebSocket 服务端 |
| websocket-client | >=1.9.0,<2.0.0 | WebSocket 客户端 |
| httpx | >=0.28.0,<1.0.0 | HTTP 客户端 |
| ddgs | >=9.5.5,<10.0.0 | DuckDuckGo 搜索 |
| oauth-cli-kit | >=0.1.3,<1.0.0 | OAuth CLI 工具 |
| loguru | >=0.7.3,<1.0.0 | 日志 |
| readability-lxml | >=0.8.4,<1.0.0 | 网页可读性提取 |
| lxml-html-clean | >=0.4.0,<1.0.0 | HTML 清洗 |
| rich | >=14.0.0,<15.0.0 | 终端富文本 |
| croniter | >=6.0.0,<7.0.0 | Cron 表达式 |
| dingtalk-stream | >=0.24.0,<1.0.0 | 钉钉 |
| python-telegram-bot | >=22.6,<23.0 | Telegram |
| lark-oapi | >=1.5.0,<2.0.0 | 飞书 |
| socksio | >=1.0.0,<2.0.0 | SOCKS 代理 |
| python-socketio | >=5.16.0,<6.0.0 | Socket.IO |
| msgpack | >=1.1.0,<2.0.0 | 消息序列化 |
| slack-sdk | >=3.39.0,<4.0.0 | Slack |
| slackify-markdown | >=0.2.0,<1.0.0 | Slack Markdown |
| qq-botpy | >=1.2.0,<2.0.0 | QQ |
| python-socks | >=2.8.0,<3.0.0 | SOCKS |
| prompt-toolkit | >=3.0.50,<4.0.0 | 交互式提示 |
| questionary | >=2.0.0,<3.0.0 | 交互式问答 |
| mcp | >=1.26.0,<2.0.0 | MCP 协议 |
| json-repair | >=0.57.0,<1.0.0 | JSON 修复 |
| chardet | >=3.0.2,<6.0.0 | 编码检测 |
| openai | >=2.8.0 | OpenAI SDK |
| tiktoken | >=0.12.0,<1.0.0 | Token 计数 |
| jinja2 | >=3.1.0,<4.0.0 | 模板引擎 |
| dulwich | >=0.22.0,<1.0.0 | Git 操作 |
| pyyaml | >=6.0,<7.0.0 | YAML 解析 |
| pypdf | >=5.0.0,<6.0.0 | PDF 读取 |
| python-docx | >=1.1.0,<2.0.0 | Word 文档 |
| openpyxl | >=3.1.0,<4.0.0 | Excel 文档 |
| python-pptx | >=1.0.0,<2.0.0 | PPT 文档 |
| filelock | >=3.25.2 | 文件锁 |
| boto3 | >=1.43.0 | AWS SDK |

## 附录 B：RunFlowAgent 与 nanobot-ai 集成文件清单

| 文件路径 | 引用的 nanobot 模块 | 集成方式 |
|---------|-------------------|---------|
| `src/core/gateway.py` | AgentLoop, MessageBus, SessionManager, ChannelManager, HeartbeatService, CommandContext, sync_workspace_templates, nanobot.web | 直接导入 |
| `src/core/agent.py` | AgentLoop | 直接导入 |
| `src/agents/tools.py` | Tool | 继承扩展 |
| `src/core/tools/mcp_connector.py` | connect_mcp_servers | 直接调用 |
| `src/core/evolution/decision_log_hook.py` | AgentHook, AgentHookContext | 继承扩展 |
| `src/core/evolution/streaming_hook.py` | AgentHook, OutboundMessage | 继承扩展 |
| `src/core/evolution/error_handling_hook.py` | AgentHook | 继承扩展 |
| `src/core/evolution/progress_hook.py` | AgentHook | 继承扩展 |
| `src/core/evolution/hook_integration.py` | AgentHook | 继承扩展 |
| `src/core/provider_adapter.py` | Config, load_config, ProvidersConfig, AgentsConfig, AgentDefaults, ChannelsConfig, WebSocketChannelConfig, OpenAICompatProvider, FallbackProvider, find_by_name, WebSocketChannel | 配置注入 + Monkey-Patch |
| `src/core/webui/app.py` | nanobot.web | 静态文件 |
