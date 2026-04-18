import json
from pathlib import Path
from typing import Any

from src.core.env_manager import EnvManager
from src.core.exceptions import ConfigError
from src.core.logger import get_logger

logger = get_logger(__name__)

_AGENTS_MD_TEMPLATE = """# AGENTS.md - Nanobot Runner Agent 配置

> 此文件由初始化向导自动生成

## 1. LLM 配置

- **Provider**: {llm_provider}
- **Model**: {llm_model}

## 2. 业务配置

- **数据目录**: {data_dir}
- **时区**: {timezone}

## 3. 工具配置

- **飞书通知**: {feishu_enabled}
"""


class ConfigGenerator:
    """配置文件生成器

    根据用户输入生成 config.json、.env.local、AGENTS.md 等配置文件。
    """

    def __init__(self, env_manager: EnvManager | None = None) -> None:
        """初始化配置文件生成器

        Args:
            env_manager: 环境变量管理器（可选）
        """
        self.env_manager = env_manager or EnvManager()

    def generate_config_json(self, config: dict[str, Any]) -> str:
        """生成 config.json 文件内容

        Args:
            config: 配置字典

        Returns:
            str: JSON 格式的配置文件内容
        """
        return json.dumps(config, indent=2, ensure_ascii=False)

    def generate_env_local(self, env_vars: dict[str, str]) -> str:
        """生成 .env.local 文件内容

        Args:
            env_vars: 环境变量字典

        Returns:
            str: .env.local 文件内容
        """
        lines: list[str] = ["# Nanobot Runner 环境变量配置\n"]

        if env_vars.get("NANOBOT_LLM_API_KEY"):
            lines.append("# LLM 配置\n")
            lines.append(
                f"NANOBOT_LLM_PROVIDER={env_vars.get('NANOBOT_LLM_PROVIDER', 'openai')}\n"
            )
            lines.append(
                f"NANOBOT_LLM_MODEL={env_vars.get('NANOBOT_LLM_MODEL', 'gpt-4o-mini')}\n"
            )
            lines.append(f"NANOBOT_LLM_API_KEY={env_vars['NANOBOT_LLM_API_KEY']}\n")
            base_url = env_vars.get("NANOBOT_LLM_BASE_URL", "")
            if base_url:
                lines.append(f"NANOBOT_LLM_BASE_URL={base_url}\n")

        feishu_keys = [
            "NANOBOT_FEISHU_APP_ID",
            "NANOBOT_FEISHU_APP_SECRET",
            "NANOBOT_FEISHU_RECEIVE_ID",
        ]
        has_feishu = any(env_vars.get(k) for k in feishu_keys)
        if has_feishu:
            lines.append("\n# 飞书通知配置\n")
            for key in feishu_keys:
                if env_vars.get(key):
                    lines.append(f"{key}={env_vars[key]}\n")
            lines.append(
                f"NANOBOT_AUTO_PUSH_FEISHU={env_vars.get('NANOBOT_AUTO_PUSH_FEISHU', 'false')}\n"
            )

        return "".join(lines)

    def generate_agents_md(self, config: dict[str, Any]) -> str:
        """生成 AGENTS.md 文件内容

        Args:
            config: 配置字典

        Returns:
            str: AGENTS.md 文件内容
        """
        return _AGENTS_MD_TEMPLATE.format(
            llm_provider=config.get("llm_provider", "openai"),
            llm_model=config.get("llm_model", "gpt-4o-mini"),
            data_dir=config.get("data_dir", ""),
            timezone=config.get("timezone", "Asia/Shanghai"),
            feishu_enabled="已启用" if config.get("auto_push_feishu") else "未启用",
        )

    def write_config_files(
        self,
        workspace_dir: Path,
        config: dict[str, Any],
        env_vars: dict[str, str] | None = None,
    ) -> dict[str, Path]:
        """写入所有配置文件

        Args:
            workspace_dir: workspace 目录路径
            config: 配置字典
            env_vars: 环境变量字典（可选）

        Returns:
            dict[str, Path]: 写入的文件路径字典

        Raises:
            ConfigError: 写入失败时抛出
        """
        written: dict[str, Path] = {}

        try:
            workspace_dir.mkdir(parents=True, exist_ok=True)

            config_path = workspace_dir / "config.json"
            config_path.write_text(self.generate_config_json(config), encoding="utf-8")
            written["config"] = config_path

            if env_vars:
                env_path = workspace_dir / ".env.local"
                env_path.write_text(self.generate_env_local(env_vars), encoding="utf-8")
                written["env"] = env_path

            agents_path = workspace_dir / "AGENTS.md"
            agents_path.write_text(self.generate_agents_md(config), encoding="utf-8")
            written["agents"] = agents_path

            logger.info(f"配置文件已写入: {list(written.keys())}")
            return written

        except OSError as e:
            raise ConfigError(
                f"写入配置文件失败: {e}",
                recovery_suggestion="请检查目录权限和磁盘空间",
            ) from e
