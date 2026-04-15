"""Gateway E2E测试

测试目标：
- 验证 gateway 命令结构正确
- 验证命令执行流程完整
- 验证错误处理

Bug历史：
- gateway 命令缺少子命令导致 Missing command 错误
"""

import subprocess


class TestGatewayCommandStructure:
    """测试 Gateway 命令结构"""

    def test_gateway_help_shows_subcommands(self):
        """验证 gateway --help 显示子命令"""
        result = subprocess.run(
            ["uv", "run", "nanobotrun", "gateway", "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0, f"gateway --help 应成功: {result.stderr}"
        assert "start" in result.stdout, "gateway 应有 start 子命令"

    def test_gateway_start_help(self):
        """验证 gateway start --help 正常执行"""
        result = subprocess.run(
            ["uv", "run", "nanobotrun", "gateway", "start", "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0, f"gateway start --help 应成功: {result.stderr}"

    def test_gateway_without_subcommand_shows_error(self):
        """验证 gateway 不带子命令时显示错误"""
        result = subprocess.run(
            ["uv", "run", "nanobotrun", "gateway"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert (
            result.returncode != 0
            or "Missing command" in result.stderr
            or "Usage" in result.stdout
        )


class TestCLICommandStructure:
    """测试 CLI 命令结构"""

    def test_data_stats_command(self):
        """验证 data stats 命令正常执行"""
        result = subprocess.run(
            ["uv", "run", "nanobotrun", "data", "stats", "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0, f"data stats --help 应成功: {result.stderr}"

    def test_analysis_vdot_command(self):
        """验证 analysis vdot 命令正常执行"""
        result = subprocess.run(
            ["uv", "run", "nanobotrun", "analysis", "vdot", "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0, f"analysis vdot --help 应成功: {result.stderr}"

    def test_analysis_load_command(self):
        """验证 analysis load 命令正常执行"""
        result = subprocess.run(
            ["uv", "run", "nanobotrun", "analysis", "load", "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0, f"analysis load --help 应成功: {result.stderr}"

    def test_analysis_hr_drift_command(self):
        """验证 analysis hr-drift 命令正常执行"""
        result = subprocess.run(
            ["uv", "run", "nanobotrun", "analysis", "hr-drift", "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0, (
            f"analysis hr-drift --help 应成功: {result.stderr}"
        )


class TestAgentChatCommand:
    """测试 Agent Chat 命令"""

    def test_agent_chat_help(self):
        """验证 agent chat --help 正常执行"""
        result = subprocess.run(
            ["uv", "run", "nanobotrun", "agent", "chat", "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0, f"agent chat --help 应成功: {result.stderr}"


class TestReportCommand:
    """测试 Report 命令"""

    def test_report_weekly_help(self):
        """验证 report weekly --help 正常执行"""
        result = subprocess.run(
            ["uv", "run", "nanobotrun", "report", "weekly", "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0, f"report weekly --help 应成功: {result.stderr}"

    def test_report_monthly_help(self):
        """验证 report monthly --help 正常执行"""
        result = subprocess.run(
            ["uv", "run", "nanobotrun", "report", "monthly", "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0, f"report monthly --help 应成功: {result.stderr}"


class TestSystemCommand:
    """测试 System 命令"""

    def test_system_version(self):
        """验证 system version 命令正常执行"""
        result = subprocess.run(
            ["uv", "run", "nanobotrun", "system", "version"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0, f"system version 应成功: {result.stderr}"

    def test_system_init_help(self):
        """验证 system init --help 正常执行"""
        result = subprocess.run(
            ["uv", "run", "nanobotrun", "system", "init", "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0, f"system init --help 应成功: {result.stderr}"
