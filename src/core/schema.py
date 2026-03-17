# Parquet Schema定义模块
# 定义统一的数据结构规范，确保数据一致性

from datetime import datetime
from typing import Any, Dict, List

import polars as pl

from src.core.logger import get_logger

logger = get_logger(__name__)


class ParquetSchema:
    """Parquet数据Schema定义"""

    # 核心活动元数据字段
    ACTIVITY_METADATA = {
        "activity_id": pl.String,
        "timestamp": pl.Datetime,
        "source_file": pl.String,
        "filename": pl.String,
        "serial_number": pl.String,
        "time_created": pl.Datetime,
        "total_distance": pl.Float64,
        "total_timer_time": pl.Float64,
        "total_calories": pl.Int64,
        "avg_heart_rate": pl.Int64,
        "max_heart_rate": pl.Int64,
        "record_count": pl.Int64,
    }

    # 秒级记录字段
    RECORD_FIELDS = {
        "timestamp": pl.Datetime,
        "position_lat": pl.Float64,
        "position_long": pl.Float64,
        "distance": pl.Float64,
        "duration": pl.Float64,
        "heart_rate": pl.Int32,
        "cadence": pl.Int32,
        "speed": pl.Float64,
        "power": pl.Int32,
        "altitude": pl.Float64,
        "temperature": pl.Int32,
    }

    # 统一Schema：活动元数据 + 秒级记录
    UNIFIED_SCHEMA = {**ACTIVITY_METADATA, **RECORD_FIELDS}

    # 必填字段（不能为null）
    REQUIRED_FIELDS = {
        "activity_id",
        "timestamp",
        "source_file",
        "filename",
        "total_distance",
        "total_timer_time",
    }

    # 默认值映射
    DEFAULT_VALUES = {
        "serial_number": "UNKNOWN",
        "time_created": datetime(1970, 1, 1),
        "total_distance": 0.0,
        "total_timer_time": 0.0,
        "total_calories": 0,
        "avg_heart_rate": None,
        "max_heart_rate": None,
        "record_count": 0,
        "position_lat": None,
        "position_long": None,
        "cadence": None,
        "speed": None,
        "power": None,
        "altitude": None,
        "temperature": None,
    }

    @classmethod
    def get_schema(cls) -> Dict[str, pl.DataType]:
        """获取完整Schema定义"""
        return {k: v for k, v in cls.UNIFIED_SCHEMA.items()}

    @classmethod
    def get_required_fields(cls) -> set:
        """获取必填字段集合"""
        return cls.REQUIRED_FIELDS.copy()

    @classmethod
    def get_default_values(cls) -> Dict[str, Any]:
        """获取默认值映射"""
        return cls.DEFAULT_VALUES.copy()

    @classmethod
    def validate_dataframe(cls, df: pl.DataFrame) -> dict:
        """
        验证DataFrame是否符合Schema

        Args:
            df: 待验证的DataFrame

        Returns:
            dict: 验证结果字典，包含'valid'和'messages'键
        """
        schema = cls.get_schema()
        messages = []
        is_valid = True

        # 只检查必填字段
        for col_name in cls.REQUIRED_FIELDS:
            if col_name not in df.columns:
                msg = f"缺少必填字段：{col_name}"
                messages.append(msg)
                logger.warning(msg)
                is_valid = False
            elif df.schema[col_name] != schema[col_name]:
                msg = f"字段 {col_name} 类型不匹配：期望 {schema[col_name]}, 实际 {df.schema[col_name]}"
                messages.append(msg)
                logger.warning(msg)
                is_valid = False

        extra_fields = [col for col in df.columns if col not in schema]
        if extra_fields:
            msg = f"存在未定义的字段: {', '.join(extra_fields)}"
            messages.append(msg)
            logger.info(msg)

        return {"valid": is_valid, "messages": messages}

    @classmethod
    def normalize_dataframe(cls, df: pl.DataFrame) -> pl.DataFrame:
        """
        标准化DataFrame以符合Schema

        Args:
            df: 待标准化的DataFrame

        Returns:
            pl.DataFrame: 标准化后的DataFrame
        """
        schema = cls.get_schema()
        default_values = cls.get_default_values()

        # 如果是空DataFrame，直接返回
        if df.height == 0:
            return df

        # 添加缺失的列
        for col_name, col_type in schema.items():
            if col_name not in df.columns:
                default_value = default_values.get(col_name)
                df = df.with_columns(
                    pl.lit(default_value).alias(col_name).cast(col_type)
                )

        # 转换现有列类型
        for col_name, col_type in schema.items():
            if col_name in df.columns:
                try:
                    df = df.with_columns(pl.col(col_name).cast(col_type))
                except Exception:
                    pass

        return df


def create_activity_id(filename: str, timestamp: datetime) -> str:
    """
    生成活动唯一ID

    Args:
        filename: 源文件名
        timestamp: 活动开始时间

    Returns:
        str: 活动ID
    """
    timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
    return f"{filename}_{timestamp_str}"


def create_schema_dataframe(
    metadata: Dict[str, Any], records: List[Dict[str, Any]]
) -> pl.DataFrame:
    """
    创建符合Schema的DataFrame

    Args:
        metadata: 活动元数据
        records: 秒级记录列表

    Returns:
        pl.DataFrame: 符合Schema的DataFrame
    """
    schema = ParquetSchema.get_schema()
    default_values = ParquetSchema.get_default_values()

    # 生成活动ID
    activity_id = create_activity_id(
        metadata.get("filename", "unknown"),
        metadata.get("time_created", datetime.now()),
    )

    # 构建记录列表
    normalized_records = []
    for record in records:
        normalized_record = default_values.copy()
        normalized_record.update(record)
        normalized_record["activity_id"] = activity_id
        normalized_record.update(
            {
                "serial_number": metadata.get(
                    "serial_number", default_values["serial_number"]
                ),
                "time_created": metadata.get(
                    "time_created", default_values["time_created"]
                ),
                "total_distance": metadata.get(
                    "total_distance", default_values["total_distance"]
                ),
                "total_timer_time": metadata.get(
                    "total_timer_time", default_values["total_timer_time"]
                ),
                "total_calories": metadata.get(
                    "total_calories", default_values["total_calories"]
                ),
                "avg_heart_rate": metadata.get(
                    "avg_heart_rate", default_values["avg_heart_rate"]
                ),
                "max_heart_rate": metadata.get(
                    "max_heart_rate", default_values["max_heart_rate"]
                ),
                "record_count": metadata.get(
                    "record_count", default_values["record_count"]
                ),
            }
        )
        normalized_records.append(normalized_record)

    # 创建DataFrame
    if not normalized_records:
        df = pl.DataFrame()
    else:
        df = pl.DataFrame(normalized_records)

    # 应用Schema转换
    df = ParquetSchema.normalize_dataframe(df)

    return df
