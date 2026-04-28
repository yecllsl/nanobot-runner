# 日志系统单元测试
# 测试日志模块的功能

import json
import logging
from pathlib import Path

from src.core.base.logger import (
    JsonFormatter,
    LogConfig,
    TextFormatter,
    get_default_logger,
    get_logger,
    log_with_data,
    setup_logging,
)


class TestLogConfig:
    """测试日志配置类"""

    def test_default_config(self):
        """测试默认配置"""
        config = LogConfig()
        assert config.log_level == logging.INFO
        assert config.log_format == "text"
        assert config.log_file is None
        assert config.max_bytes == 10 * 1024 * 1024
        assert config.backup_count == 5
        assert config.console_output is True

    def test_custom_config(self):
        """测试自定义配置"""
        config = LogConfig(
            log_level="DEBUG",
            log_format="json",
            log_file=Path("/tmp/test.log"),
            max_bytes=1024,
            backup_count=3,
            console_output=False,
        )
        assert config.log_level == logging.DEBUG
        assert config.log_format == "json"
        assert config.log_file == Path("/tmp/test.log")
        assert config.max_bytes == 1024
        assert config.backup_count == 3
        assert config.console_output is False

    def test_from_dict(self):
        """测试从字典创建配置"""
        config_dict = {
            "log_level": "WARNING",
            "log_format": "json",
            "log_file": "/var/log/app.log",
            "max_bytes": 2048,
            "backup_count": 10,
            "console_output": False,
        }
        config = LogConfig.from_dict(config_dict)
        assert config.log_level == logging.WARNING
        assert config.log_format == "json"
        assert config.log_file == Path("/var/log/app.log")
        assert config.max_bytes == 2048
        assert config.backup_count == 10
        assert config.console_output is False

    def test_to_dict(self):
        """测试转换为字典"""
        config = LogConfig(
            log_level="ERROR",
            log_format="json",
            log_file=Path("/tmp/test.log"),
        )
        result = config.to_dict()
        assert result["log_level"] == "ERROR"
        assert result["log_format"] == "json"
        assert "test.log" in result["log_file"]
        assert result["max_bytes"] == 10 * 1024 * 1024
        assert result["backup_count"] == 5
        assert result["console_output"] is True


class TestJsonFormatter:
    """测试JSON格式化器"""

    def test_format_basic(self):
        """测试基本格式化"""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="test message",
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)
        data = json.loads(result)
        assert data["level"] == "INFO"
        assert data["logger"] == "test"
        assert data["message"] == "test message"
        assert data["module"] == "test"
        assert data["line"] == 10

    def test_format_with_exception(self):
        """测试带异常的格式化"""
        formatter = JsonFormatter()
        try:
            raise ValueError("test error")
        except ValueError:
            import sys

            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=20,
            msg="error occurred",
            args=(),
            exc_info=exc_info,
        )
        result = formatter.format(record)
        data = json.loads(result)
        assert data["level"] == "ERROR"
        assert "exception" in data
        assert "ValueError: test error" in data["exception"]

    def test_format_with_extra_data(self):
        """测试带额外数据的格式化"""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=30,
            msg="test message",
            args=(),
            exc_info=None,
        )
        record.extra_data = {"user_id": 123, "action": "login"}
        result = formatter.format(record)
        data = json.loads(result)
        assert data["data"]["user_id"] == 123
        assert data["data"]["action"] == "login"


class TestTextFormatter:
    """测试文本格式化器"""

    def test_format_basic(self):
        """测试基本格式化"""
        formatter = TextFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.WARNING,
            pathname="test.py",
            lineno=10,
            msg="warning message",
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)
        assert "WARNING" in result
        assert "[test.logger]" in result
        assert "warning message" in result

    def test_format_with_exception(self):
        """测试带异常的格式化"""
        formatter = TextFormatter()
        try:
            raise RuntimeError("test runtime error")
        except RuntimeError:
            import sys

            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=20,
            msg="error occurred",
            args=(),
            exc_info=exc_info,
        )
        result = formatter.format(record)
        assert "RuntimeError: test runtime error" in result


class TestGetLogger:
    """测试获取日志记录器"""

    def test_get_logger_basic(self):
        """测试获取基本日志记录器"""
        logger = get_logger("test_basic")
        assert logger is not None
        assert logger.name == "test_basic"
        assert logger.level == logging.DEBUG

    def test_get_logger_with_config(self, tmp_path):
        """测试使用配置获取日志记录器"""
        log_file = tmp_path / "test.log"
        config = LogConfig(
            log_level="DEBUG",
            log_format="json",
            log_file=log_file,
            console_output=False,
        )
        logger = get_logger("test_config", config=config)
        logger.info("test message")

        assert log_file.exists()
        content = log_file.read_text(encoding="utf-8")
        data = json.loads(content.strip())
        assert data["message"] == "test message"

    def test_get_logger_text_format(self, tmp_path):
        """测试文本格式日志"""
        log_file = tmp_path / "test_text.log"
        config = LogConfig(
            log_level="INFO",
            log_format="text",
            log_file=log_file,
            console_output=False,
        )
        logger = get_logger("test_text", config=config)
        logger.info("text message")

        assert log_file.exists()
        content = log_file.read_text(encoding="utf-8")
        assert "INFO" in content
        assert "text message" in content

    def test_get_logger_singleton(self):
        """测试同一名称返回同一实例"""
        logger1 = get_logger("singleton_test")
        logger2 = get_logger("singleton_test")
        assert logger1 is logger2


class TestSetupLogging:
    """测试全局日志配置"""

    def test_setup_logging_default(self):
        """测试默认全局配置"""
        setup_logging()
        logger = get_logger("global_test")
        assert logger is not None

    def test_setup_logging_custom(self):
        """测试自定义全局配置"""
        config = LogConfig(log_level="DEBUG", log_format="json")
        setup_logging(config)
        logger = get_logger("global_custom_test")
        assert logger is not None


class TestLogWithData:
    """测试带数据的日志记录"""

    def test_log_with_data(self):
        """测试记录带额外数据的日志"""
        import io

        config = LogConfig(
            log_level="DEBUG",
            log_format="json",
            console_output=True,
        )
        logger = get_logger("data_test", config=config)

        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(JsonFormatter())
        logger.handlers.clear()
        logger.addHandler(handler)

        log_with_data(
            logger, logging.INFO, "user action", {"user_id": 456, "action": "click"}
        )

        output = stream.getvalue()
        data = json.loads(output.strip())
        assert data["message"] == "user action"
        assert data["data"]["user_id"] == 456
        assert data["data"]["action"] == "click"


class TestGetDefaultLogger:
    """测试获取默认日志记录器"""

    def test_get_default_logger(self):
        """测试获取默认日志记录器"""
        logger = get_default_logger()
        assert logger is not None
        assert logger.name == "nanobot_runner"

    def test_get_default_logger_singleton(self):
        """测试默认日志记录器单例"""
        logger1 = get_default_logger()
        logger2 = get_default_logger()
        assert logger1 is logger2


class TestLogFileRotation:
    """测试日志文件轮转"""

    def test_file_rotation_config(self, tmp_path):
        """测试文件轮转配置"""
        log_file = tmp_path / "rotation.log"
        config = LogConfig(
            log_level="DEBUG",
            log_file=log_file,
            max_bytes=100,
            backup_count=2,
            console_output=False,
        )
        logger = get_logger("rotation_test", config=config)

        for i in range(20):
            logger.info(f"test message {i} " + "x" * 10)

        assert log_file.exists()
        backup1 = tmp_path / "rotation.log.1"
        assert backup1.exists() or log_file.stat().st_size < 500
