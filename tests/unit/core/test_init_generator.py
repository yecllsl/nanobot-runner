from src.core.init.generator import ConfigGenerator


class TestConfigGeneratorEnvLocal:
    """ConfigGenerator.generate_env_local 测试"""

    def _make_generator(self) -> ConfigGenerator:
        return ConfigGenerator(env_manager=None)

    def test_fallback_api_keys_included(self):
        gen = self._make_generator()
        env_vars = {
            "NANOBOT_LLM_PROVIDER": "siliconflow",
            "NANOBOT_LLM_MODEL": "Qwen/Qwen3-235B-A22B",
            "NANOBOT_LLM_API_KEY": "sk-sf-test",
            "NANOBOT_LLM_BASE_URL": "https://api.siliconflow.cn/v1",
            "NANOBOT_LLM_API_KEY_NVIDIA": "nvapi-test",
            "NANOBOT_LLM_API_KEY_OPENROUTER": "sk-or-test",
        }
        result = gen.generate_env_local(env_vars)
        assert "NANOBOT_LLM_API_KEY_NVIDIA=nvapi-test" in result
        assert "NANOBOT_LLM_API_KEY_OPENROUTER=sk-or-test" in result
        assert "备选供应商" in result

    def test_no_fallback_keys_omits_section(self):
        gen = self._make_generator()
        env_vars = {
            "NANOBOT_LLM_PROVIDER": "openai",
            "NANOBOT_LLM_MODEL": "gpt-4o-mini",
            "NANOBOT_LLM_API_KEY": "sk-test",
        }
        result = gen.generate_env_local(env_vars)
        assert "备选供应商" not in result
