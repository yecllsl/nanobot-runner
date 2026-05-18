import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.core.base.exceptions import LLMError
from src.core.config.llm_config import LLMConfig
from src.core.config.manager import ConfigManager
from src.core.provider_adapter import AgentDefaults, RunnerProviderAdapter


@pytest.fixture
def mock_runner_config():
    config = MagicMock(spec=ConfigManager)
    config.has_llm_config.return_value = True
    config.get_llm_config.return_value = {
        "provider": "openai",
        "model": "gpt-4o-mini",
        "api_key": "test-key",
        "base_url": "https://api.openai.com",
        "max_iterations": 10,
        "context_window_tokens": 128000,
        "context_block_limit": 10,
        "max_tool_result_chars": 32000,
    }
    config.get.return_value = None
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

        with patch.object(adapter, "_try_load_nanobot_config", return_value=False):
            with pytest.raises(LLMError, match="未配置LLM"):
                adapter.get_llm_config()

    def test_get_llm_config_fallback_to_nanobot(self):
        config = MagicMock(spec=ConfigManager)
        config.has_llm_config.return_value = False
        adapter = RunnerProviderAdapter(config)

        mock_nanobot_config = MagicMock()
        mock_nanobot_config.agents.defaults.model = "gpt-4"
        mock_nanobot_config.agents.defaults.max_tool_iterations = 15
        mock_nanobot_config.agents.defaults.context_window_tokens = 128000
        mock_nanobot_config.agents.defaults.context_block_limit = 10
        mock_nanobot_config.agents.defaults.max_tool_result_chars = 32000
        mock_nanobot_config.providers.default = "openai"
        mock_provider_cfg = MagicMock()
        mock_provider_cfg.api_key = "nanobot-key"
        mock_provider_cfg.base_url = "https://api.openai.com"
        mock_nanobot_config.providers = MagicMock()
        mock_nanobot_config.providers.default = "openai"
        mock_nanobot_config.providers.openai = mock_provider_cfg

        adapter._nanobot_config = mock_nanobot_config

        with patch.object(adapter, "_try_load_nanobot_config", return_value=True):
            llm_config = adapter.get_llm_config()
            assert llm_config.model == "gpt-4"
            assert llm_config.api_key == "nanobot-key"


class TestRunnerProviderAdapterIsAvailable:
    def test_is_available_with_runner_config(self, mock_runner_config):
        adapter = RunnerProviderAdapter(mock_runner_config)
        assert adapter.is_available() is True

    def test_is_available_no_config(self):
        config = MagicMock(spec=ConfigManager)
        config.has_llm_config.return_value = False
        adapter = RunnerProviderAdapter(config)

        with patch.object(adapter, "_try_load_nanobot_config", return_value=False):
            assert adapter.is_available() is False

    def test_is_available_with_nanobot_fallback(self):
        config = MagicMock(spec=ConfigManager)
        config.has_llm_config.return_value = False
        adapter = RunnerProviderAdapter(config)

        with patch.object(adapter, "_try_load_nanobot_config", return_value=True):
            assert adapter.is_available() is True


class TestRunnerProviderAdapterGetAgentDefaults:
    def test_get_agent_defaults(self, mock_runner_config):
        adapter = RunnerProviderAdapter(mock_runner_config)
        defaults = adapter.get_agent_defaults()
        assert isinstance(defaults, AgentDefaults)
        assert defaults.model == "gpt-4o-mini"
        assert defaults.max_tool_iterations == 10


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
        config.has_llm_config.side_effect = Exception("error")
        adapter = RunnerProviderAdapter(config)
        assert adapter._has_runner_llm_config() is False


class TestRunnerProviderAdapterTryLoadNanobotConfig:
    def test_try_load_already_loaded(self, mock_runner_config):
        adapter = RunnerProviderAdapter(mock_runner_config)
        adapter._nanobot_config = MagicMock()
        assert adapter._try_load_nanobot_config() is True

    def test_try_load_import_error(self, mock_runner_config):
        adapter = RunnerProviderAdapter(mock_runner_config)

        with patch(
            "src.core.provider_adapter.RunnerProviderAdapter._try_load_nanobot_config",
            return_value=False,
        ):
            result = adapter._try_load_nanobot_config()
            assert result is False


class TestRunnerProviderAdapterFromRunnerConfig:
    def test_from_runner_config(self, mock_runner_config):
        adapter = RunnerProviderAdapter(mock_runner_config)
        llm_config = adapter._from_runner_config()
        assert llm_config.provider == "openai"
        assert llm_config.model == "gpt-4o-mini"
        assert llm_config.api_key == "test-key"
        assert llm_config.base_url == "https://api.openai.com"


class TestRunnerProviderAdapterFromNanobotConfig:
    def test_from_nanobot_config_no_config(self, mock_runner_config):
        adapter = RunnerProviderAdapter(mock_runner_config)
        with pytest.raises(LLMError, match="nanobot配置未加载"):
            adapter._from_nanobot_config()

    def test_from_nanobot_config_with_config(self, mock_runner_config):
        adapter = RunnerProviderAdapter(mock_runner_config)

        mock_cfg = MagicMock()
        mock_cfg.agents.defaults.model = "gpt-4"
        mock_cfg.agents.defaults.max_tool_iterations = 15
        mock_cfg.agents.defaults.context_window_tokens = 128000
        mock_cfg.agents.defaults.context_block_limit = 10
        mock_cfg.agents.defaults.max_tool_result_chars = 32000
        mock_cfg.providers.default = "openai"
        mock_provider = MagicMock()
        mock_provider.api_key = "key-123"
        mock_provider.base_url = "https://api.openai.com"
        mock_cfg.providers.openai = mock_provider

        adapter._nanobot_config = mock_cfg
        llm_config = adapter._from_nanobot_config()
        assert llm_config.provider == "openai"
        assert llm_config.model == "gpt-4"
        assert llm_config.api_key == "key-123"

    def test_from_nanobot_config_no_api_key_uses_env(self, mock_runner_config):
        adapter = RunnerProviderAdapter(mock_runner_config)

        mock_cfg = MagicMock()
        mock_cfg.agents.defaults.model = "gpt-4"
        mock_cfg.agents.defaults.max_tool_iterations = 15
        mock_cfg.agents.defaults.context_window_tokens = 128000
        mock_cfg.agents.defaults.context_block_limit = 10
        mock_cfg.agents.defaults.max_tool_result_chars = 32000
        mock_cfg.providers.default = "openai"
        mock_provider = MagicMock()
        mock_provider.api_key = None
        mock_provider.base_url = None
        mock_cfg.providers.openai = mock_provider

        adapter._nanobot_config = mock_cfg
        with patch.dict(os.environ, {"NANOBOT_LLM_API_KEY": "env-key"}):
            llm_config = adapter._from_nanobot_config()
            assert llm_config.api_key == "env-key"


class TestParseEnvFile:
    def test_parse_env_file(self, tmp_path: Path):
        env_file = tmp_path / ".env"
        env_file.write_text(
            "KEY1=value1\nKEY2=value2\n# comment\n\nKEY3='quoted'\n",
            encoding="utf-8",
        )
        result = RunnerProviderAdapter._parse_env_file(env_file)
        assert result["KEY1"] == "value1"
        assert result["KEY2"] == "value2"
        assert result["KEY3"] == "quoted"

    def test_parse_env_file_no_equals(self, tmp_path: Path):
        env_file = tmp_path / ".env"
        env_file.write_text("NOEQUALS\nKEY=val\n", encoding="utf-8")
        result = RunnerProviderAdapter._parse_env_file(env_file)
        assert "NOEQUALS" not in result
        assert result["KEY"] == "val"

    def test_parse_env_file_nonexistent(self, tmp_path: Path):
        result = RunnerProviderAdapter._parse_env_file(tmp_path / "missing.env")
        assert result == {}

    def test_parse_env_file_empty_value(self, tmp_path: Path):
        env_file = tmp_path / ".env"
        env_file.write_text("EMPTY=\nKEY=val\n", encoding="utf-8")
        result = RunnerProviderAdapter._parse_env_file(env_file)
        assert "EMPTY" not in result
        assert result["KEY"] == "val"
