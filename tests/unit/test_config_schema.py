# 配置 Schema 单元测试
# 测试配置 Schema 验证机制

import pytest

from src.core.config_schema import AppConfig


class TestAppConfigValidate:
    """测试 AppConfig 验证功能"""

    def test_validate_valid_config(self):
        """测试验证有效配置"""
        config = {
            "version": "0.1.0",
            "data_dir": "/data",
            "auto_push_feishu": False,
        }
        is_valid, errors = AppConfig.validate(config)
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_missing_required_field(self):
        """测试验证缺少必填字段"""
        config = {"version": "0.1.0"}  # 缺少 data_dir
        is_valid, errors = AppConfig.validate(config)
        assert is_valid is False
        assert any("缺少必填字段：data_dir" in e for e in errors)

    def test_validate_empty_required_field(self):
        """测试验证空必填字段"""
        config = {
            "version": "0.1.0",
            "data_dir": "",
        }
        is_valid, errors = AppConfig.validate(config)
        assert is_valid is False
        assert any("必填字段不能为空：data_dir" in e for e in errors)

    def test_validate_invalid_version_format(self):
        """测试验证无效版本号格式"""
        config = {
            "version": "0.1",  # 缺少补丁版本号
            "data_dir": "/data",
        }
        is_valid, errors = AppConfig.validate(config)
        assert is_valid is False
        assert any("版本号格式错误" in e for e in errors)

    def test_validate_invalid_receive_id_type(self):
        """测试验证无效的接收者 ID 类型"""
        config = {
            "version": "0.1.0",
            "data_dir": "/data",
            "feishu_receive_id_type": "invalid_type",
        }
        is_valid, errors = AppConfig.validate(config)
        assert is_valid is False
        assert any("feishu_receive_id_type 值错误" in e for e in errors)

    def test_validate_valid_receive_id_types(self):
        """测试验证有效的接收者 ID 类型"""
        valid_types = ["user_id", "open_id", "union_id"]
        for receive_type in valid_types:
            config = {
                "version": "0.1.0",
                "data_dir": "/data",
                "feishu_receive_id_type": receive_type,
            }
            is_valid, errors = AppConfig.validate(config)
            assert is_valid is True, f"类型 {receive_type} 应该有效"

    def test_validate_wrong_field_type(self):
        """测试验证错误的字段类型"""
        config = {
            "version": "0.1.0",
            "data_dir": "/data",
            "auto_push_feishu": "true",  # 应该是 bool，不是 str
        }
        is_valid, errors = AppConfig.validate(config)
        assert is_valid is False
        assert any("类型错误" in e for e in errors)

    def test_validate_with_optional_fields(self):
        """测试验证包含可选字段的配置"""
        config = {
            "version": "0.1.0",
            "data_dir": "/data",
            "auto_push_feishu": True,
            "feishu_app_id": "app123",
            "feishu_app_secret": "secret123",
            "feishu_receive_id": "user123",
            "feishu_receive_id_type": "user_id",
        }
        is_valid, errors = AppConfig.validate(config)
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_with_unknown_fields(self):
        """测试验证包含未知字段的配置"""
        config = {
            "version": "0.1.0",
            "data_dir": "/data",
            "unknown_field": "value",  # 未知字段应该被忽略
        }
        is_valid, errors = AppConfig.validate(config)
        # 未知字段不应该导致验证失败
        assert is_valid is True


class TestAppConfigFromDict:
    """测试 AppConfig from_dict 功能"""

    def test_from_dict_valid_config(self):
        """测试从有效字典创建配置"""
        config = {
            "version": "0.1.0",
            "data_dir": "/data",
            "auto_push_feishu": True,
        }
        app_config = AppConfig.from_dict(config)
        assert app_config.version == "0.1.0"
        assert app_config.data_dir == "/data"
        assert app_config.auto_push_feishu is True

    def test_from_dict_invalid_config(self):
        """测试从无效字典创建配置"""
        config = {"version": "0.1.0"}  # 缺少 data_dir
        with pytest.raises(ValueError) as exc_info:
            AppConfig.from_dict(config)
        assert "配置验证失败" in str(exc_info.value)
        assert "缺少必填字段：data_dir" in str(exc_info.value)

    def test_from_dict_with_defaults(self):
        """测试从字典创建配置使用默认值"""
        config = {
            "version": "0.1.0",
            "data_dir": "/data",
        }
        app_config = AppConfig.from_dict(config)
        assert app_config.auto_push_feishu is False
        assert app_config.feishu_receive_id_type == "user_id"
        assert app_config.feishu_app_id is None

    def test_from_dict_filters_unknown_fields(self):
        """测试从字典创建配置过滤未知字段"""
        config = {
            "version": "0.1.0",
            "data_dir": "/data",
            "unknown_field": "value",
        }
        app_config = AppConfig.from_dict(config)
        # 未知字段不应该在配置对象中
        assert not hasattr(app_config, "unknown_field")


class TestAppConfigToDict:
    """测试 AppConfig to_dict 功能"""

    def test_to_dict(self):
        """测试配置转字典"""
        app_config = AppConfig(
            version="0.1.0",
            data_dir="/data",
            auto_push_feishu=True,
            feishu_app_id="app123",
        )
        config_dict = app_config.to_dict()
        assert config_dict["version"] == "0.1.0"
        assert config_dict["data_dir"] == "/data"
        assert config_dict["auto_push_feishu"] is True
        assert config_dict["feishu_app_id"] == "app123"

    def test_to_dict_with_all_fields(self):
        """测试配置转字典包含所有字段"""
        app_config = AppConfig(
            version="0.1.0",
            data_dir="/data",
            auto_push_feishu=True,
            feishu_app_id="app123",
            feishu_app_secret="secret123",
            feishu_receive_id="user123",
            feishu_receive_id_type="open_id",
        )
        config_dict = app_config.to_dict()
        assert len(config_dict) == 7
        assert config_dict["feishu_receive_id_type"] == "open_id"


class TestAppConfigInit:
    """测试 AppConfig 初始化功能"""

    def test_init_valid(self):
        """测试有效初始化"""
        app_config = AppConfig(version="0.1.0", data_dir="/data")
        assert app_config.version == "0.1.0"
        assert app_config.data_dir == "/data"

    def test_init_with_all_params(self):
        """测试使用所有参数初始化"""
        app_config = AppConfig(
            version="0.2.0",
            data_dir="/test/data",
            auto_push_feishu=True,
            feishu_app_id="app456",
            feishu_app_secret="secret456",
            feishu_receive_id="user456",
            feishu_receive_id_type="union_id",
        )
        assert app_config.version == "0.2.0"
        assert app_config.auto_push_feishu is True
        assert app_config.feishu_receive_id_type == "union_id"

    def test_init_invalid_version(self):
        """测试无效版本号初始化"""
        with pytest.raises(ValueError) as exc_info:
            AppConfig(version="invalid", data_dir="/data")
        assert "配置验证失败" in str(exc_info.value)

    def test_init_post_init_validation(self):
        """测试初始化后自动验证"""
        # __post_init__ 会自动验证配置
        config = AppConfig(version="0.1.0", data_dir="/data")
        assert config.version == "0.1.0"


class TestAppConfigConstants:
    """测试 AppConfig 常量定义"""

    def test_required_fields_defined(self):
        """测试必填字段已定义"""
        assert "version" in AppConfig.REQUIRED_FIELDS
        assert "data_dir" in AppConfig.REQUIRED_FIELDS

    def test_field_types_defined(self):
        """测试字段类型已定义"""
        assert "version" in AppConfig.FIELD_TYPES
        assert "data_dir" in AppConfig.FIELD_TYPES
        assert "auto_push_feishu" in AppConfig.FIELD_TYPES

    def test_field_types_correct(self):
        """测试字段类型正确"""
        assert AppConfig.FIELD_TYPES["version"] == str
        assert AppConfig.FIELD_TYPES["data_dir"] == str
        assert AppConfig.FIELD_TYPES["auto_push_feishu"] == bool
        assert AppConfig.FIELD_TYPES["feishu_receive_id_type"] == str
