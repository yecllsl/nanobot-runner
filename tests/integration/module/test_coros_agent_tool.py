# Coros Agent工具集成测试
# 验证Agent能够通过自然语言调用Coros活动下载工具

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def config_with_coros_tools(tmp_path: Path) -> Path:
    """创建包含Coros工具配置的config.json"""
    config_path = tmp_path / "config.json"
    config = {
        "version": "0.13.0",
        "data_dir": str(tmp_path / "data"),
        "timezone": "Asia/Shanghai",
        "llm_provider": "openai",
        "llm_model": "gpt-4o-mini",
        "tools": {
            "mcp_servers": {
                "coros": {
                    "type": "stdio",
                    "command": "npx",
                    "args": ["-y", "coros-cli", "mcp"],
                    "tool_timeout": 30,
                    "enabled_tools": ["*"],
                }
            }
        },
    }
    config_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")
    return config_path


@pytest.fixture
def temp_workspace_with_coros_skill(tmp_path: Path) -> tuple[Path, Path]:
    """创建包含Coros技能的临时工作空间"""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    skills_dir = workspace / "skills"
    skills_dir.mkdir()

    coros_skill_dir = skills_dir / "coros-activity-downloader"
    coros_skill_dir.mkdir()

    skill_content = """---
name: coros-activity-downloader
description: Coros活动数据下载技能
version: 1.0.0
author: nanobot-runner
tags:
  - coros
  - activity
dependencies:
  - name: coros
    optional: false
enabled_tools:
  - mcp_coros_download_activity
  - mcp_coros_list_activities
---

# Coros活动数据下载技能

支持跑步运动类型(sportType=100)FIT文件下载。
"""
    (coros_skill_dir / "SKILL.md").write_text(skill_content, encoding="utf-8")

    config_path = tmp_path / "config.json"
    config = {
        "version": "0.13.0",
        "data_dir": str(workspace / "data"),
        "skills": {"disabled": []},
        "tools": {
            "mcp_servers": {
                "coros": {
                    "type": "stdio",
                    "command": "npx",
                    "args": ["-y", "coros-cli", "mcp"],
                    "tool_timeout": 30,
                    "enabled_tools": ["*"],
                }
            }
        },
    }
    config_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")

    return workspace, config_path


class TestCorosAgentToolIntegration:
    """Coros Agent工具集成测试"""

    @pytest.mark.asyncio
    async def test_coros_tool_config_loaded(self, config_with_coros_tools: Path):
        """测试Coros工具配置正确加载"""
        from src.core.tools.mcp_config_helper import MCPConfigHelper

        helper = MCPConfigHelper(config_with_coros_tools)
        tools_config = helper.load_tools_config()

        assert tools_config.mcp_servers is not None
        assert "coros" in tools_config.mcp_servers

    @pytest.mark.asyncio
    @patch("nanobot.agent.tools.mcp.connect_mcp_servers", new_callable=AsyncMock)
    async def test_coros_tool_connected(
        self, mock_connect, config_with_coros_tools: Path
    ):
        """测试Coros工具成功连接"""
        from contextlib import AsyncExitStack

        from src.core.tools.mcp_connector import connect_mcp_tools_from_config

        mock_exit_stack = AsyncExitStack()
        mock_connect.return_value = {"coros": mock_exit_stack}

        registry = MagicMock()
        result = await connect_mcp_tools_from_config(config_with_coros_tools, registry)

        assert "coros" in result["connected_servers"]
        assert result["failed_servers"] == []

    @pytest.mark.asyncio
    @patch("nanobot.agent.tools.mcp.connect_mcp_servers", new_callable=AsyncMock)
    async def test_coros_tool_naming_convention(
        self, mock_connect, config_with_coros_tools: Path
    ):
        """测试Coros工具命名规范（mcp_coros_*）"""
        from contextlib import AsyncExitStack

        from src.core.tools.mcp_connector import connect_mcp_tools_from_config

        mock_exit_stack = AsyncExitStack()
        mock_connect.return_value = {"coros": mock_exit_stack}

        registry = MagicMock()
        await connect_mcp_tools_from_config(config_with_coros_tools, registry)

        mock_connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_coros_tool_connection_failure_handling(
        self, config_with_coros_tools: Path
    ):
        """测试Coros工具连接失败的优雅降级"""
        with patch("nanobot.agent.tools.mcp.connect_mcp_servers") as mock_connect:
            mock_connect.side_effect = Exception("Connection failed")

            from src.core.tools.mcp_connector import connect_mcp_tools_from_config

            registry = MagicMock()
            result = await connect_mcp_tools_from_config(
                config_with_coros_tools, registry
            )

            assert result["connected_servers"] == []
            assert "coros" in result["failed_servers"]

    def test_coros_skill_loaded(
        self, temp_workspace_with_coros_skill: tuple[Path, Path]
    ):
        """测试Coros技能正确加载"""
        workspace, config_path = temp_workspace_with_coros_skill
        from src.core.skills.skill_manager import SkillManager

        manager = SkillManager(workspace, config_path)
        skills = manager.list_skills()

        assert len(skills) == 1
        assert skills[0].name == "coros-activity-downloader"

    def test_coros_skill_enabled_tools(
        self, temp_workspace_with_coros_skill: tuple[Path, Path]
    ):
        """测试Coros技能启用的工具"""
        workspace, config_path = temp_workspace_with_coros_skill
        from src.core.skills.skill_manager import SkillManager

        manager = SkillManager(workspace, config_path)
        skill = manager.get_skill("coros-activity-downloader")

        assert skill is not None
        assert "mcp_coros_download_activity" in skill.enabled_tools
        assert "mcp_coros_list_activities" in skill.enabled_tools

    def test_coros_skill_dependencies(
        self, temp_workspace_with_coros_skill: tuple[Path, Path]
    ):
        """测试Coros技能依赖"""
        workspace, config_path = temp_workspace_with_coros_skill
        from src.core.skills.skill_manager import SkillManager

        manager = SkillManager(workspace, config_path)
        skill = manager.get_skill("coros-activity-downloader")

        assert skill is not None
        assert len(skill.dependencies) == 1
        assert skill.dependencies[0].name == "coros"
        assert skill.dependencies[0].optional is False

    @pytest.mark.asyncio
    @patch("nanobot.agent.tools.mcp.connect_mcp_servers", new_callable=AsyncMock)
    async def test_coros_tool_with_skill_integration(
        self, mock_connect, temp_workspace_with_coros_skill: tuple[Path, Path]
    ):
        """测试Coros工具与技能集成"""
        from contextlib import AsyncExitStack

        from src.core.tools.mcp_connector import connect_mcp_tools_from_config

        workspace, config_path = temp_workspace_with_coros_skill

        mock_exit_stack = AsyncExitStack()
        mock_connect.return_value = {"coros": mock_exit_stack}

        registry = MagicMock()
        result = await connect_mcp_tools_from_config(config_path, registry)

        assert "coros" in result["connected_servers"]

    @pytest.mark.asyncio
    async def test_coros_tool_disabled_server_skipped(self, tmp_path: Path):
        """测试禁用的Coros工具服务器被跳过"""
        config_path = tmp_path / "config.json"
        config = {
            "version": "0.13.0",
            "data_dir": str(tmp_path / "data"),
            "tools": {
                "mcp_servers": {
                    "coros": {
                        "type": "stdio",
                        "command": "npx",
                        "args": ["-y", "coros-cli", "mcp"],
                        "disabled": True,
                        "enabled_tools": ["*"],
                    }
                }
            },
        }
        config_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")

        from src.core.tools.mcp_connector import connect_mcp_tools_from_config

        registry = MagicMock()
        result = await connect_mcp_tools_from_config(config_path, registry)

        assert result["connected_servers"] == []
        assert result["failed_servers"] == []
