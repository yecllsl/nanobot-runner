from unittest.mock import MagicMock, patch

import pytest

from src.core.exceptions import LLMError
from src.core.llm_config import LLMConfig
from src.core.provider_adapter import AgentDefaults, RunnerProviderAdapter


class TestLLMConfig:
    """LLMConfig数据类测试"""

    def test_default_values(self) -> None:
        config = LLMConfig(provider="openai", model="gpt-4o-mini")
        assert config.provider == "openai"
        assert config.model == "gpt-4o-mini"
        assert config.api_key is None
        assert config.base_url is None
        assert config.max_iterations == 10
        assert config.context_window_tokens == 128000
        assert config.context_block_limit == 10
        assert config.max_tool_result_chars == 32000

    def test_custom_values(self) -> None:
        config = LLMConfig(
            provider="anthropic",
            model="claude-3-5-sonnet",
            api_key="sk-test",
            base_url="https://api.anthropic.com",
            max_iterations=20,
        )
        assert config.provider == "anthropic"
        assert config.api_key == "sk-test"
        assert config.max_iterations == 20

    def test_is_complete(self) -> None:
        assert LLMConfig(provider="openai", model="gpt-4o-mini").is_complete()
        assert not LLMConfig(provider="", model="gpt-4o-mini").is_complete()
        assert not LLMConfig(provider="openai", model="").is_complete()

    def test_has_api_key(self) -> None:
        assert LLMConfig(
            provider="openai", model="gpt-4o-mini", api_key="sk-test"
        ).has_api_key()
        assert not LLMConfig(provider="openai", model="gpt-4o-mini").has_api_key()
        assert not LLMConfig(
            provider="openai", model="gpt-4o-mini", api_key=""
        ).has_api_key()

    def test_to_dict_masks_api_key(self) -> None:
        config = LLMConfig(provider="openai", model="gpt-4o-mini", api_key="sk-secret")
        d = config.to_dict()
        assert d["api_key"] == "***"
        assert d["provider"] == "openai"

    def test_to_dict_no_api_key(self) -> None:
        config = LLMConfig(provider="openai", model="gpt-4o-mini")
        d = config.to_dict()
        assert d["api_key"] is None

    def test_frozen(self) -> None:
        config = LLMConfig(provider="openai", model="gpt-4o-mini")
        with pytest.raises(AttributeError):
            config.provider = "anthropic"  # type: ignore[misc]


class TestAgentDefaults:
    """AgentDefaults数据类测试"""

    def test_default_values(self) -> None:
        defaults = AgentDefaults(model="gpt-4o-mini")
        assert defaults.model == "gpt-4o-mini"
        assert defaults.max_tool_iterations == 10
        assert defaults.context_window_tokens == 128000

    def test_custom_values(self) -> None:
        defaults = AgentDefaults(
            model="claude-3",
            max_tool_iterations=20,
            context_window_tokens=64000,
        )
        assert defaults.model == "claude-3"
        assert defaults.max_tool_iterations == 20
        assert defaults.context_window_tokens == 64000


class TestRunnerProviderAdapter:
    """RunnerProviderAdapter测试"""

    def _make_mock_config(self, llm_config: dict | None = None) -> MagicMock:
        mock = MagicMock()
        if llm_config is not None:
            mock.has_llm_config.return_value = bool(
                llm_config.get("provider") and llm_config.get("model")
            )
            mock.get_llm_config.return_value = llm_config
        else:
            mock.has_llm_config.return_value = False
            mock.get_llm_config.return_value = {
                "provider": "",
                "model": "",
                "api_key": None,
                "base_url": None,
            }
        return mock

    def test_get_llm_config_from_runner(self) -> None:
        mock_config = self._make_mock_config(
            {
                "provider": "openai",
                "model": "gpt-4o-mini",
                "api_key": "sk-test",
                "base_url": None,
            }
        )

        adapter = RunnerProviderAdapter(mock_config)
        llm = adapter.get_llm_config()

        assert llm.provider == "openai"
        assert llm.model == "gpt-4o-mini"
        assert llm.api_key == "sk-test"

    def test_get_llm_config_no_config_raises(self) -> None:
        mock_config = self._make_mock_config()

        with patch.object(
            RunnerProviderAdapter, "_try_load_nanobot_config", return_value=False
        ):
            adapter = RunnerProviderAdapter(mock_config)
            with pytest.raises(LLMError, match="未配置LLM"):
                adapter.get_llm_config()

    def test_is_available_with_runner_config(self) -> None:
        mock_config = self._make_mock_config(
            {
                "provider": "openai",
                "model": "gpt-4o-mini",
            }
        )

        adapter = RunnerProviderAdapter(mock_config)
        assert adapter.is_available()

    def test_is_available_no_config(self) -> None:
        mock_config = self._make_mock_config()

        with patch.object(
            RunnerProviderAdapter, "_try_load_nanobot_config", return_value=False
        ):
            adapter = RunnerProviderAdapter(mock_config)
            assert not adapter.is_available()

    def test_get_agent_defaults(self) -> None:
        mock_config = self._make_mock_config(
            {
                "provider": "openai",
                "model": "gpt-4o-mini",
                "api_key": "sk-test",
                "base_url": None,
            }
        )

        adapter = RunnerProviderAdapter(mock_config)
        defaults = adapter.get_agent_defaults()

        assert isinstance(defaults, AgentDefaults)
        assert defaults.model == "gpt-4o-mini"
        assert defaults.max_tool_iterations == 10

    @patch("src.core.provider_adapter.RunnerProviderAdapter._try_load_nanobot_config")
    def test_fallback_to_nanobot_config(self, mock_try_load: MagicMock) -> None:
        mock_config = self._make_mock_config()
        mock_try_load.return_value = True

        mock_nanobot = MagicMock()
        mock_nanobot.agents.defaults.model = "deepseek-chat"
        mock_nanobot.agents.defaults.max_tool_iterations = 15
        mock_nanobot.agents.defaults.context_window_tokens = 64000
        mock_nanobot.agents.defaults.context_block_limit = 8
        mock_nanobot.agents.defaults.max_tool_result_chars = 16000
        mock_nanobot.providers.default = "deepseek"

        adapter = RunnerProviderAdapter(mock_config)
        adapter._nanobot_config = mock_nanobot

        llm = adapter.get_llm_config()
        assert llm.provider == "deepseek"
        assert llm.model == "deepseek-chat"
        assert llm.max_iterations == 15

    def test_close_clears_provider(self) -> None:
        mock_config = self._make_mock_config(
            {
                "provider": "openai",
                "model": "gpt-4o-mini",
            }
        )

        adapter = RunnerProviderAdapter(mock_config)
        adapter._provider_instance = MagicMock()
        adapter.close()
        assert adapter._provider_instance is None

    @patch("src.core.provider_adapter.RunnerProviderAdapter._try_load_nanobot_config")
    def test_get_provider_instance_import_error(self, mock_try_load: MagicMock) -> None:
        mock_config = self._make_mock_config(
            {
                "provider": "openai",
                "model": "gpt-4o-mini",
            }
        )

        adapter = RunnerProviderAdapter(mock_config)

        with patch.dict(
            "sys.modules", {"nanobot.providers.openai_compat_provider": None}
        ):
            with pytest.raises(LLMError, match="无法导入nanobot模块"):
                adapter.get_provider_instance()

    def test_has_runner_llm_config_exception_returns_false(self) -> None:
        mock_config = MagicMock()
        mock_config.has_llm_config.side_effect = Exception("config error")

        adapter = RunnerProviderAdapter(mock_config)
        assert not adapter._has_runner_llm_config()

    @patch("src.core.provider_adapter.RunnerProviderAdapter._try_load_nanobot_config")
    def test_from_runner_config_with_env_override(
        self, mock_try_load: MagicMock
    ) -> None:
        mock_config = self._make_mock_config(
            {
                "provider": "openai",
                "model": "gpt-4o-mini",
                "api_key": "sk-env-key",
                "base_url": "https://custom.api.com",
            }
        )

        adapter = RunnerProviderAdapter(mock_config)
        llm = adapter._from_runner_config()

        assert llm.provider == "openai"
        assert llm.model == "gpt-4o-mini"
        assert llm.api_key == "sk-env-key"
        assert llm.base_url == "https://custom.api.com"
