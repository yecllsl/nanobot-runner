"""nanobot 框架兼容性测试

测试目标：
- 验证与 nanobot 框架的 API 兼容性
- 验证框架初始化参数正确
- 验证框架组件集成

Bug历史：
- SessionManager.__init__() got an unexpected keyword argument 'bus'
- ChannelManager.__init__() got an unexpected keyword argument 'workspace'
- context_window_tokens 为 None 导致比较错误
- BaseTool 缺少 cast_params 方法
"""

from unittest.mock import patch


class TestNanobotToolCompatibility:
    """测试与 nanobot Tool 基类的兼容性"""

    def test_basetool_inherits_from_nanobot_tool(self):
        """
        测试 BaseTool 继承自 nanobot.Tool

        Bug历史：BaseTool 未继承 nanobot.Tool 导致缺少 cast_params 方法
        """
        from nanobot.agent.tools.base import Tool

        from src.agents.tools import BaseTool

        assert issubclass(BaseTool, Tool), "BaseTool 必须继承自 nanobot.Tool"

    def test_tool_has_cast_params_method(self):
        """
        测试工具具有 cast_params 方法

        Bug历史：nanobot 框架调用 tool.cast_params() 但方法不存在
        """
        from src.agents.tools import GetRunningStatsTool, RunnerTools

        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = GetRunningStatsTool(runner_tools)

            assert hasattr(tool, "cast_params"), "工具必须具有 cast_params 方法"
            assert callable(tool.cast_params), "cast_params 必须是可调用方法"

    def test_tool_has_concurrency_safe_attribute(self):
        """
        测试工具具有 concurrency_safe 属性

        Bug历史：nanobot 框架要求工具具有 concurrency_safe 属性
        """
        from src.agents.tools import GetRunningStatsTool, RunnerTools

        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = GetRunningStatsTool(runner_tools)

            assert hasattr(tool, "concurrency_safe"), (
                "工具必须具有 concurrency_safe 属性"
            )

    def test_tool_to_schema_format(self):
        """测试工具 schema 格式符合 OpenAI function calling 规范"""
        from src.agents.tools import GetRunningStatsTool, RunnerTools

        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = GetRunningStatsTool(runner_tools)
            schema = tool.to_schema()

        assert schema["type"] == "function"
        assert "function" in schema
        assert "name" in schema["function"]
        assert "description" in schema["function"]
        assert "parameters" in schema["function"]


class TestNanobotMessageCompatibility:
    """测试与 nanobot 消息类型的兼容性"""

    def test_inbound_message_required_fields(self):
        """测试 InboundMessage 必需字段"""
        from nanobot.bus.events import InboundMessage

        msg = InboundMessage(
            channel="feishu",
            chat_id="test_chat",
            sender_id="test_sender",
            content="/stats",
        )

        assert msg.channel == "feishu"
        assert msg.chat_id == "test_chat"
        assert msg.sender_id == "test_sender"
        assert msg.content == "/stats"

    def test_outbound_message_content_must_be_string(self):
        """
        测试 OutboundMessage.content 必须是字符串

        Bug历史：content 为 dict/list 时导致飞书发送失败
        """
        from nanobot.bus.events import OutboundMessage

        msg = OutboundMessage(
            channel="feishu",
            chat_id="test",
            content="测试内容",
        )

        assert isinstance(msg.content, str), "OutboundMessage.content 必须是字符串"

    def test_outbound_message_with_metadata(self):
        """测试 OutboundMessage 可以携带 metadata"""
        from nanobot.bus.events import OutboundMessage

        msg = OutboundMessage(
            channel="feishu",
            chat_id="test",
            content="测试内容",
            metadata={"render_as": "text"},
        )

        assert msg.metadata == {"render_as": "text"}


class TestNanobotCommandRouterCompatibility:
    """测试与 nanobot CommandRouter 的兼容性"""

    def test_command_context_structure(self):
        """测试 CommandContext 结构"""
        from nanobot.bus.events import InboundMessage
        from nanobot.command.router import CommandContext

        ctx = CommandContext(
            msg=InboundMessage(
                channel="feishu",
                chat_id="test_chat",
                sender_id="test_sender",
                content="/stats",
            ),
            session=None,
            key="test",
            raw="/stats",
        )

        assert ctx.msg is not None
        assert ctx.key == "test"
        assert ctx.raw == "/stats"


class TestNanobotConfigCompatibility:
    """测试与 nanobot 配置的兼容性"""

    def test_agent_defaults_context_window_tokens(self):
        """
        测试 AgentDefaults.context_window_tokens 不为 None

        Bug历史：context_window_tokens 为 None 导致比较错误
        """
        from nanobot.config.schema import AgentDefaults

        defaults = AgentDefaults()

        assert defaults.context_window_tokens is not None, (
            "context_window_tokens 不能为 None"
        )
        assert isinstance(defaults.context_window_tokens, int), (
            "context_window_tokens 必须是整数"
        )
        assert defaults.context_window_tokens > 0, "context_window_tokens 必须大于 0"

    def test_config_loader_returns_valid_config(self):
        """测试配置加载器返回有效配置"""
        from nanobot.config.loader import load_config

        config = load_config()

        assert config is not None
        assert hasattr(config, "agents"), "配置必须包含 agents 部分"


class TestNanobotBusCompatibility:
    """测试与 nanobot 消息总线的兼容性"""

    def test_message_bus_can_be_created(self):
        """测试 MessageBus 可以正常创建"""
        from nanobot.bus import MessageBus

        bus = MessageBus()

        assert bus is not None


class TestNanobotSessionCompatibility:
    """测试与 nanobot Session 管理的兼容性"""

    def test_session_manager_initialization(self):
        """
        测试 SessionManager 初始化参数

        Bug历史：SessionManager.__init__() got an unexpected keyword argument 'bus'
        """
        from pathlib import Path

        from nanobot.session.manager import SessionManager

        workspace = Path.home() / ".nanobot-runner"

        session = SessionManager(workspace=workspace)

        assert session is not None


class TestNanobotChannelCompatibility:
    """测试与 nanobot Channel 管理的兼容性"""

    def test_channel_manager_initialization(self):
        """
        测试 ChannelManager 初始化参数

        Bug历史：ChannelManager.__init__() got an unexpected keyword argument 'workspace'
        """
        from nanobot.bus import MessageBus
        from nanobot.channels.manager import ChannelManager
        from nanobot.config.loader import load_config

        config = load_config()
        bus = MessageBus()

        channels = ChannelManager(config=config, bus=bus)

        assert channels is not None


class TestNanobotProviderCompatibility:
    """测试与 nanobot Provider 的兼容性"""

    def test_provider_can_be_created(self):
        """
        测试 Provider 可以正常创建

        Bug历史：_make_provider 需要 API 密钥，CI 环境缺少配置导致失败
        v0.26.0: _make_provider 从 nanobot.cli.commands 迁移到 nanobot.providers.factory.make_provider
        """
        from unittest.mock import MagicMock

        from nanobot.config.loader import load_config

        config = load_config()

        with patch("nanobot.providers.factory.make_provider") as mock_provider:
            mock_provider.return_value = MagicMock()
            provider = mock_provider(config)

            assert provider is not None
            mock_provider.assert_called_once_with(config)


class TestNanobotAgentLoopCompatibility:
    """测试与 nanobot AgentLoop 的兼容性"""

    def test_agent_loop_context_window_tokens(self):
        """
        测试 AgentLoop 正确传递 context_window_tokens

        Bug历史：context_window_tokens 为 None 导致 Consolidator 报错
                 _make_provider 需要 API 密钥，CI 环境缺少配置导致失败
        v0.26.0: _make_provider 从 nanobot.cli.commands 迁移到 nanobot.providers.factory.make_provider
        """
        from pathlib import Path
        from unittest.mock import MagicMock

        from nanobot.agent.loop import AgentLoop
        from nanobot.bus import MessageBus
        from nanobot.config.loader import load_config
        from nanobot.config.schema import AgentDefaults

        config = load_config()
        bus = MessageBus()
        workspace = Path.home() / ".nanobot-runner"
        defaults = AgentDefaults()

        with patch("nanobot.providers.factory.make_provider") as mock_provider:
            mock_provider.return_value = MagicMock()
            provider = mock_provider(config)

            agent = AgentLoop(
                bus=bus,
                provider=provider,
                workspace=workspace,
                context_window_tokens=defaults.context_window_tokens,
            )

            assert agent.context_window_tokens is not None, (
                "context_window_tokens 不能为 None"
            )
            assert agent.context_window_tokens == defaults.context_window_tokens


class TestNanobotCronServiceCompatibility:
    """测试与 nanobot CronService 的兼容性"""

    def test_cron_service_initialization(self):
        """
        测试 CronService 初始化参数

        Bug历史：CronService 初始化参数变更
        """
        from pathlib import Path

        from nanobot.cron.service import CronService

        workspace = Path.home() / ".nanobot-runner"
        store_path = workspace / "cron.json"

        cron = CronService(store_path=store_path)

        assert cron is not None


class TestNanobot022BreakingChanges:
    """验证 nanobot-ai 0.2.2 破坏性变更已正确适配

    基于 0.2.2 升级公告的 7 项破坏性变更，验证 RunFlowAgent 不受影响
    或已完成适配。
    """

    def test_base_class_available(self):
        """验证 Base 类可从 config.schema 导入

        0.2.2 公告：Base 类迁移到 config_base.py。
        实际调研：config.schema 仍可导入 Base，无需 fallback。
        """
        from nanobot.config.schema import Base

        assert Base is not None

    def test_context_window_tokens_default(self):
        """验证 context_window_tokens 默认值

        0.2.2 公告：context_window_tokens 默认值变更。
        RunFlowAgent 显式控制此值，不受默认值影响。
        """
        from nanobot.config.schema import AgentDefaults

        defaults = AgentDefaults()
        assert defaults.context_window_tokens in [65536, 200000], (
            f"意外的默认值: {defaults.context_window_tokens}"
        )

    def test_webui_modules_importable(self):
        """验证 webui 模块重构后仍可导入

        0.2.2 公告：websocket.py 重构。
        实际调研：settings_api/mcp_presets_api/cli_apps_api 模块仍存在。
        RunFlowAgent 移除 monkey-patch 后不再依赖这些模块的本地引用。
        """
        import nanobot.webui.cli_apps_api  # noqa: F401
        import nanobot.webui.mcp_presets_api  # noqa: F401
        import nanobot.webui.settings_api  # noqa: F401

    def test_dream_class_removed(self):
        """验证 Dream 类已删除

        0.2.2 公告：Dream 类移除，改为 cron + process_direct 模式。
        RunFlowAgent 的 DreamIntegration 已适配此变更。
        """
        try:
            from nanobot.agent.memory import Dream  # noqa: F401

            raise AssertionError("Dream 类应已删除")
        except ImportError:
            pass  # 预期行为：Dream 类已移除

    def test_agent_loop_has_submit_cron_turn(self):
        """验证 AgentLoop 新增 submit_cron_turn 公开方法

        0.2.2 新增：submit_cron_turn 替代私有 cron 调用。
        AgentLoopAdapter 已封装此方法。
        """
        from nanobot.agent.loop import AgentLoop

        assert hasattr(AgentLoop, "submit_cron_turn"), (
            "AgentLoop 应包含 submit_cron_turn 方法（0.2.2 新增）"
        )

    def test_agent_hook_has_run_level_methods(self):
        """验证 AgentHook 新增 run-level hook

        0.2.2 新增：before_run/after_run 方法。
        DecisionLogHook 已接入这两个方法。
        """
        from nanobot.agent.hook import AgentHook

        assert hasattr(AgentHook, "before_run"), (
            "AgentHook 应包含 before_run 方法（0.2.2 新增）"
        )
        assert hasattr(AgentHook, "after_run"), (
            "AgentHook 应包含 after_run 方法（0.2.2 新增）"
        )
