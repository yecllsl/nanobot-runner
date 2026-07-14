"""WebUI 测试共享 fixtures"""
import pytest
from fastapi.testclient import TestClient

from src.core.webui.auth import create_access_token


@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
    """生成认证头，使用与 app 一致的 token_secret"""
    secret = client.app.state.webui_secret
    token = create_access_token(secret=secret, ttl_seconds=3600)
    return {"Authorization": f"Bearer {token}"}
