"""
长期训练规划生成器 - v0.12.0

支持年度/赛季/多周期训练规划生成
"""

import logging
from datetime import datetime, timedelta

from src.core.models import LongTermPlan, TrainingCycle

logger = logging.getLogger(__name__)


class LongTermPlanGenerator:
    """长期训练规划生成器

    根据用户当前体能水平、目标赛事和时间范围，生成多周期训练规划。
    遵循经典周期化训练理论：基础期→提升期→巅峰期→减量期。
    """

    CYCLE_TYPES = ["base", "build", "peak", "taper"]

    DEFAULT_CYCLE_DISTRIBUTION = {
        "base": 0.35,
        "build": 0.30,
        "peak": 0.20,
        "taper": 0.15,
    }

    VDOT_BASE_WEEKLY_VOLUME = {
        "beginner": (20, 35),
        "intermediate": (30, 55),
        "advanced": (45, 75),
        "elite": (60, 100),
    }

    def generate_plan(
        self,
        plan_name: str,
        current_vdot: float,
        target_vdot: float | None = None,
        target_race: str | None = None,
        target_date: str | None = None,
        total_weeks: int = 16,
        fitness_level: str = "intermediate",
        auto_create_training_plans: bool = True,
    ) -> LongTermPlan:
        """生成长期训练规划

        Args:
            plan_name: 计划名称
            current_vdot: 当前VDOT
            target_vdot: 目标VDOT
            target_race: 目标赛事
            target_date: 目标日期(YYYY-MM-DD)
            total_weeks: 总周数
            fitness_level: 体能水平(beginner/intermediate/advanced/elite)
            auto_create_training_plans: 是否自动创建关联的TrainingPlan

        Returns:
            LongTermPlan: 长期训练规划
        """
        cycles = self._generate_cycles(
            total_weeks=total_weeks,
            current_vdot=current_vdot,
            target_vdot=target_vdot,
            target_date=target_date,
            fitness_level=fitness_level,
        )
        volume_range = self._calculate_volume_range(
            current_vdot=current_vdot,
            fitness_level=fitness_level,
        )
        milestones = self._generate_milestones(
            current_vdot=current_vdot,
            target_vdot=target_vdot,
            total_weeks=total_weeks,
            cycles=cycles,
        )

        training_plan_ids: list[str] = []
        if auto_create_training_plans:
            training_plan_ids = self._create_training_plans_for_cycles(
                plan_name=plan_name,
                cycles=cycles,
                current_vdot=current_vdot,
                fitness_level=fitness_level,
            )

        return LongTermPlan(
            plan_name=plan_name,
            target_race=target_race,
            target_date=target_date,
            current_vdot=current_vdot,
            target_vdot=target_vdot,
            total_weeks=total_weeks,
            cycles=cycles,
            weekly_volume_range_km=volume_range,
            key_milestones=milestones,
            training_plan_ids=training_plan_ids,
        )

    def _generate_cycles(
        self,
        total_weeks: int,
        current_vdot: float,
        target_vdot: float | None,
        target_date: str | None,
        fitness_level: str,
    ) -> list[TrainingCycle]:
        """生成训练周期列表"""
        distribution = self.DEFAULT_CYCLE_DISTRIBUTION.copy()
        cycle_weeks = {
            ct: max(2, int(total_weeks * ratio)) for ct, ratio in distribution.items()
        }

        total_assigned = sum(cycle_weeks.values())
        diff = total_weeks - total_assigned
        if diff > 0:
            cycle_weeks["build"] += diff
        elif diff < 0:
            cycle_weeks["base"] += diff

        start_date = self._resolve_start_date(target_date, total_weeks)

        cycles: list[TrainingCycle] = []
        current_date = start_date

        for cycle_type in self.CYCLE_TYPES:
            weeks = cycle_weeks[cycle_type]
            end_date = current_date + timedelta(weeks=weeks)

            volume = self._calculate_cycle_volume(
                cycle_type=cycle_type,
                current_vdot=current_vdot,
                fitness_level=fitness_level,
            )
            key_workouts = self._get_key_workouts(cycle_type)
            goal = self._get_cycle_goal(cycle_type, current_vdot, target_vdot)

            cycles.append(
                TrainingCycle(
                    cycle_type=cycle_type,
                    start_date=current_date.strftime("%Y-%m-%d"),
                    end_date=end_date.strftime("%Y-%m-%d"),
                    weekly_volume_km=volume,
                    key_workouts=key_workouts,
                    goal=goal,
                )
            )
            current_date = end_date

        return cycles

    def _resolve_start_date(
        self, target_date: str | None, total_weeks: int
    ) -> datetime:
        """解析训练开始日期"""
        if target_date:
            try:
                end_dt = datetime.strptime(target_date, "%Y-%m-%d")
                return end_dt - timedelta(weeks=total_weeks)
            except ValueError:
                pass
        return datetime.now()

    def _calculate_cycle_volume(
        self,
        cycle_type: str,
        current_vdot: float,
        fitness_level: str,
    ) -> float:
        """计算周期跑量"""
        level_ranges = self.VDOT_BASE_WEEKLY_VOLUME.get(
            fitness_level, self.VDOT_BASE_WEEKLY_VOLUME["intermediate"]
        )
        base_volume = (level_ranges[0] + level_ranges[1]) / 2

        volume_multipliers = {
            "base": 0.8,
            "build": 1.0,
            "peak": 1.1,
            "taper": 0.6,
        }
        multiplier = volume_multipliers.get(cycle_type, 1.0)

        vdot_factor = max(0.7, min(1.3, current_vdot / 45.0))

        return round(base_volume * multiplier * vdot_factor, 1)

    def _get_key_workouts(self, cycle_type: str) -> list[str]:
        """获取周期关键训练"""
        workouts_map = {
            "base": ["轻松跑", "长距离跑", "恢复跑"],
            "build": ["间歇跑", "阈值跑", "长距离跑"],
            "peak": ["比赛配速跑", "间歇跑", "长距离跑"],
            "taper": ["轻松跑", "短距离间歇", "恢复跑"],
        }
        return workouts_map.get(cycle_type, ["轻松跑"])

    def _get_cycle_goal(
        self,
        cycle_type: str,
        current_vdot: float,
        target_vdot: float | None,
    ) -> str:
        """获取周期目标描述"""
        goals_map = {
            "base": "建立有氧基础，提升周跑量",
            "build": "提升速度耐力，增加高强度训练",
            "peak": "达到最佳竞技状态，模拟比赛强度",
            "taper": "减量恢复，为比赛蓄力",
        }
        base_goal = goals_map.get(cycle_type, "完成训练")

        if target_vdot and current_vdot:
            if cycle_type == "base":
                mid_vdot = current_vdot + (target_vdot - current_vdot) * 0.3
                return f"{base_goal}，目标VDOT达到{mid_vdot:.1f}"
            elif cycle_type == "build":
                mid_vdot = current_vdot + (target_vdot - current_vdot) * 0.7
                return f"{base_goal}，目标VDOT达到{mid_vdot:.1f}"
            elif cycle_type == "peak":
                return f"{base_goal}，目标VDOT达到{target_vdot:.1f}"

        return base_goal

    def _calculate_volume_range(
        self,
        current_vdot: float,
        fitness_level: str,
    ) -> tuple[float, float]:
        """计算周跑量范围"""
        level_ranges = self.VDOT_BASE_WEEKLY_VOLUME.get(
            fitness_level, self.VDOT_BASE_WEEKLY_VOLUME["intermediate"]
        )
        vdot_factor = max(0.7, min(1.3, current_vdot / 45.0))
        low = round(level_ranges[0] * vdot_factor, 1)
        high = round(level_ranges[1] * vdot_factor, 1)
        return (low, high)

    def _generate_milestones(
        self,
        current_vdot: float,
        target_vdot: float | None,
        total_weeks: int,
        cycles: list[TrainingCycle],
    ) -> list[str]:
        """生成关键里程碑"""
        milestones: list[str] = []

        if len(cycles) >= 1:
            milestones.append(f"完成基础期，周跑量达到{cycles[0].weekly_volume_km}km")

        if len(cycles) >= 2:
            milestones.append(f"完成提升期，适应{cycles[1].weekly_volume_km}km周跑量")

        if target_vdot and current_vdot:
            mid_vdot = current_vdot + (target_vdot - current_vdot) * 0.5
            milestones.append(f"VDOT达到{mid_vdot:.1f}")

        if len(cycles) >= 3:
            milestones.append("完成巅峰期，达到最佳竞技状态")

        if target_vdot:
            milestones.append(f"目标VDOT达到{target_vdot:.1f}")

        return milestones

    def _create_training_plans_for_cycles(
        self,
        plan_name: str,
        cycles: list[TrainingCycle],
        current_vdot: float,
        fitness_level: str,
    ) -> list[str]:
        """为每个训练周期创建对应的TrainingPlan

        Args:
            plan_name: 长期规划名称
            cycles: 训练周期列表
            current_vdot: 当前VDOT
            fitness_level: 体能水平

        Returns:
            list[str]: 创建的TrainingPlan ID列表
        """
        from src.core.context import get_context
        from src.core.training_plan import TrainingPlanEngine

        context = get_context()
        engine = TrainingPlanEngine()
        plan_ids: list[str] = []

        for i, cycle in enumerate(cycles):
            try:
                plan = engine.generate_plan(
                    user_id="default",
                    goal_distance_km=42.195,
                    goal_date=cycle.end_date,
                    current_vdot=current_vdot,
                    current_weekly_distance_km=cycle.weekly_volume_km,
                )

                plan.metadata = {
                    "long_term_plan_name": plan_name,
                    "cycle_type": cycle.cycle_type,
                    "cycle_index": i,
                }

                plan_id = context.plan_manager.create_plan(plan)
                plan_ids.append(plan_id)
                logger.info(
                    f"为周期[{cycle.cycle_type}]创建TrainingPlan成功：{plan_id}"
                )
            except Exception as e:
                logger.warning(
                    f"创建TrainingPlan失败：{e}，跳过周期[{cycle.cycle_type}]"
                )

        return plan_ids
