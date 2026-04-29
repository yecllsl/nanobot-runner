import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

from src.core.base.logger import get_logger

logger = get_logger(__name__)


@dataclass
class VerificationReport:
    """校验报告"""

    success: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    checked_files: int = 0
    elapsed_time: float = 0.0


class VerifyManager:
    """数据完整性校验管理器

    提供文件和配置的完整性校验功能，支持 Parquet 文件校验。
    """

    def verify_files(self, files: list[Path]) -> VerificationReport:
        """校验文件完整性

        Args:
            files: 待校验的文件路径列表

        Returns:
            VerificationReport: 校验报告
        """
        errors: list[str] = []
        warnings: list[str] = []
        checked = 0

        for file_path in files:
            if not file_path.exists():
                errors.append(f"文件不存在: {file_path}")
                continue

            if file_path.stat().st_size == 0:
                warnings.append(f"文件为空: {file_path}")
                checked += 1
                continue

            if file_path.suffix == ".parquet":
                parquet_errors = self._verify_parquet_file(file_path)
                if parquet_errors:
                    errors.extend(parquet_errors)
                checked += 1
            elif file_path.suffix == ".json":
                json_errors = self._verify_json_file(file_path)
                if json_errors:
                    errors.extend(json_errors)
                checked += 1
            else:
                checked += 1

        return VerificationReport(
            success=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            checked_files=checked,
        )

    def verify_config(self, config: dict) -> VerificationReport:
        """校验配置完整性

        Args:
            config: 配置字典

        Returns:
            VerificationReport: 校验报告
        """
        errors: list[str] = []
        warnings: list[str] = []

        required_keys = ["version", "data_dir"]
        for key in required_keys:
            if key not in config:
                errors.append(f"缺少必填配置项: {key}")
            elif not config[key]:
                errors.append(f"配置项不能为空: {key}")

        if "data_dir" in config and config["data_dir"]:
            data_path = Path(config["data_dir"])
            if not data_path.exists():
                warnings.append(f"数据目录不存在: {data_path}")

        if "version" in config and config["version"]:
            import re

            if not re.match(r"^\d+\.\d+\.\d+$", str(config["version"])):
                errors.append(f"版本号格式错误: {config['version']}")

        return VerificationReport(
            success=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            checked_files=1,
        )

    def generate_report(
        self,
        files: list[Path] | None = None,
        config: dict | None = None,
    ) -> VerificationReport:
        """生成综合校验报告

        Args:
            files: 待校验的文件路径列表（可选）
            config: 配置字典（可选）

        Returns:
            VerificationReport: 综合校验报告
        """
        all_errors: list[str] = []
        all_warnings: list[str] = []
        total_checked = 0

        if files:
            file_report = self.verify_files(files)
            all_errors.extend(file_report.errors)
            all_warnings.extend(file_report.warnings)
            total_checked += file_report.checked_files

        if config:
            config_report = self.verify_config(config)
            all_errors.extend(config_report.errors)
            all_warnings.extend(config_report.warnings)
            total_checked += config_report.checked_files

        return VerificationReport(
            success=len(all_errors) == 0,
            errors=all_errors,
            warnings=all_warnings,
            checked_files=total_checked,
        )

    @staticmethod
    def compute_file_hash(file_path: Path) -> str:
        """计算文件哈希值

        Args:
            file_path: 文件路径

        Returns:
            str: SHA256哈希值
        """
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    @staticmethod
    def _verify_parquet_file(file_path: Path) -> list[str]:
        """校验 Parquet 文件

        Args:
            file_path: Parquet 文件路径

        Returns:
            list[str]: 错误列表
        """
        errors: list[str] = []
        try:
            import pyarrow.parquet as pq

            parquet_file = pq.read_metadata(file_path)
            if parquet_file.num_rows == 0:
                errors.append(f"Parquet 文件无数据行: {file_path}")
        except ImportError:
            try:
                import polars as pl

                pl.scan_parquet(str(file_path)).collect()
            except Exception as e:
                errors.append(f"Parquet 文件损坏: {file_path} - {e}")
        except Exception as e:
            errors.append(f"Parquet 文件损坏: {file_path} - {e}")

        return errors

    @staticmethod
    def _verify_json_file(file_path: Path) -> list[str]:
        """校验 JSON 文件

        Args:
            file_path: JSON 文件路径

        Returns:
            list[str]: 错误列表
        """
        errors: list[str] = []
        try:
            with open(file_path, encoding="utf-8") as f:
                json.load(f)
        except json.JSONDecodeError as e:
            errors.append(f"JSON 文件格式错误: {file_path} - {e}")
        except OSError as e:
            errors.append(f"JSON 文件读取失败: {file_path} - {e}")

        return errors
