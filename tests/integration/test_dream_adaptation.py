"""Dream 适配集成测试

验证 DreamIntegration 适配 nanobot 0.2.2（Dream 类移除后的兼容性）。
nanobot 0.2.2 已移除 Dream 类，改为 cron + process_direct 模式，
DreamIntegration 仅提供配置层面的管理接口。
"""

from pathlib import Path

from src.core.memory.dream_integration import DreamIntegration


def test_dream_integration_initialization(tmp_path: Path):
    """测试 DreamIntegration 初始化不报错"""
    integration = DreamIntegration(config_path=tmp_path / "config.json")
    assert integration is not None
    assert integration.config_path == tmp_path / "config.json"


def test_dream_integration_default_config(tmp_path: Path):
    """测试无配置文件时返回默认 Dream 配置"""
    integration = DreamIntegration(config_path=tmp_path / "config.json")
    config = integration.get_dream_config()

    assert config["enabled"] is True
    assert config["frequency"] == "daily"
    assert config["auto_archive"] is True
    assert config["auto_extract_preferences"] is True


def test_dream_integration_trigger_when_enabled(tmp_path: Path):
    """测试 Dream 启用时 trigger_dream 返回成功（默认启用）"""
    integration = DreamIntegration(config_path=tmp_path / "config.json")
    result = integration.trigger_dream()

    assert result["success"] is True
    assert "config" in result


def test_dream_integration_update_config_persists(tmp_path: Path):
    """测试 update_dream_config 持久化到文件"""
    config_path = tmp_path / "config.json"
    integration = DreamIntegration(config_path=config_path)

    success = integration.set_frequency("weekly")
    assert success is True

    # 重新加载验证持久化
    integration2 = DreamIntegration(config_path=config_path)
    config = integration2.get_dream_config()
    assert config["frequency"] == "weekly"
