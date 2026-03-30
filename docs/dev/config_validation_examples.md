# 配置验证示例文档

## 概述

本文档提供 Nanobot Runner 项目中配置验证的完整示例，包括配置Schema定义、验证逻辑和错误处理。

## 配置验证架构

```
┌─────────────────────────────────────────────────────────────┐
│                    配置验证流程                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   加载配置    │ -> │   Schema验证  │ -> │   业务验证    │  │
│  │  (JSON文件)   │    │  (类型/必填)  │    │  (逻辑检查)   │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│         │                   │                   │          │
│         ▼                   ▼                   ▼          │
│  ┌──────────────────────────────────────────────────────┐ │
│  │                      错误处理                          │ │
│  │  • 格式错误 -> 使用默认配置 + 警告                      │ │
│  │  • 验证失败 -> 详细错误信息 + 修复建议                  │ │
│  │  • 业务冲突 -> 降级处理 + 日志记录                      │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 基础配置验证

### 1. 配置Schema定义

```python
# src/core/config_schema.py
"""配置Schema定义模块

定义所有配置项的数据结构和验证规则。
"""

from dataclasses import dataclass, field, fields
from typing import Optional, Any, get_type_hints
from enum import Enum
import json


class LogLevel(Enum):
    """日志级别枚举"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class PartitionStrategy(Enum):
    """数据分区策略"""
    YEAR = "year"
    QUARTER = "quarter"
    MONTH = "month"


class CompressionType(Enum):
    """压缩类型"""
    SNAPPY = "snappy"
    ZSTD = "zstd"
    GZIP = "gzip"
    NONE = "none"


@dataclass
class FeishuConfig:
    """飞书配置Schema
    
    Attributes:
        app_id: 飞书应用ID
        app_secret: 飞书应用密钥
        receive_id: 接收者ID
        receive_id_type: 接收者ID类型
        webhook_url: Webhook地址（兼容旧版）
    """
    app_id: Optional[str] = None
    app_secret: Optional[str] = None
    receive_id: Optional[str] = None
    receive_id_type: str = "user_id"
    webhook_url: Optional[str] = None
    
    # 有效的接收者ID类型
    VALID_RECEIVE_ID_TYPES = ["user_id", "open_id", "union_id", "email", "chat_id"]
    
    def validate(self) -> tuple[bool, list[str]]:
        """验证飞书配置
        
        Returns:
            tuple[bool, list[str]]: (是否有效, 错误信息列表)
        """
        errors = []
        
        # 验证app_id和app_secret的配对关系
        if self.app_id and not self.app_secret:
            errors.append("配置feishu_app_id时，必须同时配置feishu_app_secret")
        
        if self.app_secret and not self.app_id:
            errors.append("配置feishu_app_secret时，必须同时配置feishu_app_id")
        
        # 验证receive_id_type
        if self.receive_id_type not in self.VALID_RECEIVE_ID_TYPES:
            errors.append(
                f"feishu_receive_id_type必须是以下之一: {self.VALID_RECEIVE_ID_TYPES}"
            )
        
        # 验证webhook_url格式（如果配置）
        if self.webhook_url:
            if not self.webhook_url.startswith(("http://", "https://")):
                errors.append("feishu_webhook必须是有效的URL格式")
        
        return len(errors) == 0, errors


@dataclass
class DataConfig:
    """数据配置Schema
    
    Attributes:
        data_dir: 数据目录路径
        index_file: 索引文件名
        partition_strategy: 分区策略
        compression: 压缩类型
    """
    data_dir: str = "~/.nanobot-runner/data"
    index_file: str = "index.json"
    partition_strategy: str = "year"
    compression: str = "snappy"
    
    def validate(self) -> tuple[bool, list[str]]:
        """验证数据配置"""
        errors = []
        
        # 验证分区策略
        valid_strategies = ["year", "quarter", "month"]
        if self.partition_strategy not in valid_strategies:
            errors.append(f"partition_strategy必须是以下之一: {valid_strategies}")
        
        # 验证压缩类型
        valid_compressions = ["snappy", "zstd", "gzip", "none"]
        if self.compression not in valid_compressions:
            errors.append(f"compression必须是以下之一: {valid_compressions}")
        
        # 验证数据目录路径格式
        if not self.data_dir:
            errors.append("data_dir不能为空")
        
        return len(errors) == 0, errors


@dataclass
class LoggingConfig:
    """日志配置Schema
    
    Attributes:
        level: 日志级别
        format: 日志格式
        file: 日志文件路径（可选）
    """
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: Optional[str] = None
    
    VALID_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR"]
    
    def validate(self) -> tuple[bool, list[str]]:
        """验证日志配置"""
        errors = []
        
        if self.level not in self.VALID_LEVELS:
            errors.append(f"log_level必须是以下之一: {self.VALID_LEVELS}")
        
        return len(errors) == 0, errors


@dataclass
class AppConfig:
    """应用配置Schema
    
    这是根配置对象，包含所有子配置。
    """
    version: str = "0.4.1"
    feishu: FeishuConfig = field(default_factory=FeishuConfig)
    data: DataConfig = field(default_factory=DataConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    auto_push_feishu: bool = False
    debug_mode: bool = False
    
    # 必填字段列表
    REQUIRED_FIELDS = ["version"]
    
    @classmethod
    def from_dict(cls, config: dict[str, Any]) -> "AppConfig":
        """从字典创建配置对象
        
        Args:
            config: 配置字典
            
        Returns:
            AppConfig: 配置对象
        """
        return cls(
            version=config.get("version", "0.4.1"),
            feishu=FeishuConfig(
                app_id=config.get("feishu_app_id"),
                app_secret=config.get("feishu_app_secret"),
                receive_id=config.get("feishu_receive_id"),
                receive_id_type=config.get("feishu_receive_id_type", "user_id"),
                webhook_url=config.get("feishu_webhook"),
            ),
            data=DataConfig(
                data_dir=config.get("data_dir", "~/.nanobot-runner/data"),
                index_file=config.get("index_file", "index.json"),
                partition_strategy=config.get("partition_strategy", "year"),
                compression=config.get("compression", "snappy"),
            ),
            logging=LoggingConfig(
                level=config.get("log_level", "INFO"),
                format=config.get("log_format", LoggingConfig.format),
                file=config.get("log_file"),
            ),
            auto_push_feishu=config.get("auto_push_feishu", False),
            debug_mode=config.get("debug_mode", False),
        )
    
    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "version": self.version,
            "data_dir": self.data.data_dir,
            "index_file": self.data.index_file,
            "partition_strategy": self.data.partition_strategy,
            "compression": self.data.compression,
            "auto_push_feishu": self.auto_push_feishu,
            "feishu_app_id": self.feishu.app_id,
            "feishu_app_secret": self.feishu.app_secret,
            "feishu_receive_id": self.feishu.receive_id,
            "feishu_receive_id_type": self.feishu.receive_id_type,
            "feishu_webhook": self.feishu.webhook_url,
            "log_level": self.logging.level,
            "log_format": self.logging.format,
            "log_file": self.logging.file,
            "debug_mode": self.debug_mode,
        }
    
    def validate(self) -> tuple[bool, list[str]]:
        """验证完整配置
        
        Returns:
            tuple[bool, list[str]]: (是否有效, 错误信息列表)
        """
        errors = []
        
        # 验证必填字段
        for field_name in self.REQUIRED_FIELDS:
            if not getattr(self, field_name):
                errors.append(f"缺少必填字段: {field_name}")
        
        # 验证版本格式（语义化版本）
        if self.version:
            try:
                parts = self.version.split(".")
                if len(parts) != 3:
                    errors.append("version必须是语义化版本格式 (如: 0.4.1)")
                for part in parts:
                    if not part.isdigit():
                        errors.append("version格式无效，必须包含数字")
                        break
            except Exception:
                errors.append("version格式无效")
        
        # 验证子配置
        feishu_valid, feishu_errors = self.feishu.validate()
        if not feishu_valid:
            errors.extend([f"飞书配置: {e}" for e in feishu_errors])
        
        data_valid, data_errors = self.data.validate()
        if not data_valid:
            errors.extend([f"数据配置: {e}" for e in data_errors])
        
        logging_valid, logging_errors = self.logging.validate()
        if not logging_valid:
            errors.extend([f"日志配置: {e}" for e in logging_errors])
        
        return len(errors) == 0, errors
```

### 2. 配置验证器

```python
# src/core/config_validator.py
"""配置验证器模块

提供配置验证的高级功能，包括环境变量验证、路径验证等。
"""

import os
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

from .config_schema import AppConfig


class ConfigValidator:
    """配置验证器
    
    提供额外的配置验证逻辑，超越Schema的基础类型检查。
    """
    
    @staticmethod
    def validate_path(path: str, must_exist: bool = False) -> tuple[bool, str]:
        """验证路径配置
        
        Args:
            path: 路径字符串
            must_exist: 是否必须已存在
            
        Returns:
            tuple[bool, str]: (是否有效, 错误信息)
        """
        try:
            p = Path(path).expanduser()
            
            if must_exist and not p.exists():
                return False, f"路径不存在: {path}"
            
            # 检查路径是否可写（对于目录）
            if p.exists() and not os.access(p, os.W_OK):
                return False, f"路径不可写: {path}"
            
            return True, ""
        except Exception as e:
            return False, f"路径格式无效: {e}"
    
    @staticmethod
    def validate_url(url: str, allowed_schemes: Optional[list[str]] = None) -> tuple[bool, str]:
        """验证URL配置
        
        Args:
            url: URL字符串
            allowed_schemes: 允许的协议列表
            
        Returns:
            tuple[bool, str]: (是否有效, 错误信息)
        """
        try:
            result = urlparse(url)
            
            if not result.scheme:
                return False, "URL缺少协议（如https://）"
            
            if not result.netloc:
                return False, "URL缺少主机名"
            
            if allowed_schemes and result.scheme not in allowed_schemes:
                return False, f"URL协议必须是以下之一: {allowed_schemes}"
            
            return True, ""
        except Exception as e:
            return False, f"URL格式无效: {e}"
    
    @staticmethod
    def validate_environment() -> tuple[bool, list[str]]:
        """验证环境配置
        
        检查必要的环境变量和系统环境。
        
        Returns:
            tuple[bool, list[str]]: (是否有效, 警告信息列表)
        """
        warnings = []
        
        # 检查Python版本
        import sys
        if sys.version_info < (3, 11):
            warnings.append(f"Python版本建议>=3.11，当前: {sys.version_info.major}.{sys.version_info.minor}")
        
        # 检查必要的环境变量（如果有）
        # if not os.getenv("SOME_REQUIRED_VAR"):
        #     warnings.append("缺少环境变量: SOME_REQUIRED_VAR")
        
        return len(warnings) == 0, warnings
    
    @classmethod
    def validate_full_config(cls, config: AppConfig) -> tuple[bool, list[str]]:
        """执行完整配置验证
        
        包括Schema验证和业务逻辑验证。
        
        Args:
            config: 配置对象
            
        Returns:
            tuple[bool, list[str]]: (是否有效, 错误信息列表)
        """
        errors = []
        
        # 1. Schema验证
        schema_valid, schema_errors = config.validate()
        if not schema_valid:
            errors.extend(schema_errors)
        
        # 2. 路径验证
        data_dir_valid, data_dir_error = cls.validate_path(config.data.data_dir)
        if not data_dir_valid:
            errors.append(f"数据目录: {data_dir_error}")
        
        # 3. Webhook URL验证（如果配置）
        if config.feishu.webhook_url:
            url_valid, url_error = cls.validate_url(
                config.feishu.webhook_url, 
                allowed_schemes=["http", "https"]
            )
            if not url_valid:
                errors.append(f"飞书Webhook: {url_error}")
        
        # 4. 环境验证
        env_valid, env_warnings = cls.validate_environment()
        if env_warnings:
            # 环境警告不视为错误，但记录
            pass
        
        return len(errors) == 0, errors
```

### 3. 配置管理器集成验证

```python
# src/core/config_manager.py（验证相关部分）
"""配置管理器 - 验证集成示例"""

import json
import logging
from pathlib import Path
from typing import Optional, Any

from .config_schema import AppConfig
from .config_validator import ConfigValidator

logger = logging.getLogger(__name__)


class ConfigManager:
    """配置管理器"""
    
    def __init__(
        self,
        config_path: Optional[Path] = None,
        auto_create: bool = True,
        validate: bool = True
    ):
        self.config_path = config_path or Path.home() / ".nanobot-runner" / "config.json"
        self._config: Optional[AppConfig] = None
        self._validate = validate
        
        # 加载配置
        if self.config_path.exists():
            self._load_config()
        elif auto_create:
            self._create_default_config()
    
    def _load_config(self):
        """加载并验证配置"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config_dict = json.load(f)
            
            # 创建配置对象
            self._config = AppConfig.from_dict(config_dict)
            
            # 验证配置
            if self._validate:
                self._validate_config()
            
            logger.info(f"配置加载成功: {self.config_path}")
            
        except json.JSONDecodeError as e:
            logger.error(f"配置文件格式错误: {e}")
            self._handle_corrupted_config()
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            self._create_default_config()
    
    def _validate_config(self):
        """验证配置并处理错误"""
        if self._config is None:
            return
        
        # 执行完整验证
        valid, errors = ConfigValidator.validate_full_config(self._config)
        
        if not valid:
            logger.warning("配置验证失败:")
            for error in errors:
                logger.warning(f"  - {error}")
            
            # 根据错误严重程度处理
            critical_errors = [e for e in errors if "必填" in e]
            if critical_errors:
                logger.error("存在严重配置错误，使用默认配置")
                self._create_default_config()
            else:
                logger.warning("配置存在非严重错误，继续使用")
    
    def _handle_corrupted_config(self):
        """处理损坏的配置文件"""
        if self.config_path.exists():
            # 备份损坏的配置
            backup_path = self.config_path.with_suffix('.json.bak')
            try:
                import shutil
                shutil.move(self.config_path, backup_path)
                logger.warning(f"损坏的配置已备份: {backup_path}")
            except Exception as e:
                logger.error(f"备份配置失败: {e}")
        
        # 创建默认配置
        self._create_default_config()
    
    def _create_default_config(self):
        """创建默认配置"""
        self._config = AppConfig()
        self.save_config()
        logger.info(f"已创建默认配置: {self.config_path}")
    
    def save_config(self):
        """保存配置到文件"""
        if self._config is None:
            return
        
        try:
            # 确保目录存在
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 保存前验证
            if self._validate:
                valid, errors = self._config.validate()
                if not valid:
                    logger.warning(f"保存的配置存在验证问题: {errors}")
            
            config_dict = self._config.to_dict()
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"配置已保存: {self.config_path}")
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
    
    def validate(self) -> tuple[bool, list[str]]:
        """验证当前配置"""
        if self._config is None:
            return False, ["配置未加载"]
        return ConfigValidator.validate_full_config(self._config)
```

## 配置验证使用示例

### 示例1: 基本配置验证

```python
from src.core.config_schema import AppConfig
from src.core.config_validator import ConfigValidator

# 创建配置对象
config = AppConfig.from_dict({
    "version": "0.4.1",
    "data_dir": "~/.nanobot-runner/data",
    "feishu_app_id": "cli_xxx",
    "feishu_app_secret": "secret_xxx",
    "log_level": "INFO"
})

# 验证配置
valid, errors = ConfigValidator.validate_full_config(config)

if valid:
    print("✓ 配置验证通过")
else:
    print("✗ 配置验证失败:")
    for error in errors:
        print(f"  - {error}")
```

### 示例2: 配置错误处理

```python
from src.core.config_manager import ConfigManager

# 尝试加载配置（自动验证）
config_manager = ConfigManager()

# 手动验证
valid, errors = config_manager.validate()

if not valid:
    print("配置存在问题:")
    for error in errors:
        print(f"  - {error}")
    
    # 根据错误类型处理
    critical = [e for e in errors if "必填" in e or "不存在" in e]
    if critical:
        print("存在严重错误，请修复后重试")
    else:
        print("存在警告，但配置可用")
```

### 示例3: 环境变量验证

```python
import os
from src.core.config_validator import ConfigValidator

# 设置环境变量
os.environ["NANOBOT_RUNNER_FEISHU_APP_ID"] = "cli_xxx"
os.environ["NANOBOT_RUNNER_LOG_LEVEL"] = "DEBUG"

# 验证环境
valid, warnings = ConfigValidator.validate_environment()

if warnings:
    print("环境警告:")
    for warning in warnings:
        print(f"  - {warning}")
```

## 配置验证检查清单

- [ ] Schema定义完整（类型、默认值、必填项）
- [ ] 验证逻辑覆盖所有业务规则
- [ ] 错误信息清晰明确
- [ ] 损坏配置有备份机制
- [ ] 默认值合理且可用
- [ ] 环境变量验证完整
- [ ] 路径验证处理expanduser

---

*文档版本: 1.0*  
*适用版本: v0.4.1+*  
*最后更新: 2026-03-29*
