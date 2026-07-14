from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.core.base.exceptions import LLMError, NanobotRunnerError
from src.core.config.llm_config import LLMConfig
from src.core.config.manager import ConfigManager
from src.core.provider_adapter import AgentDefaults, RunnerProviderAdapter


@pytest.fixture
def mock_runner_config():
    """模拟带 nanobot_config.json 的 ConfigManager（v0.32.0 配置物理分离）"""
    config = MagicMock(spec=ConfigManager)
    config.has_llm_config.return_value = True
    config.load_nanobot_config.return_value = {
        "providers": {
            "default": "openai",
            "openai": {
                "apiKey": "test-key",
                "apiBase": "https://api.openai.com",
                "apiType": "auto",
            },
        },
        "agents": {
            "defaults": {
                "model": "gpt-4o-mini",
                "maxToolIterations": 10,
                "contextWindowTokens": 128000,
            }
        },
    }

    def _mock_get(key: str, default: Any = None) -> Any:
        if key == "timezone":
            return "Asia/Shanghai"
        return default

    config.get.side_effect = _mock_get
    config.base_dir = Path("/test/runner")
    return config


class TestAgentDefaults:
    def test_defaults(self):
        defaults = AgentDefaults(model="gpt-4o-mini")
        assert defaults.model == "gpt-4o-mini"
        assert defaults.max_tool_iterations == 10
        assert defaults.context_window_tokens == 128000
        assert defaults.context_block_limit == 10
        assert defaults.max_tool_result_chars == 32000

    def test_custom_values(self):
        defaults = AgentDefaults(
            model="claude-3",
            max_tool_iterations=20,
            context_window_tokens=256000,
            context_block_limit=5,
            max_tool_result_chars=16000,
        )
        assert defaults.model == "claude-3"
        assert defaults.max_tool_iterations == 20
        assert defaults.context_window_tokens == 256000


class TestRunnerProviderAdapterGetLlmConfig:
    def test_get_llm_config_from_runner(self, mock_runner_config):
        adapter = RunnerProviderAdapter(mock_runner_config)
        config = adapter.get_llm_config()
        assert isinstance(config, LLMConfig)
        assert config.provider == "openai"
        assert config.model == "gpt-4o-mini"
        assert config.api_key == "test-key"

    def test_get_llm_config_no_runner_config(self):
        config = MagicMock(spec=ConfigManager)
        config.has_llm_config.return_value = False
        adapter = RunnerProviderAdapter(config)

        with pytest.raises(LLMError, match="未配置LLM"):
            adapter.get_llm_config()


class TestRunnerProviderAdapterIsAvailable:
    def test_is_available_with_runner_config(self, mock_runner_config):
        adapter = RunnerProviderAdapter(mock_runner_config)
        assert adapter.is_available() is True

    def test_is_available_no_config(self):
        config = MagicMock(spec=ConfigManager)
        config.has_llm_config.return_value = False
        adapter = RunnerProviderAdapter(config)
        assert adapter.is_available() is False


class TestRunnerProviderAdapterGetAgentDefaults:
    def test_get_agent_defaults(self, mock_runner_config):
        adapter = RunnerProviderAdapter(mock_runner_config)
        defaults = adapter.get_agent_defaults()
        assert isinstance(defaults, AgentDefaults)
        assert defaults.model == "gpt-4o-mini"
        assert defaults.max_tool_iterations == 10

    def test_get_agent_defaults_includes_timezone(self, mock_runner_config):
        """回归测试: AgentDefaults 应包含项目配置的 timezone

        根因: config.json 配置了 "timezone": "Asia/Shanghai"，但
        RunnerProviderAdapter.get_agent_defaults() 未返回 timezone，
        导致 AgentLoop 默认使用 UTC。
        """
        adapter = RunnerProviderAdapter(mock_runner_config)
        defaults = adapter.get_agent_defaults()
        assert defaults.timezone == "Asia/Shanghai"

    def test_get_agent_defaults_timezone_fallback(self):
        """未配置 timezone 时，AgentDefaults 应回退到默认值"""
        config = MagicMock(spec=ConfigManager)
        config.has_llm_config.return_value = True
        config.load_nanobot_config.return_value = {
            "providers": {
                "default": "openai",
                "openai": {"apiKey": "test-key"},
            },
            "agents": {
                "defaults": {
                    "model": "gpt-4o-mini",
                    "maxToolIterations": 10,
                    "contextWindowTokens": 128000,
                }
            },
        }
        config.get.return_value = None

        adapter = RunnerProviderAdapter(config)
        defaults = adapter.get_agent_defaults()
        assert defaults.timezone == "UTC"


class TestRunnerProviderAdapterClose:
    def test_close_clears_provider(self, mock_runner_config):
        adapter = RunnerProviderAdapter(mock_runner_config)
        adapter._provider_instance = MagicMock()
        adapter.close()
        assert adapter._provider_instance is None


class TestRunnerProviderAdapterGetProviderInstance:
    def test_get_provider_instance_cached(self, mock_runner_config):
        adapter = RunnerProviderAdapter(mock_runner_config)
        cached = MagicMock()
        adapter._provider_instance = cached
        assert adapter.get_provider_instance() is cached

    def test_get_provider_instance_import_error(self, mock_runner_config):
        adapter = RunnerProviderAdapter(mock_runner_config)

        with patch.dict("sys.modules", {}):
            with patch("builtins.__import__", side_effect=ImportError("no nanobot")):
                with pytest.raises(LLMError, match="无法导入nanobot模块"):
                    adapter.get_provider_instance()


class TestRunnerProviderAdapterHasRunnerLlmConfig:
    def test_has_runner_llm_config_true(self, mock_runner_config):
        adapter = RunnerProviderAdapter(mock_runner_config)
        assert adapter._has_runner_llm_config() is True

    def test_has_runner_llm_config_exception(self):
        config = MagicMock(spec=ConfigManager)
        config.has_llm_config.side_effect = NanobotRunnerError("error")
        adapter = RunnerProviderAdapter(config)
        assert adapter._has_runner_llm_config() is False


class TestFromNanobotConfig:
    """测试 _from_nanobot_config 方法（v0.32.0 重命名自 _from_runner_config）"""

    def test_from_nanobot_config(self, mock_runner_config):
        adapter = RunnerProviderAdapter(mock_runner_config)
        llm_config = adapter._from_nanobot_config()
        assert llm_config.provider == "openai"
        assert llm_config.model == "gpt-4o-mini"
        assert llm_config.api_key == "test-key"
        assert llm_config.base_url == "https://api.openai.com"


class TestRunnerProviderAdapterFallback:
    """FallbackProvider 集成测试"""

    def _make_mock_config_with_fallback(self):
        config = MagicMock(spec=ConfigManager)
        config.has_llm_config.return_value = True
        config.load_nanobot_config.return_value = {
            "providers": {
                "default": "siliconflow",
                "siliconflow": {
                    "apiKey": "sk-sf-test",
                    "apiBase": "https://api.siliconflow.cn/v1",
                },
                "nvidia": {
                    "apiKey": "nvapi-test",
                    "apiBase": "https://integrate.api.nvidia.com/v1",
                },
            },
            "agents": {
                "defaults": {
                    "model": "Qwen/Qwen3-235B-A22B",
                    "maxToolIterations": 200,
                    "contextWindowTokens": 200000,
                    "fallbackModels": [
                        {
                            "provider": "nvidia",
                            "model": "meta/llama-4-maverick-17b-128e-instruct-maas",
                        },
                    ],
                }
            },
        }
        config.get.return_value = None
        config.base_dir = Path("/test/runner")
        return config

    def test_no_fallback_returns_plain_provider(self, mock_runner_config):
        adapter = RunnerProviderAdapter(mock_runner_config)
        with patch.object(adapter, "_create_primary_provider") as mock_create:
            mock_provider = MagicMock()
            mock_create.return_value = mock_provider
            result = adapter.get_provider_instance()
            assert result is mock_provider

    def test_with_fallback_returns_fallback_provider(self):
        config = self._make_mock_config_with_fallback()
        adapter = RunnerProviderAdapter(config)
        mock_primary = MagicMock()
        mock_primary.get_default_model.return_value = "Qwen/Qwen3-235B-A22B"
        with patch.object(
            adapter, "_create_primary_provider", return_value=mock_primary
        ):
            with patch(
                "nanobot.providers.fallback_provider.FallbackProvider"
            ) as MockFB:
                mock_fb_instance = MagicMock()
                MockFB.return_value = mock_fb_instance
                result = adapter.get_provider_instance()
                MockFB.assert_called_once()
                assert result is mock_fb_instance

    def test_fallback_import_error_degrades_to_primary(self):
        config = self._make_mock_config_with_fallback()
        adapter = RunnerProviderAdapter(config)
        mock_primary = MagicMock()
        with patch.object(
            adapter, "_create_primary_provider", return_value=mock_primary
        ):
            with patch.dict(
                "sys.modules", {"nanobot.providers.fallback_provider": None}
            ):
                result = adapter.get_provider_instance()
                assert result is mock_primary

    def test_resolve_fallback_presets_converts_config(self):
        config = self._make_mock_config_with_fallback()
        adapter = RunnerProviderAdapter(config)
        presets = adapter._resolve_fallback_presets()
        assert len(presets) == 1
        assert presets[0].model == "meta/llama-4-maverick-17b-128e-instruct-maas"
        assert presets[0].provider == "nvidia"

    def test_resolve_fallback_presets_skips_missing_model_or_provider(self):
        """model 或 provider 缺失的 fallback 条目应被跳过"""
        config = self._make_mock_config_with_fallback()
        config.load_nanobot_config.return_value = {
            "providers": {"default": "openai"},
            "agents": {
                "defaults": {
                    "fallbackModels": [
                        {"provider": "nvidia"},  # 缺少 model
                        {"model": "llama-4"},  # 缺少 provider
                    ],
                }
            },
        }
        adapter = RunnerProviderAdapter(config)
        presets = adapter._resolve_fallback_presets()
        assert len(presets) == 0


class TestProviderAdapterBranchCoverage:
    """补充分支覆盖测试：异常处理、ImportError 回退、边界条件"""

    def test_resolve_fallback_presets_import_error(self, mock_runner_config):
        """测试 _resolve_fallback_presets 在 ImportError 时返回空列表"""
        adapter = RunnerProviderAdapter(mock_runner_config)
        with patch.dict("sys.modules", {"nanobot.config.schema": None}):
            with patch("builtins.__import__", side_effect=ImportError("no schema")):
                presets = adapter._resolve_fallback_presets()
                assert presets == []

    def test_create_primary_provider_import_error(self, mock_runner_config):
        """测试 _create_primary_provider 在 ImportError 时抛出 LLMError"""
        adapter = RunnerProviderAdapter(mock_runner_config)
        llm_config = LLMConfig(
            provider="openai",
            model="gpt-4o-mini",
            api_key="test-key",
            base_url="https://api.openai.com",
        )
        with patch("builtins.__import__", side_effect=ImportError("no nanobot")):
            with pytest.raises(LLMError, match="无法导入nanobot模块"):
                adapter._create_primary_provider(llm_config)

    def test_create_primary_provider_value_error(self, mock_runner_config):
        """测试 _create_primary_provider 在 ValueError 时抛出 LLMError"""
        adapter = RunnerProviderAdapter(mock_runner_config)
        llm_config = LLMConfig(
            provider="openai",
            model="gpt-4o-mini",
            api_key="test-key",
            base_url="https://api.openai.com",
        )
        with patch(
            "nanobot.providers.registry.find_by_name",
            side_effect=ValueError("provider not found"),
            create=True,
        ):
            with patch(
                "nanobot.providers.openai_compat_provider.OpenAICompatProvider",
                create=True,
            ):
                with pytest.raises(LLMError, match="创建Provider失败"):
                    adapter._create_primary_provider(llm_config)

    def test_create_fallback_provider_builds_provider(self, mock_runner_config):
        """测试 _create_fallback_provider 构造 fallback Provider 实例"""
        config = MagicMock(spec=ConfigManager)
        config.has_llm_config.return_value = True
        config.load_nanobot_config.return_value = {
            "providers": {
                "default": "openai",
                "openai": {
                    "apiKey": "test-key",
                    "apiBase": "https://api.openai.com",
                },
                "nvidia": {
                    "apiKey": "nvapi-test",
                    "apiBase": "https://api.nvidia.com",
                },
            },
            "agents": {
                "defaults": {
                    "model": "gpt-4o-mini",
                }
            },
        }
        config.base_dir = Path("/test")

        adapter = RunnerProviderAdapter(config)
        preset = MagicMock()
        preset.provider = "nvidia"
        preset.model = "llama-4"

        mock_provider_cls = MagicMock()
        mock_spec = MagicMock()
        with patch(
            "nanobot.providers.openai_compat_provider.OpenAICompatProvider",
            mock_provider_cls,
        ):
            with patch(
                "nanobot.providers.registry.find_by_name", return_value=mock_spec
            ):
                result = adapter._create_fallback_provider(preset)
                mock_provider_cls.assert_called_once()
                assert result is mock_provider_cls.return_value


class TestRunnerProviderAdapterFromNanobotConfig:
    """测试从 nanobot_config.json 读取配置（v0.32.0）"""

    @pytest.fixture
    def mock_config_with_nanobot(self):
        """模拟带 nanobot_config.json 的 ConfigManager"""
        config = MagicMock(spec=ConfigManager)
        config.load_nanobot_config.return_value = {
            "providers": {
                "default": "custom",
                "custom": {
                    "apiKey": "sk-test-key",
                    "apiBase": "https://api.test.com/v1",
                    "apiType": "auto",
                },
            },
            "agents": {
                "defaults": {
                    "model": "test-model",
                    "maxToolIterations": 200,
                    "contextWindowTokens": 200000,
                }
            },
        }
        config.has_llm_config.return_value = True

        def _mock_get(key: str, default: Any = None) -> Any:
            if key == "timezone":
                return "Asia/Shanghai"
            return default

        config.get.side_effect = _mock_get
        config.base_dir = Path("/test/runner")
        return config

    def test_get_llm_config_from_nanobot(self, mock_config_with_nanobot):
        """从 nanobot_config.json 读取 LLM 配置"""
        adapter = RunnerProviderAdapter(mock_config_with_nanobot)
        llm_config = adapter.get_llm_config()
        assert llm_config.provider == "custom"
        assert llm_config.model == "test-model"
        assert llm_config.api_key == "sk-test-key"
        assert llm_config.base_url == "https://api.test.com/v1"

    def test_get_agent_defaults_from_nanobot(self, mock_config_with_nanobot):
        """从 nanobot_config.json 读取 Agent 默认配置"""
        adapter = RunnerProviderAdapter(mock_config_with_nanobot)
        defaults = adapter.get_agent_defaults()
        assert defaults.model == "test-model"
        assert defaults.max_tool_iterations == 200
        assert defaults.context_window_tokens == 200000
        assert defaults.timezone == "Asia/Shanghai"

    def test_is_available_true(self, mock_config_with_nanobot):
        """nanobot_config.json 有效时 is_available 返回 True"""
        adapter = RunnerProviderAdapter(mock_config_with_nanobot)
        assert adapter.is_available() is True

    def test_is_available_false_no_nanobot_config(self):
        """nanobot_config.json 无效时 is_available 返回 False"""
        config = MagicMock(spec=ConfigManager)
        config.has_llm_config.return_value = False
        adapter = RunnerProviderAdapter(config)
        assert adapter.is_available() is False

    def test_get_llm_config_raises_when_no_config(self):
        """无 nanobot_config.json 时 get_llm_config 抛出 LLMError"""
        config = MagicMock(spec=ConfigManager)
        config.has_llm_config.return_value = False
        adapter = RunnerProviderAdapter(config)
        with pytest.raises(LLMError, match="未配置LLM"):
            adapter.get_llm_config()
