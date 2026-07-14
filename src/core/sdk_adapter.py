"""SDK 适配器 - 编程式 Agent 调用入口

封装 nanobot 0.2.2 Python SDK，为业务模块提供编程式 Agent 调用能力，
绕过 Gateway 消息总线。

基于 nanobot 0.2.2 实际 API 调研：
- SDK 入口类为 Nanobot（非 NanobotSDK）
- 通过 Nanobot.from_config() classmethod 创建实例
- 支持 async with 上下文管理器
- stream() 返回 AsyncIterator[StreamEvent]，文本片段在 event.delta
- run() 返回 RunResult，最终文本在 result.content
"""

import logging
from collections.abc import AsyncIterator
from pathlib import Path

from nanobot.nanobot import Nanobot

logger = logging.getLogger(__name__)


class SDKUnavailableError(Exception):
    """SDK 不可用异常"""


class SDKAdapter:
    """封装 nanobot 0.2.2 SDK，提供编程式 Agent 调用

    使用场景：
    - 进化引擎触发 Agent 决策（无需 Gateway）
    - 数字孪生 What-If 推演（编程式调用）
    - 训练计划自动生成（嵌入业务流程）
    """

    def __init__(self, workspace: str | Path | None = None):
        """初始化 SDKAdapter

        Args:
            workspace: nanobot 工作区路径
        """
        self._workspace = workspace

    async def create_session(self, session_key: str = "sdk:default") -> Nanobot:
        """创建 SDK 会话

        Args:
            session_key: 会话键（用于日志追踪）

        Returns:
            Nanobot: SDK 实例，调用方负责通过 async with 管理生命周期

        Raises:
            SDKUnavailableError: SDK 创建失败
        """
        try:
            logger.debug("创建 SDK 会话: %s", session_key)
            return Nanobot.from_config(workspace=self._workspace)
        except Exception as e:
            logger.error("SDK 会话创建失败: %s", e)
            raise SDKUnavailableError(f"SDK 模式不可用: {e}") from e

    async def stream_query(
        self, message: str, session_key: str | None = None
    ) -> AsyncIterator[str]:
        """流式查询 Agent

        Args:
            message: 用户消息
            session_key: 会话键（None 表示默认会话）

        Yields:
            str: Agent 响应文本片段（来自 StreamEvent.delta）

        Raises:
            SDKUnavailableError: SDK 模式不可用
        """
        key = session_key or "sdk:default"
        sdk = await self.create_session(key)
        try:
            async with sdk:
                async for event in sdk.stream(message, session_key=key):
                    if event.delta:
                        yield event.delta
        except SDKUnavailableError:
            raise
        except Exception as e:
            logger.warning("SDK 流式查询失败: %s", e)
            raise SDKUnavailableError(f"SDK 模式不可用: {e}") from e

    async def query(self, message: str, session_key: str | None = None) -> str:
        """同步查询 Agent（非流式）

        Args:
            message: 用户消息
            session_key: 会话键

        Returns:
            str: Agent 完整响应（来自 RunResult.content）

        Raises:
            SDKUnavailableError: SDK 模式不可用
        """
        key = session_key or "sdk:default"
        sdk = await self.create_session(key)
        try:
            async with sdk:
                result = await sdk.run(message, session_key=key)
                return result.content or ""
        except SDKUnavailableError:
            raise
        except Exception as e:
            logger.warning("SDK 查询失败: %s", e)
            raise SDKUnavailableError(f"SDK 模式不可用: {e}") from e
