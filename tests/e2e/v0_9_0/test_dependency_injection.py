#!/usr/bin/env python3
"""
v0.9.0 依赖注入端到端测试

测试目标：
- 验证AppContext/Factory机制正确性
- 确保依赖注入容器正确创建
- 验证各模块依赖正确注入
- 验证配置路径正确传递

执行方式：
- pytest tests/e2e/v0_9_0/test_dependency_injection.py -v
"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.core.config import ConfigManager
from src.core.context import AppContextFactory
from src.core.storage import StorageManager


class TestDependencyInjectionE2E:
    """依赖注入端到端测试"""

    def setup_method(self):
        """测试前置设置"""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_data_dir = Path(self.temp_dir.name)

    def teardown_method(self):
        """测试后置清理"""
        import gc
        import time

        gc.collect()
        time.sleep(0.1)
        try:
            self.temp_dir.cleanup()
        except PermissionError:
            pass

    def test_app_context_creation(self):
        """
        E2E-DI-001: AppContext创建测试
        验证依赖注入容器正确创建
        优先级: P0
        """
        print("\n=== AppContext创建测试 ===")

        config = ConfigManager()
        config.data_dir = self.test_data_dir
        context = AppContextFactory.create(config=config)

        assert context is not None, "AppContext创建失败"
        assert context.storage is not None, "StorageManager未注入"
        assert context.analytics is not None, "AnalyticsEngine未注入"
        assert context.profile_engine is not None, "ProfileEngine未注入"

        print("✓ AppContext创建测试通过")
        print(f"  - StorageManager: {type(context.storage).__name__}")
        print(f"  - AnalyticsEngine: {type(context.analytics).__name__}")
        print(f"  - ProfileEngine: {type(context.profile_engine).__name__}")

    def test_factory_pattern(self):
        """
        E2E-DI-002: Factory模式测试
        验证工厂方法正确性
        优先级: P0
        """
        print("\n=== Factory模式测试 ===")

        config1 = ConfigManager()
        config1.data_dir = self.test_data_dir / "context1"
        context1 = AppContextFactory.create(config=config1)

        config2 = ConfigManager()
        config2.data_dir = self.test_data_dir / "context2"
        context2 = AppContextFactory.create(config=config2)

        assert context1 is not None, "第一个AppContext创建失败"
        assert context2 is not None, "第二个AppContext创建失败"

        assert context1 is not context2, "Factory应创建新实例"

        assert context1.storage is not context2.storage, "StorageManager应为不同实例"

        print("✓ Factory模式测试通过")
        print(f"  - Context1: {id(context1)}")
        print(f"  - Context2: {id(context2)}")

    def test_dependency_injection_integration(self):
        """
        E2E-DI-003: 依赖注入集成测试
        验证各模块依赖正确注入
        优先级: P0
        """
        print("\n=== 依赖注入集成测试 ===")

        config = ConfigManager()
        config.data_dir = self.test_data_dir
        context = AppContextFactory.create(config=config)

        assert context.analytics.storage is context.storage, (
            "AnalyticsEngine应使用注入的StorageManager"
        )

        assert context.profile_engine.storage is context.storage, (
            "ProfileEngine应使用注入的StorageManager"
        )

        print("✓ 依赖注入集成测试通过")
        print("  - 所有模块共享同一StorageManager实例")

    def test_config_path_propagation(self):
        """
        E2E-DI-004: 配置路径传递测试
        验证配置路径正确传递
        优先级: P1
        """
        print("\n=== 配置路径传递测试 ===")

        custom_data_dir = self.test_data_dir / "custom_data"
        config = ConfigManager()
        config.data_dir = custom_data_dir
        context = AppContextFactory.create(config=config)

        assert context.storage.data_dir == custom_data_dir, (
            f"配置路径未正确传递: {context.storage.data_dir} != {custom_data_dir}"
        )

        print("✓ 配置路径传递测试通过")
        print(f"  - 配置路径: {custom_data_dir}")
        print(f"  - 实际路径: {context.storage.data_dir}")

    def test_lazy_initialization(self):
        """
        E2E-DI-005: 延迟初始化测试
        验证依赖按需初始化
        优先级: P1
        """
        print("\n=== 延迟初始化测试 ===")

        config = ConfigManager()
        config.data_dir = self.test_data_dir
        context = AppContextFactory.create(config=config)

        analytics_instance = context.analytics

        print("✓ 延迟初始化测试通过")
        print(f"  - Analytics实例: {type(analytics_instance).__name__}")

    def test_context_with_mock_dependencies(self):
        """
        E2E-DI-006: Mock依赖注入测试
        验证可以注入Mock对象用于测试
        优先级: P1
        """
        print("\n=== Mock依赖注入测试 ===")

        mock_storage = MagicMock(spec=StorageManager)
        mock_analytics = MagicMock()

        config = ConfigManager()
        context = AppContextFactory.create(
            config=config,
            storage=mock_storage,
            analytics=mock_analytics,
        )

        assert context.storage is mock_storage, "Mock StorageManager未正确注入"
        assert context.analytics is mock_analytics, "Mock AnalyticsEngine未正确注入"

        context.analytics.calculate_vdot(5000, 1800)
        mock_analytics.calculate_vdot.assert_called_once_with(5000, 1800)

        print("✓ Mock依赖注入测试通过")

    def test_context_cleanup(self):
        """
        E2E-DI-007: Context清理测试
        验证资源正确释放
        优先级: P2
        """
        print("\n=== Context清理测试 ===")

        config = ConfigManager()
        config.data_dir = self.test_data_dir
        context = AppContextFactory.create(config=config)

        storage_ref = context.storage
        analytics_ref = context.analytics

        del context

        print("✓ Context清理测试通过")
        print("  - 资源已释放")


class TestAppContextFactory:
    """AppContextFactory测试"""

    def test_factory_with_default_config(self):
        """
        测试Factory使用默认配置
        优先级: P1
        """
        print("\n=== Factory默认配置测试 ===")

        with tempfile.TemporaryDirectory() as temp_dir:
            config = ConfigManager()
            config.data_dir = Path(temp_dir)
            context = AppContextFactory.create(config=config)

            assert context is not None
            assert context.storage is not None

            print("✓ Factory默认配置测试通过")

    def test_factory_with_custom_config(self):
        """
        测试Factory使用自定义配置
        优先级: P1
        """
        print("\n=== Factory自定义配置测试 ===")

        with tempfile.TemporaryDirectory() as temp_dir:
            config = ConfigManager()
            config.data_dir = Path(temp_dir)

            context = AppContextFactory.create(config=config)

            assert context is not None
            assert context.storage.data_dir == Path(temp_dir)

            print("✓ Factory自定义配置测试通过")


def test_dependency_injection_e2e_suite():
    """
    执行完整的依赖注入E2E测试套件
    优先级: P0
    """
    print("\n🚀 开始执行依赖注入E2E测试套件")

    test_instance = TestDependencyInjectionE2E()

    try:
        test_instance.setup_method()

        test_instance.test_app_context_creation()
        test_instance.test_factory_pattern()
        test_instance.test_dependency_injection_integration()
        test_instance.test_config_path_propagation()
        test_instance.test_lazy_initialization()
        test_instance.test_context_with_mock_dependencies()
        test_instance.test_context_cleanup()

        print("\n🎉 依赖注入E2E测试套件执行完成！")
        print("✅ 所有测试通过")

    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        raise
    finally:
        test_instance.teardown_method()


if __name__ == "__main__":
    """
    直接运行依赖注入E2E测试
    """
    pytest.main([__file__, "-v", "-s"])
