"""WebUI AI 对话入口测试

测试 WebUI 数据可视化页面到 Agent 对话的导航入口。
注意：AI 对话功能在 Gateway 端口 8765，数据可视化在 API 端口 8766。
"""


class TestAIChatEntry:
    """AI 对话入口测试"""

    def test_agent_chat_link_visible(self, page, webui_base_url, auth_headers):
        """WebUI 应有 Agent 对话入口链接"""
        page.goto(f"{webui_base_url}/")
        page.wait_for_load_state("networkidle")
        # 检查顶部 banner 中的 Agent 对话链接
        link = page.locator("a:has-text('Agent对话')")
        assert link.is_visible()

    def test_agent_chat_link_navigates_to_gateway(
        self, page, webui_base_url, auth_headers
    ):
        """Agent 对话链接应指向 Gateway 端口"""
        page.goto(f"{webui_base_url}/")
        page.wait_for_load_state("networkidle")
        link = page.locator("a:has-text('Agent对话')")
        href = link.get_attribute("href")
        assert href is not None
        assert "8765" in href


class TestNavigationLinks:
    """导航链接测试"""

    def test_sidebar_has_all_nav_items(self, page, webui_base_url, auth_headers):
        """侧边栏应包含所有导航项"""
        page.goto(f"{webui_base_url}/")
        page.wait_for_load_state("networkidle")
        nav = page.locator("nav")
        assert nav.is_visible()
        # 检查 8 个导航项
        assert nav.locator("a:has-text('仪表盘')").is_visible()
        assert nav.locator("a:has-text('VDOT')").is_visible()
        assert nav.locator("a:has-text('负荷')").is_visible()
        assert nav.locator("a:has-text('活动')").is_visible()
        assert nav.locator("a:has-text('身体')").is_visible()
        assert nav.locator("a:has-text('计划')").is_visible()
        assert nav.locator("a:has-text('进化')").is_visible()
        assert nav.locator("a:has-text('设置')").is_visible()
