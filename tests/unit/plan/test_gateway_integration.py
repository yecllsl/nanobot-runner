# Gateway 集成模块单元测试 - v0.17.0

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.core.plan.gateway_integration import GatewayIntegration


class TestGatewayIntegration:
    """GatewayIntegration 测试"""

    def test_init_default(self):
        """测试默认初始化"""
        workspace = Path(tempfile.mkdtemp())

        try:
            integration = GatewayIntegration(workspace)

            assert integration.workspace == workspace
            assert integration.data_dir == workspace / "data"
            assert integration.bus is None
            assert integration.console is None
            assert integration.reminder_manager is None
            assert integration.cron_service is None
            assert integration.streaming_hook is None
        finally:
            import shutil

            shutil.rmtree(workspace, ignore_errors=True)

    def test_init_custom(self):
        """测试自定义初始化"""
        workspace = Path(tempfile.mkdtemp())
        data_dir = Path(tempfile.mkdtemp())
        bus = MagicMock()
        console = MagicMock()

        try:
            integration = GatewayIntegration(
                workspace=workspace,
                bus=bus,
                console=console,
                data_dir=data_dir,
            )

            assert integration.bus == bus
            assert integration.console == console
            assert integration.data_dir == data_dir
        finally:
            import shutil

            shutil.rmtree(workspace, ignore_errors=True)
            shutil.rmtree(data_dir, ignore_errors=True)

    def test_setup_cron_service(self):
        """测试设置Cron服务"""
        workspace = Path(tempfile.mkdtemp())

        try:
            with patch("src.core.plan.gateway_integration.CronService") as MockCron:
                mock_cron = MagicMock()
                mock_cron.list_jobs.return_value = []
                MockCron.return_value = mock_cron

                integration = GatewayIntegration(workspace)
                cron = integration.setup_cron_service(auto_register_reminder=False)

                assert cron is mock_cron
                assert integration.reminder_manager is not None
                assert integration.cron_callback is not None
                assert integration.cron_service is not None

                MockCron.assert_called_once()
                call_kwargs = MockCron.call_args.kwargs
                assert "store_path" in call_kwargs
                assert "on_job" in call_kwargs
        finally:
            import shutil

            shutil.rmtree(workspace, ignore_errors=True)

    def test_setup_cron_service_auto_register(self):
        """测试自动注册训练提醒"""
        workspace = Path(tempfile.mkdtemp())

        try:
            with patch("src.core.plan.gateway_integration.CronService") as MockCron:
                mock_cron = MagicMock()
                mock_cron.list_jobs.return_value = []
                MockCron.return_value = mock_cron

                integration = GatewayIntegration(workspace)
                cron = integration.setup_cron_service(auto_register_reminder=True)

                # 验证训练提醒任务被注册
                mock_cron.register_job.assert_called_once()
                call_kwargs = mock_cron.register_job.call_args.kwargs
                assert call_kwargs["name"] == "training_reminder"
        finally:
            import shutil

            shutil.rmtree(workspace, ignore_errors=True)

    def test_setup_cron_service_existing_job(self):
        """测试已存在任务时跳过注册"""
        workspace = Path(tempfile.mkdtemp())

        try:
            with patch("src.core.plan.gateway_integration.CronService") as MockCron:
                mock_cron = MagicMock()
                # 模拟已存在训练提醒任务
                existing_job = MagicMock()
                existing_job.name = "training_reminder"
                mock_cron.list_jobs.return_value = [existing_job]
                MockCron.return_value = mock_cron

                integration = GatewayIntegration(workspace)
                cron = integration.setup_cron_service(auto_register_reminder=True)

                # 验证没有重复注册
                mock_cron.register_job.assert_not_called()
        finally:
            import shutil

            shutil.rmtree(workspace, ignore_errors=True)

    def test_setup_streaming_hook(self):
        """测试设置流式输出Hook"""
        workspace = Path(tempfile.mkdtemp())
        bus = MagicMock()
        console = MagicMock()

        try:
            with patch("src.core.plan.gateway_integration.StreamingHook") as MockHook:
                mock_hook = MagicMock()
                MockHook.return_value = mock_hook

                integration = GatewayIntegration(
                    workspace=workspace,
                    bus=bus,
                    console=console,
                )
                hook = integration.setup_streaming_hook(
                    channel="feishu",
                    chat_id="test_chat",
                )

                assert hook is mock_hook
                assert integration.streaming_hook is mock_hook

                MockHook.assert_called_once_with(
                    console=console,
                    bus=bus,
                    channel="feishu",
                    chat_id="test_chat",
                )
        finally:
            import shutil

            shutil.rmtree(workspace, ignore_errors=True)

    def test_get_hooks(self):
        """测试获取Hooks列表"""
        workspace = Path(tempfile.mkdtemp())

        try:
            integration = GatewayIntegration(workspace)

            # 没有设置streaming_hook时应该返回空列表
            hooks = integration.get_hooks()
            assert hooks == []

            # 设置streaming_hook后应该返回包含该hook的列表
            integration.streaming_hook = MagicMock()
            hooks = integration.get_hooks()
            assert len(hooks) == 1
        finally:
            import shutil

            shutil.rmtree(workspace, ignore_errors=True)

    def test_get_cron_status_disabled(self):
        """测试获取未初始化的Cron状态"""
        workspace = Path(tempfile.mkdtemp())

        try:
            integration = GatewayIntegration(workspace)
            status = integration.get_cron_status()

            assert status["enabled"] is False
            assert "message" in status
        finally:
            import shutil

            shutil.rmtree(workspace, ignore_errors=True)

    def test_get_cron_status_enabled(self):
        """测试获取已启用的Cron状态"""
        workspace = Path(tempfile.mkdtemp())

        try:
            with patch("src.core.plan.gateway_integration.CronService") as MockCron:
                mock_cron = MagicMock()
                mock_cron.status.return_value = {"jobs": 2}
                mock_cron.list_jobs.return_value = []
                MockCron.return_value = mock_cron

                integration = GatewayIntegration(workspace)
                integration.setup_cron_service(auto_register_reminder=False)

                status = integration.get_cron_status()

                assert status["enabled"] is True
                assert status["jobs_count"] == 2
        finally:
            import shutil

            shutil.rmtree(workspace, ignore_errors=True)

    def test_shutdown(self):
        """测试关闭组件"""
        workspace = Path(tempfile.mkdtemp())

        try:
            with patch("src.core.plan.gateway_integration.CronService") as MockCron:
                mock_cron = MagicMock()
                mock_cron.list_jobs.return_value = []
                MockCron.return_value = mock_cron

                integration = GatewayIntegration(workspace)
                integration.setup_cron_service(auto_register_reminder=False)
                integration.setup_streaming_hook()

                # 验证组件已初始化
                assert integration.cron_service is not None
                assert integration.streaming_hook is not None

                # 关闭组件
                integration.shutdown()

                # 验证组件已清理
                assert integration.cron_service is None
                assert integration.reminder_manager is None
                assert integration.cron_callback is None
                assert integration.streaming_hook is None

                # 验证Cron服务已停止
                mock_cron.stop.assert_called_once()
        finally:
            import shutil

            shutil.rmtree(workspace, ignore_errors=True)
