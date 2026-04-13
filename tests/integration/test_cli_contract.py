# CLI命令契约测试
# 验证CLI命令名称与文档定义一致

from pathlib import Path

from typer.testing import CliRunner

from src.cli.app import app

runner = CliRunner()


class TestCLICommandContract:
    """
    CLI命令契约测试

    目标：验证CLI命令名称与文档定义一致
    优先级：P0

    覆盖场景：
    1. 命令名称与文档一致
    2. 命令别名正确
    3. 命令参数正确
    """

    def test_data_import_command_name(self):
        """
        测试 data import 命令名称

        文档定义：nanobotrun data import <path>
        Bug历史：曾使用 import-data，导致用户执行失败
        """
        result = runner.invoke(app, ["data", "import", "--help"])
        assert result.exit_code == 0, f"命令执行失败: {result.output}"
        assert "FIT" in result.output or "导入" in result.output

    def test_data_import_command_alias_removed(self):
        """
        测试 import-data 别名已移除（用户应使用 import）

        Bug历史：曾使用 import-data，现已统一为 import
        """
        result = runner.invoke(app, ["data", "import-data", "--help"])
        assert result.exit_code != 0
        assert (
            "No such command" in result.output
            or "Did you mean 'import'" in result.output
        )

    def test_data_stats_command_name(self):
        """
        测试 data stats 命令名称
        """
        result = runner.invoke(app, ["data", "stats", "--help"])
        assert result.exit_code == 0, f"命令执行失败: {result.output}"

    def test_data_recent_command_name(self):
        """
        测试 data recent 命令名称
        """
        result = runner.invoke(app, ["data", "recent", "--help"])
        assert result.exit_code == 0, f"命令执行失败: {result.output}"

    def test_analysis_vdot_command_name(self):
        """
        测试 analysis vdot 命令名称
        """
        result = runner.invoke(app, ["analysis", "vdot", "--help"])
        assert result.exit_code == 0, f"命令执行失败: {result.output}"

    def test_analysis_load_command_name(self):
        """
        测试 analysis load 命令名称
        """
        result = runner.invoke(app, ["analysis", "load", "--help"])
        assert result.exit_code == 0, f"命令执行失败: {result.output}"

    def test_analysis_hr_drift_command_name(self):
        """
        测试 analysis hr-drift 命令名称
        """
        result = runner.invoke(app, ["analysis", "hr-drift", "--help"])
        assert result.exit_code == 0, f"命令执行失败: {result.output}"

    def test_agent_chat_command_name(self):
        """
        测试 agent chat 命令名称
        """
        result = runner.invoke(app, ["agent", "chat", "--help"])
        assert result.exit_code == 0, f"命令执行失败: {result.output}"

    def test_report_command_name(self):
        """
        测试 report report 命令名称

        注意：report命令是 nanobotrun report report
        """
        result = runner.invoke(app, ["report", "report", "--help"])
        assert result.exit_code == 0, f"命令执行失败: {result.output}"

    def test_system_version_command_name(self):
        """
        测试 system version 命令名称
        """
        result = runner.invoke(app, ["system", "version", "--help"])
        assert result.exit_code == 0, f"命令执行失败: {result.output}"

    def test_data_stats_date_parameters(self):
        """
        测试 data stats 命令的日期参数

        Bug历史：字符串日期与datetime类型比较失败
        """
        result = runner.invoke(
            app, ["data", "stats", "--start", "2024-01-01", "--end", "2024-12-31"]
        )
        assert result.exit_code == 0 or result.exit_code == 1
        assert "错误" not in result.output or "暂无数据" in result.output

    def test_data_stats_year_parameter(self):
        """
        测试 data stats 命令的年份参数
        """
        result = runner.invoke(app, ["data", "stats", "--year", "2024"])
        assert result.exit_code == 0 or result.exit_code == 1

    def test_all_commands_listed_in_help(self):
        """
        测试所有命令都在帮助信息中列出
        """
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "data" in result.output
        assert "analysis" in result.output
        assert "agent" in result.output
        assert "report" in result.output
        assert "system" in result.output


class TestCLICommandIntegration:
    """
    CLI命令集成测试

    目标：验证CLI命令端到端执行正确
    优先级：P0
    """

    def test_data_import_with_real_path(self, tmp_path: Path):
        """
        测试导入命令与真实路径

        Bug历史：路径不存在时报错信息不友好
        """
        nonexistent_path = tmp_path / "nonexistent.fit"
        result = runner.invoke(app, ["data", "import", str(nonexistent_path)])
        assert result.exit_code != 0
        assert "路径不存在" in result.output or "不存在" in result.output

    def test_data_stats_with_date_range_string(self):
        """
        测试统计命令与字符串日期参数

        Bug历史：字符串日期与datetime类型比较失败
        """
        result = runner.invoke(
            app, ["data", "stats", "--start", "2024-01-01", "--end", "2024-12-31"]
        )
        assert result.exit_code == 0 or result.exit_code == 1
        assert "cannot compare" not in result.output.lower()
        assert "NoneType" not in result.output

    def test_analysis_vdot_output_format(self):
        """
        测试VDOT命令输出格式

        Bug历史：日期、距离、时长字段显示为N/A
        """
        result = runner.invoke(app, ["analysis", "vdot"])
        assert result.exit_code == 0 or result.exit_code == 1

        if result.exit_code == 0:
            assert "N/A" not in result.output or "暂无" in result.output

    def test_cli_help_for_each_command(self):
        """
        测试每个命令的帮助信息可访问
        """
        commands = [
            ["data", "import"],
            ["data", "stats"],
            ["data", "recent"],
            ["analysis", "vdot"],
            ["analysis", "load"],
            ["analysis", "hr-drift"],
            ["agent", "chat"],
            ["report", "report"],
            ["system", "version"],
        ]

        for cmd in commands:
            result = runner.invoke(app, cmd + ["--help"])
            assert result.exit_code == 0, f"命令 {' '.join(cmd)} --help 失败"
