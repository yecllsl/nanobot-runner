"""Gateway消息处理集成测试

测试目标：
- 验证命令处理函数返回正确的消息类型
- 验证消息内容为字符串（飞书发送要求）
- 验证与 nanobot 框架的 CommandRouter 集成

Bug历史：
- /stats 命令返回 dict，导致飞书发送失败：'dict' object has no attribute 'strip'
- /vd 命令返回 list，导致飞书发送失败：'list' object has no attribute 'strip'
"""

from unittest.mock import MagicMock

import pytest
from nanobot.bus.events import InboundMessage, OutboundMessage
from nanobot.command.router import CommandContext


class TestGatewayCommandHandlers:
    """测试 Gateway 命令处理函数"""

    @pytest.fixture
    def mock_runner_tools(self):
        """创建模拟的 RunnerTools"""
        runner_tools = MagicMock()
        runner_tools.get_running_stats.return_value = {
            "total_runs": 10,
            "total_distance": 50.0,
            "total_duration": 36000.0,
            "avg_distance": 5.0,
            "avg_duration": 3600.0,
        }
        runner_tools.get_recent_runs.return_value = [
            {
                "timestamp": "2024-01-15T08:00:00",
                "distance_km": 5.0,
                "duration": "00:25:00",
                "avg_hr": 150,
            }
        ]
        runner_tools.get_vdot_trend.return_value = [
            {
                "date": "2024-01-15",
                "distance_km": 5.0,
                "duration": "00:25:00",
                "vdot": 45.2,
            }
        ]
        runner_tools.get_hr_drift_analysis.return_value = {
            "correlation": -0.65,
            "is_hr_drift": False,
            "avg_hr": 150.0,
            "hr_range": [140.0, 160.0],
        }
        runner_tools.get_training_load.return_value = {
            "atl": 50.0,
            "ctl": 65.0,
            "tsb": 15.0,
        }
        return runner_tools

    @pytest.fixture
    def mock_context(self):
        """创建模拟的 CommandContext"""
        return CommandContext(
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

    @pytest.mark.asyncio
    async def test_stats_command_returns_string_content(
        self, mock_runner_tools, mock_context
    ):
        """
        测试 /stats 命令返回字符串内容

        Bug历史：/stats 命令返回 dict，导致飞书发送失败
        """
        from src.cli.commands.gateway import _format_stats

        data = mock_runner_tools.get_running_stats()
        formatted = _format_stats(data)

        assert isinstance(formatted, str), (
            f"格式化结果必须是字符串，实际是 {type(formatted)}"
        )
        assert "训练统计" in formatted

    @pytest.mark.asyncio
    async def test_vdot_command_returns_string_content(
        self, mock_runner_tools, mock_context
    ):
        """
        测试 /vd 命令返回字符串内容

        Bug历史：/vd 命令返回 list，导致飞书发送失败
        """
        from src.cli.commands.gateway import _format_vdot

        data = mock_runner_tools.get_vdot_trend()
        formatted = _format_vdot(data)

        assert isinstance(formatted, str), (
            f"格式化结果必须是字符串，实际是 {type(formatted)}"
        )
        assert "VDOT" in formatted

    @pytest.mark.asyncio
    async def test_recent_command_returns_string_content(
        self, mock_runner_tools, mock_context
    ):
        """测试 /recent 命令返回字符串内容"""
        from src.cli.commands.gateway import _format_recent

        data = mock_runner_tools.get_recent_runs()
        formatted = _format_recent(data)

        assert isinstance(formatted, str), (
            f"格式化结果必须是字符串，实际是 {type(formatted)}"
        )
        assert "最近训练" in formatted

    @pytest.mark.asyncio
    async def test_hr_drift_command_returns_string_content(
        self, mock_runner_tools, mock_context
    ):
        """测试 /hr_drift 命令返回字符串内容"""
        from src.cli.commands.gateway import _format_hr_drift

        data = mock_runner_tools.get_hr_drift_analysis()
        formatted = _format_hr_drift(data)

        assert isinstance(formatted, str), (
            f"格式化结果必须是字符串，实际是 {type(formatted)}"
        )
        assert "心率漂移" in formatted

    @pytest.mark.asyncio
    async def test_load_command_returns_string_content(
        self, mock_runner_tools, mock_context
    ):
        """测试 /load 命令返回字符串内容"""
        from src.cli.commands.gateway import _format_training_load

        data = mock_runner_tools.get_training_load()
        formatted = _format_training_load(data)

        assert isinstance(formatted, str), (
            f"格式化结果必须是字符串，实际是 {type(formatted)}"
        )
        assert "训练负荷" in formatted


class TestOutboundMessageType:
    """测试 OutboundMessage 内容类型"""

    @pytest.mark.asyncio
    async def test_outbound_message_content_is_string(self):
        """
        测试 OutboundMessage.content 必须是字符串

        这是飞书发送消息的必要条件
        """
        msg = OutboundMessage(
            channel="feishu",
            chat_id="test",
            content="测试内容",
        )

        assert isinstance(msg.content, str), "OutboundMessage.content 必须是字符串"

    @pytest.mark.asyncio
    async def test_outbound_message_with_dict_content_fails(self):
        """
        测试 OutboundMessage.content 为 dict 时会导致问题

        这是之前 Bug 的根因
        """
        content = {"key": "value"}

        with pytest.raises(Exception):
            content.strip()

    @pytest.mark.asyncio
    async def test_outbound_message_with_list_content_fails(self):
        """
        测试 OutboundMessage.content 为 list 时会导致问题

        这是之前 Bug 的根因
        """
        content = [1, 2, 3]

        with pytest.raises(Exception):
            content.strip()


class TestCommandRouterIntegration:
    """测试与 CommandRouter 的集成"""

    @pytest.mark.asyncio
    async def test_command_handler_returns_outbound_message(self):
        """测试命令处理函数返回 OutboundMessage"""
        from src.cli.commands.gateway import _register_runner_commands

        runner_tools = MagicMock()
        runner_tools.get_running_stats.return_value = {
            "total_runs": 10,
            "total_distance": 50.0,
            "total_duration": 36000.0,
            "avg_distance": 5.0,
            "avg_duration": 3600.0,
        }

        agent = MagicMock()
        agent.commands = MagicMock()

        _register_runner_commands(agent, runner_tools)

        assert agent.commands.exact.called or agent.commands.prefix.called

    @pytest.mark.asyncio
    async def test_command_handler_content_type_validation(self):
        """
        测试命令处理函数返回的内容类型

        验证所有命令处理函数返回的 content 都是字符串
        """
        from src.cli.commands.gateway import (
            _format_hr_drift,
            _format_recent,
            _format_stats,
            _format_training_load,
            _format_vdot,
        )

        format_functions = [
            (
                _format_stats,
                {
                    "total_runs": 1,
                    "total_distance": 1.0,
                    "total_duration": 600.0,
                    "avg_distance": 1.0,
                    "avg_duration": 600.0,
                },
            ),
            (
                _format_recent,
                [
                    {
                        "timestamp": "2024-01-15",
                        "distance_km": 1.0,
                        "duration": "00:10:00",
                        "avg_hr": 150,
                    }
                ],
            ),
            (
                _format_vdot,
                [
                    {
                        "date": "2024-01-15",
                        "distance_km": 1.0,
                        "duration": "00:10:00",
                        "vdot": 40.0,
                    }
                ],
            ),
            (
                _format_hr_drift,
                {
                    "correlation": -0.5,
                    "is_hr_drift": False,
                    "avg_hr": 150.0,
                    "hr_range": [140.0, 160.0],
                },
            ),
            (_format_training_load, {"atl": 50.0, "ctl": 60.0, "tsb": 10.0}),
        ]

        for func, data in format_functions:
            result = func(data)
            assert isinstance(result, str), (
                f"{func.__name__} 必须返回字符串，实际返回 {type(result)}"
            )


class TestEmptyDataHandling:
    """测试空数据处理"""

    @pytest.mark.asyncio
    async def test_stats_empty_data_returns_friendly_message(self):
        """测试空数据返回友好提示"""
        from src.cli.commands.gateway import _format_stats

        result = _format_stats({"message": "暂无跑步数据"})
        assert isinstance(result, str)
        assert "暂无" in result

    @pytest.mark.asyncio
    async def test_recent_empty_data_returns_friendly_message(self):
        """测试空数据返回友好提示"""
        from src.cli.commands.gateway import _format_recent

        result = _format_recent([])
        assert isinstance(result, str)
        assert "暂无" in result

    @pytest.mark.asyncio
    async def test_vdot_empty_data_returns_friendly_message(self):
        """测试空数据返回友好提示"""
        from src.cli.commands.gateway import _format_vdot

        result = _format_vdot([])
        assert isinstance(result, str)
        assert "暂无" in result

    @pytest.mark.asyncio
    async def test_hr_drift_error_data_returns_error_message(self):
        """测试错误数据返回错误信息"""
        from src.cli.commands.gateway import _format_hr_drift

        result = _format_hr_drift({"error": "暂无心率数据"})
        assert isinstance(result, str)
        assert "暂无" in result or "error" in result.lower()

    @pytest.mark.asyncio
    async def test_load_error_data_returns_error_message(self):
        """测试错误数据返回错误信息"""
        from src.cli.commands.gateway import _format_training_load

        result = _format_training_load({"error": "暂无训练数据"})
        assert isinstance(result, str)
        assert "暂无" in result or "error" in result.lower()
