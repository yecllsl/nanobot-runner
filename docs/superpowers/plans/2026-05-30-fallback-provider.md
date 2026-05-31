# FallbackProvider 多供应商故障转移 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 接入 nanobot-ai 的 FallbackProvider，实现主备链式故障转移，并在系统初始化向导中支持配置多个供应商。

**Architecture:** 在现有 `model_presets` 机制上新增 `fallback_models` 字段，通过 `RunnerProviderAdapter` 将 fallback 配置转换为底座 `FallbackProvider` 所需的 `ModelPresetConfig` 列表，实现主备自动切换。API Key 按供应商名分存到 `.env.local`。

**Tech Stack:** Python 3.11+, nanobot-ai FallbackProvider, questionary (交互式向导)

---

## File Structure

| 文件 | 职责 | 操作 |
|------|------|------|
| `src/core/config/schema.py` | AppConfig Schema，新增 `fallback_models` 字段 | 修改 |
| `src/core/config/manager.py` | ConfigManager，新增 fallback 读取/保存方法 | 修改 |
| `src/core/config/env_manager.py` | EnvManager，新增 fallback API Key 查找方法 | 修改 |
| `src/core/provider_adapter.py` | RunnerProviderAdapter，核心改造集成 FallbackProvider | 修改 |
| `src/core/init/prompts.py` | 初始化向导，新增备选供应商配置交互 | 修改 |
| `src/core/init/generator.py` | ConfigGenerator，env 生成支持备选供应商 API Key | 修改 |
| `src/cli/handlers/model_handler.py` | ModelHandler，返回 fallback 信息 | 修改 |
| `src/cli/commands/model.py` | model list 命令，展示 fallback 标注 | 修改 |
| `tests/unit/core/test_fallback_config.py` | fallback 配置相关单元测试 | 新建 |
| `tests/unit/core/test_provider_adapter.py` | ProviderAdapter fallback 集成测试 | 修改 |

---

### Task 1: AppConfig Schema 扩展

**Files:**
- Modify: `src/core/config/schema.py`
- Test: `tests/unit/core/test_fallback_config.py`

- [ ] **Step 1: 写失败测试 — AppConfig 支持 fallback_models 字段**

创建 `tests/unit/core/test_fallback_config.py`：

```python
from src.core.config.schema import AppConfig


class TestAppConfigFallbackModels:
    def test_fallback_models_none_by_default(self):
        config = AppConfig(version="0.9.5", data_dir="/data")
        assert config.fallback_models is None

    def test_fallback_models_with_list(self):
        config = AppConfig(
            version="0.9.5",
            data_dir="/data",
            fallback_models=["nvidia-llama4", "openrouter-gemini"],
        )
        assert config.fallback_models == ["nvidia-llama4", "openrouter-gemini"]

    def test_validate_fallback_models_str_list(self):
        config = {
            "version": "0.9.5",
            "data_dir": "/data",
            "fallback_models": ["preset-a", "preset-b"],
        }
        is_valid, errors = AppConfig.validate(config)
        assert is_valid
        assert len(errors) == 0

    def test_validate_fallback_models_rejects_non_str_items(self):
        config = {
            "version": "0.9.5",
            "data_dir": "/data",
            "fallback_models": [123, "preset-b"],
        }
        is_valid, errors = AppConfig.validate(config)
        assert not is_valid
        assert any("fallback_models" in e for e in errors)

    def test_from_dict_with_fallback_models(self):
        config = {
            "version": "0.9.5",
            "data_dir": "/data",
            "fallback_models": ["preset-a"],
        }
        app_config = AppConfig.from_dict(config)
        assert app_config.fallback_models == ["preset-a"]

    def test_to_dict_includes_fallback_models(self):
        config = AppConfig(
            version="0.9.5",
            data_dir="/data",
            fallback_models=["preset-a"],
        )
        d = config.to_dict()
        assert d["fallback_models"] == ["preset-a"]

    def test_to_dict_fallback_models_none(self):
        config = AppConfig(version="0.9.5", data_dir="/data")
        d = config.to_dict()
        assert d["fallback_models"] is None
```

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/unit/core/test_fallback_config.py -v`
Expected: FAIL — `AppConfig.__init__` 不接受 `fallback_models` 参数

- [ ] **Step 3: 实现 — AppConfig 新增 fallback_models 字段**

修改 `src/core/config/schema.py`：

1. 在 `AppConfig` 数据类中新增字段（在 `llm_base_url` 之后）：
```python
fallback_models: list[str] | None = None
```

2. 在 `FIELD_TYPES` 字典中新增：
```python
"fallback_models": (list, type(None)),
```

3. 在 `to_dict()` 方法中新增：
```python
"fallback_models": self.fallback_models,
```

4. 在 `validate()` 方法中，在版本号格式检查之后新增 fallback_models 条目类型校验：
```python
if "fallback_models" in config and config["fallback_models"] is not None:
    if not isinstance(config["fallback_models"], list):
        errors.append("字段 'fallback_models' 类型错误，期望 list，实际非列表")
    else:
        for i, item in enumerate(config["fallback_models"]):
            if not isinstance(item, str):
                errors.append(
                    f"fallback_models[{i}] 类型错误，期望 str，实际 {type(item).__name__}"
                )
```

- [ ] **Step 4: 运行测试确认通过**

Run: `uv run pytest tests/unit/core/test_fallback_config.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/core/config/schema.py tests/unit/core/test_fallback_config.py
git commit -m "feat: add fallback_models field to AppConfig schema"
```

---

### Task 2: ConfigManager fallback 方法

**Files:**
- Modify: `src/core/config/manager.py`
- Modify: `src/core/config/env_manager.py`
- Test: `tests/unit/core/test_fallback_config.py`

- [ ] **Step 1: 写失败测试 — ConfigManager.get_fallback_api_key**

在 `tests/unit/core/test_fallback_config.py` 末尾追加：

```python
import os
from unittest.mock import MagicMock, patch

from src.core.config.manager import ConfigManager


class TestConfigManagerFallbackApiKey:
    def test_get_fallback_api_key_from_env(self):
        config = ConfigManager(allow_default=True)
        with patch.dict(os.environ, {"NANOBOT_LLM_API_KEY_NVIDIA": "nvapi-test"}, clear=False):
            result = config.get_fallback_api_key("nvidia")
            assert result == "nvapi-test"

    def test_get_fallback_api_key_fallback_to_main(self):
        config = ConfigManager(allow_default=True)
        with patch.dict(os.environ, {"NANOBOT_LLM_API_KEY": "main-key"}, clear=False):
            with patch.dict(os.environ, {}, clear=False):
                if "NANOBOT_LLM_API_KEY_NVIDIA" in os.environ:
                    del os.environ["NANOBOT_LLM_API_KEY_NVIDIA"]
                result = config.get_fallback_api_key("nvidia")
                assert result == "main-key"

    def test_get_fallback_api_key_none(self):
        config = ConfigManager(allow_default=True)
        env_to_clear = [
            "NANOBOT_LLM_API_KEY_NVIDIA",
            "NANOBOT_LLM_API_KEY",
        ]
        with patch.dict(os.environ, {}, clear=False):
            for k in env_to_clear:
                if k in os.environ:
                    del os.environ[k]
            result = config.get_fallback_api_key("nvidia")
            assert result is None


class TestConfigManagerGetFallbackModels:
    def test_get_fallback_models_empty(self):
        config = ConfigManager(allow_default=True)
        with patch.object(config, "load_config", return_value={"version": "0.9.5", "data_dir": "/data"}):
            result = config.get_fallback_models()
            assert result == []

    def test_get_fallback_models_with_presets(self):
        config = ConfigManager(allow_default=True)
        mock_config = {
            "version": "0.9.5",
            "data_dir": "/data",
            "model_presets": {
                "nvidia-llama4": {
                    "provider": "nvidia",
                    "model": "meta/llama-4-maverick-17b-128e-instruct-maas",
                    "base_url": "https://integrate.api.nvidia.com/v1",
                },
            },
            "fallback_models": ["nvidia-llama4"],
        }
        with patch.object(config, "load_config", return_value=mock_config):
            with patch.object(config, "get_fallback_api_key", return_value="nvapi-test"):
                result = config.get_fallback_models()
                assert len(result) == 1
                assert result[0]["provider"] == "nvidia"
                assert result[0]["model"] == "meta/llama-4-maverick-17b-128e-instruct-maas"
                assert result[0]["base_url"] == "https://integrate.api.nvidia.com/v1"
                assert result[0]["api_key"] == "nvapi-test"

    def test_get_fallback_models_missing_preset_skipped(self):
        config = ConfigManager(allow_default=True)
        mock_config = {
            "version": "0.9.5",
            "data_dir": "/data",
            "model_presets": {},
            "fallback_models": ["nonexistent-preset"],
        }
        with patch.object(config, "load_config", return_value=mock_config):
            result = config.get_fallback_models()
            assert result == []

    def test_get_fallback_models_incomplete_preset_skipped(self):
        config = ConfigManager(allow_default=True)
        mock_config = {
            "version": "0.9.5",
            "data_dir": "/data",
            "model_presets": {
                "bad-preset": {"provider": "nvidia"},
            },
            "fallback_models": ["bad-preset"],
        }
        with patch.object(config, "load_config", return_value=mock_config):
            result = config.get_fallback_models()
            assert result == []
```

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/unit/core/test_fallback_config.py::TestConfigManagerFallbackApiKey -v`
Expected: FAIL — `ConfigManager` 没有 `get_fallback_api_key` 方法

- [ ] **Step 3: 实现 — ConfigManager 新增 fallback 方法**

修改 `src/core/config/manager.py`，在 `save_llm_config()` 方法之后新增：

```python
def get_fallback_api_key(self, provider: str) -> str | None:
    """获取备选供应商 API Key

    查找优先级：
    1. NANOBOT_LLM_API_KEY_{PROVIDER_UPPER}
    2. NANOBOT_LLM_API_KEY（主供应商 Key 兜底）

    Args:
        provider: 供应商名称

    Returns:
        str | None: API Key，未找到返回 None
    """
    provider_key = f"NANOBOT_LLM_API_KEY_{provider.upper()}"
    key = os.getenv(provider_key)
    if key:
        return key
    return os.getenv("NANOBOT_LLM_API_KEY")

def get_fallback_models(self) -> list[dict[str, Any]]:
    """获取备选供应商配置列表

    从 config.json 的 fallback_models 和 model_presets 中解析完整的备选供应商配置。

    Returns:
        list[dict[str, Any]]: 备选供应商配置列表，每个字典包含 provider/model/base_url/api_key
    """
    config = self.load_config()
    fallback_names: list[str] = config.get("fallback_models") or []
    presets: dict[str, dict[str, Any]] = config.get("model_presets") or {}

    result: list[dict[str, Any]] = []
    for name in fallback_names:
        preset = presets.get(name)
        if preset is None:
            logger.warning(f"fallback_models 引用的预设 '{name}' 在 model_presets 中不存在，跳过")
            continue
        provider = preset.get("provider", "")
        model = preset.get("model", "")
        if not provider or not model:
            logger.warning(f"预设 '{name}' 缺少 provider 或 model，跳过")
            continue
        api_key = self.get_fallback_api_key(provider)
        result.append({
            "provider": provider,
            "model": model,
            "base_url": preset.get("base_url"),
            "api_key": api_key,
        })
    return result
```

- [ ] **Step 4: 运行测试确认通过**

Run: `uv run pytest tests/unit/core/test_fallback_config.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/core/config/manager.py tests/unit/core/test_fallback_config.py
git commit -m "feat: add get_fallback_api_key and get_fallback_models to ConfigManager"
```

---

### Task 3: RunnerProviderAdapter 集成 FallbackProvider

**Files:**
- Modify: `src/core/provider_adapter.py`
- Test: `tests/unit/core/test_provider_adapter.py`

- [ ] **Step 1: 写失败测试 — ProviderAdapter 支持 FallbackProvider 包装**

在 `tests/unit/core/test_provider_adapter.py` 末尾追加：

```python
class TestRunnerProviderAdapterFallback:
    def _make_mock_config_with_fallback(self):
        config = MagicMock(spec=ConfigManager)
        config.has_llm_config.return_value = True
        config.get_llm_config.return_value = {
            "provider": "siliconflow",
            "model": "Qwen/Qwen3-235B-A22B",
            "api_key": "sk-sf-test",
            "base_url": "https://api.siliconflow.cn/v1",
        }
        config.get.return_value = None
        config.get_websocket_config.return_value = {}
        config.get_fallback_models.return_value = [
            {
                "provider": "nvidia",
                "model": "meta/llama-4-maverick-17b-128e-instruct-maas",
                "base_url": "https://integrate.api.nvidia.com/v1",
                "api_key": "nvapi-test",
            },
        ]
        return config

    def test_no_fallback_returns_plain_provider(self, mock_runner_config):
        mock_runner_config.get_fallback_models.return_value = []
        adapter = RunnerProviderAdapter(mock_runner_config)
        with patch("src.core.provider_adapter.RunnerProviderAdapter._create_primary_provider") as mock_create:
            mock_provider = MagicMock()
            mock_create.return_value = mock_provider
            result = adapter.get_provider_instance()
            assert result is mock_provider

    def test_with_fallback_returns_fallback_provider(self):
        config = self._make_mock_config_with_fallback()
        adapter = RunnerProviderAdapter(config)
        mock_primary = MagicMock()
        mock_primary.get_default_model.return_value = "Qwen/Qwen3-235B-A22B"
        with patch("src.core.provider_adapter.RunnerProviderAdapter._create_primary_provider", return_value=mock_primary):
            with patch("nanobot.providers.fallback_provider.FallbackProvider") as MockFB:
                mock_fb_instance = MagicMock()
                MockFB.return_value = mock_fb_instance
                result = adapter.get_provider_instance()
                MockFB.assert_called_once()
                assert result is mock_fb_instance

    def test_fallback_import_error_degrades_to_primary(self):
        config = self._make_mock_config_with_fallback()
        adapter = RunnerProviderAdapter(config)
        mock_primary = MagicMock()
        with patch("src.core.provider_adapter.RunnerProviderAdapter._create_primary_provider", return_value=mock_primary):
            with patch.dict("sys.modules", {"nanobot.providers.fallback_provider": None}):
                result = adapter.get_provider_instance()
                assert result is mock_primary

    def test_resolve_fallback_presets_converts_config(self):
        config = self._make_mock_config_with_fallback()
        adapter = RunnerProviderAdapter(config)
        presets = adapter._resolve_fallback_presets()
        assert len(presets) == 1
        assert presets[0].model == "meta/llama-4-maverick-17b-128e-instruct-maas"
        assert presets[0].provider == "nvidia"

    def test_resolve_fallback_presets_skips_missing_api_key(self):
        config = self._make_mock_config_with_fallback()
        config.get_fallback_models.return_value = [
            {
                "provider": "nvidia",
                "model": "meta/llama-4-maverick-17b-128e-instruct-maas",
                "base_url": "https://integrate.api.nvidia.com/v1",
                "api_key": None,
            },
        ]
        adapter = RunnerProviderAdapter(config)
        presets = adapter._resolve_fallback_presets()
        assert len(presets) == 0
```

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/unit/core/test_provider_adapter.py::TestRunnerProviderAdapterFallback -v`
Expected: FAIL — `RunnerProviderAdapter` 没有 `_create_primary_provider` 和 `_resolve_fallback_presets` 方法

- [ ] **Step 3: 实现 — RunnerProviderAdapter 改造**

修改 `src/core/provider_adapter.py`：

1. 将 `get_provider_instance()` 中的主 Provider 创建逻辑提取到 `_create_primary_provider()` 方法：

```python
def _create_primary_provider(self, llm_config: LLMConfig) -> Any:
    """创建主 Provider 实例

    Args:
        llm_config: LLM 配置

    Returns:
        Any: nanobot Provider 实例

    Raises:
        LLMError: Provider 创建失败时抛出
    """
    try:
        from nanobot.providers.openai_compat_provider import OpenAICompatProvider
        from nanobot.providers.registry import find_by_name

        spec = find_by_name(llm_config.provider)
        return OpenAICompatProvider(
            api_key=llm_config.api_key,
            api_base=llm_config.base_url,
            default_model=llm_config.model,
            spec=spec,
        )
    except ImportError as e:
        raise LLMError(
            f"无法导入nanobot模块: {e}",
            recovery_suggestion="请确认已安装nanobot-ai: uv add nanobot-ai",
        ) from e
    except (NanobotRunnerError, OSError, ValueError) as e:
        raise LLMError(
            f"创建Provider失败: {e}",
            recovery_suggestion="请检查LLM配置是否正确，特别是API Key和Base URL",
        ) from e
```

2. 新增 `_resolve_fallback_presets()` 方法：

```python
def _resolve_fallback_presets(self) -> list[Any]:
    """解析 fallback 预设列表

    从 ConfigManager 读取 fallback_models 配置，
    转换为底座 ModelPresetConfig 格式。
    跳过 API Key 缺失的条目。

    Returns:
        list[Any]: ModelPresetConfig 列表
    """
    try:
        from nanobot.config.schema import ModelPresetConfig
    except ImportError:
        logger.warning("nanobot-ai 不支持 ModelPresetConfig，跳过 fallback 配置")
        return []

    fallback_list = self._runner_config.get_fallback_models()
    if not fallback_list:
        return []

    presets: list[Any] = []
    for fb in fallback_list:
        api_key = fb.get("api_key")
        if not api_key:
            logger.warning(
                "备选供应商 '%s' API Key 缺失，跳过",
                fb.get("provider", "unknown"),
            )
            continue

        preset = ModelPresetConfig(
            model=fb["model"],
            provider=fb["provider"],
        )
        presets.append(preset)

    return presets
```

3. 新增 `_create_fallback_provider()` 方法：

```python
def _create_fallback_provider(self, preset: Any) -> Any:
    """为 fallback 预设创建 Provider 实例

    Args:
        preset: ModelPresetConfig 实例

    Returns:
        Any: nanobot Provider 实例
    """
    from nanobot.providers.openai_compat_provider import OpenAICompatProvider
    from nanobot.providers.registry import find_by_name

    api_key = self._runner_config.get_fallback_api_key(preset.provider)
    spec = find_by_name(preset.provider)

    fb_config = self._runner_config.get_fallback_models()
    base_url: str | None = None
    for fb in fb_config:
        if fb.get("provider") == preset.provider and fb.get("model") == preset.model:
            base_url = fb.get("base_url")
            break

    return OpenAICompatProvider(
        api_key=api_key,
        api_base=base_url,
        default_model=preset.model,
        spec=spec,
    )
```

4. 重写 `get_provider_instance()` 方法：

```python
def get_provider_instance(self) -> Any:
    """获取Provider实例

    支持 FallbackProvider 包装：当配置了 fallback_models 时，
    自动创建主备链式故障转移。

    Returns:
        Any: nanobot Provider 实例（可能是 FallbackProvider 包装）

    Raises:
        LLMError: Provider 创建失败时抛出
    """
    if self._provider_instance is not None:
        return self._provider_instance

    llm_config = self.get_llm_config()
    primary = self._create_primary_provider(llm_config)

    fallback_presets = self._resolve_fallback_presets()
    if not fallback_presets:
        self._provider_instance = primary
        return primary

    try:
        from nanobot.providers.fallback_provider import FallbackProvider

        self._provider_instance = FallbackProvider(
            primary=primary,
            fallback_presets=fallback_presets,
            provider_factory=self._create_fallback_provider,
        )
        logger.info(
            "FallbackProvider 已启用，主供应商: %s，备选: %d 个",
            llm_config.provider,
            len(fallback_presets),
        )
        return self._provider_instance
    except ImportError:
        logger.warning("nanobot-ai 未支持 FallbackProvider，降级为单供应商模式")
        self._provider_instance = primary
        return primary
```

5. 更新 `close()` 方法，同时清除缓存：

```python
def close(self) -> None:
    """关闭Provider连接，释放资源"""
    self._provider_instance = None
```

- [ ] **Step 4: 运行测试确认通过**

Run: `uv run pytest tests/unit/core/test_provider_adapter.py -v`
Expected: PASS

- [ ] **Step 5: 运行全量 ProviderAdapter 测试确认无回归**

Run: `uv run pytest tests/unit/core/test_provider_adapter.py tests/integration/module/test_config_injection.py -v`
Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add src/core/provider_adapter.py tests/unit/core/test_provider_adapter.py
git commit -m "feat: integrate FallbackProvider into RunnerProviderAdapter"
```

---

### Task 4: _build_nanobot_config_from_runner 注入 fallback

**Files:**
- Modify: `src/core/provider_adapter.py`
- Test: `tests/unit/core/test_provider_adapter.py`

- [ ] **Step 1: 写失败测试 — nanobot Config 包含 fallback_models**

在 `tests/unit/core/test_provider_adapter.py` 的 `TestRunnerProviderAdapterFallback` 类中追加：

```python
def test_build_nanobot_config_includes_fallback(self):
    config = self._make_mock_config_with_fallback()
    config.load_config.return_value = {
        "version": "0.9.5",
        "data_dir": "/data",
        "llm_provider": "siliconflow",
        "llm_model": "Qwen/Qwen3-235B-A22B",
        "llm_base_url": "https://api.siliconflow.cn/v1",
        "fallback_models": ["nvidia-llama4"],
        "model_presets": {
            "nvidia-llama4": {
                "provider": "nvidia",
                "model": "meta/llama-4-maverick-17b-128e-instruct-maas",
                "base_url": "https://integrate.api.nvidia.com/v1",
            },
        },
    }
    adapter = RunnerProviderAdapter(config)
    with patch.dict(os.environ, {"NANOBOT_LLM_API_KEY": "sk-test"}, clear=False):
        with patch.dict(os.environ, {"NANOBOT_LLM_API_KEY_NVIDIA": "nvapi-test"}, clear=False):
            nb_config = adapter._get_or_create_nanobot_config()
            defaults = nb_config.agents.defaults
            assert hasattr(defaults, "fallback_models")
            assert len(defaults.fallback_models) == 1
```

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/unit/core/test_provider_adapter.py::TestRunnerProviderAdapterFallback::test_build_nanobot_config_includes_fallback -v`
Expected: FAIL — nanobot Config 的 `agents.defaults` 不包含 `fallback_models`

- [ ] **Step 3: 实现 — _build_nanobot_config_from_runner 注入 fallback**

修改 `src/core/provider_adapter.py` 中的 `_build_nanobot_config_from_runner()` 方法。

在构建 `AgentsConfig` 时，从 config.json 读取 `fallback_models` 和 `model_presets`，注入到 nanobot Config：

在 `agents = AgentsConfig(...)` 构建之后，设置 fallback_models：

```python
runner_config = self._runner_config.load_config()
fallback_names = runner_config.get("fallback_models", [])
if fallback_names:
    from nanobot.config.schema import InlineFallbackConfig, ModelPresetConfig
    presets_raw = runner_config.get("model_presets", {})
    fallback_candidates: list[str | InlineFallbackConfig] = []
    for name in fallback_names:
        preset_data = presets_raw.get(name, {})
        provider = preset_data.get("provider", "")
        model = preset_data.get("model", "")
        if provider and model:
            fallback_candidates.append(InlineFallbackConfig(
                model=model,
                provider=provider,
            ))
    if fallback_candidates:
        setattr(defaults, "fallback_models", fallback_candidates)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `uv run pytest tests/unit/core/test_provider_adapter.py::TestRunnerProviderAdapterFallback -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/core/provider_adapter.py tests/unit/core/test_provider_adapter.py
git commit -m "feat: inject fallback_models into nanobot Config from runner config"
```

---

### Task 5: 初始化向导 — 备选供应商配置交互

**Files:**
- Modify: `src/core/init/prompts.py`
- Test: `tests/unit/core/test_init_prompts.py`

- [ ] **Step 1: 写失败测试 — run_fallback_wizard 返回正确结构**

在 `tests/unit/core/test_init_prompts.py` 末尾追加：

```python
class TestInitPromptsFallback:
    def test_run_fallback_wizard_no_questionary(self):
        with patch.dict("sys.modules", {"questionary": None}):
            result = InitPrompts.run_fallback_wizard(
                primary_provider="siliconflow"
            )
            assert result["_model_presets"] == {}
            assert result["_fallback_models"] == []

    def test_run_fallback_wizard_user_declines(self):
        mock_q = MagicMock()
        mock_q.confirm.return_value.ask.return_value = False

        with patch.dict("sys.modules", {"questionary": mock_q}):
            result = InitPrompts.run_fallback_wizard(
                primary_provider="siliconflow"
            )
            assert result["_fallback_models"] == []

    def test_run_fallback_wizard_adds_one_fallback(self):
        mock_q = MagicMock()
        mock_q.confirm.return_value.ask.side_effect = [True, False]
        mock_q.select.return_value.ask.return_value = "nvidia"
        mock_q.text.return_value.ask.side_effect = [
            "meta/llama-4-maverick-17b-128e-instruct-maas",
            "https://integrate.api.nvidia.com/v1",
        ]
        mock_q.password.return_value.ask.return_value = "nvapi-test"

        with patch.dict("sys.modules", {"questionary": mock_q}):
            result = InitPrompts.run_fallback_wizard(
                primary_provider="siliconflow"
            )
            assert len(result["_fallback_models"]) == 1
            assert "nvidia" in result["_fallback_models"][0]
            assert "NANOBOT_LLM_API_KEY_NVIDIA" in result
            assert result["NANOBOT_LLM_API_KEY_NVIDIA"] == "nvapi-test"

    def test_generate_preset_name(self):
        name = InitPrompts._generate_preset_name("nvidia", "meta/llama-4-maverick")
        assert name == "nvidia-llama-4-maverick"

    def test_generate_preset_name_short_model(self):
        name = InitPrompts._generate_preset_name("zhipu", "glm-4.7-flash")
        assert name == "zhipu-glm-4.7-flash"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/unit/core/test_init_prompts.py::TestInitPromptsFallback -v`
Expected: FAIL — `InitPrompts` 没有 `run_fallback_wizard` 和 `_generate_preset_name` 方法

- [ ] **Step 3: 实现 — InitPrompts 新增 fallback 向导方法**

修改 `src/core/init/prompts.py`，在 `run_llm_provider_wizard()` 方法之后新增：

```python
@staticmethod
def run_fallback_wizard(primary_provider: str) -> dict[str, Any]:
    """运行备选供应商配置向导

    在主供应商配置完成后调用，引导用户添加备选供应商。

    Args:
        primary_provider: 主供应商名称，用于排除重复

    Returns:
        dict[str, Any]: 包含 _model_presets、_fallback_models 和备选 API Key 的字典
    """
    model_presets: dict[str, dict[str, str]] = {}
    fallback_models: list[str] = []
    env_vars: dict[str, str] = {}
    configured_providers: set[str] = {primary_provider}

    try:
        import questionary

        enable = questionary.confirm(
            "是否配置备选供应商？（主供应商故障时自动切换）",
            default=False,
        ).ask()

        if not enable:
            return {"_model_presets": model_presets, "_fallback_models": fallback_models, **env_vars}

        fallback_index = 0
        while True:
            fallback_index += 1

            available = [
                p for p in ["nvidia", "openrouter", "zhipu", "siliconflow", "deepseek", "other"]
                if p not in configured_providers
            ]
            if not available:
                print("所有已知供应商已配置")
                break

            provider = questionary.select(
                f"── 备选供应商 #{fallback_index} ──\n选择备选 Provider:",
                choices=available,
            ).ask()

            if provider is None:
                break

            model = questionary.text(
                "输入模型名称:",
                default=InitPrompts._default_model_for_provider(provider),
            ).ask()

            api_key = questionary.password(
                "输入 API Key:",
            ).ask()

            base_url = questionary.text(
                "输入 Base URL（可选，留空使用默认）:",
                default="",
            ).ask()

            preset_name = InitPrompts._generate_preset_name(provider, model or "")
            model_presets[preset_name] = {
                "provider": provider,
                "model": model or InitPrompts._default_model_for_provider(provider),
            }
            if base_url:
                model_presets[preset_name]["base_url"] = base_url

            fallback_models.append(preset_name)
            configured_providers.add(provider)

            if api_key:
                env_key = f"NANOBOT_LLM_API_KEY_{provider.upper()}"
                env_vars[env_key] = api_key

            print(f"✅ 备选供应商 #{fallback_index} 已添加：{provider} / {model}")

            continue_add = questionary.confirm(
                "是否继续添加备选供应商？",
                default=False,
            ).ask()

            if not continue_add:
                break

        if fallback_models:
            print("✅ Fallback 链配置完成：")
            print(f"  主: {primary_provider}")
            for i, name in enumerate(fallback_models, 1):
                preset = model_presets[name]
                print(f"  备{i}: {preset['provider']} / {preset['model']}")

        return {"_model_presets": model_presets, "_fallback_models": fallback_models, **env_vars}

    except ImportError:
        logger.warning("questionary 未安装，跳过备选供应商配置")
        return {"_model_presets": model_presets, "_fallback_models": fallback_models, **env_vars}

@staticmethod
def _generate_preset_name(provider: str, model: str) -> str:
    """生成 model_presets 条目名

    格式：{provider}-{short_model_name}
    short_model_name 取模型名最后一段（/分隔），去除版本号后缀。

    Args:
        provider: 供应商名称
        model: 模型名称

    Returns:
        str: 预设名称
    """
    short = model.split("/")[-1] if "/" in model else model
    short = short.split(":")[0] if ":" in short else short
    return f"{provider}-{short}"
```

- [ ] **Step 4: 运行测试确认通过**

Run: `uv run pytest tests/unit/core/test_init_prompts.py::TestInitPromptsFallback -v`
Expected: PASS

- [ ] **Step 5: 改造 run_llm_provider_wizard 和 run_full_wizard**

修改 `run_llm_provider_wizard()`，在返回字典之前调用 `run_fallback_wizard()`：

在 `run_llm_provider_wizard()` 方法的 `return` 语句之前，追加：

```python
fallback_result = InitPrompts.run_fallback_wizard(provider or "openai")
```

修改返回值，合并 fallback 结果：

```python
result = {
    "NANOBOT_LLM_PROVIDER": provider,
    "NANOBOT_LLM_MODEL": model or "gpt-4o-mini",
    "NANOBOT_LLM_API_KEY": api_key or "",
    "NANOBOT_LLM_BASE_URL": base_url or "",
}
result.update(fallback_result)
return result
```

修改 `run_full_wizard()`，在 `agent_mode` 分支中处理 `_model_presets` 和 `_fallback_models`：

在 `if agent_mode:` 块中，`config["tools"] = InitPrompts._default_tools_config()` 之后追加：

```python
llm_model_presets = llm_env.pop("_model_presets", {})
llm_fallback_models = llm_env.pop("_fallback_models", [])

if llm_model_presets:
    existing_presets = config.get("model_presets", {})
    if existing_presets is None:
        existing_presets = {}
    existing_presets.update(llm_model_presets)
    config["model_presets"] = existing_presets

if llm_fallback_models:
    config["fallback_models"] = llm_fallback_models
```

- [ ] **Step 6: 运行全部 init_prompts 测试确认通过**

Run: `uv run pytest tests/unit/core/test_init_prompts.py -v`
Expected: PASS

- [ ] **Step 7: 提交**

```bash
git add src/core/init/prompts.py tests/unit/core/test_init_prompts.py
git commit -m "feat: add fallback provider wizard to init prompts"
```

---

### Task 6: ConfigGenerator env 生成扩展

**Files:**
- Modify: `src/core/init/generator.py`
- Test: `tests/unit/core/test_fallback_config.py`

- [ ] **Step 1: 写失败测试 — generate_env_local 支持备选供应商 API Key**

在 `tests/unit/core/test_fallback_config.py` 末尾追加：

```python
from src.core.init.generator import ConfigGenerator


class TestConfigGeneratorFallbackEnv:
    def test_generate_env_local_with_fallback_keys(self):
        gen = ConfigGenerator()
        env_vars = {
            "NANOBOT_LLM_PROVIDER": "siliconflow",
            "NANOBOT_LLM_MODEL": "Qwen/Qwen3-235B-A22B",
            "NANOBOT_LLM_API_KEY": "sk-sf-xxx",
            "NANOBOT_LLM_BASE_URL": "https://api.siliconflow.cn/v1",
            "NANOBOT_LLM_API_KEY_NVIDIA": "nvapi-xxx",
            "NANOBOT_LLM_API_KEY_OPENROUTER": "sk-or-xxx",
        }
        content = gen.generate_env_local(env_vars)
        assert "NANOBOT_LLM_API_KEY_NVIDIA=nvapi-xxx" in content
        assert "NANOBOT_LLM_API_KEY_OPENROUTER=sk-or-xxx" in content
        assert "备选供应商" in content
```

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/unit/core/test_fallback_config.py::TestConfigGeneratorFallbackEnv -v`
Expected: FAIL — 生成的 env 内容不包含备选供应商 API Key

- [ ] **Step 3: 实现 — generate_env_local 扩展**

修改 `src/core/init/generator.py` 的 `generate_env_local()` 方法。

在主供应商 LLM 配置输出之后、飞书配置之前，新增备选供应商 API Key 输出：

```python
fallback_keys = {
    k: v for k, v in env_vars.items()
    if k.startswith("NANOBOT_LLM_API_KEY_") and k != "NANOBOT_LLM_API_KEY"
}
if fallback_keys:
    lines.append("\n# 备选供应商 API Key\n")
    for key, value in fallback_keys.items():
        lines.append(f"{key}={value}\n")
```

- [ ] **Step 4: 运行测试确认通过**

Run: `uv run pytest tests/unit/core/test_fallback_config.py::TestConfigGeneratorFallbackEnv -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/core/init/generator.py tests/unit/core/test_fallback_config.py
git commit -m "feat: extend ConfigGenerator to support fallback API keys in env"
```

---

### Task 7: model list 命令增强

**Files:**
- Modify: `src/cli/handlers/model_handler.py`
- Modify: `src/cli/commands/model.py`
- Test: `tests/unit/core/test_fallback_config.py`

- [ ] **Step 1: 写失败测试 — ModelHandler 返回 fallback 信息**

在 `tests/unit/core/test_fallback_config.py` 末尾追加：

```python
from src.cli.handlers.model_handler import ModelHandler


class TestModelHandlerFallback:
    def test_list_presets_with_fallback_info(self):
        handler = ModelHandler.__new__(ModelHandler)
        mock_config = MagicMock()
        mock_config.load_config.return_value = {
            "model_presets": {
                "nvidia-llama4": {
                    "provider": "nvidia",
                    "model": "meta/llama-4-maverick-17b-128e-instruct-maas",
                },
                "openrouter-gemini": {
                    "provider": "openrouter",
                    "model": "google/gemini-2.5-flash-preview",
                },
            },
            "fallback_models": ["nvidia-llama4"],
        }
        handler.context = MagicMock()
        handler.context.config = mock_config

        presets = handler.list_presets()
        nvidia_preset = next(p for p in presets if p["name"] == "nvidia-llama4")
        assert nvidia_preset["is_fallback"] is True
        assert nvidia_preset["fallback_order"] == 1

        openrouter_preset = next(p for p in presets if p["name"] == "openrouter-gemini")
        assert openrouter_preset["is_fallback"] is False
        assert openrouter_preset["fallback_order"] is None
```

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/unit/core/test_fallback_config.py::TestModelHandlerFallback -v`
Expected: FAIL — `list_presets()` 返回的字典不包含 `is_fallback` 和 `fallback_order` 字段

- [ ] **Step 3: 实现 — ModelHandler 返回 fallback 信息**

修改 `src/cli/handlers/model_handler.py` 的 `list_presets()` 方法：

```python
def list_presets(self) -> list[dict[str, Any]]:
    config = self.context.config
    full_config = config.load_config()
    presets = full_config.get("model_presets", {})
    if presets is None:
        return []

    fallback_names: list[str] = full_config.get("fallback_models") or []
    fallback_order_map = {name: idx + 1 for idx, name in enumerate(fallback_names)}

    result: list[dict[str, Any]] = []
    for name, preset in presets.items():
        result.append(
            {
                "name": name,
                "provider": preset.get("provider", ""),
                "model": preset.get("model", ""),
                "temperature": preset.get("temperature"),
                "is_fallback": name in fallback_order_map,
                "fallback_order": fallback_order_map.get(name),
            }
        )
    return result
```

- [ ] **Step 4: 修改 model list 命令展示**

修改 `src/cli/commands/model.py` 的 `list_presets()` 命令：

在 table 列定义中，将 "Temperature" 列替换为 "Role" 列，或在其后新增 "Fallback" 列：

```python
table.add_column("预设名称", width=15)
table.add_column("Provider", width=15)
table.add_column("模型", width=30)
table.add_column("Temperature", width=12)
table.add_column("Fallback", width=10)

for preset in presets:
    temp = preset.get("temperature")
    temp_str = f"{temp}" if temp is not None else "-"
    fallback_str = f"备{preset['fallback_order']}" if preset.get("is_fallback") else "-"
    table.add_row(
        preset["name"],
        preset["provider"],
        preset["model"],
        temp_str,
        fallback_str,
    )
```

- [ ] **Step 5: 运行测试确认通过**

Run: `uv run pytest tests/unit/core/test_fallback_config.py::TestModelHandlerFallback -v`
Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add src/cli/handlers/model_handler.py src/cli/commands/model.py tests/unit/core/test_fallback_config.py
git commit -m "feat: show fallback info in model list command"
```

---

### Task 8: 全量测试与 lint 检查

**Files:**
- 无新增修改

- [ ] **Step 1: 运行全量单元测试**

Run: `uv run pytest tests/unit/ -v`
Expected: PASS

- [ ] **Step 2: 运行 ruff format**

Run: `uv run ruff format src/ tests/`
Expected: 无格式问题

- [ ] **Step 3: 运行 ruff check**

Run: `uv run ruff check src/ tests/`
Expected: 无 lint 错误

- [ ] **Step 4: 运行 mypy 类型检查**

Run: `uv run mypy src/ --ignore-missing-imports`
Expected: 无类型错误

- [ ] **Step 5: 运行集成测试**

Run: `uv run pytest tests/integration/ -v`
Expected: PASS

- [ ] **Step 6: 最终提交**

```bash
git add -A
git commit -m "chore: lint and typecheck pass for fallback provider feature"
```
