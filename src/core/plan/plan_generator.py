"""
训练计划生成器模块

负责调用LLM生成个性化训练计划
"""

import json
from datetime import datetime
from typing import Any

from src.core.exceptions import LLMError, ValidationError
from src.core.logger import get_logger
from src.core.models import (
    DailyPlan,
    TrainingPlan,
    UserContext,
    WeeklySchedule,
)

logger = get_logger(__name__)


class PlanGenerator:
    """
    训练计划生成器

    基于用户画像、历史数据和目标，通过LLM生成个性化训练计划
    """

    MAX_RETRIES = 3
    LLM_TIMEOUT = 60

    def __init__(self, llm_provider: Any | None = None) -> None:
        """
        初始化训练计划生成器

        Args:
            llm_provider: LLM提供者实例（可选，后续可通过set_llm_provider设置）
        """
        self.llm_provider = llm_provider

    def set_llm_provider(self, llm_provider: Any) -> None:
        """
        设置LLM提供者

        Args:
            llm_provider: LLM提供者实例
        """
        self.llm_provider = llm_provider

    def generate(
        self,
        user_context: UserContext,
        goal_distance_km: float,
        goal_date: str,
        target_time: str | None = None,
        plan_type: str = "race_preparation",
    ) -> TrainingPlan:
        """
        生成训练计划

        Args:
            user_context: 用户上下文（包含用户画像、历史数据、训练负荷等）
            goal_distance_km: 目标距离（公里）
            goal_date: 目标日期（YYYY-MM-DD）
            target_time: 目标完赛时间（HH:MM:SS，可选）
            plan_type: 计划类型（默认为赛前准备）

        Returns:
            TrainingPlan: 生成的训练计划

        Raises:
            ValidationError: 参数验证失败
            LLMError: LLM调用失败
        """
        self._validate_parameters(goal_distance_km, goal_date)

        logger.info(
            f"开始生成训练计划: 目标距离={goal_distance_km}km, "
            f"目标日期={goal_date}, 目标时间={target_time}"
        )

        prompt = self._build_prompt(
            user_context, goal_distance_km, goal_date, target_time, plan_type
        )

        for attempt in range(self.MAX_RETRIES):
            try:
                llm_response = self._call_llm(prompt)
                plan = self._parse_llm_response(
                    llm_response, user_context, goal_distance_km, goal_date, target_time
                )
                logger.info(f"训练计划生成成功: plan_id={plan.plan_id}")
                return plan
            except (LLMError, ValidationError) as e:
                logger.warning(f"第{attempt + 1}次生成失败: {e}")
                if attempt == self.MAX_RETRIES - 1:
                    raise LLMError(f"训练计划生成失败，已达到最大重试次数: {str(e)}")
                continue

        raise LLMError("训练计划生成失败，已达到最大重试次数")

    def _validate_parameters(self, goal_distance_km: float, goal_date: str) -> None:
        """
        验证输入参数

        Args:
            goal_distance_km: 目标距离
            goal_date: 目标日期

        Raises:
            ValidationError: 参数验证失败
        """
        if goal_distance_km <= 0:
            raise ValidationError("目标距离必须为正数")

        try:
            parsed_date = datetime.strptime(goal_date, "%Y-%m-%d")
            if parsed_date <= datetime.now():
                raise ValidationError("目标日期必须晚于今天")
        except ValueError as e:
            raise ValidationError(f"目标日期格式错误: {e}")

    def _build_prompt(
        self,
        user_context: UserContext,
        goal_distance_km: float,
        goal_date: str,
        target_time: str | None,
        plan_type: str,
    ) -> str:
        """
        构建LLM提示词

        Args:
            user_context: 用户上下文
            goal_distance_km: 目标距离
            goal_date: 目标日期
            target_time: 目标时间
            plan_type: 计划类型

        Returns:
            str: 构建的提示词
        """
        user_profile = user_context.profile
        training_load = user_context.training_load

        prompt_parts = [
            "你是一位专业的跑步教练，请根据以下信息生成个性化的训练计划。",
            "",
            "## 用户信息",
            f"- 总活动数: {user_profile.total_activities}",
            f"- 总跑量: {user_profile.total_distance_km:.1f}km",
            f"- 平均VDOT: {user_profile.avg_vdot:.1f}",
            f"- 最大VDOT: {user_profile.max_vdot:.1f}",
            f"- 平均周跑量: {user_profile.weekly_avg_distance_km:.1f}km",
            f"- 平均配速: {user_profile.avg_pace_min_per_km:.2f}min/km",
            f"- 静息心率: {user_profile.resting_heart_rate or '未知'}bpm",
            f"- 最大心率: {user_profile.max_heart_rate or '未知'}bpm",
            "",
            "## 训练负荷",
            f"- 最近4周跑量: {training_load.recent_4_weeks_distance_km:.1f}km",
            f"- 最近周跑量: {training_load.last_week_distance_km:.1f}km",
            f"- 平均周跑量: {training_load.avg_weekly_distance_km:.1f}km",
            f"- 最长跑步距离: {training_load.longest_run_km:.1f}km",
            f"- 训练频率: {training_load.training_frequency}次/周",
            "",
            "## 训练目标",
            f"- 目标距离: {goal_distance_km}km",
            f"- 目标日期: {goal_date}",
        ]

        if target_time:
            prompt_parts.append(f"- 目标完赛时间: {target_time}")

        prompt_parts.extend(
            [
                f"- 计划类型: {plan_type}",
                "",
                "## 硬性约束（必须严格遵守）",
                "1. 周跑量增长不超过10%",
                "2. 每周至少安排1天完全休息",
                "3. 长距离跑不超过周跑量的30%",
                "4. 高强度训练（间歇/节奏）不超过周跑量的20%",
                "5. 单次最长距离不超过目标距离的120%",
                "6. 比赛前一周跑量减少40-60%",
                "",
                "## 输出要求",
                "请以JSON格式输出训练计划，包含以下字段：",
                "- plan_id: 计划ID（格式：plan_用户ID_时间戳）",
                "- user_id: 用户ID",
                "- status: 计划状态（active）",
                "- plan_type: 计划类型",
                "- start_date: 开始日期（YYYY-MM-DD）",
                "- end_date: 结束日期（YYYY-MM-DD）",
                "- goal_distance_km: 目标距离",
                "- goal_date: 目标日期",
                "- target_time: 目标时间（可选）",
                "- weeks: 周计划数组",
                "  - week_number: 周数",
                "  - start_date: 周开始日期",
                "  - end_date: 周结束日期",
                "  - daily_plans: 每日计划数组",
                "    - date: 日期",
                "    - workout_type: 训练类型（easy/long/tempo/interval/recovery/rest/cross）",
                "    - distance_km: 距离",
                "    - duration_min: 预计时长",
                "    - target_pace_min_per_km: 目标配速（可选）",
                "    - target_hr_zone: 目标心率区间（可选）",
                "    - notes: 训练说明",
                "  - weekly_distance_km: 周跑量",
                "  - weekly_duration_min: 周训练时长",
                "  - focus: 本周重点",
                "- calendar_event_ids: 日历事件ID映射（空对象）",
                "- created_at: 创建时间",
                "- updated_at: 更新时间",
                "",
                "请确保生成的计划科学合理，符合运动训练原则。",
            ]
        )

        return "\n".join(prompt_parts)

    def _call_llm(self, prompt: str) -> str:
        """
        调用LLM生成响应

        Args:
            prompt: 提示词

        Returns:
            str: LLM响应

        Raises:
            LLMError: LLM调用失败
        """
        if not self.llm_provider:
            raise LLMError("LLM提供者未设置")

        try:
            response = self.llm_provider.generate(
                prompt=prompt,
                temperature=0.7,
                max_tokens=4000,
                timeout=self.LLM_TIMEOUT,
            )
            return response
        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
            raise LLMError(f"LLM调用失败: {e}")

    def _parse_llm_response(
        self,
        llm_response: str,
        user_context: UserContext,
        goal_distance_km: float,
        goal_date: str,
        target_time: str | None,
    ) -> TrainingPlan:
        """
        解析LLM响应，构建TrainingPlan对象

        Args:
            llm_response: LLM响应文本
            user_context: 用户上下文
            goal_distance_km: 目标距离
            goal_date: 目标日期
            target_time: 目标时间

        Returns:
            TrainingPlan: 解析后的训练计划

        Raises:
            ValidationError: 解析失败或数据验证失败
        """
        try:
            json_match = llm_response
            if "```json" in llm_response:
                json_start = llm_response.find("```json") + 7
                json_end = llm_response.find("```", json_start)
                json_match = llm_response[json_start:json_end].strip()
            elif "```" in llm_response:
                json_start = llm_response.find("```") + 3
                json_end = llm_response.find("```", json_start)
                json_match = llm_response[json_start:json_end].strip()

            plan_data = json.loads(json_match)

            weeks = []
            for week_data in plan_data.get("weeks", []):
                daily_plans = []
                for day_data in week_data.get("daily_plans", []):
                    daily_plan = DailyPlan(
                        date=day_data["date"],
                        workout_type=day_data["workout_type"],
                        distance_km=day_data["distance_km"],
                        duration_min=day_data["duration_min"],
                        target_pace_min_per_km=day_data.get("target_pace_min_per_km"),
                        target_hr_zone=day_data.get("target_hr_zone"),
                        notes=day_data.get("notes", ""),
                    )
                    daily_plans.append(daily_plan)

                weekly_schedule = WeeklySchedule(
                    week_number=week_data["week_number"],
                    start_date=week_data["start_date"],
                    end_date=week_data["end_date"],
                    daily_plans=daily_plans,
                    weekly_distance_km=week_data["weekly_distance_km"],
                    weekly_duration_min=week_data["weekly_duration_min"],
                    phase=week_data.get("phase", "base"),
                    focus=week_data.get("focus", ""),
                )
                weeks.append(weekly_schedule)

            plan = TrainingPlan(
                plan_id=plan_data["plan_id"],
                user_id=plan_data["user_id"],
                status=plan_data.get("status", "active"),
                plan_type=plan_data["plan_type"],
                start_date=plan_data["start_date"],
                end_date=plan_data["end_date"],
                goal_distance_km=plan_data["goal_distance_km"],
                goal_date=plan_data["goal_date"],
                target_time=plan_data.get("target_time", target_time or ""),
                weeks=weeks,
                calendar_event_ids=plan_data.get("calendar_event_ids", {}),
                created_at=plan_data.get("created_at", datetime.now().isoformat()),
                updated_at=plan_data.get("updated_at", datetime.now().isoformat()),
                metadata=plan_data.get("metadata"),
            )

            return plan

        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            raise ValidationError(f"LLM响应格式错误: {e}")
        except KeyError as e:
            logger.error(f"缺少必需字段: {e}")
            raise ValidationError(f"LLM响应缺少必需字段: {e}")
        except Exception as e:
            logger.error(f"解析LLM响应失败: {e}")
            raise ValidationError(f"解析LLM响应失败: {e}")
