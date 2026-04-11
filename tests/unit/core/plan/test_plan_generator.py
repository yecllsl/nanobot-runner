"""
PlanGenerator 单元测试
"""

import json
from datetime import datetime
from typing import Any
from unittest.mock import Mock

import pytest

from src.core.exceptions import LLMError, ValidationError
from src.core.models import (
    TrainingLoad,
    TrainingPlan,
    UserContext,
    UserPreferences,
)
from src.core.plan.plan_generator import PlanGenerator
from src.core.profile import RunnerProfile


class TestPlanGenerator:
    """PlanGenerator 测试类"""

    def setup_method(self):
        """每个测试方法前的设置"""
        self.mock_llm = Mock()
        self.generator = PlanGenerator(llm_provider=self.mock_llm)

        self.user_context = UserContext(
            profile=RunnerProfile(
                user_id="test_user",
                profile_date=datetime.now(),
                total_activities=100,
                total_distance_km=1500.0,
                total_duration_hours=150.0,
                avg_vdot=45.0,
                max_vdot=48.0,
                weekly_avg_distance_km=30.0,
                weekly_avg_duration_hours=3.5,
                avg_pace_min_per_km=6.0,
                resting_heart_rate=60.0,
                max_heart_rate=190.0,
            ),
            recent_activities=[],
            training_load=TrainingLoad(
                atl=10.0,
                ctl=12.0,
                tsb=-2.0,
                recent_4_weeks_distance_km=120.0,
                last_week_distance_km=35.0,
                avg_weekly_distance_km=30.0,
                longest_run_km=15.0,
                training_frequency=4,
            ),
            preferences=UserPreferences(
                preferred_training_days=["monday", "wednesday", "friday", "sunday"],
                preferred_training_time="morning",
                enable_calendar_sync=True,
            ),
            historical_best_pace_min_per_km=5.5,
        )

    def test_generate_plan_success(self):
        """测试成功生成训练计划"""
        mock_llm_response = self._create_mock_llm_response()
        self.mock_llm.generate.return_value = json.dumps(mock_llm_response)

        plan = self.generator.generate(
            user_context=self.user_context,
            goal_distance_km=21.0975,
            goal_date="2026-05-01",
            target_time="2:00:00",
            plan_type="race_preparation",
        )

        assert isinstance(plan, TrainingPlan)
        assert plan.goal_distance_km == 21.0975
        assert plan.goal_date == "2026-05-01"
        assert plan.target_time == "2:00:00"
        assert len(plan.weeks) > 0

    def test_generate_plan_with_invalid_distance(self):
        """测试无效距离参数"""
        with pytest.raises(ValidationError):
            self.generator.generate(
                user_context=self.user_context,
                goal_distance_km=0,
                goal_date="2026-05-01",
            )

        with pytest.raises(ValidationError):
            self.generator.generate(
                user_context=self.user_context,
                goal_distance_km=-5,
                goal_date="2026-05-01",
            )

    def test_generate_plan_with_invalid_date(self):
        """测试无效日期参数"""
        with pytest.raises(ValidationError):
            self.generator.generate(
                user_context=self.user_context,
                goal_distance_km=21.0975,
                goal_date="invalid-date",
            )

    def test_generate_plan_with_past_date(self):
        """测试过去的日期"""
        with pytest.raises(ValidationError):
            self.generator.generate(
                user_context=self.user_context,
                goal_distance_km=21.0975,
                goal_date="2020-01-01",
            )

    def test_generate_plan_llm_failure(self):
        """测试LLM调用失败"""
        self.mock_llm.generate.side_effect = Exception("LLM service unavailable")

        with pytest.raises(LLMError):
            self.generator.generate(
                user_context=self.user_context,
                goal_distance_km=21.0975,
                goal_date="2026-05-01",
            )

    def test_generate_plan_retry_mechanism(self):
        """测试重试机制"""
        self.mock_llm.generate.side_effect = [
            Exception("First attempt failed"),
            Exception("Second attempt failed"),
            json.dumps(self._create_mock_llm_response()),
        ]

        plan = self.generator.generate(
            user_context=self.user_context,
            goal_distance_km=21.0975,
            goal_date="2026-05-01",
        )

        assert isinstance(plan, TrainingPlan)
        assert self.mock_llm.generate.call_count == 3

    def test_generate_plan_max_retries_exceeded(self):
        """测试超过最大重试次数"""
        self.mock_llm.generate.side_effect = Exception("LLM service unavailable")

        with pytest.raises(LLMError, match="最大重试次数"):
            self.generator.generate(
                user_context=self.user_context,
                goal_distance_km=21.0975,
                goal_date="2026-05-01",
            )

    def test_build_prompt(self):
        """测试提示词构建"""
        prompt = self.generator._build_prompt(
            user_context=self.user_context,
            goal_distance_km=21.0975,
            goal_date="2026-05-01",
            target_time="2:00:00",
            plan_type="race_preparation",
        )

        assert "21.0975" in prompt
        assert "2026-05-01" in prompt
        assert "2:00:00" in prompt
        assert "30" in prompt

    def test_parse_llm_response_success(self):
        """测试成功解析LLM响应"""
        mock_response = self._create_mock_llm_response()

        plan = self.generator._parse_llm_response(
            llm_response=json.dumps(mock_response),
            user_context=self.user_context,
            goal_distance_km=21.0975,
            goal_date="2026-05-01",
            target_time="2:00:00",
        )

        assert isinstance(plan, TrainingPlan)
        assert plan.plan_id.startswith("plan_")
        assert plan.goal_distance_km == 21.0975
        assert len(plan.weeks) == 2

    def test_parse_llm_response_missing_fields(self):
        """测试LLM响应缺少必需字段"""
        invalid_response = {"weeks": []}

        with pytest.raises(ValidationError, match="缺少必需字段"):
            self.generator._parse_llm_response(
                llm_response=json.dumps(invalid_response),
                user_context=self.user_context,
                goal_distance_km=21.0975,
                goal_date="2026-05-01",
                target_time="2:00:00",
            )

    def test_parse_llm_response_invalid_json(self):
        """测试无效JSON响应"""
        with pytest.raises(ValidationError, match="LLM响应格式错误"):
            self.generator._parse_llm_response(
                llm_response="invalid json",
                user_context=self.user_context,
                goal_distance_km=21.0975,
                goal_date="2026-05-01",
                target_time="2:00:00",
            )

    def test_set_llm_provider(self):
        """测试设置LLM提供者"""
        generator = PlanGenerator()
        assert generator.llm_provider is None

        mock_llm = Mock()
        generator.set_llm_provider(mock_llm)
        assert generator.llm_provider == mock_llm

    def _create_mock_llm_response(self) -> dict[str, Any]:
        """创建模拟的LLM响应"""
        return {
            "plan_id": "plan_test_user_20260420",
            "user_id": "test_user",
            "status": "active",
            "plan_type": "race_preparation",
            "start_date": "2026-04-20",
            "end_date": "2026-05-03",
            "goal_distance_km": 21.0975,
            "goal_date": "2026-05-01",
            "target_time": "2:00:00",
            "calendar_event_ids": {},
            "created_at": "2026-04-20 10:00:00",
            "updated_at": "2026-04-20 10:00:00",
            "weeks": [
                {
                    "week_number": 1,
                    "start_date": "2026-04-20",
                    "end_date": "2026-04-26",
                    "daily_plans": [
                        {
                            "date": "2026-04-20",
                            "workout_type": "easy_run",
                            "distance_km": 8.0,
                            "duration_min": 48,
                            "target_pace_min_per_km": 6.0,
                            "target_hr_zone": 2,
                            "notes": "轻松跑",
                        },
                        {
                            "date": "2026-04-22",
                            "workout_type": "tempo_run",
                            "distance_km": 10.0,
                            "duration_min": 55,
                            "target_pace_min_per_km": 5.5,
                            "target_hr_zone": 3,
                            "notes": "节奏跑",
                        },
                        {
                            "date": "2026-04-24",
                            "workout_type": "easy_run",
                            "distance_km": 8.0,
                            "duration_min": 48,
                            "target_pace_min_per_km": 6.0,
                            "target_hr_zone": 2,
                            "notes": "轻松跑",
                        },
                        {
                            "date": "2026-04-26",
                            "workout_type": "long_run",
                            "distance_km": 16.0,
                            "duration_min": 100,
                            "target_pace_min_per_km": 6.2,
                            "target_hr_zone": 2,
                            "notes": "长距离跑",
                        },
                    ],
                    "weekly_distance_km": 42.0,
                    "weekly_duration_min": 251,
                    "phase": "base",
                    "focus": "建立基础耐力",
                },
                {
                    "week_number": 2,
                    "start_date": "2026-04-27",
                    "end_date": "2026-05-03",
                    "daily_plans": [
                        {
                            "date": "2026-04-27",
                            "workout_type": "easy_run",
                            "distance_km": 8.0,
                            "duration_min": 48,
                            "target_pace_min_per_km": 6.0,
                            "target_hr_zone": 2,
                            "notes": "轻松跑",
                        },
                        {
                            "date": "2026-04-29",
                            "workout_type": "interval",
                            "distance_km": 10.0,
                            "duration_min": 50,
                            "target_pace_min_per_km": 5.0,
                            "target_hr_zone": 4,
                            "notes": "间歇训练",
                        },
                        {
                            "date": "2026-05-01",
                            "workout_type": "rest",
                            "distance_km": 0,
                            "duration_min": 0,
                            "notes": "比赛日",
                        },
                    ],
                    "weekly_distance_km": 18.0,
                    "weekly_duration_min": 98,
                    "phase": "taper",
                    "focus": "减量调整",
                },
            ],
        }
