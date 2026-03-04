# FIT文件解析器
# 基于fitparse库解析.fit格式文件

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import fitparse
import polars as pl


class FitParser:
    """FIT文件解析器"""

    def __init__(self) -> None:
        """初始化解析器"""
        pass

    def parse_file(self, filepath: Path) -> Optional[pl.DataFrame]:
        """
        解析单个FIT文件

        Args:
            filepath: FIT文件路径

        Returns:
            pl.DataFrame: 解析后的数据框，失败返回None

        Raises:
            FileNotFoundError: 当文件不存在时
            ValueError: 当文件格式无效时
        """
        if not filepath.exists():
            raise FileNotFoundError(f"文件不存在: {filepath}")

        if filepath.suffix.lower() != ".fit":
            raise ValueError(f"文件格式无效，必须是.fit文件: {filepath}")

        try:
            fit_file = fitparse.FitFile(str(filepath))

            records = []
            session_data: Dict[str, Any] = {}

            # 解析记录数据
            for record in fit_file.get_messages("record"):
                record_data: Dict[str, Any] = {}
                for data in record:
                    record_data[data.name] = data.value
                records.append(record_data)

            # 解析会话数据
            for session in fit_file.get_messages("session"):
                for data in session:
                    session_data[data.name] = data.value

            if not records:
                print(f"警告: 文件 {filepath} 没有记录数据")
                return None

            # 转换为Polars DataFrame
            df = pl.DataFrame(records)

            # 添加会话数据作为元数据
            if session_data:
                df = self._add_session_metadata(df, session_data)

            # 添加文件信息
            df = df.with_columns(
                pl.lit(str(filepath)).alias("source_file"),
                pl.lit(datetime.now()).alias("import_timestamp"),
            )

            return df
        except Exception as e:
            raise RuntimeError(f"解析FIT文件失败: {e}") from e

    def _add_session_metadata(
        self, df: pl.DataFrame, session_data: Dict[str, Any]
    ) -> pl.DataFrame:
        """
        添加会话元数据到数据框

        Args:
            df: 原始数据框
            session_data: 会话数据字典

        Returns:
            pl.DataFrame: 添加了元数据的数据框
        """
        try:
            # 添加会话元数据作为常量列
            for key, value in session_data.items():
                if value is not None:
                    df = df.with_columns(pl.lit(value).alias(f"session_{key}"))

            return df
        except Exception as e:
            raise RuntimeError(f"添加会话元数据失败: {e}") from e

    def parse_directory(self, directory: Path) -> pl.DataFrame:
        """
        解析目录中的所有FIT文件

        Args:
            directory: 目录路径

        Returns:
            pl.DataFrame: 合并后的数据框

        Raises:
            FileNotFoundError: 当目录不存在时
        """
        if not directory.exists():
            raise FileNotFoundError(f"目录不存在: {directory}")

        if not directory.is_dir():
            raise ValueError(f"路径不是目录: {directory}")

        try:
            fit_files = list(directory.glob("*.fit"))
            if not fit_files:
                print(f"警告: 目录 {directory} 中没有找到.fit文件")
                return pl.DataFrame()

            dataframes = []
            for filepath in fit_files:
                try:
                    df = self.parse_file(filepath)
                    if df is not None and not df.is_empty():
                        dataframes.append(df)
                except Exception as e:
                    print(f"警告: 解析文件 {filepath} 失败: {e}")
                    continue

            if dataframes:
                return pl.concat(dataframes)
            else:
                return pl.DataFrame()
        except Exception as e:
            raise RuntimeError(f"解析目录失败: {e}") from e

    def validate_fit_file(self, filepath: Path) -> Dict[str, Any]:
        """
        验证FIT文件的有效性

        Args:
            filepath: FIT文件路径

        Returns:
            Dict[str, Any]: 验证结果
        """
        try:
            if not filepath.exists():
                return {"valid": False, "error": "文件不存在"}

            if filepath.suffix.lower() != ".fit":
                return {"valid": False, "error": "文件格式无效"}

            # 尝试解析文件
            df = self.parse_file(filepath)

            if df is None:
                return {"valid": False, "error": "文件解析失败"}

            # 检查数据质量
            validation_result = self._validate_data_quality(df)

            return {
                "valid": True,
                "record_count": df.height,
                "columns": df.columns,
                "data_quality": validation_result,
            }
        except Exception as e:
            return {"valid": False, "error": str(e)}

    def _validate_data_quality(self, df: pl.DataFrame) -> Dict[str, Any]:
        """
        验证数据质量

        Args:
            df: 数据框

        Returns:
            Dict[str, Any]: 数据质量评估结果
        """
        try:
            required_columns = ["timestamp", "distance", "heart_rate"]
            missing_columns = [col for col in required_columns if col not in df.columns]

            # 检查数据完整性
            null_counts = {}
            for col in df.columns:
                null_count = df[col].null_count()
                null_counts[col] = null_count

            # 检查时间序列连续性
            time_gaps = 0
            if "timestamp" in df.columns:
                timestamps = df["timestamp"].sort()
                if timestamps.len() > 1:
                    time_diffs = timestamps.diff().drop_nulls()
                    if time_diffs.len() > 0:
                        avg_gap = time_diffs.mean()
                        time_gaps = time_diffs.filter(
                            pl.col("timestamp") > avg_gap * 2
                        ).len()

            return {
                "missing_required_columns": missing_columns,
                "null_counts": null_counts,
                "time_gaps": time_gaps,
                "total_records": df.height,
                "data_quality_score": self._calculate_quality_score(
                    df, missing_columns, null_counts
                ),
            }
        except Exception as e:
            raise RuntimeError(f"数据质量验证失败: {e}") from e

    def _calculate_quality_score(
        self, df: pl.DataFrame, missing_columns: list, null_counts: dict
    ) -> float:
        """
        计算数据质量分数

        Args:
            df: 数据框
            missing_columns: 缺失的必要列
            null_counts: 各列的空值数量

        Returns:
            float: 质量分数（0-100）
        """
        try:
            # 基础分数
            score = 100.0

            # 缺失必要列扣分
            score -= len(missing_columns) * 20

            # 空值过多扣分
            total_cells = df.height * len(df.columns)
            if total_cells > 0:
                total_nulls = sum(null_counts.values())
                null_ratio = total_nulls / total_cells
                score -= null_ratio * 50

            # 确保分数在合理范围内
            return max(0.0, min(100.0, score))
        except Exception:
            return 0.0
