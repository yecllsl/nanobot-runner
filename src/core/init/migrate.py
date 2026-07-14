from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src import __version__
from src.core.base.exceptions import ConfigError, NanobotRunnerError
from src.core.base.logger import get_logger
from src.core.config.legacy import LEGACY_NANOBOT_FIELDS
from src.core.config.manager import ConfigManager

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


def build_nanobot_config_from_legacy(
    legacy_config: dict[str, Any],
    env_keys: dict[str, str],
) -> dict[str, Any]:
    """将旧版 config.json 的 nanobot 字段迁移为 nanobot_config.json 格式

    独立实现字段映射，不复用 RunnerProviderAdapter 私有方法。
    字段映射参考规格说明书第 3.8 节。

    Args:
        legacy_config: 旧版 config.json 字典
        env_keys: 从 .env.local 读取的环境变量字典

    Returns:
        dict[str, Any]: nanobot 原生格式配置字典
    """
    nanobot_config: dict[str, Any] = {}

    # --- providers ---
    provider_name = legacy_config.get("llm_provider", "")
    providers: dict[str, Any] = {}

    if provider_name:
        providers["default"] = provider_name
        provider_cfg: dict[str, Any] = {
            "apiKey": env_keys.get("NANOBOT_LLM_API_KEY", ""),
            "apiType": "auto",
        }
        base_url = legacy_config.get("llm_base_url")
        if base_url:
            provider_cfg["apiBase"] = base_url
        providers[provider_name] = provider_cfg

    # 备选供应商的 apiKey 和 apiBase
    presets = legacy_config.get("model_presets", {})
    fallback_names = legacy_config.get("fallback_models", [])
    for name in fallback_names:
        preset = presets.get(name, {})
        fb_provider = preset.get("provider", "")
        if not fb_provider or fb_provider in providers:
            continue
        fb_api_key = env_keys.get(f"NANOBOT_LLM_API_KEY_{fb_provider.upper()}", "")
        fb_base_url = preset.get("base_url")
        fb_cfg: dict[str, Any] = {"apiKey": fb_api_key, "apiType": "auto"}
        if fb_base_url:
            fb_cfg["apiBase"] = fb_base_url
        providers[fb_provider] = fb_cfg

    nanobot_config["providers"] = providers

    # --- agents.defaults ---
    agents_defaults: dict[str, Any] = {
        "model": legacy_config.get("llm_model", ""),
        "provider": "auto",
        "timezone": legacy_config.get("timezone", "UTC"),
        "workspace": "~/.nanobot-runner",
        "botName": "nanobot-runner",
        "botIcon": "🍀",
    }

    # fallbackModels
    fb_list: list[dict[str, Any]] = []
    for name in fallback_names:
        preset = presets.get(name, {})
        fb_provider = preset.get("provider", "")
        fb_model = preset.get("model", "")
        if fb_provider and fb_model:
            fb_list.append({"model": fb_model, "provider": fb_provider})
    if fb_list:
        agents_defaults["fallbackModels"] = fb_list

    nanobot_config["agents"] = {"defaults": agents_defaults}

    # --- model_presets ---
    nano_presets: dict[str, Any] = {}
    for name, preset in presets.items():
        if not isinstance(preset, dict):
            continue
        nano_presets[name] = {
            "model": preset.get("model", ""),
            "provider": preset.get("provider", "auto"),
        }
    nanobot_config["model_presets"] = nano_presets

    # --- tools.mcpServers ---
    tools_section = legacy_config.get("tools", {})
    mcp_servers = tools_section.get("mcp_servers", {})
    nanobot_config["tools"] = {"mcpServers": mcp_servers}

    # --- channels（从环境变量迁移飞书凭证）---
    channels: dict[str, Any] = {}
    feishu_app_id = env_keys.get("NANOBOT_FEISHU_APP_ID", "")
    feishu_app_secret = env_keys.get("NANOBOT_FEISHU_APP_SECRET", "")
    if feishu_app_id and feishu_app_secret:
        channels["feishu"] = {
            "enabled": True,
            "app_id": feishu_app_id,
            "app_secret": feishu_app_secret,
            "receive_id": env_keys.get("NANOBOT_FEISHU_RECEIVE_ID", ""),
            "receive_id_type": "user_id",
            "allowFrom": ["*"],
        }
    nanobot_config["channels"] = channels

    return nanobot_config


def migrate_config(
    config_manager: ConfigManager,
) -> MigrationResult:
    """将旧版 config.json 的 nanobot 字段迁移到 nanobot_config.json

    迁移流程：
    1. 读取旧 config.json
    2. 读取 .env.local 获取 API Key
    3. 构建 nanobot_config.json
    4. 备份旧 config.json 为 config.json.bak
    5. 写入 nanobot_config.json
    6. 精简 config.json（仅保留 Runner 专有字段）
    7. 更新 .gitignore 排除 nanobot_config.json

    Args:
        config_manager: 配置管理器实例

    Returns:
        MigrationResult: 迁移结果
    """
    try:
        legacy_config = config_manager.load_config()
    except (OSError, ValueError, NanobotRunnerError) as e:
        return MigrationResult(success=False, errors=[f"读取 config.json 失败: {e}"])

    # 检查是否含旧版字段
    has_legacy_fields = any(key in legacy_config for key in LEGACY_NANOBOT_FIELDS)
    if not has_legacy_fields:
        return MigrationResult(
            success=False,
            errors=["config.json 不含旧版 nanobot 字段，无需迁移"],
        )

    # 读取 .env.local
    env_keys: dict[str, str] = {}
    env_path = config_manager.base_dir / ".env.local"
    if env_path.exists():
        from src.core.config.env_manager import EnvManager

        env_manager = EnvManager(env_file=env_path)
        env_keys = env_manager.load_env()

    # 构建 nanobot_config.json
    nanobot_config = build_nanobot_config_from_legacy(legacy_config, env_keys)

    # 备份旧 config.json
    config_path = config_manager.config_file
    backup_path = config_path.with_suffix(".json.bak")
    shutil.copy2(config_path, backup_path)
    logger.info(f"已备份旧配置: {backup_path}")

    # 写入 nanobot_config.json
    nano_path = config_manager.get_nanobot_config_path()
    nano_path.write_text(
        json.dumps(nanobot_config, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # 精简 config.json
    runner_config = {
        "version": __version__,
        "data_dir": legacy_config.get("data_dir", str(config_manager.data_dir)),
        "timezone": legacy_config.get("timezone", "Asia/Shanghai"),
        "auto_push_feishu": legacy_config.get("auto_push_feishu", False),
        "user_id": legacy_config.get("user_id", "default_user"),
    }
    try:
        config_manager.save_config(runner_config)
    except (ValueError, OSError) as e:
        return MigrationResult(
            success=False,
            errors=[f"精简 config.json 失败（nanobot_config.json 已生成）: {e}"],
            config_path=nano_path,
        )

    # 更新 .gitignore
    from src.core.init.generator import ConfigGenerator

    ConfigGenerator.ensure_gitignore_excludes_nanobot_config(config_manager.base_dir)

    migrated_fields = [k for k in LEGACY_NANOBOT_FIELDS if k in legacy_config]

    return MigrationResult(
        success=True,
        migrated_fields=migrated_fields,
        config_path=nano_path,
        warnings=[
            f"旧配置已备份至: {backup_path}",
            "nanobot_config.json 已加入 .gitignore",
        ],
    )


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
        except NanobotRunnerError as e:
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

        非敏感字段（provider/model/base_url）迁移到 config.json，
        敏感字段（api_key）迁移到 .env.local。

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
            # ponytail: 非敏感字段只写入 config.json

        agents = nanobot_config.get("agents", {})
        defaults = agents.get("defaults", {})
        model = defaults.get("model", "")

        if model:
            config["llm_model"] = model
            fields.append("llm_model")

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
            # ponytail: 非敏感字段只写入 config.json

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
            except NanobotRunnerError:
                existing_config = self._runner_config._get_default_config()

            existing_config.update(llm_config)
            existing_config["version"] = __version__

            self._runner_config.save_config(existing_config)
            config_path = self._runner_config.config_file

            env_path = self._runner_config.base_dir / ".env.local"
            if env_vars:
                from src.core.config.env_manager import EnvManager

                env_manager = EnvManager(env_file=env_path)
                env_manager.save_env_file(env_vars)

            return config_path, env_path

        except OSError as e:
            raise ConfigError(
                f"保存迁移配置失败: {e}",
                recovery_suggestion="请检查目录权限和磁盘空间",
            ) from e
