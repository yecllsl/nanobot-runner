# CLI 流式输出集成模块 - v0.17.0
# 为 Agent 命令提供流式输出支持

from __future__ import annotations

import logging
from typing import Any

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.spinner import Spinner

from src.core.transparency.streaming_hook import StreamingHook

logger = logging.getLogger(__name__)


class CLIStreamingManager:
    """CLI流式输出管理器

    管理Agent的流式输出，提供Rich控制台实时显示。
    支持Markdown渲染和进度指示。

    使用方式：
        with CLIStreamingManager() as streamer:
            hook = streamer.create_hook()
            # 将hook传递给Agent
            agent.run(hooks=[hook])
    """

    def __init__(
        self,
        console: Console | None = None,
        show_spinner: bool = True,
        render_markdown: bool = True,
    ) -> None:
        """初始化流式输出管理器

        Args:
            console: Rich控制台实例，默认使用全局console
            show_spinner: 是否显示加载动画
            render_markdown: 是否渲染Markdown格式
        """
        self._console = console or globals().get("console")
        self._show_spinner = show_spinner
        self._render_markdown = render_markdown

        self._stream_buffer: str = ""
        self._stream_active: bool = False
        self._live: Live | None = None
        self._spinner: Spinner | None = None

    def __enter__(self) -> CLIStreamingManager:
        """进入上下文管理器，启动Live显示"""
        if self._show_spinner:
            self._spinner = Spinner("dots", text="[dim]思考中...[/dim]")
            self._live = Live(
                self._spinner,
                console=self._console,
                refresh_per_second=10,
                transient=True,
            )
            self._live.start()

        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """退出上下文管理器，清理资源"""
        if self._live is not None:
            self._live.stop()
            self._live = None

        self._stream_active = False

    def create_hook(self) -> StreamingHook:
        """创建流式输出Hook

        Returns:
            StreamingHook: 配置好的流式输出钩子
        """
        return StreamingHook(console=self._console)

    def on_delta(self, delta: str) -> None:
        """处理流式输出片段

        在收到流式输出片段时更新显示。
        首次收到内容时停止spinner，显示实际内容。

        Args:
            delta: 流式输出片段
        """
        if not delta:
            return

        self._stream_active = True
        self._stream_buffer += delta

        # 首次收到内容时，停止spinner并开始显示内容
        if self._live is not None and self._spinner is not None:
            self._live.update(Panel(Markdown(self._stream_buffer), border_style="blue"))
        elif self._console is not None:
            # 直接输出到控制台
            self._console.print(delta, end="")

    def on_complete(self, final_text: str | None = None) -> None:
        """流式输出完成

        输出最终内容并清理状态。

        Args:
            final_text: 最终完整文本，如果为None则使用缓冲区内容
        """
        text = final_text or self._stream_buffer

        if self._live is not None:
            self._live.stop()
            self._live = None

        if text and self._console is not None:
            if self._render_markdown:
                self._console.print(Panel(Markdown(text), border_style="green"))
            else:
                self._console.print(text)

        self._stream_active = False
        self._stream_buffer = ""

    def get_buffer(self) -> str:
        """获取当前缓冲区内容

        Returns:
            str: 已缓冲的流式输出内容
        """
        return self._stream_buffer

    def is_active(self) -> bool:
        """检查流式输出是否活动

        Returns:
            bool: 流式输出是否处于活动状态
        """
        return self._stream_active


def stream_agent_response(
    agent_runner: Any,
    console: Console | None = None,
    show_spinner: bool = True,
) -> str:
    """流式运行Agent并返回完整响应

    便捷函数，用于简化Agent流式输出的使用。

    Args:
        agent_runner: Agent运行器，需要支持hooks参数
        console: Rich控制台实例
        show_spinner: 是否显示加载动画

    Returns:
        str: Agent的完整响应文本

    示例：
        response = stream_agent_response(
            agent,
            console=console,
            show_spinner=True,
        )
    """
    with CLIStreamingManager(
        console=console,
        show_spinner=show_spinner,
    ) as manager:
        hook = manager.create_hook()

        try:
            # 运行Agent，传入hook
            result = agent_runner.run(hooks=[hook])

            # 获取完整响应
            if hasattr(result, "content"):
                final_text = result.content
            elif isinstance(result, str):
                final_text = result
            else:
                final_text = str(result)

            manager.on_complete(final_text)
            return final_text

        except Exception as e:
            logger.error(f"Agent流式输出异常: {e}", exc_info=True)
            manager.on_complete(f"执行异常: {e}")
            raise
