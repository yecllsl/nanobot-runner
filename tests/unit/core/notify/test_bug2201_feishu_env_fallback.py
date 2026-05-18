"""BUG-2201回归测试：飞书凭证.env.local自动加载

验证FeishuAuth在config.json中无凭证、os.environ中也无凭证、
但.env.local文件中有凭证时，能自动加载.env.local并读取飞书配置。
"""

import os
from pathlib import Path

from src.core.config.manager import ConfigManager
from src.notify.feishu import FeishuAuth


class TestBug2201FeishuEnvLocalAutoLoad:
    """BUG-2201: 飞书凭证.env.local自动加载测试"""

    def test_auto_load_env_local_when_config_empty(self, tmp_path: Path):
        """当config.json和环境变量都无凭证，但.env.local文件中有凭证时，
        FeishuAuth应自动加载.env.local并读取凭证"""
        config_file = tmp_path / "config.json"
        config_file.write_text(
            '{"version": "0.9.4", "data_dir": "'
            + str(tmp_path / "data").replace("\\", "\\\\")
            + '", "feishu_app_id": "", "feishu_app_secret": ""}'
        )

        env_local = tmp_path / ".env.local"
        env_local.write_text(
            "NANOBOT_FEISHU_APP_ID=env_local_app_id\n"
            "NANOBOT_FEISHU_APP_SECRET=env_local_app_secret\n"
        )

        env_keys_to_remove = [
            "NANOBOT_FEISHU_APP_ID",
            "NANOBOT_FEISHU_APP_SECRET",
        ]
        saved_env = {}
        for k in env_keys_to_remove:
            if k in os.environ:
                saved_env[k] = os.environ.pop(k)

        try:
            ConfigManager.reset_cache()
            config = ConfigManager(allow_default=False)
            config.config_file = config_file
            config._using_default = False
            config.base_dir = tmp_path

            auth = FeishuAuth(config=config)

            assert auth.app_id == "env_local_app_id", (
                f"期望app_id从.env.local读取为'env_local_app_id'，实际为'{auth.app_id}'"
            )
            assert auth.app_secret == "env_local_app_secret", (
                f"期望app_secret从.env.local读取为'env_local_app_secret'，实际为'{auth.app_secret}'"
            )
        finally:
            for k, v in saved_env.items():
                os.environ[k] = v
            for k in env_keys_to_remove:
                os.environ.pop(k, None)

    def test_is_configured_after_env_local_load(self, tmp_path: Path):
        """自动加载.env.local后，is_configured应返回True"""
        config_file = tmp_path / "config.json"
        config_file.write_text(
            '{"version": "0.9.4", "data_dir": "'
            + str(tmp_path / "data").replace("\\", "\\\\")
            + '", "feishu_app_id": "", "feishu_app_secret": ""}'
        )

        env_local = tmp_path / ".env.local"
        env_local.write_text(
            "NANOBOT_FEISHU_APP_ID=env_local_app_id\n"
            "NANOBOT_FEISHU_APP_SECRET=env_local_app_secret\n"
        )

        env_keys_to_remove = [
            "NANOBOT_FEISHU_APP_ID",
            "NANOBOT_FEISHU_APP_SECRET",
        ]
        saved_env = {}
        for k in env_keys_to_remove:
            if k in os.environ:
                saved_env[k] = os.environ.pop(k)

        try:
            ConfigManager.reset_cache()
            config = ConfigManager(allow_default=False)
            config.config_file = config_file
            config._using_default = False
            config.base_dir = tmp_path

            auth = FeishuAuth(config=config)

            assert auth.is_configured(), (
                "自动加载.env.local后，is_configured()应返回True"
            )
        finally:
            for k, v in saved_env.items():
                os.environ[k] = v
            for k in env_keys_to_remove:
                os.environ.pop(k, None)
