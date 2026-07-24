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


class TestMaxBodySizeMiddleware:
    """ISSUE-01: 请求体大小限制测试"""

    def test_reject_oversized_multipart(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """超过 60MB 的 multipart 请求返回 413"""
        # 构造超大 Content-Length 头（不实际发送 60MB 数据）
        huge_content = b"x" * (61 * 1024 * 1024)
        response = client.post(
            "/api/data/import",
            headers={
                **auth_headers,
                "Content-Type": "multipart/form-data; boundary=----test",
                "Content-Length": str(len(huge_content) + 200),
            },
            content=huge_content,
        )
        assert response.status_code == 413
        assert response.json()["detail"]  # 错误消息非空

    def test_allow_normal_size_multipart(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """正常大小的 multipart 请求不被拦截"""
        response = client.post(
            "/api/data/import",
            headers=auth_headers,
            files={"files": ("run1.fit", b"data", "application/octet-stream")},
        )
        assert response.status_code == 200

    def test_non_multipart_request_unaffected(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """非 multipart 请求不受大小限制影响（如 GET /api/activities）"""
        response = client.get("/api/activities", headers=auth_headers)
        assert response.status_code == 200


class TestImportErrorIsolation:
    """错误隔离测试：单文件失败不影响其他文件（REV-01 补充）"""

    def test_oserror_on_write_isolated(self, mock_context: MagicMock) -> None:
        """临时文件写入 OSError 被记为 error，不中断后续文件"""
        from src.core.webui.routes.import_data import _import_files_sync

        # 第一个文件 read 抛 OSError，第二个文件正常
        broken = MagicMock()
        broken.filename = "broken.fit"
        broken.file.read.side_effect = OSError("disk full")

        normal = MagicMock()
        normal.filename = "normal.fit"
        normal.file.read.return_value = b"fit-data"

        results = _import_files_sync(mock_context, [broken, normal], force=False)

        assert results["summary"]["total"] == 2
        assert results["summary"]["errors"] == 1
        assert results["summary"]["added"] == 1
        # broken 文件记为 error 且消息精确
        broken_result = next(
            r for r in results["results"] if r["filename"] == "broken.fit"
        )
        assert broken_result["status"] == "error"
        assert "临时文件写入失败" in broken_result["message"]

    def test_none_filename_isolated(self, mock_context: MagicMock) -> None:
        """filename 为 None 被记为 error，不中断后续文件（REV-01 Blocker 修复覆盖）"""
        from src.core.webui.routes.import_data import _import_files_sync

        no_name = MagicMock()
        no_name.filename = None

        normal = MagicMock()
        normal.filename = "normal.fit"
        normal.file.read.return_value = b"fit-data"

        results = _import_files_sync(mock_context, [no_name, normal], force=False)

        assert results["summary"]["errors"] == 1
        assert results["summary"]["added"] == 1
        none_result = next(
            r for r in results["results"] if r["filename"] == "<unknown>"
        )
        assert none_result["status"] == "error"
        assert "文件名为空" in none_result["message"]
