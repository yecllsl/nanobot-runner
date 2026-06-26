import os
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

    def _mock_get(key: str, default: Any = None) -> Any:
        if key == "timezone":
            return "Asia/Shanghai"
        return default

    config.get.side_effect = _mock_get
    # 默认返回空的 WebSocket 配置，表示未启用
    config.get_websocket_config.return_value = {}
    # 添加 base_dir 属性，避免 _build_nanobot_config_from_runner 失败
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
        config.get_llm_config.return_value = {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "api_key": "test-key",
            "max_iterations": 10,
            "context_window_tokens": 128000,
            "context_block_limit": 10,
            "max_tool_result_chars": 32000,
        }
        config.get.return_value = None
        config.get_websocket_config.return_value = {}
        config.base_dir = Path("/test/runner")

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


class TestRunnerProviderAdapterFromRunnerConfig:
    def test_from_runner_config(self, mock_runner_config):
        adapter = RunnerProviderAdapter(mock_runner_config)
        llm_config = adapter._from_runner_config()
        assert llm_config.provider == "openai"
        assert llm_config.model == "gpt-4o-mini"
        assert llm_config.api_key == "test-key"
        assert llm_config.base_url == "https://api.openai.com"


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
        ),
        # v0.30.0: nanobot-ai 0.2.1 将 http_error/parse_request_path 迁移至此
        "nanobot.webui": MagicMock(),
        "nanobot.webui.http_utils": MagicMock(
            http_error=MagicMock(return_value=MagicMock(status=403)),
            parse_request_path=MagicMock(return_value=("/", {})),
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

    def test_timezone_from_runner_config_passed_to_agents_defaults(
        self, mock_runner_config, mock_nanobot_modules
    ):
        """回归测试: 项目配置的 timezone 应注入到 nanobot AgentsConfig.defaults

        根因: config.json 配置了 "timezone": "Asia/Shanghai"，但
        _build_nanobot_config_from_runner 未将其传给 AgentsConfig，
        导致 WebUI 和 AgentLoop 默认使用 UTC。
        """
        adapter = RunnerProviderAdapter(mock_runner_config, webui_enabled=False)
        mock_runner_config.get_websocket_config.return_value = {}

        adapter._build_nanobot_config_from_runner()

        agents_config_cls = mock_nanobot_modules["AgentsConfig"]
        agents_config_cls.assert_called_once()
        call_kwargs = agents_config_cls.call_args[1]
        defaults = call_kwargs["defaults"]
        assert defaults["timezone"] == "Asia/Shanghai"

    def test_timezone_defaults_to_utc_when_not_configured(
        self, mock_runner_config, mock_nanobot_modules
    ):
        """未配置 timezone 时，应使用 nanobot 默认 UTC（向后兼容）"""
        mock_runner_config.get.side_effect = lambda key, default=None: default

        adapter = RunnerProviderAdapter(mock_runner_config, webui_enabled=False)
        mock_runner_config.get_websocket_config.return_value = {}

        adapter._build_nanobot_config_from_runner()

        agents_config_cls = mock_nanobot_modules["AgentsConfig"]
        call_kwargs = agents_config_cls.call_args[1]
        defaults = call_kwargs["defaults"]
        assert defaults.get("timezone") is None

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
# WebUI Settings API 代理单元测试
# ============================================================


class TestPatchWebsocketSettingsApi:
    """测试 _patch_websocket_settings_api 的 monkey-patch 行为

    验证 patch 后 nanobot.config.loader 的 load_config/save_config 源函数被替换，
    且所有已导入该函数的 webui 模块（settings_api/mcp_presets_api/cli_apps_api）
    的本地引用也被替换，读写实际指向项目配置。
    """

    @pytest.fixture
    def mock_loader_modules(self):
        """模拟 nanobot.config.loader 及 webui 子模块

        各 webui 模块的 load_config/save_config 初始指向 loader 的同名函数，
        模拟模块级 from nanobot.config.loader import load_config 的绑定行为。
        """
        mock_loader = MagicMock()
        mock_loader.load_config = MagicMock(return_value=MagicMock())
        mock_loader.save_config = MagicMock()

        mock_settings_api = MagicMock()
        mock_settings_api.load_config = mock_loader.load_config
        mock_settings_api.save_config = mock_loader.save_config

        mock_mcp_presets_api = MagicMock()
        mock_mcp_presets_api.load_config = mock_loader.load_config

        mock_cli_apps_api = MagicMock()
        mock_cli_apps_api.load_config = mock_loader.load_config

        # nanobot.config.schema.Config 返回可设置属性的 MagicMock
        mock_schema = MagicMock()
        mock_schema.Config = MagicMock(return_value=MagicMock())

        return {
            "loader": mock_loader,
            "settings_api": mock_settings_api,
            "mcp_presets_api": mock_mcp_presets_api,
            "cli_apps_api": mock_cli_apps_api,
            "schema": mock_schema,
        }

    @staticmethod
    def _make_sys_modules(modules: dict[str, Any]) -> dict[str, Any]:
        """构建 sys.modules mock，包含 nanobot.config.loader 及 webui 子模块"""
        mock_nanobot = MagicMock()
        mock_config_pkg = MagicMock()
        mock_config_pkg.loader = modules["loader"]
        mock_webui = MagicMock()
        mock_webui.settings_api = modules["settings_api"]
        mock_webui.mcp_presets_api = modules["mcp_presets_api"]
        mock_webui.cli_apps_api = modules["cli_apps_api"]
        mock_nanobot.config = mock_config_pkg
        mock_nanobot.webui = mock_webui
        return {
            "nanobot": mock_nanobot,
            "nanobot.config": mock_config_pkg,
            "nanobot.config.loader": modules["loader"],
            "nanobot.config.schema": modules["schema"],
            "nanobot.webui": mock_webui,
            "nanobot.webui.settings_api": modules["settings_api"],
            "nanobot.webui.mcp_presets_api": modules["mcp_presets_api"],
            "nanobot.webui.cli_apps_api": modules["cli_apps_api"],
        }

    def test_patch_replaces_load_and_save(self, mock_loader_modules):
        """调用 patch 后，源函数和所有 webui 模块本地引用应被替换"""
        from src.core.provider_adapter import _patch_websocket_settings_api

        # 保存原始引用，用于后续验证被替换
        original_loader_save = mock_loader_modules["loader"].save_config
        original_settings_save = mock_loader_modules["settings_api"].save_config

        sys_modules = self._make_sys_modules(mock_loader_modules)
        with patch.dict("sys.modules", sys_modules):
            _patch_websocket_settings_api()

        # 验证源函数被替换
        assert (
            getattr(mock_loader_modules["loader"].load_config, "_runner_patched", False)
            is True
        )
        # 验证所有 webui 模块本地引用被替换
        for name in ("settings_api", "mcp_presets_api", "cli_apps_api"):
            mod = mock_loader_modules[name]
            assert getattr(mod.load_config, "_runner_patched", False) is True, (
                f"{name} load_config 未被 patch"
            )
        # save_config 也应被替换（不再是原始 mock）
        assert mock_loader_modules["loader"].save_config is not original_loader_save
        assert (
            mock_loader_modules["settings_api"].save_config
            is not original_settings_save
        )

    def test_load_config_does_not_call_original(self, mock_loader_modules):
        """_runner_load_config 不应调用原始 load_config（避免读取项目配置文件触发 Pydantic 验证错误）"""
        from src.core.provider_adapter import _patch_websocket_settings_api

        # 保存原始 load_config 引用
        original_load = mock_loader_modules["loader"].load_config

        sys_modules = self._make_sys_modules(mock_loader_modules)
        with patch.dict("sys.modules", sys_modules):
            _patch_websocket_settings_api()

            with patch("src.core.provider_adapter.ConfigManager") as mock_cm_cls:
                mock_cm = MagicMock()
                mock_cm.get_llm_config.return_value = {
                    "provider": "zhipu",
                    "model": "glm-4",
                    "api_key": "test-key",
                    "base_url": "https://api.zhipu.ai",
                }
                mock_cm_cls.return_value = mock_cm

                # 通过源函数调用（模拟 websocket.py 的函数内导入）
                result = mock_loader_modules["loader"].load_config()

                # 原始 load_config 不应被调用（避免读取项目配置文件）
                original_load.assert_not_called()
                # 但 Config() 应被调用构造默认配置
                mock_loader_modules["schema"].Config.assert_called_once()
                assert result is not None

    def test_load_config_syncs_from_runner(self, mock_loader_modules):
        """_runner_load_config 应从项目配置同步 LLM 字段到 nanobot Config"""
        from src.core.provider_adapter import _patch_websocket_settings_api

        sys_modules = self._make_sys_modules(mock_loader_modules)
        with patch.dict("sys.modules", sys_modules):
            _patch_websocket_settings_api()

            with patch("src.core.provider_adapter.ConfigManager") as mock_cm_cls:
                mock_cm = MagicMock()
                mock_cm.get_llm_config.return_value = {
                    "provider": "zhipu",
                    "model": "glm-4",
                    "api_key": "test-key",
                    "base_url": "https://api.zhipu.ai",
                }
                mock_cm.get.return_value = "Asia/Shanghai"
                mock_cm_cls.return_value = mock_cm

                result = mock_loader_modules["settings_api"].load_config()

                # 验证 LLM 字段被项目配置覆盖
                assert result.agents.defaults.model == "glm-4"
                assert result.agents.defaults.provider == "zhipu"
                # 验证 timezone 被项目配置覆盖
                assert result.agents.defaults.timezone == "Asia/Shanghai"

    def test_save_config_writes_to_runner(self, mock_loader_modules):
        """_runner_save_config 应从 nanobot Config 提取 LLM 字段写入项目配置，并同步环境变量"""
        from src.core.provider_adapter import _patch_websocket_settings_api

        sys_modules = self._make_sys_modules(mock_loader_modules)
        with patch.dict("sys.modules", sys_modules):
            _patch_websocket_settings_api()

            with patch("src.core.provider_adapter.ConfigManager") as mock_cm_cls:
                mock_cm = MagicMock()
                mock_cm.load_config.return_value = {
                    "version": "0.30.0",
                    "data_dir": "/data",
                }
                mock_cm_cls.return_value = mock_cm

                # 构造一个模拟的 nanobot Config 对象
                mock_config = MagicMock()
                mock_config.agents.defaults.model = "new-model"
                mock_config.agents.defaults.provider = "openai"
                mock_config.agents.defaults.timezone = "Asia/Shanghai"
                mock_provider = MagicMock()
                mock_provider.api_key = "new-key"
                mock_provider.api_base = "https://api.openai.com"
                mock_config.providers = MagicMock()
                # getattr(config.providers, "openai") 返回 mock_provider
                mock_config.providers.openai = mock_provider

                # 保存旧环境变量，测试后恢复
                old_env = {k: os.environ.get(k) for k in ("NANOBOT_LLM_API_KEY",)}
                try:
                    mock_loader_modules["settings_api"].save_config(mock_config)

                    # 验证 ConfigManager.save_llm_config 被调用
                    mock_cm.save_llm_config.assert_called_once_with(
                        provider="openai",
                        model="new-model",
                        base_url="https://api.openai.com",
                        api_key="new-key",
                    )
                    # 验证进程环境变量仅同步 API Key（非敏感字段已写入 config.json）
                    assert os.environ["NANOBOT_LLM_API_KEY"] == "new-key"
                    # 验证 timezone 被保存到项目配置
                    mock_cm.save_config.assert_called_once()
                    saved_config = mock_cm.save_config.call_args[0][0]
                    assert saved_config["timezone"] == "Asia/Shanghai"
                finally:
                    for k, v in old_env.items():
                        if v is None:
                            os.environ.pop(k, None)
                        else:
                            os.environ[k] = v

    def test_save_config_saves_non_default_provider_keys(self, mock_loader_modules):
        """_runner_save_config 应保存非默认供应商的 api_key 到 .env.local"""
        from src.core.provider_adapter import _patch_websocket_settings_api

        sys_modules = self._make_sys_modules(mock_loader_modules)
        with patch.dict("sys.modules", sys_modules):
            _patch_websocket_settings_api()

            with (
                patch("src.core.provider_adapter.ConfigManager") as mock_cm_cls,
                patch("src.core.config.env_manager.EnvManager") as mock_env_cls,
            ):
                mock_cm = MagicMock()
                mock_cm.base_dir = Path("/test")
                mock_cm_cls.return_value = mock_cm

                # 默认供应商是 zhipu，另外配置了 siliconflow
                mock_config = MagicMock()
                mock_config.agents.defaults.model = "glm-4"
                mock_config.agents.defaults.provider = "zhipu"
                zhipu_pc = MagicMock()
                zhipu_pc.api_key = "zhipu-key"
                zhipu_pc.api_base = "https://api.zhipu.ai"
                siliconflow_pc = MagicMock()
                siliconflow_pc.api_key = "sf-key"
                siliconflow_pc.api_base = "https://api.siliconflow.cn/v1"
                mock_config.providers = MagicMock()
                mock_config.providers.zhipu = zhipu_pc
                mock_config.providers.siliconflow = siliconflow_pc
                # 让 dir() 返回真实供应商名（MagicMock 的 dir 会包含很多内部属性，
                # 但 hasattr(pc, "api_key") 会过滤掉非 ProviderConfig 的属性）
                mock_config.providers._mock_children = {
                    "zhipu": zhipu_pc,
                    "siliconflow": siliconflow_pc,
                }

                old_env = {}
                for k in ("NANOBOT_LLM_API_KEY_SILICONFLOW",):
                    old_env[k] = os.environ.get(k)
                try:
                    mock_loader_modules["settings_api"].save_config(mock_config)

                    # 验证非默认供应商 api_key 环境变量被更新（api_base 为非敏感字段，不再写入 env）
                    assert os.environ.get("NANOBOT_LLM_API_KEY_SILICONFLOW") == "sf-key"
                    # 验证 EnvManager.save_env_file 被调用
                    mock_env_cls.assert_called_once()
                    mock_env_cls.return_value.save_env_file.assert_called_once()
                finally:
                    for k, v in old_env.items():
                        if v is None:
                            os.environ.pop(k, None)
                        else:
                            os.environ[k] = v

    def test_load_config_restores_provider_keys_from_env(self, mock_loader_modules):
        """_runner_load_config 应从环境变量恢复非默认供应商的 api_key"""
        # 直接用真实 nanobot Config 验证，不 mock schema
        from nanobot.config.schema import Config as RealConfig

        from src.core.provider_adapter import _patch_websocket_settings_api

        # 设置环境变量模拟之前保存的 siliconflow 配置
        old_env = {}
        for k, v in {
            "NANOBOT_LLM_API_KEY_SILICONFLOW": "sf-key",
        }.items():
            old_env[k] = os.environ.get(k)
            os.environ[k] = v

        try:
            # 构造 loader mock，load_config 使用真实 _runner_load_config
            mock_loader = MagicMock()
            mock_loader.load_config = MagicMock(return_value=MagicMock())
            mock_loader.save_config = MagicMock()

            mock_settings_api = MagicMock()
            mock_settings_api.load_config = mock_loader.load_config
            mock_settings_api.save_config = mock_loader.save_config

            mock_schema = MagicMock()
            mock_schema.Config = RealConfig

            mock_nanobot = MagicMock()
            mock_config_pkg = MagicMock()
            mock_config_pkg.loader = mock_loader
            mock_webui = MagicMock()
            mock_webui.settings_api = mock_settings_api

            sys_modules = {
                "nanobot": mock_nanobot,
                "nanobot.config": mock_config_pkg,
                "nanobot.config.loader": mock_loader,
                "nanobot.config.schema": mock_schema,
                "nanobot.webui": mock_webui,
                "nanobot.webui.settings_api": mock_settings_api,
            }

            with patch.dict("sys.modules", sys_modules):
                _patch_websocket_settings_api()

                with patch("src.core.provider_adapter.ConfigManager") as mock_cm_cls:
                    mock_cm = MagicMock()
                    mock_cm.get_llm_config.return_value = {
                        "provider": "zhipu",
                        "model": "glm-4",
                        "api_key": "zhipu-key",
                        "base_url": "https://api.zhipu.ai",
                    }
                    mock_cm_cls.return_value = mock_cm

                    result = mock_loader.load_config()

                    # 验证非默认供应商的 api_key 被恢复（api_base 为非敏感字段，不再从环境变量恢复）
                    assert result.providers.siliconflow.api_key == "sf-key"
        finally:
            for k, v in old_env.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    def test_patch_idempotent(self, mock_loader_modules):
        """多次调用 patch 应安全（幂等）"""
        from src.core.provider_adapter import _patch_websocket_settings_api

        sys_modules = self._make_sys_modules(mock_loader_modules)
        with patch.dict("sys.modules", sys_modules):
            _patch_websocket_settings_api()
            first_load = mock_loader_modules["loader"].load_config
            first_save = mock_loader_modules["loader"].save_config

            _patch_websocket_settings_api()

            # 第二次调用不应替换
            assert mock_loader_modules["loader"].load_config is first_load
            assert mock_loader_modules["loader"].save_config is first_save

    def test_load_config_handles_exception(self, mock_loader_modules):
        """_runner_load_config 在项目配置读取失败时应返回默认 Config"""
        from src.core.provider_adapter import _patch_websocket_settings_api

        sys_modules = self._make_sys_modules(mock_loader_modules)
        with patch.dict("sys.modules", sys_modules):
            _patch_websocket_settings_api()

            with patch("src.core.provider_adapter.ConfigManager") as mock_cm_cls:
                mock_cm_cls.side_effect = Exception("config error")

                # 不应抛出异常，返回默认 config
                result = mock_loader_modules["settings_api"].load_config()
                assert result is not None

    def test_save_config_handles_exception(self, mock_loader_modules):
        """_runner_save_config 在写入失败时不应抛出异常"""
        from src.core.provider_adapter import _patch_websocket_settings_api

        sys_modules = self._make_sys_modules(mock_loader_modules)
        with patch.dict("sys.modules", sys_modules):
            _patch_websocket_settings_api()

            with patch("src.core.provider_adapter.ConfigManager") as mock_cm_cls:
                mock_cm = MagicMock()
                mock_cm.save_llm_config.side_effect = Exception("write error")
                mock_cm_cls.return_value = mock_cm

                mock_config = MagicMock()
                mock_config.agents.defaults.model = "model"
                mock_config.agents.defaults.provider = "provider"
                mock_config.providers = MagicMock()

                # 不应抛出异常
                mock_loader_modules["settings_api"].save_config(mock_config)

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
        config.base_dir = Path("/test/runner")
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


class TestProviderAdapterBranchCoverage:
    """补充分支覆盖测试：异常处理、ImportError 回退、边界条件"""

    def test_resolve_fallback_presets_import_error(self, mock_runner_config):
        """测试 _resolve_fallback_presets 在 ImportError 时返回空列表"""
        mock_runner_config.get_fallback_models.return_value = [
            {"provider": "test", "model": "test-model", "api_key": "key"}
        ]
        adapter = RunnerProviderAdapter(mock_runner_config)
        with patch.dict("sys.modules", {"nanobot.config.schema": None}):
            with patch("builtins.__import__", side_effect=ImportError("no schema")):
                presets = adapter._resolve_fallback_presets()
                assert presets == []

    def test_create_primary_provider_import_error(self, mock_runner_config):
        """测试 _create_primary_provider 在 ImportError 时抛出 LLMError"""
        from src.core.config.llm_config import LLMConfig

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
        from src.core.config.llm_config import LLMConfig

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
        config.get_llm_config.return_value = {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "api_key": "test-key",
            "base_url": "https://api.openai.com",
        }
        config.get_websocket_config.return_value = {}
        config.get_fallback_models.return_value = [
            {
                "provider": "nvidia",
                "model": "llama-4",
                "base_url": "https://api.nvidia.com",
                "api_key": "nvapi-test",
            },
        ]
        config.get_fallback_api_key.return_value = "nvapi-test"
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

    def test_get_or_create_nanobot_config_caches(self, mock_runner_config):
        """测试 _get_or_create_nanobot_config 缓存 nanobot 配置"""
        adapter = RunnerProviderAdapter(mock_runner_config, webui_enabled=False)
        mock_runner_config.get_websocket_config.return_value = {}

        with patch.dict(
            "sys.modules",
            {
                "nanobot": MagicMock(),
                "nanobot.config": MagicMock(),
                "nanobot.config.loader": MagicMock(Config=MagicMock()),
                "nanobot.config.schema": MagicMock(
                    AgentsConfig=MagicMock(),
                    ProvidersConfig=MagicMock(),
                ),
            },
        ):
            result1 = adapter._get_or_create_nanobot_config()
            # 第二次调用应返回缓存
            result2 = adapter._get_or_create_nanobot_config()
            assert result1 is result2

    def test_build_nanobot_config_skips_non_dict_preset(self, mock_runner_config):
        """测试 _build_nanobot_config_from_runner 跳过非 dict 的 model_preset"""
        adapter = RunnerProviderAdapter(mock_runner_config, webui_enabled=False)
        mock_runner_config.get_websocket_config.return_value = {}
        mock_runner_config.load_config.return_value = {
            "model_presets": {
                "valid_preset": {"provider": "openai", "model": "gpt-4"},
                "invalid_preset": "not a dict",  # 应被跳过
            }
        }

        with patch.dict(
            "sys.modules",
            {
                "nanobot": MagicMock(),
                "nanobot.config": MagicMock(),
                "nanobot.config.loader": MagicMock(Config=MagicMock()),
                "nanobot.config.schema": MagicMock(
                    AgentsConfig=MagicMock(),
                    ProvidersConfig=MagicMock(),
                    ModelPresetConfig=MagicMock(),
                ),
            },
        ):
            # 应正常构建，跳过非 dict 的 preset
            adapter._build_nanobot_config_from_runner()

    def test_build_nanobot_config_skips_non_dict_mcp_server(self, mock_runner_config):
        """测试 _build_nanobot_config_from_runner 跳过非 dict 的 mcp_server"""
        adapter = RunnerProviderAdapter(mock_runner_config, webui_enabled=False)
        mock_runner_config.get_websocket_config.return_value = {}
        mock_runner_config.load_config.return_value = {
            "tools": {
                "mcp_servers": {
                    "valid_server": {"command": "test", "args": []},
                    "invalid_server": "not a dict",  # 应被跳过
                }
            }
        }

        with patch.dict(
            "sys.modules",
            {
                "nanobot": MagicMock(),
                "nanobot.config": MagicMock(),
                "nanobot.config.loader": MagicMock(Config=MagicMock()),
                "nanobot.config.schema": MagicMock(
                    AgentsConfig=MagicMock(),
                    ProvidersConfig=MagicMock(),
                    CliAppsToolConfig=MagicMock(),
                    MCPServerConfig=MagicMock(),
                    ToolsConfig=MagicMock(),
                ),
            },
        ):
            # 应正常构建，跳过非 dict 的 mcp_server
            adapter._build_nanobot_config_from_runner()

    def test_build_nanobot_config_llm_error_on_failure(self, mock_runner_config):
        """测试 _build_nanobot_config_from_runner 失败时抛出 LLMError"""
        adapter = RunnerProviderAdapter(mock_runner_config, webui_enabled=False)
        mock_runner_config.get_websocket_config.return_value = {}
        # 让 get_llm_config 抛出异常
        mock_runner_config.get_llm_config.side_effect = NanobotRunnerError(
            "config error"
        )

        with patch.dict(
            "sys.modules",
            {
                "nanobot": MagicMock(),
                "nanobot.config": MagicMock(),
                "nanobot.config.loader": MagicMock(Config=MagicMock()),
                "nanobot.config.schema": MagicMock(
                    AgentsConfig=MagicMock(),
                    ProvidersConfig=MagicMock(),
                ),
            },
        ):
            with pytest.raises(LLMError, match="无法构建nanobot配置"):
                adapter._build_nanobot_config_from_runner()
