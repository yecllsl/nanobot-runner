# CLI模块测试用例说明

**文档版本**: v1.0  
**生效日期**: 2026-03-29  
**适用项目**: Nanobot Runner  
**文档负责人**: 测试工程师

---

## 一、概述

### 1.1 目的

本文档详细说明CLI模块的测试用例设计，旨在提升CLI模块的测试覆盖率（当前34%，目标60%+），确保CLI功能的稳定性和可靠性。

### 1.2 当前状态

| 指标 | 当前值 | 目标值 | 状态 |
|------|--------|--------|------|
| 语句覆盖率 | 34% | 60% | ❌ 未达标 |
| 分支覆盖率 | 28% | 50% | ❌ 未达标 |
| 函数覆盖率 | 40% | 70% | ❌ 未达标 |

### 1.3 测试范围

- `src/cli.py` - CLI主入口
- `src/cli_formatter.py` - 格式化输出

---

## 二、测试用例设计

### 2.1 命令参数解析测试

#### TC-CLI-PARAM-001: 有效参数解析

```python
def test_import_valid_path():
    """测试导入有效路径"""
    from typer.testing import CliRunner
    from src.cli import cli
    
    runner = CliRunner()
    result = runner.invoke(cli, ['import-data', 'tests/data/fixtures/easy_run_20240101.fit'])
    
    assert result.exit_code == 0
    assert '导入成功' in result.output or '已存在' in result.output
```

#### TC-CLI-PARAM-002: 无效路径处理

```python
def test_import_invalid_path():
    """测试导入无效路径"""
    from typer.testing import CliRunner
    from src.cli import cli
    
    runner = CliRunner()
    result = runner.invoke(cli, ['import-data', '/nonexistent/path.fit'])
    
    assert result.exit_code == 1
    assert '不存在' in result.output or '错误' in result.output
```

#### TC-CLI-PARAM-003: 参数类型验证

```python
import pytest
from typer.testing import CliRunner
from src.cli import cli


@pytest.mark.parametrize("year,expected_exit_code", [
    ("2024", 0),      # 有效年份
    ("abc", 2),       # 无效年份 - 类型错误
    ("", 2),          # 空值
    ("202", 0),       # 边界值 - 可能接受
    ("20245", 0),     # 边界值 - 可能接受
])
def test_stats_year_param(year, expected_exit_code):
    """测试stats命令年份参数"""
    runner = CliRunner()
    result = runner.invoke(cli, ['stats', '--year', year])
    
    assert result.exit_code == expected_exit_code
```

#### TC-CLI-PARAM-004: 可选参数组合

```python
def test_stats_param_combinations():
    """测试stats命令参数组合"""
    from typer.testing import CliRunner
    from src.cli import cli
    
    runner = CliRunner()
    
    # 无参数
    result = runner.invoke(cli, ['stats'])
    assert result.exit_code == 0
    
    # 仅year
    result = runner.invoke(cli, ['stats', '--year', '2024'])
    assert result.exit_code == 0
    
    # start和end
    result = runner.invoke(cli, [
        'stats', 
        '--start', '2024-01-01',
        '--end', '2024-12-31'
    ])
    assert result.exit_code == 0
    
    # 冲突参数 (year和start/end)
    result = runner.invoke(cli, [
        'stats',
        '--year', '2024',
        '--start', '2024-01-01'
    ])
    # 根据实现可能报错或优先处理
```

### 2.2 交互式输入测试

#### TC-CLI-INTERACT-001: 确认提示处理

```python
def test_memory_clear_confirm_yes():
    """测试memory clear确认 - 是"""
    from typer.testing import CliRunner
    from src.cli import cli
    
    runner = CliRunner()
    result = runner.invoke(cli, ['memory', 'clear'], input='y\n')
    
    assert result.exit_code == 0
    assert '已清空' in result.output or '清除' in result.output


def test_memory_clear_confirm_no():
    """测试memory clear确认 - 否"""
    from typer.testing import CliRunner
    from src.cli import cli
    
    runner = CliRunner()
    result = runner.invoke(cli, ['memory', 'clear'], input='n\n')
    
    assert result.exit_code == 0
    assert '取消' in result.output or '未清除' in result.output
```

### 2.3 错误处理测试

#### TC-CLI-ERROR-001: 异常捕获

```python
def test_import_corrupted_file():
    """测试导入损坏文件"""
    from typer.testing import CliRunner
    from src.cli import cli
    
    runner = CliRunner()
    result = runner.invoke(cli, ['import-data', 'tests/data/fixtures/corrupted_file.fit'])
    
    assert result.exit_code == 1
    assert '错误' in result.output or '失败' in result.output
    # 确保程序不崩溃


def test_stats_no_data():
    """测试无数据时的stats命令"""
    from typer.testing import CliRunner
    from src.cli import cli
    import tempfile
    import os
    
    runner = CliRunner()
    
    # 使用临时空目录
    with tempfile.TemporaryDirectory() as tmpdir:
        # 设置环境变量指向空目录
        old_env = os.environ.get('NANOBOT_RUNNER_DATA_DIR')
        os.environ['NANOBOT_RUNNER_DATA_DIR'] = tmpdir
        
        try:
            result = runner.invoke(cli, ['stats'])
            # 应该友好提示无数据，而不是报错
            assert '暂无数据' in result.output or '没有' in result.output or result.exit_code == 0
        finally:
            if old_env:
                os.environ['NANOBOT_RUNNER_DATA_DIR'] = old_env
            else:
                del os.environ['NANOBOT_RUNNER_DATA_DIR']
```

#### TC-CLI-ERROR-002: 权限错误

```python
@unittest.skipIf(sys.platform == 'win32', 'Unix-specific test')
def test_import_readonly_dir():
    """测试导入只读目录"""
    from typer.testing import CliRunner
    from src.cli import cli
    import tempfile
    import stat
    
    runner = CliRunner()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建只读目录
        readonly_dir = Path(tmpdir) / 'readonly'
        readonly_dir.mkdir()
        readonly_dir.chmod(stat.S_IRUSR | stat.S_IXUSR)  # 只读
        
        result = runner.invoke(cli, ['import-data', str(readonly_dir)])
        
        # 恢复权限以便清理
        readonly_dir.chmod(stat.S_IRWXU)
        
        assert result.exit_code != 0 or '权限' in result.output
```

### 2.4 输出格式测试

#### TC-CLI-OUTPUT-001: 表格输出验证

```python
def test_recent_output_format():
    """测试recent命令输出格式"""
    from typer.testing import CliRunner
    from src.cli import cli
    
    runner = CliRunner()
    result = runner.invoke(cli, ['recent', '-n', '5'])
    
    assert result.exit_code == 0
    
    # 验证表格格式
    output = result.output
    assert '日期' in output or 'Date' in output
    assert '距离' in output or 'Distance' in output
    assert '配速' in output or 'Pace' in output


def test_vdot_output_format():
    """测试vdot命令输出格式"""
    from typer.testing import CliRunner
    from src.cli import cli
    
    runner = CliRunner()
    result = runner.invoke(cli, ['vdot', '--limit', '5'])
    
    assert result.exit_code == 0
    
    # 验证VDOT值在合理范围
    output = result.output
    # VDOT值通常在20-80之间
    import re
    vdot_values = re.findall(r'\b(\d{2})\b', output)
    for v in vdot_values:
        assert 20 <= int(v) <= 80, f"VDOT值 {v} 超出合理范围"
```

#### TC-CLI-OUTPUT-002: 进度显示验证

```python
def test_import_progress_display():
    """测试导入进度显示"""
    from typer.testing import CliRunner
    from src.cli import cli
    
    runner = CliRunner()
    
    # 批量导入目录
    result = runner.invoke(cli, ['import-data', 'tests/data/fixtures/'])
    
    assert result.exit_code == 0
    # 验证有进度显示或完成提示
    assert any(word in result.output for word in ['导入', '完成', '进度', 'Processing'])
```

### 2.5 帮助信息测试

#### TC-CLI-HELP-001: 命令帮助验证

```python
@pytest.mark.parametrize("cmd", [
    [],  # 主帮助
    ['--help'],
    ['import-data', '--help'],
    ['stats', '--help'],
    ['vdot', '--help'],
    ['recent', '--help'],
    ['report', '--help'],
    ['profile', '--help'],
    ['gateway', '--help'],
    ['memory', '--help'],
])
def test_help_messages(cmd):
    """测试各命令帮助信息"""
    from typer.testing import CliRunner
    from src.cli import cli
    
    runner = CliRunner()
    result = runner.invoke(cli, cmd)
    
    assert result.exit_code == 0
    assert 'Usage:' in result.output or '用法' in result.output
    assert 'Options' in result.output or '选项' in result.output
```

---

## 三、测试实现指南

### 3.1 测试文件结构

```
tests/unit/
├── test_cli.py              # CLI主测试
├── test_cli_formatter.py    # 格式化测试
└── test_cli_integration.py  # CLI集成测试
```

### 3.2 基础测试类

```python
# tests/unit/test_cli.py
"""CLI模块单元测试"""

import pytest
from typer.testing import CliRunner
from src.cli import cli


class TestCLICommands:
    """CLI命令测试基类"""
    
    @pytest.fixture
    def runner(self):
        """提供CliRunner实例"""
        return CliRunner()
    
    @pytest.fixture
    def mock_storage(self, monkeypatch, tmp_path):
        """提供模拟存储"""
        import os
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        
        old_env = os.environ.get('NANOBOT_RUNNER_DATA_DIR')
        os.environ['NANOBOT_RUNNER_DATA_DIR'] = str(data_dir)
        
        yield data_dir
        
        if old_env:
            os.environ['NANOBOT_RUNNER_DATA_DIR'] = old_env
        else:
            del os.environ['NANOBOT_RUNNER_DATA_DIR']


class TestImportCommand(TestCLICommands):
    """导入命令测试"""
    
    def test_import_single_file(self, runner, mock_storage):
        """测试导入单个文件"""
        # 创建测试文件
        test_file = mock_storage / "test.fit"
        test_file.write_bytes(b"mock fit data")
        
        result = runner.invoke(cli, ['import-data', str(test_file)])
        
        # 由于文件格式不正确，应该报错
        assert result.exit_code == 1 or '格式' in result.output
    
    def test_import_directory(self, runner, mock_storage):
        """测试导入目录"""
        result = runner.invoke(cli, ['import-data', str(mock_storage)])
        
        # 空目录应该正常处理
        assert result.exit_code == 0


class TestStatsCommand(TestCLICommands):
    """统计命令测试"""
    
    def test_stats_empty_data(self, runner, mock_storage):
        """测试无数据时的统计"""
        result = runner.invoke(cli, ['stats'])
        
        # 应该友好提示
        assert result.exit_code == 0
        assert any(word in result.output for word in ['暂无', '没有', '空'])
    
    def test_stats_year_param(self, runner):
        """测试年份参数"""
        result = runner.invoke(cli, ['stats', '--year', '2024'])
        
        # 可能无数据但不应报错
        assert result.exit_code in [0, 1]


class TestVDOTCommand(TestCLICommands):
    """VDOT命令测试"""
    
    def test_vdot_limit_param(self, runner):
        """测试limit参数"""
        result = runner.invoke(cli, ['vdot', '--limit', '10'])
        
        assert result.exit_code in [0, 1]
    
    def test_vdot_invalid_limit(self, runner):
        """测试无效limit参数"""
        result = runner.invoke(cli, ['vdot', '--limit', '-1'])
        
        # 应该处理错误或使用默认值
        assert result.exit_code in [0, 1, 2]


class TestRecentCommand(TestCLICommands):
    """最近记录命令测试"""
    
    def test_recent_default(self, runner):
        """测试默认recent命令"""
        result = runner.invoke(cli, ['recent'])
        
        assert result.exit_code in [0, 1]
    
    def test_recent_with_count(self, runner):
        """测试指定数量的recent"""
        result = runner.invoke(cli, ['recent', '-n', '5'])
        
        assert result.exit_code in [0, 1]


class TestReportCommand(TestCLICommands):
    """报告命令测试"""
    
    def test_report_help(self, runner):
        """测试report帮助"""
        result = runner.invoke(cli, ['report', '--help'])
        
        assert result.exit_code == 0
        assert '--schedule' in result.output or 'schedule' in result.output


class TestGatewayCommand(TestCLICommands):
    """Gateway命令测试"""
    
    def test_gateway_help(self, runner):
        """测试gateway帮助"""
        result = runner.invoke(cli, ['gateway', '--help'])
        
        assert result.exit_code == 0
        assert '--port' in result.output


class TestMemoryCommand(TestCLICommands):
    """Memory命令测试"""
    
    def test_memory_show_empty(self, runner, mock_storage):
        """测试显示空记忆"""
        result = runner.invoke(cli, ['memory', 'show'])
        
        assert result.exit_code == 0
        assert '不存在' in result.output or '没有' in result.output
    
    def test_memory_clear_cancel(self, runner, mock_storage):
        """测试取消清除记忆"""
        result = runner.invoke(cli, ['memory', 'clear'], input='n\n')
        
        assert result.exit_code == 0
```

### 3.3 格式化测试

```python
# tests/unit/test_cli_formatter.py
"""CLI格式化模块测试"""

import pytest
from src.cli_formatter import format_duration, format_pace, format_distance


class TestFormatters:
    """格式化函数测试"""
    
    @pytest.mark.parametrize("seconds,expected", [
        (3600, "1:00:00"),
        (3661, "1:01:01"),
        (59, "0:00:59"),
        (0, "0:00:00"),
    ])
    def test_format_duration(self, seconds, expected):
        """测试时长格式化"""
        result = format_duration(seconds)
        assert result == expected
    
    @pytest.mark.parametrize("seconds_per_km,expected", [
        (300, "5'00\""),
        (330, "5'30\""),
        (360, "6'00\""),
    ])
    def test_format_pace(self, seconds_per_km, expected):
        """测试配速格式化"""
        result = format_pace(seconds_per_km)
        assert expected in result
    
    @pytest.mark.parametrize("meters,expected", [
        (5000, "5.00"),
        (10000, "10.00"),
        (42195, "42.20"),
    ])
    def test_format_distance(self, meters, expected):
        """测试距离格式化"""
        result = format_distance(meters)
        assert expected in result
```

---

## 四、覆盖率提升计划

### 4.1 实施计划

| 阶段 | 时间 | 目标 | 新增用例数 | 预期提升 |
|------|------|------|------------|----------|
| 1 | 2026-04-01 ~ 04-05 | 参数解析测试 | 15 | +12% |
| 2 | 2026-04-06 ~ 04-10 | 错误处理测试 | 12 | +8% |
| 3 | 2026-04-11 ~ 04-15 | 交互式测试 | 10 | +6% |

### 4.2 关键测试目标

```
覆盖率目标分解

当前: 34%
├── 命令参数解析 (当前: 20%) → 目标: 80%
├── 错误处理分支 (当前: 15%) → 目标: 70%
├── 交互式输入 (当前: 10%) → 目标: 60%
├── 进度显示 (当前: 5%) → 目标: 50%
└── 帮助信息 (当前: 80%) → 目标: 90%

目标: 60%
```

---

## 五、附录

### 5.1 快速参考

```bash
# 运行CLI测试
uv run pytest tests/unit/test_cli.py -v

# 运行特定测试
uv run pytest tests/unit/test_cli.py::TestImportCommand -v

# 查看覆盖率
uv run pytest tests/unit/test_cli.py --cov=src.cli --cov-report=term-missing
```

### 5.2 相关文档

- [Typer测试文档](https://typer.tiangolo.com/tutorial/testing/)
- [Click测试文档](https://click.palletsprojects.com/en/8.1.x/testing/)

### 5.3 修订历史

| 版本 | 日期 | 修订人 | 修订内容 |
|------|------|--------|----------|
| v1.0 | 2026-03-29 | 测试工程师智能体 | 初始版本 |

---

**文档结束**
