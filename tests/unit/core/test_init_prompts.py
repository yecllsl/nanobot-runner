from unittest.mock import MagicMock, patch

from src import __version__
from src.core.init.prompts import InitPrompts


class TestInitPrompts:
    """交互式配置向导单元测试"""

    def test_default_llm_config(self) -> None:
        config = InitPrompts._default_llm_config()
        assert config["config"]["llm_provider"] == "openai"
        assert config["config"]["llm_model"] == "gpt-4o-mini"
        assert config["env_vars"]["NANOBOT_LLM_API_KEY"] == ""

    def test_default_model_for_provider(self) -> None:
        assert InitPrompts._default_model_for_provider("openai") == "gpt-4o-mini"
        assert (
            InitPrompts._default_model_for_provider("anthropic")
            == "claude-3-5-sonnet-20241022"
        )
        assert InitPrompts._default_model_for_provider("deepseek") == "deepseek-chat"
        assert InitPrompts._default_model_for_provider("other") == "gpt-4o-mini"

    def test_run_llm_provider_wizard_no_questionary(self) -> None:
        with patch.dict("sys.modules", {"questionary": None}):
            with patch(
                "src.core.init.prompts.InitPrompts.run_llm_provider_wizard"
            ) as mock:
                mock.return_value = InitPrompts._default_llm_config()
                result = mock()
                assert result["config"]["llm_provider"] == "openai"

    def test_run_llm_provider_wizard_with_questionary(self) -> None:
        mock_questionary = MagicMock()
        mock_questionary.select.return_value.ask.return_value = "anthropic"
        mock_questionary.text.return_value.ask.return_value = "claude-3-5-sonnet"
        mock_questionary.password.return_value.ask.return_value = "sk-test-key"

        with patch.dict("sys.modules", {"questionary": mock_questionary}):
            with patch.object(
                InitPrompts,
                "run_fallback_wizard",
                return_value={"_model_presets": {}, "_fallback_models": []},
            ):
                result = InitPrompts.run_llm_provider_wizard()
                assert result["config"]["llm_provider"] == "anthropic"

    def test_run_llm_provider_wizard_user_cancels(self) -> None:
        mock_questionary = MagicMock()
        mock_questionary.select.return_value.ask.return_value = None

        with patch.dict("sys.modules", {"questionary": mock_questionary}):
            result = InitPrompts.run_llm_provider_wizard()
            assert result["config"]["llm_provider"] == "openai"

    def test_run_business_config_wizard_no_questionary(self) -> None:
        with patch.dict("sys.modules", {"questionary": None}):
            with patch(
                "src.core.init.prompts.InitPrompts.run_business_config_wizard"
            ) as mock:
                mock.return_value = {"timezone": "Asia/Shanghai"}
                result = mock()
                assert result["timezone"] == "Asia/Shanghai"

    def test_run_business_config_wizard_with_questionary(self) -> None:
        mock_questionary = MagicMock()
        mock_questionary.select.return_value.ask.return_value = "Asia/Tokyo"

        with patch.dict("sys.modules", {"questionary": mock_questionary}):
            result = InitPrompts.run_business_config_wizard()
            assert result["timezone"] == "Asia/Tokyo"

    def test_run_feishu_config_wizard_disabled(self) -> None:
        mock_questionary = MagicMock()
        mock_questionary.confirm.return_value.ask.return_value = False

        with patch.dict("sys.modules", {"questionary": mock_questionary}):
            result = InitPrompts.run_feishu_config_wizard()
            assert result["config"]["auto_push_feishu"] is False

    def test_run_feishu_config_wizard_enabled(self) -> None:
        mock_questionary = MagicMock()
        mock_questionary.confirm.return_value.ask.return_value = True
        mock_questionary.text.return_value.ask.side_effect = [
            "cli_test_id",
            "cli_test_receive",
        ]
        mock_questionary.password.return_value.ask.return_value = "cli_test_secret"

        with patch.dict("sys.modules", {"questionary": mock_questionary}):
            result = InitPrompts.run_feishu_config_wizard()
            assert result["config"]["auto_push_feishu"] is True
            assert result["env_vars"]["NANOBOT_FEISHU_APP_ID"] == "cli_test_id"
            assert result["env_vars"]["NANOBOT_FEISHU_APP_SECRET"] == "cli_test_secret"

    def test_run_feishu_config_wizard_no_questionary(self) -> None:
        with patch.dict("sys.modules", {"questionary": None}):
            with patch(
                "src.core.init.prompts.InitPrompts.run_feishu_config_wizard"
            ) as mock:
                mock.return_value = {
                    "config": {"auto_push_feishu": False},
                    "env_vars": {},
                }
                result = mock()
                assert result["config"]["auto_push_feishu"] is False

    def test_run_full_wizard_skip_optional(self) -> None:
        with patch.object(
            InitPrompts,
            "run_llm_provider_wizard",
            return_value=InitPrompts._default_llm_config(),
        ):
            with patch.object(
                InitPrompts,
                "run_business_config_wizard",
                return_value={"timezone": "Asia/Shanghai"},
            ):
                result = InitPrompts.run_full_wizard(skip_optional=True)
                assert "runner_config" in result
                assert result["runner_config"]["version"] == __version__
                assert result["runner_config"]["auto_push_feishu"] is False

    def test_run_full_wizard_with_optional(self) -> None:
        with patch.object(
            InitPrompts,
            "run_llm_provider_wizard",
            return_value=InitPrompts._default_llm_config(),
        ):
            with patch.object(
                InitPrompts,
                "run_business_config_wizard",
                return_value={"timezone": "Asia/Shanghai"},
            ):
                with patch.object(
                    InitPrompts,
                    "run_feishu_config_wizard",
                    return_value={
                        "config": {"auto_push_feishu": True},
                        "env_vars": {
                            "NANOBOT_FEISHU_APP_ID": "test_id",
                            "NANOBOT_FEISHU_APP_SECRET": "test_secret",
                            "NANOBOT_FEISHU_RECEIVE_ID": "test_receive",
                        },
                    },
                ):
                    result = InitPrompts.run_full_wizard(skip_optional=False)
                    assert result["runner_config"]["auto_push_feishu"] is True
                    # 飞书凭证写入 nanobot_config.channels.feishu
                    nano_cfg = result["nanobot_config"]
                    assert nano_cfg["channels"]["feishu"]["app_id"] == "test_id"


class TestInitPromptsFallback:
    """备选供应商配置向导测试"""

    def test_run_fallback_wizard_no_questionary(self):
        with patch.dict("sys.modules", {"questionary": None}):
            result = InitPrompts.run_fallback_wizard(primary_provider="siliconflow")
            assert result["_model_presets"] == {}
            assert result["_fallback_models"] == []

    def test_run_fallback_wizard_user_declines(self):
        mock_q = MagicMock()
        mock_q.confirm.return_value.ask.return_value = False

        with patch.dict("sys.modules", {"questionary": mock_q}):
            result = InitPrompts.run_fallback_wizard(primary_provider="siliconflow")
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
            result = InitPrompts.run_fallback_wizard(primary_provider="siliconflow")
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


class TestInitPromptsNanobotFormat:
    """测试向导返回 nanobot 原生格式（v0.32.0）"""

    def test_run_full_wizard_data_mode(self):
        """数据模式不生成 nanobot_config"""
        with patch.dict("sys.modules", {"questionary": None}):
            result = InitPrompts.run_full_wizard(agent_mode=False)
            assert result["nanobot_config"] is None
            assert "runner_config" in result

    def test_run_full_wizard_agent_mode_structure(self):
        """Agent 模式返回包含 runner_config 和 nanobot_config"""
        mock_questionary = MagicMock()
        mock_questionary.select.return_value.ask.return_value = "openai"
        mock_questionary.text.return_value.ask.return_value = "gpt-4o-mini"
        mock_questionary.password.return_value.ask.return_value = "sk-test"
        mock_questionary.confirm.return_value.ask.return_value = False

        with patch.dict("sys.modules", {"questionary": mock_questionary}):
            with patch.object(
                InitPrompts,
                "run_fallback_wizard",
                return_value={"_model_presets": {}, "_fallback_models": []},
            ):
                result = InitPrompts.run_full_wizard(agent_mode=True)
                # 验证返回结构包含 nanobot_config
                assert "nanobot_config" in result
                nano_cfg = result["nanobot_config"]
                assert "providers" in nano_cfg
                assert nano_cfg["providers"]["default"] == "openai"
                assert "apiKey" in nano_cfg["providers"]["openai"]
                assert "agents" in nano_cfg
                assert "model" in nano_cfg["agents"]["defaults"]
