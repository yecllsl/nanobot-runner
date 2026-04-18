from pathlib import Path

from src.core.verify_manager import VerifyManager


class TestVerifyManager:
    """数据完整性校验管理器单元测试"""

    def test_verify_files_all_exist(self, tmp_path: Path) -> None:
        f1 = tmp_path / "test1.txt"
        f2 = tmp_path / "test2.txt"
        f1.write_text("content1", encoding="utf-8")
        f2.write_text("content2", encoding="utf-8")

        manager = VerifyManager()
        report = manager.verify_files([f1, f2])

        assert report.success is True
        assert report.checked_files == 2

    def test_verify_files_missing(self, tmp_path: Path) -> None:
        f1 = tmp_path / "exists.txt"
        f2 = tmp_path / "missing.txt"
        f1.write_text("content", encoding="utf-8")

        manager = VerifyManager()
        report = manager.verify_files([f1, f2])

        assert report.success is False
        assert report.checked_files == 1
        assert any("不存在" in e for e in report.errors)

    def test_verify_config_valid(self) -> None:
        config = {
            "version": "0.9.4",
            "data_dir": "/tmp/data",
            "auto_push_feishu": False,
        }

        manager = VerifyManager()
        report = manager.verify_config(config)

        assert report.success is True

    def test_verify_config_missing_required(self) -> None:
        config = {"auto_push_feishu": False}

        manager = VerifyManager()
        report = manager.verify_config(config)

        assert report.success is False
        assert any("version" in e for e in report.errors)
        assert any("data_dir" in e for e in report.errors)

    def test_verify_config_empty_value(self) -> None:
        config = {"version": "", "data_dir": ""}

        manager = VerifyManager()
        report = manager.verify_config(config)

        assert report.success is False

    def test_verify_config_bad_version_format(self) -> None:
        config = {"version": "abc", "data_dir": "/tmp/data"}

        manager = VerifyManager()
        report = manager.verify_config(config)

        assert report.success is False
        assert any("版本号格式" in e for e in report.errors)

    def test_generate_report_files_only(self, tmp_path: Path) -> None:
        f1 = tmp_path / "test.txt"
        f1.write_text("content", encoding="utf-8")

        manager = VerifyManager()
        report = manager.generate_report(files=[f1])

        assert report.checked_files == 1

    def test_generate_report_config_only(self) -> None:
        config = {"version": "0.9.4", "data_dir": "/tmp/data"}

        manager = VerifyManager()
        report = manager.generate_report(config=config)

        assert report.success is True

    def test_generate_report_both(self, tmp_path: Path) -> None:
        f1 = tmp_path / "test.txt"
        f1.write_text("content", encoding="utf-8")
        config = {"version": "0.9.4", "data_dir": "/tmp/data"}

        manager = VerifyManager()
        report = manager.generate_report(files=[f1], config=config)

        assert report.success is True
        assert report.checked_files == 2

    def test_compute_file_hash(self, tmp_path: Path) -> None:
        f1 = tmp_path / "test.txt"
        f1.write_text("hello world", encoding="utf-8")

        manager = VerifyManager()
        hash1 = manager.compute_file_hash(f1)
        assert len(hash1) == 64

        hash2 = manager.compute_file_hash(f1)
        assert hash1 == hash2

    def test_verify_json_file_valid(self, tmp_path: Path) -> None:
        f1 = tmp_path / "test.json"
        f1.write_text('{"key": "value"}', encoding="utf-8")

        manager = VerifyManager()
        errors = manager._verify_json_file(f1)
        assert len(errors) == 0

    def test_verify_json_file_invalid(self, tmp_path: Path) -> None:
        f1 = tmp_path / "test.json"
        f1.write_text("invalid json{{{", encoding="utf-8")

        manager = VerifyManager()
        errors = manager._verify_json_file(f1)
        assert len(errors) > 0
