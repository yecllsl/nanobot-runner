# 装饰器模块单元测试

import json
from unittest.mock import MagicMock

import pytest

from src.core.decorators import (
    handle_empty_data,
    handle_errors,
    handle_tool_errors,
    require_storage,
    tool_wrapper,
    validate_date_format,
)
from src.core.exceptions import ParseError, StorageError, ToolResult, ValidationError


class TestHandleToolErrors:
    """测试错误处理装饰器"""

    def test_handle_tool_errors_success(self):
        """测试正常执行"""

        @handle_tool_errors()
        def successful_function():
            return {"result": "success"}

        result = successful_function()
        assert result == {"result": "success"}

    def test_handle_tool_errors_file_not_found(self):
        """测试FileNotFoundError处理"""

        @handle_tool_errors(default_response={"error": "数据不存在"})
        def file_not_found_function():
            raise FileNotFoundError("文件不存在")

        result = file_not_found_function()
        assert result == {"error": "暂无数据，请先导入跑步数据"}

    def test_handle_tool_errors_value_error(self):
        """测试ValueError处理"""

        @handle_tool_errors()
        def value_error_function():
            raise ValueError("参数错误")

        result = value_error_function()
        assert "error" in result
        assert "参数错误" in result["error"]

    def test_handle_tool_errors_key_error(self):
        """测试KeyError处理"""

        @handle_tool_errors()
        def key_error_function():
            raise KeyError("missing_key")

        result = key_error_function()
        assert "error" in result

    def test_handle_tool_errors_generic_exception(self):
        """测试通用异常处理"""

        @handle_tool_errors(error_message="操作失败")
        def generic_error_function():
            raise RuntimeError("未知错误")

        result = generic_error_function()
        assert "error" in result

    def test_handle_tool_errors_custom_default(self):
        """测试自定义默认值"""

        @handle_tool_errors(default_response={"status": "failed"})
        def custom_default_function():
            raise Exception("错误")

        result = custom_default_function()
        assert result == {"status": "failed"}


class TestRequireStorage:
    """测试存储初始化装饰器"""

    def test_require_storage_with_existing_storage(self):
        """测试已有storage的情况"""

        class TestClass:
            def __init__(self):
                self.storage = MagicMock()

            @require_storage
            def test_method(self):
                return "success"

        obj = TestClass()
        result = obj.test_method()
        assert result == "success"

    def test_require_storage_without_storage(self):
        """测试没有storage的情况"""
        from unittest.mock import patch

        from src.core.storage import StorageManager

        class TestClass:
            def __init__(self):
                self.storage = None

            @require_storage
            def test_method(self):
                return "success"

        with patch("src.core.storage.StorageManager") as MockStorage:
            mock_storage = MagicMock()
            MockStorage.return_value = mock_storage

            obj = TestClass()
            result = obj.test_method()

            assert result == "success"
            assert obj.storage is not None


class TestValidateDateFormat:
    """测试日期格式验证"""

    def test_validate_date_format_valid(self):
        """测试有效日期格式"""
        assert validate_date_format("2024-01-01") == True
        assert validate_date_format("2024-12-31") == True

    def test_validate_date_format_invalid(self):
        """测试无效日期格式"""
        assert validate_date_format("invalid") == False
        assert validate_date_format("2024/01/01") == False
        assert validate_date_format("") == False

    def test_validate_date_format_none(self):
        """测试None输入"""
        assert validate_date_format(None) == False


class TestHandleEmptyData:
    """测试空数据处理装饰器"""

    def test_handle_empty_data_with_data(self):
        """测试有数据的情况"""

        @handle_empty_data()
        def function_with_data():
            return [{"key": "value"}]

        result = function_with_data()
        assert result == [{"key": "value"}]

    def test_handle_empty_data_with_empty_list(self):
        """测试空列表"""

        @handle_empty_data(default_message="没有数据")
        def function_with_empty_list():
            return []

        result = function_with_empty_list()
        assert result == {"message": "没有数据"}

    def test_handle_empty_data_with_empty_dict(self):
        """测试空字典"""

        @handle_empty_data()
        def function_with_empty_dict():
            return {}

        result = function_with_empty_dict()
        assert result == {"message": "暂无数据"}

    def test_handle_empty_data_with_none(self):
        """测试返回None"""

        @handle_empty_data()
        def function_returns_none():
            return None

        result = function_returns_none()
        assert result == {"message": "暂无数据"}


class TestHandleErrors:
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

    def test_handle_tool_errors_nanobot_runner_error(self):
        """测试 handle_tool_errors 处理 NanobotRunnerError"""

        @handle_tool_errors()
        def error_function():
            raise ParseError(message="解析失败")

        result = error_function()
        assert "error" in result
        assert result["error"] == "解析失败"
        assert result["error_code"] == "PARSE_ERROR"


class TestToolResult:
    """测试 ToolResult 类"""

    def test_tool_result_success(self):
        """测试成功结果"""
        result = ToolResult(success=True, data={"key": "value"}, message="操作成功")
        result_dict = result.to_dict()
        assert result_dict["success"] is True
        assert result_dict["data"] == {"key": "value"}
        assert result_dict["message"] == "操作成功"
        assert "error" not in result_dict

    def test_tool_result_error(self):
        """测试错误结果"""
        result = ToolResult(success=False, error="操作失败")
        result_dict = result.to_dict()
        assert result_dict["success"] is False
        assert result_dict["error"] == "操作失败"
        assert "data" not in result_dict

    def test_tool_result_to_json(self):
        """测试JSON转换"""
        result = ToolResult(success=True, data={"test": 123})
        json_str = result.to_json()
        parsed = json.loads(json_str)
        assert parsed["success"] is True
        assert parsed["data"] == {"test": 123}


class TestToolWrapper:
    """测试 tool_wrapper 装饰器"""

    def test_tool_wrapper_success(self):
        """测试正常执行"""

        @tool_wrapper
        def successful_function():
            return {"result": "success"}

        result_json = successful_function()
        result = json.loads(result_json)
        assert result["success"] is True
        assert result["data"] == {"result": "success"}

    def test_tool_wrapper_with_tool_result(self):
        """测试返回 ToolResult 对象"""

        @tool_wrapper
        def tool_result_function():
            return ToolResult(success=True, data={"custom": "data"})

        result_json = tool_result_function()
        result = json.loads(result_json)
        assert result["success"] is True
        assert result["data"] == {"custom": "data"}

    def test_tool_wrapper_validation_error(self):
        """测试 ValidationError 处理"""

        @tool_wrapper
        def validation_error_function():
            raise ValidationError(message="输入验证失败")

        result_json = validation_error_function()
        result = json.loads(result_json)
        assert result["success"] is False
        assert "输入验证失败" in result["error"]

    def test_tool_wrapper_file_not_found(self):
        """测试 FileNotFoundError 处理"""

        @tool_wrapper
        def file_not_found_function():
            raise FileNotFoundError("文件不存在")

        result_json = file_not_found_function()
        result = json.loads(result_json)
        assert result["success"] is False
        assert "文件不存在" in result["error"]

    def test_tool_wrapper_nanobot_runner_error(self):
        """测试 NanobotRunnerError 处理"""

        @tool_wrapper
        def error_function():
            raise StorageError(message="存储失败")

        result_json = error_function()
        result = json.loads(result_json)
        assert result["success"] is False
        assert result["error"] == "存储失败"

    def test_tool_wrapper_generic_exception(self):
        """测试通用异常处理"""

        @tool_wrapper
        def generic_error_function():
            raise RuntimeError("未知错误")

        result_json = generic_error_function()
        result = json.loads(result_json)
        assert result["success"] is False
        assert "内部错误" in result["error"]
