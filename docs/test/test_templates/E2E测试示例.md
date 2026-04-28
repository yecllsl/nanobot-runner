# E2E 测试示例

```python
import pytest
from typer.testing import CliRunner
from src.cli.app import app

class TestCLICommands:
    """CLI命令E2E测试"""

    def test_data_import_command(self):
        """测试数据导入命令"""
        runner = CliRunner()

        result = runner.invoke(
            app,
            ["data", "import", "tests/data/fixtures/easy_run_20240101.fit"]
        )

        assert result.exit_code == 0
        assert "导入成功" in result.output

class TestPlanningCommands:
    """智能跑步计划CLI命令E2E测试"""

    def test_plan_generate_command(self):
        """测试计划生成命令"""
        runner = CliRunner()

        result = runner.invoke(
            app,
            ["plan", "generate", "--target", "marathon", "--time", "3:30:00"]
        )

        assert result.exit_code == 0
        assert "计划生成成功" in result.output

    def test_plan_feedback_command(self):
        """测试计划反馈命令"""
        runner = CliRunner()

        result = runner.invoke(
            app,
            ["plan", "feedback", "--plan-id", "plan_001", "--completion", "0.9"]
        )

        assert result.exit_code == 0
        assert "反馈记录成功" in result.output
```
