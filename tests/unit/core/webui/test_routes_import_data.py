"""数据导入 API 路由单元测试 (v0.34.0)"""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from src.core.webui.app import create_app


@pytest.fixture
def mock_importer() -> MagicMock:
    """模拟 ImportService，import_file 返回标准 dict"""
    importer = MagicMock()

    def _import_file(filepath, force=False):
        # 根据文件名返回不同状态，便于测试
        name = filepath.name
        if "skip" in name:
            return {"status": "skipped", "message": "文件已存在"}
        if "error" in name:
            return {"status": "error", "message": "解析失败"}
        return {"status": "added", "message": "导入成功", "fingerprint": "abc123"}

    importer.import_file.side_effect = _import_file
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
def client(mock_context: MagicMock) -> TestClient:
    app = create_app(context=mock_context)
    return TestClient(app)


class TestImportEndpointAuth:
    """认证测试"""

    def test_requires_auth(self, client: TestClient) -> None:
        """未认证返回 401"""
        response = client.post("/api/data/import")
        assert response.status_code == 401


class TestImportEndpointValidation:
    """请求阶段校验测试"""

    def test_reject_non_fit_file(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """非 .fit 文件返回 400"""
        response = client.post(
            "/api/data/import",
            headers=auth_headers,
            files={"files": ("test.txt", b"hello", "text/plain")},
        )
        assert response.status_code == 400
        assert "test.txt" in response.json()["detail"]

    def test_reject_too_many_files(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """超过 50 个文件返回 400"""
        files = [
            ("files", (f"run{i}.fit", b"fake", "application/octet-stream"))
            for i in range(51)
        ]
        response = client.post("/api/data/import", headers=auth_headers, files=files)
        assert response.status_code == 400


class TestImportEndpointSuccess:
    """正常导入测试"""

    def test_single_file_added(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        mock_importer: MagicMock,
    ) -> None:
        """单个 .fit 文件导入成功"""
        response = client.post(
            "/api/data/import",
            headers=auth_headers,
            files={
                "files": ("run1.fit", b"fake-fit-content", "application/octet-stream")
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["summary"] == {"total": 1, "added": 1, "skipped": 0, "errors": 0}
        assert data["results"][0]["filename"] == "run1.fit"
        assert data["results"][0]["status"] == "added"
        # 验证 importer 被调用，且 force 默认 False
        mock_importer.import_file.assert_called_once()
        call_kwargs = mock_importer.import_file.call_args
        assert call_kwargs.kwargs.get("force", False) is False

    def test_multiple_files_mixed_status(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        mock_importer: MagicMock,
    ) -> None:
        """多文件混合状态：added + skipped + error"""
        files = [
            ("files", ("run_added.fit", b"data", "application/octet-stream")),
            ("files", ("run_skip.fit", b"data", "application/octet-stream")),
            ("files", ("run_error.fit", b"data", "application/octet-stream")),
        ]
        response = client.post("/api/data/import", headers=auth_headers, files=files)
        assert response.status_code == 200
        data = response.json()
        assert data["summary"] == {"total": 3, "added": 1, "skipped": 1, "errors": 1}
        statuses = [r["status"] for r in data["results"]]
        assert "added" in statuses
        assert "skipped" in statuses
        assert "error" in statuses

    def test_force_param_passed_to_importer(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        mock_importer: MagicMock,
    ) -> None:
        """force=true 透传给 importer"""
        response = client.post(
            "/api/data/import?force=true",
            headers=auth_headers,
            files={"files": ("run1.fit", b"data", "application/octet-stream")},
        )
        assert response.status_code == 200
        call_kwargs = mock_importer.import_file.call_args
        assert call_kwargs.kwargs.get("force", False) is True
