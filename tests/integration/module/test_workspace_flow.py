import json
import os
from pathlib import Path
from unittest.mock import patch

from src.core.config.manager import ConfigManager
from src.core.workspace.manager import WorkspaceManager
from src.core.workspace.models import WorkspaceInfo


class TestWorkspaceFlowIntegration:
    """工作区流程集成测试：WorkspaceManager → ConfigManager"""

    def test_default_workspace_creation(self, tmp_path: Path) -> None:
        """默认工作区创建"""
        with patch.object(Path, "home", return_value=tmp_path):
            config = ConfigManager(allow_default=True)
            manager = WorkspaceManager(config=config)

            workspace_path = manager.resolve_workspace_path()
            manager.create_workspace(workspace_path)

            assert workspace_path.exists()
            assert (workspace_path / "data").exists()

    def test_custom_workspace_via_env(self, tmp_path: Path) -> None:
        """通过环境变量指定工作区"""
        custom_workspace = tmp_path / "custom_ws"

        os.environ["NANOBOT_WORKSPACE_DIR"] = str(custom_workspace)
        try:
            with patch.object(Path, "home", return_value=tmp_path):
                config = ConfigManager(allow_default=True)
                manager = WorkspaceManager(config=config)

                path = manager.resolve_workspace_path()
                assert path == custom_workspace.resolve()
        finally:
            os.environ.pop("NANOBOT_WORKSPACE_DIR", None)

    def test_workspace_info(self, tmp_path: Path) -> None:
        """获取工作区信息"""
        with patch.object(Path, "home", return_value=tmp_path):
            config = ConfigManager(allow_default=True)
            manager = WorkspaceManager(config=config)

            workspace_path = manager.resolve_workspace_path()
            manager.create_workspace(workspace_path)

            info = manager.get_workspace_info()
            assert isinstance(info, WorkspaceInfo)
            assert info.exists is True
            assert "data" in info.subdirectories

    def test_workspace_config_consistency(self, tmp_path: Path) -> None:
        """工作区与配置文件一致性"""
        config_dir = tmp_path / ".nanobot-runner"
        config_dir.mkdir(parents=True, exist_ok=True)
        data_dir = config_dir / "data"
        data_dir.mkdir(exist_ok=True)
        (config_dir / "config.json").write_text(
            json.dumps({"version": "0.9.4", "data_dir": str(data_dir)}),
            encoding="utf-8",
        )

        with patch.object(Path, "home", return_value=tmp_path):
            config = ConfigManager(allow_default=True)
            manager = WorkspaceManager(config=config)

            info = manager.get_workspace_info()
            assert info.exists is True
