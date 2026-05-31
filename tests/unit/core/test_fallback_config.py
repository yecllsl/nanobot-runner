import os
from unittest.mock import patch

from src.core.config.manager import ConfigManager
from src.core.config.schema import AppConfig


class TestAppConfigFallbackModels:
    def test_fallback_models_none_by_default(self):
        config = AppConfig(version="0.9.5", data_dir="/data")
        assert config.fallback_models is None

    def test_fallback_models_with_list(self):
        config = AppConfig(
            version="0.9.5",
            data_dir="/data",
            fallback_models=["nvidia-llama4", "openrouter-gemini"],
        )
        assert config.fallback_models == ["nvidia-llama4", "openrouter-gemini"]

    def test_validate_fallback_models_str_list(self):
        config = {
            "version": "0.9.5",
            "data_dir": "/data",
            "fallback_models": ["preset-a", "preset-b"],
        }
        is_valid, errors = AppConfig.validate(config)
        assert is_valid
        assert len(errors) == 0

    def test_validate_fallback_models_rejects_non_str_items(self):
        config = {
            "version": "0.9.5",
            "data_dir": "/data",
            "fallback_models": [123, "preset-b"],
        }
        is_valid, errors = AppConfig.validate(config)
        assert not is_valid
        assert any("fallback_models" in e for e in errors)

    def test_from_dict_with_fallback_models(self):
        config = {
            "version": "0.9.5",
            "data_dir": "/data",
            "fallback_models": ["preset-a"],
        }
        app_config = AppConfig.from_dict(config)
        assert app_config.fallback_models == ["preset-a"]

    def test_to_dict_includes_fallback_models(self):
        config = AppConfig(
            version="0.9.5",
            data_dir="/data",
            fallback_models=["preset-a"],
        )
        d = config.to_dict()
        assert d["fallback_models"] == ["preset-a"]

    def test_to_dict_fallback_models_none(self):
        config = AppConfig(version="0.9.5", data_dir="/data")
        d = config.to_dict()
        assert d["fallback_models"] is None


class TestConfigManagerFallbackApiKey:
    def test_get_fallback_api_key_from_env(self):
        config = ConfigManager(allow_default=True)
        with patch.dict(
            os.environ, {"NANOBOT_LLM_API_KEY_NVIDIA": "nvapi-test"}, clear=False
        ):
            result = config.get_fallback_api_key("nvidia")
            assert result == "nvapi-test"

    def test_get_fallback_api_key_fallback_to_main(self):
        config = ConfigManager(allow_default=True)
        with patch.dict(os.environ, {"NANOBOT_LLM_API_KEY": "main-key"}, clear=False):
            if "NANOBOT_LLM_API_KEY_NVIDIA" in os.environ:
                del os.environ["NANOBOT_LLM_API_KEY_NVIDIA"]
            result = config.get_fallback_api_key("nvidia")
            assert result == "main-key"

    def test_get_fallback_api_key_none(self):
        config = ConfigManager(allow_default=True)
        env_to_clear = [
            "NANOBOT_LLM_API_KEY_NVIDIA",
            "NANOBOT_LLM_API_KEY",
        ]
        with patch.dict(os.environ, {}, clear=False):
            for k in env_to_clear:
                if k in os.environ:
                    del os.environ[k]
            result = config.get_fallback_api_key("nvidia")
            assert result is None


class TestConfigManagerGetFallbackModels:
    def test_get_fallback_models_empty(self):
        config = ConfigManager(allow_default=True)
        with patch.object(
            config,
            "load_config",
            return_value={"version": "0.9.5", "data_dir": "/data"},
        ):
            result = config.get_fallback_models()
            assert result == []

    def test_get_fallback_models_with_presets(self):
        config = ConfigManager(allow_default=True)
        mock_config = {
            "version": "0.9.5",
            "data_dir": "/data",
            "model_presets": {
                "nvidia-llama4": {
                    "provider": "nvidia",
                    "model": "meta/llama-4-maverick-17b-128e-instruct-maas",
                    "base_url": "https://integrate.api.nvidia.com/v1",
                },
            },
            "fallback_models": ["nvidia-llama4"],
        }
        with patch.object(config, "load_config", return_value=mock_config):
            with patch.object(
                config, "get_fallback_api_key", return_value="nvapi-test"
            ):
                result = config.get_fallback_models()
                assert len(result) == 1
                assert result[0]["provider"] == "nvidia"
                assert (
                    result[0]["model"] == "meta/llama-4-maverick-17b-128e-instruct-maas"
                )
                assert result[0]["base_url"] == "https://integrate.api.nvidia.com/v1"
                assert result[0]["api_key"] == "nvapi-test"

    def test_get_fallback_models_missing_preset_skipped(self):
        config = ConfigManager(allow_default=True)
        mock_config = {
            "version": "0.9.5",
            "data_dir": "/data",
            "model_presets": {},
            "fallback_models": ["nonexistent-preset"],
        }
        with patch.object(config, "load_config", return_value=mock_config):
            result = config.get_fallback_models()
            assert result == []

    def test_get_fallback_models_incomplete_preset_skipped(self):
        config = ConfigManager(allow_default=True)
        mock_config = {
            "version": "0.9.5",
            "data_dir": "/data",
            "model_presets": {
                "bad-preset": {"provider": "nvidia"},
            },
            "fallback_models": ["bad-preset"],
        }
        with patch.object(config, "load_config", return_value=mock_config):
            result = config.get_fallback_models()
            assert result == []
