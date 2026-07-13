# 配置 Schema 验证模块
# 提供配置数据结构定义和验证机制

from dataclasses import asdict, dataclass
from typing import ClassVar


@dataclass
class AppConfig:
    """应用配置 Schema 数据类（v0.32.0 精简版）

    仅包含 Runner 专有字段。nanobot 相关配置（providers/agents/channels等）
    由 nanobot_config.json 管理，不在本 Schema 中验证。

    Attributes:
        version: 配置文件版本号，格式为 x.y.z
        data_dir: 数据目录路径
        timezone: 时区，用于训练数据时间显示、VDOT 计算等
        auto_push_feishu: 是否自动推送到飞书
        user_id: 用户标识，用于数据隔离
    """

    version: str
    data_dir: str
    timezone: str = "Asia/Shanghai"
    auto_push_feishu: bool = False
    user_id: str = "default_user"

    REQUIRED_FIELDS: ClassVar[list[str]] = ["version", "data_dir"]

    FIELD_TYPES: ClassVar[dict[str, type | tuple[type, ...]]] = {
        "version": str,
        "data_dir": str,
        "timezone": str,
        "auto_push_feishu": bool,
        "user_id": str,
    }

    @classmethod
    def validate(cls, config: dict) -> tuple[bool, list[str]]:
        """验证配置是否符合 Schema

        仅验证 Runner 专有字段。旧版 nanobot 字段（llm_provider 等）
        如果存在会被忽略，不导致验证失败（向后兼容）。

        Args:
            config: 配置字典

        Returns:
            tuple[bool, list[str]]: (是否验证通过，错误消息列表)
        """
        errors: list[str] = []

        cls._validate_required_fields(config, errors)
        cls._validate_field_types(config, errors)
        cls._validate_version(config, errors)

        return len(errors) == 0, errors

    @classmethod
    def _validate_required_fields(cls, config: dict, errors: list[str]) -> None:
        """验证必填字段是否存在且非空"""
        for field_name in cls.REQUIRED_FIELDS:
            if field_name not in config:
                errors.append(f"缺少必填字段：{field_name}")
            elif config[field_name] is None or config[field_name] == "":
                errors.append(f"必填字段不能为空：{field_name}")

    @classmethod
    def _validate_field_types(cls, config: dict, errors: list[str]) -> None:
        """验证字段类型是否正确（仅检查 Schema 中定义的字段）"""
        for field_name, value in config.items():
            if field_name not in cls.FIELD_TYPES:
                continue

            expected_type = cls.FIELD_TYPES[field_name]
            if isinstance(expected_type, tuple):
                if not any(isinstance(value, t) for t in expected_type):
                    type_names = " | ".join(
                        getattr(t, "__name__", str(t)) for t in expected_type
                    )
                    errors.append(
                        f"字段 '{field_name}' 类型错误，期望 {type_names}，实际 {type(value).__name__}"
                    )
            elif not isinstance(value, expected_type):
                errors.append(
                    f"字段 '{field_name}' 类型错误，期望 {expected_type.__name__}，实际 {type(value).__name__}"
                )

    @classmethod
    def _validate_version(cls, config: dict, errors: list[str]) -> None:
        """验证版本号格式"""
        if "version" in config and config["version"]:
            version = config["version"]
            if not cls._is_valid_version(version):
                errors.append(f"版本号格式错误：'{version}'，应为 x.y.z 格式")

    @staticmethod
    def _is_valid_version(version: str) -> bool:
        """检查版本号格式是否有效"""
        import re

        pattern = r"^\d+\.\d+\.\d+$"
        return bool(re.match(pattern, version))

    @classmethod
    def from_dict(cls, config: dict) -> "AppConfig":
        """从字典创建 AppConfig 实例

        仅提取 Schema 中定义的字段，忽略旧版 nanobot 字段。

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

        known_fields = {k: v for k, v in config.items() if k in cls.FIELD_TYPES}

        return cls(**known_fields)

    def to_dict(self) -> dict:
        """将配置实例转换为字典"""
        return asdict(self)

    def __post_init__(self) -> None:
        """数据类初始化后验证"""
        is_valid, errors = self.validate(self.to_dict())
        if not is_valid:
            error_msg = "配置验证失败:\n" + "\n".join(f"  - {e}" for e in errors)
            raise ValueError(error_msg)
