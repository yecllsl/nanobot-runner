"""WebUI 进化引擎控制台页面测试

测试进化状态面板、提示参数调优、月度进化报告。
"""

import pytest


class TestEvolutionStatusPanel:
    """进化状态面板测试"""

    def test_evolution_page_loads(self, page, webui_base_url, auth_headers):
        """进化引擎控制台页面应正常加载"""
        page.goto(f"{webui_base_url}/evolution")
        page.wait_for_load_state("networkidle")
        assert page.locator("h1:has-text('进化控制台')").is_visible()

    def test_engine_status_display(self, page, webui_base_url, auth_headers):
        """引擎状态应显示"""
        page.goto(f"{webui_base_url}/evolution")
        page.wait_for_load_state("networkidle")
        assert page.locator("h2:has-text('引擎状态')").is_visible()
        assert page.locator("text=运行中").is_visible()

    def test_trigger_conditions_display(self, page, webui_base_url, auth_headers):
        """触发条件应显示"""
        page.goto(f"{webui_base_url}/evolution")
        page.wait_for_load_state("networkidle")
        assert page.locator("h3:has-text('触发条件')").is_visible()
        # 检查 4 条触发条件
        assert page.locator("text=VDOT预测误差连续3次>5%").is_visible()
        assert page.locator("text=连续2次拒绝推荐").is_visible()
        assert page.locator("text=新数据积累>=50条").is_visible()
        assert page.locator("text=当月未生成报告").is_visible()

    def test_recent_actions_display(self, page, webui_base_url, auth_headers):
        """最近动作记录应显示"""
        page.goto(f"{webui_base_url}/evolution")
        page.wait_for_load_state("networkidle")
        assert page.locator("h3:has-text('最近动作')").is_visible()


class TestPromptTuning:
    """提示参数调优测试"""

    def test_tuning_section_renders(self, page, webui_base_url, auth_headers):
        """调优区域应渲染"""
        page.goto(f"{webui_base_url}/evolution")
        page.wait_for_load_state("networkidle")
        assert page.locator("h2:has-text('提示参数调优')").is_visible()

    def test_tuning_sliders_render(self, page, webui_base_url, auth_headers):
        """调优滑块应渲染"""
        page.goto(f"{webui_base_url}/evolution")
        page.wait_for_load_state("networkidle")
        # 检查滑块容器（input[type='range'] 或自定义滑块）
        sliders = page.locator("input[type='range'], .ant-slider, [class*='slider']")
        # 至少应有滑块或滑块容器
        assert sliders.count() > 0 or page.locator("text=语气强度").is_visible()

    def test_tuning_slider_labels(self, page, webui_base_url, auth_headers):
        """滑块标签应显示"""
        page.goto(f"{webui_base_url}/evolution")
        page.wait_for_load_state("networkidle")
        # 使用 first 避免 strict mode violation
        assert page.locator("text=语气强度").first.is_visible()
        assert page.locator("text=详细程度").first.is_visible()
        assert page.locator("text=推荐激进性").first.is_visible()
        assert page.locator("text=数据驱动权重").first.is_visible()


class TestEvolutionReports:
    """月度进化报告测试"""

    def test_report_section_renders(self, page, webui_base_url, auth_headers):
        """报告区域应渲染"""
        page.goto(f"{webui_base_url}/evolution")
        page.wait_for_load_state("networkidle")
        assert page.locator("h2:has-text('进化报告')").is_visible()
