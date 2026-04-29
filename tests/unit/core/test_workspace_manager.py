import os
from pathlib import Path
from unittest.mock import patch

from src.core.config.manager import ConfigManager
from src.core.workspace.manager import WorkspaceManager
from src.core.workspace.models import WorkspaceInfo, WorkspaceValidationResult


class TestWorkspaceModels:
    """Workspace 模块数据结构测试"""

    def test_workspace_info(self) -> None:
        info = WorkspaceInfo(
            path=Path("/tmp/workspace"),
            source="env",
            exists=True,
            subdirectories=["data", "memory"],
            disk_usage_mb=10.5,
        )
        assert info.path == Path("/tmp/workspace")
        assert info.source == "env"
        assert "data" in info.subdirectories

    def test_workspace_validation_result_valid(self) -> None:
        result = WorkspaceValidationResult(is_valid=True)
        assert result.is_valid is True
        assert result.errors == []

    def test_workspace_validation_result_invalid(self) -> None:
        result = WorkspaceValidationResult(
            is_valid=False,
            errors=["路径不是目录"],
            suggestions=["请指定目录路径"],
        )
        assert result.is_valid is False
        assert len(result.errors) == 1


class TestWorkspaceManager:
    """Workspace 管理器测试"""

    def test_resolve_workspace_path_default(self, tmp_path: Path) -> None:
        with patch.object(Path, "home", return_value=tmp_path):
            config = ConfigManager(allow_default=True)
            manager = WorkspaceManager(config=config)
            path = manager.resolve_workspace_path()
            assert str(path).endswith(".nanobot-runner") or "nanobot-runner" in str(
                path
            )

    def test_resolve_workspace_path_from_env(self, tmp_path: Path) -> None:
        custom_path = tmp_path / "custom_workspace"
        with patch.dict(
            os.environ, {"NANOBOT_WORKSPACE_DIR": str(custom_path)}, clear=False
        ):
            with patch.object(Path, "home", return_value=tmp_path):
                config = ConfigManager(allow_default=True)
                manager = WorkspaceManager(config=config)
                path = manager.resolve_workspace_path()
                assert path == custom_path.resolve()

    def test_create_workspace(self, tmp_path: Path) -> None:
        workspace = tmp_path / "workspace"
        with patch.object(Path, "home", return_value=tmp_path):
            config = ConfigManager(allow_default=True)
            manager = WorkspaceManager(config=config)
            result = manager.create_workspace(workspace)

            assert result.exists()
            assert (result / "data").exists()
            assert (result / "memory").exists()
            assert (result / "sessions").exists()

    def test_validate_path_valid(self, tmp_path: Path) -> None:
        with patch.object(Path, "home", return_value=tmp_path):
            config = ConfigManager(allow_default=True)
            manager = WorkspaceManager(config=config)
            result = manager.validate_path(tmp_path / "new_workspace")

            assert result.is_valid is True

    def test_validate_path_not_directory(self, tmp_path: Path) -> None:
        existing_file = tmp_path / "existing_file"
        existing_file.write_text("not a directory", encoding="utf-8")

        with patch.object(Path, "home", return_value=tmp_path):
            config = ConfigManager(allow_default=True)
            manager = WorkspaceManager(config=config)
            result = manager.validate_path(existing_file)

            assert result.is_valid is False
            assert any("不是目录" in e for e in result.errors)

    def test_get_workspace_info(self, tmp_path: Path) -> None:
        workspace = tmp_path / ".nanobot-runner"
        workspace.mkdir()
        (workspace / "data").mkdir()

        with patch.object(Path, "home", return_value=tmp_path):
            config = ConfigManager(allow_default=True)
            manager = WorkspaceManager(config=config)
            info = manager.get_workspace_info()

            assert isinstance(info, WorkspaceInfo)
            assert info.exists is True
            assert "data" in info.subdirectories
