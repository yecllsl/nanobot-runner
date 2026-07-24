#!/usr/bin/env python3
"""内存峰值监控验证脚本

验证 pre-commit-check 两阶段调度的内存优化效果。
用 psutil 采样运行期间所有 Python 进程的内存峰值和进程数峰值。

使用方式：uv run python scripts/verify_memory_peak.py

输出：
- 峰值进程数（应 <= max_workers + 1 = 5）
- 峰值内存（MB）
- 各检查结果
"""

from __future__ import annotations

import importlib.util
import logging
import threading
import time
from pathlib import Path

import psutil

# 加载 pre-commit-check 模块（文件名含连字符，需用 importlib）
_script_path = Path(__file__).parent / "pre-commit-check.py"
_spec = importlib.util.spec_from_file_location("pre_commit_check", _script_path)
pcm = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
_spec.loader.exec_module(pcm)  # type: ignore[union-attr]

logger = logging.getLogger(__name__)


class MemoryMonitor:
    """后台采样进程树内存峰值和进程数峰值

    区分两种进程数：
    - 总进程数：含 cmd.exe/uv.exe 等辅助进程
    - Python 进程数：仅 python.exe，对应重型检查的实际内存消耗者
    """

    def __init__(self, interval: float = 0.2):
        self.interval = interval
        self.peak_mem: int = 0  # 峰值内存（字节）
        self.peak_procs: int = 0  # 峰值总进程数
        self.peak_python_procs: int = 0  # 峰值 Python 进程数
        self.samples: list[
            tuple[float, int, int, int]
        ] = []  # (时间戳, 总进程数, Python进程数, 内存MB)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._start_time = 0.0

    def start(self) -> None:
        self._start_time = time.time()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)

    def _run(self) -> None:
        """后台采样循环：统计当前进程及其所有子进程的内存总量"""
        parent = psutil.Process()
        while not self._stop.is_set():
            try:
                children = parent.children(recursive=True)
                procs = [parent] + children
                total_mem = 0
                proc_count = 0
                python_count = 0
                for p in procs:
                    try:
                        total_mem += p.memory_info().rss
                        proc_count += 1
                        # 统计 Python 解释器进程（重型检查的实际内存消耗者）
                        if p.name().lower() in ("python.exe", "pythonw.exe"):
                            python_count += 1
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                self.peak_mem = max(self.peak_mem, total_mem)
                self.peak_procs = max(self.peak_procs, proc_count)
                self.peak_python_procs = max(self.peak_python_procs, python_count)
                self.samples.append(
                    (
                        time.time() - self._start_time,
                        proc_count,
                        python_count,
                        total_mem // (1024 * 1024),
                    )
                )
            except Exception as e:
                logger.debug(f"采样异常: {e}")
            time.sleep(self.interval)


def main() -> None:
    """运行 pre-commit-check 并监控内存峰值"""
    logging.basicConfig(level=logging.WARNING)

    # 配置：全量检查、禁用缓存、禁用增量（确保实际运行所有检查）
    config = pcm.PreCommitConfig()
    config.incremental_check = False
    config.cache_enabled = False
    config.skip_doc_only_commits = False  # 确保不跳过

    checker = pcm.PreCommitChecker(config=config)
    checker.console = None  # 关闭 Rich 输出，避免干扰

    print("=" * 60)
    print("内存峰值监控验证（两阶段调度）")
    print("=" * 60)
    print(f"max_workers: {config.max_workers}")
    print(f"预期峰值 Python 进程数 <= {config.max_workers + 1}")
    print("  （轻量检查不启动 Python 子进程；重量级串行仅 1 个 Python 进程）")
    print("  旧方案（全并行 + pytest -n 4）峰值 Python 进程数 ≈ 8-9")
    print()

    monitor = MemoryMonitor(interval=0.2)
    monitor.start()

    start = time.time()
    try:
        result = checker.run_all_checks_parallel()
    except Exception as e:
        print(f"运行异常: {e}")
        result = False
    elapsed = time.time() - start

    monitor.stop()

    print()
    print("=" * 60)
    print("验证结果")
    print("=" * 60)
    print(f"检查结果: {'✅ 全部通过' if result else '❌ 存在失败项（不影响内存验证）'}")
    print(f"耗时: {elapsed:.1f}s")
    print(f"峰值总进程数: {monitor.peak_procs}（含 cmd.exe/uv.exe 辅助进程）")
    print(f"峰值 Python 进程数: {monitor.peak_python_procs}")
    print(f"峰值内存: {monitor.peak_mem / 1024 / 1024:.1f} MB")
    print()

    # 验证峰值 Python 进程数不超阈值
    # 阈值 = max_workers + 1：轻量并行不启动 Python 子进程（ruff 是 Rust），
    # 重量级串行仅 1 个 Python 进程。旧方案（xdist -n 4）峰值 = 1(主) + 4(xdist) + mypy + bandit ≈ 8
    threshold = config.max_workers + 1
    if monitor.peak_python_procs <= threshold:
        print(
            f"✅ 峰值 Python 进程数 {monitor.peak_python_procs} <= 阈值 {threshold}（验证通过）"
        )
    else:
        print(
            f"❌ 峰值 Python 进程数 {monitor.peak_python_procs} > 阈值 {threshold}（验证失败）"
        )

    # 输出进程数时间线（简化）
    if monitor.samples:
        print()
        print("进程数时间线（采样点）:")
        for t, procs, py_procs, mem in monitor.samples[::5]:  # 每 5 个采样点取 1 个
            print(
                f"  {t:6.1f}s  总进程={procs:2d}  Python进程={py_procs}  内存={mem:5d} MB"
            )


if __name__ == "__main__":
    main()
