"""uvicorn Server 封装单元测试"""

from unittest.mock import MagicMock, patch

import uvicorn

from src.core.webui.server import create_server


def _make_mock_context() -> MagicMock:
    """创建带 webui 配置的 Mock 上下文"""
    context = MagicMock()
    context.config.get_webui_config.return_value = {
        "enabled": True,
        "host": "127.0.0.1",
        "port": 8766,
        "cors_origins": ["http://localhost:8765"],
        "token_secret": "test-secret",
        "token_ttl_s": 86400,
    }
    return context


class TestCreateServer:
    def test_returns_uvicorn_server_instance(self) -> None:
        """create_server 返回 uvicorn.Server 实例"""
        mock_context = _make_mock_context()
        server = create_server(mock_context)
        assert isinstance(server, uvicorn.Server)

    def test_server_config_host_from_webui_config(self) -> None:
        """Server 配置使用 webui_config 中的 host"""
        mock_context = _make_mock_context()
        mock_context.config.get_webui_config.return_value["host"] = "0.0.0.0"
        server = create_server(mock_context)
        assert server.config.host == "0.0.0.0"

    def test_server_config_port_from_webui_config(self) -> None:
        """Server 配置使用 webui_config 中的 port"""
        mock_context = _make_mock_context()
        mock_context.config.get_webui_config.return_value["port"] = 9999
        server = create_server(mock_context)
        assert server.config.port == 9999

    def test_server_config_default_host(self) -> None:
        """host 缺失时使用默认值 127.0.0.1"""
        mock_context = _make_mock_context()
        webui_config = mock_context.config.get_webui_config.return_value
        del webui_config["host"]
        server = create_server(mock_context)
        assert server.config.host == "127.0.0.1"

    def test_server_config_default_port(self) -> None:
        """port 缺失时使用默认值 8766"""
        mock_context = _make_mock_context()
        webui_config = mock_context.config.get_webui_config.return_value
        del webui_config["port"]
        server = create_server(mock_context)
        assert server.config.port == 8766

    def test_server_config_log_level_warning(self) -> None:
        """Server 日志级别设置为 warning"""
        mock_context = _make_mock_context()
        server = create_server(mock_context)
        assert server.config.log_level == "warning"

    def test_server_config_access_log_disabled(self) -> None:
        """Server 访问日志已禁用"""
        mock_context = _make_mock_context()
        server = create_server(mock_context)
        assert server.config.access_log is False

    @patch("src.core.webui.app.create_app")
    def test_calls_create_app_with_context(self, mock_create_app: MagicMock) -> None:
        """create_server 调用 create_app 并传入 context"""
        mock_app = MagicMock()
        mock_create_app.return_value = mock_app
        mock_context = _make_mock_context()

        server = create_server(mock_context)

        mock_create_app.assert_called_once_with(context=mock_context)
        # 验证 app 被传入 uvicorn.Config
        assert server.config.app == mock_app

    def test_server_has_serve_method(self) -> None:
        """Server 实例具有 serve 协程方法，可与 asyncio.gather 配合"""
        mock_context = _make_mock_context()
        server = create_server(mock_context)
        assert hasattr(server, "serve")
        assert callable(server.serve)

    def test_server_has_should_exit_attribute(self) -> None:
        """Server 实例具有 should_exit 属性，可用于优雅关闭"""
        mock_context = _make_mock_context()
        server = create_server(mock_context)
        assert hasattr(server, "should_exit")
