from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.core.config import ConfigManager
from src.core.exceptions import ConfigError
from src.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SyncResult:
    """配置同步结果

    Attributes:
        success: 同步是否成功
        errors: 错误信息列表
        warnings: 警告信息列表
        synced_fields: 已同步的字段列表
    """

    success: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    synced_fields: list[str] = field(default_factory=list)


class NanobotConfigSync:
    """nanobot配置同步器

    单向同步项目配置到~/.nanobot/config.json，仅用于兼容已安装nanobot的用户。
    同步方向：~/.nanobot-runner/config.json → ~/.nanobot/config.json

    同步策略：
    - 仅同步LLM相关配置（provider、model、base_url）
    - API Key通过环境变量传递，不写入nanobot配置文件
    - nanobot配置中非LLM字段保持不变
    - 同步失败时返回详细的错误信息，不影响项目功能
    """

    NANOBOT_CONFIG_DIR = Path.home() / ".nanobot"
    NANOBOT_CONFIG_FILE = NANOBOT_CONFIG_DIR / "config.json"

    def __init__(self, runner_config: ConfigManager) -> None:
        """初始化配置同步器

        Args:
            runner_config: 项目配置管理器实例
        """
        self._runner_config = runner_config

    def sync_to_nanobot(self) -> SyncResult:
        """同步项目配置到nanobot配置

        Returns:
            SyncResult: 同步结果
        """
        if not self._has_runner_llm_config():
            return SyncResult(
                success=False,
                errors=["项目配置中未找到LLM配置"],
            )

        if not self._is_nanobot_installed():
            return SyncResult(
                success=False,
                errors=["nanobot未安装或配置目录不存在"],
                warnings=["项目功能不受影响，仅无法同步到nanobot配置"],
            )

        try:
            runner_llm = self._runner_config.get_llm_config()
            nanobot_config = self._load_nanobot_config()
            synced_fields = self._merge_llm_config(nanobot_config, runner_llm)
            self._save_nanobot_config(nanobot_config)

            logger.info(f"已同步 {len(synced_fields)} 个字段到nanobot配置")
            return SyncResult(
                success=True,
                synced_fields=synced_fields,
            )
        except Exception as e:
            logger.error(f"同步到nanobot配置失败: {e}")
            return SyncResult(
                success=False,
                errors=[f"同步失败: {e}"],
                warnings=["项目功能不受影响，仅nanobot配置未更新"],
            )

    def _has_runner_llm_config(self) -> bool:
        """检查项目配置中是否有LLM配置

        Returns:
            bool: 是否存在LLM配置
        """
        try:
            return self._runner_config.has_llm_config()
        except Exception:
            return False

    def _is_nanobot_installed(self) -> bool:
        """检查nanobot是否已安装

        Returns:
            bool: nanobot配置目录是否存在
        """
        return self.NANOBOT_CONFIG_DIR.exists()

    def _load_nanobot_config(self) -> dict[str, Any]:
        """加载nanobot配置

        Returns:
            dict[str, Any]: nanobot配置字典
        """
        if not self.NANOBOT_CONFIG_FILE.exists():
            return self._create_default_nanobot_config()

        try:
            with open(self.NANOBOT_CONFIG_FILE, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"读取nanobot配置失败，创建新配置: {e}")
            return self._create_default_nanobot_config()

    def _create_default_nanobot_config(self) -> dict[str, Any]:
        """创建默认的nanobot配置

        Returns:
            dict[str, Any]: 默认nanobot配置字典
        """
        return {
            "providers": {
                "default": "openai",
                "openai": {
                    "api_key_env": "NANOBOT_LLM_API_KEY",
                },
            },
            "agents": {
                "defaults": {
                    "model": "gpt-4o-mini",
                    "max_tool_iterations": 10,
                    "context_window_tokens": 128000,
                },
            },
        }

    def _merge_llm_config(
        self,
        nanobot_config: dict[str, Any],
        runner_llm: dict[str, Any],
    ) -> list[str]:
        """合并LLM配置到nanobot配置

        Args:
            nanobot_config: nanobot配置字典
            runner_llm: 项目LLM配置字典

        Returns:
            list[str]: 已同步的字段列表
        """
        synced: list[str] = []

        provider = runner_llm.get("provider", "")
        model = runner_llm.get("model", "")
        base_url = runner_llm.get("base_url")

        if provider:
            if "providers" not in nanobot_config:
                nanobot_config["providers"] = {}
            nanobot_config["providers"]["default"] = provider

            if provider not in nanobot_config["providers"]:
                nanobot_config["providers"][provider] = {}
            nanobot_config["providers"][provider]["api_key_env"] = "NANOBOT_LLM_API_KEY"

            if base_url:
                nanobot_config["providers"][provider]["base_url"] = base_url
            elif "base_url" in nanobot_config["providers"].get(provider, {}):
                del nanobot_config["providers"][provider]["base_url"]

            synced.append("providers.default")

        if model:
            if "agents" not in nanobot_config:
                nanobot_config["agents"] = {}
            if "defaults" not in nanobot_config["agents"]:
                nanobot_config["agents"]["defaults"] = {}
            nanobot_config["agents"]["defaults"]["model"] = model
            synced.append("agents.defaults.model")

        return synced

    def _save_nanobot_config(self, config: dict[str, Any]) -> None:
        """保存nanobot配置

        Args:
            config: nanobot配置字典

        Raises:
            ConfigError: 保存失败时抛出
        """
        try:
            self.NANOBOT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(self.NANOBOT_CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except OSError as e:
            raise ConfigError(
                f"保存nanobot配置失败: {e}",
                recovery_suggestion="请检查 ~/.nanobot/ 目录权限",
            ) from e
