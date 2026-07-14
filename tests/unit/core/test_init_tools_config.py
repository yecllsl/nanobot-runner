# 初始化向导工具配置单元测试
# 测试工具配置集成（通过 run_full_wizard 间接验证 camelCase 格式）

from unittest.mock import patch

from src.core.init.prompts import InitPrompts


class TestToolsConfigIntegration:
    """测试工具配置与config.json的集成"""

    def test_tools_config_in_agent_mode(self):
        """测试agent_mode下配置包含tools字段"""
        with (
            patch.object(
                InitPrompts,
                "run_llm_provider_wizard",
                return_value={
                    "config": {
                        "llm_provider": "openai",
                        "llm_model": "gpt-4o-mini",
                    },
                    "env_vars": {"NANOBOT_LLM_API_KEY": "test-key"},
                },
            ),
            patch.object(
                InitPrompts,
                "run_business_config_wizard",
                return_value={"timezone": "Asia/Shanghai"},
            ),
            patch.object(
                InitPrompts,
                "run_websocket_config_wizard",
                return_value={
                    "enabled": True,
                    "port": 8765,
                    "tokenIssueSecret": "test-secret",
                },
            ),
            patch.object(
                InitPrompts,
                "run_feishu_config_wizard",
                return_value={
                    "config": {"auto_push_feishu": False},
                    "env_vars": {},
                },
            ),
        ):
            result = InitPrompts.run_full_wizard(skip_optional=True, agent_mode=True)
            nano_cfg = result["nanobot_config"]

            assert "tools" in nano_cfg
            assert "mcpServers" in nano_cfg["tools"]
            assert "weather" in nano_cfg["tools"]["mcpServers"]

    def test_tools_config_not_in_data_mode(self):
        """测试非agent_mode下配置不包含tools字段"""
        with patch.object(
            InitPrompts,
            "run_business_config_wizard",
            return_value={"timezone": "Asia/Shanghai"},
        ):
            result = InitPrompts.run_full_wizard(skip_optional=True, agent_mode=False)
            runner_cfg = result["runner_config"]

            assert "tools" not in runner_cfg
