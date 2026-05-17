"""Gateway E2E测试

测试目标：
- 验证 gateway 命令结构正确
- 验证命令执行流程完整
- 验证错误处理
- 验证异常场景处理
- 验证 Agent Chat 异常处理

Bug历史：
- gateway 命令缺少子命令导致 Missing command 错误
"""

import os
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


class TestGatewayErrorHandling:
    """测试 Gateway 错误处理"""

    def test_gateway_start_without_llm_config(self):
        """验证无LLM配置时启动失败（UAT-043）"""
        env = os.environ.copy()
        env.pop("NANOBOT_LLM_API_KEY", None)

        result = subprocess.run(
            ["uv", "run", "nanobotrun", "gateway", "start", "--port", "18791"],
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )

        assert result.returncode != 0, "无LLM配置时应启动失败"
        assert (
            "LLM" in result.stdout
            or "LLM" in result.stderr
            or "配置" in result.stdout
            or "配置" in result.stderr
        ), "应提示LLM配置缺失"

    def test_gateway_start_invalid_port(self):
        """验证无效端口时启动失败"""
        result = subprocess.run(
            ["uv", "run", "nanobotrun", "gateway", "start", "--port", "99999"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode != 0, "无效端口时应启动失败"


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


class TestAgentChatErrorHandling:
    """测试 Agent Chat 错误处理"""

    def test_agent_chat_without_api_key(self):
        """验证无API Key时提示配置（UAT-049）"""
        env = os.environ.copy()
        env.pop("NANOBOT_LLM_API_KEY", None)

        result = subprocess.run(
            ["uv", "run", "nanobotrun", "agent", "chat"],
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )

        assert result.returncode != 0, "无API Key时应启动失败"
        assert (
            "LLM" in result.stdout
            or "LLM" in result.stderr
            or "API" in result.stdout
            or "API" in result.stderr
            or "Key" in result.stdout
            or "Key" in result.stderr
        ), "应提示需要配置API Key"

    def test_agent_chat_help_structure(self):
        """验证 agent chat --help 显示正确结构"""
        result = subprocess.run(
            ["uv", "run", "nanobotrun", "agent", "chat", "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0, "agent chat --help 应成功"
        assert "chat" in result.stdout.lower() or "对话" in result.stdout, (
            "应包含对话相关信息"
        )


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
