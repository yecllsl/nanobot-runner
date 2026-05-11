from __future__ import annotations

import logging
from typing import Any

from src.core.prediction.config import PredictionConfig
from src.core.prediction.models import (
    DataSufficiencyReport,
    PredictionStatusReport,
    SufficiencyDimension,
)

logger = logging.getLogger(__name__)


class DataAssessor:
    """数据充足度评估器

    评估用户数据是否满足ML增强预测的最低要求，
    不满足时自动降级为参数化基线或基础预测。
    """

    def __init__(
        self,
        session_repo: Any,
        config: PredictionConfig | None = None,
    ) -> None:
        self._repo = session_repo
        self._config = config or PredictionConfig()

    def assess_sufficiency(self, prediction_type: str) -> DataSufficiencyReport:
        """评估指定预测类型的数据充足度"""
        if prediction_type == "vdot":
            return self._assess_vdot()
        elif prediction_type == "race":
            return self._assess_race()
        elif prediction_type == "injury":
            return self._assess_injury()
        else:
            raise ValueError(f"未知的预测类型: {prediction_type}")

    def get_full_status(self) -> PredictionStatusReport:
        """获取所有预测类型的数据充足度总览"""
        vdot_status = self.assess_sufficiency("vdot")
        race_status = self.assess_sufficiency("race")
        injury_status = self.assess_sufficiency("injury")

        ready_count = sum(
            [
                vdot_status.is_sufficient,
                race_status.is_sufficient,
                injury_status.is_sufficient,
            ]
        )

        advice: list[str] = []
        if not vdot_status.is_sufficient:
            advice.append("继续积累训练数据以启用VDOT ML增强预测")
        else:
            advice.append(
                "VDOT数据已充足，运行 predict model train vdot_predictor "
                "训练ML模型以启用增强预测"
            )
        if not race_status.is_sufficient:
            advice.append("积累更多比赛数据以启用个人化比赛预测")
        if not injury_status.is_sufficient:
            advice.append("积累更多训练和心率数据以启用伤病ML预测")
        else:
            advice.append(
                "伤病数据已充足，运行 predict model train injury_predictor "
                "训练ML模型以启用增强预测"
            )

        return PredictionStatusReport(
            vdot_status=vdot_status,
            race_status=race_status,
            injury_status=injury_status,
            overall_ready_count=ready_count,
            advice=advice,
        )

    def get_accumulation_advice(self, prediction_type: str) -> list[str]:
        """获取数据积累建议"""
        report = self.assess_sufficiency(prediction_type)
        advice = list(report.advice)
        if not advice:
            advice.append("数据充足，可使用ML增强预测")
        return advice

    def _assess_vdot(self) -> DataSufficiencyReport:
        """评估VDOT预测数据充足度"""
        total_records = self._safe_call("get_total_session_count", 0)
        time_span = self._safe_call("get_data_span_months", 0.0)

        time_dim = SufficiencyDimension(
            name="time_span_months",
            current_value=float(time_span),
            target_value=float(self._config.vdot_min_months),
            is_met=time_span >= self._config.vdot_min_months,
            progress_pct=min(100.0, time_span / self._config.vdot_min_months * 100),
        )

        records_dim = SufficiencyDimension(
            name="total_records",
            current_value=float(total_records),
            target_value=float(self._config.vdot_min_records),
            is_met=total_records >= self._config.vdot_min_records,
            progress_pct=min(
                100.0, total_records / self._config.vdot_min_records * 100
            ),
        )

        dimensions = [time_dim, records_dim]
        is_sufficient = time_dim.is_met and records_dim.is_met
        overall_pct = sum(d.progress_pct for d in dimensions) / len(dimensions)

        advice: list[str] = []
        if not time_dim.is_met:
            advice.append(
                f"数据时间跨度不足，当前{time_span:.0f}个月，需要{self._config.vdot_min_months}个月以上"
            )
        if not records_dim.is_met:
            advice.append(
                f"训练记录不足，当前{total_records}条，需要{self._config.vdot_min_records}条以上"
            )

        return DataSufficiencyReport(
            prediction_type="vdot",
            is_sufficient=is_sufficient,
            overall_progress_pct=round(overall_pct, 1),
            dimensions=dimensions,
            advice=advice,
        )

    def _assess_race(self) -> DataSufficiencyReport:
        """评估比赛预测数据充足度"""
        race_count = self._safe_call("get_race_session_count", 0)

        race_dim = SufficiencyDimension(
            name="race_count",
            current_value=float(race_count),
            target_value=float(self._config.race_min_races),
            is_met=race_count >= self._config.race_min_races,
            progress_pct=min(100.0, race_count / self._config.race_min_races * 100),
        )

        advice: list[str] = []
        if not race_dim.is_met:
            advice.append(
                f"比赛记录不足，当前{race_count}场，需要{self._config.race_min_races}场以上"
            )

        return DataSufficiencyReport(
            prediction_type="race",
            is_sufficient=race_dim.is_met,
            overall_progress_pct=race_dim.progress_pct,
            dimensions=[race_dim],
            advice=advice,
        )

    def _assess_injury(self) -> DataSufficiencyReport:
        """评估伤病预测数据充足度"""
        total_records = self._safe_call("get_total_session_count", 0)
        time_span = self._safe_call("get_data_span_months", 0.0)
        hr_completeness = self._safe_call("get_hr_completeness", 0.0)

        time_dim = SufficiencyDimension(
            name="time_span_months",
            current_value=float(time_span),
            target_value=float(self._config.injury_min_months),
            is_met=time_span >= self._config.injury_min_months,
            progress_pct=min(100.0, time_span / self._config.injury_min_months * 100),
        )

        records_dim = SufficiencyDimension(
            name="total_records",
            current_value=float(total_records),
            target_value=float(self._config.injury_min_records),
            is_met=total_records >= self._config.injury_min_records,
            progress_pct=min(
                100.0, total_records / self._config.injury_min_records * 100
            ),
        )

        hr_dim = SufficiencyDimension(
            name="hr_completeness",
            current_value=hr_completeness,
            target_value=self._config.injury_min_hr_completeness,
            is_met=hr_completeness >= self._config.injury_min_hr_completeness,
            progress_pct=min(
                100.0, hr_completeness / self._config.injury_min_hr_completeness * 100
            ),
        )

        dimensions = [time_dim, records_dim, hr_dim]
        is_sufficient = all(d.is_met for d in dimensions)
        overall_pct = sum(d.progress_pct for d in dimensions) / len(dimensions)

        advice: list[str] = []
        if not time_dim.is_met:
            advice.append(
                f"数据时间跨度不足，当前{time_span:.0f}个月，需要{self._config.injury_min_months}个月以上"
            )
        if not records_dim.is_met:
            advice.append(
                f"训练记录不足，当前{total_records}条，需要{self._config.injury_min_records}条以上"
            )
        if not hr_dim.is_met:
            advice.append(
                f"心率数据完整度不足，当前{hr_completeness:.0%}，需要{self._config.injury_min_hr_completeness:.0%}以上"
            )

        return DataSufficiencyReport(
            prediction_type="injury",
            is_sufficient=is_sufficient,
            overall_progress_pct=round(overall_pct, 1),
            dimensions=dimensions,
            advice=advice,
        )

    def _safe_call(self, method_name: str, default: Any) -> Any:
        """防御性调用，异常时返回默认值"""
        try:
            method = getattr(self._repo, method_name, None)
            if method is None:
                return default
            result = method()
            if not isinstance(result, (int, float)):
                return default
            return result
        except Exception as e:
            logger.warning(f"DataAssessor调用{method_name}失败: {e}")
            return default
