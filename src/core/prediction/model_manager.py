from __future__ import annotations

import contextlib
import json
import logging
from pathlib import Path
from typing import Any

from src.core.prediction.models import ModelManagementResult, ModelStatus

logger = logging.getLogger(__name__)


class ModelManager:
    """模型生命周期管理器

    管理ML模型的保存/加载/版本/回滚/增量学习
    """

    AUTO_UPDATE_MIN_SAMPLES = 50
    AUTO_UPDATE_MIN_DAYS = 30

    def __init__(self, models_dir: str | None = None) -> None:
        if models_dir is None:
            models_dir = str(Path.home() / ".nanobot-runner" / "models")
        self._models_dir = Path(models_dir)

    def save_model(
        self,
        model_type: str,
        model_data: Any,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """保存模型和元数据"""
        model_dir = self._models_dir / model_type
        model_dir.mkdir(parents=True, exist_ok=True)

        version = "v1"
        if metadata and "version" in metadata:
            version = metadata["version"]

        version_dir = model_dir / version
        version_dir.mkdir(parents=True, exist_ok=True)

        model_path = version_dir / "model.joblib"
        try:
            import joblib

            joblib.dump(model_data, str(model_path))
        except ImportError:
            raise ImportError("joblib未安装，无法保存模型。请运行: pip install joblib")

        if metadata:
            meta_path = version_dir / "metadata.json"
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)

        current_link = model_dir / "current"
        if current_link.exists() or current_link.is_symlink():
            current_link.unlink()
        with contextlib.suppress(OSError):
            current_link.symlink_to(version_dir, target_is_directory=True)

    def load_model(self, model_type: str, version: str | None = None) -> Any:
        """加载模型"""
        model_dir = self._models_dir / model_type

        if version:
            version_dir = model_dir / version
        else:
            current_link = model_dir / "current"
            if current_link.is_symlink():
                version_dir = current_link.resolve()
            else:
                versions = sorted(
                    [
                        d
                        for d in model_dir.iterdir()
                        if d.is_dir() and d.name.startswith("v")
                    ]
                )
                if not versions:
                    return None
                version_dir = versions[-1]

        model_path = version_dir / "model.joblib"
        if not model_path.exists():
            return None

        try:
            import joblib

            return joblib.load(str(model_path))
        except ImportError:
            raise ImportError("joblib未安装，无法加载模型。请运行: pip install joblib")
        except Exception as e:
            logger.warning(f"模型加载失败: {e}")
            return None

    def get_model_status(self, model_type: str) -> ModelStatus:
        """获取模型状态"""
        model_dir = self._models_dir / model_type
        if not model_dir.exists():
            return ModelStatus(
                model_type=model_type,
                version="",
                trained_at="",
                training_samples=0,
                validation_error=0.0,
                is_available=False,
            )

        current_link = model_dir / "current"
        if current_link.is_symlink():
            version_dir = current_link.resolve()
        else:
            versions = sorted(
                [
                    d
                    for d in model_dir.iterdir()
                    if d.is_dir() and d.name.startswith("v")
                ]
            )
            if not versions:
                return ModelStatus(
                    model_type=model_type,
                    version="",
                    trained_at="",
                    training_samples=0,
                    validation_error=0.0,
                    is_available=False,
                )
            version_dir = versions[-1]

        meta_path = version_dir / "metadata.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            return ModelStatus(
                model_type=model_type,
                version=meta.get("version", ""),
                trained_at=meta.get("trained_at", ""),
                training_samples=meta.get("training_samples", 0),
                validation_error=meta.get("validation_error", 0.0),
                is_available=True,
            )

        return ModelStatus(
            model_type=model_type,
            version="",
            trained_at="",
            training_samples=0,
            validation_error=0.0,
            is_available=True,
        )

    def rollback_model(
        self, model_type: str, target_version: str
    ) -> ModelManagementResult:
        """回滚模型到指定版本"""
        model_dir = self._models_dir / model_type
        target_dir = model_dir / target_version

        if not target_dir.exists():
            return ModelManagementResult(
                action="rollback",
                model_type=model_type,
                success=False,
                message=f"版本{target_version}不存在",
                details={},
            )

        current_link = model_dir / "current"
        if current_link.exists() or current_link.is_symlink():
            current_link.unlink()
        with contextlib.suppress(OSError):
            current_link.symlink_to(target_dir, target_is_directory=True)

        return ModelManagementResult(
            action="rollback",
            model_type=model_type,
            success=True,
            message=f"已回滚到{target_version}",
            details={"target_version": target_version},
        )

    def check_auto_update(
        self, model_type: str, new_samples: int = 0, days_since_last: int = 0
    ) -> bool:
        """检查是否需要自动更新"""
        return (
            new_samples >= self.AUTO_UPDATE_MIN_SAMPLES
            or days_since_last >= self.AUTO_UPDATE_MIN_DAYS
        )
