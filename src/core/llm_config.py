from dataclasses import dataclass


@dataclass(frozen=True)
class LLMConfig:
    """LLM配置数据类

    用于类型安全的LLM配置传递，包含Provider、模型、API Key等核心配置项。
    使用frozen=True确保配置不可变，防止运行时意外修改。

    Attributes:
        provider: LLM提供商名称（如openai、anthropic、deepseek）
        model: 模型名称（如gpt-4o-mini、claude-3-5-sonnet）
        api_key: API密钥，从环境变量NANOBOT_LLM_API_KEY读取
        base_url: 自定义API端点URL（可选，用于兼容OpenAI API的第三方服务）
        max_iterations: Agent最大工具调用迭代次数
        context_window_tokens: 上下文窗口token数量
        context_block_limit: 上下文块数量限制
        max_tool_result_chars: 工具返回结果最大字符数
    """

    provider: str
    model: str
    api_key: str | None = None
    base_url: str | None = None
    max_iterations: int = 10
    context_window_tokens: int = 128000
    context_block_limit: int = 10
    max_tool_result_chars: int = 32000

    def is_complete(self) -> bool:
        """检查配置是否完整可用

        至少需要provider和model才能正常工作。

        Returns:
            bool: 配置是否完整
        """
        return bool(self.provider and self.model)

    def has_api_key(self) -> bool:
        """检查是否配置了API Key

        Returns:
            bool: 是否存在API Key
        """
        return bool(self.api_key)

    def to_dict(self) -> dict[str, object]:
        """转换为字典格式

        Returns:
            dict[str, object]: 配置字典
        """
        return {
            "provider": self.provider,
            "model": self.model,
            "api_key": "***" if self.api_key else None,
            "base_url": self.base_url,
            "max_iterations": self.max_iterations,
            "context_window_tokens": self.context_window_tokens,
            "context_block_limit": self.context_block_limit,
            "max_tool_result_chars": self.max_tool_result_chars,
        }
