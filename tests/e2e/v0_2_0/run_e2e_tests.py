#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v0.2.0 Agent自然语言交互功能E2E测试一键执行脚本

本脚本提供在Trae IDE中一键执行所有E2E测试的功能，包括：
- 自动环境检查和依赖验证
- 测试数据准备
- 执行所有E2E测试用例
- 生成测试报告
- 环境清理

执行方式：
uv run python tests/e2e/v0.2.0/run_e2e_tests.py

作者: 测试工程师
创建日期: 2026-03-06
版本: 1.0
"""

import os
import sys
import time
import json
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


def check_environment() -> Dict[str, Any]:
    """检查测试环境"""
    print("🔍 检查测试环境...")
    
    environment_info = {
        "python_version": sys.version,
        "project_root": str(project_root),
        "uv_available": False,
        "dependencies_installed": False,
        "test_data_ready": False,
        "issues": []
    }
    
    # 检查uv是否可用
    try:
        result = subprocess.run(["uv", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            environment_info["uv_available"] = True
            environment_info["uv_version"] = result.stdout.strip()
        else:
            environment_info["issues"].append("uv命令不可用")
    except FileNotFoundError:
        environment_info["issues"].append("uv未安装")
    
    # 检查项目依赖
    if environment_info["uv_available"]:
        try:
            result = subprocess.run(
                ["uv", "run", "python", "-c", "import nanobot_ai; import polars; print('OK')"],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0 and "OK" in result.stdout:
                environment_info["dependencies_installed"] = True
            else:
                environment_info["issues"].append("项目依赖未正确安装")
        except Exception as e:
            environment_info["issues"].append(f"依赖检查失败: {e}")
    
    # 检查测试数据
    test_data_dir = Path.home() / ".nanobot-runner" / "test_data"
    if test_data_dir.exists():
        parquet_files = list(test_data_dir.glob("*.parquet"))
        if parquet_files:
            environment_info["test_data_ready"] = True
            environment_info["test_data_files"] = len(parquet_files)
        else:
            environment_info["issues"].append("测试数据目录存在但无数据文件")
    else:
        environment_info["issues"].append("测试数据目录不存在")
    
    return environment_info


def prepare_test_data() -> bool:
    """准备测试数据"""
    print("📊 准备测试数据...")
    
    try:
        # 运行测试数据生成脚本
        result = subprocess.run([
            "uv", "run", "python", "tests/e2e/v0_2_0/generate_test_data.py", "--action", "generate"
        ], cwd=project_root, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print("✅ 测试数据准备完成")
            return True
        else:
            print(f"❌ 测试数据准备失败: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("❌ 测试数据准备超时")
        return False
    except Exception as e:
        print(f"❌ 测试数据准备错误: {e}")
        return False


def run_e2e_tests() -> Dict[str, Any]:
    """执行E2E测试"""
    print("🚀 开始执行E2E测试...")
    
    test_results = {
        "start_time": datetime.now().isoformat(),
        "total_tests": 0,
        "passed_tests": 0,
        "failed_tests": 0,
        "skipped_tests": 0,
        "test_cases": [],
        "performance_metrics": {}
    }
    
    # 定义要执行的测试用例
    test_cases = [
        {
            "name": "新用户初始化流程",
            "file": "test_agent_e2e_main.py",
            "test": "test_new_user_initialization_flow",
            "marker": "e2e",
            "timeout": 120
        },
        {
            "name": "日常训练查询流程", 
            "file": "test_agent_e2e_main.py",
            "test": "test_daily_training_query_flow",
            "marker": "e2e",
            "timeout": 180
        },
        {
            "name": "体能状态评估流程",
            "file": "test_agent_e2e_main.py", 
            "test": "test_fitness_assessment_flow",
            "marker": "e2e",
            "timeout": 180
        },
        {
            "name": "边界条件处理流程",
            "file": "test_agent_e2e_main.py",
            "test": "test_boundary_conditions_flow", 
            "marker": "e2e",
            "timeout": 120
        },
        {
            "name": "性能基准测试",
            "file": "test_agent_e2e_main.py",
            "test": "test_performance_benchmark",
            "marker": "e2e",
            "timeout": 300
        }
    ]
    
    test_results["total_tests"] = len(test_cases)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 执行测试 {i}/{len(test_cases)}: {test_case['name']}")
        
        test_case_result = {
            "name": test_case["name"],
            "status": "pending",
            "duration": 0,
            "error": None,
            "start_time": datetime.now().isoformat()
        }
        
        try:
            start_time = time.time()
            
            # 构建pytest命令
            pytest_cmd = [
                "uv", "run", "pytest", 
                f"tests/e2e/v0_2_0/{test_case['file']}::{test_case['test']}",
                "-v", "--tb=short", "-m", test_case["marker"],
                "--timeout", str(test_case["timeout"])
            ]
            
            result = subprocess.run(
                pytest_cmd,
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=test_case["timeout"] + 10  # 额外10秒缓冲
            )
            
            duration = time.time() - start_time
            test_case_result["duration"] = round(duration, 2)
            
            if result.returncode == 0:
                test_case_result["status"] = "passed"
                test_results["passed_tests"] += 1
                print(f"✅ {test_case['name']} - 通过 ({duration:.2f}秒)")
            else:
                test_case_result["status"] = "failed"
                test_results["failed_tests"] += 1
                test_case_result["error"] = result.stderr
                print(f"❌ {test_case['name']} - 失败 ({duration:.2f}秒)")
                print(f"错误信息: {result.stderr[:200]}...")
                
        except subprocess.TimeoutExpired:
            test_case_result["status"] = "failed"
            test_results["failed_tests"] += 1
            test_case_result["error"] = "测试执行超时"
            print(f"❌ {test_case['name']} - 超时")
            
        except Exception as e:
            test_case_result["status"] = "failed"
            test_results["failed_tests"] += 1
            test_case_result["error"] = str(e)
            print(f"❌ {test_case['name']} - 异常: {e}")
        
        test_case_result["end_time"] = datetime.now().isoformat()
        test_results["test_cases"].append(test_case_result)
    
    test_results["end_time"] = datetime.now().isoformat()
    
    return test_results


def generate_test_report(test_results: Dict[str, Any], environment_info: Dict[str, Any]) -> str:
    """生成测试报告"""
    print("📄 生成测试报告...")
    
    report_dir = project_root / "tests" / "e2e" / "v0_2_0" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = report_dir / f"e2e_test_report_{timestamp}.json"
    
    # 计算总体统计
    total_duration = sum(tc["duration"] for tc in test_results["test_cases"])
    pass_rate = (test_results["passed_tests"] / test_results["total_tests"]) * 100
    
    report_data = {
        "report_info": {
            "title": "v0.2.0 Agent自然语言交互功能E2E测试报告",
            "version": "0.2.0",
            "generated_at": datetime.now().isoformat(),
            "total_duration": round(total_duration, 2)
        },
        "environment": environment_info,
        "summary": {
            "total_tests": test_results["total_tests"],
            "passed_tests": test_results["passed_tests"],
            "failed_tests": test_results["failed_tests"],
            "pass_rate": round(pass_rate, 2),
            "start_time": test_results["start_time"],
            "end_time": test_results["end_time"]
        },
        "test_cases": test_results["test_cases"],
        "recommendations": []
    }
    
    # 添加建议
    if pass_rate == 100:
        report_data["recommendations"].append("所有测试通过，可以进入下一阶段")
    elif pass_rate >= 80:
        report_data["recommendations"].append("测试通过率良好，需要修复失败用例")
    else:
        report_data["recommendations"].append("测试通过率较低，需要重点修复")
    
    # 保存报告
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)
    
    # 生成简明的控制台报告
    console_report = f"""
🎯 E2E测试执行完成

📊 测试统计:
   总测试数: {test_results['total_tests']}
   通过数: {test_results['passed_tests']}
   失败数: {test_results['failed_tests']}
   通过率: {pass_rate:.1f}%
   总耗时: {total_duration:.2f}秒

💡 建议:
   {chr(10).join(report_data['recommendations'])}

📁 详细报告: {report_file}
"""
    
    print(console_report)
    return str(report_file)


def cleanup_environment() -> None:
    """清理测试环境"""
    print("🧹 清理测试环境...")
    
    # 清理测试数据
    try:
        result = subprocess.run([
            "uv", "run", "python", "tests/e2e/v0_2_0/generate_test_data.py", "--action", "clean"
        ], cwd=project_root, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ 测试环境清理完成")
        else:
            print(f"⚠️ 测试环境清理警告: {result.stderr}")
    except Exception as e:
        print(f"⚠️ 测试环境清理异常: {e}")


def main():
    """主函数"""
    print("=" * 60)
    print("🤖 v0.2.0 Agent自然语言交互功能E2E测试")
    print("=" * 60)
    
    overall_start_time = time.time()
    
    try:
        # 1. 环境检查
        environment_info = check_environment()
        
        if environment_info["issues"]:
            print("❌ 环境检查发现问题:")
            for issue in environment_info["issues"]:
                print(f"   - {issue}")
            
            # 尝试自动修复
            if not environment_info["test_data_ready"]:
                print("\n🔄 尝试自动准备测试数据...")
                if not prepare_test_data():
                    print("❌ 测试数据准备失败，退出测试")
                    return 1
        
        # 2. 执行测试
        test_results = run_e2e_tests()
        
        # 3. 生成报告
        report_file = generate_test_report(test_results, environment_info)
        
        # 4. 环境清理
        cleanup_environment()
        
        overall_duration = time.time() - overall_start_time
        print(f"\n🎉 E2E测试流程完成，总耗时: {overall_duration:.2f}秒")
        
        # 返回退出码
        if test_results["passed_tests"] == test_results["total_tests"]:
            print("✅ 所有测试通过")
            return 0
        else:
            print("⚠️ 有测试失败，请查看详细报告")
            return 1
            
    except KeyboardInterrupt:
        print("\n⏹️ 测试被用户中断")
        cleanup_environment()
        return 130
    except Exception as e:
        print(f"\n💥 测试执行异常: {e}")
        cleanup_environment()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)