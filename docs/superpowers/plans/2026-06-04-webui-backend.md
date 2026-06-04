# v0.28.0 WebUI 后端 API 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 WebUI 前端提供 FastAPI REST API 后端，暴露 Dashboard、VDOT趋势、训练负荷、活动列表/详情、身体信号等数据接口，集成到现有 Gateway 启动流程。

**Architecture:** 新增 `src/core/webui/` 子模块，包含 FastAPI 应用工厂、JWT 认证中间件、API 路由。所有核心模块方法为同步调用，通过 `starlette.concurrency.run_in_threadpool()` 包装为异步。Gateway `start()` 命令中通过 `uvicorn.Server(config).serve()` 将 FastAPI 服务加入 `asyncio.gather()` 并发运行。

**Tech Stack:** Python 3.11+ / FastAPI / uvicorn / PyJWT / Pydantic / `get_context()` 依赖注入

---

## File Structure

| 文件 | 操作 | 职责 |
|------|------|------|
| `pyproject.toml` | 修改 | 新增 fastapi 依赖 |
| `config.example.json` | 修改 | 新增 webui 配置节 |
| `src/core/config/schema.py` | 修改 | AppConfig 新增 webui 字段 |
| `src/core/config/manager.py` | 修改 | 新增 get_webui_config() / WEBUI_ENV_KEY_MAPPING |
| `src/core/webui/__init__.py` | 创建 | 模块入口 |
| `src/core/webui/app.py` | 创建 | FastAPI 应用工厂 |
| `src/core/webui/auth.py` | 创建 | JWT 认证中间件 |
| `src/core/webui/routes/dashboard.py` | 创建 | Dashboard 汇总 API |
| `src/core/webui/routes/vdot.py` | 创建 | VDOT 趋势 API |
| `src/core/webui/routes/training_load.py` | 创建 | 训练负荷 API |
| `src/core/webui/routes/activities.py` | 创建 | 活动列表 + 详情 API |
| `src/core/webui/routes/body_signal.py` | 创建 | 身体信号 API |
| `src/core/webui/routes/__init__.py` | 创建 | 路由注册 |
| `src/core/webui/server.py` | 创建 | uvicorn Server 封装 |
| `src/cli/commands/gateway.py` | 修改 | 集成 FastAPI 启动 |
| `tests/unit/core/webui/test_auth.py` | 创建 | 认证中间件测试 |
| `tests/unit/core/webui/test_app.py` | 创建 | 应用工厂测试 |
| `tests/unit/core/webui/test_routes_dashboard.py` | 创建 | Dashboard 路由测试 |
| `tests/unit/core/webui/test_routes_vdot.py` | 创建 | VDOT 路由测试 |
| `tests/unit/core/webui/test_routes_training_load.py` | 创建 | 训练负荷路由测试 |
| `tests/unit/core/webui/test_routes_activities.py` | 创建 | 活动路由测试 |
| `tests/unit/core/webui/test_routes_body_signal.py` | 创建 | 身体信号路由测试 |
| `tests/unit/core/config/test_webui_config.py` | 创建 | WebUI 配置测试 |

---

## Task 1: 项目骨架与依赖配置 (T01)

**Files:**
- Modify: `pyproject.toml:7-26`
- Modify: `config.example.json`
- Create: `src/core/webui/__init__.py`

- [ ] **Step 1: 在 pyproject.toml 中新增 fastapi 依赖**

在 `pyproject.toml` 的 `dependencies` 列表中，在 `"joblib>=1.3.0"` 之后新增：

```toml
    "fastapi>=0.115.0",
```

- [ ] **Step 2: 在 config.example.json 中新增 webui 配置节**

在 `config.example.json` 的 `websocket` 配置节之后新增：

```json
  "webui": {
    "_comment": "WebUI FastAPI 后端配置",
    "enabled": false,
    "enabled_comment": "是否启用 WebUI REST API 后端",
    "host": "127.0.0.1",
    "host_comment": "FastAPI 服务监听地址",
    "port": 18791,
    "port_comment": "FastAPI 服务监听端口，与 WebSocket 端口分离",
    "cors_origins": ["http://127.0.0.1:8765", "http://localhost:8765"],
    "cors_origins_comment": "CORS 允许的来源列表，需包含 WebUI 前端地址",
    "token_secret": "",
    "token_secret_comment": "JWT 签名密钥，生产环境务必设置强密钥，为空则自动生成",
    "token_ttl_s": 86400,
    "token_ttl_s_comment": "JWT 令牌有效时长（秒），默认 24 小时"
  },
```

- [ ] **Step 3: 创建 webui 模块入口文件**

创建 `src/core/webui/__init__.py`：

```python
"""WebUI FastAPI 后端模块 (v0.28.0)

为 WebUI 前端提供 REST API 接口，包括：
- Dashboard 汇总数据
- VDOT 趋势数据
- 训练负荷数据
- 活动列表与详情
- 身体信号数据
"""
```

- [ ] **Step 4: 安装依赖并验证**

Run: `uv sync`
Expected: 成功安装 fastapi 及其依赖

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml config.example.json src/core/webui/__init__.py
git commit -m "feat(webui): add fastapi dependency and webui config skeleton"
```

---

## Task 2: WebUI 配置管理 (T04)

**Files:**
- Modify: `src/core/config/schema.py:38-58`
- Modify: `src/core/config/manager.py:41-53`
- Modify: `src/core/config/manager.py:454-478`
- Create: `tests/unit/core/config/test_webui_config.py`

- [ ] **Step 1: 编写 WebUI 配置读取的失败测试**

创建 `tests/unit/core/config/test_webui_config.py`：

```python
"""WebUI 配置读取单元测试"""

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from src.core.config.manager import ConfigManager


@pytest.fixture
def config_dir(tmp_path: Path) -> Path:
    """创建包含 webui 配置的临时目录"""
    config_data = {
        "version": "0.28.0",
        "data_dir": str(tmp_path / "data"),
        "webui": {
            "enabled": True,
            "host": "0.0.0.0",
            "port": 9090,
            "cors_origins": ["http://localhost:3000"],
            "token_secret": "test-secret-key",
            "token_ttl_s": 3600,
        },
    }
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(config_data), encoding="utf-8")
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return tmp_path


class TestGetWebuiConfig:
    def test_returns_webui_config_from_file(self, config_dir: Path) -> None:
        """从配置文件读取 webui 配置"""
        with patch.dict(os.environ, {"NANOBOT_CONFIG_DIR": str(config_dir)}):
            ConfigManager.reset_cache()
            mgr = ConfigManager()
            result = mgr.get_webui_config()

        assert result["enabled"] is True
        assert result["host"] == "0.0.0.0"
        assert result["port"] == 9090
        assert result["cors_origins"] == ["http://localhost:3000"]
        assert result["token_secret"] == "test-secret-key"
        assert result["token_ttl_s"] == 3600

    def test_returns_empty_dict_when_no_webui_section(self, tmp_path: Path) -> None:
        """配置文件无 webui 节时返回空 dict"""
        config_data = {
            "version": "0.28.0",
            "data_dir": str(tmp_path / "data"),
        }
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config_data), encoding="utf-8")
        (tmp_path / "data").mkdir()

        with patch.dict(os.environ, {"NANOBOT_CONFIG_DIR": str(tmp_path)}):
            ConfigManager.reset_cache()
            mgr = ConfigManager()
            result = mgr.get_webui_config()

        assert result == {}

    def test_env_override_port(self, config_dir: Path) -> None:
        """环境变量覆盖 webui.port"""
        with patch.dict(
            os.environ,
            {
                "NANOBOT_CONFIG_DIR": str(config_dir),
                "NANOBOT_WEBUI_PORT": "9999",
            },
        ):
            ConfigManager.reset_cache()
            mgr = ConfigManager()
            result = mgr.get_webui_config()

        assert result["port"] == 9999

    def test_env_override_enabled(self, config_dir: Path) -> None:
        """环境变量覆盖 webui.enabled"""
        with patch.dict(
            os.environ,
            {
                "NANOBOT_CONFIG_DIR": str(config_dir),
                "NANOBOT_WEBUI_ENABLED": "false",
            },
        ):
            ConfigManager.reset_cache()
            mgr = ConfigManager()
            result = mgr.get_webui_config()

        assert result["enabled"] is False

    def test_env_override_host(self, config_dir: Path) -> None:
        """环境变量覆盖 webui.host"""
        with patch.dict(
            os.environ,
            {
                "NANOBOT_CONFIG_DIR": str(config_dir),
                "NANOBOT_WEBUI_HOST": "192.168.1.1",
            },
        ):
            ConfigManager.reset_cache()
            mgr = ConfigManager()
            result = mgr.get_webui_config()

        assert result["host"] == "192.168.1.1"

    def test_defaults_when_missing_fields(self, tmp_path: Path) -> None:
        """webui 配置节存在但字段缺失时使用默认值"""
        config_data = {
            "version": "0.28.0",
            "data_dir": str(tmp_path / "data"),
            "webui": {"enabled": True},
        }
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config_data), encoding="utf-8")
        (tmp_path / "data").mkdir()

        with patch.dict(os.environ, {"NANOBOT_CONFIG_DIR": str(tmp_path)}):
            ConfigManager.reset_cache()
            mgr = ConfigManager()
            result = mgr.get_webui_config()

        assert result["enabled"] is True
        assert result["host"] == "127.0.0.1"
        assert result["port"] == 18791
```

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/unit/core/config/test_webui_config.py -v`
Expected: FAIL - `AttributeError: 'ConfigManager' object has no attribute 'get_webui_config'`

- [ ] **Step 3: 在 AppConfig schema 中新增 webui 字段**

在 `src/core/config/schema.py` 的 `AppConfig` 类中，在 `websocket` 字段之后新增：

```python
    webui: dict[str, Any] | None = None
```

在 `FIELD_TYPES` 字典中新增：

```python
        "webui": (dict, type(None)),
```

- [ ] **Step 4: 在 ConfigManager 中新增 WEBUI_ENV_KEY_MAPPING 和 get_webui_config 方法**

在 `src/core/config/manager.py` 中，在 `WS_ENV_KEY_MAPPING` 之后新增：

```python
# WebUI 环境变量映射，支持 NANOBOT_WEBUI_* 环境变量覆盖配置文件值
WEBUI_ENV_KEY_MAPPING: dict[str, str] = {
    "enabled": "NANOBOT_WEBUI_ENABLED",
    "host": "NANOBOT_WEBUI_HOST",
    "port": "NANOBOT_WEBUI_PORT",
    "token_secret": "NANOBOT_WEBUI_TOKEN_SECRET",
    "token_ttl_s": "NANOBOT_WEBUI_TOKEN_TTL_S",
}
```

在 `INT_KEYS` 中新增 `"token_ttl_s"`：

```python
INT_KEYS: set[str] = {"default_year", "port", "token_ttl_s"}
```

在 `ConfigManager` 类中，在 `get_websocket_config` 方法之后新增：

```python
    def get_webui_config(self) -> dict[str, Any]:
        """获取 WebUI REST API 配置

        从 config.json 的 webui 配置节读取，支持环境变量覆盖。
        优先级：环境变量 > 配置文件 > 默认值

        Returns:
            dict[str, Any]: WebUI 配置字典，配置节不存在时返回含默认值的 dict
        """
        config = self.load_config()

        # 读取 webui 配置节，不存在或类型异常时使用默认值
        webui_raw: Any = config.get("webui", {})
        if not isinstance(webui_raw, dict):
            webui_config: dict[str, Any] = {}
        else:
            webui_config = dict(webui_raw)

        # 环境变量覆盖
        for webui_key, env_key in WEBUI_ENV_KEY_MAPPING.items():
            env_value = os.getenv(env_key)
            if env_value is not None:
                webui_config[webui_key] = self._cast_env_value(webui_key, env_value)

        # 填充默认值（仅在字段缺失时）
        webui_config.setdefault("enabled", False)
        webui_config.setdefault("host", "127.0.0.1")
        webui_config.setdefault("port", 18791)
        webui_config.setdefault("cors_origins", ["http://127.0.0.1:8765", "http://localhost:8765"])
        webui_config.setdefault("token_secret", "")
        webui_config.setdefault("token_ttl_s", 86400)

        return webui_config
```

- [ ] **Step 5: 运行测试确认通过**

Run: `uv run pytest tests/unit/core/config/test_webui_config.py -v`
Expected: 全部 PASS

- [ ] **Step 6: Commit**

```bash
git add src/core/config/schema.py src/core/config/manager.py tests/unit/core/config/test_webui_config.py
git commit -m "feat(webui): add webui config with env override support"
```

---

## Task 3: JWT 认证中间件 (T03)

**Files:**
- Create: `src/core/webui/auth.py`
- Create: `tests/unit/core/webui/test_auth.py`

- [ ] **Step 1: 编写认证中间件的失败测试**

创建 `tests/unit/core/webui/test_auth.py`：

```python
"""JWT 认证中间件单元测试"""

import time
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.core.webui.auth import create_access_token, get_current_user


@pytest.fixture
def secret_key() -> str:
    return "test-secret-for-jwt"


@pytest.fixture
def app(secret_key: str) -> FastAPI:
    """创建带认证依赖的测试应用"""
    app = FastAPI()

    @app.get("/protected")
    async def protected_route(user: str = get_current_user):
        return {"user": user}

    @app.post("/auth/token")
    async def login():
        token = create_access_token(
            secret=secret_key,
            ttl_seconds=3600,
        )
        return {"access_token": token, "token_type": "bearer"}

    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    # 注入 secret_key 到 app.state
    app.state.webui_secret = secret_key
    return TestClient(app)


class TestCreateAccessToken:
    def test_create_valid_token(self, secret_key: str) -> None:
        """创建有效的 JWT 令牌"""
        token = create_access_token(secret=secret_key, ttl_seconds=3600)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_token_contains_exp_claim(self, secret_key: str) -> None:
        """令牌包含 exp 过期时间"""
        import jwt

        token = create_access_token(secret=secret_key, ttl_seconds=3600)
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        assert "exp" in payload
        assert "sub" in payload
        assert payload["sub"] == "nanobot-runner"


class TestGetCurrentUser:
    def test_valid_token_returns_user(self, client: TestClient, secret_key: str) -> None:
        """有效令牌返回用户信息"""
        token = create_access_token(secret=secret_key, ttl_seconds=3600)
        response = client.get(
            "/protected",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["user"] == "nanobot-runner"

    def test_missing_token_returns_401(self, client: TestClient) -> None:
        """缺少令牌返回 401"""
        response = client.get("/protected")
        assert response.status_code == 401

    def test_invalid_token_returns_401(self, client: TestClient) -> None:
        """无效令牌返回 401"""
        response = client.get(
            "/protected",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert response.status_code == 401

    def test_expired_token_returns_401(self, client: TestClient, secret_key: str) -> None:
        """过期令牌返回 401"""
        token = create_access_token(secret=secret_key, ttl_seconds=-1)
        response = client.get(
            "/protected",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401

    def test_token_issue_endpoint(self, client: TestClient) -> None:
        """令牌签发端点返回有效令牌"""
        response = client.post("/auth/token")
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/unit/core/webui/test_auth.py -v`
Expected: FAIL - `ModuleNotFoundError: No module named 'src.core.webui.auth'`

- [ ] **Step 3: 实现 JWT 认证中间件**

创建 `src/core/webui/auth.py`：

```python
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
```

- [ ] **Step 4: 运行测试确认通过**

Run: `uv run pytest tests/unit/core/webui/test_auth.py -v`
Expected: 全部 PASS

- [ ] **Step 5: Commit**

```bash
git add src/core/webui/auth.py tests/unit/core/webui/test_auth.py
git commit -m "feat(webui): add JWT authentication middleware"
```

---

## Task 4: FastAPI 应用工厂 (T02)

**Files:**
- Create: `src/core/webui/app.py`
- Create: `src/core/webui/routes/__init__.py`
- Create: `tests/unit/core/webui/test_app.py`

- [ ] **Step 1: 编写应用工厂的失败测试**

创建 `tests/unit/core/webui/test_app.py`：

```python
"""FastAPI 应用工厂单元测试"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.core.webui.app import create_app, get_app


class TestCreateApp:
    def test_create_app_returns_fastapi_instance(self) -> None:
        """create_app 返回 FastAPI 实例"""
        from fastapi import FastAPI

        mock_context = MagicMock()
        mock_context.config.get_webui_config.return_value = {
            "enabled": True,
            "host": "127.0.0.1",
            "port": 18791,
            "cors_origins": ["http://localhost:8765"],
            "token_secret": "test-secret",
            "token_ttl_s": 86400,
        }
        app = create_app(context=mock_context)
        assert isinstance(app, FastAPI)

    def test_health_check_endpoint(self) -> None:
        """健康检查端点返回 200"""
        mock_context = MagicMock()
        mock_context.config.get_webui_config.return_value = {
            "enabled": True,
            "host": "127.0.0.1",
            "port": 18791,
            "cors_origins": [],
            "token_secret": "test-secret",
            "token_ttl_s": 86400,
        }
        app = create_app(context=mock_context)
        client = TestClient(app)
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data

    def test_token_issue_endpoint(self) -> None:
        """令牌签发端点可用"""
        mock_context = MagicMock()
        mock_context.config.get_webui_config.return_value = {
            "enabled": True,
            "host": "127.0.0.1",
            "port": 18791,
            "cors_origins": [],
            "token_secret": "test-secret",
            "token_ttl_s": 86400,
        }
        app = create_app(context=mock_context)
        client = TestClient(app)
        response = client.post("/api/auth/token")
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_cors_middleware_configured(self) -> None:
        """CORS 中间件已配置"""
        mock_context = MagicMock()
        mock_context.config.get_webui_config.return_value = {
            "enabled": True,
            "host": "127.0.0.1",
            "port": 18791,
            "cors_origins": ["http://localhost:8765"],
            "token_secret": "test-secret",
            "token_ttl_s": 86400,
        }
        app = create_app(context=mock_context)
        # 验证 CORS 中间件已添加
        middleware_types = [type(m).__name__ for m in app.user_middleware]
        assert "CORSMiddleware" in middleware_types or any(
            "CORS" in str(m) for m in app.user_middleware
        )


class TestGetApp:
    def test_get_app_returns_none_before_create(self) -> None:
        """创建前 get_app 返回 None"""
        # 重置全局实例
        import src.core.webui.app as app_module
        app_module._app_instance = None
        assert get_app() is None
```

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/unit/core/webui/test_app.py -v`
Expected: FAIL - `ModuleNotFoundError: No module named 'src.core.webui.app'`

- [ ] **Step 3: 创建路由模块入口**

创建 `src/core/webui/routes/__init__.py`：

```python
"""WebUI API 路由模块"""
```

- [ ] **Step 4: 实现 FastAPI 应用工厂**

创建 `src/core/webui/app.py`：

```python
"""FastAPI 应用工厂 (v0.28.0)

创建和配置 FastAPI 应用实例，注册路由和中间件。
通过 create_app() 工厂函数注入 AppContext 依赖。
"""

from __future__ import annotations

import secrets
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.webui.auth import create_access_token, get_current_user

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
    from src.core.webui.routes.dashboard import router as dashboard_router
    from src.core.webui.routes.vdot import router as vdot_router
    from src.core.webui.routes.training_load import router as training_load_router
    from src.core.webui.routes.activities import router as activities_router
    from src.core.webui.routes.body_signal import router as body_signal_router

    app.include_router(dashboard_router, prefix="/api", tags=["dashboard"])
    app.include_router(vdot_router, prefix="/api", tags=["vdot"])
    app.include_router(training_load_router, prefix="/api", tags=["training-load"])
    app.include_router(activities_router, prefix="/api", tags=["activities"])
    app.include_router(body_signal_router, prefix="/api", tags=["body-signal"])

    _app_instance = app
    return app
```

- [ ] **Step 5: 创建路由占位文件（使应用工厂可导入）**

创建 `src/core/webui/routes/dashboard.py`：

```python
"""Dashboard 汇总 API 路由"""

from fastapi import APIRouter

router = APIRouter()
```

创建 `src/core/webui/routes/vdot.py`：

```python
"""VDOT 趋势 API 路由"""

from fastapi import APIRouter

router = APIRouter()
```

创建 `src/core/webui/routes/training_load.py`：

```python
"""训练负荷 API 路由"""

from fastapi import APIRouter

router = APIRouter()

```

创建 `src/core/webui/routes/activities.py`：

```python
"""活动列表与详情 API 路由"""

from fastapi import APIRouter

router = APIRouter()
```

创建 `src/core/webui/routes/body_signal.py`：

```python
"""身体信号 API 路由"""

from fastapi import APIRouter

router = APIRouter()
```

- [ ] **Step 6: 运行测试确认通过**

Run: `uv run pytest tests/unit/core/webui/test_app.py -v`
Expected: 全部 PASS

- [ ] **Step 7: Commit**

```bash
git add src/core/webui/app.py src/core/webui/routes/__init__.py src/core/webui/routes/dashboard.py src/core/webui/routes/vdot.py src/core/webui/routes/training_load.py src/core/webui/routes/activities.py src/core/webui/routes/body_signal.py tests/unit/core/webui/test_app.py
git commit -m "feat(webui): add FastAPI app factory with health check and token endpoints"
```

---

## Task 5: Dashboard API (T05)

**Files:**
- Modify: `src/core/webui/routes/dashboard.py`
- Create: `tests/unit/core/webui/test_routes_dashboard.py`

- [ ] **Step 1: 编写 Dashboard API 的失败测试**

创建 `tests/unit/core/webui/test_routes_dashboard.py`：

```python
"""Dashboard API 路由单元测试"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.core.webui.app import create_app
from src.core.webui.auth import create_access_token


@pytest.fixture
def mock_context() -> MagicMock:
    context = MagicMock()
    context.config.get_webui_config.return_value = {
        "enabled": True,
        "host": "127.0.0.1",
        "port": 18791,
        "cors_origins": [],
        "token_secret": "test-secret",
        "token_ttl_s": 86400,
    }
    context.analytics.get_training_load.return_value = {
        "atl": 45.0,
        "ctl": 55.0,
        "tsb": 10.0,
        "fitness_status": "恢复良好",
        "training_advice": "当前体能充沛",
        "days_analyzed": 42,
        "runs_count": 15,
    }
    context.analytics.get_vdot_trend.return_value = []
    context.session_repo.get_recent_sessions.return_value = []
    context.body_signal_engine.get_daily_summary.return_value = MagicMock(
        to_dict=lambda: {
            "recovery_status": "good",
            "fatigue_score": 20.0,
            "data_quality": "sufficient",
            "daily_summary": "今日状态良好",
            "training_advice": "可以进行训练",
            "alerts": [],
        }
    )
    return context


@pytest.fixture
def client(mock_context: MagicMock) -> TestClient:
    app = create_app(context=mock_context)
    return TestClient(app)


@pytest.fixture
def auth_headers() -> dict[str, str]:
    token = create_access_token(secret="test-secret", ttl_seconds=3600)
    return {"Authorization": f"Bearer {token}"}


class TestDashboardEndpoint:
    def test_get_dashboard_returns_200(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """Dashboard 端点返回 200"""
        response = client.get("/api/dashboard", headers=auth_headers)
        assert response.status_code == 200

    def test_dashboard_contains_training_load(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """Dashboard 包含训练负荷数据"""
        response = client.get("/api/dashboard", headers=auth_headers)
        data = response.json()
        assert "training_load" in data
        assert data["training_load"]["atl"] == 45.0
        assert data["training_load"]["ctl"] == 55.0

    def test_dashboard_contains_body_signal(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """Dashboard 包含身体信号数据"""
        response = client.get("/api/dashboard", headers=auth_headers)
        data = response.json()
        assert "body_signal" in data
        assert data["body_signal"]["fatigue_score"] == 20.0

    def test_dashboard_requires_auth(self, client: TestClient) -> None:
        """Dashboard 端点需要认证"""
        response = client.get("/api/dashboard")
        assert response.status_code == 401
```

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/unit/core/webui/test_routes_dashboard.py -v`
Expected: FAIL - Dashboard 端点返回 404 或缺少数据

- [ ] **Step 3: 实现 Dashboard API 路由**

修改 `src/core/webui/routes/dashboard.py`：

```python
"""Dashboard 汇总 API 路由 (v0.28.0)

提供 Dashboard 页面所需的汇总数据，一次性返回训练负荷、身体信号等关键指标。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from starlette.concurrency import run_in_threadpool

from src.core.webui.auth import get_current_user

router = APIRouter()


def _get_dashboard_data() -> dict[str, Any]:
    """同步获取 Dashboard 汇总数据"""
    from src.core.base.context import get_context

    context = get_context()

    # 训练负荷
    training_load = context.analytics.get_training_load(days=42)

    # 身体信号
    body_signal_summary = context.body_signal_engine.get_daily_summary()

    return {
        "training_load": training_load,
        "body_signal": body_signal_summary.to_dict(),
    }


@router.get("/dashboard")
async def get_dashboard(user: str = Depends(get_current_user)) -> dict[str, Any]:
    """获取 Dashboard 汇总数据

    返回训练负荷、身体信号等关键指标的汇总信息。
    """
    return await run_in_threadpool(_get_dashboard_data)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `uv run pytest tests/unit/core/webui/test_routes_dashboard.py -v`
Expected: 全部 PASS

- [ ] **Step 5: Commit**

```bash
git add src/core/webui/routes/dashboard.py tests/unit/core/webui/test_routes_dashboard.py
git commit -m "feat(webui): add dashboard API endpoint"
```

---

## Task 6: VDOT 趋势 API (T06)

**Files:**
- Modify: `src/core/webui/routes/vdot.py`
- Create: `tests/unit/core/webui/test_routes_vdot.py`

- [ ] **Step 1: 编写 VDOT 趋势 API 的失败测试**

创建 `tests/unit/core/webui/test_routes_vdot.py`：

```python
"""VDOT 趋势 API 路由单元测试"""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from src.core.models.analytics import VdotTrendItem
from src.core.webui.app import create_app
from src.core.webui.auth import create_access_token


@pytest.fixture
def mock_context() -> MagicMock:
    context = MagicMock()
    context.config.get_webui_config.return_value = {
        "enabled": True,
        "host": "127.0.0.1",
        "port": 18791,
        "cors_origins": [],
        "token_secret": "test-secret",
        "token_ttl_s": 86400,
    }
    context.analytics.get_vdot_trend.return_value = [
        VdotTrendItem(date="2024-01-15", vdot=42.5, distance=5000.0, duration=1500.0),
        VdotTrendItem(date="2024-01-20", vdot=43.1, distance=8000.0, duration=2400.0),
    ]
    return context


@pytest.fixture
def client(mock_context: MagicMock) -> TestClient:
    app = create_app(context=mock_context)
    return TestClient(app)


@pytest.fixture
def auth_headers() -> dict[str, str]:
    token = create_access_token(secret="test-secret", ttl_seconds=3600)
    return {"Authorization": f"Bearer {token}"}


class TestVdotTrendEndpoint:
    def test_get_vdot_trend_returns_200(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/vdot/trend", headers=auth_headers)
        assert response.status_code == 200

    def test_vdot_trend_returns_list(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/vdot/trend", headers=auth_headers)
        data = response.json()
        assert "items" in data
        assert len(data["items"]) == 2
        assert data["items"][0]["date"] == "2024-01-15"
        assert data["items"][0]["vdot"] == 42.5

    def test_vdot_trend_with_days_param(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/vdot/trend?days=90", headers=auth_headers)
        assert response.status_code == 200
        mock_analytics = client.app.state.context.analytics
        mock_analytics.get_vdot_trend.assert_called_with(days=90)

    def test_vdot_trend_default_days(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/vdot/trend", headers=auth_headers)
        assert response.status_code == 200
        mock_analytics = client.app.state.context.analytics
        mock_analytics.get_vdot_trend.assert_called_with(days=30)

    def test_vdot_trend_requires_auth(self, client: TestClient) -> None:
        response = client.get("/api/vdot/trend")
        assert response.status_code == 401
```

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/unit/core/webui/test_routes_vdot.py -v`
Expected: FAIL

- [ ] **Step 3: 实现 VDOT 趋势 API 路由**

修改 `src/core/webui/routes/vdot.py`：

```python
"""VDOT 趋势 API 路由 (v0.28.0)

提供 VDOT 趋势数据接口，支持按天数查询。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from starlette.concurrency import run_in_threadpool

from src.core.webui.auth import get_current_user

router = APIRouter()


def _get_vdot_trend(days: int = 30) -> dict[str, Any]:
    """同步获取 VDOT 趋势数据"""
    from src.core.base.context import get_context

    context = get_context()
    trend_items = context.analytics.get_vdot_trend(days=days)
    return {
        "items": [item.to_dict() for item in trend_items],
        "days": days,
        "count": len(trend_items),
    }


@router.get("/vdot/trend")
async def get_vdot_trend(
    days: int = Query(default=30, ge=1, le=365, description="查询天数"),
    user: str = Depends(get_current_user),
) -> dict[str, Any]:
    """获取 VDOT 趋势数据

    Args:
        days: 查询天数，默认 30 天，范围 1-365

    Returns:
        VDOT 趋势数据列表
    """
    return await run_in_threadpool(_get_vdot_trend, days)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `uv run pytest tests/unit/core/webui/test_routes_vdot.py -v`
Expected: 全部 PASS

- [ ] **Step 5: Commit**

```bash
git add src/core/webui/routes/vdot.py tests/unit/core/webui/test_routes_vdot.py
git commit -m "feat(webui): add VDOT trend API endpoint"
```

---

## Task 7: 训练负荷 API (T07)

**Files:**
- Modify: `src/core/webui/routes/training_load.py`
- Create: `tests/unit/core/webui/test_routes_training_load.py`

- [ ] **Step 1: 编写训练负荷 API 的失败测试**

创建 `tests/unit/core/webui/test_routes_training_load.py`：

```python
"""训练负荷 API 路由单元测试"""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from src.core.webui.app import create_app
from src.core.webui.auth import create_access_token


@pytest.fixture
def mock_context() -> MagicMock:
    context = MagicMock()
    context.config.get_webui_config.return_value = {
        "enabled": True,
        "host": "127.0.0.1",
        "port": 18791,
        "cors_origins": [],
        "token_secret": "test-secret",
        "token_ttl_s": 86400,
    }
    context.analytics.get_training_load.return_value = {
        "atl": 50.0,
        "ctl": 60.0,
        "tsb": 10.0,
        "fitness_status": "恢复良好",
        "training_advice": "体能充沛",
        "days_analyzed": 42,
        "runs_count": 20,
    }
    context.analytics.get_training_load_trend.return_value = {
        "trend_data": [
            {"date": "2024-01-15", "tss": 85.0, "atl": 48.0, "ctl": 55.0, "tsb": 7.0},
            {"date": "2024-01-16", "tss": 0.0, "atl": 42.0, "ctl": 55.5, "tsb": 13.5},
        ],
        "summary": {
            "current_atl": 50.0,
            "current_ctl": 60.0,
            "current_tsb": 10.0,
            "status": "恢复良好",
            "recommendation": "体能充沛",
        },
        "days_analyzed": 42,
        "total_runs": 20,
    }
    return context


@pytest.fixture
def client(mock_context: MagicMock) -> TestClient:
    app = create_app(context=mock_context)
    return TestClient(app)


@pytest.fixture
def auth_headers() -> dict[str, str]:
    token = create_access_token(secret="test-secret", ttl_seconds=3600)
    return {"Authorization": f"Bearer {token}"}


class TestTrainingLoadEndpoint:
    def test_get_training_load_returns_200(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/training-load", headers=auth_headers)
        assert response.status_code == 200

    def test_training_load_contains_atl_ctl_tsb(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/training-load", headers=auth_headers)
        data = response.json()
        assert data["atl"] == 50.0
        assert data["ctl"] == 60.0
        assert data["tsb"] == 10.0

    def test_training_load_with_days_param(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/training-load?days=90", headers=auth_headers)
        assert response.status_code == 200

    def test_training_load_requires_auth(self, client: TestClient) -> None:
        response = client.get("/api/training-load")
        assert response.status_code == 401


class TestTrainingLoadTrendEndpoint:
    def test_get_training_load_trend_returns_200(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/training-load/trend", headers=auth_headers)
        assert response.status_code == 200

    def test_trend_contains_trend_data_and_summary(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/training-load/trend", headers=auth_headers)
        data = response.json()
        assert "trend_data" in data
        assert "summary" in data
        assert len(data["trend_data"]) == 2

    def test_trend_with_days_param(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/training-load/trend?days=60", headers=auth_headers)
        assert response.status_code == 200
```

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/unit/core/webui/test_routes_training_load.py -v`
Expected: FAIL

- [ ] **Step 3: 实现训练负荷 API 路由**

修改 `src/core/webui/routes/training_load.py`：

```python
"""训练负荷 API 路由 (v0.28.0)

提供训练负荷（ATL/CTL/TSB）和训练负荷趋势数据接口。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from starlette.concurrency import run_in_threadpool

from src.core.webui.auth import get_current_user

router = APIRouter()


def _get_training_load(days: int = 42) -> dict[str, Any]:
    """同步获取训练负荷数据"""
    from src.core.base.context import get_context

    context = get_context()
    return context.analytics.get_training_load(days=days)


def _get_training_load_trend(days: int = 90) -> dict[str, Any]:
    """同步获取训练负荷趋势数据"""
    from src.core.base.context import get_context

    context = get_context()
    return context.analytics.get_training_load_trend(days=days)


@router.get("/training-load")
async def get_training_load(
    days: int = Query(default=42, ge=7, le=365, description="分析天数"),
    user: str = Depends(get_current_user),
) -> dict[str, Any]:
    """获取训练负荷（ATL/CTL/TSB）

    Args:
        days: 分析天数，默认 42 天

    Returns:
        训练负荷数据，包含 atl/ctl/tsb/fitness_status/training_advice
    """
    return await run_in_threadpool(_get_training_load, days)


@router.get("/training-load/trend")
async def get_training_load_trend(
    days: int = Query(default=90, ge=7, le=365, description="趋势天数"),
    user: str = Depends(get_current_user),
) -> dict[str, Any]:
    """获取训练负荷趋势（每日 TSS/ATL/CTL/TSB）

    Args:
        days: 趋势天数，默认 90 天

    Returns:
        训练负荷趋势数据，包含 trend_data/summary
    """
    return await run_in_threadpool(_get_training_load_trend, days)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `uv run pytest tests/unit/core/webui/test_routes_training_load.py -v`
Expected: 全部 PASS

- [ ] **Step 5: Commit**

```bash
git add src/core/webui/routes/training_load.py tests/unit/core/webui/test_routes_training_load.py
git commit -m "feat(webui): add training load and trend API endpoints"
```

---

## Task 8: 活动列表 API (T08)

**Files:**
- Modify: `src/core/webui/routes/activities.py`
- Create: `tests/unit/core/webui/test_routes_activities.py`

- [ ] **Step 1: 编写活动列表 API 的失败测试**

创建 `tests/unit/core/webui/test_routes_activities.py`：

```python
"""活动列表与详情 API 路由单元测试"""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from src.core.storage.session_repository import SessionDetail
from src.core.webui.app import create_app
from src.core.webui.auth import create_access_token


@pytest.fixture
def mock_context() -> MagicMock:
    context = MagicMock()
    context.config.get_webui_config.return_value = {
        "enabled": True,
        "host": "127.0.0.1",
        "port": 18791,
        "cors_origins": [],
        "token_secret": "test-secret",
        "token_ttl_s": 86400,
    }
    context.session_repo.get_recent_sessions.return_value = [
        SessionDetail(
            timestamp="2024-01-20T07:30:00",
            distance_km=8.02,
            duration_min=42.5,
            avg_pace_sec_km=319.4,
            avg_heart_rate=155.0,
            distance_m=8020.0,
            duration_s=2550.0,
            max_heart_rate=175.0,
            calories=520.0,
        ),
        SessionDetail(
            timestamp="2024-01-18T06:00:00",
            distance_km=5.01,
            duration_min=28.3,
            avg_pace_sec_km=338.7,
            avg_heart_rate=148.0,
            distance_m=5010.0,
            duration_s=1698.0,
            max_heart_rate=168.0,
            calories=340.0,
        ),
    ]
    return context


@pytest.fixture
def client(mock_context: MagicMock) -> TestClient:
    app = create_app(context=mock_context)
    return TestClient(app)


@pytest.fixture
def auth_headers() -> dict[str, str]:
    token = create_access_token(secret="test-secret", ttl_seconds=3600)
    return {"Authorization": f"Bearer {token}"}


class TestActivitiesListEndpoint:
    def test_get_activities_returns_200(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/activities", headers=auth_headers)
        assert response.status_code == 200

    def test_activities_returns_list(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/activities", headers=auth_headers)
        data = response.json()
        assert "items" in data
        assert len(data["items"]) == 2
        assert data["items"][0]["distance_km"] == 8.02
        assert data["items"][0]["avg_heart_rate"] == 155.0

    def test_activities_with_limit_param(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/activities?limit=5", headers=auth_headers)
        assert response.status_code == 200
        client.app.state.context.session_repo.get_recent_sessions.assert_called_with(limit=5)

    def test_activities_default_limit(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/activities", headers=auth_headers)
        assert response.status_code == 200
        client.app.state.context.session_repo.get_recent_sessions.assert_called_with(limit=20)

    def test_activities_requires_auth(self, client: TestClient) -> None:
        response = client.get("/api/activities")
        assert response.status_code == 401
```

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/unit/core/webui/test_routes_activities.py -v`
Expected: FAIL

- [ ] **Step 3: 实现活动列表 API 路由**

修改 `src/core/webui/routes/activities.py`：

```python
"""活动列表与详情 API 路由 (v0.28.0)

提供跑步活动列表查询接口。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from starlette.concurrency import run_in_threadpool

from src.core.webui.auth import get_current_user

router = APIRouter()


def _get_activities(limit: int = 20) -> dict[str, Any]:
    """同步获取最近活动列表"""
    from src.core.base.context import get_context

    context = get_context()
    sessions = context.session_repo.get_recent_sessions(limit=limit)
    return {
        "items": [s.to_dict() for s in sessions],
        "count": len(sessions),
        "limit": limit,
    }


@router.get("/activities")
async def get_activities(
    limit: int = Query(default=20, ge=1, le=100, description="返回数量限制"),
    user: str = Depends(get_current_user),
) -> dict[str, Any]:
    """获取最近跑步活动列表

    Args:
        limit: 返回数量限制，默认 20，范围 1-100

    Returns:
        活动列表数据
    """
    return await run_in_threadpool(_get_activities, limit)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `uv run pytest tests/unit/core/webui/test_routes_activities.py -v`
Expected: 全部 PASS

- [ ] **Step 5: Commit**

```bash
git add src/core/webui/routes/activities.py tests/unit/core/webui/test_routes_activities.py
git commit -m "feat(webui): add activities list API endpoint"
```

---

## Task 9: 活动详情 API (T09)

**Files:**
- Modify: `src/core/webui/routes/activities.py`
- Modify: `tests/unit/core/webui/test_routes_activities.py`

- [ ] **Step 1: 编写活动详情 API 的失败测试**

在 `tests/unit/core/webui/test_routes_activities.py` 中新增测试类：

```python
class TestActivityDetailEndpoint:
    def test_get_activity_detail_returns_200(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """活动详情端点返回 200"""
        # 配置 mock：get_recent_sessions 返回包含目标 session 的列表
        mock_session = SessionDetail(
            timestamp="2024-01-20T07:30:00",
            distance_km=8.02,
            duration_min=42.5,
            avg_pace_sec_km=319.4,
            avg_heart_rate=155.0,
            distance_m=8020.0,
            duration_s=2550.0,
            max_heart_rate=175.0,
            calories=520.0,
        )
        client.app.state.context.session_repo.get_recent_sessions.return_value = [
            mock_session
        ]
        response = client.get("/api/activities/0", headers=auth_headers)
        assert response.status_code == 200

    def test_activity_detail_contains_full_data(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """活动详情包含完整数据"""
        mock_session = SessionDetail(
            timestamp="2024-01-20T07:30:00",
            distance_km=8.02,
            duration_min=42.5,
            avg_pace_sec_km=319.4,
            avg_heart_rate=155.0,
            distance_m=8020.0,
            duration_s=2550.0,
            max_heart_rate=175.0,
            calories=520.0,
        )
        client.app.state.context.session_repo.get_recent_sessions.return_value = [
            mock_session
        ]
        response = client.get("/api/activities/0", headers=auth_headers)
        data = response.json()
        assert data["distance_km"] == 8.02
        assert data["max_heart_rate"] == 175.0
        assert data["calories"] == 520.0

    def test_activity_detail_out_of_range_returns_404(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """索引超出范围返回 404"""
        client.app.state.context.session_repo.get_recent_sessions.return_value = []
        response = client.get("/api/activities/0", headers=auth_headers)
        assert response.status_code == 404
```

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/unit/core/webui/test_routes_activities.py::TestActivityDetailEndpoint -v`
Expected: FAIL - 404 路由不存在

- [ ] **Step 3: 在活动路由中新增详情端点**

在 `src/core/webui/routes/activities.py` 中新增：

```python
def _get_activity_detail(index: int) -> dict[str, Any]:
    """同步获取单个活动详情"""
    from src.core.base.context import get_context

    context = get_context()
    # 获取足够多的 session 以支持索引
    sessions = context.session_repo.get_recent_sessions(limit=100)
    if index < 0 or index >= len(sessions):
        return None
    return sessions[index].to_dict()


@router.get("/activities/{index}")
async def get_activity_detail(
    index: int,
    user: str = Depends(get_current_user),
) -> dict[str, Any]:
    """获取单个跑步活动详情

    Args:
        index: 活动索引（按时间降序，0 为最近一次）

    Returns:
        活动详情数据

    Raises:
        HTTPException: 索引超出范围时返回 404
    """
    result = await run_in_threadpool(_get_activity_detail, index)
    if result is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="活动不存在")
    return result
```

- [ ] **Step 4: 运行测试确认通过**

Run: `uv run pytest tests/unit/core/webui/test_routes_activities.py -v`
Expected: 全部 PASS

- [ ] **Step 5: Commit**

```bash
git add src/core/webui/routes/activities.py tests/unit/core/webui/test_routes_activities.py
git commit -m "feat(webui): add activity detail API endpoint"
```

---

## Task 10: 身体信号 API (T10)

**Files:**
- Modify: `src/core/webui/routes/body_signal.py`
- Create: `tests/unit/core/webui/test_routes_body_signal.py`

- [ ] **Step 1: 编写身体信号 API 的失败测试**

创建 `tests/unit/core/webui/test_routes_body_signal.py`：

```python
"""身体信号 API 路由单元测试"""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from src.core.body_signal.models import (
    BodySignalAlert,
    BodySignalSummary,
    DataQuality,
)
from src.core.models.recovery import RecoveryStatus
from src.core.webui.app import create_app
from src.core.webui.auth import create_access_token


@pytest.fixture
def mock_context() -> MagicMock:
    context = MagicMock()
    context.config.get_webui_config.return_value = {
        "enabled": True,
        "host": "127.0.0.1",
        "port": 18791,
        "cors_origins": [],
        "token_secret": "test-secret",
        "token_ttl_s": 86400,
    }
    daily_summary = BodySignalSummary(
        recovery_status=RecoveryStatus.GOOD,
        fatigue_score=25.0,
        data_quality=DataQuality.SUFFICIENT,
        daily_summary="今日状态良好，可以进行训练",
        training_advice="建议进行中等强度训练",
        alerts=[
            BodySignalAlert(
                alert_type="high_fatigue",
                severity="warning",
                message="连续高强度训练3天",
            )
        ],
    )
    context.body_signal_engine.get_daily_summary.return_value = daily_summary
    context.body_signal_engine.get_weekly_summary.return_value = BodySignalSummary(
        recovery_status=RecoveryStatus.GOOD,
        fatigue_score=30.0,
        data_quality=DataQuality.SUFFICIENT,
        daily_summary="本周训练负荷适中",
        training_advice="保持当前训练节奏",
        alerts=[],
    )
    context.body_signal_engine.check_alerts.return_value = [
        BodySignalAlert(
            alert_type="high_fatigue",
            severity="warning",
            message="连续高强度训练3天",
        )
    ]
    return context


@pytest.fixture
def client(mock_context: MagicMock) -> TestClient:
    app = create_app(context=mock_context)
    return TestClient(app)


@pytest.fixture
def auth_headers() -> dict[str, str]:
    token = create_access_token(secret="test-secret", ttl_seconds=3600)
    return {"Authorization": f"Bearer {token}"}


class TestBodySignalDailyEndpoint:
    def test_get_daily_summary_returns_200(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/body-signal/daily", headers=auth_headers)
        assert response.status_code == 200

    def test_daily_summary_contains_fields(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/body-signal/daily", headers=auth_headers)
        data = response.json()
        assert data["recovery_status"] == "good"
        assert data["fatigue_score"] == 25.0
        assert len(data["alerts"]) == 1


class TestBodySignalWeeklyEndpoint:
    def test_get_weekly_summary_returns_200(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/body-signal/weekly", headers=auth_headers)
        assert response.status_code == 200

    def test_weekly_summary_contains_fields(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/body-signal/weekly", headers=auth_headers)
        data = response.json()
        assert data["fatigue_score"] == 30.0


class TestBodySignalAlertsEndpoint:
    def test_get_alerts_returns_200(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/body-signal/alerts", headers=auth_headers)
        assert response.status_code == 200

    def test_alerts_returns_list(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/body-signal/alerts", headers=auth_headers)
        data = response.json()
        assert "alerts" in data
        assert len(data["alerts"]) == 1
        assert data["alerts"][0]["alert_type"] == "high_fatigue"


class TestBodySignalAuthRequired:
    def test_daily_requires_auth(self, client: TestClient) -> None:
        response = client.get("/api/body-signal/daily")
        assert response.status_code == 401

    def test_weekly_requires_auth(self, client: TestClient) -> None:
        response = client.get("/api/body-signal/weekly")
        assert response.status_code == 401

    def test_alerts_requires_auth(self, client: TestClient) -> None:
        response = client.get("/api/body-signal/alerts")
        assert response.status_code == 401
```

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/unit/core/webui/test_routes_body_signal.py -v`
Expected: FAIL

- [ ] **Step 3: 实现身体信号 API 路由**

修改 `src/core/webui/routes/body_signal.py`：

```python
"""身体信号 API 路由 (v0.28.0)

提供身体信号（恢复状态、疲劳度、预警）数据接口。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from starlette.concurrency import run_in_threadpool

from src.core.webui.auth import get_current_user

router = APIRouter()


def _get_daily_summary() -> dict[str, Any]:
    """同步获取每日身体信号摘要"""
    from src.core.base.context import get_context

    context = get_context()
    summary = context.body_signal_engine.get_daily_summary()
    return summary.to_dict()


def _get_weekly_summary() -> dict[str, Any]:
    """同步获取每周身体信号摘要"""
    from src.core.base.context import get_context

    context = get_context()
    summary = context.body_signal_engine.get_weekly_summary()
    return summary.to_dict()


def _get_alerts() -> dict[str, Any]:
    """同步获取身体信号预警"""
    from src.core.base.context import get_context

    context = get_context()
    alerts = context.body_signal_engine.check_alerts()
    return {
        "alerts": [a.to_dict() for a in alerts],
        "count": len(alerts),
    }


@router.get("/body-signal/daily")
async def get_daily_summary(
    user: str = Depends(get_current_user),
) -> dict[str, Any]:
    """获取每日身体信号摘要

    返回恢复状态、疲劳度、训练建议和预警信息。
    """
    return await run_in_threadpool(_get_daily_summary)


@router.get("/body-signal/weekly")
async def get_weekly_summary(
    user: str = Depends(get_current_user),
) -> dict[str, Any]:
    """获取每周身体信号摘要"""
    return await run_in_threadpool(_get_weekly_summary)


@router.get("/body-signal/alerts")
async def get_alerts(
    user: str = Depends(get_current_user),
) -> dict[str, Any]:
    """获取身体信号预警列表"""
    return await run_in_threadpool(_get_alerts)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `uv run pytest tests/unit/core/webui/test_routes_body_signal.py -v`
Expected: 全部 PASS

- [ ] **Step 5: Commit**

```bash
git add src/core/webui/routes/body_signal.py tests/unit/core/webui/test_routes_body_signal.py
git commit -m "feat(webui): add body signal API endpoints"
```

---

## Task 11: uvicorn Server 封装 (T21 前置)

**Files:**
- Create: `src/core/webui/server.py`

- [ ] **Step 1: 实现 uvicorn Server 封装**

创建 `src/core/webui/server.py`：

```python
"""uvicorn Server 封装 (v0.28.0)

提供 FastAPI 服务的启动和停止控制。
约束 C-01: 必须使用 uvicorn.Server(config).serve()，禁止 uvicorn.run()。
"""

from __future__ import annotations

import logging
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
    port = webui_config.get("port", 18791)

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
```

- [ ] **Step 2: Commit**

```bash
git add src/core/webui/server.py
git commit -m "feat(webui): add uvicorn server wrapper"
```

---

## Task 12: Gateway 集成启动 (T21)

**Files:**
- Modify: `src/cli/commands/gateway.py:238-512`

- [ ] **Step 1: 在 Gateway start 命令中集成 FastAPI 启动**

在 `src/cli/commands/gateway.py` 的 `start()` 函数中，修改 `run()` 协程，将 FastAPI 服务加入 `asyncio.gather()`。

在 `start()` 函数中，`channels = ChannelManager(...)` 之后（约第380行），新增 WebUI 配置检查和 Server 创建：

```python
    # v0.28.0: WebUI FastAPI 后端
    fastapi_server = None
    if webui and context is not None:
        webui_config = context.config.get_webui_config()
        if webui_config.get("enabled", False):
            from src.core.webui.server import create_server

            fastapi_server = create_server(context)
            api_host = webui_config.get("host", "127.0.0.1")
            api_port = webui_config.get("port", 18791)
            console.print(
                f"[green]✓[/green] WebUI API: http://{api_host}:{api_port}/api/docs"
            )
```

修改 `run()` 协程，将 `fastapi_server.serve()` 加入 `asyncio.gather()`：

```python
    async def run():
        try:
            await cron.start()
            await heartbeat.start()

            gather_tasks = [
                agent.run(),
                channels.start_all(),
            ]
            if fastapi_server is not None:
                gather_tasks.append(fastapi_server.serve())

            await asyncio.gather(*gather_tasks)
        except KeyboardInterrupt:
            console.print("\n[yellow]正在关闭...[/yellow]")
        finally:
            if fastapi_server is not None:
                fastapi_server.should_exit = True
            await agent.close_mcp()
            heartbeat.stop()
            integration.shutdown()
            agent.stop()
            await channels.stop_all()
```

- [ ] **Step 2: 在 WebUI 交互信息区块中新增 API 信息**

在 `start()` 函数中，WebUI 交互信息区块（约第476-490行），新增 API 文档链接：

在 `console.print(f"  - 获取Token: curl http://{ws_host}:{ws_port}{token_path}")` 之后新增：

```python
        # v0.28.0: WebUI API 文档
        if fastapi_server is not None:
            webui_config = context.config.get_webui_config()
            api_host = webui_config.get("host", "127.0.0.1")
            api_port = webui_config.get("port", 18791)
            console.print(f"  - API文档: http://{api_host}:{api_port}/api/docs")
```

- [ ] **Step 3: 更新 config.example.json 中 webui.enabled 默认值**

确认 `config.example.json` 中 webui 配置节的 `enabled` 为 `false`（已在 Task 1 中设置）。

- [ ] **Step 4: 运行 lint 检查**

Run: `uv run ruff check src/cli/commands/gateway.py src/core/webui/`
Expected: 无错误

- [ ] **Step 5: Commit**

```bash
git add src/cli/commands/gateway.py
git commit -m "feat(webui): integrate FastAPI server into gateway startup"
```

---

## Task 13: 全量测试与验证

**Files:**
- All modified/created files

- [ ] **Step 1: 运行全部 WebUI 相关单元测试**

Run: `uv run pytest tests/unit/core/webui/ tests/unit/core/config/test_webui_config.py -v`
Expected: 全部 PASS

- [ ] **Step 2: 运行 ruff 格式化和检查**

Run: `uv run ruff format src/core/webui/ src/cli/commands/gateway.py src/core/config/manager.py src/core/config/schema.py && uv run ruff check src/core/webui/ src/cli/commands/gateway.py src/core/config/manager.py src/core/config/schema.py`
Expected: 无错误

- [ ] **Step 3: 运行 mypy 类型检查**

Run: `uv run mypy src/core/webui/ --ignore-missing-imports`
Expected: 无错误

- [ ] **Step 4: 运行现有测试确保无回归**

Run: `uv run pytest tests/unit/ -v --timeout=60 -x -q`
Expected: 全部 PASS

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "chore(webui): final verification and cleanup"
```

---

## Self-Review Checklist

### 1. Spec Coverage

| 任务清单项 | 对应 Task | 状态 |
|-----------|----------|------|
| T01: 项目骨架与依赖配置 | Task 1 | ✅ |
| T02: FastAPI应用工厂 | Task 4 | ✅ |
| T03: 认证中间件 | Task 3 | ✅ |
| T04: WebUI配置管理 | Task 2 | ✅ |
| T05: Dashboard API | Task 5 | ✅ |
| T06: VDOT趋势API | Task 6 | ✅ |
| T07: 训练负荷API | Task 7 | ✅ |
| T08: 活动列表API | Task 8 | ✅ |
| T09: 活动详情API | Task 9 | ✅ |
| T10: 身体信号API | Task 10 | ✅ |
| T21: Gateway集成启动 | Task 11 + Task 12 | ✅ |

### 2. Placeholder Scan

- 无 TBD / TODO / implement later
- 无 "add appropriate error handling" 等模糊描述
- 所有代码步骤包含完整实现
- 所有测试包含完整测试代码

### 3. Type Consistency

- `get_webui_config()` 返回 `dict[str, Any]` — 与 `get_websocket_config()` 一致
- `create_access_token()` 签名：`secret: str, ttl_seconds: int, subject: str` → `str`
- `get_current_user()` 返回 `str`（subject）
- 所有路由使用 `run_in_threadpool()` 包装同步核心方法
- `VdotTrendItem.to_dict()` 返回 `{"date", "vdot", "distance", "duration"}`
- `SessionDetail.to_dict()` 返回 `{"timestamp", "distance_km", "duration_min", ...}`
- `BodySignalSummary.to_dict()` 返回 `{"recovery_status", "fatigue_score", ...}`
- C-01 约束：`uvicorn.Server(config).serve()` 而非 `uvicorn.run()`
