# CLI格式化输出单元测试


from src.cli_formatter import (
    format_agent_response,
    format_distance,
    format_duration,
    format_error,
    format_pace,
    format_runs_table,
    format_stats_panel,
    format_success,
    format_vdot_trend,
    format_warning,
)


class TestFormatDuration:
    """测试时长格式化"""

    def test_format_duration_seconds(self):
        """测试格式化时长（秒）"""
        assert format_duration(30) == "30秒"

    def test_format_duration_minutes(self):
        """测试格式化时长（分）"""
        assert format_duration(150) == "2分30秒"

    def test_format_duration_hours(self):
        """测试格式化时长（小时）"""
        assert format_duration(3661) == "1小时1分1秒"

    def test_format_duration_zero(self):
        """测试零时长"""
        assert format_duration(0) == "0秒"

    def test_format_duration_exact_minute(self):
        """测试刚好整分钟"""
        assert format_duration(120) == "2分0秒"

    def test_format_duration_exact_hour(self):
        """测试刚好整小时"""
        assert format_duration(3600) == "1小时0分0秒"


class TestFormatPace:
    """测试配速格式化"""

    def test_format_pace_success(self):
        """测试格式化配速"""
        assert format_pace(300) == "5'00\""

    def test_format_pace_fast(self):
        """测试快速配速"""
        assert format_pace(180) == "3'00\""

    def test_format_pace_slow(self):
        """测试慢速配速"""
        assert format_pace(600) == "10'00\""

    def test_format_pace_invalid_zero(self):
        """测试无效配速（零）"""
        assert format_pace(0) == "N/A"

    def test_format_pace_invalid_negative(self):
        """测试无效配速（负数）"""
        assert format_pace(-10) == "N/A"

    def test_format_pace_with_seconds(self):
        """测试带秒的配速"""
        assert format_pace(330) == "5'30\""


class TestFormatDistance:
    """测试距离格式化"""

    def test_format_distance_meters(self):
        """测试格式化距离（米）"""
        assert format_distance(500) == "500米"

    def test_format_distance_kilometers(self):
        """测试格式化距离（公里）"""
        assert format_distance(5000) == "5.00公里"

    def test_format_distance_zero(self):
        """测试零距离"""
        assert format_distance(0) == "0米"

    def test_format_distance_exact_kilometer(self):
        """测试刚好一公里"""
        assert format_distance(1000) == "1.00公里"

    def test_format_distance_decimal(self):
        """测试小数公里"""
        assert format_distance(2500) == "2.50公里"


class TestFormatStatsPanel:
    """测试统计面板格式化"""

    def test_format_stats_panel_basic(self):
        """测试基本统计面板"""
        data = {"总次数": 10, "总距离": 50000}
        panel = format_stats_panel(data)
        assert panel is not None

    def test_format_stats_panel_with_duration(self):
        """测试包含时长的统计面板"""
        data = {"总时长": 3600}
        panel = format_stats_panel(data)
        assert panel is not None

    def test_format_stats_panel_with_pace(self):
        """测试包含配速的统计面板"""
        data = {"平均配速": 300}
        panel = format_stats_panel(data)
        assert panel is not None

    def test_format_stats_panel_empty(self):
        """测试空数据"""
        data = {}
        panel = format_stats_panel(data)
        assert panel is not None


class TestFormatError:
    """测试错误格式化"""

    def test_format_error_basic(self):
        """测试基本错误"""
        panel = format_error("测试错误")
        assert panel is not None

    def test_format_error_empty(self):
        """测试空错误消息"""
        panel = format_error("")
        assert panel is not None


class TestFormatSuccess:
    """测试成功格式化"""

    def test_format_success_basic(self):
        """测试基本成功消息"""
        panel = format_success("操作成功")
        assert panel is not None


class TestFormatWarning:
    """测试警告格式化"""

    def test_format_warning_basic(self):
        """测试基本警告"""
        panel = format_warning("注意警告")
        assert panel is not None


class TestFormatRunsTable:
    """测试跑步表格格式化"""

    def test_format_runs_table_empty(self):
        """测试空跑步列表"""
        table = format_runs_table([])
        assert table is not None

    def test_format_runs_table_single(self):
        """测试单条跑步记录"""
        runs = [
            {
                "timestamp": "2024-01-01",
                "distance": 5.0,
                "duration": 1800,
                "heart_rate": 145,
                "pace": 360,
            }
        ]
        table = format_runs_table(runs)
        assert table is not None

    def test_format_runs_table_multiple(self):
        """测试多条跑步记录"""
        runs = [
            {
                "timestamp": "2024-01-01",
                "distance": 5.0,
                "duration": 1800,
                "heart_rate": 145,
                "pace": 360,
            },
            {
                "timestamp": "2024-01-02",
                "distance": 10.0,
                "duration": 3600,
                "heart_rate": 150,
                "pace": 360,
            },
        ]
        table = format_runs_table(runs)
        assert table is not None

    def test_format_runs_table_with_error(self):
        """测试包含错误的记录"""
        runs = [{"error": "测试错误"}]
        table = format_runs_table(runs)
        assert table is not None

    def test_format_runs_table_none_values(self):
        """测试包含None值"""
        runs = [
            {
                "timestamp": None,
                "distance": None,
                "duration": None,
                "heart_rate": None,
                "pace": None,
            }
        ]
        table = format_runs_table(runs)
        assert table is not None


class TestFormatVdotTrend:
    """测试VDOT趋势格式化"""

    def test_format_vdot_trend_empty(self):
        """测试空VDOT数据"""
        table = format_vdot_trend([])
        assert table is not None

    def test_format_vdot_trend_single(self):
        """测试单条VDOT数据"""
        vdot_data = [
            {
                "date": "2024-01-01",
                "vdot": 45.5,
                "distance": 5000,
                "duration": 1500,
            }
        ]
        table = format_vdot_trend(vdot_data)
        assert table is not None

    def test_format_vdot_trend_multiple(self):
        """测试多条VDOT数据"""
        vdot_data = [
            {"date": "2024-01-01", "vdot": 45.5, "distance": 5000, "duration": 1500},
            {"date": "2024-01-08", "vdot": 46.0, "distance": 6000, "duration": 1800},
        ]
        table = format_vdot_trend(vdot_data)
        assert table is not None

    def test_format_vdot_trend_none_values(self):
        """测试包含None值"""
        vdot_data = [{"date": None, "vdot": None, "distance": None, "duration": None}]
        table = format_vdot_trend(vdot_data)
        assert table is not None


class TestFormatAgentResponse:
    """测试Agent响应格式化"""

    def test_format_agent_response_dict_error(self):
        """测试错误响应"""
        import sys
        from io import StringIO

        old_stdout = sys.stdout
        sys.stdout = StringIO()

        try:
            format_agent_response({"error": "测试错误"})
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout

    def test_format_agent_response_dict_message(self):
        """测试消息响应"""
        import sys
        from io import StringIO

        old_stdout = sys.stdout
        sys.stdout = StringIO()

        try:
            format_agent_response({"message": "测试消息"})
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout

    def test_format_agent_response_dict_data(self):
        """测试数据响应"""
        import sys
        from io import StringIO

        old_stdout = sys.stdout
        sys.stdout = StringIO()

        try:
            format_agent_response({"total_runs": 10, "total_distance": 50000})
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout

    def test_format_agent_response_empty_list(self):
        """测试空列表响应"""
        import sys
        from io import StringIO

        old_stdout = sys.stdout
        sys.stdout = StringIO()

        try:
            format_agent_response([])
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout

    def test_format_agent_response_list_with_runs(self):
        """测试跑步记录列表响应"""
        import sys
        from io import StringIO

        old_stdout = sys.stdout
        sys.stdout = StringIO()

        try:
            format_agent_response([{"distance": 5.0, "duration": 1800}])
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout

    def test_format_agent_response_list_with_vdot(self):
        """测试VDOT列表响应"""
        import sys
        from io import StringIO

        old_stdout = sys.stdout
        sys.stdout = StringIO()

        try:
            format_agent_response([{"vdot": 45.5}])
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout

    def test_format_agent_response_string(self):
        """测试字符串响应"""
        import sys
        from io import StringIO

        old_stdout = sys.stdout
        sys.stdout = StringIO()

        try:
            format_agent_response("纯文本响应")
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout
