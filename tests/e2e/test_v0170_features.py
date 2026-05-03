"""
v0.17.0 端到端测试

测试范围：
- Hook组合系统端到端流程
- Subagent调用完整链路
- Cron训练提醒触发
- 配置热加载
- 多通道配置管理
- LLM超时控制
- 异步用户确认
- 网关集成

"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.core.config.channels import ChannelManager, ChannelType
from src.core.config.manager import ConfigManager
from src.core.plan.ask_user_confirm import (
    AskUserConfirmManager,
    ConfirmScenario,
    ConfirmStatus,
)
from src.core.plan.cron_callback import CronCallbackHandler
from src.core.plan.gateway_integration import GatewayIntegration
from src.core.plan.heartbeat_tasks import (
    HeartbeatTask,
    HeartbeatTaskManager,
    HeartbeatTaskType,
)
from src.core.plan.training_reminder_manager import TrainingReminderManager
from src.core.transparency.error_handling_hook import ErrorHandlingHook
from src.core.transparency.hook_integration import ObservabilityHook
from src.core.transparency.progress_hook import ProgressDisplayHook
from src.core.transparency.streaming_hook import StreamingHook


class TestHookSystemE2E:
    """Hook组合系统端到端测试"""

    def test_progress_hook_creation(self) -> None:
        """测试进度Hook创建"""
        console = MagicMock()
        hook = ProgressDisplayHook(console=console)
        assert hook is not None
        assert hook.get_pending_tools() == {}

    def test_error_handling_hook_creation(self) -> None:
        """测试错误处理Hook创建"""
        console = MagicMock()
        hook = ErrorHandlingHook(console=console)
        assert hook is not None
        assert hook._last_error is None

    def test_streaming_hook_creation(self) -> None:
        """测试流式输出Hook创建"""
        console = MagicMock()
        hook = StreamingHook(console=console)
        assert hook is not None
        assert hook.wants_streaming() is True

    def test_observability_hook_creation(self) -> None:
        """测试可观测性Hook创建"""
        manager = MagicMock()
        hook = ObservabilityHook(manager=manager)
        assert hook is not None
        assert hook.get_iteration_count() == 0

    @pytest.mark.asyncio
    async def test_progress_hook_execution(self) -> None:
        """测试进度Hook执行流程"""
        console = MagicMock()
        hook = ProgressDisplayHook(console=console)

        tc = MagicMock()
        tc.name = "test_tool"
        ctx = MagicMock()
        ctx.tool_calls = [tc]

        await hook.before_execute_tools(ctx)
        assert "test_tool" in hook.get_pending_tools()
        console.print.assert_called_once_with("🔧 正在调用: test_tool ...")

        await hook.after_iteration(ctx)
        assert hook.get_pending_tools() == {}

    def test_hook_reset(self) -> None:
        """测试Hook重置功能"""
        console = MagicMock()
        hook = ProgressDisplayHook(console=console)

        tc = MagicMock()
        tc.name = "test_tool"
        ctx = MagicMock()
        ctx.tool_calls = [tc]

        import asyncio

        asyncio.run(hook.before_execute_tools(ctx))
        assert "test_tool" in hook.get_pending_tools()

        hook.reset()
        assert hook.get_pending_tools() == {}


class TestSubagentE2E:
    """Subagent架构端到端测试"""

    def test_subagent_tool_exists(self) -> None:
        """测试Subagent工具存在"""
        from src.agents.tools import RunnerTools, SpawnSubagentTool

        runner_tools = MagicMock(spec=RunnerTools)
        tool = SpawnSubagentTool(runner_tools=runner_tools)
        assert tool.name == "spawn_subagent"
        assert "data_analyst" in tool.description
        assert "report_writer" in tool.description

    def test_subagent_tool_parameters(self) -> None:
        """测试Subagent工具参数"""
        from src.agents.tools import RunnerTools, SpawnSubagentTool

        runner_tools = MagicMock(spec=RunnerTools)
        tool = SpawnSubagentTool(runner_tools=runner_tools)
        params = tool.parameters
        assert "subagent_type" in params["properties"]
        assert "user_request" in params["properties"]
        assert "date_range" in params["properties"]
        assert "report_type" in params["properties"]

    def test_subagent_types_in_description(self) -> None:
        """测试Subagent类型在工具描述中"""
        from src.agents.tools import RunnerTools, SpawnSubagentTool

        runner_tools = MagicMock(spec=RunnerTools)
        tool = SpawnSubagentTool(runner_tools=runner_tools)
        assert "data_analyst" in tool.description
        assert "report_writer" in tool.description


class TestCronReminderE2E:
    """Cron训练提醒端到端测试"""

    def test_training_reminder_manager_creation(self) -> None:
        """测试训练提醒管理器创建"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TrainingReminderManager(data_dir=Path(tmpdir))
            assert manager is not None
            assert manager.schedule is not None

    def test_reminder_manager_schedule(self) -> None:
        """测试提醒管理器调度配置"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TrainingReminderManager(data_dir=Path(tmpdir))
            schedule = manager.schedule

            assert schedule.enabled is True
            assert schedule.cron_expression == "0 7 * * *"
            assert schedule.advance_minutes == 30

    def test_reminder_manager_update_schedule(self) -> None:
        """测试提醒管理器更新配置"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TrainingReminderManager(data_dir=Path(tmpdir))

            updated = manager.update_schedule(
                enabled=False,
                cron_expression="0 8 * * *",
                advance_minutes=60,
            )

            assert updated.enabled is False
            assert updated.cron_expression == "0 8 * * *"
            assert updated.advance_minutes == 60

    def test_reminder_today_status(self) -> None:
        """测试今日提醒状态"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TrainingReminderManager(data_dir=Path(tmpdir))
            status = manager.get_today_status()

            assert "has_record" in status
            assert "status" in status

    def test_reminder_history(self) -> None:
        """测试提醒历史记录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TrainingReminderManager(data_dir=Path(tmpdir))
            history = manager.get_history(days=7)

            assert isinstance(history, list)

    def test_cron_callback_handler_creation(self) -> None:
        """测试Cron回调处理器创建"""
        with tempfile.TemporaryDirectory() as tmpdir:
            reminder_manager = TrainingReminderManager(data_dir=Path(tmpdir))
            handler = CronCallbackHandler(reminder_manager=reminder_manager)
            assert handler is not None


class TestConfigHotReloadE2E:
    """配置热加载端到端测试"""

    def test_config_manager_reload(self) -> None:
        """测试配置管理器重新加载"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.json"
            config_file.write_text(
                json.dumps(
                    {"version": "0.17.0", "data_dir": str(tmpdir), "key": "value1"}
                ),
                encoding="utf-8",
            )

            with patch.dict(os.environ, {"NANOBOT_CONFIG_FILE": str(config_file)}):
                ConfigManager.reset_cache()
                manager = ConfigManager()

                # 初始加载
                config = manager.load_config(use_cache=False)
                assert config["key"] == "value1"

                # 修改配置
                config_file.write_text(
                    json.dumps(
                        {"version": "0.17.0", "data_dir": str(tmpdir), "key": "value2"}
                    ),
                    encoding="utf-8",
                )

                # 强制重新加载
                config = manager.reload_config()
                assert config["key"] == "value2"

    def test_config_cache_invalidation(self) -> None:
        """测试配置缓存失效"""
        ConfigManager.reset_cache()
        assert ConfigManager._cache is None
        assert ConfigManager._cache_time == 0

    def test_config_with_env_override(self) -> None:
        """测试环境变量覆盖配置"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.json"
            config_file.write_text(
                json.dumps(
                    {
                        "version": "0.17.0",
                        "data_dir": str(tmpdir),
                        "llm_provider": "openai",
                    }
                ),
                encoding="utf-8",
            )

            env_vars = {
                "NANOBOT_CONFIG_FILE": str(config_file),
                "NANOBOT_LLM_PROVIDER": "anthropic",
            }
            with patch.dict(os.environ, env_vars):
                ConfigManager.reset_cache()
                manager = ConfigManager()
                config = manager.load_config_with_env_override()
                assert config["llm_provider"] == "anthropic"


class TestMultiChannelConfigE2E:
    """多通道配置端到端测试"""

    def test_channel_manager_creation(self) -> None:
        """测试通道管理器创建"""
        manager = ChannelManager()
        assert manager is not None
        assert manager.channel_count == 0
        assert manager.enabled_count == 0

    def test_channel_add_and_get(self) -> None:
        """测试添加和获取通道"""
        from src.core.config.channels import FeishuChannelConfig

        manager = ChannelManager()
        config = FeishuChannelConfig(
            app_id="test_app_id",
            app_secret="test_secret",
            receive_id="test_user",
        )

        manager.add_channel("feishu", config)
        assert manager.channel_count == 1
        assert manager.enabled_count == 1

        retrieved = manager.get_channel("feishu")
        assert retrieved is not None
        assert retrieved.channel_type == ChannelType.FEISHU

    def test_channel_enable_disable(self) -> None:
        """测试通道启用禁用"""
        from src.core.config.channels import FeishuChannelConfig

        manager = ChannelManager()
        config = FeishuChannelConfig()
        manager.add_channel("feishu", config)

        assert manager.enabled_count == 1

        manager.disable_channel("feishu")
        assert manager.enabled_count == 0

        manager.enable_channel("feishu")
        assert manager.enabled_count == 1

    def test_channel_filter_by_type(self) -> None:
        """测试按类型筛选通道"""
        from src.core.config.channels import EmailChannelConfig, FeishuChannelConfig

        manager = ChannelManager()
        manager.add_channel("feishu", FeishuChannelConfig())
        manager.add_channel("email", EmailChannelConfig())

        feishu_channels = manager.get_channels_by_type(ChannelType.FEISHU)
        assert len(feishu_channels) == 1
        assert "feishu" in feishu_channels

    def test_channel_to_dict(self) -> None:
        """测试通道配置序列化"""
        from src.core.config.channels import FeishuChannelConfig

        manager = ChannelManager()
        config = FeishuChannelConfig(app_id="test_id")
        manager.add_channel("feishu", config)

        data = manager.to_dict()
        assert "feishu" in data
        assert data["feishu"]["type"] == "feishu"


class TestAskUserConfirmE2E:
    """异步用户确认端到端测试"""

    def test_training_plan_confirm_flow(self) -> None:
        """测试训练计划确认完整流程"""
        manager = AskUserConfirmManager()

        # 创建确认提示
        prompt = manager.create_plan_confirm_prompt(
            plan_id="plan_e2e_001",
            plan_summary={
                "goal": "半马破2",
                "weeks": 12,
                "weekly_volume_km": 40,
            },
        )

        assert prompt.scenario == ConfirmScenario.TRAINING_PLAN
        assert "半马破2" in prompt.message
        assert len(prompt.options) == 3

        # 模拟用户确认
        result = manager.parse_user_response("plan_e2e_001", "confirm")
        assert result.status == ConfirmStatus.CONFIRMED
        assert result.selected_key == "confirm"
        assert result.is_confirmed is True

        # 确认后应从待确认列表移除
        assert manager.has_pending_confirm("plan_e2e_001") is False

    def test_rpe_feedback_flow(self) -> None:
        """测试RPE反馈完整流程"""
        manager = AskUserConfirmManager()

        prompt = manager.create_rpe_prompt(
            session_id="session_e2e_001",
            session_summary={"distance_km": 15, "duration_min": 90},
        )

        assert prompt.scenario == ConfirmScenario.RPE_FEEDBACK
        assert len(prompt.options) == 10

        # 模拟用户评分
        result = manager.parse_user_response("session_e2e_001", "7")
        assert result.status == ConfirmStatus.CONFIRMED
        assert result.selected_key == "7"

    def test_injury_risk_flow(self) -> None:
        """测试伤病风险确认流程"""
        manager = AskUserConfirmManager()

        prompt = manager.create_injury_risk_prompt(
            plan_id="risk_e2e_001",
            risk_level="high",
            suggestions=[
                {"content": "减少跑量", "priority": "high"},
                {"content": "增加休息日", "priority": "medium"},
            ],
        )

        assert prompt.scenario == ConfirmScenario.INJURY_RISK_ADJUSTMENT
        assert len(prompt.options) == 3

        result = manager.parse_user_response("risk_e2e_001", "accept")
        assert result.status == ConfirmStatus.CONFIRMED

    def test_confirm_rejection(self) -> None:
        """测试确认拒绝"""
        manager = AskUserConfirmManager()

        manager.create_plan_confirm_prompt("plan_reject_001", {"goal": "测试"})
        result = manager.parse_user_response("plan_reject_001", "拒绝")

        assert result.status == ConfirmStatus.REJECTED
        assert result.is_confirmed is False

    def test_confirm_history_tracking(self) -> None:
        """测试确认历史追踪"""
        manager = AskUserConfirmManager()

        manager.create_plan_confirm_prompt("plan_hist_001", {"goal": "测试"})
        manager.parse_user_response("plan_hist_001", "confirm")

        history = manager.get_confirm_history()
        assert len(history) == 1
        assert history[0]["scenario"] == "training_plan"
        assert history[0]["result"]["status"] == "confirmed"

    def test_invalid_prompt_id(self) -> None:
        """测试无效提示ID"""
        manager = AskUserConfirmManager()

        result = manager.parse_user_response("nonexistent_id", "confirm")
        assert result.status == ConfirmStatus.REJECTED
        assert result.is_confirmed is False


class TestGatewayIntegrationE2E:
    """网关集成端到端测试"""

    def test_gateway_integration_creation(self) -> None:
        """测试网关集成器创建"""
        with tempfile.TemporaryDirectory() as tmpdir:
            integration = GatewayIntegration(workspace=Path(tmpdir))
            assert integration is not None

    def test_gateway_cron_status(self) -> None:
        """测试网关Cron状态"""
        with tempfile.TemporaryDirectory() as tmpdir:
            integration = GatewayIntegration(workspace=Path(tmpdir))
            status = integration.get_cron_status()

            assert isinstance(status, dict)
            assert "enabled" in status

    def test_gateway_shutdown(self) -> None:
        """测试网关关闭"""
        with tempfile.TemporaryDirectory() as tmpdir:
            integration = GatewayIntegration(workspace=Path(tmpdir))
            integration.shutdown()
            assert integration.cron_service is None


class TestHeartbeatTasksE2E:
    """Heartbeat任务端到端测试"""

    def test_task_manager_creation(self) -> None:
        """测试任务管理器创建"""
        manager = HeartbeatTaskManager()
        assert manager is not None
        assert manager.task_count == 0

    def test_task_registration(self) -> None:
        """测试任务注册"""
        from src.core.plan.heartbeat_tasks import TaskPriority

        manager = HeartbeatTaskManager()

        def test_handler() -> str:
            return "test"

        task = HeartbeatTask(
            name="test_task",
            task_type=HeartbeatTaskType.HEALTH_CHECK,
            priority=TaskPriority.NORMAL,
            enabled=True,
            handler=test_handler,
            interval_seconds=60,
        )

        manager.register_task(task)
        assert manager.task_count == 1
        assert "test_task" in manager

    def test_task_execution(self) -> None:
        """测试任务执行"""
        from src.core.plan.heartbeat_tasks import TaskPriority

        manager = HeartbeatTaskManager()
        execution_count = [0]

        def counting_task() -> None:
            execution_count[0] += 1

        task = HeartbeatTask(
            name="count_task",
            task_type=HeartbeatTaskType.HEALTH_CHECK,
            priority=TaskPriority.NORMAL,
            enabled=True,
            handler=counting_task,
            interval_seconds=1,
        )

        manager.register_task(task)
        manager.execute_task("count_task")
        assert execution_count[0] == 1

        manager.execute_task("count_task")
        assert execution_count[0] == 2

    def test_task_enable_disable(self) -> None:
        """测试任务启用禁用"""
        from src.core.plan.heartbeat_tasks import TaskPriority

        manager = HeartbeatTaskManager()

        task = HeartbeatTask(
            name="toggle_task",
            task_type=HeartbeatTaskType.HEALTH_CHECK,
            priority=TaskPriority.NORMAL,
            enabled=True,
            handler=lambda: None,
            interval_seconds=60,
        )

        manager.register_task(task)
        assert manager.get_task_status("toggle_task")["enabled"] is True

        manager.disable_task("toggle_task")
        assert manager.get_task_status("toggle_task")["enabled"] is False

        manager.enable_task("toggle_task")
        assert manager.get_task_status("toggle_task")["enabled"] is True


class TestV0170IntegrationE2E:
    """v0.17.0整体集成端到端测试"""

    def test_multiple_features_together(self) -> None:
        """测试多个功能协同工作"""
        # 1. 创建Hook
        console = MagicMock()
        progress_hook = ProgressDisplayHook(console=console)

        # 2. 创建提醒管理器
        with tempfile.TemporaryDirectory() as tmpdir:
            reminder_manager = TrainingReminderManager(data_dir=Path(tmpdir))

            # 3. 创建确认管理器
            confirm_manager = AskUserConfirmManager()

            # 验证所有组件可以共存
            assert progress_hook is not None
            assert reminder_manager is not None
            assert confirm_manager is not None

            # 验证可以创建确认
            prompt = confirm_manager.create_plan_confirm_prompt(
                "integration_plan",
                {"goal": "集成测试"},
            )
            assert confirm_manager.has_pending_confirm("integration_plan") is True

            # 验证提醒管理器配置
            assert reminder_manager.schedule.enabled is True

    def test_error_handling_flow(self) -> None:
        """测试错误处理流程"""
        console = MagicMock()
        error_hook = ErrorHandlingHook(console=console)

        # 验证错误Hook可以处理错误
        assert error_hook._last_error is None

        # 模拟错误上下文
        friendly_error = MagicMock()
        friendly_error.category.value = "test"
        friendly_error.friendly_message = "测试错误"
        friendly_error.recovery_suggestion = "重试"

        with patch(
            "src.core.transparency.error_handling_hook.ErrorClassifier.classify",
            return_value=friendly_error,
        ):
            ctx = MagicMock()
            ctx.error = ValueError("测试错误")
            ctx.tool_calls = []

            import asyncio

            asyncio.run(error_hook.after_iteration(ctx))

            assert error_hook._last_error is not None

    def test_config_priority_resolution(self) -> None:
        """测试配置优先级解析端到端"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.json"
            config_file.write_text(
                json.dumps(
                    {
                        "version": "0.17.0",
                        "data_dir": str(tmpdir),
                        "llm_provider": "openai",
                    }
                ),
                encoding="utf-8",
            )

            env_vars = {
                "NANOBOT_CONFIG_FILE": str(config_file),
                "NANOBOT_LLM_PROVIDER": "anthropic",
            }
            with patch.dict(os.environ, env_vars):
                ConfigManager.reset_cache()
                manager = ConfigManager()
                config = manager.load_config_with_env_override()

                # 环境变量应该覆盖文件配置
                assert config.get("llm_provider") == "anthropic"

    def test_end_to_end_user_journey(self) -> None:
        """端到端用户旅程测试"""
        # 模拟用户创建训练计划并确认的完整流程

        # 1. 创建确认管理器
        manager = AskUserConfirmManager()

        # 2. 生成训练计划确认
        prompt = manager.create_plan_confirm_prompt(
            plan_id="journey_plan_001",
            plan_summary={
                "goal": "全马破4",
                "weeks": 16,
                "weekly_volume_km": 50,
            },
        )

        # 3. 验证提示内容
        agent_prompt = prompt.to_agent_prompt()
        assert "全马破4" in agent_prompt
        assert "16 周" in agent_prompt

        # 4. 模拟用户确认
        result = manager.parse_user_response("journey_plan_001", "确认采用")
        assert result.is_confirmed is True
        assert result.selected_key == "confirm"

        # 5. 验证历史记录
        history = manager.get_confirm_history()
        assert len(history) == 1
        assert history[0]["result"]["selected_key"] == "confirm"

    def test_streaming_hook_dual_channel(self) -> None:
        """测试流式输出双通道"""
        console = MagicMock()
        bus = MagicMock()

        hook = StreamingHook(
            console=console,
            bus=bus,
            channel="test_channel",
            chat_id="test_chat",
        )

        ctx = MagicMock()

        import asyncio

        asyncio.run(hook.on_stream(ctx, "Hello"))

        # 验证CLI通道输出
        console.print.assert_called_with("Hello", end="")

        # 验证Gateway通道输出
        bus.publish_outbound.assert_called_once()


@pytest.mark.slow
class TestPerformanceE2E:
    """性能端到端测试"""

    def test_confirm_manager_scaling(self) -> None:
        """测试确认管理器扩展性"""
        manager = AskUserConfirmManager()

        # 创建大量确认
        for i in range(100):
            manager.create_plan_confirm_prompt(f"plan_{i}", {"goal": f"测试{i}"})

        # 验证待确认数量
        pending_count = sum(1 for _ in manager._pending_confirms)
        assert pending_count == 100

        # 解析应该仍然快速
        import time

        start = time.time()
        manager.parse_user_response("plan_50", "confirm")
        elapsed = time.time() - start

        assert elapsed < 1.0

    def test_channel_manager_scaling(self) -> None:
        """测试通道管理器扩展性"""
        from src.core.config.channels import FeishuChannelConfig

        manager = ChannelManager()

        # 创建大量通道
        for i in range(100):
            config = FeishuChannelConfig(app_id=f"app_{i}")
            manager.add_channel(f"feishu_{i}", config)

        assert manager.channel_count == 100
        assert manager.enabled_count == 100

        # 查询应该快速
        import time

        start = time.time()
        enabled = manager.get_enabled_channels()
        elapsed = time.time() - start

        assert len(enabled) == 100
        assert elapsed < 1.0
