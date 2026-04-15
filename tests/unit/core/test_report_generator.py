# ReportGenerator 单元测试
# 测试报告生成器的核心功能

from datetime import datetime
from pathlib import Path
from unittest.mock import Mock

import polars as pl
import pytest

from src.core.models import ReportData, ReportType
from src.core.report_generator import ReportConfig, ReportGenerator, TemplateEngine


class TestTemplateEngine:
    """测试模板引擎"""

    def test_init_default_templates(self):
        """测试初始化默认模板"""
        engine = TemplateEngine()

        assert "weekly" in engine._templates
        assert "monthly" in engine._templates
        assert "training_cycle" in engine._templates

    def test_get_template_weekly(self):
        """测试获取周报模板"""
        engine = TemplateEngine()
        template = engine.get_template(ReportType.WEEKLY)

        assert "跑步训练周报" in template
        assert "{total_runs}" in template
        assert "{total_distance" in template

    def test_get_template_monthly(self):
        """测试获取月报模板"""
        engine = TemplateEngine()
        template = engine.get_template(ReportType.MONTHLY)

        assert "跑步训练月报" in template
        assert "{total_runs}" in template
        assert "{start_ctl" in template

    def test_get_template_training_cycle(self):
        """测试获取训练周期报告模板"""
        engine = TemplateEngine()
        template = engine.get_template(ReportType.TRAINING_CYCLE)

        assert "训练周期报告" in template
        assert "{cycle_type}" in template
        assert "{next_cycle_advice}" in template

    def test_get_template_custom_file(self, tmp_path):
        """测试使用自定义模板文件"""
        custom_template = "# 自定义报告\n\n训练次数: {total_runs}"
        template_file = tmp_path / "custom_template.md"
        template_file.write_text(custom_template, encoding="utf-8")

        engine = TemplateEngine(template_path=template_file)
        template = engine.get_template(ReportType.WEEKLY)

        assert "自定义报告" in template
        assert "{total_runs}" in template

    def test_get_template_custom_file_not_found(self):
        """测试自定义模板文件不存在时使用默认模板"""
        engine = TemplateEngine(template_path=Path("/nonexistent/template.md"))
        template = engine.get_template(ReportType.WEEKLY)

        assert "跑步训练周报" in template


class TestReportConfig:
    """测试报告配置数据类"""

    def test_report_config_creation(self):
        """测试创建报告配置"""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 7)
        config = ReportConfig(
            report_type=ReportType.WEEKLY,
            start_date=start_date,
            end_date=end_date,
            age=30,
            rest_hr=60,
        )

        assert config.report_type == ReportType.WEEKLY
        assert config.start_date == start_date
        assert config.end_date == end_date
        assert config.age == 30
        assert config.rest_hr == 60
        assert config.include_hr_analysis is True
        assert config.include_vdot_trend is True
        assert config.include_training_load is True


class TestReportGeneratorInit:
    """测试报告生成器初始化"""

    def test_init_with_context(self):
        """测试使用 AppContext 初始化"""
        mock_context = Mock()
        mock_context.config = Mock()
        mock_context.storage = Mock()
        mock_context.analytics = Mock()

        generator = ReportGenerator(mock_context)

        assert generator.context == mock_context
        assert generator.config == mock_context.config
        assert generator.storage == mock_context.storage
        assert generator.analytics == mock_context.analytics
        assert isinstance(generator.template_engine, TemplateEngine)


class TestCalculateStartDate:
    """测试计算开始日期"""

    @pytest.fixture
    def generator(self):
        """创建 ReportGenerator 实例"""
        mock_context = Mock()
        mock_context.config = Mock()
        mock_context.storage = Mock()
        mock_context.analytics = Mock()
        return ReportGenerator(mock_context)

    def test_calculate_start_date_weekly(self, generator):
        """测试计算周报开始日期"""
        end_date = datetime(2024, 1, 7)
        start_date = generator._calculate_start_date(ReportType.WEEKLY, end_date)

        assert start_date == datetime(2024, 1, 1)
        assert (end_date - start_date).days == 6

    def test_calculate_start_date_monthly(self, generator):
        """测试计算月报开始日期"""
        end_date = datetime(2024, 1, 31)
        start_date = generator._calculate_start_date(ReportType.MONTHLY, end_date)

        assert start_date == datetime(2024, 1, 2)
        assert (end_date - start_date).days == 29

    def test_calculate_start_date_training_cycle(self, generator):
        """测试计算训练周期报告开始日期"""
        end_date = datetime(2024, 1, 31)
        start_date = generator._calculate_start_date(
            ReportType.TRAINING_CYCLE, end_date
        )

        assert start_date == datetime(2023, 12, 21)
        assert (end_date - start_date).days == 41

    def test_calculate_start_date_with_custom_start(self, generator):
        """测试使用自定义开始日期"""
        end_date = datetime(2024, 1, 31)
        custom_start = datetime(2024, 1, 15)
        start_date = generator._calculate_start_date(
            ReportType.WEEKLY, end_date, custom_start
        )

        assert start_date == custom_start


class TestGenerateReport:
    """测试生成报告"""

    @pytest.fixture
    def mock_context(self):
        """创建 Mock AppContext"""
        mock_context = Mock()
        mock_context.config = Mock()
        mock_context.storage = Mock()
        mock_context.analytics = Mock()
        return mock_context

    @pytest.fixture
    def generator(self, mock_context):
        """创建 ReportGenerator 实例"""
        return ReportGenerator(mock_context)

    def test_generate_report_weekly_success(self, generator, mock_context):
        """测试生成周报成功"""
        mock_context.storage.query_by_date_range.return_value = []
        mock_context.analytics.calculate_tss.return_value = 0.0
        mock_context.analytics.get_training_load.return_value = {
            "atl": 50.0,
            "ctl": 60.0,
            "tsb": 10.0,
            "fitness_status": "良好",
        }
        mock_context.analytics.get_heart_rate_zones.return_value = None
        mock_context.analytics.get_vdot_trend.return_value = []

        result = generator.generate_report(
            report_type=ReportType.WEEKLY,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 7),
            age=30,
        )

        assert isinstance(result, ReportData)
        assert result.success is True
        assert result.report_type == "weekly"
        assert result.content is not None
        assert "跑步训练周报" in result.content

    def test_generate_report_monthly_success(self, generator, mock_context):
        """测试生成月报成功"""
        mock_context.storage.query_by_date_range.return_value = []
        mock_context.analytics.calculate_tss.return_value = 0.0
        mock_context.analytics.get_training_load.return_value = {
            "atl": 50.0,
            "ctl": 60.0,
            "tsb": 10.0,
            "fitness_status": "良好",
        }
        mock_context.analytics.get_heart_rate_zones.return_value = None
        mock_context.analytics.get_vdot_trend.return_value = []

        result = generator.generate_report(
            report_type=ReportType.MONTHLY,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
            age=30,
        )

        assert isinstance(result, ReportData)
        assert result.success is True
        assert result.report_type == "monthly"
        assert result.content is not None
        assert "跑步训练月报" in result.content

    def test_generate_report_invalid_date_range(self, generator):
        """测试无效日期范围"""
        result = generator.generate_report(
            report_type=ReportType.WEEKLY,
            start_date=datetime(2024, 1, 31),
            end_date=datetime(2024, 1, 1),
            age=30,
        )

        assert isinstance(result, ReportData)
        assert result.success is False
        assert "参数错误" in result.error

    def test_generate_report_with_exception(self, generator, mock_context):
        """测试生成报告时发生异常"""
        mock_context.analytics.get_running_summary.side_effect = Exception("数据库错误")

        result = generator.generate_report(
            report_type=ReportType.WEEKLY,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 7),
            age=30,
        )

        assert isinstance(result, ReportData)
        assert result.success is False
        assert "生成失败" in result.error

    def test_generate_report_auto_date_range(self, generator, mock_context):
        """测试自动计算日期范围"""
        import polars as pl

        from src.core.models import HRZoneResult

        mock_stats = pl.DataFrame(
            {
                "total_runs": [0],
                "total_distance": [0.0],
                "total_timer_time": [0.0],
                "avg_heart_rate": [0.0],
            }
        )
        mock_context.analytics.get_running_summary.return_value = mock_stats
        mock_context.analytics.calculate_tss.return_value = 0.0
        mock_context.analytics.get_training_load.return_value = {
            "atl": 50.0,
            "ctl": 60.0,
            "tsb": 10.0,
            "fitness_status": "良好",
        }
        mock_hr_zones = HRZoneResult(
            max_hr=190,
            zones=[],
            total_time_in_hr=0,
            activities_count=0,
        )
        mock_context.analytics.get_heart_rate_zones.return_value = mock_hr_zones
        mock_context.analytics.get_vdot_trend.return_value = []

        end_date = datetime(2024, 1, 7)
        result = generator.generate_report(
            report_type=ReportType.WEEKLY,
            end_date=end_date,
            age=30,
        )

        assert isinstance(result, ReportData)
        assert result.success is True
        mock_context.analytics.get_running_summary.assert_called_once()


class TestFormatMethods:
    """测试格式化方法"""

    @pytest.fixture
    def generator(self):
        """创建 ReportGenerator 实例"""
        mock_context = Mock()
        mock_context.config = Mock()
        mock_context.storage = Mock()
        mock_context.analytics = Mock()
        return ReportGenerator(mock_context)

    def test_format_hr_zones_with_data(self, generator):
        """测试格式化心率区间数据"""
        hr_zones_data = {
            "zones": [
                {
                    "zone": 1,
                    "name": "热身",
                    "time_seconds": 600,
                    "percentage": 10.0,
                },
                {
                    "zone": 2,
                    "name": "燃脂",
                    "time_seconds": 1200,
                    "percentage": 20.0,
                },
            ]
        }

        result = generator._format_hr_zones(hr_zones_data)

        assert "1" in result
        assert "2" in result
        assert "热身" in result
        assert "燃脂" in result

    def test_format_hr_zones_empty(self, generator):
        """测试格式化空心率区间数据"""
        result = generator._format_hr_zones({})

        assert "暂无心率区间数据" in result

    def test_format_vdot_trend_with_data(self, generator):
        """测试格式化 VDOT 趋势数据"""
        vdot_trend = [
            {"date": "2024-01-01", "vdot": 40.5},
            {"date": "2024-01-07", "vdot": 41.2},
        ]

        result = generator._format_vdot_trend(vdot_trend)

        assert "2024-01-01" in result
        assert "40.5" in result
        assert "2024-01-07" in result
        assert "41.2" in result

    def test_format_vdot_trend_empty(self, generator):
        """测试格式化空 VDOT 趋势数据"""
        result = generator._format_vdot_trend([])

        assert "暂无 VDOT 趋势数据" in result

    def test_format_pace_distribution_with_data(self, generator):
        """测试格式化配速分布数据"""
        pace_data = {
            "zones": {
                "Z1": {
                    "label": "恢复跑",
                    "count": 5,
                    "distance": 10.0,
                },
                "Z2": {
                    "label": "轻松跑",
                    "count": 10,
                    "distance": 20.0,
                },
            }
        }

        result = generator._format_pace_distribution(pace_data)

        assert "恢复跑" in result
        assert "轻松跑" in result
        assert "Z1" in result
        assert "Z2" in result

    def test_format_pace_distribution_empty(self, generator):
        """测试格式化空配速分布数据"""
        result = generator._format_pace_distribution({})

        assert "暂无配速分布数据" in result


class TestCollectReportData:
    """测试收集报告数据"""

    @pytest.fixture
    def generator(self):
        """创建 ReportGenerator 实例"""
        mock_context = Mock()
        mock_context.config = Mock()
        mock_context.storage = Mock()
        mock_context.analytics = Mock()
        return ReportGenerator(mock_context)

    def test_collect_report_data_basic(self, generator):
        """测试收集基本报告数据"""
        config = ReportConfig(
            report_type=ReportType.WEEKLY,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 7),
            age=30,
        )

        generator.storage.query_by_date_range.return_value = []
        generator.analytics.calculate_tss.return_value = 0.0
        generator.analytics.get_training_load.return_value = {
            "atl": 50.0,
            "ctl": 60.0,
            "tsb": 10.0,
            "fitness_status": "良好",
        }
        generator.analytics.get_heart_rate_zones.return_value = None
        generator.analytics.get_vdot_trend.return_value = []

        result = generator._collect_report_data(config)

        assert "start_date" in result
        assert "end_date" in result
        assert "total_runs" in result
        assert "total_distance" in result
        assert "total_duration" in result

    def test_collect_report_data_with_sessions(self, generator):
        """测试收集包含训练记录的报告数据"""
        import polars as pl

        from src.core.models import HRZoneResult

        config = ReportConfig(
            report_type=ReportType.WEEKLY,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 7),
            age=30,
        )

        mock_stats = pl.DataFrame(
            {
                "total_runs": [2],
                "total_distance": [18000.0],
                "total_timer_time": [108.0],
                "avg_heart_rate": [147.5],
            }
        )

        generator.analytics.get_running_summary.return_value = mock_stats
        generator.analytics.calculate_tss.return_value = 150.0
        generator.analytics.get_training_load.return_value = {
            "atl": 50.0,
            "ctl": 60.0,
            "tsb": 10.0,
            "fitness_status": "良好",
        }
        mock_hr_zones = HRZoneResult(
            max_hr=190,
            zones=[],
            total_time_in_hr=0,
            activities_count=0,
        )
        generator.analytics.get_heart_rate_zones.return_value = mock_hr_zones
        generator.analytics.get_vdot_trend.return_value = []

        result = generator._collect_report_data(config)

        assert result["total_runs"] == 2
        assert result["total_distance"] == 18.0
        assert result["total_duration"] == 108.0 / 3600


class TestReportGeneratorIntegration:
    """报告生成器集成测试"""

    @pytest.fixture
    def mock_context(self):
        """创建完整的 Mock AppContext"""
        mock_context = Mock()
        mock_context.config = Mock()
        mock_context.storage = Mock()
        mock_context.analytics = Mock()
        return mock_context

    def test_full_weekly_report_workflow(self, mock_context):
        """测试完整的周报生成流程"""
        mock_sessions = [
            {
                "date": "2024-01-01",
                "distance_km": 10.0,
                "duration_min": 60.0,
                "avg_hr": 150,
                "avg_pace": 360.0,
            }
        ]

        mock_context.storage.query_by_date_range.return_value = mock_sessions
        mock_context.analytics.calculate_tss.return_value = 100.0
        mock_context.analytics.get_training_load.return_value = {
            "atl": 50.0,
            "ctl": 60.0,
            "tsb": 10.0,
            "fitness_status": "良好",
        }
        mock_context.analytics.get_heart_rate_zones.return_value = {
            "zones": [
                {"zone": 1, "min_hr": 100, "max_hr": 120, "time_min": 10},
            ]
        }
        mock_context.analytics.get_vdot_trend.return_value = [
            {"date": "2024-01-01", "vdot": 40.5}
        ]

        generator = ReportGenerator(mock_context)
        result = generator.generate_report(
            report_type=ReportType.WEEKLY,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 7),
            age=30,
        )

        assert result.success is True
        assert result.report_type == "weekly"
        assert len(result.content) > 0
        assert result.data is not None

    def test_full_monthly_report_workflow(self, mock_context):
        """测试完整的月报生成流程"""
        mock_sessions = [
            {
                "date": "2024-01-01",
                "distance_km": 10.0,
                "duration_min": 60.0,
                "avg_hr": 150,
                "avg_pace": 360.0,
            }
        ]

        mock_context.storage.query_by_date_range.return_value = mock_sessions
        mock_context.analytics.calculate_tss.return_value = 100.0
        mock_context.analytics.get_training_load.return_value = {
            "atl": 50.0,
            "ctl": 60.0,
            "tsb": 10.0,
            "fitness_status": "良好",
        }
        mock_context.analytics.get_heart_rate_zones.return_value = None
        mock_context.analytics.get_vdot_trend.return_value = []

        generator = ReportGenerator(mock_context)
        result = generator.generate_report(
            report_type=ReportType.MONTHLY,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
            age=30,
        )

        assert result.success is True
        assert result.report_type == "monthly"
        assert len(result.content) > 0


class TestTemplateEngineAdvanced:
    """测试模板引擎高级功能"""

    def test_render_with_missing_variable(self):
        """测试渲染时缺少变量"""
        engine = TemplateEngine()
        template = "Hello {name}, your score is {score}"

        result = engine.render(template, {"name": "Alice"})

        assert result == template

    def test_render_with_error(self):
        """测试渲染时发生错误"""
        engine = TemplateEngine()
        template = "Hello {name}"

        result = engine.render(template, None)

        assert "模板渲染失败" in result or "Hello {name}" in result

    def test_set_custom_template(self):
        """测试设置自定义模板"""
        engine = TemplateEngine()
        custom_template = "# Custom Report\n\nDistance: {total_distance}"

        engine.set_custom_template(ReportType.WEEKLY, custom_template)
        template = engine.get_template(ReportType.WEEKLY)

        assert "Custom Report" in template
        assert "{total_distance}" in template


class TestReportGeneratorAdvanced:
    """测试报告生成器高级功能"""

    @pytest.fixture
    def mock_context(self):
        """创建 Mock AppContext"""
        mock_context = Mock()
        mock_context.config = Mock()
        mock_context.storage = Mock()
        mock_context.analytics = Mock()
        return mock_context

    @pytest.fixture
    def generator(self, mock_context):
        """创建 ReportGenerator 实例"""
        return ReportGenerator(mock_context)

    def test_generate_training_cycle_report(self, generator, mock_context):
        """测试生成训练周期报告"""
        mock_context.storage.query_by_date_range.return_value = []
        mock_context.analytics.calculate_tss.return_value = 0.0
        mock_context.analytics.get_training_load.return_value = {
            "atl": 50.0,
            "ctl": 60.0,
            "tsb": 10.0,
            "fitness_status": "良好",
        }
        mock_context.analytics.get_heart_rate_zones.return_value = None
        mock_context.analytics.get_vdot_trend.return_value = []

        result = generator.generate_report(
            report_type=ReportType.TRAINING_CYCLE,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31),
            age=30,
        )

        assert result.success is True
        assert result.report_type == "training_cycle"

    def test_calculate_total_tss_with_data(self, generator, mock_context):
        """测试计算总TSS"""
        mock_df = pl.DataFrame(
            {
                "timestamp": [datetime(2024, 1, 1)],
                "total_distance": [5000.0],
                "total_timer_time": [1800.0],
                "avg_heart_rate": [150],
            }
        )
        mock_context.storage.read_parquet.return_value = mock_df.lazy()
        mock_context.analytics.calculate_tss_for_run.return_value = 100.0

        from src.core.report_generator import ReportConfig

        config = ReportConfig(
            report_type=ReportType.WEEKLY,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 7),
            age=30,
            rest_hr=60,
        )

        tss = generator._calculate_total_tss(config)

        assert tss >= 0

    def test_save_report_to_file(self, generator, mock_context, tmp_path):
        """测试保存报告到文件"""
        mock_context.config.base_dir = tmp_path

        result = generator.save_report(
            report_content="# Test Report",
            report_type=ReportType.WEEKLY,
        )

        assert result["success"] is True
        assert "file_path" in result

    def test_determine_cycle_type(self, generator):
        """测试确定周期类型"""
        assert generator._determine_cycle_type(5) == "小周期"
        assert generator._determine_cycle_type(14) == "中周期"
        assert generator._determine_cycle_type(30) == "大周期"
        assert generator._determine_cycle_type(60) == "长周期"

    def test_generate_cycle_evaluation(self, generator):
        """测试生成周期评估"""
        report_data = {
            "ctl": 60.0,
            "tsb": 10.0,
            "total_tss": 400.0,
            "total_runs": 5,
        }

        evaluation = generator._generate_cycle_evaluation(report_data)

        assert len(evaluation) > 0
        assert "体能" in evaluation or "训练" in evaluation

    def test_generate_next_cycle_advice(self, generator):
        """测试生成下一周期建议"""
        report_data = {
            "tsb": 5.0,
            "ctl": 40.0,
            "fitness_status": "良好",
        }

        advice = generator._generate_next_cycle_advice(report_data, "中周期")

        assert len(advice) > 0
