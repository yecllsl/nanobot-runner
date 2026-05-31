# FallbackProvider 多供应商故障转移设计

> **日期**: 2026-05-30
> **状态**: 已确认
> **涉及版本**: v0.27.0
> **当前基线**: v0.26.0

---

## 1. 背景与动机

nanobot-ai 0.2.0 提供了 FallbackProvider 能力，支持主备模型自动故障转移、断路器机制和智能错误分类。在实际使用中，单一供应商的限流、服务不可用等问题严重影响产品体验。通过接入 FallbackProvider，可在主供应商故障时自动切换到备选供应商，显著提升服务可用性。

**核心需求**：
1. 接入 nanobot-ai 的 FallbackProvider，实现主备链式故障转移
2. 在系统初始化向导中支持配置多个供应商（主必填 + 备选可选）
3. API Key 按供应商名分存到 `.env.local`，确保安全性
4. 触发条件仅使用底座内置的智能错误分类，不额外扩展

---

## 2. 设计决策

| 决策项 | 选择 | 理由 |
|--------|------|------|
| 供应商关系 | 主备链式 | 与底座 FallbackProvider 设计一致 |
| 配置模式 | `model_presets` + `fallback_models` 引用 | 与底座 `FallbackCandidate = str \| InlineFallbackConfig` 对齐 |
| 初始化交互 | 主必填 + 备选可选 | 不增加入门门槛 |
| API Key 存储 | 按供应商名分存 `.env.local` | 清晰且安全 |
| 触发条件 | 仅用底座内置 | 零额外开发，底座已覆盖主要场景 |

---

## 3. 配置结构设计

### 3.1 config.json 结构

```json
{
  "version": "0.9.5",
  "data_dir": "~/.nanobot-runner/data",
  "llm_provider": "siliconflow",
  "llm_model": "Qwen/Qwen3-235B-A22B",
  "llm_base_url": "https://api.siliconflow.cn/v1",
  "model_presets": {
    "nvidia-llama4": {
      "provider": "nvidia",
      "model": "meta/llama-4-maverick-17b-128e-instruct-maas",
      "base_url": "https://integrate.api.nvidia.com/v1"
    },
    "openrouter-gemini": {
      "provider": "openrouter",
      "model": "google/gemini-2.5-flash-preview",
      "base_url": "https://openrouter.ai/api/v1"
    },
    "zhipu-glm4": {
      "provider": "zhipu",
      "model": "glm-4.7-flash",
      "base_url": "https://open.bigmodel.cn/api/paas/v4"
    }
  },
  "fallback_models": ["nvidia-llama4", "openrouter-gemini", "zhipu-glm4"]
}
```

### 3.2 .env.local 结构

```env
# 主供应商
NANOBOT_LLM_API_KEY=sk-siliconflow-xxx
NANOBOT_LLM_PROVIDER=siliconflow
NANOBOT_LLM_MODEL=Qwen/Qwen3-235B-A22B
NANOBOT_LLM_BASE_URL=https://api.siliconflow.cn/v1

# 备选供应商（按供应商名分存）
NANOBOT_LLM_API_KEY_NVIDIA=nvapi-xxx
NANOBOT_LLM_API_KEY_OPENROUTER=sk-or-xxx
NANOBOT_LLM_API_KEY_ZHIPU=xxx.zhipu-xxx
```

### 3.3 API Key 命名规则

- 主供应商：复用现有 `NANOBOT_LLM_API_KEY`
- 备选供应商：`NANOBOT_LLM_API_KEY_{PROVIDER_UPPER}`
- 查找优先级：`NANOBOT_LLM_API_KEY_{PROVIDER_UPPER}` → `NANOBOT_LLM_API_KEY`（兜底） → `None`（Ollama 等不需要 Key 的供应商）

---

## 4. 核心代码改造

### 4.1 AppConfig Schema 扩展

文件：`src/core/config/schema.py`

新增字段：
```python
fallback_models: list[str] | None = None
```

在 `FIELD_TYPES` 中注册：
```python
"fallback_models": (list, type(None)),
```

在 `to_dict()` 中输出该字段。

### 4.2 ConfigManager 扩展

文件：`src/core/config/manager.py`

新增方法：

- `get_fallback_models() -> list[dict[str, Any]]`：解析 `fallback_models` 列表，从 `model_presets` 中查找每个预设的完整配置，返回包含 provider/model/base_url/api_key 的字典列表
- `get_fallback_api_key(provider: str) -> str | None`：按 `NANOBOT_LLM_API_KEY_{PROVIDER_UPPER}` 规则查找 API Key
- `save_fallback_config(presets, fallback_models, api_keys)`：保存 fallback 配置到 config.json + .env.local

### 4.3 RunnerProviderAdapter 核心改造

文件：`src/core/provider_adapter.py`

`get_provider_instance()` 方法改造：

1. 创建主 Provider（现有逻辑）
2. 从 `ConfigManager` 读取 `fallback_models` 配置
3. 为每个 fallback 预设创建 Provider 实例的工厂函数
4. 用 `FallbackProvider` 包装主 Provider

```python
def get_provider_instance(self) -> Any:
    if self._provider_instance is not None:
        return self._provider_instance

    llm_config = self.get_llm_config()
    primary = self._create_primary_provider(llm_config)

    fallback_presets = self._resolve_fallback_presets()
    if not fallback_presets:
        self._provider_instance = primary
        return primary

    from nanobot.providers.fallback_provider import FallbackProvider
    self._provider_instance = FallbackProvider(
        primary=primary,
        fallback_presets=fallback_presets,
        provider_factory=self._create_fallback_provider,
    )
    return self._provider_instance
```

新增私有方法：
- `_resolve_fallback_presets() -> list[Any]`：从 ConfigManager 解析 fallback 预设列表，转换为底座 `ModelPresetConfig` 格式
- `_create_primary_provider(llm_config) -> LLMProvider`：提取现有主 Provider 创建逻辑
- `_create_fallback_provider(preset) -> LLMProvider`：为 fallback 预设创建 Provider 实例

### 4.4 _build_nanobot_config_from_runner 同步改造

扩展该方法，在构建 nanobot Config 对象时注入 `fallback_models` 配置，使底座在需要时也能直接读取 fallback 配置。

### 4.5 初始化向导扩展

文件：`src/core/init/prompts.py`

#### 4.5.1 交互流程

在 `run_llm_provider_wizard()` 完成主供应商配置后，追加备选供应商配置交互：

```
✅ 主供应商配置完成：siliconflow / Qwen/Qwen3-235B-A22B

? 是否配置备选供应商？（主供应商故障时自动切换）(y/N): y

── 备选供应商 #1 ──
? 选择备选 Provider:
  > nvidia
    openrouter
    zhipu
    siliconflow
    deepseek
    other
? 输入模型名称: meta/llama-4-maverick-17b-128e-instruct-maas
? 输入 API Key: ********
? 输入 Base URL (可选，留空使用默认): https://integrate.api.nvidia.com/v1

✅ 备选供应商 #1 已添加：nvidia / meta/llama-4-maverick-17b-128e-instruct-maas

? 是否继续添加备选供应商？(y/N): y

── 备选供应商 #2 ──
? 选择备选 Provider:
  > openrouter
    nvidia
    zhipu
    siliconflow
    deepseek
    other
? 输入模型名称: google/gemini-2.5-flash-preview
? 输入 API Key: ********
? 输入 Base URL (可选，留空使用默认): https://openrouter.ai/api/v1

✅ 备选供应商 #2 已添加：openrouter / google/gemini-2.5-flash-preview

? 是否继续添加备选供应商？(y/N): n

✅ Fallback 链配置完成：
  主: siliconflow / Qwen/Qwen3-235B-A22B
  备1: nvidia / meta/llama-4-maverick-17b-128e-instruct-maas
  备2: openrouter / google/gemini-2.5-flash-preview
```

#### 4.5.2 交互逻辑

1. 主供应商配置完成后，询问是否配置备选（默认 N，降低入门门槛）
2. 每添加一个备选后，询问是否继续
3. 备选供应商选择列表中排除已配置的供应商（避免重复）
4. 自动为每个备选生成 `model_presets` 条目名（格式：`{provider}-{short_model_name}`）
5. 最终展示完整的 Fallback 链摘要

#### 4.5.3 返回值结构扩展

`run_llm_provider_wizard()` 返回值在现有主供应商字段基础上，新增备选供应商相关字段：

```python
{
    # 主供应商（现有）
    "NANOBOT_LLM_PROVIDER": "siliconflow",
    "NANOBOT_LLM_MODEL": "Qwen/Qwen3-235B-A22B",
    "NANOBOT_LLM_API_KEY": "sk-xxx",
    "NANOBOT_LLM_BASE_URL": "https://api.siliconflow.cn/v1",

    # 备选供应商 API Key（新增，按供应商名分存）
    "NANOBOT_LLM_API_KEY_NVIDIA": "nvapi-xxx",
    "NANOBOT_LLM_API_KEY_OPENROUTER": "sk-or-xxx",

    # 预设和 fallback 配置（新增，供 wizard.py 写入 config.json）
    "_model_presets": {
        "nvidia-llama4": {"provider": "nvidia", "model": "...", "base_url": "..."},
        "openrouter-gemini": {"provider": "openrouter", "model": "...", "base_url": "..."}
    },
    "_fallback_models": ["nvidia-llama4", "openrouter-gemini"]
}
```

#### 4.5.4 run_full_wizard() 同步改造

`run_full_wizard()` 需要将 `_model_presets` 和 `_fallback_models` 合并到 `config` 字典中：
- `_model_presets` 合并到 `config["model_presets"]`（与已有预设合并）
- `_fallback_models` 写入 `config["fallback_models"]`
- 备选供应商 API Key 合并到 `env_vars`

### 4.6 ConfigGenerator 扩展

文件：`src/core/init/generator.py`

`generate_env_local()` 方法扩展：
- 支持生成 `NANOBOT_LLM_API_KEY_{PROVIDER_UPPER}` 格式的备选供应商 API Key

### 4.7 model list 命令增强

文件：`src/cli/commands/model.py`、`src/cli/handlers/model_handler.py`

在 `nanobotrun model list` 输出中：
- 标注哪些预设是 fallback
- 显示 fallback 顺序编号

---

## 5. 数据流

```
config.json + .env.local
        ↓
ConfigManager.get_llm_config()          → 主供应商配置
ConfigManager.get_fallback_models()     → 备选供应商列表（从 model_presets 解析）
ConfigManager.get_fallback_api_key()    → 按供应商名查找 API Key
        ↓
RunnerProviderAdapter.get_provider_instance()
        ↓
┌─────────────────────────────────────────────┐
│ 1. 创建主 Provider (OpenAICompatProvider)    │
│ 2. 解析 fallback_presets → list[PresetConfig]│
│ 3. FallbackProvider(primary, presets, factory)│
└─────────────────────────────────────────────┘
        ↓
AgentLoop 使用 FallbackProvider 实例
        ↓
请求 → 主供应商 → 成功? → 返回
                  → 可回退错误? → 尝试 fallback[0] → 成功? → 返回
                                                       → 失败? → fallback[1] → ...
                  → 不可回退错误? → 直接返回错误
```

---

## 6. 错误处理

| 场景 | 处理方式 |
|------|---------|
| `fallback_models` 引用的预设名在 `model_presets` 中不存在 | 启动时日志警告，跳过该条目，不阻塞启动 |
| 备选供应商 API Key 缺失 | 日志警告，跳过该备选，继续尝试下一个 |
| 所有备选供应商均失败 | 返回最后一个错误响应（底座 FallbackProvider 内置行为） |
| 主供应商断路器打开（连续3次失败） | 自动跳过主供应商，直接尝试备选（60秒后半开探测） |
| `model_presets` 中预设缺少 `provider` 或 `model` | 启动时日志警告，跳过该条目 |
| nanobot-ai 未安装 FallbackProvider | 降级为单供应商模式，日志警告 |

---

## 7. 降级策略

当底座不支持 FallbackProvider 或无 fallback 配置时，自动降级为单供应商模式：

```python
def get_provider_instance(self) -> Any:
    primary = self._create_primary_provider(llm_config)
    fallback_presets = self._resolve_fallback_presets()

    if not fallback_presets:
        return primary

    try:
        from nanobot.providers.fallback_provider import FallbackProvider
        return FallbackProvider(primary, fallback_presets, factory)
    except ImportError:
        logger.warning("nanobot-ai 未支持 FallbackProvider，降级为单供应商模式")
        return primary
```

---

## 8. 配置验证

在 `AppConfig.validate()` 中新增：
- `fallback_models` 中的每个条目必须是 `str` 类型
- `model_presets` 中每个预设必须包含 `provider` 和 `model` 字段
- 不在 `validate` 中强制校验 `fallback_models` 引用是否存在（运行时容错），而是在 `RunnerProviderAdapter` 中做运行时检查

---

## 9. 改动范围汇总

| 文件 | 改动类型 | 改动量 |
|------|---------|--------|
| `src/core/config/schema.py` | 新增 `fallback_models` 字段 | 小 |
| `src/core/config/manager.py` | 新增 fallback 相关方法 | 中 |
| `src/core/provider_adapter.py` | 核心改造：FallbackProvider 集成 | 大 |
| `src/core/init/prompts.py` | 向导扩展：备选供应商配置 | 中 |
| `src/core/init/generator.py` | env 生成扩展 | 小 |
| `src/cli/commands/model.py` | 展示增强：标注 fallback | 小 |
| `src/cli/handlers/model_handler.py` | 展示增强：返回 fallback 信息 | 小 |
