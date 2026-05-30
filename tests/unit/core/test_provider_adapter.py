import os
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.base.exceptions import LLMError, NanobotRunnerError
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
    # 默认返回空的 WebSocket 配置，表示未启用
    config.get_websocket_config.return_value = {}
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
        config.has_llm_config.side_effect = NanobotRunnerError("error")
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


# ============================================================
# WebSocket 配置构建单元测试
# ============================================================


class TestBuildWebsocketChannelConfig:
    """测试 _build_websocket_channel_config 方法的 WebSocket 通道配置构建逻辑"""

    def test_webui_enabled_with_empty_config(self, mock_runner_config):
        """webui_enabled=True 且 ws_config 为空时，应构建 WebSocket 通道配置"""
        adapter = RunnerProviderAdapter(mock_runner_config, webui_enabled=True)
        channels: dict[str, Any] = {}
        ws_config: dict[str, Any] = {}

        adapter._build_websocket_channel_config(channels, ws_config)

        assert "websocket" in channels
        ws = channels["websocket"]
        assert ws["enabled"] is True
        # 验证默认值
        assert ws["host"] == "127.0.0.1"
        assert ws["port"] == 8765
        assert ws["path"] == "/"
        assert ws["streaming"] is True

    def test_webui_disabled_config_not_enabled(self, mock_runner_config):
        """webui_enabled=False 且 config 中 enabled=False 时，不应构建 WebSocket 配置"""
        adapter = RunnerProviderAdapter(mock_runner_config, webui_enabled=False)
        channels: dict[str, Any] = {}
        ws_config = {"enabled": False}

        adapter._build_websocket_channel_config(channels, ws_config)

        assert "websocket" not in channels

    def test_webui_disabled_but_config_enabled(self, mock_runner_config):
        """webui_enabled=False 但 config 中 enabled=True 时，应构建 WebSocket 配置"""
        adapter = RunnerProviderAdapter(mock_runner_config, webui_enabled=False)
        channels: dict[str, Any] = {}
        ws_config = {"enabled": True}

        adapter._build_websocket_channel_config(channels, ws_config)

        assert "websocket" in channels
        assert channels["websocket"]["enabled"] is True

    def test_webui_enabled_and_config_enabled(self, mock_runner_config):
        """webui_enabled=True 且 config 中 enabled=True 时，应构建 WebSocket 配置"""
        adapter = RunnerProviderAdapter(mock_runner_config, webui_enabled=True)
        channels: dict[str, Any] = {}
        ws_config = {"enabled": True}

        adapter._build_websocket_channel_config(channels, ws_config)

        assert "websocket" in channels
        assert channels["websocket"]["enabled"] is True

    def test_custom_ws_config_values(self, mock_runner_config):
        """自定义 WebSocket 配置值应正确写入通道配置"""
        adapter = RunnerProviderAdapter(mock_runner_config, webui_enabled=True)
        channels: dict[str, Any] = {}
        ws_config = {
            "host": "0.0.0.0",
            "port": 9999,
            "path": "/ws",
            "streaming": False,
            "max_message_bytes": 1048576,
            "ping_interval_s": 30.0,
            "ping_timeout_s": 10.0,
        }

        adapter._build_websocket_channel_config(channels, ws_config)

        ws = channels["websocket"]
        assert ws["host"] == "0.0.0.0"
        assert ws["port"] == 9999
        assert ws["path"] == "/ws"
        assert ws["streaming"] is False
        assert ws["max_message_bytes"] == 1048576
        assert ws["ping_interval_s"] == 30.0
        assert ws["ping_timeout_s"] == 10.0

    def test_security_config_defaults(self, mock_runner_config):
        """安全配置默认值：token 为空，websocket_requires_token 为 True"""
        adapter = RunnerProviderAdapter(mock_runner_config, webui_enabled=True)
        channels: dict[str, Any] = {}
        ws_config: dict[str, Any] = {}

        adapter._build_websocket_channel_config(channels, ws_config)

        ws = channels["websocket"]
        assert ws["token"] == ""
        assert ws["websocket_requires_token"] is True
        assert ws["token_issue_path"] == ""
        assert ws["token_issue_secret"] == ""
        assert ws["token_ttl_s"] == 300

    def test_security_config_custom_token(self, mock_runner_config):
        """自定义安全配置：token 和 websocket_requires_token 正确传递"""
        adapter = RunnerProviderAdapter(mock_runner_config, webui_enabled=True)
        channels: dict[str, Any] = {}
        ws_config = {
            "token": "my-secret-token",
            "websocket_requires_token": False,
            "token_issue_path": "/api/token",
            "token_issue_secret": "issue-secret",
            "token_ttl_s": 600,
        }

        adapter._build_websocket_channel_config(channels, ws_config)

        ws = channels["websocket"]
        assert ws["token"] == "my-secret-token"
        assert ws["websocket_requires_token"] is False
        assert ws["token_issue_path"] == "/api/token"
        assert ws["token_issue_secret"] == "issue-secret"
        assert ws["token_ttl_s"] == 600

    def test_ssl_config_defaults(self, mock_runner_config):
        """SSL 配置默认值为空字符串"""
        adapter = RunnerProviderAdapter(mock_runner_config, webui_enabled=True)
        channels: dict[str, Any] = {}
        ws_config: dict[str, Any] = {}

        adapter._build_websocket_channel_config(channels, ws_config)

        ws = channels["websocket"]
        assert ws["ssl_certfile"] == ""
        assert ws["ssl_keyfile"] == ""

    def test_allow_from_default(self, mock_runner_config):
        """allow_from 默认值为 ['*']"""
        adapter = RunnerProviderAdapter(mock_runner_config, webui_enabled=True)
        channels: dict[str, Any] = {}
        ws_config: dict[str, Any] = {}

        adapter._build_websocket_channel_config(channels, ws_config)

        ws = channels["websocket"]
        assert ws["allow_from"] == ["*"]

    def test_does_not_affect_existing_channels(self, mock_runner_config):
        """构建 WebSocket 配置不应影响已有的其他通道配置"""
        adapter = RunnerProviderAdapter(mock_runner_config, webui_enabled=True)
        channels: dict[str, Any] = {
            "feishu": {
                "enabled": True,
                "app_id": "test-app-id",
                "app_secret": "test-secret",
            }
        }
        ws_config: dict[str, Any] = {}

        adapter._build_websocket_channel_config(channels, ws_config)

        # 飞书通道应保持不变
        assert "feishu" in channels
        assert channels["feishu"]["app_id"] == "test-app-id"
        assert channels["feishu"]["app_secret"] == "test-secret"
        # WebSocket 通道应被添加
        assert "websocket" in channels


@pytest.fixture
def mock_nanobot_modules():
    """模拟 nanobot-ai 的配置模块，使 _build_nanobot_config_from_runner 可运行"""
    mock_config_cls = MagicMock()
    mock_agents_config_cls = MagicMock()
    mock_providers_config_cls = MagicMock()

    # 让 Config() 返回一个可设置属性的对象
    mock_config_instance = MagicMock()
    mock_config_cls.return_value = mock_config_instance
    # 让 AgentsConfig() 返回一个可设置属性的对象
    mock_agents_instance = MagicMock()
    mock_agents_config_cls.return_value = mock_agents_instance
    # 让 ProvidersConfig() 返回一个可设置属性的对象
    mock_providers_instance = MagicMock()
    mock_providers_config_cls.return_value = mock_providers_instance

    mock_modules = {
        "nanobot": MagicMock(),
        "nanobot.config": MagicMock(),
        "nanobot.config.loader": MagicMock(Config=mock_config_cls),
        "nanobot.config.schema": MagicMock(
            AgentsConfig=mock_agents_config_cls,
            ProvidersConfig=mock_providers_config_cls,
        ),
        "nanobot.channels": MagicMock(),
        "nanobot.channels.websocket": MagicMock(
            WebSocketChannel=MagicMock(),
            _parse_request_path=MagicMock(return_value=("/", {})),
            _http_error=MagicMock(return_value=MagicMock(status=403)),
        ),
    }

    with patch.dict("sys.modules", mock_modules):
        yield {
            "Config": mock_config_cls,
            "AgentsConfig": mock_agents_config_cls,
            "ProvidersConfig": mock_providers_config_cls,
            "config_instance": mock_config_instance,
            "agents_instance": mock_agents_instance,
            "providers_instance": mock_providers_instance,
        }


class TestBuildNanobotConfigWebsocket:
    """测试 _build_nanobot_config_from_runner 中 WebSocket 相关的配置构建逻辑

    需要模拟 nanobot-ai 的导入，因为该方法内部依赖 nanobot.config.loader 和
    nanobot.config.schema 模块。
    """

    def test_brand_fields_default_values(
        self, mock_runner_config, mock_nanobot_modules
    ):
        """品牌字段（bot_name/bot_icon/unified_session）在 ws_config 为空时使用默认值"""
        adapter = RunnerProviderAdapter(mock_runner_config, webui_enabled=False)
        # ws_config 为空，使用默认值
        mock_runner_config.get_websocket_config.return_value = {}

        adapter._build_nanobot_config_from_runner()

        # 验证 AgentsConfig 被调用时 defaults 包含品牌字段
        agents_config_cls = mock_nanobot_modules["AgentsConfig"]
        agents_config_cls.assert_called_once()
        call_kwargs = agents_config_cls.call_args[1]
        defaults = call_kwargs["defaults"]
        assert defaults["bot_name"] == "Nanobot-Runner"
        assert defaults["bot_icon"] == "🏃‍♂️"
        assert defaults["unified_session"] is False

    def test_brand_fields_custom_values(self, mock_runner_config, mock_nanobot_modules):
        """品牌字段从 ws_config 中读取自定义值"""
        adapter = RunnerProviderAdapter(mock_runner_config, webui_enabled=False)
        mock_runner_config.get_websocket_config.return_value = {
            "bot_name": "MyBot",
            "bot_icon": "🤖",
            "unified_session": True,
        }

        adapter._build_nanobot_config_from_runner()

        agents_config_cls = mock_nanobot_modules["AgentsConfig"]
        agents_config_cls.assert_called_once()
        call_kwargs = agents_config_cls.call_args[1]
        defaults = call_kwargs["defaults"]
        assert defaults["bot_name"] == "MyBot"
        assert defaults["bot_icon"] == "🤖"
        assert defaults["unified_session"] is True

    def test_websocket_channel_built_when_webui_enabled(
        self, mock_runner_config, mock_nanobot_modules
    ):
        """webui_enabled=True 时，Config 的 channels 参数应包含 websocket 键"""
        adapter = RunnerProviderAdapter(mock_runner_config, webui_enabled=True)
        mock_runner_config.get_websocket_config.return_value = {}

        adapter._build_nanobot_config_from_runner()

        config_cls = mock_nanobot_modules["Config"]
        config_cls.assert_called_once()
        call_kwargs = config_cls.call_args[1]
        channels = call_kwargs["channels"]
        assert "websocket" in channels
        assert channels["websocket"]["enabled"] is True

    def test_no_websocket_channel_when_disabled(
        self, mock_runner_config, mock_nanobot_modules
    ):
        """webui_enabled=False 且 config 未启用时，Config 的 channels 不包含 websocket"""
        adapter = RunnerProviderAdapter(mock_runner_config, webui_enabled=False)
        mock_runner_config.get_websocket_config.return_value = {"enabled": False}

        adapter._build_nanobot_config_from_runner()

        config_cls = mock_nanobot_modules["Config"]
        config_cls.assert_called_once()
        call_kwargs = config_cls.call_args[1]
        channels = call_kwargs["channels"]
        assert "websocket" not in channels

    def test_websocket_channel_when_config_enabled(
        self, mock_runner_config, mock_nanobot_modules
    ):
        """webui_enabled=False 但 config 中 enabled=True 时，应构建 WebSocket 通道"""
        adapter = RunnerProviderAdapter(mock_runner_config, webui_enabled=False)
        mock_runner_config.get_websocket_config.return_value = {
            "enabled": True,
            "host": "0.0.0.0",
            "port": 9090,
        }

        adapter._build_nanobot_config_from_runner()

        config_cls = mock_nanobot_modules["Config"]
        call_kwargs = config_cls.call_args[1]
        channels = call_kwargs["channels"]
        assert "websocket" in channels
        assert channels["websocket"]["host"] == "0.0.0.0"
        assert channels["websocket"]["port"] == 9090

    def test_security_config_passed_to_websocket_channel(
        self, mock_runner_config, mock_nanobot_modules
    ):
        """安全配置（token/requires_token）正确传递到 WebSocket 通道"""
        adapter = RunnerProviderAdapter(mock_runner_config, webui_enabled=True)
        mock_runner_config.get_websocket_config.return_value = {
            "token": "secure-token-123",
            "websocket_requires_token": False,
        }

        adapter._build_nanobot_config_from_runner()

        config_cls = mock_nanobot_modules["Config"]
        call_kwargs = config_cls.call_args[1]
        channels = call_kwargs["channels"]
        ws = channels["websocket"]
        assert ws["token"] == "secure-token-123"
        assert ws["websocket_requires_token"] is False

    def test_feishu_channel_not_affected_by_websocket(
        self, mock_runner_config, mock_nanobot_modules
    ):
        """WebSocket 配置不影响飞书通道的构建"""
        adapter = RunnerProviderAdapter(mock_runner_config, webui_enabled=True)
        mock_runner_config.get_websocket_config.return_value = {}

        # 模拟飞书环境变量，使飞书通道被构建
        with patch.dict(
            os.environ,
            {
                "NANOBOT_FEISHU_APP_ID": "feishu-app-id",
                "NANOBOT_FEISHU_APP_SECRET": "feishu-app-secret",
            },
        ):
            adapter._build_nanobot_config_from_runner()

        config_cls = mock_nanobot_modules["Config"]
        call_kwargs = config_cls.call_args[1]
        channels = call_kwargs["channels"]

        # 两个通道都应存在且互不影响
        assert "feishu" in channels
        assert "websocket" in channels
        assert channels["feishu"]["app_id"] == "feishu-app-id"
        assert channels["feishu"]["app_secret"] == "feishu-app-secret"
        assert channels["websocket"]["enabled"] is True

    def test_model_field_in_agents_defaults(
        self, mock_runner_config, mock_nanobot_modules
    ):
        """agents.defaults 中 model 字段仍正确设置"""
        adapter = RunnerProviderAdapter(mock_runner_config, webui_enabled=False)
        mock_runner_config.get_websocket_config.return_value = {}

        adapter._build_nanobot_config_from_runner()

        agents_config_cls = mock_nanobot_modules["AgentsConfig"]
        call_kwargs = agents_config_cls.call_args[1]
        defaults = call_kwargs["defaults"]
        assert defaults["model"] == "gpt-4o-mini"

    def test_nanobot_config_cached_after_build(
        self, mock_runner_config, mock_nanobot_modules
    ):
        """构建后的 nanobot 配置应被缓存到 _nanobot_config"""
        adapter = RunnerProviderAdapter(mock_runner_config, webui_enabled=True)
        mock_runner_config.get_websocket_config.return_value = {}

        result = adapter._build_nanobot_config_from_runner()

        assert adapter._nanobot_config is not None
        assert adapter._nanobot_config is result


# ============================================================
# WebUI Settings API 拦截单元测试
# ============================================================


class TestPatchWebsocketSettingsApi:
    """测试 _patch_websocket_settings_api 的 monkey-patch 行为

    验证 WebUI Settings 写操作端点被拦截返回 403，
    而读端点和其他端点不受影响。
    """

    @pytest.fixture
    def mock_ws_channel_cls(self):
        """模拟 nanobot.channels.websocket.WebSocketChannel 类"""
        mock_cls = MagicMock()
        # 保存原始 _dispatch_http 方法（不含 _runner_patched 属性）
        original_dispatch = MagicMock(spec=[])
        mock_cls._dispatch_http = original_dispatch
        return mock_cls, original_dispatch

    def test_settings_update_blocked(self, mock_ws_channel_cls):
        """调用 patch 后，/api/settings/update 应返回 403 而非调用原始方法"""
        from src.core.provider_adapter import _patch_websocket_settings_api

        mock_cls, original_dispatch = mock_ws_channel_cls

        with patch.dict(
            "sys.modules",
            {"nanobot.channels.websocket": MagicMock(WebSocketChannel=mock_cls)},
        ):
            _patch_websocket_settings_api()

        # 验证 _dispatch_http 已被替换
        assert mock_cls._dispatch_http is not original_dispatch

    def test_blocked_paths_return_403(self, mock_runner_config):
        """3 个写端点路径在 _BLOCKED_SETTINGS_PATHS 中"""
        from src.core.provider_adapter import _BLOCKED_SETTINGS_PATHS

        assert "/api/settings/update" in _BLOCKED_SETTINGS_PATHS
        assert "/api/settings/provider/update" in _BLOCKED_SETTINGS_PATHS
        assert "/api/settings/web-search/update" in _BLOCKED_SETTINGS_PATHS

    def test_read_paths_not_blocked(self):
        """读端点路径不在 _BLOCKED_SETTINGS_PATHS 中"""
        from src.core.provider_adapter import _BLOCKED_SETTINGS_PATHS

        assert "/api/settings" not in _BLOCKED_SETTINGS_PATHS
        assert "/api/sessions" not in _BLOCKED_SETTINGS_PATHS
        assert "/webui/bootstrap" not in _BLOCKED_SETTINGS_PATHS
        assert "/api/commands" not in _BLOCKED_SETTINGS_PATHS

    @pytest.mark.asyncio
    async def test_dispatch_http_blocks_write_endpoints(self):
        """monkey-patch 后的 _dispatch_http 应拦截写端点并返回 403"""
        from src.core.provider_adapter import (
            _patch_websocket_settings_api,
        )

        # 构造模拟的 WebSocketChannel 类
        original_dispatch = AsyncMock(return_value=MagicMock(status=200), spec=[])
        mock_cls = MagicMock()
        mock_cls._dispatch_http = original_dispatch

        mock_ws_module = MagicMock(WebSocketChannel=mock_cls)

        # 模拟 _parse_request_path 和 _http_error
        mock_parse = MagicMock(return_value=("/api/settings/update", {}))
        mock_error = MagicMock(return_value=MagicMock(status=403))

        mock_ws_module._parse_request_path = mock_parse
        mock_ws_module._http_error = mock_error

        with patch.dict("sys.modules", {"nanobot.channels.websocket": mock_ws_module}):
            _patch_websocket_settings_api()

        # 获取 patch 后的方法
        patched_dispatch = mock_cls._dispatch_http

        # 模拟调用
        mock_self = MagicMock()
        mock_connection = MagicMock()
        mock_request = MagicMock()
        mock_request.path = "/api/settings/update"

        result = await patched_dispatch(mock_self, mock_connection, mock_request)

        # 验证 _http_error 被调用，状态码 403
        mock_error.assert_called_once()
        call_args = mock_error.call_args
        assert call_args[0][0] == 403

    @pytest.mark.asyncio
    async def test_dispatch_http_passes_read_endpoints(self):
        """monkey-patch 后的 _dispatch_http 应放行读端点，调用原始方法"""
        from src.core.provider_adapter import _patch_websocket_settings_api

        original_dispatch = AsyncMock(return_value=MagicMock(status=200), spec=[])
        mock_cls = MagicMock()
        mock_cls._dispatch_http = original_dispatch

        mock_ws_module = MagicMock(WebSocketChannel=mock_cls)
        mock_parse = MagicMock(return_value=("/api/settings", {}))
        mock_error = MagicMock(return_value=MagicMock(status=403))

        mock_ws_module._parse_request_path = mock_parse
        mock_ws_module._http_error = mock_error

        with patch.dict("sys.modules", {"nanobot.channels.websocket": mock_ws_module}):
            _patch_websocket_settings_api()

        patched_dispatch = mock_cls._dispatch_http

        mock_self = MagicMock()
        mock_connection = MagicMock()
        mock_request = MagicMock()
        mock_request.path = "/api/settings"

        result = await patched_dispatch(mock_self, mock_connection, mock_request)

        # 验证原始方法被调用，_http_error 未被调用
        original_dispatch.assert_called_once()
        mock_error.assert_not_called()

    def test_patch_called_during_config_build_when_webui_enabled(
        self, mock_runner_config, mock_nanobot_modules
    ):
        """webui_enabled=True 时，_build_nanobot_config_from_runner 应调用 _patch_websocket_settings_api"""
        with patch(
            "src.core.provider_adapter._patch_websocket_settings_api"
        ) as mock_patch:
            adapter = RunnerProviderAdapter(mock_runner_config, webui_enabled=True)
            mock_runner_config.get_websocket_config.return_value = {}

            adapter._build_nanobot_config_from_runner()

            mock_patch.assert_called_once()

    def test_patch_not_called_when_webui_disabled(
        self, mock_runner_config, mock_nanobot_modules
    ):
        """webui_enabled=False 且 config 未启用时，不应调用 _patch_websocket_settings_api"""
        with patch(
            "src.core.provider_adapter._patch_websocket_settings_api"
        ) as mock_patch:
            adapter = RunnerProviderAdapter(mock_runner_config, webui_enabled=False)
            mock_runner_config.get_websocket_config.return_value = {"enabled": False}

            adapter._build_nanobot_config_from_runner()

            mock_patch.assert_not_called()


class TestRunnerProviderAdapterFallback:
    """FallbackProvider 集成测试"""

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
        config.get_fallback_api_key.return_value = "nvapi-test"
        return config

    def test_no_fallback_returns_plain_provider(self, mock_runner_config):
        mock_runner_config.get_fallback_models.return_value = []
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

    def test_build_nanobot_config_includes_fallback(self):
        """_build_nanobot_config_from_runner 应注入 fallback_models 到 nanobot Config"""
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
            with patch.dict(
                os.environ, {"NANOBOT_LLM_API_KEY_NVIDIA": "nvapi-test"}, clear=False
            ):
                nb_config = adapter._get_or_create_nanobot_config()
                defaults = nb_config.agents.defaults
                assert hasattr(defaults, "fallback_models")
                assert len(defaults.fallback_models) == 1
