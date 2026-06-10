"""FastAPI 应用工厂 (v0.28.0)

创建和配置 FastAPI 应用实例，注册路由和中间件。
通过 create_app() 工厂函数注入 AppContext 依赖。
支持挂载前端静态文件，提供 SPA fallback 路由。
"""

from __future__ import annotations

import importlib.metadata
import secrets
from pathlib import Path
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

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

    # 动态读取包版本号
    try:
        app_version = importlib.metadata.version("nanobot-runner")
    except importlib.metadata.PackageNotFoundError:
        app_version = "dev"

    app = FastAPI(
        title="Nanobot Runner WebUI API",
        version=app_version,
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
        return {"status": "ok", "version": app_version}

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
    from src.core.webui.routes.evolution import router as evolution_router
    from src.core.webui.routes.plan import router as plan_router
    from src.core.webui.routes.settings import router as settings_router
    from src.core.webui.routes.training_load import router as training_load_router
    from src.core.webui.routes.vdot import router as vdot_router

    app.include_router(dashboard_router, prefix="/api", tags=["dashboard"])
    app.include_router(vdot_router, prefix="/api", tags=["vdot"])
    app.include_router(training_load_router, prefix="/api", tags=["training-load"])
    app.include_router(activities_router, prefix="/api", tags=["activities"])
    app.include_router(body_signal_router, prefix="/api", tags=["body-signal"])
    # v0.29.0 新增路由（统一 /api 前缀，资源名在路由路径中）
    app.include_router(plan_router, prefix="/api", tags=["plan"])
    app.include_router(evolution_router, prefix="/api", tags=["evolution"])
    app.include_router(settings_router, prefix="/api", tags=["settings"])

    # 挂载前端静态文件（SPA 模式）
    # 优先查找项目 webui/dist 目录，回退到 nanobot 内置目录
    _mount_frontend(app)

    _app_instance = app
    return app


def _find_webui_dist() -> Path | None:
    """查找前端构建产物目录

    Returns:
        Path | None: dist 目录路径，不存在时返回 None
    """
    # 优先使用项目 webui/dist 目录
    project_dist = (
        Path(__file__).resolve().parent.parent.parent.parent / "webui" / "dist"
    )
    if project_dist.is_dir() and (project_dist / "index.html").exists():
        return project_dist

    # 回退到 nanobot 内置目录
    try:
        import nanobot.web as web_pkg

        default_dist = Path(web_pkg.__file__).resolve().parent / "dist"
        if default_dist.is_dir() and (default_dist / "index.html").exists():
            return default_dist
    except ImportError:
        pass

    return None


def _mount_frontend(app: FastAPI) -> None:
    """挂载前端静态文件并提供 SPA fallback

    静态资源（/assets/*）由 StaticFiles 处理，
    其他非 /api 路径回退到 index.html（SPA 路由）。
    """
    dist_dir = _find_webui_dist()
    if dist_dir is None:
        return

    assets_dir = dist_dir / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    # SPA fallback：非 /api 路径返回 index.html
    @app.get("/{path:path}", include_in_schema=False)
    async def serve_spa(path: str) -> FileResponse:
        """SPA fallback 路由，所有非 API 路径返回 index.html"""
        # 尝试匹配 dist 中的实际文件（如 favicon.ico）
        candidate = dist_dir / path
        if path and candidate.is_file():
            return FileResponse(str(candidate))
        return FileResponse(str(dist_dir / "index.html"))
