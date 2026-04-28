# BUG-001 修复集成测试
# 覆盖 plan create / plan long-term --skip-plans 命令

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from src.cli.app import app

runner = CliRunner()


class TestPlanCreateCommand:
    """plan create 命令集成测试"""

    def test_plan_create_help(self):
        """测试 plan create --help"""
        result = runner.invoke(app, ["plan", "create", "--help"])
        assert result.exit_code == 0
        assert "创建" in result.output

    def test_plan_create_missing_args(self):
        """测试缺少必要参数"""
        result = runner.invoke(app, ["plan", "create"])
        assert result.exit_code != 0

    def test_plan_create_missing_goal_date(self):
        """测试缺少目标日期参数"""
        result = runner.invoke(app, ["plan", "create", "42.195"])
        assert result.exit_code != 0

    def test_plan_create_missing_vdot(self):
        """测试缺少VDOT参数"""
        result = runner.invoke(app, ["plan", "create", "42.195", "2026-06-15"])
        assert result.exit_code != 0

    @patch("src.core.base.context.get_context")
    @patch("src.core.training_plan.TrainingPlanEngine")
    def test_plan_create_success(self, mock_engine_cls, mock_get_context):
        """测试正常创建训练计划"""
        mock_context = MagicMock()
        mock_context.config.user_id = "test_user"
        mock_plan_manager = MagicMock()
        mock_plan_manager.create_plan.return_value = "plan_test_001"
        mock_context.plan_manager = mock_plan_manager
        mock_get_context.return_value = mock_context

        mock_engine = MagicMock()
        mock_plan = MagicMock()
        mock_plan.plan_id = "plan_test_001"
        mock_plan.plan_type = MagicMock()
        mock_plan.plan_type.label = "基础期"
        mock_plan.fitness_level = MagicMock()
        mock_plan.fitness_level.label = "中级"
        mock_plan.weeks = [MagicMock()] * 8
        mock_engine.generate_plan.return_value = mock_plan
        mock_engine_cls.return_value = mock_engine

        result = runner.invoke(
            app,
            ["plan", "create", "42.195", "2026-06-15", "--vdot", "42.0"],
        )

        assert result.exit_code == 0
        assert "OK" in result.output or "创建成功" in result.output
        assert "plan_test_001" in result.output

    @patch("src.core.base.context.get_context")
    @patch("src.core.training_plan.TrainingPlanEngine")
    def test_plan_create_with_options(self, mock_engine_cls, mock_get_context):
        """测试带可选参数创建训练计划"""
        mock_context = MagicMock()
        mock_context.config.user_id = "test_user"
        mock_plan_manager = MagicMock()
        mock_plan_manager.create_plan.return_value = "plan_test_002"
        mock_context.plan_manager = mock_plan_manager
        mock_get_context.return_value = mock_context

        mock_engine = MagicMock()
        mock_plan = MagicMock()
        mock_plan.plan_id = "plan_test_002"
        mock_plan.plan_type = MagicMock()
        mock_plan.plan_type.label = "进展期"
        mock_plan.fitness_level = MagicMock()
        mock_plan.fitness_level.label = "进阶"
        mock_plan.weeks = [MagicMock()] * 12
        mock_engine.generate_plan.return_value = mock_plan
        mock_engine_cls.return_value = mock_engine

        result = runner.invoke(
            app,
            [
                "plan",
                "create",
                "21.1",
                "2026-05-01",
                "-v",
                "40.0",
                "--volume",
                "30",
                "--age",
                "35",
                "--rhr",
                "55",
            ],
        )

        assert result.exit_code == 0
        mock_engine.generate_plan.assert_called_once_with(
            user_id="test_user",
            goal_distance_km=21.1,
            goal_date="2026-05-01",
            current_vdot=40.0,
            current_weekly_distance_km=30.0,
            age=35,
            resting_hr=55,
        )

    @patch("src.core.base.context.get_context")
    @patch("src.core.training_plan.TrainingPlanEngine")
    def test_plan_create_failure(self, mock_engine_cls, mock_get_context):
        """测试创建训练计划失败"""
        mock_context = MagicMock()
        mock_context.config.user_id = "test_user"
        mock_plan_manager = MagicMock()
        mock_context.plan_manager = mock_plan_manager
        mock_get_context.return_value = mock_context

        mock_engine = MagicMock()
        mock_engine.generate_plan.side_effect = ValueError("目标日期必须晚于今天")
        mock_engine_cls.return_value = mock_engine

        result = runner.invoke(
            app,
            ["plan", "create", "42.195", "2020-01-01", "--vdot", "42.0"],
        )

        assert result.exit_code != 0


class TestPlanLongTermWithSkipPlans:
    """plan long-term --skip-plans 命令集成测试"""

    def test_plan_long_term_help(self):
        """测试 plan long-term --help"""
        result = runner.invoke(app, ["plan", "long-term", "--help"])
        assert result.exit_code == 0
        assert "长期" in result.output or "规划" in result.output

    @patch("src.core.base.context.get_context")
    def test_plan_long_term_with_skip_plans(self, mock_get_context):
        """测试 --skip-plans 跳过自动创建训练计划"""
        mock_context = MagicMock()
        mock_generator = MagicMock()
        mock_plan = MagicMock()
        mock_plan.plan_name = "测试计划"
        mock_plan.current_vdot = 42.0
        mock_plan.target_vdot = 48.0
        mock_plan.target_race = None
        mock_plan.target_date = None
        mock_plan.has_target_race = False
        mock_plan.total_weeks = 16
        mock_plan.weekly_volume_range_km = (30.0, 50.0)
        mock_plan.cycles = []
        mock_plan.key_milestones = ["完成基础期"]
        mock_plan.training_plan_ids = []
        mock_generator.generate_plan.return_value = mock_plan
        mock_context.long_term_plan_generator = mock_generator
        mock_get_context.return_value = mock_context

        result = runner.invoke(
            app,
            [
                "plan",
                "long-term",
                "测试计划",
                "--vdot",
                "42.0",
                "--skip-plans",
            ],
        )

        assert result.exit_code == 0
        mock_generator.generate_plan.assert_called_once_with(
            plan_name="测试计划",
            current_vdot=42.0,
            target_vdot=None,
            target_race=None,
            target_date=None,
            total_weeks=16,
            fitness_level="intermediate",
            auto_create_training_plans=False,
        )

    @patch("src.core.base.context.get_context")
    def test_plan_long_term_with_training_plan_ids(self, mock_get_context):
        """测试输出关联训练计划ID"""
        mock_context = MagicMock()
        mock_generator = MagicMock()

        mock_cycle_base = MagicMock()
        mock_cycle_base.cycle_type = "base"
        mock_cycle_base.start_date = "2026-06-01"
        mock_cycle_base.end_date = "2026-07-15"
        mock_cycle_base.weekly_volume_km = 35.0
        mock_cycle_base.goal = "建立有氧基础"
        mock_cycle_build = MagicMock()
        mock_cycle_build.cycle_type = "build"
        mock_cycle_build.start_date = "2026-07-16"
        mock_cycle_build.end_date = "2026-08-31"
        mock_cycle_build.weekly_volume_km = 45.0
        mock_cycle_build.goal = "提升速度耐力"
        mock_cycle_peak = MagicMock()
        mock_cycle_peak.cycle_type = "peak"
        mock_cycle_peak.start_date = "2026-09-01"
        mock_cycle_peak.end_date = "2026-09-30"
        mock_cycle_peak.weekly_volume_km = 50.0
        mock_cycle_peak.goal = "达到最佳竞技状态"
        mock_cycle_taper = MagicMock()
        mock_cycle_taper.cycle_type = "taper"
        mock_cycle_taper.start_date = "2026-10-01"
        mock_cycle_taper.end_date = "2026-10-15"
        mock_cycle_taper.weekly_volume_km = 25.0
        mock_cycle_taper.goal = "减量恢复"

        mock_plan = MagicMock()
        mock_plan.plan_name = "春季备赛"
        mock_plan.current_vdot = 42.0
        mock_plan.target_vdot = 48.0
        mock_plan.target_race = "北京马拉松"
        mock_plan.target_date = "2026-10-15"
        mock_plan.has_target_race = True
        mock_plan.total_weeks = 16
        mock_plan.weekly_volume_range_km = (30.0, 50.0)
        mock_plan.cycles = [
            mock_cycle_base,
            mock_cycle_build,
            mock_cycle_peak,
            mock_cycle_taper,
        ]
        mock_plan.key_milestones = ["完成基础期"]
        mock_plan.training_plan_ids = [
            "plan_base_001",
            "plan_build_002",
            "plan_peak_003",
            "plan_taper_004",
        ]
        mock_generator.generate_plan.return_value = mock_plan
        mock_context.long_term_plan_generator = mock_generator
        mock_get_context.return_value = mock_context

        result = runner.invoke(
            app,
            [
                "plan",
                "long-term",
                "春季备赛",
                "--vdot",
                "42.0",
                "--target",
                "48.0",
                "--race",
                "北京马拉松",
                "--date",
                "2026-10-15",
            ],
        )

        if result.exit_code != 0:
            print(f"OUTPUT: {result.output}")
            if result.exception:
                import traceback

                traceback.print_exception(
                    type(result.exception),
                    result.exception,
                    result.exception.__traceback__,
                )

        assert result.exit_code == 0
        assert "plan_base_001" in result.output
        assert "plan_build_002" in result.output
        assert "plan_peak_003" in result.output
        assert "plan_taper_004" in result.output
        assert "关联训练计划" in result.output

    @patch("src.core.base.context.get_context")
    def test_plan_long_term_without_training_plan_ids(self, mock_get_context):
        """测试无关联训练计划时不输出关联信息"""
        mock_context = MagicMock()
        mock_generator = MagicMock()
        mock_plan = MagicMock()
        mock_plan.plan_name = "测试计划"
        mock_plan.current_vdot = 42.0
        mock_plan.target_vdot = None
        mock_plan.target_race = None
        mock_plan.target_date = None
        mock_plan.has_target_race = False
        mock_plan.total_weeks = 16
        mock_plan.weekly_volume_range_km = (30.0, 50.0)
        mock_plan.cycles = []
        mock_plan.key_milestones = ["完成基础期"]
        mock_plan.training_plan_ids = []
        mock_generator.generate_plan.return_value = mock_plan
        mock_context.long_term_plan_generator = mock_generator
        mock_get_context.return_value = mock_context

        result = runner.invoke(
            app,
            [
                "plan",
                "long-term",
                "测试计划",
                "--vdot",
                "42.0",
                "--skip-plans",
            ],
        )

        assert result.exit_code == 0
        assert "关联训练计划" not in result.output
