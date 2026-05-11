from __future__ import annotations

import contextlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import polars as pl

from src.core.prediction.models import (
    ModelManagementResult,
    ModelStatus,
    PredictionRecord,
)

logger = logging.getLogger(__name__)


class ModelManager:
    """模型生命周期管理器

    管理ML模型的保存/加载/版本/回滚/增量学习/预测历史
    """

    AUTO_UPDATE_MIN_SAMPLES = 50
    AUTO_UPDATE_MIN_DAYS = 30
    AUTO_UPDATE_ERROR_THRESHOLD = 0.15
    PREDICTIONS_DIR_NAME = "predictions"

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
        """加载模型 — 含sklearn版本兼容性校验"""
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

            model = joblib.load(str(model_path))
        except ImportError:
            raise ImportError("joblib未安装，无法加载模型。请运行: pip install joblib")
        except Exception as e:
            logger.warning(f"模型加载失败: {e}")
            return None

        if not self._check_sklearn_compat(version_dir):
            logger.warning("sklearn版本不兼容，需要重新训练")
            return None

        return model

    def _check_sklearn_compat(self, version_dir: Path) -> bool:
        """校验sklearn版本兼容性"""
        meta_path = version_dir / "metadata.json"
        if not meta_path.exists():
            return True

        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            saved_version = meta.get("sklearn_version", "")
            if not saved_version:
                return True

            import sklearn

            current_version = sklearn.__version__
            saved_major = saved_version.split(".")[0]
            current_major = current_version.split(".")[0]
            if saved_major != current_major:
                logger.warning(
                    f"sklearn主版本不兼容: 保存={saved_version}, 当前={current_version}"
                )
                return False
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"sklearn版本校验异常: {e}")

        return True

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

    def rollback(self, model_type: str, target_version: str | None = None) -> bool:
        """回滚模型到上一版本或指定版本"""
        model_dir = self._models_dir / model_type
        if not model_dir.exists():
            return False

        versions = sorted(
            [d for d in model_dir.iterdir() if d.is_dir() and d.name.startswith("v")]
        )
        if len(versions) < 2:
            return False

        if target_version:
            target_dir = model_dir / target_version
            if not target_dir.exists():
                return False
        else:
            current_link = model_dir / "current"
            if current_link.is_symlink():
                current_version = current_link.resolve().name
                idx = next(
                    (i for i, v in enumerate(versions) if v.name == current_version),
                    len(versions) - 1,
                )
                if idx == 0:
                    return False
                target_dir = versions[idx - 1]
            else:
                target_dir = versions[-2]

        current_link = model_dir / "current"
        if current_link.exists() or current_link.is_symlink():
            current_link.unlink()
        with contextlib.suppress(OSError):
            current_link.symlink_to(target_dir, target_is_directory=True)

        return True

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

    def record_prediction(self, record: PredictionRecord) -> None:
        """记录预测历史 — 写入predictions.parquet按年分片"""
        predictions_dir = self._models_dir / self.PREDICTIONS_DIR_NAME
        predictions_dir.mkdir(parents=True, exist_ok=True)

        year = record.prediction_date[:4]
        parquet_path = predictions_dir / f"predictions_{year}.parquet"

        new_row = pl.DataFrame(
            {
                "prediction_date": [record.prediction_date],
                "prediction_type": [record.prediction_type],
                "predicted_value": [record.predicted_value],
                "predicted_unit": [record.predicted_unit],
                "actual_value": [record.actual_value],
                "deviation_pct": [record.deviation_pct],
                "prediction_method": [record.prediction_method],
                "model_version": [record.model_version],
                "confidence": [record.confidence],
            },
            schema={
                "prediction_date": pl.Utf8,
                "prediction_type": pl.Utf8,
                "predicted_value": pl.Float64,
                "predicted_unit": pl.Utf8,
                "actual_value": pl.Float64,
                "deviation_pct": pl.Float64,
                "prediction_method": pl.Utf8,
                "model_version": pl.Utf8,
                "confidence": pl.Float64,
            },
        )

        if parquet_path.exists():
            existing = pl.read_parquet(str(parquet_path))
            combined = pl.concat([existing, new_row])
            combined.write_parquet(str(parquet_path))
        else:
            new_row.write_parquet(str(parquet_path))

    def query_predictions(
        self,
        prediction_type: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[PredictionRecord]:
        """查询预测历史 — 支持按类型和日期范围筛选"""
        predictions_dir = self._models_dir / self.PREDICTIONS_DIR_NAME
        if not predictions_dir.exists():
            return []

        parquet_files = sorted(predictions_dir.glob("predictions_*.parquet"))
        if not parquet_files:
            return []

        dfs: list[pl.DataFrame] = []
        for pf in parquet_files:
            if pf.exists():
                dfs.append(pl.read_parquet(str(pf)))

        if not dfs:
            return []

        combined = pl.concat(dfs)

        if prediction_type:
            combined = combined.filter(pl.col("prediction_type") == prediction_type)
        if start_date:
            combined = combined.filter(pl.col("prediction_date") >= start_date)
        if end_date:
            combined = combined.filter(pl.col("prediction_date") <= end_date)

        records: list[PredictionRecord] = []
        for row in combined.iter_rows(named=True):
            records.append(
                PredictionRecord(
                    prediction_date=str(row["prediction_date"]),
                    prediction_type=str(row["prediction_type"]),
                    predicted_value=float(row["predicted_value"]),
                    predicted_unit=str(row["predicted_unit"]),
                    actual_value=(
                        float(row["actual_value"])
                        if row["actual_value"] is not None
                        else None
                    ),
                    deviation_pct=(
                        float(row["deviation_pct"])
                        if row["deviation_pct"] is not None
                        else None
                    ),
                    prediction_method=str(row["prediction_method"]),
                    model_version=str(row["model_version"]),
                    confidence=float(row["confidence"]),
                )
            )

        return records

    def check_and_update_actual(self, prediction_type: str) -> int:
        """回填实际值并计算偏差 — 返回更新记录数"""
        predictions_dir = self._models_dir / self.PREDICTIONS_DIR_NAME
        if not predictions_dir.exists():
            return 0

        parquet_files = sorted(predictions_dir.glob("predictions_*.parquet"))
        if not parquet_files:
            return 0

        updated_count = 0
        for pf in parquet_files:
            df = pl.read_parquet(str(pf))
            pending = df.filter(
                (pl.col("prediction_type") == prediction_type)
                & pl.col("actual_value").is_null()
            )
            if pending.height == 0:
                continue

            actuals = self._fetch_actual_values(prediction_type, pending)
            if not actuals:
                continue

            rows = df.to_dicts()
            for row in rows:
                if (
                    row["prediction_type"] == prediction_type
                    and row["actual_value"] is None
                    and row["prediction_date"] in actuals
                ):
                    row["actual_value"] = actuals[row["prediction_date"]]
                    predicted = row["predicted_value"]
                    if predicted and predicted != 0:
                        row["deviation_pct"] = round(
                            abs(row["actual_value"] - predicted) / abs(predicted) * 100,
                            2,
                        )
                    updated_count += 1

            df = pl.DataFrame(rows, schema=df.schema)
            df.write_parquet(str(pf))

        return updated_count

    def _fetch_actual_values(
        self, prediction_type: str, pending_df: pl.DataFrame
    ) -> dict[str, float]:
        """获取实际值 — 子类或外部可覆写"""
        try:
            from datetime import datetime as dt

            from src.core.base.context import get_context

            context = get_context()
            session_repo = context.session_repo

            actuals: dict[str, float] = {}
            for row in pending_df.iter_rows(named=True):
                date_str = str(row["prediction_date"])
                try:
                    target_date = dt.fromisoformat(date_str)
                    sessions = session_repo.get_sessions_by_date_range(
                        target_date, target_date
                    )
                except Exception as e:
                    logger.debug(f"获取日期范围session失败({date_str}): {e}")
                    sessions = []
                if sessions:
                    if prediction_type == "vdot":
                        vdot = getattr(sessions[0], "vdot", None)
                        if vdot and vdot > 0:
                            actuals[date_str] = float(vdot)
                    elif prediction_type == "race":
                        duration = getattr(sessions[0], "duration_seconds", None)
                        if duration and duration > 0:
                            actuals[date_str] = float(duration)
            return actuals
        except Exception as e:
            logger.warning(f"获取实际值失败: {e}")
            return {}

    def trigger_auto_update_if_needed(
        self, model_type: str, new_samples: int = 0
    ) -> bool:
        """检查并触发增量学习 — 新增数据/距上次训练/误差超阈值"""
        status = self.get_model_status(model_type)
        if not status.is_available:
            return True

        if new_samples >= self.AUTO_UPDATE_MIN_SAMPLES:
            logger.info(f"{model_type}: 新增{new_samples}条数据，触发增量学习")
            return True

        if status.trained_at:
            try:
                trained_dt = datetime.fromisoformat(status.trained_at)
                days_since = (datetime.now() - trained_dt).days
                if days_since >= self.AUTO_UPDATE_MIN_DAYS:
                    logger.info(f"{model_type}: 距上次训练{days_since}天，触发增量学习")
                    return True
            except (ValueError, TypeError):
                pass

        predictions = self.query_predictions(prediction_type=model_type)
        if predictions:
            with_actual = [
                p
                for p in predictions
                if p.actual_value is not None and p.deviation_pct is not None
            ]
            if with_actual:
                avg_deviation = sum(
                    abs(p.deviation_pct if p.deviation_pct is not None else 0)
                    for p in with_actual
                ) / len(with_actual)
                if avg_deviation > self.AUTO_UPDATE_ERROR_THRESHOLD * 100:
                    logger.info(
                        f"{model_type}: 平均偏差{avg_deviation:.1f}%，触发增量学习"
                    )
                    return True

        return False

    def check_auto_update(
        self, model_type: str, new_samples: int = 0, days_since_last: int = 0
    ) -> bool:
        """检查是否需要自动更新"""
        return (
            new_samples >= self.AUTO_UPDATE_MIN_SAMPLES
            or days_since_last >= self.AUTO_UPDATE_MIN_DAYS
        )
