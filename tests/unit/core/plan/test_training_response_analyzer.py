# TrainingResponseAnalyzer单元测试

from unittest.mock import MagicMock

from src.core.models import (
    PlanExecutionStats,
    TrainingResponsePattern,
    TrainingType,
)
from src.core.plan.plan_execution_repository import PlanExecutionRepository
from src.core.plan.training_response_analyzer import TrainingResponseAnalyzer


def create_test_stats(
    completion_rate: float = 0.7,
    avg_effort: float = 5.0,
) -> PlanExecutionStats:
    """创建测试执行统计"""
    return PlanExecutionStats(
        plan_id="test_plan",
        total_planned_days=7,
        completed_days=5,
        completion_rate=completion_rate,
        avg_effort_score=avg_effort,
        total_distance_km=25.0,
        total_duration_min=180,
        avg_hr=145,
        avg_hr_drift=2.5,
    )


def create_test_patterns() -> list[TrainingResponsePattern]:
    """创建测试训练响应模式"""
    return [
        TrainingResponsePattern(
            workout_type=TrainingType.EASY,
            avg_completion_rate=0.95,
            avg_effort_score=4.0,
            avg_hr_drift=1.5,
            sample_count=5,
            recommendation="适应良好",
        ),
        TrainingResponsePattern(
            workout_type=TrainingType.INTERVAL,
            avg_completion_rate=0.5,
            avg_effort_score=8.5,
            avg_hr_drift=4.0,
            sample_count=3,
            recommendation="适应较差",
        ),
        TrainingResponsePattern(
            workout_type=TrainingType.TEMPO,
            avg_completion_rate=0.75,
            avg_effort_score=6.0,
            avg_hr_drift=2.8,
            sample_count=4,
            recommendation="适应一般",
        ),
    ]


class TestAnalyzePlanResponse:
    """测试分析计划执行响应"""

    def setup_method(self):
        self.mock_repo = MagicMock(spec=PlanExecutionRepository)
        self.analyzer = TrainingResponseAnalyzer(self.mock_repo)

    def test_returns_success_with_valid_plan(self):
        self.mock_repo.get_plan_execution_stats.return_value = create_test_stats()
        self.mock_repo.get_training_response_patterns.return_value = (
            create_test_patterns()
        )

        result = self.analyzer.analyze_plan_response("test_plan")

        assert result["success"] is True
        assert "data" in result
        assert "stats" in result["data"]
        assert "patterns" in result["data"]
        assert "overall_assessment" in result["data"]

    def test_returns_error_on_exception(self):
        self.mock_repo.get_plan_execution_stats.side_effect = Exception("db error")

        result = self.analyzer.analyze_plan_response("test_plan")

        assert result["success"] is False
        assert "error" in result

    def test_includes_weak_types(self):
        self.mock_repo.get_plan_execution_stats.return_value = create_test_stats()
        self.mock_repo.get_training_response_patterns.return_value = (
            create_test_patterns()
        )

        result = self.analyzer.analyze_plan_response("test_plan")

        assert "weak_types" in result["data"]
        weak = result["data"]["weak_types"]
        assert any(wt["workout_type"] == "interval" for wt in weak)

    def test_includes_strong_types(self):
        self.mock_repo.get_plan_execution_stats.return_value = create_test_stats()
        self.mock_repo.get_training_response_patterns.return_value = (
            create_test_patterns()
        )

        result = self.analyzer.analyze_plan_response("test_plan")

        assert "strong_types" in result["data"]
        strong = result["data"]["strong_types"]
        assert any(st["workout_type"] == "easy" for st in strong)


class TestAssessOverall:
    """测试整体评估"""

    def setup_method(self):
        self.mock_repo = MagicMock(spec=PlanExecutionRepository)
        self.analyzer = TrainingResponseAnalyzer(self.mock_repo)

    def test_empty_plan(self):
        stats = PlanExecutionStats(
            plan_id="empty",
            total_planned_days=0,
            completed_days=0,
            completion_rate=0.0,
            avg_effort_score=0.0,
            total_distance_km=0.0,
            total_duration_min=0,
            avg_hr=None,
            avg_hr_drift=None,
        )
        result = self.analyzer._assess_overall(stats, [])
        assert "尚未开始" in result

    def test_excellent_response(self):
        stats = create_test_stats(completion_rate=0.95, avg_effort=4.0)
        result = self.analyzer._assess_overall(stats, [])
        assert "适应良好" in result

    def test_good_completion_tired_effort(self):
        stats = create_test_stats(completion_rate=0.75, avg_effort=8.0)
        result = self.analyzer._assess_overall(stats, [])
        assert "体感偏累" in result

    def test_moderate_completion(self):
        stats = create_test_stats(completion_rate=0.75, avg_effort=5.5)
        result = self.analyzer._assess_overall(stats, [])
        assert "良好" in result

    def test_low_completion(self):
        stats = create_test_stats(completion_rate=0.4, avg_effort=5.0)
        result = self.analyzer._assess_overall(stats, [])
        assert "偏低" in result

    def test_very_low_completion(self):
        stats = create_test_stats(completion_rate=0.3, avg_effort=5.0)
        result = self.analyzer._assess_overall(stats, [])
        assert "偏低" in result


class TestIdentifyWeakTypes:
    """测试识别适应性较差的训练类型"""

    def setup_method(self):
        self.mock_repo = MagicMock(spec=PlanExecutionRepository)
        self.analyzer = TrainingResponseAnalyzer(self.mock_repo)

    def test_identifies_low_completion(self):
        patterns = [
            TrainingResponsePattern(
                workout_type=TrainingType.INTERVAL,
                avg_completion_rate=0.4,
                avg_effort_score=6.0,
                avg_hr_drift=3.0,
                sample_count=3,
                recommendation="test",
            ),
        ]
        weak = self.analyzer._identify_weak_types(patterns)
        assert len(weak) == 1
        assert weak[0]["workout_type"] == "interval"

    def test_identifies_high_effort(self):
        patterns = [
            TrainingResponsePattern(
                workout_type=TrainingType.LONG,
                avg_completion_rate=0.7,
                avg_effort_score=9.0,
                avg_hr_drift=3.0,
                sample_count=2,
                recommendation="test",
            ),
        ]
        weak = self.analyzer._identify_weak_types(patterns)
        assert len(weak) == 1

    def test_no_weak_types(self):
        patterns = [
            TrainingResponsePattern(
                workout_type=TrainingType.EASY,
                avg_completion_rate=0.9,
                avg_effort_score=4.0,
                avg_hr_drift=1.5,
                sample_count=5,
                recommendation="test",
            ),
        ]
        weak = self.analyzer._identify_weak_types(patterns)
        assert len(weak) == 0


class TestIdentifyStrongTypes:
    """测试识别适应性较好的训练类型"""

    def setup_method(self):
        self.mock_repo = MagicMock(spec=PlanExecutionRepository)
        self.analyzer = TrainingResponseAnalyzer(self.mock_repo)

    def test_identifies_strong_type(self):
        patterns = [
            TrainingResponsePattern(
                workout_type=TrainingType.EASY,
                avg_completion_rate=0.9,
                avg_effort_score=4.0,
                avg_hr_drift=1.5,
                sample_count=5,
                recommendation="test",
            ),
        ]
        strong = self.analyzer._identify_strong_types(patterns)
        assert len(strong) == 1
        assert strong[0]["workout_type"] == "easy"

    def test_no_strong_types(self):
        patterns = [
            TrainingResponsePattern(
                workout_type=TrainingType.INTERVAL,
                avg_completion_rate=0.5,
                avg_effort_score=8.0,
                avg_hr_drift=4.0,
                sample_count=3,
                recommendation="test",
            ),
        ]
        strong = self.analyzer._identify_strong_types(patterns)
        assert len(strong) == 0
