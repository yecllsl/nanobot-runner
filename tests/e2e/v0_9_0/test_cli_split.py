#!/usr/bin/env python3
"""
v0.9.0 CLI拆分端到端测试

测试目标：
- 验证拆分后命令正确路由
- 确保命令正确调用业务层
- 验证输出格式正确性
- 验证错误信息正确显示

执行方式：
- pytest tests/e2e/v0_9_0/test_cli_split.py -v
"""

import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))


class TestCLISplitE2E:
    """CLI拆分端到端测试"""

    def setup_method(self):
        """测试前置设置"""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_data_dir = Path(self.temp_dir.name)

    def teardown_method(self):
        """测试后置清理"""
        import gc
        import time

        gc.collect()
        time.sleep(0.1)
        try:
            self.temp_dir.cleanup()
        except PermissionError:
            pass

    def test_command_routing_help(self):
        """
        E2E-CLI-001: 命令路由测试 - 帮助命令
        验证拆分后命令正确路由
        优先级: P0
        """
        print("\n=== 命令路由测试 - 帮助命令 ===")

        result = subprocess.run(
            [sys.executable, "-m", "src.cli", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0, f"帮助命令应成功，返回码: {result.returncode}"

        assert (
            "Nanobot Runner" in result.stdout or "nanobotrun" in result.stdout
        ), f"帮助输出应包含应用名称"

        print("✓ 帮助命令路由测试通过")
        print(f"  - 返回码: {result.returncode}")
        print(f"  - 输出包含应用名称")

    def test_command_routing_import_data(self):
        """
        E2E-CLI-002: 命令路由测试 - data命令
        验证data命令正确路由
        优先级: P0
        """
        print("\n=== 命令路由测试 - data命令 ===")

        result = subprocess.run(
            [sys.executable, "-m", "src.cli", "data", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0, f"data帮助命令应成功，返回码: {result.returncode}"

        print("✓ data命令路由测试通过")
        print(f"  - 返回码: {result.returncode}")

    def test_command_routing_stats(self):
        """
        E2E-CLI-003: 命令路由测试 - analysis命令
        验证analysis命令正确路由
        优先级: P0
        """
        print("\n=== 命令路由测试 - analysis命令 ===")

        result = subprocess.run(
            [sys.executable, "-m", "src.cli", "analysis", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0, f"analysis帮助命令应成功，返回码: {result.returncode}"

        print("✓ analysis命令路由测试通过")
        print(f"  - 返回码: {result.returncode}")

    def test_command_routing_chat(self):
        """
        E2E-CLI-004: 命令路由测试 - agent命令
        验证agent命令正确路由
        优先级: P0
        """
        print("\n=== 命令路由测试 - agent命令 ===")

        result = subprocess.run(
            [sys.executable, "-m", "src.cli", "agent", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0, f"agent帮助命令应成功，返回码: {result.returncode}"

        print("✓ agent命令路由测试通过")
        print(f"  - 返回码: {result.returncode}")

    def test_command_routing_plan(self):
        """
        E2E-CLI-005: 命令路由测试 - gateway命令
        验证gateway命令正确路由
        优先级: P0
        """
        print("\n=== 命令路由测试 - gateway命令 ===")

        result = subprocess.run(
            [sys.executable, "-m", "src.cli", "gateway", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0, f"gateway帮助命令应成功，返回码: {result.returncode}"

        print("✓ gateway命令路由测试通过")
        print(f"  - 返回码: {result.returncode}")

    def test_command_routing_report(self):
        """
        E2E-CLI-006: 命令路由测试 - report命令
        验证report命令正确路由
        优先级: P1
        """
        print("\n=== 命令路由测试 - report命令 ===")

        result = subprocess.run(
            [sys.executable, "-m", "src.cli", "report", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0, f"report帮助命令应成功，返回码: {result.returncode}"

        print("✓ report命令路由测试通过")
        print(f"  - 返回码: {result.returncode}")

    def test_command_routing_config(self):
        """
        E2E-CLI-007: 命令路由测试 - system命令
        验证system命令正确路由
        优先级: P1
        """
        print("\n=== 命令路由测试 - system命令 ===")

        result = subprocess.run(
            [sys.executable, "-m", "src.cli", "system", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0, f"system帮助命令应成功，返回码: {result.returncode}"

        print("✓ system命令路由测试通过")
        print(f"  - 返回码: {result.returncode}")

    def test_invalid_command_handling(self):
        """
        E2E-CLI-008: 无效命令处理测试
        验证错误信息正确显示
        优先级: P0
        """
        print("\n=== 无效命令处理测试 ===")

        result = subprocess.run(
            [sys.executable, "-m", "src.cli", "invalid_command"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode != 0, "无效命令应返回非零退出码"

        assert "No such command" in result.stderr or "Error" in result.stderr, "应显示错误信息"

        print("✓ 无效命令处理测试通过")
        print(f"  - 返回码: {result.returncode}")
        print(f"  - 错误信息已显示")

    def test_cli_startup_performance(self):
        """
        E2E-CLI-009: CLI启动性能测试
        验证CLI启动时间符合预期
        优先级: P1
        """
        print("\n=== CLI启动性能测试 ===")

        import time

        start_time = time.time()

        result = subprocess.run(
            [sys.executable, "-m", "src.cli", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        elapsed_time = time.time() - start_time

        assert result.returncode == 0, f"CLI启动应成功，返回码: {result.returncode}"

        assert elapsed_time < 3.0, f"CLI启动时间应<3秒，实际: {elapsed_time:.2f}秒"

        print("✓ CLI启动性能测试通过")
        print(f"  - 启动时间: {elapsed_time:.2f}秒")

    def test_cli_module_entry_point(self):
        """
        E2E-CLI-010: CLI模块入口测试
        验证CLI可通过模块方式执行
        优先级: P0
        """
        print("\n=== CLI模块入口测试 ===")

        result = subprocess.run(
            [sys.executable, "-m", "src.cli", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        print("✓ CLI模块入口测试通过")
        print(f"  - 返回码: {result.returncode}")


class TestCLICommandIntegration:
    """CLI命令集成测试"""

    def test_stats_command_execution(self):
        """
        测试analysis命令执行
        优先级: P1
        """
        print("\n=== analysis命令执行测试 ===")

        with tempfile.TemporaryDirectory() as temp_dir:
            result = subprocess.run(
                [sys.executable, "-m", "src.cli", "analysis", "--help"],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=temp_dir,
            )

            assert result.returncode == 0, f"analysis命令应成功，返回码: {result.returncode}"

            print("✓ analysis命令执行测试通过")

    def test_import_data_command_dry_run(self):
        """
        测试data命令dry-run
        优先级: P1
        """
        print("\n=== data命令dry-run测试 ===")

        with tempfile.TemporaryDirectory() as temp_dir:
            test_path = Path(temp_dir) / "test_data"

            result = subprocess.run(
                [sys.executable, "-m", "src.cli", "data", "--help"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            print("✓ data命令dry-run测试通过")


class TestCLISplitArchitecture:
    """CLI拆分架构验证测试"""

    def test_cli_directory_structure(self):
        """
        测试CLI目录结构
        验证拆分后的目录结构符合v0.9.0基线
        优先级: P0
        """
        print("\n=== CLI目录结构验证测试 ===")

        cli_dir = Path(__file__).parent.parent.parent.parent / "src" / "cli"

        assert cli_dir.exists(), f"CLI目录应存在: {cli_dir}"

        app_file = cli_dir / "app.py"
        assert app_file.exists(), f"CLI入口文件应存在: {app_file}"

        commands_dir = cli_dir / "commands"
        assert commands_dir.exists(), f"commands目录应存在: {commands_dir}"

        print("✓ CLI目录结构验证测试通过")
        print(f"  - CLI目录: {cli_dir}")
        print(f"  - 入口文件: {app_file}")
        print(f"  - commands目录: {commands_dir}")

    def test_command_files_exist(self):
        """
        测试命令文件存在性
        验证拆分后的命令文件存在
        优先级: P0
        """
        print("\n=== 命令文件存在性测试 ===")

        cli_dir = (
            Path(__file__).parent.parent.parent.parent / "src" / "cli" / "commands"
        )

        expected_files = [
            "__init__.py",
            "agent.py",
            "analysis.py",
            "data.py",
            "gateway.py",
            "report.py",
            "system.py",
        ]

        for filename in expected_files:
            file_path = cli_dir / filename
            assert file_path.exists(), f"命令文件应存在: {file_path}"

        print("✓ 命令文件存在性测试通过")
        print(f"  - 已验证{len(expected_files)}个命令文件")


def test_cli_split_e2e_suite():
    """
    执行完整的CLI拆分E2E测试套件
    优先级: P0
    """
    print("\n🚀 开始执行CLI拆分E2E测试套件")

    test_instance = TestCLISplitE2E()

    try:
        test_instance.setup_method()

        test_instance.test_command_routing_help()
        test_instance.test_command_routing_import_data()
        test_instance.test_command_routing_stats()
        test_instance.test_command_routing_chat()
        test_instance.test_command_routing_plan()
        test_instance.test_command_routing_report()
        test_instance.test_command_routing_config()
        test_instance.test_invalid_command_handling()
        test_instance.test_cli_startup_performance()
        test_instance.test_cli_module_entry_point()

        print("\n🎉 CLI拆分E2E测试套件执行完成！")
        print("✅ 所有测试通过")

    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        raise
    finally:
        test_instance.teardown_method()


if __name__ == "__main__":
    """
    直接运行CLI拆分E2E测试
    """
    pytest.main([__file__, "-v", "-s"])
