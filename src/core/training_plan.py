# 训练计划引擎
# 基于运动科学原理生成个性化训练计划

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from src.core.logger import get_logger

logger = get_logger(__name__)


class PlanType(Enum):
    """训练计划类型"""

    BASE = "基础期"  # 打有氧基础
    BUILD = "进展期"  # 提升专项能力
    PEAK = "巅峰期"  # 赛前冲刺
    RACE = "比赛期"  # 比赛周
    RECOVERY = "恢复期"  # 赛后恢复


class WorkoutType(Enum):
    """训练课类型"""

    EASY = "轻松跑"  # 有氧恢复
    LONG = "长距离跑"  # 耐力训练
    TEMPO = "节奏跑"  # 乳酸阈值训练
    INTERVAL = "间歇跑"  # 最大摄氧量训练
    RECOVERY = "恢复跑"  # 主动恢复
    REST = "休息"  # 完全休息
    CROSS = "交叉训练"  # 力量/游泳/骑行


class FitnessLevel(Enum):
    """体能水平"""

    BEGINNER = "初学者"  # VDOT < 30
    INTERMEDIATE = "中级"  # VDOT 30-44
    ADVANCED = "进阶"  # VDOT 45-59
    ELITE = "精英"  # VDOT >= 60


@dataclass
class DailyPlan:
    """单日训练计划"""

    date: str  # 日期 (YYYY-MM-DD)
    workout_type: WorkoutType  # 训练类型
    distance_km: float  # 距离 (公里)
    duration_min: int  # 预计时长 (分钟)
    target_pace_min_per_km: float | None = None  # 目标配速 (分钟/公里)
    target_hr_zone: int | None = None  # 目标心率区间 (1-5)
    notes: str = ""  # 训练说明
    completed: bool = False  # 是否完成
    actual_distance_km: float | None = None  # 实际距离
    actual_duration_min: int | None = None  # 实际时长
    actual_avg_hr: int | None = None  # 实际平均心率
    rpe: int | None = None  # 主观疲劳度 (1-10)
    hr_drift: float | None = None  # 心率漂移 (%)
    event_id: str | None = None  # 日历事件ID

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "date": self.date,
            "workout_type": self.workout_type.value,
            "distance_km": round(self.distance_km, 2),
            "duration_min": self.duration_min,
            "target_pace_min_per_km": (
                round(self.target_pace_min_per_km, 2)
                if self.target_pace_min_per_km
                else None
            ),
            "target_hr_zone": self.target_hr_zone,
            "notes": self.notes,
            "completed": self.completed,
            "actual_distance_km": (
                round(self.actual_distance_km, 2) if self.actual_distance_km else None
            ),
            "actual_duration_min": self.actual_duration_min,
            "actual_avg_hr": self.actual_avg_hr,
            "rpe": self.rpe,
            "hr_drift": (
                round(self.hr_drift, 2) if self.hr_drift is not None else None
            ),
            "event_id": self.event_id,
        }


@dataclass
class WeeklySchedule:
    """周训练计划"""

    week_number: int  # 第几周
    start_date: str  # 周开始日期 (YYYY-MM-DD)
    end_date: str  # 周结束日期 (YYYY-MM-DD)
    daily_plans: list[DailyPlan] = field(default_factory=list)  # 每日计划
    weekly_distance_km: float = 0.0  # 周跑量 (公里)
    weekly_duration_min: int = 0  # 周训练时长 (分钟)
    focus: str = ""  # 本周重点
    notes: str = ""  # 周备注

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "week_number": self.week_number,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "daily_plans": [day.to_dict() for day in self.daily_plans],
            "weekly_distance_km": round(self.weekly_distance_km, 2),
            "weekly_duration_min": self.weekly_duration_min,
            "focus": self.focus,
            "notes": self.notes,
        }


@dataclass
class TrainingPlan:
    """训练计划"""

    plan_id: str  # 计划 ID
    user_id: str  # 用户 ID
    plan_type: PlanType  # 计划类型
    fitness_level: FitnessLevel  # 体能水平
    start_date: str  # 开始日期 (YYYY-MM-DD)
    end_date: str  # 结束日期 (YYYY-MM-DD)
    goal_distance_km: float  # 目标距离 (公里)
    goal_date: str  # 目标比赛日期 (YYYY-MM-DD)
    weeks: list[WeeklySchedule] = field(default_factory=list)  # 周计划
    created_at: datetime = field(default_factory=datetime.now)  # 创建时间
    updated_at: datetime = field(default_factory=datetime.now)  # 更新时间
    notes: str = ""  # 计划备注

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "plan_id": self.plan_id,
            "user_id": self.user_id,
            "plan_type": self.plan_type.value,
            "fitness_level": self.fitness_level.value,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "goal_distance_km": round(self.goal_distance_km, 2),
            "goal_date": self.goal_date,
            "weeks": [week.to_dict() for week in self.weeks],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TrainingPlan":
        """从字典创建训练计划"""
        weeks = []
        for week_data in data.get("weeks", []):
            daily_plans = []
            for day_data in week_data.get("daily_plans", []):
                daily_plan = DailyPlan(
                    date=day_data["date"],
                    workout_type=WorkoutType(day_data["workout_type"]),
                    distance_km=day_data["distance_km"],
                    duration_min=day_data["duration_min"],
                    target_pace_min_per_km=day_data.get("target_pace_min_per_km"),
                    target_hr_zone=day_data.get("target_hr_zone"),
                    notes=day_data.get("notes", ""),
                    completed=day_data.get("completed", False),
                    actual_distance_km=day_data.get("actual_distance_km"),
                    actual_duration_min=day_data.get("actual_duration_min"),
                    actual_avg_hr=day_data.get("actual_avg_hr"),
                    rpe=day_data.get("rpe"),
                    hr_drift=day_data.get("hr_drift"),
                    event_id=day_data.get("event_id"),
                )
                daily_plans.append(daily_plan)

            week = WeeklySchedule(
                week_number=week_data["week_number"],
                start_date=week_data["start_date"],
                end_date=week_data["end_date"],
                daily_plans=daily_plans,
                weekly_distance_km=week_data.get("weekly_distance_km", 0.0),
                weekly_duration_min=week_data.get("weekly_duration_min", 0),
                focus=week_data.get("focus", ""),
                notes=week_data.get("notes", ""),
            )
            weeks.append(week)

        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.now()

        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
        elif updated_at is None:
            updated_at = datetime.now()

        return cls(
            plan_id=data["plan_id"],
            user_id=data["user_id"],
            plan_type=PlanType(data["plan_type"]),
            fitness_level=FitnessLevel(data["fitness_level"]),
            start_date=data["start_date"],
            end_date=data["end_date"],
            goal_distance_km=data["goal_distance_km"],
            goal_date=data["goal_date"],
            weeks=weeks,
            created_at=created_at,
            updated_at=updated_at,
            notes=data.get("notes", ""),
        )


# 阶段配置：定义各训练阶段的特点
PHASE_CONFIG = {
    PlanType.BASE: {
        "duration_weeks": 4,  # 基础期 4 周
        "easy_ratio": 0.80,  # 轻松跑占比 80%
        "long_ratio": 0.15,  # 长距离跑占比 15%
        "tempo_ratio": 0.05,  # 节奏跑占比 5%
        "interval_ratio": 0.0,  # 间歇跑占比 0%
        "intensity_multiplier": 0.7,  # 强度系数
        "weekly_increase": 0.10,  # 周跑量增长率 10%
    },
    PlanType.BUILD: {
        "duration_weeks": 4,  # 进展期 4 周
        "easy_ratio": 0.60,  # 轻松跑占比 60%
        "long_ratio": 0.20,  # 长距离跑占比 20%
        "tempo_ratio": 0.15,  # 节奏跑占比 15%
        "interval_ratio": 0.05,  # 间歇跑占比 5%
        "intensity_multiplier": 0.85,  # 强度系数
        "weekly_increase": 0.05,  # 周跑量增长率 5%
    },
    PlanType.PEAK: {
        "duration_weeks": 3,  # 巅峰期 3 周
        "easy_ratio": 0.50,  # 轻松跑占比 50%
        "long_ratio": 0.20,  # 长距离跑占比 20%
        "tempo_ratio": 0.20,  # 节奏跑占比 20%
        "interval_ratio": 0.10,  # 间歇跑占比 10%
        "intensity_multiplier": 1.0,  # 强度系数
        "weekly_increase": 0.0,  # 周跑量不增长
    },
    PlanType.RACE: {
        "duration_weeks": 1,  # 比赛期 1 周
        "easy_ratio": 0.70,  # 轻松跑占比 70%
        "long_ratio": 0.0,  # 长距离跑占比 0%
        "tempo_ratio": 0.20,  # 节奏跑占比 20% (赛前刺激)
        "interval_ratio": 0.10,  # 间歇跑占比 10% (赛前激活)
        "intensity_multiplier": 0.6,  # 强度系数 (减量)
        "weekly_increase": -0.50,  # 周跑量减少 50%
    },
    PlanType.RECOVERY: {
        "duration_weeks": 2,  # 恢复期 2 周
        "easy_ratio": 0.60,  # 轻松跑占比 60%
        "long_ratio": 0.0,  # 长距离跑占比 0%
        "tempo_ratio": 0.0,  # 节奏跑占比 0%
        "interval_ratio": 0.0,  # 间歇跑占比 0%
        "cross_ratio": 0.40,  # 交叉训练占比 40%
        "intensity_multiplier": 0.5,  # 强度系数
        "weekly_increase": -0.30,  # 周跑量减少 30%
    },
}


class TrainingPlanEngine:
    """训练计划引擎"""

    def __init__(self) -> None:
        """初始化训练计划引擎"""
        pass

    def get_phase_config_by_fitness_level(
        self, plan_type: PlanType, fitness_level: FitnessLevel
    ) -> dict[str, Any]:
        """
        根据体能水平获取动态阶段配置

        Args:
            plan_type: 计划类型
            fitness_level: 体能水平

        Returns:
            Dict[str, Any]: 调整后的阶段配置

        Notes:
            - 初学者：降低强度，增加恢复时间
            - 精英：提高强度，增加专项训练
        """
        base_config = PHASE_CONFIG.get(plan_type, PHASE_CONFIG[PlanType.BASE]).copy()

        # 根据体能水平调整配置
        if fitness_level == FitnessLevel.BEGINNER:
            # 初学者：降低强度 20%，增加轻松跑比例
            base_config["intensity_multiplier"] *= 0.8
            base_config["easy_ratio"] = min(
                0.90, base_config.get("easy_ratio", 0.80) + 0.10
            )
            if "interval_ratio" in base_config:
                base_config["interval_ratio"] *= 0.5  # 间歇跑减半
            base_config["weekly_increase"] = min(
                0.05, base_config.get("weekly_increase", 0.10) * 0.5
            )  # 增长率减半

        elif fitness_level == FitnessLevel.INTERMEDIATE:
            # 中级：保持标准配置
            pass

        elif fitness_level == FitnessLevel.ADVANCED:
            # 进阶：提高强度 10%，增加专项训练
            base_config["intensity_multiplier"] *= 1.1
            if "interval_ratio" in base_config:
                base_config["interval_ratio"] = min(
                    0.15, base_config.get("interval_ratio", 0.05) * 1.5
                )

        elif fitness_level == FitnessLevel.ELITE:
            # 精英：提高强度 20%，大幅增加专项训练
            base_config["intensity_multiplier"] *= 1.2
            if "interval_ratio" in base_config:
                base_config["interval_ratio"] = min(
                    0.20, base_config.get("interval_ratio", 0.05) * 2.0
                )
            if "tempo_ratio" in base_config:
                base_config["tempo_ratio"] = min(
                    0.25, base_config.get("tempo_ratio", 0.05) * 1.3
                )

        return base_config

    def generate_plan(
        self,
        user_id: str,
        goal_distance_km: float,
        goal_date: str,
        current_vdot: float,
        current_weekly_distance_km: float,
        age: int = 30,
        resting_hr: int = 60,
    ) -> TrainingPlan:
        """
        生成训练计划

        Args:
            user_id: 用户 ID
            goal_distance_km: 目标距离（公里）
            goal_date: 目标比赛日期（YYYY-MM-DD）
            current_vdot: 当前 VDOT 值
            current_weekly_distance_km: 当前周跑量（公里）
            age: 年龄（默认 30）
            resting_hr: 静息心率（默认 60）

        Returns:
            TrainingPlan: 生成的训练计划

        Raises:
            ValueError: 当参数无效时

        Notes:
            - 基于目标距离和日期自动划分训练阶段
            - 根据当前体能水平调整训练强度
            - 遵循 10% 原则（周跑量增长不超过 10%）
        """
        # 参数验证
        if goal_distance_km <= 0:
            raise ValueError("目标距离必须为正数")
        if goal_date <= datetime.now().strftime("%Y-%m-%d"):
            raise ValueError("目标日期必须晚于今天")
        if current_vdot <= 0:
            raise ValueError("VDOT 值必须为正数")
        if current_weekly_distance_km < 0:
            raise ValueError("周跑量不能为负数")
        if age <= 0 or age > 120:
            raise ValueError("年龄必须在 1-120 之间")
        if resting_hr <= 0 or resting_hr > 250:
            raise ValueError("静息心率必须在合理范围内")

        # 确定体能水平
        fitness_level = self._determine_fitness_level(current_vdot)

        # 计算可用周数
        start_date = datetime.now()
        end_date = datetime.strptime(goal_date, "%Y-%m-%d")
        total_weeks = (end_date - start_date).days // 7

        if total_weeks < 4:
            raise ValueError("训练时间至少需要 4 周")

        # 划分训练阶段
        phases = self._allocate_phases(total_weeks, goal_distance_km)

        # 生成计划 ID
        plan_id = f"plan_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # 创建训练计划
        plan = TrainingPlan(
            plan_id=plan_id,
            user_id=user_id,
            plan_type=PlanType.BASE,  # 初始为基础期
            fitness_level=fitness_level,
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            goal_distance_km=goal_distance_km,
            goal_date=goal_date,
        )

        # 生成各周计划
        current_week = 1
        current_date = start_date
        weekly_distance = current_weekly_distance_km

        for phase_type, phase_weeks in phases:
            phase_config = self.get_phase_config_by_fitness_level(
                phase_type, fitness_level
            )

            for _week_in_phase in range(phase_weeks):
                week_start = current_date
                week_end = current_date + timedelta(days=6)

                # 计算本周跑量
                if current_week > 1:
                    weekly_distance *= 1 + phase_config.get("weekly_increase", 0)

                # 限制周跑量增长不超过 10%
                if current_week > 1:
                    max_weekly_distance = current_weekly_distance_km * (
                        1 + 0.10 ** (current_week - 1)
                    )
                    weekly_distance = min(weekly_distance, max_weekly_distance)

                # 生成周计划
                weekly_schedule = self._generate_weekly_schedule(
                    week_number=current_week,
                    start_date=week_start.strftime("%Y-%m-%d"),
                    end_date=week_end.strftime("%Y-%m-%d"),
                    weekly_distance_km=weekly_distance,
                    phase_config=phase_config,
                    _fitness_level=fitness_level,
                    current_vdot=current_vdot,
                )

                plan.weeks.append(weekly_schedule)
                current_week += 1
                current_date = week_end + timedelta(days=1)

        # 更新计划类型（根据当前所在阶段）
        if phases:
            plan.plan_type = phases[0][0]

        plan.notes = f"目标：{goal_distance_km}公里 | 当前 VDOT: {current_vdot} | 体能水平：{fitness_level.value}"

        logger.info(f"生成训练计划：{plan_id}, 共{len(plan.weeks)}周")
        return plan

    def _determine_fitness_level(self, vdot: float) -> FitnessLevel:
        """
        根据 VDOT 值确定体能水平

        Args:
            vdot: VDOT 值

        Returns:
            FitnessLevel: 体能水平
        """
        if vdot < 30:
            return FitnessLevel.BEGINNER
        elif vdot < 45:
            return FitnessLevel.INTERMEDIATE
        elif vdot < 60:
            return FitnessLevel.ADVANCED
        else:
            return FitnessLevel.ELITE

    def _allocate_phases(
        self, total_weeks: int, goal_distance_km: float
    ) -> list[tuple[PlanType, int]]:
        """
        分配训练阶段

        Args:
            total_weeks: 总周数
            goal_distance_km: 目标距离

        Returns:
            List[tuple]: 阶段类型和周数的列表

        Notes:
            - 10km 以下：基础期 4 周 + 进展期 2 周 + 比赛期 1 周
            - 10-21km：基础期 4 周 + 进展期 3 周 + 巅峰期 2 周 + 比赛期 1 周
            - 21km 以上：基础期 6 周 + 进展期 4 周 + 巅峰期 3 周 + 比赛期 1 周
        """
        phases = []
        remaining_weeks = total_weeks

        if goal_distance_km < 10:
            # 短距离目标
            base_weeks = min(4, remaining_weeks - 3)
            if base_weeks > 0:
                phases.append((PlanType.BASE, base_weeks))
                remaining_weeks -= base_weeks

            build_weeks = min(2, remaining_weeks - 1)
            if build_weeks > 0:
                phases.append((PlanType.BUILD, build_weeks))
                remaining_weeks -= build_weeks

            if remaining_weeks > 0:
                phases.append((PlanType.RACE, 1))
                remaining_weeks -= 1

        elif goal_distance_km < 21:
            # 半马距离
            base_weeks = min(4, remaining_weeks - 6)
            if base_weeks > 0:
                phases.append((PlanType.BASE, base_weeks))
                remaining_weeks -= base_weeks

            build_weeks = min(3, remaining_weeks - 3)
            if build_weeks > 0:
                phases.append((PlanType.BUILD, build_weeks))
                remaining_weeks -= build_weeks

            peak_weeks = min(2, remaining_weeks - 1)
            if peak_weeks > 0:
                phases.append((PlanType.PEAK, peak_weeks))
                remaining_weeks -= peak_weeks

            if remaining_weeks > 0:
                phases.append((PlanType.RACE, 1))
                remaining_weeks -= 1

        else:
            # 全马距离
            base_weeks = min(6, remaining_weeks - 8)
            if base_weeks > 0:
                phases.append((PlanType.BASE, base_weeks))
                remaining_weeks -= base_weeks

            build_weeks = min(4, remaining_weeks - 4)
            if build_weeks > 0:
                phases.append((PlanType.BUILD, build_weeks))
                remaining_weeks -= build_weeks

            peak_weeks = min(3, remaining_weeks - 1)
            if peak_weeks > 0:
                phases.append((PlanType.PEAK, peak_weeks))
                remaining_weeks -= peak_weeks

            if remaining_weeks > 0:
                phases.append((PlanType.RACE, 1))
                remaining_weeks -= 1

        # 如果还有剩余周数，添加恢复期
        if remaining_weeks > 0 and goal_distance_km >= 21:
            recovery_weeks = min(2, remaining_weeks)
            phases.insert(0, (PlanType.RECOVERY, recovery_weeks))

        # 如果 phases 为空，至少安排基础期
        if not phases:
            phases = [(PlanType.BASE, max(1, total_weeks))]

        return phases

    def _generate_weekly_schedule(
        self,
        week_number: int,
        start_date: str,
        end_date: str,
        weekly_distance_km: float,
        phase_config: dict[str, Any],
        _fitness_level: FitnessLevel,
        current_vdot: float,
    ) -> WeeklySchedule:
        """
        生成周训练计划

        Args:
            week_number: 周数
            start_date: 开始日期
            end_date: 结束日期
            weekly_distance_km: 周跑量
            phase_config: 阶段配置
            fitness_level: 体能水平
            current_vdot: 当前 VDOT

        Returns:
            WeeklySchedule: 周计划
        """
        weekly_schedule = WeeklySchedule(
            week_number=week_number,
            start_date=start_date,
            end_date=end_date,
        )

        # 计算各类型训练的跑量
        easy_distance = weekly_distance_km * phase_config.get("easy_ratio", 0.80)
        long_distance = weekly_distance_km * phase_config.get("long_ratio", 0.15)
        tempo_distance = weekly_distance_km * phase_config.get("tempo_ratio", 0.05)
        interval_distance = weekly_distance_km * phase_config.get("interval_ratio", 0.0)
        cross_distance = weekly_distance_km * phase_config.get("cross_ratio", 0.0)

        # 强度系数
        intensity = phase_config.get("intensity_multiplier", 0.7)

        # 生成一周 7 天的训练计划（周一为休息日）
        daily_arrangements = [
            # (训练类型，距离系数，心率区间，备注)
            (WorkoutType.REST, 0, None, "完全休息日"),  # 周一
            (WorkoutType.EASY, easy_distance * 0.25, 2, "轻松有氧跑"),  # 周二
            (WorkoutType.TEMPO, tempo_distance, 3, "节奏跑训练"),  # 周三
            (WorkoutType.EASY, easy_distance * 0.25, 2, "恢复性轻松跑"),  # 周四
            (WorkoutType.INTERVAL, interval_distance, 4, "间歇跑训练"),  # 周五
            (WorkoutType.LONG, long_distance, 2, "长距离耐力跑"),  # 周六
            (WorkoutType.EASY, easy_distance * 0.50, 2, "周末轻松跑"),  # 周日
        ]

        # 处理交叉训练
        if cross_distance > 0:
            # 将周四改为交叉训练
            daily_arrangements[3] = (
                WorkoutType.CROSS,
                cross_distance,
                None,
                "交叉训练（力量/游泳/骑行）",
            )

        current_date = datetime.strptime(start_date, "%Y-%m-%d")
        total_distance = 0.0
        total_duration = 0

        for workout_type, distance_coef, hr_zone, notes in daily_arrangements:
            if workout_type == WorkoutType.REST:
                # 休息日
                daily_plan = DailyPlan(
                    date=current_date.strftime("%Y-%m-%d"),
                    workout_type=workout_type,
                    distance_km=0.0,
                    duration_min=0,
                    notes=notes,
                )
            else:
                # 计算距离和时长
                distance = max(0.5, distance_coef)  # 最少 0.5km
                total_distance += distance

                # 根据体能水平和强度系数调整配速
                base_pace = self._calculate_target_pace(current_vdot, workout_type)
                adjusted_pace = base_pace / intensity if intensity > 0 else base_pace

                # 计算时长（分钟）
                duration = int(distance * adjusted_pace)

                daily_plan = DailyPlan(
                    date=current_date.strftime("%Y-%m-%d"),
                    workout_type=workout_type,
                    distance_km=round(distance, 2),
                    duration_min=duration,
                    target_pace_min_per_km=round(adjusted_pace, 2),
                    target_hr_zone=hr_zone,
                    notes=notes,
                )
                total_duration += duration

            weekly_schedule.daily_plans.append(daily_plan)
            current_date += timedelta(days=1)

        # 更新周统计
        weekly_schedule.weekly_distance_km = round(total_distance, 2)
        weekly_schedule.weekly_duration_min = total_duration

        # 设置本周重点
        phase_type = self._get_phase_type_from_config(phase_config)
        weekly_schedule.focus = (
            f"{phase_type.value} - 周跑量{round(total_distance, 1)}km"
        )

        return weekly_schedule

    def _get_phase_type_from_config(self, phase_config: dict[str, Any]) -> PlanType:
        """根据配置反推阶段类型"""
        for plan_type, config in PHASE_CONFIG.items():
            if (
                abs(
                    config.get("duration_weeks", 0)
                    - phase_config.get("duration_weeks", 0)
                )
                < 1
            ):
                return plan_type
        return PlanType.BASE

    def _calculate_target_pace(self, vdot: float, workout_type: WorkoutType) -> float:
        """
        根据 VDOT 和训练类型计算目标配速

        Args:
            vdot: VDOT 值
            workout_type: 训练类型

        Returns:
            float: 目标配速（分钟/公里）
        """
        # 基于 VDOT 的配速估算（简化版 Powers 公式）
        # VDOT 40 ≈ 5:00/km, VDOT 50 ≈ 4:15/km, VDOT 60 ≈ 3:40/km
        base_pace = 6.0 - (vdot - 30) * 0.05  # 线性近似

        # 根据训练类型调整
        pace_multipliers = {
            WorkoutType.EASY: 1.2,  # 轻松跑比比赛配速慢 20%
            WorkoutType.LONG: 1.15,  # 长距离慢 15%
            WorkoutType.TEMPO: 0.95,  # 节奏跑快 5%
            WorkoutType.INTERVAL: 0.90,  # 间歇跑快 10%
            WorkoutType.RECOVERY: 1.4,  # 恢复跑慢 40%
            WorkoutType.REST: 1.0,  # 休息日不适用
            WorkoutType.CROSS: 1.0,  # 交叉训练不适用
        }

        multiplier = pace_multipliers.get(workout_type, 1.0)
        return max(3.0, min(8.0, base_pace * multiplier))  # 限制在 3-8 分钟/公里

    def adjust_plan(
        self,
        plan: TrainingPlan,
        week_number: int,
        hr_drift: float | None = None,
        rpe: int | None = None,
        completed_runs: list[dict[str, Any]] | None = None,
    ) -> TrainingPlan:
        """
        调整训练计划（基于心率漂移和主观疲劳度）

        Args:
            plan: 原训练计划
            week_number: 要调整的周数
            hr_drift: 心率漂移百分比（>5% 表示疲劳累积）
            rpe: 主观疲劳度（1-10 分）
            completed_runs: 已完成的训练记录

        Returns:
            TrainingPlan: 调整后的训练计划

        Raises:
            ValueError: 当参数无效时

        Notes:
            - 心率漂移 > 5%：降低下周训练强度 10-20%
            - RPE > 7：降低训练量 10-30%
            - 连续未完成：降低训练量 20%
        """
        # 参数验证
        if week_number < 1 or week_number > len(plan.weeks):
            raise ValueError(f"周数必须在 1-{len(plan.weeks)}之间")

        if hr_drift is not None and (hr_drift < -50 or hr_drift > 50):
            raise ValueError("心率漂移值异常")

        if rpe is not None and (rpe < 1 or rpe > 10):
            raise ValueError("主观疲劳度必须在 1-10 之间")

        # 获取要调整的周计划
        week_schedule = plan.weeks[week_number - 1]

        # 计算调整系数
        intensity_adjustment = 1.0
        volume_adjustment = 1.0

        # 基于心率漂移调整
        if hr_drift is not None:
            if hr_drift > 10:
                # 心率漂移严重，降低强度 20%，降低跑量 30%
                intensity_adjustment *= 0.8
                volume_adjustment *= 0.7
                logger.warning(f"心率漂移严重 ({hr_drift}%), 大幅降低训练负荷")
            elif hr_drift > 5:
                # 心率漂移明显，降低强度 10%，降低跑量 15%
                intensity_adjustment *= 0.9
                volume_adjustment *= 0.85
                logger.info(f"心率漂移明显 ({hr_drift}%), 适度降低训练负荷")

        # 基于主观疲劳度调整
        if rpe is not None:
            if rpe >= 8:
                # 非常疲劳，降低跑量 30%
                volume_adjustment *= 0.7
                logger.warning(f"主观疲劳度高 (RPE={rpe}), 降低训练量")
            elif rpe >= 6:
                # 中度疲劳，降低跑量 15%
                volume_adjustment *= 0.85
                logger.info(f"主观疲劳度中等 (RPE={rpe}), 适度降低训练量")

        # 基于完成情况调整
        if completed_runs:
            incomplete_count = sum(
                1 for run in completed_runs if not run.get("completed", True)
            )
            total_count = len(completed_runs)

            if total_count > 0 and incomplete_count / total_count > 0.5:
                # 超过一半未完成，降低跑量 20%
                volume_adjustment *= 0.8
                logger.info("训练完成率较低，降低训练量")

        # 应用调整到每日计划
        for daily_plan in week_schedule.daily_plans:
            if daily_plan.workout_type in [WorkoutType.REST, WorkoutType.RECOVERY]:
                # 休息日和恢复跑不调整
                continue

            # 调整距离
            original_distance = daily_plan.distance_km
            adjusted_distance = original_distance * volume_adjustment
            daily_plan.distance_km = round(max(0.5, adjusted_distance), 2)

            # 调整时长（基于调整后的距离和配速）
            if daily_plan.target_pace_min_per_km:
                daily_plan.duration_min = int(
                    daily_plan.distance_km * daily_plan.target_pace_min_per_km
                )

            # 调整目标配速（如果强度需要调整）
            if intensity_adjustment < 1.0 and daily_plan.target_pace_min_per_km:
                # 降低强度意味着配速变慢
                adjusted_pace = daily_plan.target_pace_min_per_km / intensity_adjustment
                daily_plan.target_pace_min_per_km = round(adjusted_pace, 2)

        # 更新周统计
        week_schedule.weekly_distance_km = round(
            sum(day.distance_km for day in week_schedule.daily_plans), 2
        )
        week_schedule.weekly_duration_min = sum(
            day.duration_min for day in week_schedule.daily_plans
        )

        # 添加调整说明
        adjustment_notes = []
        if hr_drift is not None:
            adjustment_notes.append(f"心率漂移：{hr_drift}%")
        if rpe is not None:
            adjustment_notes.append(f"主观疲劳度：{rpe}")
        if volume_adjustment < 1.0:
            adjustment_notes.append(f"跑量调整：{volume_adjustment * 100:.0f}%")
        if intensity_adjustment < 1.0:
            adjustment_notes.append(f"强度调整：{intensity_adjustment * 100:.0f}%")

        week_schedule.notes = f"计划调整：{', '.join(adjustment_notes)}"

        # 更新时间戳
        plan.updated_at = datetime.now()

        logger.info(
            f"调整训练计划第{week_number}周：跑量{volume_adjustment * 100:.0f}%, 强度{intensity_adjustment * 100:.0f}%"
        )
        return plan

    def get_daily_workout(
        self,
        plan: TrainingPlan,
        target_date: str | None = None,
    ) -> DailyPlan | None:
        """
        获取指定日期的训练内容

        Args:
            plan: 训练计划
            target_date: 目标日期（YYYY-MM-DD），不指定则返回今日训练

        Returns:
            Optional[DailyPlan]: 当日训练计划，无计划返回 None
        """
        # 确定目标日期
        if target_date is None:
            target_date = datetime.now().strftime("%Y-%m-%d")

        try:
            target_dt = datetime.strptime(target_date, "%Y-%m-%d")
        except ValueError as e:
            raise ValueError(f"日期格式无效：{target_date}，应为 YYYY-MM-DD") from e

        # 查找对应周
        for week in plan.weeks:
            week_start = datetime.strptime(week.start_date, "%Y-%m-%d")
            week_end = datetime.strptime(week.end_date, "%Y-%m-%d")

            if week_start <= target_dt <= week_end:
                # 找到对应周，查找当日计划
                for daily_plan in week.daily_plans:
                    if daily_plan.date == target_date:
                        return daily_plan

        # 未找到计划
        return None

    def get_plan_summary(self, plan: TrainingPlan) -> dict[str, Any]:
        """
        获取训练计划摘要

        Args:
            plan: 训练计划

        Returns:
            Dict[str, Any]: 计划摘要
        """
        total_distance = sum(week.weekly_distance_km for week in plan.weeks)
        total_duration = sum(week.weekly_duration_min for week in plan.weeks)

        # 统计各类型训练次数
        workout_counts: dict[str, int] = {}
        for week in plan.weeks:
            for daily_plan in week.daily_plans:
                workout_type = daily_plan.workout_type.value
                workout_counts[workout_type] = workout_counts.get(workout_type, 0) + 1

        return {
            "plan_id": plan.plan_id,
            "user_id": plan.user_id,
            "plan_type": plan.plan_type.value,
            "fitness_level": plan.fitness_level.value,
            "duration_weeks": len(plan.weeks),
            "total_distance_km": round(total_distance, 2),
            "total_duration_hours": round(total_duration / 60, 2),
            "goal_distance_km": round(plan.goal_distance_km, 2),
            "goal_date": plan.goal_date,
            "workout_distribution": workout_counts,
            "created_at": plan.created_at.isoformat(),
            "updated_at": plan.updated_at.isoformat(),
            "notes": plan.notes,
        }
