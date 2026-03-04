# 配置管理模块
# 管理项目配置和本地数据目录

import json
import os
from pathlib import Path


class ConfigManager:
    """配置管理器，管理项目配置和本地数据目录"""

    def __init__(self):
        """初始化配置管理器"""
        self.base_dir = Path.home() / ".nanobot-runner"
        self.data_dir = self.base_dir / "data"
        self.config_file = self.base_dir / "config.json"
        self.index_file = self.data_dir / "index.json"

        self._ensure_dirs()
        self._ensure_config()

    def _ensure_dirs(self):
        """确保必要目录存在"""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _ensure_config(self):
        """确保配置文件存在"""
        if not self.config_file.exists():
            default_config = {
                "version": "0.1.0",
                "data_dir": str(self.data_dir),
                "auto_push_feishu": False,
                "feishu_webhook": "",
            }
            self.save_config(default_config)

    def save_config(self, config: dict):
        """保存配置"""
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

    def load_config(self) -> dict:
        """加载配置"""
        with open(self.config_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def get(self, key: str, default=None):
        """获取配置项"""
        config = self.load_config()
        return config.get(key, default)

    def set(self, key: str, value):
        """设置配置项"""
        config = self.load_config()
        config[key] = value
        self.save_config(config)


config = ConfigManager()
