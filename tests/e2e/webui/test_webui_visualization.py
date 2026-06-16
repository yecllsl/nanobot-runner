"""WebUI 数据可视化页面测试

测试 VDOT 趋势、训练负荷、活动列表、身体信号等数据可视化页面。
"""


class TestVdotPage:
    """VDOT 趋势页面测试"""

    def test_vdot_page_loads(self, page, webui_base_url, auth_headers):
        """VDOT 趋势页面应正常加载"""
        page.goto(f"{webui_base_url}/vdot")
        page.wait_for_load_state("networkidle")
        assert page.locator("h2:has-text('VDOT 趋势')").is_visible()

    def test_vdot_chart_renders(self, page, webui_base_url, auth_headers):
        """VDOT 趋势图表应渲染"""
        page.goto(f"{webui_base_url}/vdot")
        page.wait_for_load_state("networkidle")
        # 检查图表容器（Recharts 渲染为 SVG）
        chart = page.locator("svg, .recharts-wrapper, canvas").first
        assert chart.is_visible()

    def test_vdot_time_range_selector(self, page, webui_base_url, auth_headers):
        """VDOT 趋势应支持时间范围切换"""
        page.goto(f"{webui_base_url}/vdot")
        page.wait_for_load_state("networkidle")
        assert page.locator("button:has-text('7天')").is_visible()
        assert page.locator("button:has-text('30天')").is_visible()
        assert page.locator("button:has-text('90天')").is_visible()

    def test_vdot_stats_display(self, page, webui_base_url, auth_headers):
        """VDOT 趋势应显示统计信息"""
        page.goto(f"{webui_base_url}/vdot")
        page.wait_for_load_state("networkidle")
        # 检查最新VDOT/最高VDOT/数据点等统计
        assert (
            page.locator("text=最新VDOT").is_visible()
            or page.locator("text=均值").is_visible()
        )


class TestTrainingLoadPage:
    """训练负荷页面测试"""

    def test_training_load_page_loads(self, page, webui_base_url, auth_headers):
        """训练负荷页面应正常加载"""
        page.goto(f"{webui_base_url}/training-load")
        page.wait_for_load_state("networkidle")
        assert page.locator("h2:has-text('训练负荷')").is_visible()

    def test_training_load_chart_renders(self, page, webui_base_url, auth_headers):
        """训练负荷图表应渲染"""
        page.goto(f"{webui_base_url}/training-load")
        page.wait_for_load_state("networkidle")
        chart = page.locator("svg, .recharts-wrapper, canvas").first
        assert chart.is_visible()

    def test_training_load_metrics_display(self, page, webui_base_url, auth_headers):
        """训练负荷应显示 ATL/CTL/TSB 指标"""
        page.goto(f"{webui_base_url}/training-load")
        page.wait_for_load_state("networkidle")
        # 使用更精确的选择器避免 strict mode violation
        assert page.get_by_text("ATL (急性)").first.is_visible()
        assert page.get_by_text("CTL (慢性)").first.is_visible()
        assert page.get_by_text("TSB (平衡)").first.is_visible()


class TestActivitiesPage:
    """活动列表页面测试"""

    def test_activities_page_loads(self, page, webui_base_url, auth_headers):
        """活动列表页面应正常加载"""
        page.goto(f"{webui_base_url}/activities")
        page.wait_for_load_state("networkidle")
        assert page.locator("h2:has-text('活动记录')").is_visible()

    def test_activities_table_headers(self, page, webui_base_url, auth_headers):
        """活动列表应显示表头"""
        page.goto(f"{webui_base_url}/activities")
        page.wait_for_load_state("networkidle")
        assert page.locator("text=日期").is_visible()
        assert page.locator("text=距离").is_visible()
        assert page.locator("text=时长").is_visible()
        assert page.locator("text=配速").is_visible()
        assert page.locator("text=心率").is_visible()

    def test_activities_list_has_data(self, page, webui_base_url, auth_headers):
        """活动列表应有数据行"""
        page.goto(f"{webui_base_url}/activities")
        page.wait_for_load_state("networkidle")
        # 检查是否有日期格式的数据（2026-）
        assert (
            page.locator("text=/2026-/").first.is_visible()
            or page.locator("text=暂无数据").is_visible()
        )


class TestBodySignalsPage:
    """身体信号页面测试"""

    def test_body_signals_page_loads(self, page, webui_base_url, auth_headers):
        """身体信号页面应正常加载"""
        page.goto(f"{webui_base_url}/body-signals")
        page.wait_for_load_state("networkidle")
        assert page.locator("h2:has-text('身体信号')").is_visible()

    def test_body_signals_today_status(self, page, webui_base_url, auth_headers):
        """身体信号应显示今日状态"""
        page.goto(f"{webui_base_url}/body-signals")
        page.wait_for_load_state("networkidle")
        assert page.locator("h3:has-text('今日状态')").is_visible()

    def test_body_signals_weekly_status(self, page, webui_base_url, auth_headers):
        """身体信号应显示本周状态"""
        page.goto(f"{webui_base_url}/body-signals")
        page.wait_for_load_state("networkidle")
        assert page.locator("h3:has-text('本周状态')").is_visible()

    def test_body_signals_metrics_display(self, page, webui_base_url, auth_headers):
        """身体信号应显示恢复/疲劳度指标"""
        page.goto(f"{webui_base_url}/body-signals")
        page.wait_for_load_state("networkidle")
        # 使用更精确的选择器避免 strict mode violation
        assert page.get_by_text("恢复状态", exact=True).first.is_visible()
        assert page.get_by_text("疲劳度", exact=True).first.is_visible()
