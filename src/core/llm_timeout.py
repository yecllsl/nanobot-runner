# LLM 超时控制模块 - v0.17.0
# 为LLM调用提供超时保护和优雅降级

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any, TypeVar

from src.core.base.exceptions import LLMError

logger = logging.getLogger(__name__)

T = TypeVar("T")


class TimeoutStrategy(Enum):
    """超时处理策略"""

    RAISE = "raise"  # 抛出异常
    RETURN_NONE = "return_none"  # 返回None
    FALLBACK = "fallback"  # 使用备用函数
    RETRY = "retry"  # 重试


@dataclass
class TimeoutConfig:
    """超时配置数据类

    Attributes:
        timeout_seconds: 超时时间（秒）
        strategy: 超时处理策略
        max_retries: 最大重试次数（仅RETRY策略）
        retry_delay: 重试延迟（秒）
        fallback_fn: 备用函数（仅FALLBACK策略）
    """

    timeout_seconds: float = 30.0
    strategy: TimeoutStrategy = TimeoutStrategy.RAISE
    max_retries: int = 1
    retry_delay: float = 1.0
    fallback_fn: Callable[..., T] | None = None


class LLMTimeoutController:
    """LLM超时控制器

    为LLM调用提供超时保护和优雅降级机制。
    支持多种超时处理策略：抛出异常、返回None、使用备用函数、重试。

    使用方式：
        controller = LLMTimeoutController(timeout=30.0)
        result = await controller.call_with_timeout(llm_function, args...)
    """

    def __init__(self, config: TimeoutConfig | None = None) -> None:
        """初始化超时控制器

        Args:
            config: 超时配置，默认使用30秒超时+抛出异常策略
        """
        self.config = config or TimeoutConfig()

    async def call_with_timeout(
        self,
        func: Callable[..., T],
        *args: Any,
        **kwargs: Any,
    ) -> T | None:
        """带超时的函数调用

        Args:
            func: 要执行的异步函数
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            函数返回值，或根据策略处理超时

        Raises:
            LLMError: 策略为RAISE时超时抛出
        """
        attempt = 0

        while attempt <= self.config.max_retries:
            try:
                if attempt > 0:
                    logger.info(f"第{attempt}次重试...")
                    await asyncio.sleep(self.config.retry_delay)

                # 使用asyncio.wait_for实现超时
                if asyncio.iscoroutinefunction(func):
                    result = await asyncio.wait_for(
                        func(*args, **kwargs),
                        timeout=self.config.timeout_seconds,
                    )
                else:
                    # 同步函数在线程池中执行
                    loop = asyncio.get_event_loop()
                    result = await asyncio.wait_for(
                        loop.run_in_executor(None, lambda: func(*args, **kwargs)),
                        timeout=self.config.timeout_seconds,
                    )

                return result

            except TimeoutError:
                attempt += 1
                logger.warning(
                    f"LLM调用超时 ({self.config.timeout_seconds}s)，"
                    f"尝试 {attempt}/{self.config.max_retries + 1}"
                )

                if attempt > self.config.max_retries:
                    return self._handle_timeout_error()

            except Exception as e:
                attempt += 1
                logger.warning(
                    f"LLM调用失败: {e}，尝试 {attempt}/{self.config.max_retries + 1}"
                )

                if attempt > self.config.max_retries:
                    return self._handle_timeout_error()

        # 所有重试都失败了
        return self._handle_timeout_error()

    def _handle_timeout_error(self) -> Any:
        """处理超时错误

        Returns:
            根据策略返回相应值

        Raises:
            LLMError: 策略为RAISE时抛出
        """
        strategy = self.config.strategy

        if strategy == TimeoutStrategy.RAISE:
            raise LLMError(
                f"LLM调用超时 ({self.config.timeout_seconds}s)"
                f"，已重试{self.config.max_retries}次",
                recovery_suggestion="请检查网络连接或增加超时时间",
            )

        elif strategy == TimeoutStrategy.RETURN_NONE:
            logger.info("超时策略: 返回None")
            return None

        elif strategy == TimeoutStrategy.FALLBACK:
            if self.config.fallback_fn is not None:
                logger.info("超时策略: 使用备用函数")
                try:
                    return self.config.fallback_fn()
                except Exception as e:
                    logger.error(f"备用函数执行失败: {e}")
                    return None
            else:
                logger.warning("未配置备用函数，返回None")
                return None

        elif strategy == TimeoutStrategy.RETRY:
            # RETRY策略在call_with_timeout中已经处理
            logger.warning("重试次数已耗尽")
            return None

        else:
            logger.warning(f"未知超时策略: {strategy}")
            return None

    @classmethod
    def with_timeout(
        cls,
        timeout_seconds: float = 30.0,
        strategy: TimeoutStrategy = TimeoutStrategy.RAISE,
    ) -> LLMTimeoutController:
        """便捷构造方法

        Args:
            timeout_seconds: 超时时间（秒）
            strategy: 超时处理策略

        Returns:
            LLMTimeoutController: 配置好的超时控制器
        """
        config = TimeoutConfig(
            timeout_seconds=timeout_seconds,
            strategy=strategy,
        )
        return cls(config)

    @classmethod
    def with_fallback(
        cls,
        fallback_fn: Callable[..., Any],
        timeout_seconds: float = 30.0,
    ) -> LLMTimeoutController:
        """使用备用函数的便捷构造方法

        Args:
            fallback_fn: 超时时的备用函数
            timeout_seconds: 超时时间（秒）

        Returns:
            LLMTimeoutController: 配置好的超时控制器
        """
        config = TimeoutConfig(
            timeout_seconds=timeout_seconds,
            strategy=TimeoutStrategy.FALLBACK,
            fallback_fn=fallback_fn,
        )
        return cls(config)


# 便捷函数


async def call_with_timeout(
    func: Callable[..., T],
    *args: Any,
    timeout: float = 30.0,
    **kwargs: Any,
) -> T | None:
    """便捷函数：带超时的函数调用

    Args:
        func: 要执行的函数
        *args: 位置参数
        timeout: 超时时间（秒）
        **kwargs: 关键字参数

    Returns:
        函数返回值，超时返回None

    Raises:
        LLMError: 超时抛出异常
    """
    controller = LLMTimeoutController.with_timeout(timeout)
    return await controller.call_with_timeout(func, *args, **kwargs)


def create_timeout_decorator(
    timeout_seconds: float = 30.0,
    strategy: TimeoutStrategy = TimeoutStrategy.RAISE,
) -> Callable[[Callable[..., T]], Callable[..., Any]]:
    """创建超时装饰器

    Args:
        timeout_seconds: 超时时间（秒）
        strategy: 超时处理策略

    Returns:
        装饰器函数
    """

    def decorator(func: Callable[..., T]) -> Callable[..., Any]:
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            controller = LLMTimeoutController.with_timeout(timeout_seconds, strategy)
            return await controller.call_with_timeout(func, *args, **kwargs)

        return wrapper

    return decorator
