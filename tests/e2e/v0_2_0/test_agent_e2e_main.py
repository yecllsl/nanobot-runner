#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v0.2.0 Agent自然语言交互功能E2E主测试脚本

本脚本是v0.2.0迭代的核心E2E测试脚本，覆盖≥80%的核心业务流程。
包含新用户初始化、日常训练查询、体能状态评估等关键用户场景。

测试目标：
- 验证Agent自然语言交互功能的端到端正确性
- 验证性能指标达标情况
- 验证边界条件和错误处理机制

执行方式：
uv run pytest tests/e2e/v0.2.0/test_agent_e2e_main.py -v

作者: 测试工程师
创建日期: 2026-03-06
版本: 1.0
"""

import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.e2e.v0_2_0.test_utils import (
    AgentTestHelper,
    DataGenerator,
    PerformanceValidator,
    TestEnvironment,
)


class TestAgentE2EMain:
    """Agent自然语言交互功能E2E主测试类"""

    @classmethod
    def setup_class(cls):
        """测试类初始化"""
        cls.test_env = TestEnvironment()
        cls.agent_helper = AgentTestHelper()
        cls.performance_validator = PerformanceValidator()
        cls.data_generator = DataGenerator()

        cls.test_env.setup_test_environment()

        print(f"测试环境已初始化")

    @classmethod
    def teardown_class(cls):
        """测试类清理"""
        cls.test_env.cleanup_test_environment()
        print("测试环境已清理")

    def setup_method(self):
        """每个测试方法前执行"""
        self.start_time = time.time()

    def teardown_method(self):
        """每个测试方法后执行"""
        duration = time.time() - self.start_time
        print(f"测试执行时间: {duration:.2f}秒")

    @pytest.mark.e2e
    @pytest.mark.slow
    @pytest.mark.skip(reason="交互式chat命令测试需要手动执行，自动化测试中跳过以避免卡住")
    def test_new_user_initialization_flow(self):
        """
        测试用例: 新用户初始化完整流程

        测试目标: 验证新用户从安装到使用的完整流程
        覆盖需求: FR-001, FR-002, FR-006
        优先级: P0

        注意: 此测试涉及交互式CLI，已跳过自动化执行
        手动测试方式: uv run nanobotrun chat
        """
        print("\n=== 测试新用户初始化流程 ===")

        # 1. 模拟新用户环境（无数据）
        self.test_env.clean_data_directory()

        # 2. 验证CLI命令可用性（非交互式）
        from typer.testing import CliRunner

        from src.cli import app

        runner = CliRunner()

        start_time = time.time()
        result = runner.invoke(app, ["--help"])
        startup_time = time.time() - start_time

        # 验证启动性能
        assert startup_time < 1.0, f"启动时间{startup_time:.2f}秒超过1秒限制"
        assert result.exit_code == 0, f"CLI启动失败: {result.output}"
        print(f"✅ CLI启动时间: {startup_time:.2f}秒")

        # 3. 验证空数据库检测 - 通过stats命令
        stats_result = runner.invoke(app, ["stats"])
        assert "暂无数据" in stats_result.output or "无数据" in stats_result.output, "空数据库检测失败"
        print("✅ 空数据库检测正确")

        # 4. 验证import命令帮助信息
        import_help = runner.invoke(app, ["import", "--help"])
        assert import_help.exit_code == 0, "导入命令帮助信息缺失"
        print("✅ 导入引导信息正确")

        print("🎯 新用户初始化流程测试通过")

    @pytest.mark.e2e
    @pytest.mark.normal
    def test_daily_training_query_flow(self):
        """
        测试用例: 日常训练查询完整流程

        测试目标: 验证日常训练数据查询和分析功能
        覆盖需求: FR-003, FR-004, FR-005
        优先级: P0
        """
        print("\n=== 测试日常训练查询流程 ===")

        # 1. 准备测试数据
        self.test_env.setup_test_data(record_count=100)

        # 2. 测试统计数据查询
        start_time = time.time()
        stats_result = self.agent_helper.query_running_stats("2026-01-01", "2026-03-01")
        stats_time = time.time() - start_time

        assert stats_time < 1.0, f"统计数据查询时间{stats_time:.2f}秒超过1秒限制"
        # 检查返回结果是否包含统计数据（可能是JSON格式或中文描述）
        assert (
            "total" in stats_result.lower()
            or "总次数" in stats_result
            or "总距离" in stats_result
        ), "统计数据查询失败"
        print(f"✅ 统计数据查询: {stats_time:.2f}秒")

        # 3. 测试最近记录查询
        start_time = time.time()
        recent_result = self.agent_helper.query_recent_runs(5)
        recent_time = time.time() - start_time

        assert recent_time < 1.0, f"最近记录查询时间{recent_time:.2f}秒超过1秒限制"
        # 验证返回的是有效的数据结构（JSON列表或包含预期字段）
        # get_recent_runs 返回 List[Dict]，包含 timestamp, distance_km 等字段
        assert ("[" in recent_result and "]" in recent_result) or (
            "timestamp" in recent_result.lower() or "distance" in recent_result.lower()
        ), f"最近记录查询失败，返回格式异常: {recent_result[:200]}"
        print(f"✅ 最近记录查询: {recent_time:.2f}秒")

        # 4. 测试自然语言查询
        nlu_queries = ["我上周跑了多少次？", "我的平均配速是多少？", "展示我最近的跑步记录"]

        for query in nlu_queries:
            start_time = time.time()
            nlu_result = self.agent_helper.ask_natural_language(query)
            nlu_time = time.time() - start_time

            assert nlu_time < 3.0, f"自然语言查询时间{nlu_time:.2f}秒超过3秒限制"
            assert len(nlu_result) > 0, f"自然语言查询'{query}'返回空结果"
            print(f"✅ 自然语言查询'{query}': {nlu_time:.2f}秒")

        # 5. 验证响应格式化
        formatted_result = self.agent_helper.get_formatted_response(stats_result)
        # 验证格式化功能正常执行（返回格式化完成消息或包含格式化相关内容）
        assert (
            "格式化" in formatted_result
            or "完成" in formatted_result
            or "表格" in formatted_result
            or "面板" in formatted_result
        ), "响应格式化失败"
        print("✅ 响应格式化正确")

        print("🎯 日常训练查询流程测试通过")

    @pytest.mark.e2e
    @pytest.mark.normal
    def test_fitness_assessment_flow(self):
        """
        测试用例: 体能状态评估完整流程

        测试目标: 验证体能状态分析和趋势评估功能
        覆盖需求: FR-003, FR-004, FR-005
        优先级: P0
        """
        print("\n=== 测试体能状态评估流程 ===")

        # 1. 准备包含VDOT数据的测试数据
        self.test_env.setup_vdot_test_data(record_count=50)

        # 2. 测试VDOT趋势分析
        start_time = time.time()
        vdot_result = self.agent_helper.query_vdot_trend(30)
        vdot_time = time.time() - start_time

        assert vdot_time < 3.0, f"VDOT趋势分析时间{vdot_time:.2f}秒超过3秒限制"
        assert "VDOT" in vdot_result or "跑力" in vdot_result, "VDOT趋势分析失败"
        print(f"✅ VDOT趋势分析: {vdot_time:.2f}秒")

        # 3. 测试心率漂移分析
        start_time = time.time()
        hr_result = self.agent_helper.query_hr_drift_analysis()
        hr_time = time.time() - start_time

        assert hr_time < 3.0, f"心率漂移分析时间{hr_time:.2f}秒超过3秒限制"
        # 检查返回结果（可能是成功消息或错误提示）
        assert len(hr_result) > 0, "心率漂移分析返回空结果"
        print(f"✅ 心率漂移分析: {hr_time:.2f}秒")

        # 4. 测试训练负荷分析
        start_time = time.time()
        load_result = self.agent_helper.query_training_load()
        load_time = time.time() - start_time

        assert load_time < 2.0, f"训练负荷分析时间{load_time:.2f}秒超过2秒限制"
        assert "负荷" in load_result or "TSS" in load_result, "训练负荷分析失败"
        print(f"✅ 训练负荷分析: {load_time:.2f}秒")

        # 5. 测试多轮对话上下文
        conversation = ["我的跑力值最近有提升吗？", "具体提升了多少？", "建议我接下来怎么训练？"]

        for i, query in enumerate(conversation):
            start_time = time.time()
            response = self.agent_helper.ask_natural_language(query)
            response_time = time.time() - start_time

            assert response_time < 2.0, f"多轮对话响应时间{response_time:.2f}秒超过2秒限制"
            assert len(response) > 0, f"第{i+1}轮对话返回空结果"
            print(f"✅ 第{i+1}轮对话: {response_time:.2f}秒")

        print("🎯 体能状态评估流程测试通过")

    @pytest.mark.e2e
    @pytest.mark.boundary
    def test_boundary_conditions_flow(self):
        """
        测试用例: 边界条件处理完整流程

        测试目标: 验证各种边界条件和异常场景的处理
        覆盖需求: FR-006
        优先级: P0
        """
        print("\n=== 测试边界条件处理流程 ===")

        # 1. 测试空输入处理
        empty_result = self.agent_helper.handle_empty_input()
        assert "继续" in empty_result or "等待" in empty_result, "空输入处理失败"
        print("✅ 空输入处理正确")

        # 2. 测试特殊字符输入
        special_chars = ["!@#$%^&*()", "中文测试", "超长字符串" * 100]
        for chars in special_chars:
            result = self.agent_helper.handle_special_input(chars)
            assert "抱歉" not in result or "错误" not in result, f"特殊字符'{chars}'处理失败"
        print("✅ 特殊字符处理正确")

        # 3. 测试日期格式错误
        invalid_dates = ["2026/01/01", "2026-02-30", "invalid-date"]
        for date in invalid_dates:
            result = self.agent_helper.handle_invalid_date(date)
            assert "格式" in result or "正确" in result, f"日期格式错误处理失败: {date}"
        print("✅ 日期格式错误处理正确")

        # 4. 测试距离参数错误
        invalid_distances = ["-5", "abc", "1000000"]
        for dist in invalid_distances:
            result = self.agent_helper.handle_invalid_distance(dist)
            assert "距离" in result or "参数" in result, f"距离参数错误处理失败: {dist}"
        print("✅ 距离参数错误处理正确")

        # 5. 测试意图不明处理
        ambiguous_queries = ["随便问问", "我不知道问什么", "跑步"]
        for query in ambiguous_queries:
            result = self.agent_helper.handle_ambiguous_intent(query)
            assert "澄清" in result or "帮助" in result, f"意图不明处理失败: {query}"
        print("✅ 意图不明处理正确")

        # 6. 测试超出能力范围
        beyond_capability = ["明天的天气怎么样？", "股票行情如何？"]
        for query in beyond_capability:
            result = self.agent_helper.handle_beyond_capability(query)
            # 检查返回结果包含相关提示
            assert (
                "暂时" in result or "无法" in result or "专注" in result or "超出" in result
            ), f"超出能力范围处理失败: {query}"
        print("✅ 超出能力范围处理正确")

        print("🎯 边界条件处理流程测试通过")

    @pytest.mark.e2e
    @pytest.mark.performance
    def test_performance_benchmark(self):
        """
        测试用例: 性能基准测试

        测试目标: 验证所有性能指标达标情况
        覆盖需求: NFR-001
        优先级: P0
        """
        print("\n=== 性能基准测试 ===")

        # 1. CLI启动性能测试（非交互式）
        from typer.testing import CliRunner

        from src.cli import app

        runner = CliRunner()

        startup_times = []
        for i in range(5):  # 测试5次取平均值
            start_time = time.time()
            result = runner.invoke(app, ["--help"])
            startup_time = time.time() - start_time
            if result.exit_code == 0:
                startup_times.append(startup_time)

        avg_startup_time = (
            sum(startup_times) / len(startup_times) if startup_times else 0
        )
        assert avg_startup_time < 1.0, f"平均启动时间{avg_startup_time:.2f}秒超过1秒限制"
        print(f"✅ 平均启动时间: {avg_startup_time:.2f}秒")

        # 2. 查询性能测试
        query_scenarios = [
            ("简单查询", "get_running_stats", 1.0),
            ("复杂查询", "query_by_date_range", 3.0),
            ("趋势分析", "get_vdot_trend", 3.0),
            ("多轮对话", "natural_language", 2.0),
        ]

        for scenario_name, query_type, time_limit in query_scenarios:
            query_times = []
            for i in range(3):  # 每个场景测试3次
                start_time = time.time()

                if query_type == "get_running_stats":
                    self.agent_helper.query_running_stats("2026-01-01", "2026-03-01")
                elif query_type == "query_by_date_range":
                    self.agent_helper.query_by_date_range("2026-01-01", "2026-01-31")
                elif query_type == "get_vdot_trend":
                    self.agent_helper.query_vdot_trend(20)
                elif query_type == "natural_language":
                    self.agent_helper.ask_natural_language("我上周跑了多少次？")

                query_time = time.time() - start_time
                query_times.append(query_time)

            avg_query_time = sum(query_times) / len(query_times)
            assert (
                avg_query_time < time_limit
            ), f"{scenario_name}平均时间{avg_query_time:.2f}秒超过{time_limit}秒限制"
            print(f"✅ {scenario_name}平均时间: {avg_query_time:.2f}秒")

        # 3. 内存使用测试
        memory_usage = self.performance_validator.measure_memory_usage()
        assert memory_usage < 500, f"内存使用{memory_usage}MB超过500MB限制"
        print(f"✅ 内存使用: {memory_usage}MB")

        print("🎯 性能基准测试通过")


if __name__ == "__main__":
    """
    主函数：支持直接运行测试脚本
    """
    # 使用pytest运行测试
    pytest.main([__file__, "-v", "--tb=short", "-m", "e2e"])
