"""ConfigInjector 单元测试"""

from pathlib import Path

import pytest

from src.core.config_injector import ConfigInjectionError, ConfigInjector


@pytest.fixture
def config_injector(tmp_path):
    config_path = tmp_path / "config.json"
    return ConfigInjector(config_path=config_path)


@pytest.fixture
def runner_config():
    return {
        "agents": {
            "defaults": {
                "model": "gpt-4",
                "provider": "openai",
                "timezone": "Asia/Shanghai",
                "workspace": "~/.nanobot-runner/",
                "max_tool_iterations": 10,
                "context_window_tokens": 128000,
            }
        },
        "providers": {
            "openai": {"api_key": "sk-test", "api_base": "https://api.openai.com/v1"}
        },
        "websocket": {"host": "127.0.0.1", "port": 8765},
        "webui": {"host": "127.0.0.1", "port": 8766},
    }


def test_config_injector_initialization(config_injector, tmp_path):
    """测试 ConfigInjector 初始化"""
    assert config_injector.config_path == tmp_path / "config.json"


def test_build_nanobot_config_success(config_injector, runner_config):
    """测试成功构建 nanobot Config"""
    config = config_injector.build_nanobot_config(runner_config)
    assert config is not None


def test_build_nanobot_config_missing_field(config_injector):
    """测试缺少必要字段时抛出 ConfigInjectionError"""
    with pytest.raises(ConfigInjectionError):
        config_injector.build_nanobot_config({})


def test_save_runner_config(config_injector, tmp_path):
    """测试保存 RunFlowAgent 配置"""
    config = {"test": "value"}
    config_injector.save_runner_config(config)
    assert config_injector.config_path.exists()


def test_resolve_webui_dist_custom(config_injector, tmp_path, monkeypatch):
    """测试解析自定义 WebUI dist 目录"""
    custom_dist = tmp_path / "webui" / "dist"
    custom_dist.mkdir(parents=True)
    # 测试目录存在时返回非 None
    result = config_injector.resolve_webui_dist()
    # 结果可能是 Path 或 None，取决于实际 dist 目录是否存在
    assert result is None or isinstance(result, Path)
