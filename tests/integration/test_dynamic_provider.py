"""动态 Provider 注册集成测试

验证 DynamicProviderRegistry 注册自定义 Provider 的完整流程。
"""

from src.core.provider_adapter import DynamicProviderRegistry


def test_register_and_list_custom_provider():
    """测试注册并列出自定义 Provider"""
    DynamicProviderRegistry._custom_providers.clear()
    DynamicProviderRegistry._provider_metadata.clear()

    DynamicProviderRegistry.register_custom_provider(
        name="my_custom",
        api_base="https://api.custom.com/v1",
        api_key="sk-custom",
        default_model="custom-model",
    )

    providers = DynamicProviderRegistry.list_custom_providers()
    assert "my_custom" in providers


def test_builtin_name_conflict_rejected():
    """测试内置 Provider 名称被拒绝"""
    DynamicProviderRegistry._custom_providers.clear()
    DynamicProviderRegistry._provider_metadata.clear()

    DynamicProviderRegistry.register_custom_provider(
        name="openai",
        api_base="https://api.openai.com/v1",
        api_key="sk-test",
        default_model="gpt-4",
    )

    assert "openai" not in DynamicProviderRegistry.list_custom_providers()


def test_get_provider_spec():
    """测试获取已注册的 ProviderSpec"""
    DynamicProviderRegistry._custom_providers.clear()
    DynamicProviderRegistry._provider_metadata.clear()

    DynamicProviderRegistry.register_custom_provider(
        name="test_provider",
        api_base="https://api.test.com/v1",
        api_key="sk-test",
        default_model="test-model",
    )

    spec = DynamicProviderRegistry.get_provider_spec("test_provider")
    assert spec is not None
    assert spec.name == "test_provider"
    assert spec.default_api_base == "https://api.test.com/v1"


def test_get_nonexistent_provider_returns_none():
    """测试获取未注册的 Provider 返回 None"""
    DynamicProviderRegistry._custom_providers.clear()
    DynamicProviderRegistry._provider_metadata.clear()
    assert DynamicProviderRegistry.get_provider_spec("nonexistent") is None
