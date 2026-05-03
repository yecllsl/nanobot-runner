# Subagent调用链集成测试 - v0.17.0
# 验证"主Agent预查询 + 数据上下文传入"模式的完整流程

import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import polars as pl
import pytest

from src.agents.tools import RunnerTools, SpawnSubagentTool, create_tools
from src.core.analytics import AnalyticsEngine
from src.core.storage.parquet_manager import StorageManager
from tests.conftest import create_mock_context


class TestSubagentDataPreparation:
    """Subagent数据预查询集成测试"""

    def test_data_analyst_context_with_real_data(self):
        """测试数据分析Subagent使用真实数据的上下文准备"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir) / "data"
            data_dir.mkdir()

            storage = StorageManager(data_dir=data_dir)

            # 创建真实测试数据
            test_data = pl.DataFrame(
                {
                    "activity_id": ["test_001", "test_002", "test_003"],
                    "timestamp": [
                        datetime(2024, 1, 1),
                        datetime(2024, 1, 8),
                        datetime(2024, 1, 15),
                    ],
                    "session_start_time": [
                        datetime(2024, 1, 1, 6, 0),
                        datetime(2024, 1, 8, 6, 0),
                        datetime(2024, 1, 15, 6, 0),
                    ],
                    "session_total_distance": [5000.0, 10000.0, 8000.0],
                    "session_total_timer_time": [1800, 3600, 2880],
                    "session_avg_heart_rate": [140, 150, 145],
                }
            )
            storage.save_to_parquet(test_data, 2024)

            analytics = AnalyticsEngine(storage)
            context = create_mock_context(storage=storage, analytics=analytics)
            tools = RunnerTools(context=context)

            # 预查询数据分析上下文
            context_data = tools._prepare_subagent_context(
                subagent_type="data_analyst",
                user_request="分析我的VDOT趋势",
            )

            # 验证上下文包含预期数据
            assert "vdot_trend" in context_data
            assert "training_load" in context_data
            assert "hr_drift" in context_data
            assert "recent_runs" in context_data
            assert context_data["user_request"] == "分析我的VDOT趋势"

            # 验证VDOT趋势数据
            vdot_trend = context_data["vdot_trend"]
            assert isinstance(vdot_trend, list)
            if len(vdot_trend) > 0:
                assert "vdot" in vdot_trend[0]
                assert isinstance(vdot_trend[0]["vdot"], (int, float))

    def test_report_writer_context_with_date_range(self):
        """测试报告撰写Subagent带日期范围的上下文准备"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir) / "data"
            data_dir.mkdir()

            storage = StorageManager(data_dir=data_dir)

            # 创建跨月份的测试数据
            test_data = pl.DataFrame(
                {
                    "activity_id": ["test_001", "test_002"],
                    "timestamp": [
                        datetime(2024, 1, 10),
                        datetime(2024, 1, 20),
                    ],
                    "session_start_time": [
                        datetime(2024, 1, 10, 6, 0),
                        datetime(2024, 1, 20, 6, 0),
                    ],
                    "session_total_distance": [5000.0, 10000.0],
                    "session_total_timer_time": [1800, 3600],
                    "session_avg_heart_rate": [140, 150],
                }
            )
            storage.save_to_parquet(test_data, 2024)

            analytics = AnalyticsEngine(storage)
            context = create_mock_context(storage=storage, analytics=analytics)
            tools = RunnerTools(context=context)

            # 预查询报告撰写上下文（带日期范围）
            context_data = tools._prepare_subagent_context(
                subagent_type="report_writer",
                user_request="生成1月训练报告",
                date_range="2024-01-01 ~ 2024-01-31",
                report_type="monthly",
            )

            # 验证上下文包含预期数据
            assert "runs_in_range" in context_data
            assert "running_stats" in context_data
            assert "vdot_trend" in context_data
            assert "training_load" in context_data
            assert context_data["report_type"] == "monthly"

    def test_report_writer_context_without_date_range(self):
        """测试报告撰写Subagent不带日期范围的上下文准备"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir) / "data"
            data_dir.mkdir()

            storage = StorageManager(data_dir=data_dir)

            test_data = pl.DataFrame(
                {
                    "activity_id": ["test_001"],
                    "timestamp": [datetime(2024, 1, 1)],
                    "session_start_time": [datetime(2024, 1, 1, 6, 0)],
                    "session_total_distance": [5000.0],
                    "session_total_timer_time": [1800],
                    "session_avg_heart_rate": [140],
                }
            )
            storage.save_to_parquet(test_data, 2024)

            analytics = AnalyticsEngine(storage)
            context = create_mock_context(storage=storage, analytics=analytics)
            tools = RunnerTools(context=context)

            # 预查询报告撰写上下文（不带日期范围）
            context_data = tools._prepare_subagent_context(
                subagent_type="report_writer",
                user_request="生成训练总结",
            )

            # 不带日期范围时应使用最近跑步记录
            assert "recent_runs" in context_data
            assert "running_stats" in context_data
            assert context_data["report_type"] == "summary"


class TestSubagentTaskAssembly:
    """Subagent任务参数组装集成测试"""

    def test_task_format_compliance(self):
        """测试task参数格式符合规范"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir) / "data"
            data_dir.mkdir()

            storage = StorageManager(data_dir=data_dir)
            context = create_mock_context(storage=storage)
            tools = RunnerTools(context=context)

            context_data = {
                "vdot_trend": [{"date": "2024-01-01", "vdot": 45.0}],
                "user_request": "分析VDOT趋势",
            }

            task = tools._build_subagent_task(
                user_request="分析VDOT趋势",
                context_data=context_data,
            )

            # 验证格式：{user_request}\n---数据上下文---\n{serialized_data}\n---数据上下文结束---
            assert "分析VDOT趋势" in task
            assert SpawnSubagentTool.CONTEXT_SEPARATOR in task
            assert SpawnSubagentTool.CONTEXT_END in task

            # 验证数据上下文部分可以解析为JSON
            parts = task.split(SpawnSubagentTool.CONTEXT_SEPARATOR)
            assert len(parts) == 2

            data_part = parts[1].replace(SpawnSubagentTool.CONTEXT_END, "")
            parsed_data = json.loads(data_part)
            assert parsed_data["vdot_trend"][0]["vdot"] == 45.0

    def test_task_with_special_characters(self):
        """测试task参数包含特殊字符的处理"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir) / "data"
            data_dir.mkdir()

            storage = StorageManager(data_dir=data_dir)
            context = create_mock_context(storage=storage)
            tools = RunnerTools(context=context)

            # 用户请求包含特殊字符
            user_request = "分析我的训练数据，包括：心率、配速、步频"
            context_data = {
                "recent_runs": [{"note": "包含\n换行\t制表符"}],
                "user_request": user_request,
            }

            task = tools._build_subagent_task(
                user_request=user_request,
                context_data=context_data,
            )

            # 验证task可以被正确解析
            parts = task.split(SpawnSubagentTool.CONTEXT_SEPARATOR)
            assert len(parts) == 2
            assert user_request in parts[0]


class TestSubagentContextSizeControl:
    """Subagent数据上下文大小控制集成测试"""

    def test_context_size_within_limit(self):
        """测试正常数据上下文大小在限制范围内"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir) / "data"
            data_dir.mkdir()

            storage = StorageManager(data_dir=data_dir)

            # 创建少量测试数据
            test_data = pl.DataFrame(
                {
                    "activity_id": ["test_001"],
                    "timestamp": [datetime(2024, 1, 1)],
                    "session_start_time": [datetime(2024, 1, 1, 6, 0)],
                    "session_total_distance": [5000.0],
                    "session_total_timer_time": [1800],
                }
            )
            storage.save_to_parquet(test_data, 2024)

            analytics = AnalyticsEngine(storage)
            context = create_mock_context(storage=storage, analytics=analytics)
            tools = RunnerTools(context=context)

            result = tools.spawn_subagent(
                subagent_type="data_analyst",
                user_request="分析VDOT趋势",
            )

            assert result["success"] is True
            assert (
                result["data"]["context_size"] <= SpawnSubagentTool.MAX_CONTEXT_LENGTH
            )

    def test_context_truncation_for_large_data(self):
        """测试大量数据时上下文截断功能"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir) / "data"
            data_dir.mkdir()

            storage = StorageManager(data_dir=data_dir)

            # 创建大量测试数据（超过8000字符限制）
            num_records = 200
            test_data = pl.DataFrame(
                {
                    "activity_id": [f"test_{i:03d}" for i in range(num_records)],
                    "timestamp": [datetime(2024, 1, 1) for _ in range(num_records)],
                    "session_start_time": [
                        datetime(2024, 1, 1, 6, 0) for _ in range(num_records)
                    ],
                    "session_total_distance": [
                        float(5000 + i * 100) for i in range(num_records)
                    ],
                    "session_total_timer_time": [1800 for _ in range(num_records)],
                    "session_avg_heart_rate": [140 for _ in range(num_records)],
                }
            )
            storage.save_to_parquet(test_data, 2024)

            analytics = AnalyticsEngine(storage)
            context = create_mock_context(storage=storage, analytics=analytics)
            tools = RunnerTools(context=context)

            result = tools.spawn_subagent(
                subagent_type="data_analyst",
                user_request="分析所有跑步记录的VDOT趋势和训练负荷变化",
            )

            assert result["success"] is True
            assert (
                result["data"]["context_size"] <= SpawnSubagentTool.MAX_CONTEXT_LENGTH
            )
            # 验证截断后的上下文仍然包含用户请求
            task_preview = result["data"]["task_preview"]
            assert "分析所有跑步记录" in task_preview


class TestSubagentInvocation:
    """Subagent调用集成测试"""

    def test_data_analyst_invocation(self):
        """测试数据分析Subagent调用"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir) / "data"
            data_dir.mkdir()

            storage = StorageManager(data_dir=data_dir)

            test_data = pl.DataFrame(
                {
                    "activity_id": ["test_001"],
                    "timestamp": [datetime(2024, 1, 1)],
                    "session_start_time": [datetime(2024, 1, 1, 6, 0)],
                    "session_total_distance": [5000.0],
                    "session_total_timer_time": [1800],
                }
            )
            storage.save_to_parquet(test_data, 2024)

            analytics = AnalyticsEngine(storage)
            context = create_mock_context(storage=storage, analytics=analytics)
            tools = RunnerTools(context=context)

            result = tools.spawn_subagent(
                subagent_type="data_analyst",
                user_request="分析我的VDOT趋势",
            )

            assert result["success"] is True
            assert result["data"]["subagent_type"] == "data_analyst"
            assert "result" in result["data"]
            assert result["data"]["result"]["status"] == "ready_to_spawn"
            assert result["data"]["result"]["label"] == "data_analyst"

    def test_report_writer_invocation(self):
        """测试报告撰写Subagent调用"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir) / "data"
            data_dir.mkdir()

            storage = StorageManager(data_dir=data_dir)

            test_data = pl.DataFrame(
                {
                    "activity_id": ["test_001"],
                    "timestamp": [datetime(2024, 1, 1)],
                    "session_start_time": [datetime(2024, 1, 1, 6, 0)],
                    "session_total_distance": [5000.0],
                    "session_total_timer_time": [1800],
                }
            )
            storage.save_to_parquet(test_data, 2024)

            analytics = AnalyticsEngine(storage)
            context = create_mock_context(storage=storage, analytics=analytics)
            tools = RunnerTools(context=context)

            result = tools.spawn_subagent(
                subagent_type="report_writer",
                user_request="生成本周训练报告",
                report_type="weekly",
            )

            assert result["success"] is True
            assert result["data"]["subagent_type"] == "report_writer"
            assert result["data"]["result"]["status"] == "ready_to_spawn"

    def test_invalid_subagent_type(self):
        """测试无效Subagent类型的处理"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir) / "data"
            data_dir.mkdir()

            storage = StorageManager(data_dir=data_dir)
            context = create_mock_context(storage=storage)
            tools = RunnerTools(context=context)

            result = tools.spawn_subagent(
                subagent_type="invalid_type",
                user_request="测试请求",
            )

            assert result["success"] is True
            assert result["data"]["result"]["status"] == "error"
            assert "不支持的Subagent类型" in result["data"]["result"]["error"]


class TestSubagentToolRegistration:
    """Subagent工具注册集成测试"""

    def test_spawn_subagent_in_tools_list(self):
        """测试spawn_subagent工具在工具列表中"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir) / "data"
            data_dir.mkdir()

            storage = StorageManager(data_dir=data_dir)
            context = create_mock_context(storage=storage)
            tools = RunnerTools(context=context)

            tool_list = create_tools(tools)
            tool_names = [t.name for t in tool_list]

            assert "spawn_subagent" in tool_names

    def test_spawn_subagent_schema(self):
        """测试spawn_subagent工具的schema格式"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir) / "data"
            data_dir.mkdir()

            storage = StorageManager(data_dir=data_dir)
            context = create_mock_context(storage=storage)
            tools = RunnerTools(context=context)

            tool_list = create_tools(tools)
            spawn_tool = next(t for t in tool_list if t.name == "spawn_subagent")

            schema = spawn_tool.to_schema()
            assert schema["type"] == "function"
            assert schema["function"]["name"] == "spawn_subagent"
            assert "subagent_type" in schema["function"]["parameters"]["properties"]
            assert "user_request" in schema["function"]["parameters"]["properties"]

    @pytest.mark.anyio
    async def test_spawn_subagent_tool_execution(self):
        """测试spawn_subagent工具的执行"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir) / "data"
            data_dir.mkdir()

            storage = StorageManager(data_dir=data_dir)

            test_data = pl.DataFrame(
                {
                    "activity_id": ["test_001"],
                    "timestamp": [datetime(2024, 1, 1)],
                    "session_start_time": [datetime(2024, 1, 1, 6, 0)],
                    "session_total_distance": [5000.0],
                    "session_total_timer_time": [1800],
                }
            )
            storage.save_to_parquet(test_data, 2024)

            analytics = AnalyticsEngine(storage)
            context = create_mock_context(storage=storage, analytics=analytics)
            tools = RunnerTools(context=context)

            tool_list = create_tools(tools)
            spawn_tool = next(t for t in tool_list if t.name == "spawn_subagent")

            result = await spawn_tool.execute(
                subagent_type="data_analyst",
                user_request="分析VDOT趋势",
            )

            result_dict = json.loads(result)
            assert result_dict["success"] is True
            assert result_dict["data"]["subagent_type"] == "data_analyst"


class TestSubagentFallback:
    """Subagent降级处理集成测试"""

    def test_fallback_on_invoke_failure(self):
        """测试Subagent调用失败时的降级处理"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir) / "data"
            data_dir.mkdir()

            storage = StorageManager(data_dir=data_dir)

            test_data = pl.DataFrame(
                {
                    "activity_id": ["test_001"],
                    "timestamp": [datetime(2024, 1, 1)],
                    "session_start_time": [datetime(2024, 1, 1, 6, 0)],
                    "session_total_distance": [5000.0],
                    "session_total_timer_time": [1800],
                }
            )
            storage.save_to_parquet(test_data, 2024)

            analytics = AnalyticsEngine(storage)
            context = create_mock_context(storage=storage, analytics=analytics)
            tools = RunnerTools(context=context)

            # 模拟 _invoke_subagent 失败
            with patch.object(
                tools, "_invoke_subagent", side_effect=Exception("调用失败")
            ):
                result = tools.spawn_subagent(
                    subagent_type="data_analyst",
                    user_request="分析VDOT趋势",
                )

                assert result["success"] is False
                assert "error" in result
                assert "fallback_result" in result
                assert result["fallback_result"]["type"] == "fallback"

    def test_fallback_data_availability(self):
        """测试降级时返回的数据可用性"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir) / "data"
            data_dir.mkdir()

            storage = StorageManager(data_dir=data_dir)

            test_data = pl.DataFrame(
                {
                    "activity_id": ["test_001"],
                    "timestamp": [datetime(2024, 1, 1)],
                    "session_start_time": [datetime(2024, 1, 1, 6, 0)],
                    "session_total_distance": [5000.0],
                    "session_total_timer_time": [1800],
                }
            )
            storage.save_to_parquet(test_data, 2024)

            analytics = AnalyticsEngine(storage)
            context = create_mock_context(storage=storage, analytics=analytics)
            tools = RunnerTools(context=context)

            fallback = tools._prepare_fallback_response(
                subagent_type="data_analyst",
                user_request="分析VDOT趋势",
            )

            assert fallback["type"] == "fallback"
            assert fallback["subagent_type"] == "data_analyst"
            assert "data" in fallback
            assert "message" in fallback
            # 验证降级数据中包含预查询数据
            assert "vdot_trend" in fallback["data"] or "error" in fallback["data"]


class TestSubagentEndToEnd:
    """Subagent端到端集成测试"""

    def test_full_data_analyst_workflow(self):
        """测试完整的数据分析Subagent工作流"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir) / "data"
            data_dir.mkdir()

            storage = StorageManager(data_dir=data_dir)

            # 创建多周训练数据
            test_data = pl.DataFrame(
                {
                    "activity_id": [f"run_{i:03d}" for i in range(10)],
                    "timestamp": [datetime(2024, 1, i + 1) for i in range(10)],
                    "session_start_time": [
                        datetime(2024, 1, i + 1, 6, 0) for i in range(10)
                    ],
                    "session_total_distance": [5000.0 + i * 500 for i in range(10)],
                    "session_total_timer_time": [1800 + i * 60 for i in range(10)],
                    "session_avg_heart_rate": [140 + i * 2 for i in range(10)],
                }
            )
            storage.save_to_parquet(test_data, 2024)

            analytics = AnalyticsEngine(storage)
            context = create_mock_context(storage=storage, analytics=analytics)
            tools = RunnerTools(context=context)

            # 执行完整的Subagent调用流程
            result = tools.spawn_subagent(
                subagent_type="data_analyst",
                user_request="分析我最近的训练趋势，包括VDOT变化、训练负荷和心率漂移",
            )

            # 验证结果结构
            assert result["success"] is True
            assert "data" in result
            assert "subagent_type" in result["data"]
            assert "result" in result["data"]
            assert "context_size" in result["data"]
            assert "task_preview" in result["data"]

            # 验证Subagent结果
            subagent_result = result["data"]["result"]
            assert subagent_result["status"] == "ready_to_spawn"
            assert subagent_result["subagent_type"] == "data_analyst"

            # 验证task参数包含完整的数据上下文
            task = subagent_result["task"]
            assert SpawnSubagentTool.CONTEXT_SEPARATOR in task
            assert SpawnSubagentTool.CONTEXT_END in task
            assert "分析我最近的训练趋势" in task

            # 验证上下文大小在限制内
            assert (
                result["data"]["context_size"] <= SpawnSubagentTool.MAX_CONTEXT_LENGTH
            )

    def test_full_report_writer_workflow(self):
        """测试完整的报告撰写Subagent工作流"""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir) / "data"
            data_dir.mkdir()

            storage = StorageManager(data_dir=data_dir)

            # 创建月度训练数据
            test_data = pl.DataFrame(
                {
                    "activity_id": [f"run_{i:03d}" for i in range(15)],
                    "timestamp": [datetime(2024, 1, i + 1) for i in range(15)],
                    "session_start_time": [
                        datetime(2024, 1, i + 1, 6, 0) for i in range(15)
                    ],
                    "session_total_distance": [
                        8000.0 if i % 3 == 0 else 5000.0 for i in range(15)
                    ],
                    "session_total_timer_time": [
                        2400 if i % 3 == 0 else 1800 for i in range(15)
                    ],
                    "session_avg_heart_rate": [145 for _ in range(15)],
                }
            )
            storage.save_to_parquet(test_data, 2024)

            analytics = AnalyticsEngine(storage)
            context = create_mock_context(storage=storage, analytics=analytics)
            tools = RunnerTools(context=context)

            # 执行完整的报告撰写Subagent调用
            result = tools.spawn_subagent(
                subagent_type="report_writer",
                user_request="生成1月训练月报",
                date_range="2024-01-01 ~ 2024-01-31",
                report_type="monthly",
            )

            # 验证结果
            assert result["success"] is True
            assert result["data"]["subagent_type"] == "report_writer"

            # 验证task参数
            task = result["data"]["result"]["task"]
            assert "生成1月训练月报" in task
            assert "runs_in_range" in task or "recent_runs" in task
            assert "running_stats" in task

            # 验证上下文大小
            assert (
                result["data"]["context_size"] <= SpawnSubagentTool.MAX_CONTEXT_LENGTH
            )
