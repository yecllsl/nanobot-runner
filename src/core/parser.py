# FIT文件解析器
# 基于fitparse库解析.fit格式文件

from datetime import datetime
from pathlib import Path
from typing import Any

import fitparse
import polars as pl

from src.core.exceptions import ParseError, ValidationError
from src.core.logger import get_logger
from src.core.schema import ParquetSchema

logger = get_logger(__name__)

_original_parse_definition_message = fitparse.base.FitFile._parse_definition_message


def _patched_parse_definition_message(self, header) -> None:  # type: ignore[no-untyped-def]
    from fitparse.records import BASE_TYPE_BYTE, BASE_TYPES, FieldDefinition

    endian = ">" if self._read_struct("xB") else "<"
    global_mesg_num, num_fields = self._read_struct("HB", endian=endian)
    mesg_type = fitparse.profile.MESSAGE_TYPES.get(global_mesg_num)
    field_defs = []

    for _n in range(num_fields):
        field_def_num, field_size, base_type_num = self._read_struct(
            "3B", endian=endian
        )
        field = mesg_type.fields.get(field_def_num) if mesg_type else None
        base_type = BASE_TYPES.get(base_type_num, BASE_TYPE_BYTE)

        if (field_size % base_type.size) != 0:
            logger.debug(
                f"非标准字段大小: {field_def_num}, size={field_size}, "
                f"base_type={base_type.name}, expected_multiple={base_type.size}"
            )
            base_type = BASE_TYPE_BYTE
            field_size = field_size

        if field and field.components:
            for component in field.components:
                if component.accumulate:
                    accumulators = self._accumulators.setdefault(global_mesg_num, {})
                    accumulators[component.def_num] = 0

        field_defs.append(
            FieldDefinition(
                field=field,
                def_num=field_def_num,
                base_type=base_type,
                size=field_size,
            )
        )

    dev_field_defs = []
    if header.is_developer_data:
        num_dev_fields = self._read_struct("B", endian=endian)
        for _n in range(num_dev_fields):
            field_def_num, field_size, dev_data_index = self._read_struct(
                "3B", endian=endian
            )
            field = fitparse.records.get_dev_type(dev_data_index, field_def_num)
            dev_field_defs.append(
                fitparse.records.DevFieldDefinition(
                    field=field,
                    dev_data_index=dev_data_index,
                    def_num=field_def_num,
                    size=field_size,
                )
            )

    def_mesg = fitparse.records.DefinitionMessage(
        header=header,
        endian=endian,
        mesg_type=mesg_type,
        mesg_num=global_mesg_num,
        field_defs=field_defs,
        dev_field_defs=dev_field_defs,
    )
    self._local_mesgs[header.local_mesg_num] = def_mesg
    return def_mesg


fitparse.base.FitFile._parse_definition_message = _patched_parse_definition_message


class FitParser:
    """FIT文件解析器"""

    def __init__(self) -> None:
        logger.debug("FitParser 初始化")

    def parse_file(self, filepath: Path) -> pl.DataFrame | None:
        if not filepath.exists():
            logger.error(f"文件不存在: {filepath}")
            raise ValidationError(
                message=f"文件不存在: {filepath}",
                recovery_suggestion="请确认文件路径是否正确",
            )

        if filepath.suffix.lower() != ".fit":
            logger.error(f"文件格式无效: {filepath}")
            raise ValidationError(
                message=f"文件格式无效，必须是.fit文件: {filepath}",
                recovery_suggestion="请选择正确的FIT格式文件",
            )

        try:
            logger.debug(f"开始解析文件: {filepath}")
            fit_file = fitparse.FitFile(str(filepath))

            records = []
            session_data: dict[str, Any] = {}

            for record in fit_file.get_messages("record"):
                record_data: dict[str, Any] = {}
                for data in record:
                    record_data[data.name] = data.value
                records.append(record_data)

            for session in fit_file.get_messages("session"):
                for data in session:
                    session_data[data.name] = data.value

            if not records:
                logger.warning(f"文件无记录数据: {filepath}")
                return None

            df = pl.DataFrame(records)

            if session_data:
                df = self._add_session_metadata(df, session_data)

            df = df.with_columns(
                pl.lit(str(filepath)).alias("source_file"),
                pl.lit(datetime.now()).alias("import_timestamp"),
            )

            df = self._apply_schema_validation(df, filepath)

            logger.info(f"解析文件成功: {filepath}, 记录数: {df.height}")
            return df
        except (ValidationError, ParseError):
            raise
        except Exception as e:
            logger.error(f"解析FIT文件失败: {filepath}, 错误: {e}")
            raise ParseError(
                message=f"解析FIT文件失败: {e}",
                recovery_suggestion="请确认文件格式正确，或尝试重新导出FIT文件",
            ) from e

    def _add_session_metadata(
        self, df: pl.DataFrame, session_data: dict[str, Any]
    ) -> pl.DataFrame:
        try:
            for key, value in session_data.items():
                if value is not None:
                    df = df.with_columns(pl.lit(value).alias(f"session_{key}"))

            logger.debug(f"添加会话元数据: {len(session_data)} 个字段")
            return df
        except Exception as e:
            logger.error(f"添加会话元数据失败: {e}")
            raise ParseError(
                message=f"添加会话元数据失败: {e}",
                recovery_suggestion="请检查FIT文件数据结构",
            ) from e

    def _apply_schema_validation(
        self, df: pl.DataFrame, filepath: Path
    ) -> pl.DataFrame:
        """
        应用Schema校验和标准化

        Args:
            df: 原始DataFrame
            filepath: 文件路径（用于日志）

        Returns:
            pl.DataFrame: 标准化后的DataFrame
        """
        df = df.with_columns(
            pl.lit(filepath.stem).alias("filename"),
        )

        if "session_total_distance" not in df.columns:
            df = df.with_columns(pl.lit(0.0).alias("session_total_distance"))
        if "session_total_timer_time" not in df.columns:
            df = df.with_columns(pl.lit(0.0).alias("session_total_timer_time"))

        validation_result = ParquetSchema.validate_dataframe(df)

        if not validation_result["valid"]:
            logger.warning(f"Schema校验警告: {validation_result['messages']}")

        df = ParquetSchema.normalize_dataframe(df)
        logger.debug(f"Schema标准化完成: {filepath}")
        return df

    def parse_directory(self, directory: Path) -> pl.DataFrame:
        if not directory.exists():
            logger.error(f"目录不存在: {directory}")
            raise ValidationError(
                message=f"目录不存在: {directory}",
                recovery_suggestion="请确认目录路径是否正确",
            )

        if not directory.is_dir():
            logger.error(f"路径不是目录: {directory}")
            raise ValidationError(
                message=f"路径不是目录: {directory}",
                recovery_suggestion="请选择有效的目录路径",
            )

        try:
            fit_files = list(directory.glob("*.fit"))
            if not fit_files:
                logger.debug(f"目录中无FIT文件: {directory}")
                return pl.DataFrame()

            logger.info(f"开始解析目录: {directory}, 文件数: {len(fit_files)}")
            dataframes = []
            for filepath in fit_files:
                try:
                    df = self.parse_file(filepath)
                    if df is not None and not df.is_empty():
                        dataframes.append(df)
                except (ValidationError, ParseError):
                    continue

            if dataframes:
                result = pl.concat(dataframes)
                logger.info(f"目录解析完成: {result.height} 条记录")
                return result
            else:
                logger.warning(f"目录解析无有效数据: {directory}")
                return pl.DataFrame()
        except (ValidationError, ParseError):
            raise
        except Exception as e:
            logger.error(f"解析目录失败: {e}")
            raise ParseError(
                message=f"解析目录失败: {e}",
                recovery_suggestion="请检查目录权限和文件格式",
            ) from e

    def parse_file_metadata(self, filepath: Path) -> dict[str, Any]:
        try:
            if not filepath.exists():
                logger.error(f"文件不存在: {filepath}")
                raise ValidationError(
                    message=f"文件不存在: {filepath}",
                    recovery_suggestion="请确认文件路径是否正确",
                )

            if filepath.suffix.lower() != ".fit":
                logger.error(f"文件格式无效: {filepath}")
                raise ValidationError(
                    message=f"文件格式无效，必须是.fit文件: {filepath}",
                    recovery_suggestion="请选择正确的FIT格式文件",
                )

            fit_file = fitparse.FitFile(str(filepath))

            metadata: dict[str, Any] = {
                "filename": filepath.stem,
                "filepath": str(filepath),
            }

            for msg in fit_file.get_messages("file_id"):
                for data in msg:
                    metadata[data.name] = data.value

            logger.debug(f"解析文件元数据: {filepath}")
            return metadata

        except (ValidationError, ParseError):
            raise
        except Exception as e:
            logger.error(f"解析FIT文件元数据失败: {e}")
            raise ParseError(
                message=f"解析FIT文件元数据失败: {e}",
                recovery_suggestion="请确认文件格式正确",
            ) from e

    def validate_fit_file(self, filepath: Path) -> dict[str, Any]:
        try:
            if not filepath.exists():
                return {"valid": False, "error": "文件不存在"}

            if filepath.suffix.lower() != ".fit":
                return {"valid": False, "error": "文件格式无效"}

            try:
                fit_file = fitparse.FitFile(str(filepath))
                file_id_data = {}
                for msg in fit_file.get_messages("file_id"):
                    for data in msg:
                        file_id_data[data.name] = data.value
                logger.debug(f"验证文件有效: {filepath}")
                return {"valid": True, "file_id": file_id_data}
            except Exception as e:
                logger.warning(f"文件验证失败: {filepath}, 错误: {e}")
                return {"valid": False, "error": str(e)}
        except Exception as e:
            logger.error(f"验证文件异常: {filepath}, 错误: {e}")
            return {"valid": False, "error": str(e)}

    def _validate_data_quality(self, df: pl.DataFrame) -> dict[str, Any]:
        """
        验证数据质量

        Args:
            df: 数据框

        Returns:
            Dict[str, Any]: 数据质量评估结果

        Raises:
            ParseError: 当验证失败时
        """
        try:
            required_columns = ["timestamp", "distance", "heart_rate"]
            missing_columns = [col for col in required_columns if col not in df.columns]

            null_counts = {}
            for col in df.columns:
                null_count = df[col].null_count()
                null_counts[col] = null_count

            time_gaps = 0
            if "timestamp" in df.columns:
                timestamps = df["timestamp"].sort()
                if timestamps.len() > 1:
                    time_diffs = timestamps.diff().drop_nulls()
                    if time_diffs.len() > 0:
                        avg_gap = time_diffs.mean()
                        # time_diffs 是 Series，直接对 Series 进行过滤
                        # 使用 float 乘法避免类型问题
                        threshold = avg_gap * 2.0 if avg_gap is not None else 0.0  # type: ignore[operator]
                        time_gaps = time_diffs.filter(time_diffs > threshold).len()

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
            raise ParseError(
                message=f"数据质量验证失败: {e}",
                recovery_suggestion="请检查数据结构",
            ) from e

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
            score = 100.0

            score -= len(missing_columns) * 20

            total_cells = df.height * len(df.columns)
            if total_cells > 0:
                total_nulls = sum(null_counts.values())
                null_ratio = total_nulls / total_cells
                score -= null_ratio * 50

            return max(0.0, min(100.0, score))
        except Exception:
            return 0.0
