"""预提交检查两阶段调度单元测试

验证 systematic-debugging 修复：两阶段调度（轻量并行/重量级串行）+ 移除 pytest -n 4。
根因：ThreadPoolExecutor(4) + pytest-xdist(-n 4) 两层并行叠加，峰值 8-9 个重型进程。

测试策略：
- 用线程并发计数器直接验证峰值并发度（比内存监控更精确地验证根因）
- 轻/重量级检查用独立 tracker，互不干扰
- 验证 -n 4 已从所有命令路径移除
"""

from __future__ import annotations

import importlib.util
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# 加载脚本模块（文件名含连字符，需用 importlib）
_SCRIPT_PATH = (
    Path(__file__).parent.parent.parent.parent / "scripts" / "pre-commit-check.py"
)
_spec = importlib.util.spec_from_file_location("pre_commit_check", _SCRIPT_PATH)
pcm = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
_spec.loader.exec_module(pcm)  # type: ignore[union-attr]

CheckResult = pcm.CheckResult
CheckStatus = pcm.CheckStatus
PreCommitChecker = pcm.PreCommitChecker
PreCommitConfig = pcm.PreCommitConfig


def _make_tracked_check(name: str, tracker: dict, delay: float = 0.05):
    """创建带并发追踪的 mock 检查方法

    tracker 记录 current（当前并发数）、peak（峰值并发数）、order（进入顺序）。
    通过 sleep 制造可观测的时间窗口，使并行/串行可检测。
    """

    def check():
        tracker["current"] += 1
        tracker["peak"] = max(tracker["peak"], tracker["current"])
        tracker["order"].append(name)
        time.sleep(delay)
        tracker["current"] -= 1
        return CheckResult(
            name=name,
            status=CheckStatus.PASSED,
            message="ok",
            duration=0,
            command="",
        )

    return check


@pytest.fixture
def checker():
    """构造禁用缓存和增量检查的 PreCommitChecker 实例"""
    config = PreCommitConfig()
    config.cache_enabled = False
    config.incremental_check = False
    c = PreCommitChecker(config=config)
    c.console = None  # 关闭 Rich 输出，避免测试输出污染
    return c


class TestTwoPhaseScheduling:
    """两阶段调度核心逻辑测试"""

    def test_light_checks_run_in_parallel(self, checker):
        """轻量检查（ruff_format/ruff_lint/schema）应并行执行

        验证：3 个轻量检查的峰值并发数 >= 2（并行证据）
        """
        light_tracker = {"current": 0, "peak": 0, "order": []}
        heavy_tracker = {"current": 0, "peak": 0, "order": []}

        checker.check_ruff_format = _make_tracked_check(
            "ruff_format", light_tracker, delay=0.1
        )
        checker.check_ruff_lint = _make_tracked_check(
            "ruff_lint", light_tracker, delay=0.1
        )
        checker.check_schema_updates = _make_tracked_check(
            "schema", light_tracker, delay=0.1
        )
        checker.check_mypy_types = _make_tracked_check("mypy", heavy_tracker, delay=0)
        checker.check_bandit_security = _make_tracked_check(
            "bandit", heavy_tracker, delay=0
        )
        checker.check_pytest_tests = _make_tracked_check(
            "pytest", heavy_tracker, delay=0
        )

        checker.run_all_checks_parallel()

        assert light_tracker["peak"] >= 2, (
            f"轻量检查应并行执行，峰值并发数仅 {light_tracker['peak']}"
        )

    def test_heavy_checks_run_sequentially(self, checker):
        """重量级检查（mypy/bandit/pytest）应串行执行

        验证：重量级检查的峰值并发数 <= 1（无重叠）
        """
        light_tracker = {"current": 0, "peak": 0, "order": []}
        heavy_tracker = {"current": 0, "peak": 0, "order": []}

        checker.check_ruff_format = _make_tracked_check(
            "ruff_format", light_tracker, delay=0
        )
        checker.check_ruff_lint = _make_tracked_check(
            "ruff_lint", light_tracker, delay=0
        )
        checker.check_schema_updates = _make_tracked_check(
            "schema", light_tracker, delay=0
        )
        # 重量级检查带较长延迟，确保能检测到重叠
        checker.check_mypy_types = _make_tracked_check("mypy", heavy_tracker, delay=0.1)
        checker.check_bandit_security = _make_tracked_check(
            "bandit", heavy_tracker, delay=0.1
        )
        checker.check_pytest_tests = _make_tracked_check(
            "pytest", heavy_tracker, delay=0.1
        )

        checker.run_all_checks_parallel()

        assert heavy_tracker["peak"] <= 1, (
            f"重量级检查应串行执行，峰值并发数为 {heavy_tracker['peak']}（存在重叠）"
        )

    def test_heavy_checks_preserve_order(self, checker):
        """重量级检查应按固定顺序串行执行（mypy → bandit → pytest）"""
        heavy_tracker = {"current": 0, "peak": 0, "order": []}
        noop = {"current": 0, "peak": 0, "order": []}

        checker.check_ruff_format = _make_tracked_check("rf", noop, delay=0)
        checker.check_ruff_lint = _make_tracked_check("rl", noop, delay=0)
        checker.check_schema_updates = _make_tracked_check("sc", noop, delay=0)
        checker.check_mypy_types = _make_tracked_check(
            "mypy", heavy_tracker, delay=0.01
        )
        checker.check_bandit_security = _make_tracked_check(
            "bandit", heavy_tracker, delay=0.01
        )
        checker.check_pytest_tests = _make_tracked_check(
            "pytest", heavy_tracker, delay=0.01
        )

        checker.run_all_checks_parallel()

        assert heavy_tracker["order"] == ["mypy", "bandit", "pytest"], (
            f"重量级检查顺序应为 mypy→bandit→pytest，实际 {heavy_tracker['order']}"
        )

    def test_all_checks_executed(self, checker):
        """两阶段调度应执行全部 6 项检查（无遗漏）"""
        tracker = {"current": 0, "peak": 0, "order": []}

        checker.check_ruff_format = _make_tracked_check("ruff_format", tracker, delay=0)
        checker.check_ruff_lint = _make_tracked_check("ruff_lint", tracker, delay=0)
        checker.check_mypy_types = _make_tracked_check("mypy", tracker, delay=0)
        checker.check_bandit_security = _make_tracked_check("bandit", tracker, delay=0)
        checker.check_pytest_tests = _make_tracked_check("pytest", tracker, delay=0)
        checker.check_schema_updates = _make_tracked_check("schema", tracker, delay=0)

        checker.run_all_checks_parallel()

        assert set(tracker["order"]) == {
            "ruff_format",
            "ruff_lint",
            "mypy",
            "bandit",
            "pytest",
            "schema",
        }

    def test_peak_concurrency_under_threshold(self, checker):
        """峰值并发数不超过 max_workers + 1（轻量并行上限 + 1 个重量级）

        这是进程爆炸根因的直接守护：旧方案峰值 = max_workers + 4（xdist）= 8，
        两阶段调度后峰值 <= max_workers + 1 = 5。
        """
        tracker = {"current": 0, "peak": 0, "order": []}
        # 所有检查带相同延迟，制造最大重叠窗口
        for name, attr in [
            ("ruff_format", "check_ruff_format"),
            ("ruff_lint", "check_ruff_lint"),
            ("schema", "check_schema_updates"),
            ("mypy", "check_mypy_types"),
            ("bandit", "check_bandit_security"),
            ("pytest", "check_pytest_tests"),
        ]:
            setattr(checker, attr, _make_tracked_check(name, tracker, delay=0.1))

        checker.run_all_checks_parallel()

        threshold = checker.config.max_workers + 1
        assert tracker["peak"] <= threshold, (
            f"峰值并发数 {tracker['peak']} 超过阈值 {threshold}"
            f"（max_workers={checker.config.max_workers} + 1 重量级）"
        )


class TestNoXdistParallelism:
    """验证 pytest -n 4（xdist 嵌套并行）已移除"""

    def test_default_config_pytest_no_n4(self):
        """默认配置的 pytest 命令不应含 -n 4"""
        config = PreCommitConfig()
        cmd = config.pytest.command or ""
        assert "-n 4" not in cmd, f"默认 pytest 命令仍含 -n 4: {cmd}"
        assert "-n " not in cmd, f"默认 pytest 命令仍含 xdist 并行: {cmd}"

    def test_check_pytest_tests_no_n4(self, checker):
        """check_pytest_tests 生成的命令不应含 -n 4"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        with patch.object(pcm.subprocess, "run", return_value=mock_result) as mock_run:
            checker.check_pytest_tests()
            assert mock_run.called, "subprocess.run 未被调用"
            called_cmd = mock_run.call_args[0][0]
            assert "-n 4" not in called_cmd, f"pytest 命令仍含 -n 4: {called_cmd}"
            assert "-n " not in called_cmd, f"pytest 命令仍含 xdist: {called_cmd}"

    def test_incremental_test_command_no_n4(self, checker):
        """增量测试命令不应含 -n 4"""
        checker.config.incremental_check = True
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        with (
            patch.object(
                PreCommitChecker,
                "get_changed_files",
                return_value=[Path("src/core/calculators/vdot.py")],
            ),
            patch.object(pcm.subprocess, "run", return_value=mock_result) as mock_run,
        ):
            checker.check_pytest_tests()
            assert mock_run.called, "subprocess.run 未被调用"
            called_cmd = mock_run.call_args[0][0]
            assert "-n 4" not in called_cmd, f"增量测试命令仍含 -n 4: {called_cmd}"


class TestSingleInstanceLock:
    """单实例锁测试 — 防止双进程并发"""

    def test_lock_prevents_concurrent_instance(self, tmp_path: Path):
        """已存在有效锁时，第二个实例应被拒绝"""
        lock_dir = tmp_path / ".nanobot-runner"
        lock_file = lock_dir / ".pre-commit.lock"

        # 模拟第一个实例获取锁（使用当前时间，确保锁有效）
        lock_dir.mkdir(parents=True, exist_ok=True)
        lock_file.write_text(
            f"{os.getpid()}\n{datetime.now().isoformat()}", encoding="utf-8"
        )

        # 第二个实例尝试获取锁应失败
        lock = pcm.SingleInstanceLock(lock_dir=lock_dir)
        assert lock.acquire() is False, "应有有效锁存在时 acquire 应返回 False"
        assert lock.is_locked is False

    def test_lock_acquire_success_when_no_lock(self, tmp_path: Path):
        """无锁文件时，应成功获取锁"""
        lock_dir = tmp_path / ".nanobot-runner"
        lock = pcm.SingleInstanceLock(lock_dir=lock_dir)
        assert lock.acquire() is True, "无锁文件时应成功获取锁"
        assert lock.is_locked is True
        lock.release()

    def test_stale_lock_is_overwritten(self, tmp_path: Path):
        """过期锁（超过超时时间）应被覆写"""
        lock_dir = tmp_path / ".nanobot-runner"
        lock_file = lock_dir / ".pre-commit.lock"
        lock_dir.mkdir(parents=True, exist_ok=True)

        # 模拟一个很早的锁（超时 300s，写入时间设为 600s 前）
        stale_time = datetime.now() - timedelta(seconds=600)
        lock_file.write_text(f"99999\n{stale_time.isoformat()}", encoding="utf-8")

        lock = pcm.SingleInstanceLock(lock_dir=lock_dir, timeout_seconds=300)
        assert lock.acquire() is True, "过期锁应被覆写"
        assert lock.is_locked is True
        lock.release()

    def test_lock_contains_pid(self, tmp_path: Path):
        """锁文件应包含当前进程 PID"""
        lock_dir = tmp_path / ".nanobot-runner"
        lock = pcm.SingleInstanceLock(lock_dir=lock_dir)
        lock.acquire()
        content = (lock_dir / ".pre-commit.lock").read_text(encoding="utf-8")
        assert str(os.getpid()) in content, "锁文件应包含当前 PID"
        lock.release()

    def test_release_removes_lock_file(self, tmp_path: Path):
        """release 应删除锁文件"""
        lock_dir = tmp_path / ".nanobot-runner"
        lock_file = lock_dir / ".pre-commit.lock"
        lock = pcm.SingleInstanceLock(lock_dir=lock_dir)
        lock.acquire()
        assert lock_file.exists()
        lock.release()
        assert not lock_file.exists(), "release 应删除锁文件"
        assert lock.is_locked is False


class TestShellFalse:
    """验证 subprocess.run 使用 shell=False（无 cmd.exe 包装）"""

    def test_run_command_uses_shell_false(self, checker):
        """run_command 调用 subprocess.run 时 shell 应为 False"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        with patch.object(pcm.subprocess, "run", return_value=mock_result) as mock_run:
            checker.run_command("uv run echo hello", "test")
            assert mock_run.called
            # 验证 shell 参数不是 True（未传递或 False 均可）
            shell_arg = mock_run.call_args[1].get("shell")
            assert shell_arg is not True, (
                f"subprocess.run 不应使用 shell=True，实际 shell={shell_arg}"
            )
            # 验证命令是 list 而非 string
            cmd_arg = mock_run.call_args[0][0]
            assert isinstance(cmd_arg, list), (
                f"命令应为 list 类型，实际 {type(cmd_arg).__name__}: {cmd_arg}"
            )

    def test_auto_fix_uses_shell_false(self, checker):
        """auto_fix_issues 中的 subprocess.run 也应使用 shell=False"""
        # 让检查失败，触发 auto_fix
        checker.results = [
            pcm.CheckResult(
                name="ruff format 代码格式化检查",
                status=pcm.CheckStatus.FAILED,
                message="fail",
                duration=0,
                command="",
            )
        ]
        with patch.object(
            pcm.subprocess, "run", return_value=MagicMock(returncode=0)
        ) as mock_run:
            checker.auto_fix_issues()
            assert mock_run.called
            shell_arg = mock_run.call_args[1].get("shell")
            assert shell_arg is not True, (
                f"auto_fix 中的 subprocess.run 不应使用 shell=True，实际 shell={shell_arg}"
            )
