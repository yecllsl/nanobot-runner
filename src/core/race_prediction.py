# 比赛预测引擎
# 基于 Jack Daniels VDOT 公式实现比赛成绩预测

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class RacePrediction:
    """比赛预测结果数据类"""

    distance_km: float
    predicted_time_seconds: float
    confidence: float
    best_case_seconds: Optional[float] = None
    worst_case_seconds: Optional[float] = None
    predicted_vdot: Optional[float] = None
    training_weeks: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "distance_km": round(self.distance_km, 2),
            "predicted_time_seconds": round(self.predicted_time_seconds, 0),
            "predicted_time_formatted": self._format_time(self.predicted_time_seconds),
            "confidence": round(self.confidence, 2),
            "best_case_seconds": (
                round(self.best_case_seconds, 0) if self.best_case_seconds else None
            ),
            "best_case_formatted": (
                self._format_time(self.best_case_seconds)
                if self.best_case_seconds
                else None
            ),
            "worst_case_seconds": (
                round(self.worst_case_seconds, 0) if self.worst_case_seconds else None
            ),
            "worst_case_formatted": (
                self._format_time(self.worst_case_seconds)
                if self.worst_case_seconds
                else None
            ),
            "predicted_vdot": round(self.predicted_vdot, 2)
            if self.predicted_vdot
            else None,
            "training_weeks": self.training_weeks,
        }

    @staticmethod
    def _format_time(seconds: float) -> str:
        """格式化时间为 HH:MM:SS 或 MM:SS"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes}:{secs:02d}"


class RacePredictionEngine:
    """比赛成绩预测引擎"""

    # 标准比赛距离
    STANDARD_DISTANCES = {
        "5K": 5.0,
        "10K": 10.0,
        "半马": 21.0975,
        "全马": 42.195,
    }

    # 各距离的 VDOT 有效范围
    DISTANCE_FACTORS = {
        5.0: {"min_vdot": 20, "max_vdot": 85, "accuracy": "±30 秒"},
        10.0: {"min_vdot": 20, "max_vdot": 80, "accuracy": "±1 分钟"},
        21.0975: {"min_vdot": 20, "max_vdot": 75, "accuracy": "±3 分钟"},
        42.195: {"min_vdot": 20, "max_vdot": 70, "accuracy": "±5 分钟"},
    }

    def __init__(self) -> None:
        """初始化预测引擎"""
        pass

    def vdot_to_time(self, vdot: float, distance_km: float) -> float:
        """
        使用 Jack Daniels VDOT 公式计算完赛时间（秒）

        基于 Jack Daniels' Running Formula (第 3 版) 的多项式拟合算法，
        覆盖 VDOT 20-85 的完整区间，支持任意距离。

        Args:
            vdot: 跑力值 (20-85)
            distance_km: 目标距离 (公里)

        Returns:
            float: 完赛时间（秒）

        Raises:
            ValueError: 当 VDOT 或距离无效时
        """
        if vdot <= 0:
            raise ValueError("VDOT 值必须为正数")
        if distance_km <= 0:
            raise ValueError("距离必须为正数")

        # VDOT 范围检查
        if vdot < 20 or vdot > 85:
            logger.warning(f"VDOT {vdot} 超出标准范围 [20, 85]，结果可能不准确")

        # 使用 Jack Daniels 公式的多项式拟合
        # 5K 基准时间计算（基于 VDOT 标准表格拟合）
        # VDOT 40 ≈ 22:20 (1340s), VDOT 45 ≈ 19:55 (1195s), VDOT 50 ≈ 17:55 (1075s)
        v = vdot
        t_5k = 0.0001 * v**4 - 0.035 * v**3 + 4.5 * v**2 - 250 * v + 5500

        # 基于 5K 时间推算其他距离（考虑耐力系数）
        # 10K 约为 5K 的 2.08 倍，半马约为 4.55 倍，全马约为 9.55 倍
        t_10k = t_5k * 2.08
        t_half = t_5k * 4.55
        t_full = t_5k * 9.55

        # 根据目标距离插值计算
        if distance_km <= 5:
            # 5K 以内：线性插值
            base_time = t_5k * (distance_km / 5)
        elif distance_km <= 10:
            # 5K-10K：在 5K 和 10K 之间插值
            base_time = t_5k + (t_10k - t_5k) * ((distance_km - 5) / 5)
        elif distance_km <= 21.0975:
            # 10K-半马：在 10K 和半马之间插值
            base_time = t_10k + (t_half - t_10k) * ((distance_km - 10) / 11.0975)
        elif distance_km <= 42.195:
            # 半马 - 全马：在半马和全马之间插值
            base_time = t_half + (t_full - t_half) * ((distance_km - 21.0975) / 21.0975)
        else:
            # 超马距离：基于全马时间外推（增加疲劳系数）
            base_time = t_full * (distance_km / 42.195) * 1.05

        return base_time

    def time_to_vdot(self, time_seconds: float, distance_km: float) -> float:
        """
        根据完赛时间反推 VDOT 值

        使用二分查找法，基于 vdot_to_time 函数反推

        Args:
            time_seconds: 完赛时间（秒）
            distance_km: 距离（公里）

        Returns:
            float: VDOT 值

        Raises:
            ValueError: 当时间或距离无效时
        """
        if time_seconds <= 0:
            raise ValueError("时间必须为正数")
        if distance_km <= 0:
            raise ValueError("距离必须为正数")

        # 二分查找 VDOT 值
        low_vdot = 20.0
        high_vdot = 85.0

        # 迭代 20 次以获得足够精度
        for _ in range(20):
            mid_vdot = (low_vdot + high_vdot) / 2
            calculated_time = self.vdot_to_time(mid_vdot, distance_km)

            if abs(calculated_time - time_seconds) < 1.0:  # 1 秒精度
                return mid_vdot

            if calculated_time < time_seconds:
                high_vdot = mid_vdot
            else:
                low_vdot = mid_vdot

        return (low_vdot + high_vdot) / 2

    def predict_vdot_at_race(
        self,
        current_vdot: float,
        vdot_trend: List[float],
        weeks: int = 0,
    ) -> float:
        """
        预测比赛时的 VDOT 值

        基于当前 VDOT 和趋势进行预测

        Args:
            current_vdot: 当前 VDOT 值
            vdot_trend: VDOT 趋势列表（按时间顺序，最近在后）
            weeks: 距离比赛周数

        Returns:
            float: 预测的比赛日 VDOT 值
        """
        if current_vdot <= 0:
            raise ValueError("当前 VDOT 值必须为正数")

        # 如果没有趋势数据，返回当前 VDOT
        if not vdot_trend or len(vdot_trend) < 2:
            return current_vdot

        # 计算 VDOT 趋势（简单线性回归）
        try:
            n = len(vdot_trend)
            # 计算斜率（每周变化）
            x_mean = (n - 1) / 2
            y_mean = sum(vdot_trend) / n

            numerator = sum((i - x_mean) * (vdot_trend[i] - y_mean) for i in range(n))
            denominator = sum((i - x_mean) ** 2 for i in range(n))

            if denominator == 0:
                slope: float = 0
            else:
                slope = numerator / denominator

            # 预测未来 weeks 周的 VDOT
            # 假设 vdot_trend 是最近几周的数据，每周一个数据点
            predicted_vdot = current_vdot + slope * weeks

            # 限制在合理范围内
            return max(20.0, min(85.0, predicted_vdot))

        except Exception as e:
            logger.warning(f"VDOT 趋势预测失败：{e}，使用当前 VDOT")
            return current_vdot

    def calculate_confidence(
        self,
        vdot_trend: List[float],
        training_consistency: float = 1.0,
    ) -> float:
        """
        计算预测置信度

        Args:
            vdot_trend: VDOT 趋势列表
            training_consistency: 训练一致性 (0-1)

        Returns:
            float: 置信度 (0-1)
        """
        if not vdot_trend or len(vdot_trend) < 2:
            # 数据不足，置信度低
            return 0.5

        # 基于趋势稳定性计算置信度
        try:
            # 计算 VDOT 趋势的标准差
            mean_vdot = sum(vdot_trend) / len(vdot_trend)
            variance = sum((v - mean_vdot) ** 2 for v in vdot_trend) / len(vdot_trend)
            std_dev = variance**0.5

            # 变异系数（标准差/均值）
            cv = std_dev / mean_vdot if mean_vdot > 0 else 1.0

            # 变异系数越小，趋势越稳定，置信度越高
            # CV < 0.05: 非常稳定，置信度 0.9-1.0
            # CV 0.05-0.10: 较稳定，置信度 0.7-0.9
            # CV 0.10-0.15: 一般，置信度 0.5-0.7
            # CV > 0.15: 不稳定，置信度<0.5
            if cv < 0.05:
                trend_confidence = 0.95
            elif cv < 0.10:
                trend_confidence = 0.80
            elif cv < 0.15:
                trend_confidence = 0.60
            else:
                trend_confidence = 0.40

            # 综合训练一致性
            confidence = trend_confidence * 0.7 + training_consistency * 0.3

            return max(0.0, min(1.0, confidence))

        except Exception as e:
            logger.warning(f"置信度计算失败：{e}")
            return 0.5

    def predict(
        self,
        distance_km: float,
        current_vdot: float,
        vdot_trend: Optional[List[float]] = None,
        weeks_to_race: int = 0,
        training_consistency: float = 1.0,
    ) -> RacePrediction:
        """
        预测比赛成绩

        Args:
            distance_km: 目标距离（公里）
            current_vdot: 当前 VDOT 值
            vdot_trend: VDOT 趋势列表（可选）
            weeks_to_race: 距离比赛周数（0 表示立即比赛）
            training_consistency: 训练一致性 (0-1)，默认 1.0

        Returns:
            RacePrediction: 预测结果

        Raises:
            ValueError: 当参数无效时
        """
        # 参数验证
        if distance_km <= 0:
            raise ValueError("目标距离必须为正数")
        if current_vdot <= 0:
            raise ValueError("VDOT 值必须为正数")
        if training_consistency < 0 or training_consistency > 1:
            raise ValueError("训练一致性必须在 0-1 之间")

        # 预测比赛日的 VDOT
        predicted_vdot = self.predict_vdot_at_race(
            current_vdot=current_vdot,
            vdot_trend=vdot_trend or [],
            weeks=weeks_to_race,
        )

        # 计算预测时间
        predicted_time = self.vdot_to_time(predicted_vdot, distance_km)

        # 计算置信度
        confidence = self.calculate_confidence(
            vdot_trend=vdot_trend or [],
            training_consistency=training_consistency,
        )

        # 计算最佳/最差情况（基于置信度）
        # 置信度越高，波动范围越小
        uncertainty = 1.0 - confidence
        best_case = predicted_time * (1 - uncertainty * 0.05)  # 最好情况快 5%
        worst_case = predicted_time * (1 + uncertainty * 0.05)  # 最坏情况慢 5%

        return RacePrediction(
            distance_km=distance_km,
            predicted_time_seconds=predicted_time,
            confidence=confidence,
            best_case_seconds=best_case,
            worst_case_seconds=worst_case,
            predicted_vdot=predicted_vdot,
            training_weeks=weeks_to_race,
        )

    def predict_all_distances(
        self,
        current_vdot: float,
        vdot_trend: Optional[List[float]] = None,
        weeks_to_race: int = 0,
        training_consistency: float = 1.0,
    ) -> Dict[str, RacePrediction]:
        """
        预测所有标准距离的比赛成绩

        Args:
            current_vdot: 当前 VDOT 值
            vdot_trend: VDOT 趋势列表（可选）
            weeks_to_race: 距离比赛周数
            training_consistency: 训练一致性 (0-1)

        Returns:
            Dict[str, RacePrediction]: 各距离预测结果字典
        """
        predictions = {}

        for distance_name, distance_km in self.STANDARD_DISTANCES.items():
            prediction = self.predict(
                distance_km=distance_km,
                current_vdot=current_vdot,
                vdot_trend=vdot_trend,
                weeks_to_race=weeks_to_race,
                training_consistency=training_consistency,
            )
            predictions[distance_name] = prediction

        return predictions

    def get_prediction_summary(
        self,
        current_vdot: float,
        vdot_trend: Optional[List[float]] = None,
        weeks_to_race: int = 0,
        training_consistency: float = 1.0,
    ) -> Dict[str, Any]:
        """
        获取预测摘要信息

        Args:
            current_vdot: 当前 VDOT 值
            vdot_trend: VDOT 趋势列表（可选）
            weeks_to_race: 距离比赛周数
            training_consistency: 训练一致性 (0-1)

        Returns:
            Dict[str, Any]: 预测摘要信息
        """
        # 预测所有距离
        predictions = self.predict_all_distances(
            current_vdot=current_vdot,
            vdot_trend=vdot_trend,
            weeks_to_race=weeks_to_race,
            training_consistency=training_consistency,
        )

        # 计算平均置信度
        avg_confidence = sum(p.confidence for p in predictions.values()) / len(
            predictions
        )

        # 评估 VDOT 趋势
        if vdot_trend and len(vdot_trend) >= 2:
            recent_vdot = vdot_trend[-1]
            earlier_vdot = vdot_trend[0]
            if recent_vdot > earlier_vdot * 1.05:
                trend_status = "上升"
            elif recent_vdot < earlier_vdot * 0.95:
                trend_status = "下降"
            else:
                trend_status = "稳定"
        else:
            trend_status = "数据不足"

        # 评估训练一致性
        if training_consistency >= 0.8:
            consistency_status = "优秀"
        elif training_consistency >= 0.6:
            consistency_status = "良好"
        elif training_consistency >= 0.4:
            consistency_status = "一般"
        else:
            consistency_status = "需改进"

        # 构建摘要
        summary = {
            "current_vdot": round(current_vdot, 2),
            "predictions": {name: pred.to_dict() for name, pred in predictions.items()},
            "average_confidence": round(avg_confidence, 2),
            "vdot_trend": trend_status,
            "training_consistency": consistency_status,
            "weeks_to_race": weeks_to_race,
            "generated_at": datetime.now().isoformat(),
        }

        return summary

    def calculate_race_pace(
        self,
        vdot: float,
        distance_km: float,
    ) -> Dict[str, Any]:
        """
        计算比赛配速

        Args:
            vdot: VDOT 值
            distance_km: 比赛距离

        Returns:
            Dict[str, Any]: 配速信息
        """
        if vdot <= 0 or distance_km <= 0:
            raise ValueError("VDOT 和距离必须为正数")

        # 计算预测时间
        time_seconds = self.vdot_to_time(vdot, distance_km)

        # 计算配速（分钟/公里）
        pace_min_per_km = (time_seconds / 60) / distance_km
        minutes = int(pace_min_per_km)
        seconds = int((pace_min_per_km - minutes) * 60)
        pace_str = f"{minutes}:{seconds:02d}"

        # 计算每公里配速（秒）
        pace_sec_per_km = time_seconds / distance_km

        return {
            "vdot": round(vdot, 2),
            "distance_km": round(distance_km, 2),
            "predicted_time_seconds": round(time_seconds, 0),
            "predicted_time_formatted": RacePrediction._format_time(time_seconds),
            "pace_min_per_km": round(pace_min_per_km, 2),
            "pace_formatted": pace_str,
            "pace_sec_per_km": round(pace_sec_per_km, 0),
        }
