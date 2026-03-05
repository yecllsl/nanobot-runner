# Parquet存储管理器
# 管理跑步数据的Parquet文件读写

from pathlib import Path
from typing import Any, Dict, List, Optional

import polars as pl


class StorageManager:
    """Parquet存储管理器，管理跑步数据的存储"""

    def __init__(self, data_dir: Optional[Path] = None) -> None:
        """
        初始化存储管理器

        Args:
            data_dir: 数据目录路径，不指定则使用默认目录

        Raises:
            OSError: 当无法创建数据目录时
        """
        self.data_dir = data_dir or Path.home() / ".nanobot-runner" / "data"
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise OSError(f"无法创建数据目录 {self.data_dir}: {e}") from e

    def save_to_parquet(self, dataframe: pl.DataFrame, year: int) -> bool:
        """
        保存数据到Parquet文件（按年份分片）

        Args:
            dataframe: Polars DataFrame数据
            year: 年份

        Returns:
            bool: 保存是否成功

        Raises:
            ValueError: 当数据框为空或年份无效时
        """
        if dataframe.is_empty():
            raise ValueError("数据框不能为空")

        if year < 2000 or year > 2100:
            raise ValueError("年份必须在2000-2100范围内")

        try:
            filename = f"activities_{year}.parquet"
            filepath = self.data_dir / filename

            if filepath.exists():
                existing_df = pl.read_parquet(filepath)
                combined_df = pl.concat([existing_df, dataframe])
                combined_df.write_parquet(filepath, compression="snappy")
            else:
                dataframe.write_parquet(filepath, compression="snappy")

            return True
        except Exception as e:
            raise RuntimeError(f"保存Parquet文件失败: {e}") from e

    def read_parquet(self, years: Optional[List[int]] = None) -> pl.LazyFrame:
        """
        使用LazyFrame读取Parquet数据（优化查询性能）

        Args:
            years: 要读取的年份列表，None表示读取所有年份

        Returns:
            pl.LazyFrame: 延迟加载的DataFrame

        Raises:
            FileNotFoundError: 当数据文件不存在时
        """
        try:
            if years:
                parquet_files = []
                for year in years:
                    filename = f"activities_{year}.parquet"
                    filepath = self.data_dir / filename
                    if filepath.exists():
                        parquet_files.append(filepath)

                if not parquet_files:
                    return pl.LazyFrame()

                return pl.concat([pl.scan_parquet(f) for f in parquet_files])
            else:
                parquet_files = list(self.data_dir.glob("activities_*.parquet"))
                if not parquet_files:
                    return pl.LazyFrame()

                return pl.concat([pl.scan_parquet(f) for f in parquet_files])
        except Exception as e:
            raise RuntimeError(f"读取Parquet数据失败: {e}") from e

    def read_activities(self, year: Optional[int] = None) -> pl.DataFrame:
        """
        读取跑步活动数据

        Args:
            year: 年份，不指定则读取所有年份数据

        Returns:
            pl.DataFrame: 跑步活动数据

        Raises:
            FileNotFoundError: 当数据文件不存在时
        """
        try:
            if year:
                filename = f"activities_{year}.parquet"
                filepath = self.data_dir / filename
                if not filepath.exists():
                    return pl.DataFrame()
                return pl.read_parquet(filepath)
            else:
                # 读取所有年份数据
                parquet_files = list(self.data_dir.glob("activities_*.parquet"))
                if not parquet_files:
                    return pl.DataFrame()

                dataframes = []
                for filepath in parquet_files:
                    df = pl.read_parquet(filepath)
                    dataframes.append(df)

                if dataframes:
                    return pl.concat(dataframes)
                else:
                    return pl.DataFrame()
        except Exception as e:
            raise RuntimeError(f"读取活动数据失败: {e}") from e

    def get_available_years(self) -> List[int]:
        """
        获取可用的数据年份

        Returns:
            List[int]: 可用年份列表
        """
        try:
            parquet_files = list(self.data_dir.glob("activities_*.parquet"))
            years = []
            for filepath in parquet_files:
                try:
                    year_str = filepath.stem.split("_")[1]
                    years.append(int(year_str))
                except (IndexError, ValueError):
                    continue

            return sorted(years)
        except Exception as e:
            raise RuntimeError(f"获取可用年份失败: {e}") from e

    def get_data_summary(self) -> Dict[str, Any]:
        """
        获取数据存储摘要信息

        Returns:
            Dict[str, Any]: 数据摘要信息
        """
        try:
            years = self.get_available_years()
            total_records = 0
            total_size_bytes = 0

            for year in years:
                filename = f"activities_{year}.parquet"
                filepath = self.data_dir / filename
                if filepath.exists():
                    df = pl.read_parquet(filepath)
                    total_records += df.height
                    total_size_bytes += filepath.stat().st_size

            return {
                "available_years": years,
                "total_records": total_records,
                "total_size_mb": round(total_size_bytes / (1024 * 1024), 2),
                "data_directory": str(self.data_dir),
            }
        except Exception as e:
            raise RuntimeError(f"获取数据摘要失败: {e}") from e

    def delete_year_data(self, year: int) -> bool:
        """
        删除指定年份的数据

        Args:
            year: 要删除的年份

        Returns:
            bool: 删除是否成功

        Raises:
            ValueError: 当年份无效时
        """
        if year < 2000 or year > 2100:
            raise ValueError("年份必须在2000-2100范围内")

        try:
            filename = f"activities_{year}.parquet"
            filepath = self.data_dir / filename

            if filepath.exists():
                filepath.unlink()
                return True
            else:
                return False
        except Exception as e:
            raise RuntimeError(f"删除年份数据失败: {e}") from e

    def get_stats(self) -> Dict[str, Any]:
        """
        获取存储统计信息

        Returns:
            dict: 统计信息
        """
        try:
            years = self.get_available_years()
            total_records = 0
            
            for year in years:
                df = self.read_activities(year)
                total_records += df.height

            time_range = {}
            if years:
                df = self.read_activities()
                if not df.is_empty():
                    timestamps = df["timestamp"]
                    time_range = {
                        "start": str(timestamps.min()),
                        "end": str(timestamps.max())
                    }

            return {
                "total_records": total_records,
                "years": years,
                "time_range": time_range
            }
        except Exception as e:
            return {"total_records": 0, "years": [], "time_range": {}, "error": str(e)}

    def query_activities(self, years: Optional[List[int]] = None, 
                        days: Optional[int] = None,
                        min_distance: Optional[float] = None,
                        min_heart_rate: Optional[int] = None) -> pl.DataFrame:
        """
        查询跑步活动数据（支持过滤）

        Args:
            years: 要查询的年份列表，None表示查询所有年份
            days: 查询最近N天的数据，优先级高于years
            min_distance: 最小距离过滤（米）
            min_heart_rate: 最小心率过滤

        Returns:
            pl.DataFrame: 查询结果
        """
        lf = self.read_parquet(years)

        if days is not None:
            from datetime import datetime, timedelta
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            start_str = start_date.strftime("%Y-%m-%d")
            end_str = end_date.strftime("%Y-%m-%d")

            lf = lf.filter(pl.col("timestamp") >= start_str).filter(pl.col("timestamp") <= end_str)

        if min_distance is not None:
            lf = lf.filter(pl.col("total_distance") >= min_distance)

        if min_heart_rate is not None:
            lf = lf.filter(pl.col("avg_heart_rate") >= min_heart_rate)

        return lf.collect()
