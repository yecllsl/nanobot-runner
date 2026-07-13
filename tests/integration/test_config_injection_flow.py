"""配置注入全流程集成测试

验证 ConfigInjector 将 RunFlowAgent 配置转换为 nanobot Config 的完整链路。
"""

from pathlib import Path

from src.core.config_injector import ConfigInjector


def test_config_injection_full_flow(tmp_path: Path):
    """测试 ConfigInjector → nanobot Config 完整链路"""
    config_path = tmp_path / "config.json"
    injector = ConfigInjector(config_path=config_path)

    runner_config = {
        "agents": {
            "defaults": {
                "model": "gpt-4",
                "provider": "openai",
                "timezone": "Asia/Shanghai",
                "max_tool_iterations": 10,
                "context_window_tokens": 128000,
            }
        },
        "providers": {
            "openai": {"api_key": "sk-test", "api_base": "https://api.openai.com/v1"},
            "mistral": {
                "api_key": "sk-mistral",
                "api_base": "https://api.mistral.ai/v1",
            },
        },
        "transcription": {
            "enabled": False,
            "provider": "assemblyai",
            "language": "zh",
        },
    }

    config = injector.build_nanobot_config(runner_config)

    # 验证 agents 配置
    assert config.agents.defaults.model == "gpt-4"
    assert config.agents.defaults.provider == "openai"
    assert config.agents.defaults.timezone == "Asia/Shanghai"
    assert config.agents.defaults.max_tool_iterations == 10
    assert config.agents.defaults.context_window_tokens == 128000

    # 验证 providers 配置（ProvidersConfig extra="allow"）
    assert config.providers.openai.api_key == "sk-test"
    assert config.providers.openai.api_base == "https://api.openai.com/v1"
    assert config.providers.mistral.api_key == "sk-mistral"

    # 验证 transcription 配置
    assert config.transcription.enabled is False
    assert config.transcription.provider == "assemblyai"
    assert config.transcription.language == "zh"


def test_config_injection_minimal_config(tmp_path: Path):
    """测试最小配置（仅 agents.defaults）"""
    injector = ConfigInjector(config_path=tmp_path / "config.json")
    config = injector.build_nanobot_config(
        {"agents": {"defaults": {"model": "gpt-4", "provider": "openai"}}}
    )
    assert config.agents.defaults.model == "gpt-4"
    assert config.agents.defaults.provider == "openai"


def test_config_injection_with_transcription_disabled(tmp_path: Path):
    """测试 transcription 默认禁用"""
    injector = ConfigInjector(config_path=tmp_path / "config.json")
    config = injector.build_nanobot_config(
        {
            "agents": {"defaults": {"model": "gpt-4", "provider": "openai"}},
            "transcription": {"enabled": False},
        }
    )
    assert config.transcription.enabled is False
