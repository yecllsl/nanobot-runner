from src.core.config import ConfigManager
from src.core.env_manager import EnvManager
from src.core.logger import get_logger
from src.core.validate.models import (
    ConnectivityResult,
    ErrorLevel,
    ValidationError,
    ValidationReport,
)

logger = get_logger(__name__)


class ConfigValidator:
    """配置验证器

    验证配置文件的完整性、正确性和有效性。
    """

    def __init__(
        self,
        config: ConfigManager,
        env_manager: EnvManager | None = None,
    ) -> None:
        """初始化配置验证器

        Args:
            config: 配置管理器
            env_manager: 环境变量管理器（可选）
        """
        self.config = config
        self.env_manager = env_manager or EnvManager()

    def validate_all(self) -> ValidationReport:
        """执行全部验证

        Returns:
            ValidationReport: 验证报告
        """
        import time

        start = time.time()

        all_errors: list[ValidationError] = []
        all_warnings: list[ValidationError] = []
        all_infos: list[ValidationError] = []

        format_errors = self.validate_format()
        all_errors.extend(format_errors)

        completeness_errors = self.validate_completeness()
        all_errors.extend(
            [e for e in completeness_errors if e.level == ErrorLevel.ERROR]
        )
        all_warnings.extend(
            [e for e in completeness_errors if e.level == ErrorLevel.WARNING]
        )

        validity_errors = self.validate_validity()
        all_errors.extend([e for e in validity_errors if e.level == ErrorLevel.ERROR])
        all_warnings.extend(
            [e for e in validity_errors if e.level == ErrorLevel.WARNING]
        )

        consistency_errors = self.validate_consistency()
        all_warnings.extend(consistency_errors)

        elapsed = time.time() - start

        return ValidationReport(
            is_valid=len(all_errors) == 0,
            errors=all_errors,
            warnings=all_warnings,
            infos=all_infos,
            summary={
                "total_errors": len(all_errors),
                "total_warnings": len(all_warnings),
                "format_errors": len(format_errors),
                "completeness_issues": len(completeness_errors),
                "validity_issues": len(validity_errors),
                "consistency_issues": len(consistency_errors),
            },
            elapsed_time=elapsed,
        )

    def validate_format(self) -> list[ValidationError]:
        """验证配置文件格式

        Returns:
            list[ValidationError]: 格式错误列表
        """
        errors: list[ValidationError] = []

        config_file = self.config.config_file
        if not config_file.exists():
            errors.append(
                ValidationError(
                    level=ErrorLevel.ERROR,
                    field="config_file",
                    message=f"配置文件不存在: {config_file}",
                    suggestion="运行 nanobotrun system init 初始化配置",
                )
            )
            return errors

        try:
            import json

            with open(config_file, encoding="utf-8") as f:
                config_data = json.load(f)

            if not isinstance(config_data, dict):
                errors.append(
                    ValidationError(
                        level=ErrorLevel.ERROR,
                        field="config_file",
                        message="配置文件格式错误：根元素必须是对象",
                        suggestion="检查 config.json 格式",
                    )
                )

        except json.JSONDecodeError as e:
            errors.append(
                ValidationError(
                    level=ErrorLevel.ERROR,
                    field="config_file",
                    message=f"JSON 格式错误: {e}",
                    suggestion="检查 config.json 的 JSON 语法",
                )
            )
        except OSError as e:
            errors.append(
                ValidationError(
                    level=ErrorLevel.ERROR,
                    field="config_file",
                    message=f"文件读取失败: {e}",
                    suggestion="检查文件权限",
                )
            )

        return errors

    def validate_completeness(self) -> list[ValidationError]:
        """验证配置完整性

        Returns:
            list[ValidationError]: 完整性错误列表
        """
        errors: list[ValidationError] = []

        try:
            config_data = self.config.load_config()
        except Exception:
            return errors

        required_fields = {
            "version": "版本号",
            "data_dir": "数据目录",
        }

        for field_name, display_name in required_fields.items():
            if field_name not in config_data or not config_data[field_name]:
                errors.append(
                    ValidationError(
                        level=ErrorLevel.ERROR,
                        field=field_name,
                        message=f"缺少必填配置项: {display_name}",
                        suggestion=f"在 config.json 中添加 {field_name} 配置",
                    )
                )

        optional_fields = {
            "llm_provider": "LLM Provider",
            "llm_model": "LLM Model",
        }

        for field_name, display_name in optional_fields.items():
            if field_name not in config_data or not config_data[field_name]:
                errors.append(
                    ValidationError(
                        level=ErrorLevel.WARNING,
                        field=field_name,
                        message=f"可选配置项未设置: {display_name}",
                        suggestion=f"建议在 config.json 中添加 {field_name} 配置以启用 Agent 功能",
                    )
                )

        return errors

    def validate_validity(self) -> list[ValidationError]:
        """验证配置有效性

        Returns:
            list[ValidationError]: 有效性错误列表
        """
        errors: list[ValidationError] = []

        try:
            config_data = self.config.load_config()
        except Exception:
            return errors

        import re
        from pathlib import Path

        if "version" in config_data:
            version = str(config_data["version"])
            if not re.match(r"^\d+\.\d+\.\d+$", version):
                errors.append(
                    ValidationError(
                        level=ErrorLevel.ERROR,
                        field="version",
                        message=f"版本号格式错误: {version}",
                        suggestion="版本号应为 x.y.z 格式",
                    )
                )

        if "data_dir" in config_data:
            data_path = Path(config_data["data_dir"])
            if data_path.exists() and not data_path.is_dir():
                errors.append(
                    ValidationError(
                        level=ErrorLevel.ERROR,
                        field="data_dir",
                        message=f"数据路径不是目录: {data_path}",
                        suggestion="请修改 data_dir 为有效的目录路径",
                    )
                )

        return errors

    def validate_consistency(self) -> list[ValidationError]:
        """验证配置一致性

        Returns:
            list[ValidationError]: 一致性错误列表
        """
        warnings: list[ValidationError] = []

        inconsistencies = self.config.validate_config_consistency()

        for item in inconsistencies:
            warnings.append(
                ValidationError(
                    level=ErrorLevel.WARNING,
                    field=item["field"],
                    message=(
                        f"配置不一致: 环境变量 {item['env_value']} "
                        f"与配置文件 {item['file_value']} 冲突"
                    ),
                    suggestion="环境变量优先级高于配置文件，确认是否为预期行为",
                )
            )

        return warnings

    def test_api_connectivity(self, provider: str | None = None) -> ConnectivityResult:
        """测试 API 连通性

        Args:
            provider: LLM Provider 名称（可选）

        Returns:
            ConnectivityResult: 连通性测试结果
        """
        import time

        try:
            config_data = self.config.load_config()
        except Exception:
            return ConnectivityResult(
                provider=provider or "unknown",
                is_connected=False,
                error_message="无法加载配置",
            )

        target_provider = provider or config_data.get("llm_provider", "openai")
        api_key = self.env_manager.get_env("NANOBOT_LLM_API_KEY") or config_data.get(
            "llm_api_key", ""
        )

        if not api_key:
            return ConnectivityResult(
                provider=target_provider,
                is_connected=False,
                error_message="API Key 未配置",
            )

        start = time.time()

        try:
            if target_provider == "openai":
                return self._test_openai_connectivity(api_key, time.time() - start)
            else:
                return ConnectivityResult(
                    provider=target_provider,
                    is_connected=True,
                    response_time=time.time() - start,
                )
        except Exception as e:
            return ConnectivityResult(
                provider=target_provider,
                is_connected=False,
                response_time=time.time() - start,
                error_message=str(e),
            )

    @staticmethod
    def _test_openai_connectivity(api_key: str, elapsed: float) -> ConnectivityResult:
        """测试 OpenAI API 连通性

        Args:
            api_key: API Key
            elapsed: 已消耗时间

        Returns:
            ConnectivityResult: 连通性测试结果
        """
        import time

        try:
            import urllib.request

            req = urllib.request.Request(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            start = time.time()
            with urllib.request.urlopen(req, timeout=10) as resp:  # nosec: B310
                _ = resp.read()
            return ConnectivityResult(
                provider="openai",
                is_connected=True,
                response_time=time.time() - start,
            )
        except Exception as e:
            return ConnectivityResult(
                provider="openai",
                is_connected=False,
                response_time=time.time() - elapsed,
                error_message=str(e),
            )
