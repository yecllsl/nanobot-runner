"""WebUI 数据导入功能 E2E 测试 (v0.34.0)

验证导入页面的导航、UI 元素和导入流程。
使用 Playwright 进行真实浏览器测试，webui_server fixture 自动启停服务器。
"""

import pytest
from fastapi.testclient import TestClient
from playwright.sync_api import Page, expect

# ============================================================
# API 层 E2E 测试（使用 TestClient，无需浏览器）
# ============================================================


class TestImportAPIEndpoint:
    """数据导入 API 端点 E2E 测试"""

    def test_import_endpoint_registered(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """验证 /api/data/import 端点已注册"""
        # 未带文件应返回 422（缺少必需参数）而非 404
        response = client.post("/api/data/import", headers=auth_headers)
        assert response.status_code != 404
        assert response.status_code == 422  # 缺少 files 参数

    def test_import_single_file_via_api(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """通过 API 上传单个 FIT 文件"""
        fit_content = b".FIT" + b"\x00" * 116
        response = client.post(
            "/api/data/import",
            headers=auth_headers,
            files={"files": ("e2e_run.fit", fit_content, "application/octet-stream")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["summary"]["total"] == 1
        assert data["summary"]["added"] == 1
        assert data["results"][0]["filename"] == "e2e_run.fit"

    def test_import_force_param_via_api(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        """通过 API 传递 force 参数"""
        fit_content = b".FIT" + b"\x00" * 116
        response = client.post(
            "/api/data/import?force=true",
            headers=auth_headers,
            files={"files": ("force_run.fit", fit_content, "application/octet-stream")},
        )
        assert response.status_code == 200


# ============================================================
# Playwright UI 测试（需要浏览器）
# ============================================================


@pytest.mark.ui
class TestImportPageUI:
    """导入页面 UI 测试（需要 Playwright 浏览器）"""

    def test_import_page_accessible(
        self, page: Page, webui_base_url: str, auth_headers: dict[str, str]
    ) -> None:
        """导入页面可访问"""
        # 通过 cookie 或 localStorage 注入 token（前端会自动获取，但直接访问页面也应有渲染）
        page.goto(f"{webui_base_url}/import")
        page.wait_for_load_state("networkidle")
        # 页面应包含"数据导入"标题
        expect(page.get_by_text("数据导入").first).to_be_visible()

    def test_import_page_has_file_button(self, page: Page, webui_base_url: str) -> None:
        """导入页有文件选择按钮"""
        page.goto(f"{webui_base_url}/import")
        page.wait_for_load_state("networkidle")
        expect(page.get_by_role("button", name="选择 .fit 文件")).to_be_visible()

    def test_import_page_has_force_checkbox(
        self, page: Page, webui_base_url: str
    ) -> None:
        """导入页有强制重新导入复选框"""
        page.goto(f"{webui_base_url}/import")
        page.wait_for_load_state("networkidle")
        expect(page.get_by_text("强制重新导入")).to_be_visible()

    def test_import_button_disabled_without_files(
        self, page: Page, webui_base_url: str
    ) -> None:
        """未选择文件时开始导入按钮禁用"""
        page.goto(f"{webui_base_url}/import")
        page.wait_for_load_state("networkidle")
        button = page.get_by_role("button", name="开始导入")
        expect(button).to_be_disabled()

    def test_sidebar_has_import_nav(self, page: Page, webui_base_url: str) -> None:
        """侧边栏有导入导航项"""
        page.goto(f"{webui_base_url}/")
        page.wait_for_load_state("networkidle")
        expect(page.get_by_role("link", name="导入").first).to_be_visible()
