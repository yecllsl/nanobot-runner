# LLM 超时控制模块单元测试 - v0.17.0

import asyncio
from unittest.mock import MagicMock

import pytest

from src.core.base.exceptions import LLMError
from src.core.llm_timeout import (
    LLMTimeoutController,
    TimeoutConfig,
    TimeoutStrategy,
    call_with_timeout,
    create_timeout_decorator,
)


class TestTimeoutConfig:
    """TimeoutConfig 测试"""

    def test_default_config(self):
        """测试默认配置"""
        config = TimeoutConfig()
        assert config.timeout_seconds == 30.0
        assert config.strategy == TimeoutStrategy.RAISE
        assert config.max_retries == 1
        assert config.retry_delay == 1.0
        assert config.fallback_fn is None

    def test_custom_config(self):
        """测试自定义配置"""
        fallback = MagicMock()
        config = TimeoutConfig(
            timeout_seconds=60.0,
            strategy=TimeoutStrategy.FALLBACK,
            max_retries=3,
            retry_delay=2.0,
            fallback_fn=fallback,
        )
        assert config.timeout_seconds == 60.0
        assert config.strategy == TimeoutStrategy.FALLBACK
        assert config.max_retries == 3
        assert config.retry_delay == 2.0
        assert config.fallback_fn is fallback


class TestLLMTimeoutController:
    """LLMTimeoutController 测试"""

    @pytest.mark.asyncio
    async def test_successful_call(self):
        """测试正常调用"""
        controller = LLMTimeoutController.with_timeout(5.0)

        async def success_func():
            return "success"

        result = await controller.call_with_timeout(success_func)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_timeout_raise_strategy(self):
        """测试超时抛出异常策略"""
        controller = LLMTimeoutController.with_timeout(0.1, TimeoutStrategy.RAISE)

        async def slow_func():
            await asyncio.sleep(10.0)
            return "should not reach"

        with pytest.raises(LLMError, match="超时"):
            await controller.call_with_timeout(slow_func)

    @pytest.mark.asyncio
    async def test_timeout_return_none_strategy(self):
        """测试超时返回None策略"""
        controller = LLMTimeoutController.with_timeout(0.1, TimeoutStrategy.RETURN_NONE)

        async def slow_func():
            await asyncio.sleep(10.0)
            return "should not reach"

        result = await controller.call_with_timeout(slow_func)
        assert result is None

    @pytest.mark.asyncio
    async def test_timeout_fallback_strategy(self):
        """测试超时备用函数策略"""
        fallback_result = "fallback value"
        fallback_fn = MagicMock(return_value=fallback_result)

        controller = LLMTimeoutController.with_fallback(
            fallback_fn=fallback_fn,
            timeout_seconds=0.1,
        )

        async def slow_func():
            await asyncio.sleep(10.0)
            return "should not reach"

        result = await controller.call_with_timeout(slow_func)
        assert result == fallback_result
        fallback_fn.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_function_timeout(self):
        """测试同步函数超时"""
        controller = LLMTimeoutController.with_timeout(0.1, TimeoutStrategy.RETURN_NONE)

        def slow_sync_func():
            import time

            time.sleep(10.0)
            return "should not reach"

        result = await controller.call_with_timeout(slow_sync_func)
        assert result is None

    @pytest.mark.asyncio
    async def test_retry_mechanism(self):
        """测试重试机制"""
        config = TimeoutConfig(
            timeout_seconds=0.1,
            strategy=TimeoutStrategy.RAISE,
            max_retries=2,
            retry_delay=0.01,
        )
        controller = LLMTimeoutController(config)

        call_count = 0

        async def failing_func():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(10.0)
            return "should not reach"

        with pytest.raises(LLMError):
            await controller.call_with_timeout(failing_func)

        # 验证被调用了 max_retries + 1 次
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_success_on_second_attempt(self):
        """测试第二次重试成功"""
        config = TimeoutConfig(
            timeout_seconds=0.5,
            strategy=TimeoutStrategy.RAISE,
            max_retries=2,
            retry_delay=0.01,
        )
        controller = LLMTimeoutController(config)

        call_count = 0

        async def sometimes_slow():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                await asyncio.sleep(10.0)
            return "success"

        result = await controller.call_with_timeout(sometimes_slow)
        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_exception_handling(self):
        """测试异常处理"""
        controller = LLMTimeoutController.with_timeout(5.0, TimeoutStrategy.RETURN_NONE)

        async def error_func():
            raise ValueError("test error")

        result = await controller.call_with_timeout(error_func)
        assert result is None

    def test_with_timeout_classmethod(self):
        """测试便捷构造方法"""
        controller = LLMTimeoutController.with_timeout(45.0, TimeoutStrategy.FALLBACK)
        assert controller.config.timeout_seconds == 45.0
        assert controller.config.strategy == TimeoutStrategy.FALLBACK

    def test_with_fallback_classmethod(self):
        """测试备用函数构造方法"""
        fallback = MagicMock()
        controller = LLMTimeoutController.with_fallback(
            fallback_fn=fallback,
            timeout_seconds=20.0,
        )
        assert controller.config.timeout_seconds == 20.0
        assert controller.config.strategy == TimeoutStrategy.FALLBACK
        assert controller.config.fallback_fn is fallback


class TestCallWithTimeout:
    """call_with_timeout 便捷函数测试"""

    @pytest.mark.asyncio
    async def test_call_with_timeout_success(self):
        """测试便捷函数成功调用"""

        async def success_func():
            return "success"

        result = await call_with_timeout(success_func, timeout=5.0)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_call_with_timeout_raises(self):
        """测试便捷函数超时抛出"""

        async def slow_func():
            await asyncio.sleep(10.0)
            return "should not reach"

        with pytest.raises(LLMError):
            await call_with_timeout(slow_func, timeout=0.1)


class TestTimeoutDecorator:
    """超时装饰器测试"""

    @pytest.mark.asyncio
    async def test_decorator_success(self):
        """测试装饰器正常执行"""
        decorator = create_timeout_decorator(5.0, TimeoutStrategy.RETURN_NONE)

        @decorator
        async def success_func():
            return "success"

        result = await success_func()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_decorator_timeout(self):
        """测试装饰器超时"""
        decorator = create_timeout_decorator(0.1, TimeoutStrategy.RETURN_NONE)

        @decorator
        async def slow_func():
            await asyncio.sleep(10.0)
            return "should not reach"

        result = await slow_func()
        assert result is None

    @pytest.mark.asyncio
    async def test_decorator_with_args(self):
        """测试装饰器带参数"""
        decorator = create_timeout_decorator(5.0, TimeoutStrategy.RETURN_NONE)

        @decorator
        async def func_with_args(a: int, b: str) -> str:
            return f"{a}-{b}"

        result = await func_with_args(1, "test")
        assert result == "1-test"
