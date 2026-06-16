"""WebUI 设置中心页面测试

测试个人信息、偏好设置、系统配置。
"""


class TestSettingsProfile:
    """个人信息设置测试"""

    def test_settings_page_loads(self, page, webui_base_url, auth_headers):
        """设置中心页面应正常加载"""
        page.goto(f"{webui_base_url}/settings")
        page.wait_for_load_state("networkidle")
        assert page.locator("h1:has-text('设置中心')").is_visible()

    def test_profile_section_display(self, page, webui_base_url, auth_headers):
        """个人信息区域应显示"""
        page.goto(f"{webui_base_url}/settings")
        page.wait_for_load_state("networkidle")
        assert page.locator("h2:has-text('个人信息')").is_visible()

    def test_profile_fields_display(self, page, webui_base_url, auth_headers):
        """个人信息字段应显示"""
        page.goto(f"{webui_base_url}/settings")
        page.wait_for_load_state("networkidle")
        assert page.locator("text=昵称").is_visible()
        assert page.locator("text=年龄").is_visible()
        assert page.locator("text=性别").is_visible()
        assert page.locator("text=最大心率").is_visible()
        assert page.locator("text=静息心率").is_visible()

    def test_profile_edit_form(self, page, webui_base_url, auth_headers):
        """个人信息编辑表单应可用"""
        page.goto(f"{webui_base_url}/settings")
        page.wait_for_load_state("networkidle")
        # 检查保存按钮
        assert page.locator("button:has-text('保存')").is_visible()


class TestSettingsSystem:
    """系统配置测试"""

    def test_system_config_display(self, page, webui_base_url, auth_headers):
        """系统配置区域应显示"""
        page.goto(f"{webui_base_url}/settings")
        page.wait_for_load_state("networkidle")
        assert page.locator("h2:has-text('系统配置')").is_visible()

    def test_system_config_fields(self, page, webui_base_url, auth_headers):
        """系统配置字段应显示"""
        page.goto(f"{webui_base_url}/settings")
        page.wait_for_load_state("networkidle")
        assert page.locator("text=数据目录").is_visible()
        assert page.locator("text=版本").is_visible()
        assert page.locator("text=WebUI 状态").is_visible()
        assert page.locator("text=WebUI 端口").is_visible()

    def test_version_display(self, page, webui_base_url, auth_headers):
        """版本号应显示"""
        page.goto(f"{webui_base_url}/settings")
        page.wait_for_load_state("networkidle")
        assert page.locator("text=0.29.0").is_visible()
