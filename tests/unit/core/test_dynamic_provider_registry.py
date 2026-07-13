"""DynamicProviderRegistry 单元测试"""

import pytest

from src.core.provider_adapter import DynamicProviderRegistry


@pytest.fixture(autouse=True)
def cleanup_registry():
    """每个测试前后清理注册表，避免测试间状态泄漏"""
    DynamicProviderRegistry._custom_providers.clear()
    DynamicProviderRegistry._provider_metadata.clear()
    yield
    DynamicProviderRegistry._custom_providers.clear()
    DynamicProviderRegistry._provider_metadata.clear()


def test_register_custom_provider():
    """测试注册自定义 Provider"""
    DynamicProviderRegistry.register_custom_provider(
        name="custom-llm",
        api_base="https://api.custom-llm.com/v1",
        api_key="sk-test",
        default_model="custom-model",
    )
    assert "custom-llm" in DynamicProviderRegistry._custom_providers


def test_registered_provider_has_api_base():
    """测试注册的 ProviderSpec 包含 api_base"""
    DynamicProviderRegistry.register_custom_provider(
        name="custom-llm",
        api_base="https://api.custom-llm.com/v1",
        api_key="sk-test",
        default_model="custom-model",
    )
    spec = DynamicProviderRegistry._custom_providers["custom-llm"]
    assert spec.default_api_base == "https://api.custom-llm.com/v1"


def test_registered_provider_backend_is_openai_compat():
    """测试注册的 Provider backend 为 openai_compat"""
    DynamicProviderRegistry.register_custom_provider(
        name="my-provider",
        api_base="https://api.my.com/v1",
        api_key="sk-test",
        default_model="model",
    )
    spec = DynamicProviderRegistry._custom_providers["my-provider"]
    assert spec.backend == "openai_compat"


def test_list_custom_providers():
    """测试列出自定义 Provider"""
    DynamicProviderRegistry.register_custom_provider(
        name="custom-1",
        api_base="https://api.custom.com/v1",
        api_key="sk-test",
        default_model="model-1",
    )
    DynamicProviderRegistry.register_custom_provider(
        name="custom-2",
        api_base="https://api.custom2.com/v1",
        api_key="sk-test",
        default_model="model-2",
    )
    providers = DynamicProviderRegistry.list_custom_providers()
    assert "custom-1" in providers
    assert "custom-2" in providers
    assert len(providers) == 2


def test_name_conflict_rejection():
    """测试内置 Provider 名称冲突被拒绝"""
    DynamicProviderRegistry.register_custom_provider(
        name="openai",
        api_base="https://api.custom.com/v1",
        api_key="sk-test",
        default_model="model",
    )
    assert "openai" not in DynamicProviderRegistry._custom_providers


def test_name_conflict_anthropic_rejection():
    """测试 anthropic 名称冲突被拒绝"""
    DynamicProviderRegistry.register_custom_provider(
        name="anthropic",
        api_base="https://api.custom.com/v1",
        api_key="sk-test",
        default_model="model",
    )
    assert "anthropic" not in DynamicProviderRegistry._custom_providers


def test_metadata_stored():
    """测试 api_key 和 default_model 存储在 metadata 中"""
    DynamicProviderRegistry.register_custom_provider(
        name="custom-llm",
        api_base="https://api.custom-llm.com/v1",
        api_key="sk-test-key",
        default_model="custom-model",
    )
    metadata = DynamicProviderRegistry._provider_metadata["custom-llm"]
    assert metadata["api_key"] == "sk-test-key"
    assert metadata["default_model"] == "custom-model"


def test_empty_api_base():
    """测试空 api_base 时不覆盖默认值"""
    DynamicProviderRegistry.register_custom_provider(
        name="no-base-provider",
        api_base="",
        api_key="sk-test",
        default_model="model",
    )
    assert "no-base-provider" in DynamicProviderRegistry._custom_providers


def test_list_empty_when_no_registrations():
    """测试无注册时返回空列表"""
    providers = DynamicProviderRegistry.list_custom_providers()
    assert providers == []


def test_get_provider_spec():
    """测试获取已注册的 ProviderSpec"""
    DynamicProviderRegistry.register_custom_provider(
        name="custom-llm",
        api_base="https://api.custom-llm.com/v1",
        api_key="sk-test",
        default_model="custom-model",
    )
    spec = DynamicProviderRegistry.get_provider_spec("custom-llm")
    assert spec is not None
    assert spec.default_api_base == "https://api.custom-llm.com/v1"


def test_get_provider_spec_not_found():
    """测试获取未注册的 ProviderSpec 返回 None"""
    spec = DynamicProviderRegistry.get_provider_spec("nonexistent")
    assert spec is None
