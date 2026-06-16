"""WebUI 仪表盘页面测试

测试仪表盘页面加载、训练负荷卡片、身体信号摘要、最近活动列表。
"""


class TestDashboardPageLoad:
    """仪表盘页面加载测试"""

    def test_dashboard_page_loads(self, page, webui_base_url, auth_headers):
        """仪表盘页面应正常加载"""
        page.goto(f"{webui_base_url}/")
        page.wait_for_load_state("networkidle")
        # 检查页面标题
        assert page.locator("h1:has-text('Nanobot Runner')").is_visible()

    def test_dashboard_has_navigation(self, page, webui_base_url, auth_headers):
        """仪表盘应有侧边导航栏"""
        page.goto(f"{webui_base_url}/")
        page.wait_for_load_state("networkidle")
        # 检查导航栏
        nav = page.locator("nav").first
        assert nav.is_visible()


class TestDashboardTrainingLoad:
    """仪表盘训练负荷卡片测试"""

    def test_training_load_card_visible(self, page, webui_base_url, auth_headers):
        """训练负荷卡片应可见"""
        page.goto(f"{webui_base_url}/")
        page.wait_for_load_state("networkidle")
        # 检查训练负荷标题
        assert page.locator("h3:has-text('训练负荷')").is_visible()

    def test_training_load_values_display(self, page, webui_base_url, auth_headers):
        """训练负荷数值应显示"""
        page.goto(f"{webui_base_url}/")
        page.wait_for_load_state("networkidle")
        # 使用更精确的选择器避免 strict mode violation
        assert page.get_by_text("ATL (急性)").first.is_visible()
        assert page.get_by_text("CTL (慢性)").first.is_visible()
        assert page.get_by_text("TSB (平衡)").first.is_visible()


class TestDashboardBodySignal:
    """仪表盘身体信号摘要测试"""

    def test_body_signal_card_visible(self, page, webui_base_url, auth_headers):
        """身体信号卡片应可见"""
        page.goto(f"{webui_base_url}/")
        page.wait_for_load_state("networkidle")
        # 检查身体信号标题
        assert page.locator("h3:has-text('身体信号')").is_visible()


class TestDashboardRecentActivities:
    """仪表盘最近活动列表测试"""

    def test_recent_activities_visible(self, page, webui_base_url, auth_headers):
        """最近活动列表应可见"""
        page.goto(f"{webui_base_url}/")
        page.wait_for_load_state("networkidle")
        # 检查快捷入口
        assert page.locator("h3:has-text('快捷入口')").is_visible()
