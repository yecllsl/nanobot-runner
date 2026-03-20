# 自定义异常类单元测试

import pytest

from src.core.decorators import handle_errors, handle_tool_errors
from src.core.exceptions import (
    ConfigError,
    ImportError,
    IndexStoreError,
    NanobotRunnerError,
    ParseError,
    StorageError,
    ValidationError,
)


class TestNanobotRunnerError:
    """测试基础异常类"""

    def test_basic_error(self):
        """测试基本错误创建"""
        error = NanobotRunnerError(message="测试错误")
        assert error.message == "测试错误"
        assert error.error_code == "UNKNOWN_ERROR"
        assert error.recovery_suggestion is None

    def test_error_with_all_fields(self):
        """测试包含所有字段的错误"""
        error = NanobotRunnerError(
            message="测试错误",
            error_code="TEST_ERROR",
            recovery_suggestion="请重试",
        )
        assert error.message == "测试错误"
        assert error.error_code == "TEST_ERROR"
        assert error.recovery_suggestion == "请重试"

    def test_to_dict(self):
        """测试转换为字典"""
        error = NanobotRunnerError(
            message="测试错误",
            error_code="TEST_ERROR",
            recovery_suggestion="请重试",
        )
        result = error.to_dict()
        assert result["error"] == "测试错误"
        assert result["error_code"] == "TEST_ERROR"
        assert result["recovery_suggestion"] == "请重试"

    def test_exception_inheritance(self):
        """测试异常继承"""
        error = NanobotRunnerError(message="测试错误")
        assert isinstance(error, Exception)

    def test_raise_exception(self):
        """测试抛出异常"""
        with pytest.raises(NanobotRunnerError) as exc_info:
            raise NanobotRunnerError(message="测试错误")
        assert str(exc_info.value) == "测试错误"


class TestStorageError:
    """测试存储错误"""

    def test_default_values(self):
        """测试默认值"""
        error = StorageError(message="存储失败")
        assert error.message == "存储失败"
        assert error.error_code == "STORAGE_ERROR"
        assert error.recovery_suggestion == "请检查数据目录权限和磁盘空间"

    def test_custom_recovery_suggestion(self):
        """测试自定义恢复建议"""
        error = StorageError(
            message="存储失败",
            recovery_suggestion="自定义建议",
        )
        assert error.recovery_suggestion == "自定义建议"

    def test_inheritance(self):
        """测试继承关系"""
        error = StorageError(message="存储失败")
        assert isinstance(error, NanobotRunnerError)
        assert isinstance(error, Exception)


class TestParseError:
    """测试解析错误"""

    def test_default_values(self):
        """测试默认值"""
        error = ParseError(message="解析失败")
        assert error.message == "解析失败"
        assert error.error_code == "PARSE_ERROR"
        assert error.recovery_suggestion == "请确认文件格式正确，或尝试重新导出FIT文件"

    def test_inheritance(self):
        """测试继承关系"""
        error = ParseError(message="解析失败")
        assert isinstance(error, NanobotRunnerError)


class TestConfigError:
    """测试配置错误"""

    def test_default_values(self):
        """测试默认值"""
        error = ConfigError(message="配置错误")
        assert error.message == "配置错误"
        assert error.error_code == "CONFIG_ERROR"
        assert error.recovery_suggestion == "请检查配置文件格式，或删除配置文件后重新初始化"

    def test_inheritance(self):
        """测试继承关系"""
        error = ConfigError(message="配置错误")
        assert isinstance(error, NanobotRunnerError)


class TestValidationError:
    """测试验证错误"""

    def test_default_values(self):
        """测试默认值"""
        error = ValidationError(message="验证失败")
        assert error.message == "验证失败"
        assert error.error_code == "VALIDATION_ERROR"
        assert error.recovery_suggestion == "请检查输入数据是否符合要求"

    def test_inheritance(self):
        """测试继承关系"""
        error = ValidationError(message="验证失败")
        assert isinstance(error, NanobotRunnerError)


class TestIndexStoreError:
    """测试索引错误"""

    def test_default_values(self):
        """测试默认值"""
        error = IndexStoreError(message="索引错误")
        assert error.message == "索引错误"
        assert error.error_code == "INDEX_ERROR"
        assert error.recovery_suggestion == "请尝试重新导入数据以重建索引"

    def test_inheritance(self):
        """测试继承关系"""
        error = IndexStoreError(message="索引错误")
        assert isinstance(error, NanobotRunnerError)


class TestImportError:
    """测试导入错误"""

    def test_default_values(self):
        """测试默认值"""
        error = ImportError(message="导入失败")
        assert error.message == "导入失败"
        assert error.error_code == "IMPORT_ERROR"
        assert error.recovery_suggestion == "请检查文件路径和文件格式"

    def test_inheritance(self):
        """测试继承关系"""
        error = ImportError(message="导入失败")
        assert isinstance(error, NanobotRunnerError)


class TestHandleErrorsDecorator:
    """测试 handle_errors 装饰器"""

    def test_handle_errors_success(self):
        """测试正常执行"""

        @handle_errors()
        def successful_function():
            return {"result": "success"}

        result = successful_function()
        assert result == {"result": "success"}

    def test_handle_errors_nanobot_runner_error(self):
        """测试 NanobotRunnerError 处理"""

        @handle_errors()
        def error_function():
            raise StorageError(message="存储失败")

        result = error_function()
        assert "error" in result
        assert result["error"] == "存储失败"
        assert result["error_code"] == "STORAGE_ERROR"

    def test_handle_errors_file_not_found(self):
        """测试 FileNotFoundError 处理"""

        @handle_errors()
        def file_not_found_function():
            raise FileNotFoundError("文件不存在")

        result = file_not_found_function()
        assert "error" in result
        assert "文件未找到" in result["error"]
        assert result["error_code"] == "FILE_NOT_FOUND"

    def test_handle_errors_value_error(self):
        """测试 ValueError 处理"""

        @handle_errors()
        def value_error_function():
            raise ValueError("参数错误")

        result = value_error_function()
        assert "error" in result
        assert "参数错误" in result["error"]
        assert result["error_code"] == "VALUE_ERROR"

    def test_handle_errors_key_error(self):
        """测试 KeyError 处理"""

        @handle_errors()
        def key_error_function():
            raise KeyError("missing_key")

        result = key_error_function()
        assert "error" in result
        assert result["error_code"] == "KEY_ERROR"

    def test_handle_errors_generic_exception(self):
        """测试通用异常处理"""

        @handle_errors()
        def generic_error_function():
            raise RuntimeError("未知错误")

        result = generic_error_function()
        assert "error" in result
        assert result["error_code"] == "UNKNOWN_ERROR"

    def test_handle_errors_custom_default(self):
        """测试自定义默认返回值"""

        @handle_errors(default_response={"status": "failed"})
        def custom_default_function():
            raise Exception("错误")

        result = custom_default_function()
        assert result == {"status": "failed"}

    def test_handle_errors_no_traceback(self):
        """测试不记录堆栈"""

        @handle_errors(log_traceback=False)
        def error_function():
            raise StorageError(message="存储失败")

        result = error_function()
        assert "error" in result


class TestHandleToolErrorsDecorator:
    """测试 handle_tool_errors 装饰器"""

    def test_handle_tool_errors_nanobot_runner_error(self):
        """测试 NanobotRunnerError 处理"""

        @handle_tool_errors()
        def error_function():
            raise ParseError(message="解析失败")

        result = error_function()
        assert "error" in result
        assert result["error"] == "解析失败"
        assert result["error_code"] == "PARSE_ERROR"

    def test_handle_tool_errors_success(self):
        """测试正常执行"""

        @handle_tool_errors()
        def successful_function():
            return {"result": "success"}

        result = successful_function()
        assert result == {"result": "success"}

    def test_handle_tool_errors_custom_default(self):
        """测试自定义默认返回值"""

        @handle_tool_errors(default_response={"status": "failed"})
        def custom_default_function():
            raise Exception("错误")

        result = custom_default_function()
        assert result == {"status": "failed"}
