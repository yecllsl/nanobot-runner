"""FastAPI 应用工厂 (v0.28.0)

创建和配置 FastAPI 应用实例，注册路由和中间件。
通过 create_app() 工厂函数注入 AppContext 依赖。
支持挂载前端静态文件，提供 SPA fallback 路由。
约束 C-01: 必须使用 uvicorn.Server(config).serve()，禁止 uvicorn.run()。
"""

from __future__ import annotations

import importlib.metadata
import json
import secrets
from pathlib import Path
from typing import TYPE_CHECKING, Any

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from typing_extensions import TypedDict

from src.core.base.logger import get_logger
from src.core.webui.auth import create_access_token

if TYPE_CHECKING:
    from src.core.base.context import AppContext

logger = get_logger(__name__)


class HealthCheckResponse(TypedDict):
    """健康检查端点响应"""

    status: str
    version: str


class TokenResponse(TypedDict):
    """令牌签发端点响应"""

    access_token: str
    token_type: str


class MaxBodySizeMiddleware:
    """请求体大小限制中间件 (v0.34.0, ISSUE-01)

    FastAPI/Starlette 默认不限制请求体大小，超大上传会耗尽内存。
    本中间件仅对 multipart/form-data 请求限制总大小，其他请求放行。

    采用纯 ASGI 实现而非 BaseHTTPMiddleware，因为后者会缓冲整个响应体，
    破坏 SSE/WebSocket 等流式响应（见 test_routes_runtime_events 回归）。

    Args:
        app: ASGI 应用
        max_bytes: 请求体最大字节数
    """

    def __init__(self, app: Any, max_bytes: int = 60 * 1024 * 1024) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] == "http":
            headers = scope.get("headers", [])
            content_type = ""
            content_length = 0
            for name, value in headers:
                if name == b"content-type":
                    content_type = value.decode("latin-1")
                elif name == b"content-length":
                    try:
                        content_length = int(value)
                    except ValueError:
                        content_length = 0

            if (
                content_type.startswith("multipart/form-data")
                and content_length > self.max_bytes
            ):
                # 直接构造 413 响应，不调用下游应用
                body = json.dumps(
                    {"detail": "请求体过大，单次上传总计不超过 60MB"},
                    ensure_ascii=False,
                ).encode()
                await send(
                    {
                        "type": "http.response.start",
                        "status": 413,
                        "headers": [
                            (b"content-type", b"application/json"),
                            (b"content-length", str(len(body)).encode()),
                        ],
                    }
                )
                await send({"type": "http.response.body", "body": body})
                return

        await self.app(scope, receive, send)


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

    # v0.32.0: 从 context 读取 WebUI 配置
    webui_config: dict[str, Any] = context.config.get_webui_config()

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

    # v0.34.0: 请求体大小限制中间件（ISSUE-01 修复）
    # FastAPI/Starlette 默认无强制限制，显式设置 60MB 上限防止超大上传耗尽内存
    app.add_middleware(MaxBodySizeMiddleware, max_bytes=60 * 1024 * 1024)

    # 将 context 和配置注入 app.state
    app.state.context = context
    token_secret = webui_config.get("token_secret") or secrets.token_hex(32)
    app.state.webui_secret = token_secret
    app.state.webui_config = webui_config

    # 初始化运行时事件 Hook（v0.32.0）
    from src.core.transparency.runtime_event_hook import RuntimeEventHook

    app.state.runtime_event_hook = RuntimeEventHook(event_publisher=None)

    # 健康检查端点（无需认证）
    @app.get("/api/health", tags=["system"])
    async def health_check() -> HealthCheckResponse:
        return {"status": "ok", "version": app_version}

    # 令牌签发端点（无需认证）
    @app.post("/api/auth/token", tags=["auth"])
    async def issue_token() -> TokenResponse:
        ttl = webui_config.get("token_ttl_s", 86400)
        token = create_access_token(secret=token_secret, ttl_seconds=ttl)
        return {"access_token": token, "token_type": "bearer"}  # nosec B105

    # 注册业务路由
    from src.core.webui.routes.activities import router as activities_router
    from src.core.webui.routes.body_signal import router as body_signal_router
    from src.core.webui.routes.dashboard import router as dashboard_router
    from src.core.webui.routes.evolution import router as evolution_router
    from src.core.webui.routes.import_data import router as import_data_router
    from src.core.webui.routes.plan import router as plan_router
    from src.core.webui.routes.runtime_events import router as runtime_events_router
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
    # v0.32.0 运行时事件 SSE 端点
    app.include_router(runtime_events_router, prefix="/api", tags=["runtime-events"])
    # v0.34.0 数据导入路由
    app.include_router(import_data_router, prefix="/api", tags=["import"])

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
        # 路径穿越防护：resolve 后校验仍在 dist_dir 子树内
        resolved_dist = dist_dir.resolve()
        candidate = (resolved_dist / path).resolve()
        try:
            candidate.relative_to(resolved_dist)
        except ValueError:
            # 路径逃逸 dist_dir，回退到 index.html
            return FileResponse(str(resolved_dist / "index.html"))
        # 尝试匹配 dist 中的实际文件（如 favicon.ico）
        if path and candidate.is_file():
            return FileResponse(str(candidate))
        return FileResponse(str(resolved_dist / "index.html"))


def create_server(context: AppContext) -> uvicorn.Server:
    """创建 uvicorn Server 实例

    使用 uvicorn.Server(config).serve() 模式，
    可与 asyncio.gather() 配合实现并发运行。

    Args:
        context: 应用上下文

    Returns:
        uvicorn.Server: 配置好的 Server 实例
    """
    host = "127.0.0.1"
    port = 8766

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
