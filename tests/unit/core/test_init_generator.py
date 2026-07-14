from src.core.init.generator import ConfigGenerator


class TestConfigGeneratorEnvLocal:
    """ConfigGenerator.generate_env_local 测试"""

    def _make_generator(self) -> ConfigGenerator:
        return ConfigGenerator(env_manager=None)

    def test_fallback_api_keys_included(self):
        """v0.32.0: 所有 env_vars 原样写入，含备选供应商 API Key"""
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

    def test_env_local_writes_all_vars(self):
        """v0.32.0: 无备选 key 时仅写入传入的变量"""
        gen = self._make_generator()
        env_vars = {
            "NANOBOT_LLM_PROVIDER": "openai",
            "NANOBOT_LLM_MODEL": "gpt-4o-mini",
            "NANOBOT_LLM_API_KEY": "sk-test",
        }
        result = gen.generate_env_local(env_vars)
        assert "NANOBOT_LLM_API_KEY=sk-test" in result
