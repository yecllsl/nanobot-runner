# AppContext 扩展属性单元测试 - v0.17.0

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.core.base.context import AppContext


class TestAppContextExtensions:
    """AppContext v0.17.0 扩展属性测试"""

    @pytest.fixture
    def mock_context(self):
        """创建Mock上下文"""
        config = MagicMock()
        config.data_dir = Path(tempfile.mkdtemp())
        config.base_dir = Path(tempfile.mkdtemp())

        context = AppContext(
            config=config,
            storage=MagicMock(),
            indexer=MagicMock(),
            parser=MagicMock(),
            importer=MagicMock(),
            analytics=MagicMock(),
            profile_engine=MagicMock(),
            profile_storage=MagicMock(),
            session_repo=MagicMock(),
            report_service=MagicMock(),
            plan_manager=MagicMock(),
        )

        yield context

        # 清理临时目录
        import shutil

        shutil.rmtree(config.data_dir, ignore_errors=True)
        shutil.rmtree(config.base_dir, ignore_errors=True)

    def test_training_reminder_manager_lazy_load(self, mock_context):
        """测试训练提醒管理器延迟加载"""
        # 初始状态应为None
        assert mock_context.get_extension("training_reminder_manager") is None

        # 访问属性时应自动创建
        with patch(
            "src.core.plan.training_reminder_manager.TrainingReminderManager"
        ) as MockManager:
            mock_manager = MagicMock()
            MockManager.return_value = mock_manager

            manager = mock_context.training_reminder_manager

            assert manager is mock_manager
            MockManager.assert_called_once_with(data_dir=mock_context.config.data_dir)

        # 再次访问应返回缓存的实例
        assert mock_context.training_reminder_manager is manager

    def test_cron_callback_handler_lazy_load(self, mock_context):
        """测试Cron回调处理器延迟加载"""
        # 初始状态应为None
        assert mock_context.get_extension("cron_callback_handler") is None

        # 访问属性时应自动创建
        with patch("src.core.plan.cron_callback.CronCallbackHandler") as MockHandler:
            mock_handler = MagicMock()
            MockHandler.return_value = mock_handler

            # 先设置training_reminder_manager扩展
            mock_context.set_extension("training_reminder_manager", MagicMock())

            handler = mock_context.cron_callback_handler

            assert handler is mock_handler
            MockHandler.assert_called_once()

        # 再次访问应返回缓存的实例
        assert mock_context.cron_callback_handler is handler

    def test_gateway_integration_lazy_load(self, mock_context):
        """测试Gateway集成器延迟加载"""
        # 初始状态应为None
        assert mock_context.get_extension("gateway_integration") is None

        # 访问属性时应自动创建
        with patch(
            "src.core.plan.gateway_integration.GatewayIntegration"
        ) as MockIntegration:
            mock_integration = MagicMock()
            MockIntegration.return_value = mock_integration

            integration = mock_context.gateway_integration

            assert integration is mock_integration
            MockIntegration.assert_called_once_with(
                workspace=mock_context.config.base_dir,
                data_dir=mock_context.config.data_dir,
            )

        # 再次访问应返回缓存的实例
        assert mock_context.gateway_integration is integration

    def test_extension_caching(self, mock_context):
        """测试扩展实例缓存"""
        with patch(
            "src.core.plan.training_reminder_manager.TrainingReminderManager"
        ) as MockManager:
            mock_manager = MagicMock()
            MockManager.return_value = mock_manager

            # 第一次访问
            manager1 = mock_context.training_reminder_manager
            # 第二次访问
            manager2 = mock_context.training_reminder_manager

            # 验证只创建了一次
            MockManager.assert_called_once()
            assert manager1 is manager2

    def test_extension_isolation(self):
        """测试扩展实例隔离"""
        config1 = MagicMock()
        config1.data_dir = Path(tempfile.mkdtemp())
        config1.base_dir = Path(tempfile.mkdtemp())

        config2 = MagicMock()
        config2.data_dir = Path(tempfile.mkdtemp())
        config2.base_dir = Path(tempfile.mkdtemp())

        context1 = AppContext(
            config=config1,
            storage=MagicMock(),
            indexer=MagicMock(),
            parser=MagicMock(),
            importer=MagicMock(),
            analytics=MagicMock(),
            profile_engine=MagicMock(),
            profile_storage=MagicMock(),
            session_repo=MagicMock(),
            report_service=MagicMock(),
            plan_manager=MagicMock(),
        )

        context2 = AppContext(
            config=config2,
            storage=MagicMock(),
            indexer=MagicMock(),
            parser=MagicMock(),
            importer=MagicMock(),
            analytics=MagicMock(),
            profile_engine=MagicMock(),
            profile_storage=MagicMock(),
            session_repo=MagicMock(),
            report_service=MagicMock(),
            plan_manager=MagicMock(),
        )

        try:
            with patch(
                "src.core.plan.training_reminder_manager.TrainingReminderManager"
            ) as MockManager:
                mock_manager1 = MagicMock()
                mock_manager2 = MagicMock()
                MockManager.side_effect = [mock_manager1, mock_manager2]

                manager1 = context1.training_reminder_manager
                manager2 = context2.training_reminder_manager

                assert manager1 is mock_manager1
                assert manager2 is mock_manager2
                assert manager1 is not manager2
        finally:
            import shutil

            shutil.rmtree(config1.data_dir, ignore_errors=True)
            shutil.rmtree(config1.base_dir, ignore_errors=True)
            shutil.rmtree(config2.data_dir, ignore_errors=True)
            shutil.rmtree(config2.base_dir, ignore_errors=True)

    def test_extension_manual_override(self, mock_context):
        """测试手动覆盖扩展实例"""
        custom_manager = MagicMock()
        mock_context.set_extension("training_reminder_manager", custom_manager)

        # 访问属性时应返回手动设置的实例
        manager = mock_context.training_reminder_manager
        assert manager is custom_manager
