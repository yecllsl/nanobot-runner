#!/usr/bin/env python3
"""诊断脚本：追踪 pre-commit-check.py 运行时的进程树结构

用于验证双进程假设：
- 假设 1：shell=True 产生额外的 cmd.exe 包装进程
- 假设 2：uv run 产生额外的 uv.exe 包装进程
- 假设 3：旧代码全并行 + pytest -n 4 导致进程数量爆炸

输出：
- 进程树结构（父子关系）
- 每个 Python 进程的完整命令行
- 每个进程的内存占用
"""

from __future__ import annotations

import subprocess
import sys
import time

try:
    import psutil
except ImportError:
    print("请先安装 psutil: uv add --dev psutil")
    sys.exit(1)


def get_process_tree() -> list[dict]:
    """获取当前进程及其所有子进程的详细信息"""
    parent = psutil.Process()
    result = []

    def _walk(proc, depth=0):
        try:
            info = {
                "depth": depth,
                "pid": proc.pid,
                "name": proc.name(),
                "cmdline": " ".join(proc.cmdline()) if proc.cmdline() else "(empty)",
                "memory_mb": proc.memory_info().rss / 1024 / 1024,
                "status": proc.status(),
            }
            # 截断过长的命令行
            if len(info["cmdline"]) > 200:
                info["cmdline"] = info["cmdline"][:197] + "..."
            result.append(info)

            for child in proc.children():
                _walk(child, depth + 1)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    _walk(parent)
    return result


def print_tree(processes: list[dict]) -> None:
    """打印进程树"""
    print(f"\n{'=' * 80}")
    print("进程树诊断")
    print(f"{'=' * 80}")
    print(f"{'PID':>8}  {'深度':>4}  {'内存(MB)':>10}  {'状态':<10}  进程名 / 命令行")
    print("-" * 80)

    for p in processes:
        indent = "  " * p["depth"]
        # 高亮 Python 进程
        is_python = "python" in p["name"].lower()
        marker = "🐍" if is_python else "  "
        print(
            f"{marker}{p['pid']:>6}  {p['depth']:>4}  {p['memory_mb']:>10.1f}  "
            f"{p['status']:<10}  {indent}{p['name']}"
        )
        # Python 进程显示完整命令行
        if is_python:
            print(
                f"{' ':>8}  {' ':>4}  {' ':>10}  {' ':10}  {indent}  ↳ {p['cmdline']}"
            )

    print("-" * 80)
    python_procs = [p for p in processes if "python" in p["name"].lower()]
    total_mem = sum(p["memory_mb"] for p in processes)
    print(f"统计: 总进程 {len(processes)} 个, Python 进程 {len(python_procs)} 个")
    print(f"总内存: {total_mem:.1f} MB")


def test_shell_true_vs_false():
    """对比 shell=True vs shell=False 的进程树差异"""
    print("\n" + "=" * 80)
    print("对比测试: shell=True vs shell=False")
    print("=" * 80)

    # 测试 shell=True
    print("\n--- shell=True ---")
    proc = subprocess.Popen(
        'python -c "import time; time.sleep(2)"',
        shell=True,
    )
    time.sleep(0.5)
    tree = get_process_tree_for_pid(proc.pid)
    print(f"直接子进程数: {len(tree)}")
    for p in tree:
        print(f"  {p['name']} (PID={p['pid']}, {p['memory_mb']:.1f}MB)")
    proc.terminate()
    proc.wait()

    # 测试 shell=False
    print("\n--- shell=False ---")
    proc = subprocess.Popen(
        ["python", "-c", "import time; time.sleep(2)"],
        shell=False,
    )
    time.sleep(0.5)
    tree = get_process_tree_for_pid(proc.pid)
    print(f"直接子进程数: {len(tree)}")
    for p in tree:
        print(f"  {p['name']} (PID={p['pid']}, {p['memory_mb']:.1f}MB)")
    proc.terminate()
    proc.wait()


def get_process_tree_for_pid(pid: int) -> list[dict]:
    """获取指定 PID 的直接子进程"""
    result = []
    try:
        parent = psutil.Process(pid)
        for child in parent.children(recursive=False):
            result.append(
                {
                    "pid": child.pid,
                    "name": child.name(),
                    "memory_mb": child.memory_info().rss / 1024 / 1024,
                }
            )
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
    return result


def main():
    """诊断入口"""
    # 先做 shell=True vs shell=False 对比
    test_shell_true_vs_false()

    # 显示当前进程树
    print("\n" + "=" * 80)
    print("当前进程树（诊断脚本自身）")
    print("=" * 80)
    tree = get_process_tree()
    print_tree(tree)

    print("\n💡 运行建议:")
    print("  uv run python scripts/diagnose_process_tree.py")
    print("  或在 pre-commit-check.py 的 run_command 中临时添加")
    print("  print(get_process_tree()) 来捕获实际运行时的进程树")


if __name__ == "__main__":
    main()
