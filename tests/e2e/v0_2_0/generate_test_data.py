#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v0.2.0 Agent自然语言交互功能E2E测试数据生成脚本

本脚本用于生成E2E测试所需的模拟跑步数据，包括：
- 基础跑步统计数据
- VDOT趋势数据
- 心率漂移分析数据
- 训练负荷数据

执行方式：
uv run python tests/e2e/v0.2.0/generate_test_data.py

作者: 测试工程师
创建日期: 2026-03-06
版本: 1.0
"""

import json
import os
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import polars as pl

from tests.e2e.v0_2_0.test_utils import DataGenerator


def generate_basic_test_data(record_count: int = 1000) -> pl.DataFrame:
    """
    生成基础测试数据

    Args:
        record_count: 记录数量

    Returns:
        Polars DataFrame
    """
    print(f"生成基础测试数据，记录数: {record_count}")

    generator = DataGenerator()
    test_data = generator.generate_running_data(record_count)

    # 转换为Polars DataFrame
    df = pl.DataFrame(test_data)

    # 验证数据完整性
    required_columns = [
        "activity_id",
        "timestamp",
        "source_file",
        "filename",
        "total_distance",
        "total_timer_time",
        "avg_heart_rate",
    ]

    for col in required_columns:
        if col not in df.columns:
            raise ValueError(f"缺失必需列: {col}")

    print(f"基础测试数据生成完成，包含 {len(df)} 条记录")
    return df


def generate_vdot_trend_data(record_count: int = 200) -> pl.DataFrame:
    """
    生成VDOT趋势测试数据

    Args:
        record_count: 记录数量

    Returns:
        Polars DataFrame
    """
    print(f"生成VDOT趋势测试数据，记录数: {record_count}")

    generator = DataGenerator()
    test_data = generator.generate_vdot_test_data(record_count)

    # 转换为Polars DataFrame
    df = pl.DataFrame(test_data)

    # 确保包含VDOT相关字段
    if "vdot_estimate" not in df.columns:
        # 添加VDOT估算字段
        df = df.with_columns(
            [
                pl.lit(50.0).alias("vdot_estimate"),
                pl.lit(0.9).alias("hr_drift_factor"),
                pl.lit(0.1).alias("hr_drift_correlation"),
            ]
        )

    print(f"✅ VDOT趋势测试数据生成完成，包含 {len(df)} 条记录")
    return df


def generate_performance_test_data(record_count: int = 10000) -> pl.DataFrame:
    """
    生成性能测试数据（大数据量）

    Args:
        record_count: 记录数量

    Returns:
        Polars DataFrame
    """
    print(f"生成性能测试数据，记录数: {record_count}")

    generator = DataGenerator()
    test_data = generator.generate_running_data(record_count)

    # 转换为Polars DataFrame
    df = pl.DataFrame(test_data)

    print(f"✅ 性能测试数据生成完成，包含 {len(df)} 条记录")
    return df


def save_data_to_parquet(df: pl.DataFrame, file_path: Path, year: int = None) -> None:
    """
    保存数据到Parquet文件

    Args:
        df: 数据DataFrame
        file_path: 文件路径
        year: 年份（用于分片）
    """
    if year:
        # 按年份过滤数据
        df_filtered = df.filter(pl.col("timestamp").dt.year() == year)
    else:
        df_filtered = df

    # 保存到Parquet文件
    df_filtered.write_parquet(file_path, compression="snappy")
    print(f"✅ 数据已保存到: {file_path} ({len(df_filtered)} 条记录)")


def create_test_data_index(data_dir: Path, file_info: List[Dict[str, Any]]) -> None:
    """
    创建测试数据索引文件

    Args:
        data_dir: 数据目录
        file_info: 文件信息列表
    """
    index_data = {
        "version": "0.2.0",
        "created_at": datetime.now().isoformat(),
        "files": file_info,
        "total_records": sum(info["record_count"] for info in file_info),
        "data_range": {
            "start_date": min(info["start_date"] for info in file_info),
            "end_date": max(info["end_date"] for info in file_info),
        },
    }

    index_file = data_dir / "test_index.json"
    with open(index_file, "w", encoding="utf-8") as f:
        json.dump(index_data, f, indent=2, ensure_ascii=False)

    print(f"✅ 测试数据索引已创建: {index_file}")


def setup_e2e_test_environment() -> Path:
    """
    设置E2E测试环境

    Returns:
        测试数据目录路径
    """
    # 创建测试数据目录
    # 在CI环境中使用临时目录，在生产环境中使用用户主目录
    if os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"):
        base_dir = Path("/tmp") / ".nanobot-runner"
    else:
        base_dir = Path.home() / ".nanobot-runner"
    test_data_dir = base_dir / "test_data"
    test_data_dir.mkdir(parents=True, exist_ok=True)

    # 清理现有测试数据
    for file in test_data_dir.glob("*.parquet"):
        file.unlink()

    index_file = test_data_dir / "test_index.json"
    if index_file.exists():
        index_file.unlink()

    print(f"测试数据目录: {test_data_dir}")
    return test_data_dir


def generate_comprehensive_test_dataset() -> Dict[str, Any]:
    """
    生成完整的测试数据集

    Returns:
        数据集信息
    """
    print("=== 开始生成完整的E2E测试数据集 ===")

    # 设置测试环境
    test_data_dir = setup_e2e_test_environment()
    file_info = []

    # 1. 生成基础测试数据（覆盖多个年份）
    print("\n1. 生成基础测试数据...")
    base_df = generate_basic_test_data(1000)

    # 按年份分片保存
    years = [2024, 2025, 2026]
    for year in years:
        file_path = test_data_dir / f"activities_{year}.parquet"
        save_data_to_parquet(base_df, file_path, year)

        # 收集文件信息
        year_df = base_df.filter(pl.col("timestamp").dt.year() == year)
        if len(year_df) > 0:
            file_info.append(
                {
                    "filename": file_path.name,
                    "year": year,
                    "record_count": len(year_df),
                    "start_date": year_df["timestamp"].min().strftime("%Y-%m-%d"),
                    "end_date": year_df["timestamp"].max().strftime("%Y-%m-%d"),
                }
            )

    # 2. 生成VDOT趋势测试数据
    print("\n2. 生成VDOT趋势测试数据...")
    vdot_df = generate_vdot_trend_data(200)
    vdot_file = test_data_dir / "activities_vdot.parquet"
    save_data_to_parquet(vdot_df, vdot_file)

    file_info.append(
        {
            "filename": vdot_file.name,
            "year": "vdot",
            "record_count": len(vdot_df),
            "start_date": vdot_df["timestamp"].min().strftime("%Y-%m-%d"),
            "end_date": vdot_df["timestamp"].max().strftime("%Y-%m-%d"),
        }
    )

    # 3. 生成性能测试数据
    print("\n3. 生成性能测试数据...")
    perf_df = generate_performance_test_data(10000)
    perf_file = test_data_dir / "activities_perf.parquet"
    save_data_to_parquet(perf_df, perf_file)

    file_info.append(
        {
            "filename": perf_file.name,
            "year": "performance",
            "record_count": len(perf_df),
            "start_date": perf_df["timestamp"].min().strftime("%Y-%m-%d"),
            "end_date": perf_df["timestamp"].max().strftime("%Y-%m-%d"),
        }
    )

    # 4. 创建测试数据索引
    print("\n4. 创建测试数据索引...")
    create_test_data_index(test_data_dir, file_info)

    # 统计信息
    total_records = sum(info["record_count"] for info in file_info)

    print(f"\n=== E2E测试数据集生成完成 ===")
    print(f"总记录数: {total_records}")
    print(f"文件数量: {len(file_info)}")
    print(f"数据目录: {test_data_dir}")

    return {
        "data_dir": test_data_dir,
        "file_info": file_info,
        "total_records": total_records,
    }


def create_sample_fit_files() -> Path:
    """
    创建示例FIT文件（用于导入测试）

    Returns:
        FIT文件目录路径
    """
    print("创建示例FIT文件...")

    generator = DataGenerator()
    temp_dir = tempfile.mkdtemp(prefix="nanobot_fit_")
    fit_dir = generator.create_sample_fit_files(temp_dir, 10)

    print(f"✅ 示例FIT文件已创建: {fit_dir}")
    return Path(fit_dir)


def validate_test_data() -> bool:
    """
    验证测试数据完整性

    Returns:
        验证结果
    """
    print("验证测试数据完整性...")

    # 在CI环境中使用临时目录，在生产环境中使用用户主目录
    if os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"):
        base_dir = Path("/tmp") / ".nanobot-runner"
    else:
        base_dir = Path.home() / ".nanobot-runner"
    test_data_dir = base_dir / "test_data"

    if not test_data_dir.exists():
        print("❌ 测试数据目录不存在")
        return False

    parquet_files = list(test_data_dir.glob("*.parquet"))
    if not parquet_files:
        print("❌ 未找到Parquet数据文件")
        return False

    # 验证每个文件
    for file_path in parquet_files:
        try:
            df = pl.read_parquet(file_path)
            required_columns = [
                "activity_id",
                "timestamp",
                "total_distance",
                "total_timer_time",
                "avg_heart_rate",
            ]

            for col in required_columns:
                if col not in df.columns:
                    print(f"❌ 文件 {file_path.name} 缺失列: {col}")
                    return False

            print(f"✅ 文件 {file_path.name} 验证通过 ({len(df)} 条记录)")

        except Exception as e:
            print(f"❌ 文件 {file_path.name} 验证失败: {e}")
            return False

    # 验证索引文件
    index_file = test_data_dir / "test_index.json"
    if index_file.exists():
        try:
            with open(index_file, "r", encoding="utf-8") as f:
                index_data = json.load(f)
            print(f"✅ 索引文件验证通过")
        except Exception as e:
            print(f"❌ 索引文件验证失败: {e}")
            return False

    print("✅ 所有测试数据验证通过")
    return True


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="E2E测试数据生成脚本")
    parser.add_argument(
        "--action",
        choices=["generate", "validate", "clean"],
        default="generate",
        help="执行动作",
    )
    parser.add_argument("--record-count", type=int, default=1000, help="基础数据记录数量")

    args = parser.parse_args()

    if args.action == "generate":
        # 生成测试数据
        result = generate_comprehensive_test_dataset()

        # 创建示例FIT文件
        fit_dir = create_sample_fit_files()

        print(f"\n🎯 E2E测试数据准备完成")
        print(f"数据目录: {result['data_dir']}")
        print(f"FIT文件目录: {fit_dir}")
        print(f"总记录数: {result['total_records']}")

    elif args.action == "validate":
        # 验证测试数据
        if validate_test_data():
            print("🎯 测试数据验证通过")
        else:
            print("❌ 测试数据验证失败")
            sys.exit(1)

    elif args.action == "clean":
        # 清理测试数据
        # 在CI环境中使用临时目录，在生产环境中使用用户主目录
        if os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"):
            base_dir = Path("/tmp") / ".nanobot-runner"
        else:
            base_dir = Path.home() / ".nanobot-runner"
        test_data_dir = base_dir / "test_data"
        if test_data_dir.exists():
            import shutil

            shutil.rmtree(test_data_dir)
            print(f"✅ 测试数据已清理: {test_data_dir}")
        else:
            print("ℹ️ 测试数据目录不存在，无需清理")


if __name__ == "__main__":
    main()
