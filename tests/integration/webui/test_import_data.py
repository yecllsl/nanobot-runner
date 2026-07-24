"""数据导入 API 集成测试 (v0.34.0)

使用真实 FastAPI app + mock ImportService，验证 API 层端到端流程：
- 路由正确注册
- 临时文件清理
- 错误隔离
- force 参数透传

注：真实 FIT 解析由 ImportService 单测覆盖，此处聚焦 API 层。
"""

import glob
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from src.core.webui.app import create_app
from src.core.webui.auth import create_access_token


@pytest.fixture
def mock_importer() -> MagicMock:
    """模拟 ImportService，记录所有调用"""
    importer = MagicMock()
    importer.import_file.return_value = {
        "status": "added",
        "message": "导入成功",
        "fingerprint": "test-fingerprint",
    }
    return importer


@pytest.fixture
def mock_context(mock_importer: MagicMock) -> MagicMock:
    context = MagicMock()
    context.config.get_webui_config.return_value = {
        "enabled": True,
        "host": "127.0.0.1",
        "port": 8766,
        "cors_origins": [],
        "token_secret": "test-secret",
        "token_ttl_s": 86400,
    }
    context.importer = mock_importer
    return context


@pytest.fixture
def integration_client(mock_context: MagicMock) -> TestClient:
    app = create_app(context=mock_context)
    return TestClient(app)


@pytest.fixture
def integration_auth_headers(integration_client: TestClient) -> dict[str, str]:
    secret = integration_client.app.state.webui_secret
    token = create_access_token(secret=secret, ttl_seconds=3600)
    return {"Authorization": f"Bearer {token}"}


class TestImportEndpointIntegration:
    """集成测试：真实 FastAPI app + mock ImportService"""

    def test_full_import_flow_end_to_end(
        self,
        integration_client: TestClient,
        integration_auth_headers: dict[str, str],
        mock_importer: MagicMock,
    ) -> None:
        """完整导入流程：上传 → 调 ImportService → 返回结果"""
        fit_content = b".FIT" + b"\x00" * 116  # 最小 FIT 文件占位
        response = integration_client.post(
            "/api/data/import",
            headers=integration_auth_headers,
            files={"files": ("test_run.fit", fit_content, "application/octet-stream")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["summary"]["total"] == 1
        assert data["summary"]["added"] == 1
        assert data["results"][0]["filename"] == "test_run.fit"
        assert data["results"][0]["status"] == "added"

        # 验证 ImportService 被调用
        mock_importer.import_file.assert_called_once()
        call_args = mock_importer.import_file.call_args
        # 验证传入的是 Path 对象
        assert isinstance(call_args.args[0], Path)
        assert call_args.args[0].name == "test_run.fit"

    def test_temp_files_cleaned_after_import(
        self,
        integration_client: TestClient,
        integration_auth_headers: dict[str, str],
    ) -> None:
        """NFR-D-26: 导入后临时文件清理"""
        fit_content = b".FIT" + b"\x00" * 116
        integration_client.post(
            "/api/data/import",
            headers=integration_auth_headers,
            files={
                "files": ("cleanup_test.fit", fit_content, "application/octet-stream")
            },
        )
        # 检查系统临时目录下无 nanobot_import_ 残留
        temp_dirs = glob.glob(str(Path(tempfile.gettempdir()) / "nanobot_import_*"))
        assert len(temp_dirs) == 0, f"临时目录未清理: {temp_dirs}"

    def test_temp_files_cleaned_on_error(
        self,
        integration_client: TestClient,
        integration_auth_headers: dict[str, str],
        mock_importer: MagicMock,
    ) -> None:
        """NFR-D-26: 即使 ImportService 抛异常，临时文件仍清理"""
        mock_importer.import_file.side_effect = Exception("模拟解析失败")
        fit_content = b".FIT" + b"\x00" * 116
        # 异常被 _import_files_sync 捕获记为 error，不传播到 500
        response = integration_client.post(
            "/api/data/import",
            headers=integration_auth_headers,
            files={"files": ("error_run.fit", fit_content, "application/octet-stream")},
        )
        # ImportService 异常应被捕获，记为 error 状态
        assert response.status_code == 200
        assert response.json()["results"][0]["status"] == "error"

        # 验证临时文件已清理
        temp_dirs = glob.glob(str(Path(tempfile.gettempdir()) / "nanobot_import_*"))
        assert len(temp_dirs) == 0, f"异常后临时目录未清理: {temp_dirs}"

    def test_error_isolation_between_files(
        self,
        integration_client: TestClient,
        integration_auth_headers: dict[str, str],
        mock_importer: MagicMock,
    ) -> None:
        """单文件失败不影响后续文件"""
        call_count = [0]

        def _side_effect(filepath, force=False):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("第一个文件失败")
            return {"status": "added", "message": "导入成功"}

        mock_importer.import_file.side_effect = _side_effect

        files = [
            ("files", ("fail.fit", b"data", "application/octet-stream")),
            ("files", ("ok.fit", b"data", "application/octet-stream")),
        ]
        response = integration_client.post(
            "/api/data/import", headers=integration_auth_headers, files=files
        )
        assert response.status_code == 200
        data = response.json()
        # 两个文件都处理了
        assert data["summary"]["total"] == 2
        assert data["summary"]["errors"] == 1
        assert data["summary"]["added"] == 1
