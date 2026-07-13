# 配置物理分离设计：消除 config.json → nanobot_config.json 转换层

> **日期**: 2026-07-14
> **版本**: v0.32.0
> **状态**: 评审修订版

---

## 1. 背景与动机

### 1.1 问题

v0.32.0 将 monkey-patch 替换为 `ConfigInjector` 后，引入了 `config.json` → `nanobot_config.json` 的运行时转换层。该转换层导致了多轮 bug：

- `extra='forbid'`：Runner 私有字段（`version`、`data_dir` 等）无法直接放入 nanobot 配置
- `ProviderConfig` schema：dict vs 对象、`base_url` vs `apiBase` 字段名不匹配
- Provider 同步遗漏：`model_presets` 中的其他 provider 的 `apiBase` 未同步

每次 nanobot-ai schema 变更，转换代码都必须同步修改，维护成本高且脆弱。

### 1.2 目标

消除运行时转换层，让 `nanobot_config.json` 成为 nanobot 配置的唯一真实源，用户直接按 nanobot 原生格式维护。v0.32.0 一次性完成迁移，不分多版本。

### 1.3 方案选择

采用 **方案 A：彻底分离** — `nanobot_config.json` 为 nanobot 唯一真实源，`config.json` 仅保留 Runner 专有字段。

排除方案：
- 方案 B（向导写两文件、保留双入口）：仍保留双文件认知负担
- 方案 C（合并为一个文件）：nanobot `extra='forbid'` 不允许 Runner 字段，技术不可行

---

## 2. 架构总览

### 2.1 文件职责划分

```
~/.nanobot-runner/
├── nanobot_config.json   ← nanobot 原生配置（唯一真实源）⚠️ 含敏感凭证
│                          providers / agents / channels / model_presets / tools / transcription
│                          用户直接编辑此文件管理 LLM、飞书、WebSocket、MCP 工具等
│                          ⚠️ 包含 apiKey、app_secret 等敏感信息，必须加入 .gitignore
│
├── config.json           ← Runner 专有配置（精简后）
│                          version / data_dir / timezone / auto_push_feishu / user_id
│
├── .env.local            ← 保留但不再包含 LLM/飞书凭证
│                          （如果未来有 Runner 专有环境变量可放这里，当前可为空）
│
├── data/                 ← 跑步数据（Parquet）
├── memory/               ← Agent 记忆
├── sessions/             ← 会话历史
└── cron/                 ← 定时任务
```

**安全策略**：`nanobot_config.json` 包含 `apiKey`、`app_secret` 等明文敏感凭证，**必须加入 `.gitignore`**，防止泄露到版本控制。初始化向导在生成 `nanobot_config.json` 时同步写入 `.gitignore` 条目。

### 2.2 数据流

```
nanobot_config.json  ──→  set_config_path  ──→  nanobot-ai 运行时
                  └──→  nanobot.config.loader.load_config()  ──→  ChannelManager (Config 对象)
                  └──→  ConfigManager.load_nanobot_config()  ──→  Runner 业务逻辑 (dict)
                  └──→  load_mcp_servers_config()  ──→  MCP 工具配置
config.json  ──→  ConfigManager.load_config()  ──→  Runner 业务逻辑（data_dir/timezone 等）
```

- `nanobot_config.json` 同时被 nanobot-ai（通过 `set_config_path`）和 Runner（通过 `load_nanobot_config()` / `load_config()`）读取
- `ChannelManager` 通过 `nanobot.config.loader.load_config()` 加载 nanobot `Config` 对象（Pydantic 模型）
- `config.json` 仅被 Runner 读取，只含 Runner 专有字段
- **不再有运行时转换**，`gateway.py` 启动时直接 `set_config_path(nanobot_config.json)`

### 2.3 核心变更摘要

| 模块 | 变更 |
|---|---|
| `ConfigManager` | 新增读取 `nanobot_config.json` 的能力；删除 LLM/WebSocket/WebUI 相关方法；精简 `_get_default_config()` 和 `ENV_KEY_MAPPING` |
| `RunnerProviderAdapter` | 删除 `_build_nanobot_config_from_runner()`、`save_nanobot_config()`、`_get_or_create_nanobot_config()`；改为从 `nanobot_config.json` 直接读取 |
| `ConfigInjector` | 删除 `build_nanobot_config()` 转换方法；`resolve_webui_dist()` 迁移至 `ConfigManager`，类整体删除 |
| `gateway.py` | 直接 `set_config_path()`，不再调用 `save_nanobot_config()`；`ChannelManager` 改为从 `nanobot_config.json` 加载 Config 对象；MCP 配置读取源改为 `nanobot_config.json` |
| `mcp_connector.py` | `load_mcp_servers_config()` 改为从 `nanobot_config.json` 的 `tools.mcpServers` 读取 |
| 初始化向导 (`src/core/init/`) | 直接生成 `nanobot_config.json`（nanobot 原生格式）；`_TRACKED_FILES` 排除 `nanobot_config.json`，写入 `.gitignore` |
| `env_manager.py` | 简化 `.env.local` 模板，移除 LLM/飞书凭证模板 |
| `system.py` | 新增 `migrate-config` 命令 |

---

## 3. nanobot_config.json 目标 Schema

### 3.1 顶层结构

```json
{
  "agents": { ... },
  "channels": { ... },
  "providers": { ... },
  "model_presets": { ... },
  "tools": { ... },
  "transcription": { ... }
}
```

> 注：nanobot 原生 schema 还支持 `api`、`gateway` 等顶层字段，但 Runner 不使用，向导不生成。用户如需可自行添加。

### 3.2 providers — LLM 供应商配置

用户在此直接配置每个供应商的 `apiKey` 和 `apiBase`：

```json
{
  "default": "custom",
  "custom": {
    "apiKey": "sk-xxx",
    "apiBase": "https://apihub.agnes-ai.com/v1",
    "apiType": "auto"
  },
  "nvidia": {
    "apiKey": "nvapi-xxx",
    "apiBase": "https://integrate.api.nvidia.com/v1",
    "apiType": "auto"
  }
}
```

迁移后 `apiKey` 直接写在配置文件中，`.env.local` 不再参与 LLM 凭证管理。

### 3.3 agents.defaults — Agent 核心配置

```json
{
  "model": "agnes-2.0-flash",
  "provider": "auto",
  "timezone": "Asia/Shanghai",
  "workspace": "~/.nanobot-runner",
  "botName": "nanobot-runner",
  "botIcon": "🍀",
  "fallbackModels": [
    {"model": "deepseek-ai/deepseek-v4-flash", "provider": "nvidia"}
  ]
}
```

### 3.4 channels.feishu — 飞书凭证

```json
{
  "enabled": true,
  "app_id": "cli_xxx",
  "app_secret": "xxx",
  "receive_id": "xxx",
  "receive_id_type": "user_id",
  "allowFrom": ["*"]
}
```

### 3.5 channels.websocket — WebSocket 配置

```json
{
  "enabled": true,
  "host": "127.0.0.1",
  "port": 8765,
  "token": "",
  "websocket_requires_token": true
}
```

### 3.6 tools.mcpServers — MCP 工具配置

替代原 config.json 的 `tools.mcp_servers`，格式不变。

### 3.7 model_presets — 模型预设

替代原 config.json 的 `model_presets` + `fallback_models`，格式为 nanobot 原生格式。

### 3.8 字段映射表

| config.json 原字段 | nanobot_config.json 目标位置 |
|---|---|
| `llm_provider` | `providers.default`（值为 provider 名称，如 `"custom"`；对应 provider 配置在 `providers.<该名称>` 中） |
| `llm_model` | `agents.defaults.model` |
| `llm_base_url` | `providers.<name>.apiBase` |
| `NANOBOT_LLM_API_KEY` (env) | `providers.<name>.apiKey` |
| `model_presets` | `model_presets` |
| `fallback_models` | `agents.defaults.fallbackModels` |
| `tools.mcp_servers` | `tools.mcpServers` |
| `tools.cli_apps` | `tools.cliApps` |
| `websocket.*` | `channels.websocket.*` |
| `websocket.bot_name` | `agents.defaults.botName` |
| `websocket.bot_icon` | `agents.defaults.botIcon` |
| 飞书 env 变量 | `channels.feishu.*` |

---

## 4. config.json 精简后 Schema

### 4.1 仅保留 5 个字段

```json
{
  "version": "0.32.0",
  "data_dir": "C:\\Users\\yecll\\.nanobot-runner\\data",
  "timezone": "Asia/Shanghai",
  "auto_push_feishu": true,
  "user_id": "default_user"
}
```

### 4.2 字段说明

| 字段 | 用途 | 为什么留在 config.json |
|---|---|---|
| `version` | Runner 配置文件版本号 | nanobot 不认识此字段，`extra='forbid'` 会报错 |
| `data_dir` | 跑步数据存储目录（Parquet） | Runner 专有，nanobot 无此概念 |
| `timezone` | 时区，用于训练数据时间显示、VDOT 计算等 | nanobot_config.json 的 `agents.defaults.timezone` 服务于 Agent 时间感知；Runner 的 timezone 服务于业务计算。两者独立配置，向导同时写入 |
| `auto_push_feishu` | 训练导入后是否自动推送飞书通知 | Runner 专有业务逻辑 |
| `user_id` | 用户标识，用于数据隔离 | Runner 专有 |

### 4.3 从 config.json 移除的字段

| 移除的字段 | 迁移目标 |
|---|---|
| `llm_provider` | `nanobot_config.json` → `providers.default` |
| `llm_model` | `nanobot_config.json` → `agents.defaults.model` |
| `llm_base_url` | `nanobot_config.json` → `providers.<name>.apiBase` |
| `fallback_models` | `nanobot_config.json` → `agents.defaults.fallbackModels` |
| `model_presets` | `nanobot_config.json` → `model_presets` |
| `tools.mcp_servers` | `nanobot_config.json` → `tools.mcpServers` |
| `tools.cli_apps` | `nanobot_config.json` → `tools.cliApps` |
| `websocket.*` | `nanobot_config.json` → `channels.websocket.*` + `agents.defaults.botName/botIcon` |

### 4.4 AppConfig Schema 更新

`src/core/config/schema.py` 中的 `AppConfig` 需要同步精简，移除对 `llm_*`、`model_presets`、`fallback_models`、`tools`、`websocket` 字段的验证。

### 4.5 关于 timezone 的双写说明

`timezone` 在两个文件中各有一份，但用途不同：
- `config.json` 的 `timezone` → Runner 业务计算（训练时间、VDOT 等）
- `nanobot_config.json` 的 `agents.defaults.timezone` → nanobot Agent 的时间感知

初始化向导会同时写入两个文件，用户修改时只需改一处即可（建议改 `config.json`，因为 Runner 业务更依赖它）。这不是"同步"问题，因为 nanobot 的 timezone 仅影响 Agent 对话中的时间表述，不影响数据计算。

---

## 5. 代码改造

### 5.1 ConfigManager 改造

**删除的方法**：

| 方法 | 原用途 | 替代方案 |
|---|---|---|
| `get_llm_config()` | 从 config.json 读 llm_provider/model/base_url | 直接读 nanobot_config.json 的 `providers` + `agents.defaults.model` |
| `save_llm_config()` | 写 llm_provider/model 到 config.json | 向导直接写 nanobot_config.json |
| `has_llm_config()` | 检查 config.json 是否有 llm_provider+model | 检查 nanobot_config.json 是否有 `providers.default` 且对应 provider 有 `apiKey` |
| `get_fallback_models()` | 从 config.json 解析 fallback_models + model_presets | 直接读 nanobot_config.json 的 `agents.defaults.fallbackModels` |
| `get_fallback_api_key()` | 从环境变量查备选 API Key | 直接从 nanobot_config.json 的 `providers.<name>.apiKey` 读取 |
| `get_websocket_config()` | 从 config.json 读 websocket 节 | 直接读 nanobot_config.json 的 `channels.websocket` |
| `get_webui_config()` | 从 config.json 读 webui 节 | 直接读 nanobot_config.json 的相关配置 |

**新增的方法**：

```python
def get_nanobot_config_path(self) -> Path:
    """获取 nanobot_config.json 路径"""
    return self.base_dir / "nanobot_config.json"

def load_nanobot_config(self) -> dict[str, Any]:
    """加载 nanobot_config.json
    
    Returns:
        dict: nanobot 配置字典，文件不存在时返回空 dict
    """
    path = self.get_nanobot_config_path()
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)
```

**保留不变的方法**：`load_config()`、`save_config()`、`get()`、`set()` 等继续操作 config.json（仅含 Runner 专有字段）。

**其他改动**：

- `_get_default_config()` — 移除 `feishu_app_id`、`feishu_receive_id`、`feishu_receive_id_type` 字段，仅保留 `version`、`data_dir`、`auto_push_feishu`
- `ENV_KEY_MAPPING` — 移除飞书环境变量映射（`feishu_app_id`、`feishu_app_secret`），这些凭证已在 `nanobot_config.json` 中
- `WS_ENV_KEY_MAPPING` / `WEBUI_ENV_KEY_MAPPING` — 移除 WebSocket/WebUI 敏感字段映射，改为从 `nanobot_config.json` 读取
- `load_config_with_env_override()` — 不再对飞书、WebSocket、WebUI 字段做环境变量覆盖

### 5.2 RunnerProviderAdapter 改造

核心变化：**从转换器变为读取器**。

**删除的方法**：
- `_build_nanobot_config_from_runner()` — 整个方法删除（约 200 行转换逻辑）
- `save_nanobot_config()` — 不再需要自动生成
- `_get_or_create_nanobot_config()` — 不再需要从 Runner 配置构建 nanobot Config 对象
- `_build_feishu_channel_config()` — 飞书配置已在 nanobot_config.json 中
- `_build_websocket_channel_config()` — WebSocket 配置已在 nanobot_config.json 中
- `_parse_env_file()` — 不再需要从 .env.local 读飞书凭证

> **注意**：`_get_or_create_nanobot_config()` 原用于向 `ChannelManager` 提供 nanobot `Config` 对象（Pydantic 模型）。删除后，`ChannelManager` 的初始化改为由 `gateway.py` 直接通过 `nanobot.config.loader.load_config()` 从 `nanobot_config.json` 加载（见 5.4 节）。

**修改的方法**：

`get_llm_config()` — 改为从 nanobot_config.json 读取：

```python
def get_llm_config(self) -> LLMConfig:
    nano_cfg = self._runner_config.load_nanobot_config()
    providers = nano_cfg.get("providers", {})
    default_provider = providers.get("default", "")
    provider_cfg = providers.get(default_provider, {})
    
    return LLMConfig(
        provider=default_provider,
        model=nano_cfg.get("agents", {}).get("defaults", {}).get("model", ""),
        api_key=provider_cfg.get("apiKey", ""),
        base_url=provider_cfg.get("apiBase"),
    )
```

`get_agent_defaults()` — 改为从 nanobot_config.json 读取：

```python
def get_agent_defaults(self) -> AgentDefaults:
    nano_cfg = self._runner_config.load_nanobot_config()
    defaults = nano_cfg.get("agents", {}).get("defaults", {})
    return AgentDefaults(
        model=defaults.get("model", ""),
        max_tool_iterations=defaults.get("maxToolIterations", 200),
        context_window_tokens=defaults.get("contextWindowTokens", 200000),
        timezone=self._runner_config.get("timezone", "UTC"),
    )
```

`get_provider_instance()` — 创建 Provider 时直接用 nanobot_config.json 中的 apiKey。

`_resolve_fallback_presets()` — 从 nanobot_config.json 的 `agents.defaults.fallbackModels` 读取。

`is_available()` / `has_llm_config()` — 检查 nanobot_config.json 是否有有效 provider。

### 5.3 ConfigInjector 改造

`build_nanobot_config()` 方法删除。`resolve_webui_dist()` 方法（解析 WebUI dist 目录，含两级回退查找逻辑）迁移至 `ConfigManager` 作为 `resolve_webui_dist()` 方法。整个 `ConfigInjector` 类删除。

### 5.4 gateway.py 改造

**配置路径设置**：

```python
# 改造前
if context.config.has_llm_config():
    adapter = RunnerProviderAdapter(context.config, webui_enabled=webui)
    nanobot_config_path = context.config.base_dir / "nanobot_config.json"
    adapter.save_nanobot_config(nanobot_config_path)
    set_config_path(nanobot_config_path)

# 改造后
nanobot_config_path = context.config.get_nanobot_config_path()
if nanobot_config_path.exists():
    from nanobot.config.loader import set_config_path
    set_config_path(nanobot_config_path)

if context.config.has_llm_config():
    adapter = RunnerProviderAdapter(context.config, webui_enabled=webui)
```

关键变化：`set_config_path` 直接指向用户维护的 `nanobot_config.json`，不再调用 `save_nanobot_config()` 自动生成。

**ChannelManager 初始化改造**：

```python
# 改造前
channels = ChannelManager(
    config=adapter._get_or_create_nanobot_config(),  # 从 Runner 配置构建
    bus=bus,
    session_manager=session_manager,
    webui_runtime_model_name=get_runtime_model_name,
)

# 改造后
from nanobot.config.loader import load_config as load_nanobot_config
nanobot_cfg = load_nanobot_config(nanobot_config_path)  # 直接从 nanobot_config.json 加载
channels = ChannelManager(
    config=nanobot_cfg,
    bus=bus,
    session_manager=session_manager,
    webui_runtime_model_name=get_runtime_model_name,
)
```

`ChannelManager` 需要的是 nanobot `Config` 对象（Pydantic 模型），不能直接传 dict。改造后通过 `nanobot.config.loader.load_config()` 从 `nanobot_config.json` 加载，不再通过 adapter 间接构建。

**MCP 配置读取改造**：

```python
# 改造前
from src.core.tools.mcp_connector import load_mcp_servers_config
mcp_servers = load_mcp_servers_config(context.config.config_file)  # 从 config.json 读

# 改造后
from src.core.tools.mcp_connector import load_mcp_servers_config
mcp_servers = load_mcp_servers_config(context.config.get_nanobot_config_path())  # 从 nanobot_config.json 读
```

`load_mcp_servers_config()` 的参数从 `config.json` 路径改为 `nanobot_config.json` 路径。函数内部通过 `MCPConfigHelper` 读取 `tools.mcpServers` 字段。

### 5.5 agent.py 改造

`agent.py` 中通过 `RunnerProviderAdapter.is_available()` 间接检查 LLM 配置可用性。`is_available()` 的内部实现改为检查 `nanobot_config.json`，`agent.py` 本身无需修改。

`agent.py` 中的 MCP 配置加载需同步改造（与 gateway.py 一致）：

```python
# 改造前
mcp_config = load_mcp_servers_config(context.config.config_file)

# 改造后
mcp_config = load_mcp_servers_config(context.config.get_nanobot_config_path())
```

---

## 6. 初始化向导改造

### 6.1 向导输出变化

**改造前**：向导收集用户输入 → 生成 `config.json`（含 llm_*、model_presets、tools 等）→ 运行时转换为 `nanobot_config.json`

**改造后**：向导收集用户输入 → 同时生成两个文件：
- `config.json`：仅含 `version`、`data_dir`、`timezone`、`auto_push_feishu`
- `nanobot_config.json`：含 `providers`、`agents`、`channels`、`model_presets`、`tools`

### 6.2 InitPrompts 改造

> 文件位置：`src/core/init/prompts.py`（类名 `InitPrompts`）

`run_full_wizard()` 返回结构变化：

```python
# 改造后返回
{
    "runner_config": {
        "version": "0.32.0",
        "timezone": "Asia/Shanghai",
        "auto_push_feishu": false
    },
    "nanobot_config": {
        "providers": {
            "default": "custom",
            "custom": {"apiKey": "sk-xxx", "apiBase": "...", "apiType": "auto"}
        },
        "agents": {
            "defaults": {
                "model": "agnes-2.0-flash",
                "provider": "auto",
                "timezone": "Asia/Shanghai",
                "workspace": "~/.nanobot-runner",
                "botName": "nanobot-runner",
                "botIcon": "🍀"
            }
        },
        "channels": {},
        "model_presets": {},
        "tools": {"mcpServers": {}}
    }
}
```

关键变化：
- `run_llm_provider_wizard()` 返回 nanobot 原生格式的 `providers` + `agents.defaults`
- `run_fallback_wizard()` 返回 `agents.defaults.fallbackModels` + `model_presets`（nanobot 格式）
- `run_feishu_config_wizard()` 返回 `channels.feishu`（含 app_secret，不再放 env_vars）
- `.env.local` 不再生成（API Key 和飞书凭证都写在 nanobot_config.json 中）
- `nanobot_config.json` 写入后同步追加 `.gitignore` 条目，防止敏感凭证泄露

### 6.3 ConfigGenerator 改造

> 文件位置：`src/core/init/generator.py`

`write_config_files()` 新增写入 `nanobot_config.json`：

```python
def write_config_files(self, workspace_dir, runner_config, nanobot_config, init_git=True):
    # 1. 写 config.json（Runner 专有字段）
    config_path = workspace_dir / "config.json"
    config_path.write_text(self.generate_config_json(runner_config), encoding="utf-8")
    
    # 2. 写 nanobot_config.json（nanobot 原生格式）
    if nanobot_config:
        nano_path = workspace_dir / "nanobot_config.json"
        nano_path.write_text(json.dumps(nanobot_config, indent=2, ensure_ascii=False), encoding="utf-8")
    
    # 3. 写 .gitignore（排除 nanobot_config.json）
    gitignore_path = workspace_dir / ".gitignore"
    if not gitignore_path.exists() or "nanobot_config.json" not in gitignore_path.read_text():
        with open(gitignore_path, "a", encoding="utf-8") as f:
            f.write("\n# 敏感凭证配置，禁止提交\nnanobot_config.json\n")
    
    # 4. 模板文件、memory、skills 复制逻辑不变
```

`_TRACKED_FILES` 更新：
- `nanobot_config.json` **不加入** `_TRACKED_FILES`（含敏感凭证，不应被 git 追踪）
- `.env.local` 可从 `_TRACKED_FILES` 中移除（不再包含凭证，且不再生成）

`generate_env_local()` 方法简化或移除（不再有 LLM API Key 和飞书凭证写入 .env.local）。

### 6.4 迁移命令

新增 `nanobotrun system migrate-config` 命令，将现有 `config.json` 中的 nanobot 相关字段一次性迁移到 `nanobot_config.json`：

> 文件位置：`src/core/init/migrate.py`（已有 `MigrationResult` 数据类，迁移逻辑在此扩展）

```python
def migrate_config():
    """将旧版 config.json 的 nanobot 字段迁移到 nanobot_config.json"""
    config = load_config()  # 读旧 config.json
    
    # 构建 nanobot_config.json（独立实现字段映射，不复用 RunnerProviderAdapter 私有方法）
    nanobot_config = build_nanobot_config_from_legacy(config)
    save_nanobot_config(nanobot_config)
    
    # 精简 config.json（移除 nanobot 字段）
    runner_config = {
        "version": config["version"],
        "data_dir": config["data_dir"],
        "timezone": config.get("timezone", "UTC"),
        "auto_push_feishu": config.get("auto_push_feishu", False),
        "user_id": config.get("user_id", "default_user"),
    }
    save_config(runner_config)
    
    # 将 .env.local 中的 API Key 写入 nanobot_config.json
    migrate_env_keys_to_nanobot_config(nanobot_config)
```

> **设计说明**：迁移逻辑在 `migrate.py` 中**独立实现**字段映射（`build_nanobot_config_from_legacy()`），**不复用** `RunnerProviderAdapter._build_nanobot_config_from_runner()`。字段映射知识参考第 3.8 节的字段映射表，但作为一次性迁移工具的独立函数，不依赖运行时类。迁移完成后，`RunnerProviderAdapter` 中的转换方法可安全删除。

### 6.5 数据模式（无 LLM）

当用户选择数据模式（`agent_mode=False`）时：
- 仍生成 `config.json`（含 version、data_dir、timezone）
- 不生成 `nanobot_config.json`
- `gateway start` 和 `agent chat` 会提示"未配置 LLM，请运行 nanobotrun system init"

---

## 7. 迁移策略与错误处理

### 7.1 迁移触发时机

`nanobotrun system init` 检测到旧版 `config.json`（含 `llm_provider` 字段）时：

- **`nanobot_config.json` 不存在**：提示迁移

```
检测到旧版配置格式（config.json 含 llm_provider 字段）。
是否自动迁移到 nanobot_config.json？[Y/n]
```

- **`nanobot_config.json` 已存在**：提示冲突

```
检测到 config.json 含旧版字段，但 nanobot_config.json 已存在。
请确认以哪个为准：
  [1] 以 nanobot_config.json 为准，清理 config.json 旧字段
  [2] 以 config.json 为准，覆盖 nanobot_config.json
```

- 用户选 Y / [1]：执行迁移，迁移后精简 config.json
- 用户选 n：跳过，但 `gateway start` 会报错提示"未找到 nanobot_config.json，请运行 nanobotrun system migrate-config"

### 7.2 迁移流程

```
读取旧 config.json
    → 提取 nanobot 相关字段
    → 读取 .env.local 获取 API Key
    → 组装 nanobot_config.json
    → 写入 nanobot_config.json
    → 精简 config.json（仅保留 Runner 字段）
    → 备份旧 config.json 为 config.json.bak
    → 迁移完成
```

**备份策略**：迁移前将旧 `config.json` 备份为 `config.json.bak`。如果 `.bak` 已存在则覆盖。迁移成功后**保留** `.bak` 供用户手动回滚（不自动删除），用户确认无误后可自行删除。迁移失败时从 `.bak` 回滚 `config.json`，删除半成品 `nanobot_config.json`。

**API Key 迁移**：从 `.env.local` 读取 `NANOBOT_LLM_API_KEY`、`NANOBOT_FEISHU_APP_ID`、`NANOBOT_FEISHU_APP_SECRET`，写入 `nanobot_config.json` 对应字段。迁移后 `.env.local` 保留但不被运行时读取。

### 7.3 错误处理

| 场景 | 处理方式 |
|---|---|
| `nanobot_config.json` 不存在 | `has_llm_config()` 返回 False，gateway/agent 提示"请运行 nanobotrun system init" |
| `nanobot_config.json` 存在但 `providers` 为空 | 同上，提示"未配置 LLM" |
| `nanobot_config.json` JSON 格式错误 | 抛出 `ConfigError`，提示"配置文件格式错误，请检查 nanobot_config.json" |
| `providers.default` 指向的 provider 不存在 | 抛出 `LLMError`，提示"default provider 不存在，请检查 nanobot_config.json" |
| `apiKey` 为空 | `has_llm_config()` 返回 False，提示"未配置 API Key" |
| `config.json` 仍含旧字段（llm_provider 等） | 打印 warning："检测到旧版字段，建议运行 nanobotrun system migrate-config 迁移" |
| 迁移过程中写入失败 | 回滚 config.json，删除半成品 nanobot_config.json，提示错误 |

### 7.4 向后兼容

迁移完成后，旧字段（`llm_provider`、`llm_model` 等）从 `config.json` 中移除。`AppConfig.validate()` 不再校验这些字段，`ConfigManager.get("llm_provider")` 返回 None。

如果用户手动恢复旧版 `config.json`（含 llm 字段），`ConfigManager` 启动时检测到旧字段会打印 warning 但不崩溃。`has_llm_config()` 以 `nanobot_config.json` 为准，不受 config.json 旧字段影响。

---

## 8. 测试策略

| 测试类型 | 覆盖内容 |
|---|---|
| 单元测试 | `ConfigManager.load_nanobot_config()` 读写 |
| 单元测试 | `RunnerProviderAdapter.get_llm_config()` 从 nanobot_config 读取 |
| 单元测试 | `has_llm_config()` 新逻辑 |
| 单元测试 | `migrate_config()` 迁移正确性：旧字段→新字段映射、备份/回滚 |
| 单元测试 | `AppConfig.validate()` 精简后 schema 验证 |
| 单元测试 | `load_mcp_servers_config()` 从 nanobot_config.json 读取 MCP 配置 |
| 单元测试 | `.gitignore` 生成包含 `nanobot_config.json` |
| 集成测试 | 向导端到端：init → 生成两文件 + .gitignore → gateway start → WebSocket 连接 |
| 集成测试 | 迁移端到端：旧 config.json + .env.local → migrate → nanobot_config.json 正确 → gateway start |
| 集成测试 | ChannelManager 从 nanobot_config.json 加载 Config 对象 |
| 回归测试 | 数据模式（无 LLM）：init → 仅 config.json → data import 正常 |

---

## 9. 变更文件清单

| 文件 | 变更类型 |
|---|---|
| `src/core/config/manager.py` | 删除 LLM/WS/WebUI 方法，新增 `load_nanobot_config()`；精简 `_get_default_config()`、`ENV_KEY_MAPPING`；迁移 `resolve_webui_dist()` |
| `src/core/config/schema.py` | 精简 `AppConfig`，移除 nanobot 字段验证 |
| `src/core/config/llm_config.py` | 不变（`LLMConfig` dataclass 仍作为内部传递对象） |
| `src/core/config/env_manager.py` | 简化 `.env.local` 模板，移除 LLM/飞书凭证模板 |
| `src/core/provider_adapter.py` | 删除 `_build_nanobot_config_from_runner()`、`save_nanobot_config()`、`_get_or_create_nanobot_config()` 等转换方法，改为从 nanobot_config.json 读取 |
| `src/core/config_injector.py` | 删除整个类（`build_nanobot_config()` 删除，`resolve_webui_dist()` 迁移至 `ConfigManager`） |
| `src/cli/commands/gateway.py` | 直接 `set_config_path()`；`ChannelManager` 改为从 `nanobot_config.json` 加载 Config；MCP 配置读取源改为 `nanobot_config.json` |
| `src/cli/commands/agent.py` | MCP 配置读取源改为 `nanobot_config.json` |
| `src/cli/commands/system.py` | 新增 `migrate-config` 命令 |
| `src/core/init/prompts.py` | 向导返回结构改造，生成 nanobot 原生格式 |
| `src/core/init/generator.py` | 写入 `nanobot_config.json` + `.gitignore`；更新 `_TRACKED_FILES` |
| `src/core/init/wizard.py` | 向导流程适配双文件输出 |
| `src/core/init/migrate.py` | 新增 `migrate_config()` 和 `build_nanobot_config_from_legacy()` |
| `src/core/tools/mcp_connector.py` | `load_mcp_servers_config()` 读取源从 config.json 改为 nanobot_config.json |
| `src/core/tools/mcp_config_helper.py` | 适配从 nanobot_config.json 的 `tools.mcpServers` 读取 |
| `src/core/base/context.py` | `has_llm_config()` 调用路径可能调整 |
