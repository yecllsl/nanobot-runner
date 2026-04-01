#!/usr/bin/env python3
"""
预提交检查脚本
基于 AGENTS.md 中的提交前 Checklist 实现

功能：
- 执行 black 代码格式化检查
- 执行 isort 导入排序检查
- 执行 mypy 类型检查
- 执行 pytest 单元测试
- 检查 Schema/TOOL_DESCRIPTIONS 更新
- 生成详细的检查报告

使用方式：
1. 手动执行：uv run python scripts/pre-commit-check.py
2. Git Hook：自动在 git commit 前执行
"""

import os
import sys
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum

# ========== 全局编码设置（Windows 兼容）==========
if sys.platform == "win32":
    # 强制 Python 标准输出为 UTF-8
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    # 强制 subprocess 默认使用 UTF-8
    os.environ["PYTHONUTF8"] = "1"   # Python 3.7+ 的 UTF-8 模式
    os.environ["PYTHONIOENCODING"] = "utf-8"
# ================================================

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.logger import get_logger

logger = get_logger(__name__)


class CheckStatus(Enum):
    """检查状态枚举"""
    PASSED = "✅"
    FAILED = "❌"
    WARNING = "⚠️"
    SKIPPED = "⏭️"


@dataclass
class CheckResult:
    """检查结果"""
    name: str
    status: CheckStatus
    message: str
    duration: float
    command: str
    output: str = ""


class PreCommitChecker:
    """预提交检查器"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.results: List[CheckResult] = []
        self.start_time = time.time()
        
    def run_command(self, command: str, check_name: str) -> CheckResult:
        """运行命令并返回检查结果"""
        start_time = time.time()
        
        try:
            logger.info(f"开始执行: {check_name}")
            logger.debug(f"命令: {command}")
            
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=300  # 5分钟超时
            )
            
            duration = time.time() - start_time
            
            if result.returncode == 0:
                status = CheckStatus.PASSED
                message = f"检查通过 ({duration:.2f}s)"
            else:
                status = CheckStatus.FAILED
                message = f"检查失败 ({duration:.2f}s)"
            
            return CheckResult(
                name=check_name,
                status=status,
                message=message,
                duration=duration,
                command=command,
                output=result.stdout + result.stderr
            )
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return CheckResult(
                name=check_name,
                status=CheckStatus.FAILED,
                message=f"执行超时 ({duration:.2f}s)",
                duration=duration,
                command=command,
                output="命令执行超时"
            )
        except Exception as e:
            duration = time.time() - start_time
            return CheckResult(
                name=check_name,
                status=CheckStatus.FAILED,
                message=f"执行异常: {e} ({duration:.2f}s)",
                duration=duration,
                command=command,
                output=str(e)
            )
    
    def check_black_formatting(self) -> CheckResult:
        """检查代码格式化"""
        command = "uv run black --check src/ tests/"
        return self.run_command(command, "black 代码格式化检查")
    
    def check_isort_imports(self) -> CheckResult:
        """检查导入排序"""
        command = "uv run isort --check-only src/ tests/"
        return self.run_command(command, "isort 导入排序检查")
    
    def check_mypy_types(self) -> CheckResult:
        """检查类型注解"""
        command = "uv run mypy src/ --ignore-missing-imports"
        return self.run_command(command, "mypy 类型检查")
    
    def check_pytest_tests(self) -> CheckResult:
        """运行单元测试"""
        command = "uv run pytest tests/unit/ -v"
        return self.run_command(command, "pytest 单元测试")
    
    def check_schema_updates(self) -> CheckResult:
        """检查 Schema/TOOL_DESCRIPTIONS 更新"""
        # 检查是否有新增字段或工具需要更新文档
        start_time = time.time()
        
        try:
            # 检查核心 Schema 文件
            schema_files = [
                "src/core/schema.py",
                "src/agents/tools.py"
            ]
            
            # 检查 TOOL_DESCRIPTIONS 常量
            tools_file = "src/agents/tools.py"
            if os.path.exists(tools_file):
                with open(tools_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if "TOOL_DESCRIPTIONS" in content:
                        # 简单的检查：确保 TOOL_DESCRIPTIONS 存在且格式正确
                        if "TOOL_DESCRIPTIONS = {" in content:
                            status = CheckStatus.PASSED
                            message = "TOOL_DESCRIPTIONS 格式正确"
                        else:
                            status = CheckStatus.WARNING
                            message = "TOOL_DESCRIPTIONS 可能需要更新"
                    else:
                        status = CheckStatus.SKIPPED
                        message = "未找到 TOOL_DESCRIPTIONS，跳过检查"
            else:
                status = CheckStatus.SKIPPED
                message = "工具文件不存在，跳过检查"
            
            duration = time.time() - start_time
            return CheckResult(
                name="Schema/TOOL_DESCRIPTIONS 更新检查",
                status=status,
                message=message,
                duration=duration,
                command="手动检查 Schema 和 TOOL_DESCRIPTIONS"
            )
            
        except Exception as e:
            duration = time.time() - start_time
            return CheckResult(
                name="Schema/TOOL_DESCRIPTIONS 更新检查",
                status=CheckStatus.FAILED,
                message=f"检查异常: {e}",
                duration=duration,
                command="手动检查 Schema 和 TOOL_DESCRIPTIONS"
            )
    
    def run_all_checks(self) -> bool:
        """运行所有检查"""
        logger.info("🔍 开始预提交检查...")
        
        # 执行所有检查
        checks = [
            self.check_black_formatting,
            self.check_isort_imports,
            self.check_mypy_types,
            self.check_pytest_tests,
            self.check_schema_updates
        ]
        
        for check_func in checks:
            result = check_func()
            self.results.append(result)
            
            # 实时显示检查结果
            print(f"{result.status.value} {result.name}: {result.message}")
            
            # 如果检查失败，显示详细信息
            if result.status == CheckStatus.FAILED and result.output:
                print(f"   详细输出:\n{result.output}")
        
        # 生成总结报告
        return self.generate_report()
    
    def generate_report(self) -> bool:
        """生成检查报告"""
        total_time = time.time() - self.start_time
        
        # 统计结果
        passed = sum(1 for r in self.results if r.status == CheckStatus.PASSED)
        failed = sum(1 for r in self.results if r.status == CheckStatus.FAILED)
        warning = sum(1 for r in self.results if r.status == CheckStatus.WARNING)
        skipped = sum(1 for r in self.results if r.status == CheckStatus.SKIPPED)
        
        print("\n" + "="*60)
        print("📋 预提交检查报告")
        print("="*60)
        
        # 显示详细结果
        for result in self.results:
            print(f"{result.status.value} {result.name}: {result.message}")
        
        print("-"*60)
        print(f"总计: {len(self.results)} 项检查")
        print(f"✅ 通过: {passed} | ❌ 失败: {failed} | ⚠️ 警告: {warning} | ⏭️ 跳过: {skipped}")
        print(f"⏱️  总耗时: {total_time:.2f}秒")
        
        # 生成修复建议
        if failed > 0:
            print("\n💡 修复建议:")
            for result in self.results:
                if result.status == CheckStatus.FAILED:
                    if "black" in result.name.lower():
                        print("  - 执行: uv run black src/ tests/")
                    elif "isort" in result.name.lower():
                        print("  - 执行: uv run isort src/ tests/")
                    elif "mypy" in result.name.lower():
                        print("  - 执行: uv run mypy src/ --ignore-missing-imports")
                    elif "pytest" in result.name.lower():
                        print("  - 执行: uv run pytest tests/unit/ -v")
        
        # 最终结论
        if failed == 0:
            print("\n🎉 所有检查通过，可以提交！")
            return True
        else:
            print(f"\n🚫 检查失败，请修复 {failed} 个问题后再提交")
            return False
    
    def get_fix_commands(self) -> List[str]:
        """获取修复命令列表"""
        fix_commands = []
        
        for result in self.results:
            if result.status == CheckStatus.FAILED:
                if "black" in result.name.lower():
                    fix_commands.append("uv run black src/ tests/")
                elif "isort" in result.name.lower():
                    fix_commands.append("uv run isort src/ tests/")
                elif "mypy" in result.name.lower():
                    fix_commands.append("uv run mypy src/ --ignore-missing-imports")
                elif "pytest" in result.name.lower():
                    fix_commands.append("uv run pytest tests/unit/ -v")
        
        return fix_commands


def main():
    """主函数"""
    checker = PreCommitChecker()
    
    try:
        success = checker.run_all_checks()
        
        # 如果是 Git Hook 模式，返回相应的退出码
        if "GIT_HOOK" in os.environ:
            sys.exit(0 if success else 1)
        else:
            sys.exit(0 if success else 1)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  检查被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 检查过程出现异常: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()