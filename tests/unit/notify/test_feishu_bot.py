# 飞书机器人 Channel 单元测试

import asyncio
from unittest.mock import MagicMock, patch

import pytest
import requests

from src.notify.feishu import CommandType, FeishuBot, ParsedCommand


class TestCommandType:
    """测试 CommandType 枚举"""

    def test_command_type_values(self):
        """测试命令类型枚举值"""
        assert CommandType.STATS.value == "/stats"
        assert CommandType.IMPORT.value == "/import"
        assert CommandType.HELP.value == "/help"
        assert CommandType.RECENT.value == "/recent"
        assert CommandType.VD.value == "/vd"
        assert CommandType.HR_DRIFT.value == "/hr_drift"
        assert CommandType.LOAD.value == "/load"
        assert CommandType.UNKNOWN.value == "unknown"

    def test_command_type_from_string(self):
        """测试从字符串创建命令类型"""
        assert CommandType("/stats") == CommandType.STATS
        assert CommandType("/import") == CommandType.IMPORT
        assert CommandType("/help") == CommandType.HELP


class TestParsedCommand:
    """测试 ParsedCommand 数据结构"""

    def test_create_parsed_command(self):
        """测试创建解析后的命令"""
        cmd = ParsedCommand(
            command_type=CommandType.STATS,
            raw_text="/stats --year 2024",
            args=["--year", "2024"],
            chat_id="chat_123",
            user_id="user_456",
            message_id="msg_789",
        )

        assert cmd.command_type == CommandType.STATS
        assert cmd.raw_text == "/stats --year 2024"
        assert cmd.args == ["--year", "2024"]
        assert cmd.chat_id == "chat_123"
        assert cmd.user_id == "user_456"
        assert cmd.message_id == "msg_789"

    def test_create_parsed_command_optional_fields(self):
        """测试创建解析后的命令（可选字段）"""
        cmd = ParsedCommand(
            command_type=CommandType.HELP,
            raw_text="/help",
            args=[],
        )

        assert cmd.command_type == CommandType.HELP
        assert cmd.raw_text == "/help"
        assert cmd.args == []
        assert cmd.chat_id is None
        assert cmd.user_id is None
        assert cmd.message_id is None


class TestFeishuBotInit:
    """测试 FeishuBot 初始化"""

    @patch("src.notify.feishu.ConfigManager")
    def test_init_with_app_credentials(self, mock_config_manager):
        """测试使用应用凭证初始化"""
        mock_config_manager.return_value.get.return_value = None
        bot = FeishuBot(
            app_id="test_app_id",
            app_secret="test_app_secret",
            receive_id="test_user_id",
            receive_id_type="user_id",
        )

        assert bot.auth.app_id == "test_app_id"
        assert bot.auth.app_secret == "test_app_secret"
        assert bot.receive_id == "test_user_id"
        assert bot.receive_id_type == "user_id"
        assert bot._nanobot_feishu_enabled is None
        assert bot._feishu_channel is None
        assert len(bot._command_handlers) > 0

    @patch("src.notify.feishu.ConfigManager")
    def test_init_without_credentials_load_from_config(self, mock_config_manager):
        """测试无凭证时从配置加载"""
        mock_config = mock_config_manager.return_value
        mock_config.get.side_effect = lambda key, default=None: {
            "feishu_app_id": "config_app_id",
            "feishu_app_secret": "config_app_secret",
            "feishu_receive_id": "config_user_id",
            "feishu_receive_id_type": "user_id",
        }.get(key, default)

        bot = FeishuBot()

        assert bot.auth.app_id == "config_app_id"
        assert bot.auth.app_secret == "config_app_secret"
        assert bot.receive_id == "config_user_id"

    @patch("src.notify.feishu.ConfigManager")
    def test_init_command_handlers_registered(self, mock_config_manager):
        """测试初始化时命令处理器已注册"""
        mock_config_manager.return_value.get.return_value = None
        bot = FeishuBot()

        assert CommandType.HELP in bot._command_handlers
        assert CommandType.STATS in bot._command_handlers
        assert CommandType.RECENT in bot._command_handlers
        assert CommandType.VD in bot._command_handlers
        assert CommandType.HR_DRIFT in bot._command_handlers
        assert CommandType.LOAD in bot._command_handlers
        assert CommandType.IMPORT in bot._command_handlers


class TestFeishuBotParseMessage:
    """测试 FeishuBot 消息解析"""

    @pytest.fixture
    def bot(self):
        """创建 FeishuBot 实例"""
        with patch("src.notify.feishu.ConfigManager"):
            return FeishuBot()

    def test_parse_help_command(self, bot):
        """测试解析帮助命令"""
        message_data = {
            "content": "/help",
            "chat_id": "chat_123",
            "user_id": "user_456",
            "message_id": "msg_789",
        }

        cmd = bot.parse_message(message_data)

        assert cmd is not None
        assert cmd.command_type == CommandType.HELP
        assert cmd.raw_text == "/help"
        assert cmd.args == []
        assert cmd.chat_id == "chat_123"

    def test_parse_stats_command_with_args(self, bot):
        """测试解析统计命令（带参数）"""
        message_data = {
            "content": "/stats --year 2024 --start 2024-01-01",
            "chat_id": "chat_123",
        }

        cmd = bot.parse_message(message_data)

        assert cmd is not None
        assert cmd.command_type == CommandType.STATS
        assert cmd.args == ["--year", "2024", "--start", "2024-01-01"]

    def test_parse_import_command(self, bot):
        """测试解析导入命令"""
        message_data = {
            "content": "/import D:/garmin/activities",
            "chat_id": "chat_123",
        }

        cmd = bot.parse_message(message_data)

        assert cmd is not None
        assert cmd.command_type == CommandType.IMPORT
        assert cmd.args == ["D:/garmin/activities"]

    def test_parse_recent_command_with_count(self, bot):
        """测试解析最近记录命令（带数量）"""
        message_data = {
            "content": "/recent 10",
            "chat_id": "chat_123",
        }

        cmd = bot.parse_message(message_data)

        assert cmd is not None
        assert cmd.command_type == CommandType.RECENT
        assert cmd.args == ["10"]

    def test_parse_command_with_extra_whitespace(self, bot):
        """测试解析带空格的命令"""
        message_data = {
            "content": "  /help  ",
            "chat_id": "chat_123",
        }

        cmd = bot.parse_message(message_data)

        assert cmd is not None
        assert cmd.command_type == CommandType.HELP

    def test_parse_empty_content(self, bot):
        """测试解析空内容"""
        message_data = {
            "content": "",
            "chat_id": "chat_123",
        }

        cmd = bot.parse_message(message_data)

        assert cmd is None

    def test_parse_unknown_command(self, bot):
        """测试解析未知命令"""
        message_data = {
            "content": "/unknown_command",
            "chat_id": "chat_123",
        }

        cmd = bot.parse_message(message_data)

        assert cmd is None

    def test_parse_chinese_command(self, bot):
        """测试解析中文命令"""
        message_data = {
            "content": "/统计 --year 2024",
            "chat_id": "chat_123",
        }

        cmd = bot.parse_message(message_data)

        assert cmd is not None
        assert cmd.command_type == CommandType.STATS

    def test_parse_command_missing_metadata(self, bot):
        """测试解析缺少元数据的命令"""
        message_data = {
            "content": "/help",
        }

        cmd = bot.parse_message(message_data)

        assert cmd is not None
        assert cmd.command_type == CommandType.HELP
        assert cmd.chat_id is None
        assert cmd.user_id is None
        assert cmd.message_id is None


class TestFeishuBotExtractCommandType:
    """测试命令类型提取"""

    @pytest.fixture
    def bot(self):
        """创建 FeishuBot 实例"""
        with patch("src.notify.feishu.ConfigManager"):
            return FeishuBot()

    def test_extract_stats_command(self, bot):
        """测试提取统计命令类型"""
        assert bot._extract_command_type("/stats") == CommandType.STATS
        assert bot._extract_command_type("/stats --year 2024") == CommandType.STATS
        assert bot._extract_command_type("/统计") == CommandType.STATS

    def test_extract_import_command(self, bot):
        """测试提取导入命令类型"""
        assert bot._extract_command_type("/import") == CommandType.IMPORT
        assert bot._extract_command_type("/import path/to/file") == CommandType.IMPORT
        assert bot._extract_command_type("/导入") == CommandType.IMPORT

    def test_extract_help_command(self, bot):
        """测试提取帮助命令类型"""
        assert bot._extract_command_type("/help") == CommandType.HELP
        assert bot._extract_command_type("/帮助") == CommandType.HELP

    def test_extract_recent_command(self, bot):
        """测试提取最近记录命令类型"""
        assert bot._extract_command_type("/recent") == CommandType.RECENT
        assert bot._extract_command_type("/recent 10") == CommandType.RECENT
        assert bot._extract_command_type("/最近") == CommandType.RECENT

    def test_extract_vd_command(self, bot):
        """测试提取 VDOT 命令类型"""
        assert bot._extract_command_type("/vd") == CommandType.VD
        assert bot._extract_command_type("/vdot") == CommandType.VD

    def test_extract_hr_drift_command(self, bot):
        """测试提取心率漂移命令类型"""
        assert bot._extract_command_type("/hr_drift") == CommandType.HR_DRIFT
        assert bot._extract_command_type("/心率漂移") == CommandType.HR_DRIFT

    def test_extract_load_command(self, bot):
        """测试提取训练负荷命令类型"""
        assert bot._extract_command_type("/load") == CommandType.LOAD
        assert bot._extract_command_type("/load 2024-01-01") == CommandType.LOAD
        assert bot._extract_command_type("/负荷") == CommandType.LOAD

    def test_extract_unknown_command(self, bot):
        """测试提取未知命令类型"""
        assert bot._extract_command_type("/unknown") == CommandType.UNKNOWN
        assert bot._extract_command_type("hello") == CommandType.UNKNOWN
        assert bot._extract_command_type("") == CommandType.UNKNOWN

    def test_extract_command_case_insensitive(self, bot):
        """测试命令提取大小写不敏感"""
        assert bot._extract_command_type("/HELP") == CommandType.HELP
        assert bot._extract_command_type("/Stats") == CommandType.STATS
        assert bot._extract_command_type("/IMPORT") == CommandType.IMPORT


class TestFeishuBotExtractArgs:
    """测试命令参数提取"""

    @pytest.fixture
    def bot(self):
        """创建 FeishuBot 实例"""
        with patch("src.notify.feishu.ConfigManager"):
            return FeishuBot()

    def test_extract_no_args(self, bot):
        """测试无参数提取"""
        assert bot._extract_command_args("/help") == []
        assert bot._extract_command_args("/vd") == []

    def test_extract_single_arg(self, bot):
        """测试单个参数提取"""
        assert bot._extract_command_args("/import D:/garmin") == ["D:/garmin"]
        assert bot._extract_command_args("/recent 10") == ["10"]

    def test_extract_multiple_args(self, bot):
        """测试多个参数提取"""
        args = bot._extract_command_args("/stats --year 2024 --start 2024-01-01")
        assert args == ["--year", "2024", "--start", "2024-01-01"]

    def test_extract_args_with_spaces(self, bot):
        """测试带空格的参数提取"""
        args = bot._extract_command_args("/stats  --year  2024")
        assert args == ["--year", "2024"]


class TestFeishuBotCommandHandlers:
    """测试命令处理器"""

    @pytest.fixture
    def bot(self):
        """创建 FeishuBot 实例"""
        with patch("src.notify.feishu.ConfigManager"):
            return FeishuBot()

    def test_handle_help_command(self, bot):
        """测试处理帮助命令"""
        cmd = ParsedCommand(
            command_type=CommandType.HELP,
            raw_text="/help",
            args=[],
        )

        result = bot._handle_help(cmd)

        assert result["success"] is True
        assert "跑步助理命令帮助" in result["message"]
        assert result["msg_type"] == "text"

    def test_handle_stats_command_no_args(self, bot):
        """测试处理统计命令（无参数）"""
        cmd = ParsedCommand(
            command_type=CommandType.STATS,
            raw_text="/stats",
            args=[],
        )

        result = bot._handle_stats(cmd)

        assert result["success"] is True
        assert "查询统计" in result["message"]

    def test_handle_stats_command_with_year(self, bot):
        """测试处理统计命令（带年份参数）"""
        cmd = ParsedCommand(
            command_type=CommandType.STATS,
            raw_text="/stats --year 2024",
            args=["--year", "2024"],
        )

        result = bot._handle_stats(cmd)

        assert result["success"] is True
        assert "2024" in result["message"]

    def test_handle_stats_command_with_date_range(self, bot):
        """测试处理统计命令（带日期范围）"""
        cmd = ParsedCommand(
            command_type=CommandType.STATS,
            raw_text="/stats --start 2024-01-01 --end 2024-12-31",
            args=["--start", "2024-01-01", "--end", "2024-12-31"],
        )

        result = bot._handle_stats(cmd)

        assert result["success"] is True
        assert "2024-01-01" in result["message"]
        assert "2024-12-31" in result["message"]

    def test_handle_recent_command_default(self, bot):
        """测试处理最近记录命令（默认数量）"""
        cmd = ParsedCommand(
            command_type=CommandType.RECENT,
            raw_text="/recent",
            args=[],
        )

        result = bot._handle_recent(cmd)

        assert result["success"] is True
        assert "5" in result["message"]

    def test_handle_recent_command_custom_count(self, bot):
        """测试处理最近记录命令（自定义数量）"""
        cmd = ParsedCommand(
            command_type=CommandType.RECENT,
            raw_text="/recent 10",
            args=["10"],
        )

        result = bot._handle_recent(cmd)

        assert result["success"] is True
        assert "10" in result["message"]

    def test_handle_recent_command_max_limit(self, bot):
        """测试处理最近记录命令（最大限制）"""
        cmd = ParsedCommand(
            command_type=CommandType.RECENT,
            raw_text="/recent 100",
            args=["100"],
        )

        result = bot._handle_recent(cmd)

        assert result["success"] is True
        assert "20" in result["message"]  # 最多 20 条

    def test_handle_vd_command(self, bot):
        """测试处理 VDOT 命令"""
        cmd = ParsedCommand(
            command_type=CommandType.VD,
            raw_text="/vd",
            args=[],
        )

        result = bot._handle_vd(cmd)

        assert result["success"] is True
        assert "VDOT" in result["message"]

    def test_handle_hr_drift_command(self, bot):
        """测试处理心率漂移命令"""
        cmd = ParsedCommand(
            command_type=CommandType.HR_DRIFT,
            raw_text="/hr_drift",
            args=[],
        )

        result = bot._handle_hr_drift(cmd)

        assert result["success"] is True
        assert "心率漂移" in result["message"]

    def test_handle_load_command_default(self, bot):
        """测试处理训练负荷命令（默认）"""
        cmd = ParsedCommand(
            command_type=CommandType.LOAD,
            raw_text="/load",
            args=[],
        )

        result = bot._handle_load(cmd)

        assert result["success"] is True
        assert "最近 7 天" in result["message"]

    def test_handle_load_command_custom_range(self, bot):
        """测试处理训练负荷命令（自定义范围）"""
        cmd = ParsedCommand(
            command_type=CommandType.LOAD,
            raw_text="/load 2024-01-01 2024-01-31",
            args=["2024-01-01", "2024-01-31"],
        )

        result = bot._handle_load(cmd)

        assert result["success"] is True
        assert "2024-01-01" in result["message"]

    def test_handle_import_command_no_path(self, bot):
        """测试处理导入命令（无路径）"""
        cmd = ParsedCommand(
            command_type=CommandType.IMPORT,
            raw_text="/import",
            args=[],
        )

        result = bot._handle_import(cmd)

        assert result["success"] is False
        assert "请提供 FIT 文件路径" in result["message"]

    def test_handle_import_command_with_path(self, bot):
        """测试处理导入命令（有路径）"""
        cmd = ParsedCommand(
            command_type=CommandType.IMPORT,
            raw_text="/import D:/garmin/activities",
            args=["D:/garmin/activities"],
        )

        result = bot._handle_import(cmd)

        assert result["success"] is True
        assert "D:/garmin/activities" in result["message"]


class TestFeishuBotHandleMessage:
    """测试消息处理"""

    @pytest.fixture
    def bot(self):
        """创建 FeishuBot 实例"""
        with patch("src.notify.feishu.ConfigManager"):
            return FeishuBot()

    def test_handle_message_help(self, bot):
        """测试处理帮助消息"""
        message_data = {
            "content": "/help",
            "chat_id": "chat_123",
        }

        # 使用 asyncio.run() 运行异步函数
        result = asyncio.run(bot.handle_message(message_data))

        assert result["success"] is True
        assert "跑步助理命令帮助" in result["message"]

    def test_handle_message_stats(self, bot):
        """测试处理统计消息"""
        message_data = {
            "content": "/stats --year 2024",
            "chat_id": "chat_123",
        }

        result = asyncio.run(bot.handle_message(message_data))

        assert result["success"] is True
        assert "查询统计" in result["message"]

    def test_handle_message_unknown_command(self, bot):
        """测试处理未知命令消息"""
        message_data = {
            "content": "/unknown_command",
            "chat_id": "chat_123",
        }

        result = asyncio.run(bot.handle_message(message_data))

        assert result["success"] is False
        assert "未识别的命令格式" in result["message"]

    def test_handle_message_empty_content(self, bot):
        """测试处理空内容消息"""
        message_data = {
            "content": "",
            "chat_id": "chat_123",
        }

        result = asyncio.run(bot.handle_message(message_data))

        assert result["success"] is False
        assert "未识别的命令格式" in result["message"]

    def test_handle_message_handler_exception(self, bot):
        """测试处理命令处理器异常"""

        # Mock 一个会抛出异常的处理器
        def mock_handler(cmd):
            raise Exception("测试异常")

        bot._command_handlers[CommandType.HELP] = mock_handler

        message_data = {
            "content": "/help",
            "chat_id": "chat_123",
        }

        result = asyncio.run(bot.handle_message(message_data))

        assert result["success"] is False
        assert "命令执行失败" in result["message"]


class TestFeishuBotRegisterHandler:
    """测试命令处理器注册"""

    @pytest.fixture
    def bot(self):
        """创建 FeishuBot 实例"""
        with patch("src.notify.feishu.ConfigManager"):
            return FeishuBot()

    def test_register_custom_handler(self, bot):
        """测试注册自定义处理器"""
        custom_handler = MagicMock(return_value={"success": True, "message": "自定义"})

        bot.register_command_handler(CommandType.STATS, custom_handler)

        assert CommandType.STATS in bot._command_handlers
        assert bot._command_handlers[CommandType.STATS] == custom_handler

    def test_unregister_handler(self, bot):
        """测试注销处理器"""
        custom_handler = MagicMock(return_value={"success": True, "message": "自定义"})
        bot.register_command_handler(CommandType.STATS, custom_handler)

        bot.unregister_command_handler(CommandType.STATS)

        assert CommandType.STATS not in bot._command_handlers

    def test_unregister_nonexistent_handler(self, bot):
        """测试注销不存在的处理器"""
        # 不应该抛出异常
        bot.unregister_command_handler(CommandType.STATS)


class TestFeishuBotSendMessages:
    """测试消息发送"""

    @pytest.fixture
    def bot(self):
        """创建 FeishuBot 实例"""
        with patch("src.notify.feishu.ConfigManager"):
            return FeishuBot(
                app_id="test_app_id",
                app_secret="test_app_secret",
                receive_id="test_user_id",
            )

    @patch.object(FeishuBot, "_send_with_retry")
    def test_send_text_success(self, mock_send, bot):
        """测试发送文本消息成功"""
        mock_send.return_value = {"success": True, "data": {"message_id": "123"}}

        result = bot.send_text("测试消息")

        assert result.get("success") is True
        mock_send.assert_called_once()

    @patch.object(FeishuBot, "_send_with_retry")
    def test_send_text_failure(self, mock_send, bot):
        """测试发送文本消息失败"""
        mock_send.return_value = {"success": False, "error": "发送失败"}

        result = bot.send_text("测试消息")

        assert result.get("success") is False
        assert "error" in result

    def test_send_text_no_credentials(self):
        """测试无凭证时发送文本消息"""
        with patch("src.notify.feishu.ConfigManager") as mock_config:
            mock_config.return_value.get.return_value = None
            bot = FeishuBot()

            result = bot.send_text("测试消息")

            assert result.get("success") is False
            assert "未配置飞书应用凭证" in result.get("error", "")

    @patch.object(FeishuBot, "_send_with_retry")
    def test_send_card_success(self, mock_send, bot):
        """测试发送卡片消息成功"""
        mock_send.return_value = {"success": True, "data": {"message_id": "123"}}

        result = bot.send_card("标题", "内容")

        assert result.get("success") is True
        mock_send.assert_called_once()

    @patch.object(FeishuBot, "_send_with_retry")
    def test_send_import_notification(self, mock_send, bot):
        """测试发送导入通知"""
        mock_send.return_value = {"success": True, "data": {"message_id": "123"}}

        stats = {"total": 10, "added": 8, "skipped": 2, "errors": 0}
        result = bot.send_import_notification(stats)

        assert result.get("success") is True


class TestFeishuBotRetry:
    """测试重试机制"""

    def test_retry_on_timeout(self):
        """测试超时重试"""
        with patch("src.notify.feishu.ConfigManager"):
            bot = FeishuBot(
                app_id="test_app_id",
                app_secret="test_app_secret",
                receive_id="test_user_id",
            )

            # 第一次调用抛出异常，第二次成功
            call_count = 0

            def mock_send_text(content, receive_id, receive_id_type="user_id"):
                nonlocal call_count
                call_count += 1
                if call_count < 2:
                    raise RuntimeError("请求超时")
                return {"code": 0, "msg": "success", "data": {"message_id": "123"}}

            with patch.object(bot.message_api, "send_text", side_effect=mock_send_text):
                result = bot.send_text("测试消息")

                assert result.get("success") is True
                assert call_count == 2

    def test_retry_exhausted(self):
        """测试重试耗尽"""
        with patch("src.notify.feishu.ConfigManager"):
            bot = FeishuBot(
                app_id="test_app_id",
                app_secret="test_app_secret",
                receive_id="test_user_id",
            )

            # 持续失败
            call_count = 0

            def mock_send_text(content, receive_id, receive_id_type="user_id"):
                nonlocal call_count
                call_count += 1
                raise RuntimeError("持续失败")

            with patch.object(bot.message_api, "send_text", side_effect=mock_send_text):
                result = bot.send_text("测试消息")

                assert result.get("success") is False
                assert "已重试" in result.get("error", "")
                # 初始调用 1 次 + 重试 3 次 = 4 次
                assert call_count == 4


class TestFeishuBotIntegration:
    """集成测试"""

    @pytest.fixture
    def bot(self):
        """创建 FeishuBot 实例"""
        with patch("src.notify.feishu.ConfigManager"):
            return FeishuBot()

    def test_full_message_flow(self, bot):
        """测试完整的消息处理流程"""
        # 1. 解析消息
        message_data = {
            "content": "/stats --year 2024",
            "chat_id": "chat_123",
            "user_id": "user_456",
        }

        parsed_cmd = bot.parse_message(message_data)
        assert parsed_cmd is not None
        assert parsed_cmd.command_type == CommandType.STATS

        # 2. 执行命令处理器
        result = bot._handle_stats(parsed_cmd)
        assert result["success"] is True

    def test_help_command_flow(self, bot):
        """测试帮助命令完整流程"""
        message_data = {"content": "/help"}

        parsed_cmd = bot.parse_message(message_data)
        assert parsed_cmd is not None

        result = bot._handle_help(parsed_cmd)
        assert result["success"] is True
        assert "msg_type" in result


class TestFeishuBotEdgeCases:
    """边界情况测试"""

    @pytest.fixture
    def bot(self):
        """创建 FeishuBot 实例"""
        with patch("src.notify.feishu.ConfigManager"):
            return FeishuBot()

    def test_parse_message_none_content(self, bot):
        """测试解析 None 内容"""
        message_data = {"content": None}
        result = bot.parse_message(message_data)
        assert result is None

    def test_parse_message_whitespace_only(self, bot):
        """测试解析纯空白内容"""
        message_data = {"content": "   "}
        result = bot.parse_message(message_data)
        assert result is None

    def test_extract_command_type_partial_match(self, bot):
        """测试命令类型部分匹配"""
        # 应该不匹配
        assert bot._extract_command_type("/stat") == CommandType.UNKNOWN
        assert bot._extract_command_type("/statistic") == CommandType.UNKNOWN

    def test_handle_command_with_special_characters(self, bot):
        """测试处理带特殊字符的命令"""
        cmd = ParsedCommand(
            command_type=CommandType.IMPORT,
            raw_text="/import D:/garmin/活动/2024",
            args=["D:/garmin/活动/2024"],
        )

        result = bot._handle_import(cmd)
        assert result["success"] is True

    def test_command_handler_return_format(self, bot):
        """测试命令处理器返回格式"""
        cmd = ParsedCommand(
            command_type=CommandType.HELP,
            raw_text="/help",
            args=[],
        )

        result = bot._handle_help(cmd)

        # 验证返回格式统一性
        assert "success" in result
        assert "message" in result
        assert isinstance(result["success"], bool)
        assert isinstance(result["message"], str)


if __name__ == "__main__":
    pytest.main(
        [
            __file__,
            "-v",
            "--cov=src.notify.feishu",
            "--cov-report=term-missing",
            "--cov-report=html",
        ]
    )
