#!/usr/bin/env python3
"""
RunFlowAgent 全量测试执行脚本
一键执行所有测试：单元测试 → 集成测试 → E2E测试 → 性能测试

执行方式：
- 在Trae IDE终端中执行: python tests/scripts/run_all_tests.py
- 支持参数控制测试范围
"""

import subprocess
import sys
import time
import argparse
from pathlib import Path
from datetime import datetime


def run_command(cmd, description, timeout=300):
    """执行命令并处理结果"""
    print(f"\n{'='*60}")
    print(f"🚀 开始执行: {description}")
    print(f"💻 命令: {cmd}")
    print(f"⏰ 超时: {timeout}秒")
    print(f"📅 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=timeout,
            cwd=Path(__file__).parent.parent.parent  # 项目根目录
        )
        
        elapsed_time = time.time() - start_time
        
        print(f"✅ 执行完成!")
        print(f"⏱️  耗时: {elapsed_time:.2f}秒")
        print(f"📊 退出码: {result.returncode}")
        
        if result.returncode == 0:
            print("🎉 测试通过!")
            return True, result.stdout
        else:
            print("❌ 测试失败!")
            print(f"错误输出:\n{result.stderr}")
            return False, result.stderr
            
    except subprocess.TimeoutExpired:
        elapsed_time = time.time() - start_time
        print(f"⏰ 命令执行超时 ({timeout}秒)")
        print(f"⏱️  已运行: {elapsed_time:.2f}秒")
        return False, "命令执行超时"
    
    except Exception as e:
        print(f"💥 命令执行异常: {e}")
        return False, str(e)


def run_unit_tests():
    """执行单元测试"""
    cmd = "python -m pytest tests/unit/ -v --tb=short"
    return run_command(cmd, "单元测试", timeout=180)


def run_integration_tests():
    """执行集成测试"""
    cmd = "python -m pytest tests/integration/ -v --tb=short"
    return run_command(cmd, "集成测试", timeout=300)


def run_e2e_tests():
    """执行端到端测试"""
    # 先执行用户旅程测试
    success1, output1 = run_command(
        "python tests/e2e/test_user_journey.py",
        "E2E用户旅程测试",
        timeout=600
    )
    
    # 再执行性能测试
    success2, output2 = run_command(
        "python tests/e2e/test_performance.py", 
        "E2E性能测试",
        timeout=600
    )
    
    return success1 and success2, f"用户旅程: {'通过' if success1 else '失败'}, 性能测试: {'通过' if success2 else '失败'}"


def run_coverage_tests():
    """执行覆盖率测试"""
    cmd = "python -m pytest tests/ -v --cov=src --cov-report=html --cov-report=term"
    return run_command(cmd, "覆盖率测试", timeout=300)


def run_specific_module(module_name):
    """执行特定模块测试"""
    if module_name == "cli":
        cmd = "python -m pytest tests/unit/test_cli.py tests/integration/module/test_cli_flow.py -v"
    elif module_name == "analytics":
        cmd = "python -m pytest tests/unit/test_analytics.py tests/integration/module/test_analytics_flow.py -v"
    elif module_name == "import":
        cmd = "python -m pytest tests/unit/test_importer.py tests/integration/module/test_import_flow.py -v"
    else:
        return False, f"未知模块: {module_name}"
    
    return run_command(cmd, f"{module_name}模块测试", timeout=180)


def generate_test_report(results, total_time):
    """生成测试报告"""
    print(f"\n{'='*60}")
    print("📊 测试执行报告")
    print(f"{'='*60}")
    
    passed = sum(1 for result in results.values() if result[0])
    total = len(results)
    
    print(f"📅 报告时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"⏱️  总耗时: {total_time:.2f}秒")
    print(f"📈 通过率: {passed}/{total} ({passed/total*100:.1f}%)")
    
    print(f"\n📋 详细结果:")
    for test_name, (success, output) in results.items():
        status = "✅ 通过" if success else "❌ 失败"
        print(f"   {status} {test_name}")
    
    # 保存报告到文件
    report_file = Path("tests/reports/test_execution_report.txt")
    report_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("RunFlowAgent 测试执行报告\n")
        f.write("="*50 + "\n")
        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"总耗时: {total_time:.2f}秒\n")
        f.write(f"通过率: {passed}/{total} ({passed/total*100:.1f}%)\n\n")
        
        f.write("详细结果:\n")
        for test_name, (success, output) in results.items():
            status = "通过" if success else "失败"
            f.write(f"- {test_name}: {status}\n")
    
    print(f"\n📄 报告已保存: {report_file}")
    
    return passed == total


def main():
    """主函数"""
    
    parser = argparse.ArgumentParser(description='RunFlowAgent 全量测试执行脚本')
    parser.add_argument('--unit', action='store_true', help='仅执行单元测试')
    parser.add_argument('--integration', action='store_true', help='仅执行集成测试')
    parser.add_argument('--e2e', action='store_true', help='仅执行E2E测试')
    parser.add_argument('--coverage', action='store_true', help='执行覆盖率测试')
    parser.add_argument('--module', type=str, help='执行特定模块测试 (cli|analytics|import)')
    parser.add_argument('--generate-data', action='store_true', help='生成测试数据')
    
    args = parser.parse_args()
    
    print("="*60)
    print("RunFlowAgent 测试执行工具")
    print("="*60)
    
    start_time = time.time()
    results = {}
    
    try:
        # 生成测试数据（如果需要）
        if args.generate_data:
            print("\n📊 生成测试数据...")
            success, output = run_command(
                "python tests/scripts/generate_test_data.py",
                "测试数据生成",
                timeout=120
            )
            if not success:
                print("❌ 测试数据生成失败，继续执行测试...")
        
        # 执行特定模块测试
        if args.module:
            success, output = run_specific_module(args.module)
            results[args.module] = (success, output)
        
        # 执行单元测试
        elif args.unit:
            success, output = run_unit_tests()
            results["单元测试"] = (success, output)
        
        # 执行集成测试
        elif args.integration:
            success, output = run_integration_tests()
            results["集成测试"] = (success, output)
        
        # 执行E2E测试
        elif args.e2e:
            success, output = run_e2e_tests()
            results["E2E测试"] = (success, output)
        
        # 执行覆盖率测试
        elif args.coverage:
            success, output = run_coverage_tests()
            results["覆盖率测试"] = (success, output)
        
        # 执行全量测试（默认）
        else:
            print("\n🎯 开始执行全量测试...")
            
            # 单元测试
            success, output = run_unit_tests()
            results["单元测试"] = (success, output)
            
            # 集成测试
            success, output = run_integration_tests()
            results["集成测试"] = (success, output)
            
            # E2E测试
            success, output = run_e2e_tests()
            results["E2E测试"] = (success, output)
            
            # 覆盖率测试（可选）
            if args.coverage:
                success, output = run_coverage_tests()
                results["覆盖率测试"] = (success, output)
        
        total_time = time.time() - start_time
        
        # 生成测试报告
        all_passed = generate_test_report(results, total_time)
        
        # 最终结果
        print(f"\n{'='*60}")
        if all_passed:
            print("🎉 所有测试通过! 代码质量优秀!")
            print("✅ 可以安全进入发布环节")
        else:
            print("⚠️  部分测试失败，请检查代码质量")
            print("❌ 不建议直接发布，请先修复问题")
        print(f"{'='*60}")
        
        return 0 if all_passed else 1
        
    except KeyboardInterrupt:
        print("\n⏹️  测试执行被用户中断")
        return 1
    except Exception as e:
        print(f"\n💥 测试执行异常: {e}")
        return 1


if __name__ == "__main__":
    exit(main())