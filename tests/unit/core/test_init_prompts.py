from unittest.mock import MagicMock, patch

from src.core.init.prompts import InitPrompts


class TestInitPrompts:
    """交互式配置向导单元测试"""

    def test_default_llm_config(self) -> None:
        config = InitPrompts._default_llm_config()
        assert config["NANOBOT_LLM_PROVIDER"] == "openai"
        assert config["NANOBOT_LLM_MODEL"] == "gpt-4o-mini"
        assert config["NANOBOT_LLM_API_KEY"] == ""
        assert config["NANOBOT_LLM_BASE_URL"] == ""

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
                assert result["NANOBOT_LLM_PROVIDER"] == "openai"

    def test_run_llm_provider_wizard_with_questionary(self) -> None:
        mock_questionary = MagicMock()
        mock_questionary.select.return_value.ask.return_value = "anthropic"
        mock_questionary.text.return_value.ask.return_value = "claude-3-5-sonnet"
        mock_questionary.password.return_value.ask.return_value = "sk-test-key"
        mock_questionary.text.return_value.ask.return_value = (
            "https://api.anthropic.com"
        )

        with patch.dict("sys.modules", {"questionary": mock_questionary}):
            result = InitPrompts.run_llm_provider_wizard()
            assert result["NANOBOT_LLM_PROVIDER"] == "anthropic"

    def test_run_llm_provider_wizard_user_cancels(self) -> None:
        mock_questionary = MagicMock()
        mock_questionary.select.return_value.ask.return_value = None

        with patch.dict("sys.modules", {"questionary": mock_questionary}):
            result = InitPrompts.run_llm_provider_wizard()
            assert result["NANOBOT_LLM_PROVIDER"] == "openai"

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
            assert result["NANOBOT_AUTO_PUSH_FEISHU"] == "false"

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
            assert result["NANOBOT_AUTO_PUSH_FEISHU"] == "true"
            assert result["NANOBOT_FEISHU_APP_ID"] == "cli_test_id"
            assert result["NANOBOT_FEISHU_APP_SECRET"] == "cli_test_secret"

    def test_run_feishu_config_wizard_no_questionary(self) -> None:
        with patch.dict("sys.modules", {"questionary": None}):
            with patch(
                "src.core.init.prompts.InitPrompts.run_feishu_config_wizard"
            ) as mock:
                mock.return_value = {"NANOBOT_AUTO_PUSH_FEISHU": "false"}
                result = mock()
                assert result["NANOBOT_AUTO_PUSH_FEISHU"] == "false"

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
                assert "config" in result
                assert "env_vars" in result
                assert result["config"]["version"] == "0.9.5"
                assert result["config"]["auto_push_feishu"] is False

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
                        "NANOBOT_AUTO_PUSH_FEISHU": "true",
                        "NANOBOT_FEISHU_APP_ID": "test_id",
                        "NANOBOT_FEISHU_APP_SECRET": "test_secret",
                        "NANOBOT_FEISHU_RECEIVE_ID": "test_receive",
                    },
                ):
                    result = InitPrompts.run_full_wizard(skip_optional=False)
                    assert result["config"]["auto_push_feishu"] is True
                    assert "NANOBOT_FEISHU_APP_ID" in result["env_vars"]
