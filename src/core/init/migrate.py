from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.core.config import ConfigManager
from src.core.exceptions import ConfigError
from src.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class MigrationResult:
    """迁移结果

    Attributes:
        success: 迁移是否成功
        errors: 错误信息列表
        warnings: 警告信息列表
        migrated_fields: 已迁移的字段列表
        config_path: 迁移后的配置文件路径
        env_path: 迁移后的环境变量文件路径
    """

    success: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    migrated_fields: list[str] = field(default_factory=list)
    config_path: Path | None = None
    env_path: Path | None = None


class ConfigMigrator:
    """配置迁移器

    从nanobot配置（~/.nanobot/config.json）迁移到项目配置（~/.nanobot-runner/）。
    支持将LLM配置、API Key等从nanobot配置格式转换为项目配置格式。

    迁移策略：
    - LLM Provider和Model迁移到项目config.json
    - API Key迁移到.env.local（不写入config.json）
    - 非LLM配置项保持不变
    - 迁移前不删除nanobot配置（保留回退能力）
    """

    NANOBOT_CONFIG_FILE = Path.home() / ".nanobot" / "config.json"

    def __init__(self, runner_config: ConfigManager) -> None:
        """初始化配置迁移器

        Args:
            runner_config: 项目配置管理器实例
        """
        self._runner_config = runner_config

    def migrate_from_nanobot(self) -> MigrationResult:
        """从nanobot配置迁移到项目配置

        Returns:
            MigrationResult: 迁移结果
        """
        nanobot_config = self._load_nanobot_config()
        if nanobot_config is None:
            return MigrationResult(
                success=False,
                errors=["nanobot配置文件不存在或无法读取"],
            )

        migrated_fields: list[str] = []
        warnings: list[str] = []
        env_vars: dict[str, str] = {}

        llm_result = self._migrate_llm_config(nanobot_config)
        if llm_result["fields"]:
            migrated_fields.extend(llm_result["fields"])
            env_vars.update(llm_result["env_vars"])
        else:
            warnings.append("nanobot配置中未找到LLM配置")

        if not migrated_fields:
            return MigrationResult(
                success=False,
                errors=["nanobot配置中没有可迁移的LLM配置"],
                warnings=warnings,
            )

        try:
            config_path, env_path = self._save_migrated_config(
                llm_result["config"], env_vars
            )

            logger.info(f"已迁移 {len(migrated_fields)} 个字段")
            return MigrationResult(
                success=True,
                migrated_fields=migrated_fields,
                warnings=warnings,
                config_path=config_path,
                env_path=env_path,
            )
        except Exception as e:
            return MigrationResult(
                success=False,
                errors=[f"保存迁移配置失败: {e}"],
            )

    def _load_nanobot_config(self) -> dict[str, Any] | None:
        """加载nanobot配置

        Returns:
            dict[str, Any] | None: nanobot配置字典，不存在则返回None
        """
        if not self.NANOBOT_CONFIG_FILE.exists():
            return None

        try:
            with open(self.NANOBOT_CONFIG_FILE, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"读取nanobot配置失败: {e}")
            return None

    def _migrate_llm_config(self, nanobot_config: dict[str, Any]) -> dict[str, Any]:
        """迁移LLM配置

        Args:
            nanobot_config: nanobot配置字典

        Returns:
            dict[str, Any]: 包含fields、env_vars、config的迁移结果
        """
        fields: list[str] = []
        env_vars: dict[str, str] = {}
        config: dict[str, Any] = {}

        providers = nanobot_config.get("providers", {})
        provider_name = providers.get("default", "")

        if provider_name:
            config["llm_provider"] = provider_name
            fields.append("llm_provider")
            env_vars["NANOBOT_LLM_PROVIDER"] = provider_name

        agents = nanobot_config.get("agents", {})
        defaults = agents.get("defaults", {})
        model = defaults.get("model", "")

        if model:
            config["llm_model"] = model
            fields.append("llm_model")
            env_vars["NANOBOT_LLM_MODEL"] = model

        provider_cfg = providers.get(provider_name, {})
        api_key = provider_cfg.get("api_key", "")
        api_key_env = provider_cfg.get("api_key_env", "")

        if api_key:
            env_vars["NANOBOT_LLM_API_KEY"] = api_key
            fields.append("llm_api_key")
        elif api_key_env:
            env_key = os.getenv(api_key_env)
            if env_key:
                env_vars["NANOBOT_LLM_API_KEY"] = env_key
                fields.append("llm_api_key")

        base_url = provider_cfg.get("base_url", "")
        if base_url:
            config["llm_base_url"] = base_url
            fields.append("llm_base_url")
            env_vars["NANOBOT_LLM_BASE_URL"] = base_url

        return {"fields": fields, "env_vars": env_vars, "config": config}

    def _save_migrated_config(
        self,
        llm_config: dict[str, Any],
        env_vars: dict[str, str],
    ) -> tuple[Path, Path]:
        """保存迁移后的配置

        Args:
            llm_config: LLM配置字典
            env_vars: 环境变量字典

        Returns:
            tuple[Path, Path]: (配置文件路径, 环境变量文件路径)

        Raises:
            ConfigError: 保存失败时抛出
        """
        try:
            existing_config: dict[str, Any] = {}
            try:
                existing_config = self._runner_config.load_config()
            except Exception:
                existing_config = self._runner_config._get_default_config()

            existing_config.update(llm_config)
            existing_config["version"] = "0.9.5"

            self._runner_config.save_config(existing_config)
            config_path = self._runner_config.config_file

            env_path = self._runner_config.base_dir / ".env.local"
            if env_vars:
                from src.core.env_manager import EnvManager

                env_manager = EnvManager(env_file=env_path)
                env_manager.save_env_file(env_vars)

            return config_path, env_path

        except OSError as e:
            raise ConfigError(
                f"保存迁移配置失败: {e}",
                recovery_suggestion="请检查目录权限和磁盘空间",
            ) from e
