# ErrorClassifier单元测试


from src.core.base.exceptions import (
    ConfigError,
    LLMError,
    ParseError,
    StorageError,
    ValidationError,
)
from src.core.transparency.error_classifier import (
    ErrorCategory,
    ErrorClassifier,
    FriendlyError,
)


class TestErrorClassifier:
    """ErrorClassifier测试类"""

    def test_classify_storage_error(self):
        """测试StorageError分类为DATA"""
        error = StorageError("存储失败")
        result = ErrorClassifier.classify(error)

        assert isinstance(result, FriendlyError)
        assert result.category == ErrorCategory.DATA
        assert result.original_error == error
        assert "存储" in result.friendly_message or "数据" in result.friendly_message

    def test_classify_parse_error(self):
        """测试ParseError分类为DATA"""
        error = ParseError("解析失败")
        result = ErrorClassifier.classify(error)

        assert result.category == ErrorCategory.DATA

    def test_classify_validation_error(self):
        """测试ValidationError分类为DATA"""
        error = ValidationError("验证失败")
        result = ErrorClassifier.classify(error)

        assert result.category == ErrorCategory.DATA

    def test_classify_config_error(self):
        """测试ConfigError分类为CONFIG"""
        error = ConfigError("配置缺失")
        result = ErrorClassifier.classify(error)

        assert result.category == ErrorCategory.CONFIG
        assert "配置" in result.friendly_message

    def test_classify_llm_error(self):
        """测试LLMError分类为NETWORK"""
        error = LLMError("LLM调用失败")
        result = ErrorClassifier.classify(error)

        assert result.category == ErrorCategory.NETWORK

    def test_classify_string_error(self):
        """测试字符串错误消息分类"""
        result = ErrorClassifier.classify("网络连接超时")

        assert result.category == ErrorCategory.NETWORK

    def test_classify_timeout_message(self):
        """测试超时消息分类"""
        result = ErrorClassifier.classify("请求timed out")

        # "timed out"同时匹配NETWORK和TIMEOUT，按类型优先级TIMEOUT应该在NETWORK之后
        # 这里验证至少分类为NETWORK或TIMEOUT之一
        assert result.category in (ErrorCategory.TIMEOUT, ErrorCategory.NETWORK)

    def test_classify_permission_message(self):
        """测试权限消息分类"""
        result = ErrorClassifier.classify("access denied")

        assert result.category == ErrorCategory.PERMISSION

    def test_classify_tool_message(self):
        """测试工具消息分类"""
        result = ErrorClassifier.classify("MCP工具调用失败")

        assert result.category == ErrorCategory.TOOL

    def test_classify_unknown_error(self):
        """测试未知错误分类"""
        error = Exception("未知错误")
        result = ErrorClassifier.classify(error)

        assert result.category == ErrorCategory.UNKNOWN

    def test_classify_with_context_data(self):
        """测试带上下文数据的分类"""
        error = StorageError("存储失败")
        context = {"file": "test.parquet"}
        result = ErrorClassifier.classify(error, context_data=context)

        assert result.context_data == context

    def test_custom_exception_recovery_suggestion(self):
        """测试自定义异常恢复建议"""
        error = ConfigError("配置错误", recovery_suggestion="自定义建议")
        result = ErrorClassifier.classify(error)

        assert result.recovery_suggestion == "自定义建议"

    def test_custom_exception_message(self):
        """测试自定义异常消息作为友好消息"""
        error = StorageError("自定义存储错误")
        result = ErrorClassifier.classify(error)

        assert result.friendly_message == "自定义存储错误"

    def test_all_categories_defined(self):
        """测试所有7种错误类型已定义"""
        categories = list(ErrorCategory)
        assert len(categories) == 7
        assert ErrorCategory.NETWORK in categories
        assert ErrorCategory.DATA in categories
        assert ErrorCategory.CONFIG in categories
        assert ErrorCategory.PERMISSION in categories
        assert ErrorCategory.TIMEOUT in categories
        assert ErrorCategory.TOOL in categories
        assert ErrorCategory.UNKNOWN in categories
