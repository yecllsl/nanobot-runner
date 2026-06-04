"""uvicorn Server 封装 (v0.28.0)

提供 FastAPI 服务的启动和停止控制。
约束 C-01: 必须使用 uvicorn.Server(config).serve()，禁止 uvicorn.run()。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import uvicorn

from src.core.base.logger import get_logger

if TYPE_CHECKING:
    from src.core.base.context import AppContext

logger = get_logger(__name__)


def create_server(context: AppContext) -> uvicorn.Server:
    """创建 uvicorn Server 实例

    使用 uvicorn.Server(config).serve() 模式，
    可与 asyncio.gather() 配合实现并发运行。

    Args:
        context: 应用上下文

    Returns:
        uvicorn.Server: 配置好的 Server 实例
    """
    from src.core.webui.app import create_app

    webui_config = context.config.get_webui_config()
    host = webui_config.get("host", "127.0.0.1")
    port = webui_config.get("port", 8766)

    app = create_app(context=context)

    config = uvicorn.Config(
        app=app,
        host=host,
        port=port,
        log_level="warning",
        access_log=False,
    )

    server = uvicorn.Server(config)

    logger.info(f"WebUI API 服务配置: {host}:{port}")
    return server
