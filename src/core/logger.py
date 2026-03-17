# 日志系统模块
# 支持结构化日志输出、JSON格式、文件轮转

import json
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional


class JsonFormatter(logging.Formatter):
    """JSON格式日志格式化器"""

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        if hasattr(record, "extra_data") and record.extra_data:
            log_data["data"] = record.extra_data

        return json.dumps(log_data, ensure_ascii=False)


class TextFormatter(logging.Formatter):
    """文本格式日志格式化器"""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")
        base_msg = f"[{timestamp}] [{record.levelname:8}] [{record.name}] {record.getMessage()}"

        if record.exc_info:
            base_msg += f"\n{self.formatException(record.exc_info)}"

        return base_msg


class LogConfig:
    """日志配置类"""

    def __init__(
        self,
        log_level: str = "INFO",
        log_format: str = "text",
        log_file: Optional[Path] = None,
        max_bytes: int = 10 * 1024 * 1024,
        backup_count: int = 5,
        console_output: bool = True,
    ):
        self.log_level = getattr(logging, log_level.upper(), logging.INFO)
        self.log_format = log_format.lower()
        self.log_file = log_file
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self.console_output = console_output

    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> "LogConfig":
        """从字典创建配置"""
        log_file = config.get("log_file")
        return cls(
            log_level=config.get("log_level", "INFO"),
            log_format=config.get("log_format", "text"),
            log_file=Path(log_file) if log_file else None,
            max_bytes=config.get("max_bytes", 10 * 1024 * 1024),
            backup_count=config.get("backup_count", 5),
            console_output=config.get("console_output", True),
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "log_level": logging.getLevelName(self.log_level),
            "log_format": self.log_format,
            "log_file": str(self.log_file) if self.log_file else None,
            "max_bytes": self.max_bytes,
            "backup_count": self.backup_count,
            "console_output": self.console_output,
        }


_loggers: Dict[str, logging.Logger] = {}
_default_config: Optional[LogConfig] = None


def setup_logging(config: Optional[LogConfig] = None) -> None:
    """配置全局日志系统"""
    global _default_config
    _default_config = config or LogConfig()


def get_logger(name: str, config: Optional[LogConfig] = None) -> logging.Logger:
    """获取或创建日志记录器"""
    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    logger.handlers.clear()

    effective_config = config or _default_config or LogConfig()

    formatter: logging.Formatter
    if effective_config.log_format == "json":
        formatter = JsonFormatter()
    else:
        formatter = TextFormatter()

    if effective_config.console_output:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(effective_config.log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    if effective_config.log_file:
        effective_config.log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            effective_config.log_file,
            maxBytes=effective_config.max_bytes,
            backupCount=effective_config.backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(effective_config.log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    _loggers[name] = logger
    return logger


def log_with_data(
    logger: logging.Logger,
    level: int,
    message: str,
    data: Optional[Dict[str, Any]] = None,
) -> None:
    """记录带额外数据的日志"""
    record = logger.makeRecord(logger.name, level, "", 0, message, (), None)
    record.extra_data = data
    logger.handle(record)


_default_logger: Optional[logging.Logger] = None


def get_default_logger() -> logging.Logger:
    """获取默认日志记录器"""
    global _default_logger
    if _default_logger is None:
        _default_logger = get_logger("nanobot_runner")
    return _default_logger
