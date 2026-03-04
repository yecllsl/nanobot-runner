#!/usr/bin/env python3
"""
RunFlowAgent 测试数据生成脚本
生成用于E2E测试的模拟FIT文件和测试数据

执行方式：
- python tests/scripts/generate_test_data.py
- 在Trae IDE终端中直接执行
"""

import json
import random
import tempfile
from datetime import datetime, timedelta
from pathlib import Path


def create_mock_fit_file(filepath: Path, activity_data: dict):
    """
    创建模拟FIT文件

    Args:
        filepath: 文件路径
        activity_data: 活动数据字典
    """
    # 创建模拟FIT文件内容（简化版）
    content = f"""# Mock FIT File - {activity_data['filename']}
# Generated for testing purposes

[File Header]
Type: activity
Manufacturer: Garmin
Product: Forerunner 945
Serial Number: {activity_data.get('serial_number', 'TEST12345')}
Time Created: {activity_data.get('time_created', '2024-01-01T08:00:00Z')}
Number of Records: {activity_data.get('record_count', 100)}

[Activity]
Sport: running
Total Timer Time: {activity_data.get('total_timer_time', 1800)}
Total Distance: {activity_data.get('total_distance', 5000)}
Total Calories: {activity_data.get('total_calories', 300)}
Avg Heart Rate: {activity_data.get('avg_heart_rate', 150)}
Max Heart Rate: {activity_data.get('max_heart_rate', 170)}
Avg Speed: {activity_data.get('avg_speed', 2.78)}
Max Speed: {activity_data.get('max_speed', 3.5)}
Total Ascent: {activity_data.get('total_ascent', 50)}
Total Descent: {activity_data.get('total_descent', 45)}

[Records]
# Sample record data (simplified)
"""

    # 添加示例记录数据
    for i in range(min(10, activity_data.get("record_count", 10))):  # 只添加前10条记录作为示例
        timestamp = (
            datetime.fromisoformat(activity_data["time_created"].replace("Z", ""))
            + timedelta(seconds=i * 10)
        ).isoformat()
        content += f"{timestamp}, {150 + i}, {2.7 + i*0.1}, {50 + i}\n"

    filepath.write_text(content)
    print(f"创建模拟FIT文件: {filepath}")


def generate_test_dataset():
    """生成完整的测试数据集"""

    # 创建测试数据目录
    test_data_dir = Path("tests/data/fixtures")
    test_data_dir.mkdir(parents=True, exist_ok=True)

    print("🚀 开始生成测试数据集...")

    # 生成不同类型的跑步活动数据
    activity_types = [
        {
            "type": "easy_run",
            "distance_range": (3000, 8000),
            "duration_range": (1200, 2400),
            "hr_range": (130, 150),
        },
        {
            "type": "tempo_run",
            "distance_range": (5000, 10000),
            "duration_range": (1500, 3000),
            "hr_range": (150, 170),
        },
        {
            "type": "long_run",
            "distance_range": (15000, 30000),
            "duration_range": (3600, 7200),
            "hr_range": (140, 160),
        },
        {
            "type": "interval",
            "distance_range": (4000, 8000),
            "duration_range": (1200, 1800),
            "hr_range": (160, 190),
        },
    ]

    # 生成多个测试文件
    test_files = []
    base_date = datetime(2024, 1, 1)

    for i, activity_type in enumerate(activity_types):
        for day in range(7):  # 每类活动生成7天的数据
            activity_date = base_date + timedelta(days=day + i * 7)

            activity_data = {
                "filename": f"{activity_type['type']}_{activity_date.strftime('%Y%m%d')}.fit",
                "serial_number": f"TEST{1000 + i}",
                "time_created": activity_date.isoformat() + "Z",
                "total_distance": random.randint(*activity_type["distance_range"]),
                "total_timer_time": random.randint(*activity_type["duration_range"]),
                "avg_heart_rate": random.randint(*activity_type["hr_range"]),
                "max_heart_rate": random.randint(
                    activity_type["hr_range"][1], activity_type["hr_range"][1] + 20
                ),
                "total_calories": random.randint(200, 800),
                "record_count": random.randint(50, 200),
            }

            filepath = test_data_dir / activity_data["filename"]
            create_mock_fit_file(filepath, activity_data)
            test_files.append(activity_data)

    # 生成特殊场景测试文件
    special_cases = [
        {"filename": "empty_file.fit", "description": "空文件测试", "content": ""},
        {
            "filename": "corrupted_file.fit",
            "description": "损坏文件测试",
            "content": "Invalid FIT file content that should cause parsing errors",
        },
        {
            "filename": "large_file.fit",
            "description": "大文件测试",
            "record_count": 1000,
            "total_distance": 42195,  # 马拉松距离
            "total_timer_time": 7200,  # 2小时
        },
    ]

    for case in special_cases:
        filepath = test_data_dir / case["filename"]
        if "content" in case:
            filepath.write_text(case["content"])
        else:
            # 为特殊场景文件添加必要的字段
            case["serial_number"] = "TEST9999"
            case["time_created"] = datetime.now().isoformat() + "Z"
            create_mock_fit_file(filepath, case)
        test_files.append(case)

    # 保存测试文件元数据
    metadata_file = test_data_dir / "test_files_metadata.json"
    metadata_file.write_text(json.dumps(test_files, indent=2, ensure_ascii=False))

    print(f"✅ 测试数据集生成完成!")
    print(f"📁 数据目录: {test_data_dir}")
    print(f"📊 生成文件数量: {len(test_files)}")
    print(f"📋 元数据文件: {metadata_file}")

    return test_data_dir


def generate_validation_data():
    """生成验证数据（预期结果）"""

    validation_dir = Path("tests/data/validation")
    validation_dir.mkdir(parents=True, exist_ok=True)

    print("\n📊 生成验证数据...")

    # 预期分析结果
    expected_results = {
        "vdot_calculations": [
            {"distance_m": 5000, "time_s": 1800, "expected_vdot": 45.2},
            {"distance_m": 10000, "time_s": 2400, "expected_vdot": 56.8},
            {"distance_m": 21097, "time_s": 4500, "expected_vdot": 50.1},
            {"distance_m": 42195, "time_s": 9000, "expected_vdot": 55.3},
        ],
        "tss_calculations": [
            {"avg_hr": 140, "duration_s": 1800, "ftp": 200, "expected_tss": 45.6},
            {"avg_hr": 160, "duration_s": 3600, "ftp": 200, "expected_tss": 128.3},
            {"avg_hr": 180, "duration_s": 1200, "ftp": 200, "expected_tss": 52.1},
        ],
        "import_statistics": {
            "expected_file_count": 31,  # 4类×7天 + 3个特殊文件
            "expected_duplicate_rate": 0.0,
            "expected_success_rate": 0.9,  # 允许10%的失败（如损坏文件）
        },
    }

    validation_file = validation_dir / "expected_results.json"
    validation_file.write_text(json.dumps(expected_results, indent=2))

    print(f"✅ 验证数据生成完成: {validation_file}")

    return validation_dir


def generate_benchmark_data():
    """生成基准测试数据"""

    benchmark_dir = Path("tests/data/validation")
    benchmark_dir.mkdir(parents=True, exist_ok=True)

    print("\n⚡ 生成基准测试数据...")

    # 性能基准数据
    benchmark_data = {
        "performance_targets": {
            "cli_startup_time": 1.0,  # CLI启动时间 < 1秒
            "import_processing_time": 10.0,  # 导入处理时间 < 10秒
            "query_response_time": 3.0,  # 查询响应时间 < 3秒
            "memory_usage_limit": 500.0,  # 内存使用 < 500MB
            "compression_ratio": 70.0,  # 压缩率 > 70%
        },
        "scalability_targets": {
            "max_activities": 100000,  # 支持10万条活动记录
            "max_file_size": 100,  # 支持100MB单个文件
            "concurrent_operations": 5,  # 支持5个并发操作
        },
    }

    benchmark_file = benchmark_dir / "benchmark_data.json"
    benchmark_file.write_text(json.dumps(benchmark_data, indent=2))

    print(f"✅ 基准测试数据生成完成: {benchmark_file}")

    return benchmark_dir


def main():
    """主函数"""

    print("=" * 60)
    print("RunFlowAgent 测试数据生成工具")
    print("=" * 60)

    try:
        # 生成测试数据集
        test_data_dir = generate_test_dataset()

        # 生成验证数据
        validation_dir = generate_validation_data()

        # 生成基准测试数据
        benchmark_dir = generate_benchmark_data()

        print("\n" + "=" * 60)
        print("🎉 所有测试数据生成完成!")
        print("📁 测试数据目录结构:")
        print(f"   ├── {test_data_dir.relative_to(Path('.'))}/")
        print(f"   ├── {validation_dir.relative_to(Path('.'))}/")
        print(f"   └── {benchmark_dir.relative_to(Path('.'))}/")
        print("\n🚀 现在可以执行E2E测试:")
        print("   python tests/e2e/test_user_journey.py")
        print("   python tests/e2e/test_performance.py")
        print("=" * 60)

    except Exception as e:
        print(f"❌ 数据生成失败: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
