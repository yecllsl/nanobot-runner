# 配置 Schema 验证模块
# 提供配置数据结构定义和验证机制

from dataclasses import dataclass, field
from typing import Optional, Type, Union


@dataclass
class AppConfig:
    """应用配置 Schema 数据类

    定义配置文件的结构和验证规则，确保配置项的类型正确性和完整性。

    Attributes:
        version: 配置文件版本号，格式为 x.y.z
        data_dir: 数据目录路径
        auto_push_feishu: 是否自动推送到飞书
        feishu_app_id: 飞书应用 App ID
        feishu_app_secret: 飞书应用 App Secret
        feishu_receive_id: 飞书接收者 ID
        feishu_receive_id_type: 飞书接收者 ID 类型
        feishu_webhook: 飞书 Webhook URL（已废弃，保留向后兼容）
    """

    version: str
    data_dir: str
    auto_push_feishu: bool = False
    feishu_app_id: Optional[str] = None
    feishu_app_secret: Optional[str] = None
    feishu_receive_id: Optional[str] = None
    feishu_receive_id_type: str = "user_id"
    feishu_webhook: Optional[str] = None

    # 必填字段列表
    REQUIRED_FIELDS = ["version", "data_dir"]

    # 字段类型映射
    FIELD_TYPES: dict[str, type | tuple[type, ...]] = {
        "version": str,
        "data_dir": str,
        "auto_push_feishu": bool,
        "feishu_app_id": (str, type(None)),
        "feishu_app_secret": (str, type(None)),
        "feishu_receive_id": (str, type(None)),
        "feishu_receive_id_type": str,
        "feishu_webhook": (str, type(None)),
    }

    @classmethod
    def validate(cls, config: dict) -> tuple[bool, list[str]]:
        """验证配置是否符合 Schema

        检查必填字段是否存在，字段类型是否正确。

        Args:
            config: 配置字典

        Returns:
            tuple[bool, list[str]]: (是否验证通过，错误消息列表)

        Examples:
            >>> config = {"version": "0.1.0", "data_dir": "/data"}
            >>> is_valid, errors = AppConfig.validate(config)
            >>> is_valid
            True
            >>> errors
            []
        """
        errors = []

        # 检查必填字段
        for field_name in cls.REQUIRED_FIELDS:
            if field_name not in config:
                errors.append(f"缺少必填字段：{field_name}")
            elif config[field_name] is None or config[field_name] == "":
                errors.append(f"必填字段不能为空：{field_name}")

        # 检查字段类型
        for field_name, value in config.items():
            if field_name in cls.FIELD_TYPES:
                expected_type = cls.FIELD_TYPES[field_name]
                # 处理 Union types (e.g., Optional[str] = str | None)
                if isinstance(expected_type, tuple):
                    # 检查值是否为元组中的任一类型
                    if not any(isinstance(value, t) for t in expected_type):
                        type_names = " | ".join(
                            t.__name__ if hasattr(t, "__name__") else str(t)  # type: ignore[arg-type]
                            for t in expected_type
                        )
                        errors.append(
                            f"字段 '{field_name}' 类型错误，期望 {type_names}，实际 {type(value).__name__}"
                        )
                elif not isinstance(value, expected_type):
                    errors.append(
                        f"字段 '{field_name}' 类型错误，期望 {expected_type.__name__}，实际 {type(value).__name__}"
                    )

        # 检查版本号格式
        if "version" in config and config["version"]:
            version = config["version"]
            if not cls._is_valid_version(version):
                errors.append(f"版本号格式错误：'{version}'，应为 x.y.z 格式")

        # 检查 feishu_receive_id_type 的枚举值
        if "feishu_receive_id_type" in config and config["feishu_receive_id_type"]:
            valid_types = ["user_id", "open_id", "union_id"]
            if config["feishu_receive_id_type"] not in valid_types:
                errors.append(
                    f"feishu_receive_id_type 值错误：'{config['feishu_receive_id_type']}'，"
                    f"应为 {valid_types} 之一"
                )

        return len(errors) == 0, errors

    @staticmethod
    def _is_valid_version(version: str) -> bool:
        """检查版本号格式是否有效

        Args:
            version: 版本号字符串

        Returns:
            bool: 版本号格式是否有效
        """
        import re

        pattern = r"^\d+\.\d+\.\d+$"
        return bool(re.match(pattern, version))

    @classmethod
    def from_dict(cls, config: dict) -> "AppConfig":
        """从字典创建 AppConfig 实例

        Args:
            config: 配置字典

        Returns:
            AppConfig: 配置实例

        Raises:
            ValueError: 配置验证失败时抛出
        """
        is_valid, errors = cls.validate(config)
        if not is_valid:
            error_msg = "配置验证失败:\n" + "\n".join(f"  - {e}" for e in errors)
            raise ValueError(error_msg)

        # 提取已知字段，过滤未知字段
        known_fields = {k: v for k, v in config.items() if k in cls.FIELD_TYPES}

        return cls(**known_fields)

    def to_dict(self) -> dict:
        """将配置实例转换为字典

        Returns:
            dict: 配置字典
        """
        return {
            "version": self.version,
            "data_dir": self.data_dir,
            "auto_push_feishu": self.auto_push_feishu,
            "feishu_app_id": self.feishu_app_id,
            "feishu_app_secret": self.feishu_app_secret,
            "feishu_receive_id": self.feishu_receive_id,
            "feishu_receive_id_type": self.feishu_receive_id_type,
            "feishu_webhook": self.feishu_webhook,
        }

    def __post_init__(self):
        """数据类初始化后验证

        确保创建的实例符合 Schema 要求
        """
        is_valid, errors = self.validate(self.to_dict())
        if not is_valid:
            error_msg = "配置验证失败:\n" + "\n".join(f"  - {e}" for e in errors)
            raise ValueError(error_msg)
