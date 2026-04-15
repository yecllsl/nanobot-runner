"""Gateway命令处理函数单元测试

测试目标：
- 验证格式化函数返回值类型为字符串
- 验证空数据处理
- 验证边界条件

测试覆盖：
- _format_stats: 训练统计格式化
- _format_recent: 最近训练格式化
- _format_vdot: VDOT趋势格式化
- _format_hr_drift: 心率漂移格式化
- _format_training_load: 训练负荷格式化
"""

import pytest

from src.cli.commands.gateway import (
    _format_hr_drift,
    _format_recent,
    _format_stats,
    _format_training_load,
    _format_vdot,
)


class TestFormatStats:
    """测试 _format_stats 函数"""

    def test_returns_string_with_valid_data(self):
        """验证正常数据返回字符串"""
        data = {
            "total_runs": 10,
            "total_distance": 50.0,
            "total_duration": 36000.0,
            "avg_distance": 5.0,
            "avg_duration": 3600.0,
        }
        result = _format_stats(data)

        assert isinstance(result, str), f"期望 str，实际 {type(result)}"
        assert "训练统计" in result
        assert "10" in result
        assert "50.00 km" in result

    def test_returns_string_with_empty_data(self):
        """验证空数据返回友好提示"""
        data = {"message": "暂无跑步数据"}
        result = _format_stats(data)

        assert isinstance(result, str)
        assert "暂无跑步数据" in result

    def test_handles_zero_values(self):
        """验证零值处理"""
        data = {
            "total_runs": 0,
            "total_distance": 0.0,
            "total_duration": 0.0,
            "avg_distance": 0.0,
            "avg_duration": 0.0,
        }
        result = _format_stats(data)

        assert isinstance(result, str)
        assert "训练统计" in result

    def test_handles_large_numbers(self):
        """验证大数值处理"""
        data = {
            "total_runs": 1000,
            "total_distance": 5000.0,
            "total_duration": 3600000.0,
            "avg_distance": 5.0,
            "avg_duration": 3600.0,
        }
        result = _format_stats(data)

        assert isinstance(result, str)
        assert "1000" in result


class TestFormatRecent:
    """测试 _format_recent 函数"""

    def test_returns_string_with_valid_data(self):
        """验证正常数据返回字符串"""
        data = [
            {
                "timestamp": "2024-01-15T08:00:00",
                "distance_km": 5.0,
                "duration": "00:25:00",
                "avg_hr": 150,
            }
        ]
        result = _format_recent(data)

        assert isinstance(result, str), f"期望 str，实际 {type(result)}"
        assert "最近训练记录" in result
        assert "2024-01-15" in result
        assert "5.00km" in result

    def test_returns_string_with_empty_list(self):
        """验证空列表返回友好提示"""
        data = []
        result = _format_recent(data)

        assert isinstance(result, str)
        assert "暂无跑步记录" in result

    def test_handles_multiple_records(self):
        """验证多条记录处理"""
        data = [
            {
                "timestamp": "2024-01-15T08:00:00",
                "distance_km": 5.0,
                "duration": "00:25:00",
                "avg_hr": 150,
            },
            {
                "timestamp": "2024-01-14T08:00:00",
                "distance_km": 10.0,
                "duration": "00:50:00",
                "avg_hr": 145,
            },
        ]
        result = _format_recent(data)

        assert isinstance(result, str)
        assert "1." in result
        assert "2." in result

    def test_handles_missing_fields(self):
        """验证缺失字段处理"""
        data = [{"timestamp": "2024-01-15T08:00:00"}]
        result = _format_recent(data)

        assert isinstance(result, str)
        assert "2024-01-15" in result


class TestFormatVdot:
    """测试 _format_vdot 函数"""

    def test_returns_string_with_valid_data(self):
        """验证正常数据返回字符串"""
        data = [
            {
                "date": "2024-01-15",
                "distance_km": 5.0,
                "duration": "00:25:00",
                "vdot": 45.2,
            }
        ]
        result = _format_vdot(data)

        assert isinstance(result, str), f"期望 str，实际 {type(result)}"
        assert "VDOT趋势" in result
        assert "2024-01-15" in result
        assert "45.2" in result

    def test_returns_string_with_empty_list(self):
        """验证空列表返回友好提示"""
        data = []
        result = _format_vdot(data)

        assert isinstance(result, str)
        assert "暂无VDOT数据" in result

    def test_handles_multiple_records(self):
        """验证多条记录处理"""
        data = [
            {
                "date": "2024-01-15",
                "distance_km": 5.0,
                "duration": "00:25:00",
                "vdot": 45.2,
            },
            {
                "date": "2024-01-14",
                "distance_km": 10.0,
                "duration": "00:50:00",
                "vdot": 46.0,
            },
        ]
        result = _format_vdot(data)

        assert isinstance(result, str)
        assert "45.2" in result
        assert "46.0" in result


class TestFormatHrDrift:
    """测试 _format_hr_drift 函数"""

    def test_returns_string_with_valid_data(self):
        """验证正常数据返回字符串"""
        data = {
            "correlation": -0.65,
            "is_hr_drift": False,
            "avg_hr": 150.0,
            "hr_range": [140.0, 160.0],
        }
        result = _format_hr_drift(data)

        assert isinstance(result, str), f"期望 str，实际 {type(result)}"
        assert "心率漂移分析" in result
        assert "心率稳定" in result
        assert "-0.650" in result

    def test_returns_string_with_error(self):
        """验证错误数据返回错误信息"""
        data = {"error": "暂无心率数据"}
        result = _format_hr_drift(data)

        assert isinstance(result, str)
        assert "暂无心率数据" in result

    def test_handles_drift_detected(self):
        """验证心率漂移检测"""
        data = {
            "correlation": -0.75,
            "is_hr_drift": True,
            "avg_hr": 160.0,
            "hr_range": [140.0, 180.0],
        }
        result = _format_hr_drift(data)

        assert isinstance(result, str)
        assert "存在心率漂移" in result

    def test_handles_boundary_values(self):
        """验证边界值处理"""
        data = {
            "correlation": -0.7,
            "is_hr_drift": False,
            "avg_hr": 150.0,
            "hr_range": [145.0, 155.0],
        }
        result = _format_hr_drift(data)

        assert isinstance(result, str)
        assert "心率漂移分析" in result


class TestFormatTrainingLoad:
    """测试 _format_training_load 函数"""

    def test_returns_string_with_valid_data(self):
        """验证正常数据返回字符串"""
        data = {
            "atl": 50.0,
            "ctl": 65.0,
            "tsb": 15.0,
        }
        result = _format_training_load(data)

        assert isinstance(result, str), f"期望 str，实际 {type(result)}"
        assert "训练负荷" in result
        assert "ATL" in result
        assert "50.0" in result
        assert "CTL" in result
        assert "65.0" in result

    def test_returns_string_with_error(self):
        """验证错误数据返回错误信息"""
        data = {"error": "暂无训练数据"}
        result = _format_training_load(data)

        assert isinstance(result, str)
        assert "暂无训练数据" in result

    def test_handles_positive_tsb(self):
        """验证正 TSB 显示体能充沛"""
        data = {"atl": 40.0, "ctl": 60.0, "tsb": 20.0}
        result = _format_training_load(data)

        assert isinstance(result, str)
        assert "体能充沛" in result

    def test_handles_negative_tsb(self):
        """验证负 TSB 显示需要休息"""
        data = {"atl": 70.0, "ctl": 50.0, "tsb": -20.0}
        result = _format_training_load(data)

        assert isinstance(result, str)
        assert "需要休息" in result

    def test_handles_balanced_tsb(self):
        """验证平衡 TSB 显示"""
        data = {"atl": 55.0, "ctl": 60.0, "tsb": 5.0}
        result = _format_training_load(data)

        assert isinstance(result, str)
        assert "训练平衡" in result


class TestTypeContract:
    """类型契约测试 - 确保所有格式化函数返回字符串"""

    @pytest.mark.parametrize(
        "func,data",
        [
            (
                _format_stats,
                {
                    "total_runs": 1,
                    "total_distance": 1.0,
                    "total_duration": 600.0,
                    "avg_distance": 1.0,
                    "avg_duration": 600.0,
                },
            ),
            (
                _format_recent,
                [
                    {
                        "timestamp": "2024-01-15",
                        "distance_km": 1.0,
                        "duration": "00:10:00",
                        "avg_hr": 150,
                    }
                ],
            ),
            (
                _format_vdot,
                [
                    {
                        "date": "2024-01-15",
                        "distance_km": 1.0,
                        "duration": "00:10:00",
                        "vdot": 40.0,
                    }
                ],
            ),
            (
                _format_hr_drift,
                {
                    "correlation": -0.5,
                    "is_hr_drift": False,
                    "avg_hr": 150.0,
                    "hr_range": [140.0, 160.0],
                },
            ),
            (_format_training_load, {"atl": 50.0, "ctl": 60.0, "tsb": 10.0}),
        ],
    )
    def test_all_format_functions_return_string(self, func, data):
        """验证所有格式化函数返回字符串类型"""
        result = func(data)
        assert isinstance(result, str), (
            f"{func.__name__} 应返回 str，实际返回 {type(result)}"
        )
