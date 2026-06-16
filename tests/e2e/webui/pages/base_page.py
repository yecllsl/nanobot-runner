"""Page Object Model 基类"""

from playwright.sync_api import Page


class BasePage:
    """页面对象基类"""

    def __init__(self, page: Page, base_url: str = "http://127.0.0.1:8766"):
        self.page = page
        self.base_url = base_url

    def navigate(self, path: str = "/"):
        """导航到指定路径"""
        url = f"{self.base_url}{path}"
        self.page.goto(url)
        self.page.wait_for_load_state("networkidle")

    def wait_for_page_load(self):
        """等待页面加载完成"""
        self.page.wait_for_load_state("networkidle")

    def get_page_title(self) -> str:
        """获取页面标题"""
        return self.page.title()

    def is_element_visible(self, selector: str) -> bool:
        """检查元素是否可见"""
        return self.page.locator(selector).is_visible()

    def get_text_content(self, selector: str) -> str:
        """获取元素文本内容"""
        return self.page.locator(selector).text_content() or ""

    def click(self, selector: str):
        """点击元素"""
        self.page.locator(selector).click()

    def fill_input(self, selector: str, value: str):
        """填充输入框"""
        self.page.locator(selector).fill(value)

    def take_screenshot(self, path: str):
        """截图"""
        self.page.screenshot(path=path)
