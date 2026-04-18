import os
from pathlib import Path
from unittest.mock import patch

from src.core.env_manager import EnvManager


class TestEnvManager:
    """环境变量管理器单元测试"""

    def test_init_default(self, tmp_path: Path) -> None:
        manager = EnvManager()
        assert manager.env_file == Path(".env.local")
        assert manager._loaded is False

    def test_init_custom_path(self, tmp_path: Path) -> None:
        custom = tmp_path / ".env.test"
        manager = EnvManager(env_file=custom)
        assert manager.env_file == custom

    def test_load_env_file_not_exists(self, tmp_path: Path) -> None:
        manager = EnvManager(env_file=tmp_path / ".env.notexist")
        result = manager.load_env()
        assert result == {}

    def test_load_env_file_exists(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env.local"
        env_file.write_text(
            "TEST_KEY=test_value\nANOTHER_KEY=another_val\n", encoding="utf-8"
        )

        manager = EnvManager(env_file=env_file)
        result = manager.load_env()

        assert "TEST_KEY" in result
        assert result["TEST_KEY"] == "test_value"
        assert result["ANOTHER_KEY"] == "another_val"

    def test_load_env_skips_comments_and_empty(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env.local"
        env_file.write_text("# comment\n\nKEY=val\n", encoding="utf-8")

        manager = EnvManager(env_file=env_file)
        result = manager.load_env()

        assert "KEY" in result
        assert result["KEY"] == "val"
        assert len(result) == 1

    def test_load_env_strips_whitespace(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env.local"
        env_file.write_text("  KEY  =  value  \n", encoding="utf-8")

        manager = EnvManager(env_file=env_file)
        result = manager.load_env()

        assert result.get("KEY") == "value"

    def test_get_env(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, {"TEST_GET_KEY": "test_val"}, clear=False):
            manager = EnvManager()
            assert manager.get_env("TEST_GET_KEY") == "test_val"

    def test_get_env_default(self, tmp_path: Path) -> None:
        manager = EnvManager()
        assert manager.get_env("NONEXISTENT_KEY", "fallback") == "fallback"

    def test_get_env_none(self, tmp_path: Path) -> None:
        manager = EnvManager()
        assert manager.get_env("NONEXISTENT_KEY") is None

    def test_set_env(self, tmp_path: Path) -> None:
        manager = EnvManager()
        manager.set_env("TEST_SET_KEY", "set_val")
        assert os.getenv("TEST_SET_KEY") == "set_val"
        del os.environ["TEST_SET_KEY"]

    def test_set_env_persist(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env.local"
        manager = EnvManager(env_file=env_file)
        manager.set_env("TEST_PERSIST_KEY", "persist_val", persist=True)

        assert env_file.exists()
        content = env_file.read_text(encoding="utf-8")
        assert "TEST_PERSIST_KEY=persist_val" in content

    def test_save_env_file(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env.local"
        manager = EnvManager(env_file=env_file)

        env_vars = {"KEY1": "val1", "KEY2": "val2"}
        manager.save_env_file(env_vars)

        content = env_file.read_text(encoding="utf-8")
        assert "KEY1=val1" in content
        assert "KEY2=val2" in content

    def test_save_env_file_preserves_existing(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env.local"
        env_file.write_text("EXISTING_KEY=existing_val\n", encoding="utf-8")

        manager = EnvManager(env_file=env_file)
        manager.save_env_file({"NEW_KEY": "new_val"})

        content = env_file.read_text(encoding="utf-8")
        assert "EXISTING_KEY=existing_val" in content
        assert "NEW_KEY=new_val" in content

    def test_generate_env_template(self, tmp_path: Path) -> None:
        manager = EnvManager()
        template = manager.generate_env_template()

        assert "NANOBOT_LLM_API_KEY" in template
        assert "NANOBOT_FEISHU_APP_ID" in template
