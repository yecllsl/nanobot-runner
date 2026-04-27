# 初始化向导工具配置单元测试
# 测试InitPrompts._default_tools_config和工具配置集成

import json
from pathlib import Path
from unittest.mock import patch

from src.core.init.prompts import InitPrompts


class TestDefaultToolsConfig:
    """测试_default_tools_config方法"""

    def test_returns_dict_with_mcp_servers(self):
        """测试返回包含mcp_servers的字典"""
        result = InitPrompts._default_tools_config()
        assert isinstance(result, dict)
        assert "mcp_servers" in result

    def test_weather_server_configured(self):
        """测试天气MCP服务器默认配置"""
        result = InitPrompts._default_tools_config()
        mcp_servers = result["mcp_servers"]

        assert "weather" in mcp_servers
        weather = mcp_servers["weather"]

        assert weather["type"] == "stdio"
        assert weather["command"] == "npx"
        assert weather["args"] == ["-y", "@dangahagan/weather-mcp"]
        assert weather["tool_timeout"] == 30
        assert weather["enabled_tools"] == ["*"]

    def test_weather_server_not_disabled(self):
        """测试天气服务器默认不禁用"""
        result = InitPrompts._default_tools_config()
        weather = result["mcp_servers"]["weather"]
        assert "disabled" not in weather or weather.get("disabled") is False


class TestToolsConfigIntegration:
    """测试工具配置与config.json的集成"""

    def test_tools_config_in_agent_mode(self):
        """测试agent_mode下配置包含tools字段"""
        with (
            patch.object(
                InitPrompts,
                "run_llm_provider_wizard",
                return_value={
                    "NANOBOT_LLM_PROVIDER": "openai",
                    "NANOBOT_LLM_MODEL": "gpt-4o-mini",
                    "NANOBOT_LLM_API_KEY": "test-key",
                    "NANOBOT_LLM_BASE_URL": "",
                },
            ),
            patch.object(
                InitPrompts,
                "run_business_config_wizard",
                return_value={"timezone": "Asia/Shanghai"},
            ),
            patch.object(
                InitPrompts,
                "run_feishu_config_wizard",
                return_value={"NANOBOT_AUTO_PUSH_FEISHU": "false"},
            ),
        ):
            result = InitPrompts.run_full_wizard(skip_optional=True, agent_mode=True)
            config = result["config"]

            assert "tools" in config
            assert "mcp_servers" in config["tools"]
            assert "weather" in config["tools"]["mcp_servers"]

    def test_tools_config_not_in_data_mode(self):
        """测试非agent_mode下配置不包含tools字段"""
        with patch.object(
            InitPrompts,
            "run_business_config_wizard",
            return_value={"timezone": "Asia/Shanghai"},
        ):
            result = InitPrompts.run_full_wizard(skip_optional=True, agent_mode=False)
            config = result["config"]

            assert "tools" not in config

    def test_tools_config_serializable(self):
        """测试工具配置可正确序列化为JSON"""
        result = InitPrompts._default_tools_config()
        json_str = json.dumps(result, ensure_ascii=False)
        parsed = json.loads(json_str)

        assert parsed["mcp_servers"]["weather"]["type"] == "stdio"
        assert parsed["mcp_servers"]["weather"]["command"] == "npx"
        assert parsed["mcp_servers"]["weather"]["args"] == [
            "-y",
            "@dangahagan/weather-mcp",
        ]

    def test_weather_config_compatible_with_mcp_config_helper(self, tmp_path: Path):
        """测试天气配置与MCPConfigHelper兼容"""
        from src.core.tools.mcp_config_helper import MCPConfigHelper
        from src.core.tools.models import MCPTransportType

        tools_config = InitPrompts._default_tools_config()

        config_path = tmp_path / "config.json"
        config = {
            "version": "0.13.0",
            "data_dir": str(tmp_path / "data"),
            "tools": tools_config,
        }
        config_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")

        helper = MCPConfigHelper(config_path)
        loaded_config = helper.load_tools_config()

        assert "weather" in loaded_config.mcp_servers
        weather = loaded_config.mcp_servers["weather"]

        assert weather.name == "weather"
        assert weather.transport_type == MCPTransportType.STDIO
        assert weather.command == "npx"
        assert weather.args == ["-y", "@dangahagan/weather-mcp"]
        assert weather.enabled_tools == ["*"]
        assert not weather.disabled
