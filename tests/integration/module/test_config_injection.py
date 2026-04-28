from unittest.mock import MagicMock, patch

import pytest

from src.core.llm_config import LLMConfig
from src.core.provider_adapter import AgentDefaults, RunnerProviderAdapter


class TestConfigInjectionIntegration:
    """配置注入集成测试

    验证从ConfigManager → RunnerProviderAdapter → LLMConfig/AgentDefaults
    的完整配置注入链路。
    """

    def _make_mock_config(
        self,
        provider: str = "openai",
        model: str = "gpt-4o-mini",
        api_key: str | None = "sk-test",
        base_url: str | None = None,
    ) -> MagicMock:
        mock = MagicMock()
        mock.has_llm_config.return_value = bool(provider and model)
        mock.get_llm_config.return_value = {
            "provider": provider,
            "model": model,
            "api_key": api_key,
            "base_url": base_url,
        }
        return mock

    def test_full_injection_chain(self) -> None:
        """验证完整配置注入链路：ConfigManager → Adapter → LLMConfig"""
        mock_config = self._make_mock_config(
            provider="openai",
            model="gpt-4o-mini",
            api_key="sk-test-key",
            base_url="https://api.openai.com",
        )

        adapter = RunnerProviderAdapter(mock_config)

        llm_config = adapter.get_llm_config()
        assert isinstance(llm_config, LLMConfig)
        assert llm_config.provider == "openai"
        assert llm_config.model == "gpt-4o-mini"
        assert llm_config.api_key == "sk-test-key"
        assert llm_config.base_url == "https://api.openai.com"

    def test_injection_chain_to_agent_defaults(self) -> None:
        """验证配置注入链路：ConfigManager → Adapter → AgentDefaults"""
        mock_config = self._make_mock_config()

        adapter = RunnerProviderAdapter(mock_config)

        agent_defaults = adapter.get_agent_defaults()
        assert isinstance(agent_defaults, AgentDefaults)
        assert agent_defaults.model == "gpt-4o-mini"
        assert agent_defaults.max_tool_iterations == 10
        assert agent_defaults.context_window_tokens == 128000

    def test_injection_chain_availability_check(self) -> None:
        """验证配置可用性检查链路"""
        mock_config = self._make_mock_config()
        adapter = RunnerProviderAdapter(mock_config)
        assert adapter.is_available()

    @patch.object(RunnerProviderAdapter, "_try_load_nanobot_config", return_value=False)
    def test_injection_chain_missing_config(self, mock_nanobot: MagicMock) -> None:
        """验证配置缺失时的错误处理"""
        mock_config = MagicMock()
        mock_config.has_llm_config.return_value = False
        mock_config.get_llm_config.return_value = {
            "provider": "",
            "model": "",
            "api_key": None,
            "base_url": None,
        }

        adapter = RunnerProviderAdapter(mock_config)
        assert not adapter.is_available()

    def test_injection_chain_env_override(self) -> None:
        """验证环境变量覆盖配置的链路"""
        mock_config = MagicMock()
        mock_config.has_llm_config.return_value = True
        mock_config.get_llm_config.return_value = {
            "provider": "anthropic",
            "model": "claude-3-haiku",
            "api_key": "sk-override",
            "base_url": None,
        }

        adapter = RunnerProviderAdapter(mock_config)
        llm_config = adapter.get_llm_config()

        assert llm_config.provider == "anthropic"
        assert llm_config.model == "claude-3-haiku"
        assert llm_config.api_key == "sk-override"

    def test_injection_chain_close_cleanup(self) -> None:
        """验证关闭链路正确清理资源"""
        mock_config = self._make_mock_config()
        adapter = RunnerProviderAdapter(mock_config)

        adapter.close()
        assert adapter._provider_instance is None

    def test_injection_chain_custom_provider(self) -> None:
        """验证自定义Provider配置注入链路"""
        mock_config = self._make_mock_config(
            provider="deepseek",
            model="deepseek-chat",
            api_key="ds-test-key",
            base_url="https://api.deepseek.com",
        )

        adapter = RunnerProviderAdapter(mock_config)
        llm_config = adapter.get_llm_config()

        assert llm_config.provider == "deepseek"
        assert llm_config.model == "deepseek-chat"
        assert llm_config.base_url == "https://api.deepseek.com"

    def test_injection_chain_no_api_key(self) -> None:
        """验证无API Key时的配置注入链路"""
        mock_config = self._make_mock_config(
            provider="ollama",
            model="llama3",
            api_key=None,
            base_url="http://localhost:11434",
        )

        adapter = RunnerProviderAdapter(mock_config)
        llm_config = adapter.get_llm_config()

        assert llm_config.provider == "ollama"
        assert llm_config.api_key is None
        assert llm_config.base_url == "http://localhost:11434"

    @patch.object(RunnerProviderAdapter, "_try_load_nanobot_config", return_value=False)
    def test_injection_chain_no_runner_no_nanobot(
        self, mock_nanobot: MagicMock
    ) -> None:
        """验证项目配置和nanobot配置都缺失时的错误"""
        mock_config = MagicMock()
        mock_config.has_llm_config.return_value = False
        mock_config.get_llm_config.return_value = {
            "provider": "",
            "model": "",
        }

        adapter = RunnerProviderAdapter(mock_config)

        from src.core.base.exceptions import LLMError

        with pytest.raises(LLMError):
            adapter.get_llm_config()
