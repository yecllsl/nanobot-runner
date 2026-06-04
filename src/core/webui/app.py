"""FastAPI 应用工厂 (v0.28.0)

创建和配置 FastAPI 应用实例，注册路由和中间件。
通过 create_app() 工厂函数注入 AppContext 依赖。
"""

from __future__ import annotations

import secrets
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.webui.auth import create_access_token

if TYPE_CHECKING:
    from src.core.base.context import AppContext

# 全局应用实例（由 create_app 设置）
_app_instance: FastAPI | None = None


def get_app() -> FastAPI | None:
    """获取全局 FastAPI 应用实例

    Returns:
        FastAPI | None: 应用实例，未创建时返回 None
    """
    return _app_instance


def create_app(context: AppContext) -> FastAPI:
    """创建 FastAPI 应用实例

    Args:
        context: 应用上下文，提供配置和核心模块访问

    Returns:
        FastAPI: 配置好的应用实例
    """
    global _app_instance

    webui_config = context.config.get_webui_config()

    app = FastAPI(
        title="Nanobot Runner WebUI API",
        version="0.28.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # CORS 中间件
    cors_origins = webui_config.get("cors_origins", ["http://127.0.0.1:8765"])
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 将 context 和配置注入 app.state
    app.state.context = context
    token_secret = webui_config.get("token_secret") or secrets.token_hex(32)
    app.state.webui_secret = token_secret
    app.state.webui_config = webui_config

    # 健康检查端点（无需认证）
    @app.get("/api/health", tags=["system"])
    async def health_check() -> dict[str, Any]:
        return {"status": "ok", "version": "0.28.0"}

    # 令牌签发端点（无需认证）
    @app.post("/api/auth/token", tags=["auth"])
    async def issue_token() -> dict[str, Any]:
        ttl = webui_config.get("token_ttl_s", 86400)
        token = create_access_token(secret=token_secret, ttl_seconds=ttl)
        return {"access_token": token, "token_type": "bearer"}

    # 注册业务路由
    from src.core.webui.routes.activities import router as activities_router
    from src.core.webui.routes.body_signal import router as body_signal_router
    from src.core.webui.routes.dashboard import router as dashboard_router
    from src.core.webui.routes.training_load import router as training_load_router
    from src.core.webui.routes.vdot import router as vdot_router

    app.include_router(dashboard_router, prefix="/api", tags=["dashboard"])
    app.include_router(vdot_router, prefix="/api", tags=["vdot"])
    app.include_router(training_load_router, prefix="/api", tags=["training-load"])
    app.include_router(activities_router, prefix="/api", tags=["activities"])
    app.include_router(body_signal_router, prefix="/api", tags=["body-signal"])

    _app_instance = app
    return app
