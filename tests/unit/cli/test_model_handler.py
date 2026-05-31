from unittest.mock import MagicMock

from src.cli.handlers.model_handler import ModelHandler


class TestModelHandlerListPresets:
    """ModelHandler.list_presets 测试"""

    def _make_handler(self, config_data: dict) -> ModelHandler:
        mock_context = MagicMock()
        mock_config = MagicMock()
        mock_config.load_config.return_value = config_data
        mock_context.config = mock_config
        return ModelHandler(context=mock_context)

    def test_list_presets_with_fallback_flag(self):
        config_data = {
            "model_presets": {
                "siliconflow-qwen3": {
                    "provider": "siliconflow",
                    "model": "Qwen/Qwen3-235B-A22B",
                    "base_url": "https://api.siliconflow.cn/v1",
                },
                "nvidia-llama4": {
                    "provider": "nvidia",
                    "model": "meta/llama-4-maverick-17b-128e-instruct-maas",
                    "base_url": "https://integrate.api.nvidia.com/v1",
                },
            },
            "fallback_models": ["nvidia-llama4"],
        }
        handler = self._make_handler(config_data)
        presets = handler.list_presets()
        assert len(presets) == 2
        nvidia_preset = next(p for p in presets if p["name"] == "nvidia-llama4")
        assert nvidia_preset["is_fallback"] is True
        sf_preset = next(p for p in presets if p["name"] == "siliconflow-qwen3")
        assert sf_preset["is_fallback"] is False

    def test_list_presets_no_fallback_config(self):
        config_data = {
            "model_presets": {
                "openai-gpt4": {
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                },
            },
        }
        handler = self._make_handler(config_data)
        presets = handler.list_presets()
        assert len(presets) == 1
        assert presets[0]["is_fallback"] is False
