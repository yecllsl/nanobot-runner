"""JWT 认证中间件 (v0.28.0)

为 WebUI REST API 提供 Token 签发和验证功能。
使用 PyJWT 实现 HS256 签名，支持令牌过期。
"""

from __future__ import annotations

import time
from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

security = HTTPBearer(auto_error=False)


def create_access_token(
    secret: str,
    ttl_seconds: int = 86400,
    subject: str = "nanobot-runner",
) -> str:
    """签发 JWT 访问令牌

    Args:
        secret: JWT 签名密钥
        ttl_seconds: 令牌有效时长（秒）
        subject: 令牌主题（默认 nanobot-runner）

    Returns:
        str: 编码后的 JWT 字符串
    """
    now = time.time()
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": int(now),
        "exp": int(now) + ttl_seconds,
    }
    return jwt.encode(payload, secret, algorithm="HS256")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> str:
    """FastAPI 依赖项：从请求中提取并验证 JWT 令牌

    从 Authorization: Bearer <token> 头中提取令牌，
    使用 app.state.webui_secret 进行验证。

    Args:
        credentials: HTTP Bearer 凭证

    Returns:
        str: 令牌中的 subject（用户标识）

    Raises:
        HTTPException: 令牌缺失、无效或过期时返回 401
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 从 app.state 获取密钥（在应用工厂中设置）
    from src.core.webui.app import get_app

    app = get_app()
    if app is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="应用实例未初始化",
        )
    secret = getattr(app.state, "webui_secret", "")

    if not secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="服务端未配置认证密钥",
        )

    try:
        payload = jwt.decode(
            credentials.credentials,
            secret,
            algorithms=["HS256"],
        )
        subject: str = payload.get("sub", "nanobot-runner")
        return subject
    except jwt.ExpiredSignatureError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌已过期",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效令牌",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
