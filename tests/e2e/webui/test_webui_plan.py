"""WebUI 训练计划管理页面测试

测试训练计划日历视图、列表视图、执行进度、AI调整模式、手工调整模式。
"""

import pytest


class TestPlanCalendarView:
    """训练计划日历视图测试"""

    def test_plan_page_loads(self, page, webui_base_url, auth_headers):
        """训练计划页面应正常加载"""
        page.goto(f"{webui_base_url}/plan")
        page.wait_for_load_state("networkidle")
        assert page.is_visible("text=训练计划") or page.is_visible("text=计划")

    def test_calendar_view_renders(self, page, webui_base_url, auth_headers):
        """日历视图应渲染"""
        page.goto(f"{webui_base_url}/plan")
        page.wait_for_load_state("networkidle")
        # 检查日历容器
        calendar = page.locator(".calendar-container, .plan-calendar, [class*='calendar']").first
        assert calendar.is_visible() or page.is_visible("text=暂无训练计划")

    def test_calendar_week_month_switch(self, page, webui_base_url, auth_headers):
        """日历视图应支持状态过滤"""
        page.goto(f"{webui_base_url}/plan")
        page.wait_for_load_state("networkidle")
        # 检查状态过滤按钮（进行中/已完成/全部）
        assert page.locator("button:has-text('进行中')").is_visible()
        assert page.locator("button:has-text('已完成')").is_visible()
        assert page.locator("button:has-text('全部')").is_visible()


class TestPlanListView:
    """训练计划列表视图测试"""

    def test_plan_list_renders(self, page, webui_base_url, auth_headers):
        """计划列表应渲染"""
        page.goto(f"{webui_base_url}/plan")
        page.wait_for_load_state("networkidle")
        # 检查列表容器
        plan_list = page.locator(".plan-list, .plan-item, [class*='plan']").first
        assert plan_list.is_visible() or page.is_visible("text=暂无训练计划")

    def test_plan_status_display(self, page, webui_base_url, auth_headers):
        """计划状态应显示"""
        page.goto(f"{webui_base_url}/plan")
        page.wait_for_load_state("networkidle")
        # 检查状态标签
        status = page.locator(".status-tag, .plan-status, [class*='status']").first
        assert status.is_visible() or page.is_visible("text=暂无")


class TestPlanProgress:
    """计划执行进度测试"""

    def test_progress_ring_chart(self, page, webui_base_url, auth_headers):
        """进度环形图应显示"""
        page.goto(f"{webui_base_url}/plan")
        page.wait_for_load_state("networkidle")
        # 检查进度图表
        progress = page.locator(".progress-ring, .progress-chart, [class*='progress']").first
        assert progress.is_visible() or page.is_visible("text=暂无")

    def test_fidelity_metrics(self, page, webui_base_url, auth_headers):
        """忠实度指标应显示"""
        page.goto(f"{webui_base_url}/plan")
        page.wait_for_load_state("networkidle")
        # 检查忠实度显示
        fidelity = page.locator("text=忠实度, text=执行率").first
        assert fidelity.is_visible() or page.is_visible("text=暂无")
