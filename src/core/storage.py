# Parquet存储管理器
# 管理跑步数据的Parquet文件读写

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import polars as pl

from src.core.exceptions import StorageError, ValidationError
from src.core.logger import get_logger

logger = get_logger(__name__)


class StorageManager:
    """Parquet存储管理器，管理跑步数据的存储"""

    def __init__(self, data_dir: Optional[Path] = None) -> None:
        self.data_dir = data_dir or Path.home() / ".nanobot-runner" / "data"
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"存储管理器初始化，数据目录: {self.data_dir}")
        except OSError as e:
            logger.error(f"无法创建数据目录 {self.data_dir}: {e}")
            raise StorageError(
                message=f"无法创建数据目录 {self.data_dir}: {e}",
                recovery_suggestion="请检查用户目录权限或手动创建数据目录",
            ) from e

    def _convert_to_parquet_compatible(self, df: pl.DataFrame) -> pl.DataFrame:
        if df.is_empty():
            return df

        for col_name in df.columns:
            col_type = df.schema[col_name]
            if isinstance(col_type, pl.Object):
                df = df.with_columns(pl.col(col_name).cast(pl.String).alias(col_name))
                logger.debug(f"转换列类型: {col_name} Object -> String")

        return df

    def _align_dataframes(
        self, df1: pl.DataFrame, df2: pl.DataFrame
    ) -> tuple[pl.DataFrame, pl.DataFrame]:
        all_columns = sorted(set(df1.columns) | set(df2.columns))

        for col in all_columns:
            if col not in df1.columns:
                df1 = df1.with_columns(pl.lit(None).alias(col))
            if col not in df2.columns:
                df2 = df2.with_columns(pl.lit(None).alias(col))

        schema1 = df1.schema
        schema2 = df2.schema

        for col in all_columns:
            type1 = schema1[col]
            type2 = schema2[col]

            if type1 == pl.Null and type2 != pl.Null:
                df1 = df1.with_columns(pl.col(col).cast(type2))
            elif type2 == pl.Null and type1 != pl.Null:
                df2 = df2.with_columns(pl.col(col).cast(type1))
            elif type1 != type2:
                if type1 in (pl.Float64, pl.Float32) or type2 in (
                    pl.Float64,
                    pl.Float32,
                ):
                    df1 = df1.with_columns(pl.col(col).cast(pl.Float64))
                    df2 = df2.with_columns(pl.col(col).cast(pl.Float64))
                elif type1.is_integer() and type2.is_integer():
                    df1 = df1.with_columns(pl.col(col).cast(pl.Int64))
                    df2 = df2.with_columns(pl.col(col).cast(pl.Int64))
                else:
                    df1 = df1.with_columns(pl.col(col).cast(pl.String))
                    df2 = df2.with_columns(pl.col(col).cast(pl.String))

        df1 = df1.select(all_columns)
        df2 = df2.select(all_columns)

        return df1, df2

    def _concat_with_schema_alignment(
        self, lazy_frames: List[pl.LazyFrame]
    ) -> pl.LazyFrame:
        if not lazy_frames:
            return pl.LazyFrame()

        if len(lazy_frames) == 1:
            return lazy_frames[0]

        try:
            schemas = [lf.collect_schema() for lf in lazy_frames]
            all_columns = sorted(set().union(*[set(s.names()) for s in schemas]))

            aligned_frames = []
            for lf, schema in zip(lazy_frames, schemas):
                missing_cols = set(all_columns) - set(schema.names())
                if missing_cols:
                    for col in missing_cols:
                        lf = lf.with_columns(pl.lit(None).alias(col))
                lf = lf.select(all_columns)
                aligned_frames.append(lf)

            return pl.concat(aligned_frames)
        except Exception as e:
            logger.warning(f"LazyFrame schema 对齐失败，尝试使用 DataFrame: {e}")
            dfs = [lf.collect() for lf in lazy_frames]
            if not dfs:
                return pl.LazyFrame()

            schemas = [df.schema for df in dfs]
            all_columns = sorted(set().union(*[set(s.keys()) for s in schemas]))

            aligned_dfs = []
            for df, schema in zip(dfs, schemas):
                missing_cols = set(all_columns) - set(schema.keys())
                if missing_cols:
                    for col in missing_cols:
                        df = df.with_columns(pl.lit(None).alias(col))
                df = df.select(all_columns)
                aligned_dfs.append(df)

            return pl.concat(aligned_dfs).lazy()

    def _read_parquet_with_schema_fix(self, filepath: Path) -> pl.LazyFrame:
        try:
            return pl.scan_parquet(filepath)
        except Exception as e:
            logger.warning(f"scan_parquet 失败，使用 read_parquet: {e}")
            df = pl.read_parquet(filepath)
            return df.lazy()

    def _read_and_concat_parquet_files(self, parquet_files: List[Path]) -> pl.LazyFrame:
        if not parquet_files:
            return pl.LazyFrame()

        dfs = []
        for filepath in parquet_files:
            try:
                df = self._read_parquet_file_with_schema_fix(filepath)
                if df is not None:
                    dfs.append(df)
            except Exception as e:
                logger.warning(f"读取文件失败 {filepath}: {e}")
                continue

        if not dfs:
            return pl.LazyFrame()

        if len(dfs) == 1:
            return dfs[0].lazy()

        all_schemas = {}
        for df in dfs:
            for col_name, col_type in df.schema.items():
                if col_name not in all_schemas:
                    all_schemas[col_name] = col_type
                elif col_type != pl.Null and all_schemas[col_name] == pl.Null:
                    all_schemas[col_name] = col_type

        all_columns = sorted(all_schemas.keys())

        aligned_dfs = []
        for df in dfs:
            df_schema = df.schema
            missing_cols = set(all_columns) - set(df_schema.keys())
            if missing_cols:
                for col in missing_cols:
                    target_type = all_schemas[col]
                    df = df.with_columns(pl.lit(None).cast(target_type).alias(col))
            df = df.select(all_columns)
            aligned_dfs.append(df)

        result = pl.concat(aligned_dfs)
        logger.debug(f"合并 {len(dfs)} 个文件，共 {result.height} 条记录")
        return result.lazy()

    def _read_parquet_file_with_schema_fix(
        self, filepath: Path
    ) -> Optional[pl.DataFrame]:
        try:
            return pl.read_parquet(filepath)
        except Exception as e:
            logger.warning(f"pl.read_parquet 失败，尝试使用 pyarrow: {e}")
            try:
                import pyarrow.parquet as pq

                table = pq.read_table(filepath)
                result = pl.from_arrow(table)
                if isinstance(result, pl.DataFrame):
                    logger.info(f"使用 pyarrow 成功读取文件: {filepath}")
                    return result
                else:
                    logger.error(f"pyarrow 返回非 DataFrame 类型")
                    return None
            except Exception as e2:
                logger.error(f"pyarrow 读取也失败: {e2}")
                return None

    def save_to_parquet(
        self, dataframe: pl.DataFrame, year: int, allow_empty: bool = False
    ) -> bool:
        if dataframe.is_empty():
            if allow_empty:
                return True
            logger.warning("尝试保存空数据框")
            raise ValidationError(
                message="数据框不能为空",
                recovery_suggestion="请确保导入了有效的活动数据",
            )

        if year < 2000 or year > 2100:
            logger.error(f"年份无效: {year}")
            raise ValidationError(
                message="年份必须在2000-2100范围内",
                recovery_suggestion="请检查数据中的时间戳字段",
            )

        try:
            dataframe = self._convert_to_parquet_compatible(dataframe)

            filename = f"activities_{year}.parquet"
            filepath = self.data_dir / filename

            if filepath.exists():
                existing_df = pl.read_parquet(filepath)
                existing_df = self._convert_to_parquet_compatible(existing_df)
                existing_df, dataframe = self._align_dataframes(existing_df, dataframe)

                combined_df = pl.concat([existing_df, dataframe])
                combined_df = combined_df.unique()

                combined_df.write_parquet(filepath, compression="snappy")
                new_records = combined_df.height - existing_df.height
                logger.info(f"追加数据到 {filename}, 新增 {new_records} 条记录")
            else:
                dataframe.write_parquet(filepath, compression="snappy")
                logger.info(f"创建新文件 {filename}, 写入 {dataframe.height} 条记录")

            return True
        except (ValidationError, StorageError):
            raise
        except Exception as e:
            logger.error(f"保存Parquet文件失败: {e}")
            raise StorageError(
                message=f"保存Parquet文件失败: {e}",
                recovery_suggestion="请检查磁盘空间和数据目录权限",
            ) from e

    def save_activities(self, dataframe: pl.DataFrame, year: int = None) -> dict:
        try:
            if year is None:
                if not dataframe.is_empty() and "timestamp" in dataframe.columns:
                    first_timestamp = dataframe["timestamp"][0]
                    if hasattr(first_timestamp, "year"):
                        year = first_timestamp.year
                    else:
                        year = datetime.now().year
                else:
                    year = datetime.now().year

            success = self.save_to_parquet(dataframe, year)
            logger.debug(f"保存活动数据成功: {len(dataframe)} 条记录, 年份: {year}")
            return {
                "success": success,
                "records_saved": len(dataframe) if not dataframe.is_empty() else 0,
                "year": year,
            }
        except (ValidationError, StorageError) as e:
            logger.error(f"保存活动数据失败: {e.message}")
            return {
                "success": False,
                "records_saved": 0,
                "error": e.message,
                "error_code": e.error_code,
                "recovery_suggestion": e.recovery_suggestion,
                "year": year if year else datetime.now().year,
            }
        except Exception as e:
            logger.error(f"保存活动数据失败: {e}")
            return {
                "success": False,
                "records_saved": 0,
                "error": str(e),
                "year": year if year else datetime.now().year,
            }

    def load_activities(self, year: Optional[int] = None) -> pl.DataFrame:
        return self.read_activities(year)

    def read_parquet(self, years: Optional[List[int]] = None) -> pl.LazyFrame:
        try:
            if years:
                parquet_files = []
                for year in years:
                    filename = f"activities_{year}.parquet"
                    filepath = self.data_dir / filename
                    if filepath.exists():
                        parquet_files.append(filepath)

                if not parquet_files:
                    logger.debug(f"未找到指定年份的数据文件: {years}")
                    return pl.LazyFrame()

                logger.debug(f"读取 {len(parquet_files)} 个数据文件")
                return self._read_and_concat_parquet_files(parquet_files)
            else:
                parquet_files = list(self.data_dir.glob("activities_*.parquet"))
                if not parquet_files:
                    logger.debug("未找到任何数据文件")
                    return pl.LazyFrame()

                logger.debug(f"读取全部 {len(parquet_files)} 个数据文件")
                return self._read_and_concat_parquet_files(parquet_files)
        except Exception as e:
            logger.error(f"读取Parquet数据失败: {e}")
            raise StorageError(
                message=f"读取Parquet数据失败: {e}",
                recovery_suggestion="请检查数据文件是否损坏，或尝试重新导入数据",
            ) from e

    def read_activities(self, year: Optional[int] = None) -> pl.DataFrame:
        try:
            if year:
                filename = f"activities_{year}.parquet"
                filepath = self.data_dir / filename
                if not filepath.exists():
                    logger.debug(f"数据文件不存在: {filename}")
                    return pl.DataFrame()
                df = pl.read_parquet(filepath)
                logger.debug(f"读取 {filename}: {df.height} 条记录")
                return df
            else:
                parquet_files = list(self.data_dir.glob("activities_*.parquet"))
                if not parquet_files:
                    logger.debug("未找到任何数据文件")
                    return pl.DataFrame()

                dataframes = []
                for filepath in parquet_files:
                    df = pl.read_parquet(filepath)
                    dataframes.append(df)

                if dataframes:
                    result = pl.concat(dataframes)
                    logger.debug(f"读取全部数据: {result.height} 条记录")
                    return result
                else:
                    return pl.DataFrame()
        except Exception as e:
            logger.error(f"读取活动数据失败: {e}")
            raise StorageError(
                message=f"读取活动数据失败: {e}",
                recovery_suggestion="请检查数据文件是否损坏，或尝试重新导入数据",
            ) from e

    def get_available_years(self) -> List[int]:
        try:
            parquet_files = list(self.data_dir.glob("activities_*.parquet"))
            years = []
            for filepath in parquet_files:
                try:
                    year_str = filepath.stem.split("_")[1]
                    years.append(int(year_str))
                except (IndexError, ValueError):
                    continue

            logger.debug(f"可用年份: {sorted(years)}")
            return sorted(years)
        except Exception as e:
            logger.error(f"获取可用年份失败: {e}")
            raise StorageError(
                message=f"获取可用年份失败: {e}",
                recovery_suggestion="请检查数据目录是否存在",
            ) from e

    def get_data_summary(self) -> Dict[str, Any]:
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

            logger.debug(
                f"数据摘要: {total_records} 条记录, {total_size_bytes / (1024 * 1024):.2f} MB"
            )
            return {
                "available_years": years,
                "total_records": total_records,
                "total_size_mb": round(total_size_bytes / (1024 * 1024), 2),
                "data_directory": str(self.data_dir),
            }
        except Exception as e:
            logger.error(f"获取数据摘要失败: {e}")
            raise StorageError(
                message=f"获取数据摘要失败: {e}",
                recovery_suggestion="请检查数据目录和文件权限",
            ) from e

    def delete_year_data(self, year: int) -> bool:
        if year < 2000 or year > 2100:
            logger.error(f"年份无效: {year}")
            raise ValidationError(
                message="年份必须在2000-2100范围内",
                recovery_suggestion="请输入有效的年份",
            )

        try:
            filename = f"activities_{year}.parquet"
            filepath = self.data_dir / filename

            if filepath.exists():
                filepath.unlink()
                logger.info(f"删除年份数据: {filename}")
                return True
            else:
                logger.debug(f"数据文件不存在，无需删除: {filename}")
                return False
        except Exception as e:
            logger.error(f"删除年份数据失败: {e}")
            raise StorageError(
                message=f"删除年份数据失败: {e}",
                recovery_suggestion="请检查文件权限",
            ) from e

    def get_stats(self) -> Dict[str, Any]:
        """
        获取存储统计信息（使用 LazyFrame 优化性能）

        Returns:
            dict: 统计信息
        """
        try:
            years = self.get_available_years()
            total_records = 0

            for year in years:
                filename = f"activities_{year}.parquet"
                filepath = self.data_dir / filename
                if filepath.exists():
                    # 使用 scan_parquet 获取记录数，避免加载全部数据
                    total_records += (
                        pl.scan_parquet(filepath).select(pl.len()).collect().item()
                    )

            time_range = {}
            if years:
                # 使用 LazyFrame 读取时间范围
                lf = self.read_parquet()
                # 检查 LazyFrame 是否有列（空 LazyFrame 没有列）
                if len(lf.collect_schema()) > 0:
                    # 使用 LazyFrame 计算时间范围
                    result = lf.select(
                        [
                            pl.col("timestamp").min().alias("start"),
                            pl.col("timestamp").max().alias("end"),
                        ]
                    ).collect()

                    if not result.is_empty():
                        time_range = {
                            "start": str(result["start"][0]),
                            "end": str(result["end"][0]),
                        }

            return {
                "total_records": total_records,
                "years": years,
                "time_range": time_range,
            }
        except Exception as e:
            return {"total_records": 0, "years": [], "time_range": {}, "error": str(e)}

    def query_activities(
        self,
        years: Optional[List[int]] = None,
        days: Optional[int] = None,
        min_distance: Optional[float] = None,
        min_heart_rate: Optional[int] = None,
    ) -> pl.DataFrame:
        """
        查询跑步活动数据（支持过滤）

        Args:
            years: 要查询的年份列表，None 表示查询所有年份
            days: 查询最近 N 天的数据，优先级高于 years
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

            lf = lf.filter(pl.col("timestamp") >= start_date).filter(
                pl.col("timestamp") <= end_date
            )

        if min_distance is not None:
            lf = lf.filter(pl.col("session_total_distance") >= min_distance)

        if min_heart_rate is not None:
            lf = lf.filter(pl.col("session_avg_heart_rate") >= min_heart_rate)

        return lf.collect()

    def query_by_date_range(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        按日期范围查询活动数据

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            List[Dict]: 活动数据列表
        """
        lf = self.read_parquet()

        if start_date is not None:
            lf = lf.filter(pl.col("timestamp") >= start_date)

        if end_date is not None:
            lf = lf.filter(pl.col("timestamp") <= end_date)

        df = lf.collect()
        return df.to_dicts()
