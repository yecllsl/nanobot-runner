# Agent 工具集单元测试 - T009 新增工具

from unittest.mock import MagicMock, patch

import pytest

from src.agents.tools import (
    TOOL_DESCRIPTIONS,
    BaseTool,
    CalculateVdotForRunTool,
    GetHrDriftAnalysisTool,
    GetRecentRunsTool,
    GetRunningStatsTool,
    GetTrainingLoadTool,
    GetVdotTrendTool,
    QueryByDateRangeTool,
    QueryByDistanceTool,
    RunnerTools,
    UpdateMemoryTool,
    create_tools,
)


class TestUpdateMemoryTool:
    """UpdateMemoryTool 测试"""

    def test_name(self):
        """测试工具名称"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = UpdateMemoryTool(runner_tools)
            assert tool.name == "update_memory"

    def test_description(self):
        """测试工具描述"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = UpdateMemoryTool(runner_tools)
            assert "记忆" in tool.description or "Memory" in tool.description

    def test_parameters(self):
        """测试参数定义"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = UpdateMemoryTool(runner_tools)
            assert tool.parameters["type"] == "object"
            assert "note" in tool.parameters["properties"]
            assert "category" in tool.parameters["properties"]
            assert "note" in tool.parameters["required"]
            assert "category" not in tool.parameters.get("required", [])

    def test_parameters_category_enum(self):
        """测试分类参数枚举值"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = UpdateMemoryTool(runner_tools)
            category_schema = tool.parameters["properties"]["category"]
            assert "enum" in category_schema
            assert category_schema["enum"] == [
                "training",
                "preference",
                "injury",
                "other",
            ]
            assert category_schema.get("default") == "other"

    @pytest.mark.anyio
    async def test_execute_success(self):
        """测试执行成功"""
        with patch("src.core.storage.StorageManager"):
            with patch("src.agents.tools.ProfileStorageManager") as MockProfileStorage:
                mock_profile_storage = MagicMock()
                MockProfileStorage.return_value = mock_profile_storage
                mock_profile_storage.save_memory_md.return_value = True

                runner_tools = RunnerTools()
                tool = UpdateMemoryTool(runner_tools)

                result = await tool.execute(note="测试笔记", category="training")

                # 新返回格式：成功时直接返回数据，失败时返回 {"error": ...}
                assert "error" not in result or "成功" in result

    @pytest.mark.anyio
    async def test_execute_empty_note(self):
        """测试空笔记内容"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = UpdateMemoryTool(runner_tools)

            result = await tool.execute(note="")

            assert "error" in result
            assert "空" in result

    @pytest.mark.anyio
    async def test_execute_invalid_category(self):
        """测试无效分类"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = UpdateMemoryTool(runner_tools)

            result = await tool.execute(note="测试", category="invalid")

            assert "error" in result
            assert "无效" in result or "invalid" in result

    @pytest.mark.anyio
    async def test_execute_default_category(self):
        """测试默认分类"""
        with patch("src.core.storage.StorageManager"):
            with patch("src.agents.tools.ProfileStorageManager") as MockProfileStorage:
                mock_profile_storage = MagicMock()
                MockProfileStorage.return_value = mock_profile_storage
                mock_profile_storage.save_memory_md.return_value = True

                runner_tools = RunnerTools()
                tool = UpdateMemoryTool(runner_tools)

                result = await tool.execute(note="测试笔记")

                assert isinstance(result, str)

    @pytest.mark.anyio
    async def test_execute_save_failure(self):
        """测试保存失败"""
        with patch("src.core.storage.StorageManager"):
            with patch("src.agents.tools.ProfileStorageManager") as MockProfileStorage:
                mock_profile_storage = MagicMock()
                MockProfileStorage.return_value = mock_profile_storage
                mock_profile_storage.save_memory_md.return_value = False

                runner_tools = RunnerTools()
                tool = UpdateMemoryTool(runner_tools)

                result = await tool.execute(note="测试笔记")

                assert "error" in result


class TestCreateTools:
    """create_tools 函数测试 - 扩展"""

    def test_create_tools_count(self):
        """测试工具数量（新增后应为 10 个）"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tools = create_tools(runner_tools)

            assert isinstance(tools, list)
            assert len(tools) == 10

    def test_create_tools_contains_update_memory(self):
        """测试包含 UpdateMemoryTool"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tools = create_tools(runner_tools)

            tool_names = [t.name for t in tools]
            assert "update_memory" in tool_names

    def test_create_tools_all_tool_names(self):
        """测试所有工具名称"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tools = create_tools(runner_tools)

            expected_names = [
                "get_running_stats",
                "get_recent_runs",
                "calculate_vdot_for_run",
                "get_vdot_trend",
                "get_hr_drift_analysis",
                "get_training_load",
                "query_by_date_range",
                "query_by_distance",
                "update_memory",
            ]

            tool_names = [t.name for t in tools]
            for expected_name in expected_names:
                assert expected_name in tool_names


class TestToolDescriptions:
    """TOOL_DESCRIPTIONS 测试 - 扩展"""

    def test_update_memory_in_descriptions(self):
        """测试 update_memory 在描述字典中"""
        assert "update_memory" in TOOL_DESCRIPTIONS

    def test_update_memory_has_description(self):
        """测试 update_memory 有 description 字段"""
        assert "description" in TOOL_DESCRIPTIONS["update_memory"]

    def test_update_memory_has_parameters(self):
        """测试 update_memory 有 parameters 字段"""
        assert "parameters" in TOOL_DESCRIPTIONS["update_memory"]

    def test_update_memory_parameters(self):
        """测试 update_memory 参数定义"""
        update_memory_desc = TOOL_DESCRIPTIONS["update_memory"]
        params = update_memory_desc["parameters"]
        assert "note" in params
        assert "category" in params

    def test_all_tools_have_descriptions(self):
        """测试所有工具都有描述"""
        expected_tools = [
            "get_running_stats",
            "get_recent_runs",
            "calculate_vdot_for_run",
            "get_vdot_trend",
            "get_hr_drift_analysis",
            "get_training_load",
            "query_by_date_range",
            "query_by_distance",
            "update_memory",
        ]

        for tool_name in expected_tools:
            assert tool_name in TOOL_DESCRIPTIONS
            assert "description" in TOOL_DESCRIPTIONS[tool_name]


class TestRunnerToolsUpdateMemory:
    """RunnerTools.update_memory 方法测试"""

    def test_update_memory_success(self):
        """测试更新记忆成功"""
        with patch("src.core.storage.StorageManager"):
            with patch("src.agents.tools.ProfileStorageManager") as MockProfileStorage:
                mock_profile_storage = MagicMock()
                MockProfileStorage.return_value = mock_profile_storage
                mock_profile_storage.save_memory_md.return_value = True

                runner_tools = RunnerTools()
                result = runner_tools.update_memory("测试笔记", "training")

                assert result["success"] is True
                assert "message" in result
                assert "note" in result

    def test_update_memory_empty_note(self):
        """测试空笔记"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            result = runner_tools.update_memory("")

            assert "error" in result
            assert "空" in result["error"]

    def test_update_memory_whitespace_note(self):
        """测试空白字符笔记"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            result = runner_tools.update_memory("   ")

            assert "error" in result

    def test_update_memory_invalid_category(self):
        """测试无效分类"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            result = runner_tools.update_memory("测试", "invalid_category")

            assert "error" in result
            assert "无效" in result["error"]

    def test_update_memory_default_category(self):
        """测试默认分类"""
        with patch("src.core.storage.StorageManager"):
            with patch("src.agents.tools.ProfileStorageManager") as MockProfileStorage:
                mock_profile_storage = MagicMock()
                MockProfileStorage.return_value = mock_profile_storage
                mock_profile_storage.save_memory_md.return_value = True

                runner_tools = RunnerTools()
                result = runner_tools.update_memory("测试笔记")

                assert result["success"] is True

    def test_update_memory_all_categories(self):
        """测试所有有效分类"""
        categories = ["training", "preference", "injury", "other"]

        for category in categories:
            with patch("src.core.storage.StorageManager"):
                with patch(
                    "src.agents.tools.ProfileStorageManager"
                ) as MockProfileStorage:
                    mock_profile_storage = MagicMock()
                    MockProfileStorage.return_value = mock_profile_storage
                    mock_profile_storage.save_memory_md.return_value = True

                    runner_tools = RunnerTools()
                    result = runner_tools.update_memory("测试笔记", category)

                    assert result["success"] is True

    def test_update_memory_exception_handling(self):
        """测试异常处理"""
        with patch("src.core.storage.StorageManager"):
            with patch("src.agents.tools.ProfileStorageManager") as MockProfileStorage:
                mock_profile_storage = MagicMock()
                MockProfileStorage.return_value = mock_profile_storage
                mock_profile_storage.save_memory_md.side_effect = Exception("测试异常")

                runner_tools = RunnerTools()
                result = runner_tools.update_memory("测试笔记")

                assert "error" in result

    def test_update_memory_formats_note(self):
        """测试笔记格式化"""
        with patch("src.core.storage.StorageManager"):
            with patch("src.agents.tools.ProfileStorageManager") as MockProfileStorage:
                mock_profile_storage = MagicMock()
                MockProfileStorage.return_value = mock_profile_storage
                mock_profile_storage.save_memory_md.return_value = True

                runner_tools = RunnerTools()
                result = runner_tools.update_memory("测试笔记", "training")

                assert "note" in result
                assert "[训练]" in result["note"]


class TestBaseToolValidateParamsExtended:
    """BaseTool 参数验证扩展测试"""

    def test_validate_params_update_memory_required(self):
        """测试 UpdateMemoryTool 必填参数验证"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = UpdateMemoryTool(runner_tools)

            # 缺少必填参数 note
            errors = tool.validate_params({})

            assert len(errors) > 0
            assert any("missing required field" in e for e in errors)

    def test_validate_params_update_memory_valid(self):
        """测试 UpdateMemoryTool 有效参数"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = UpdateMemoryTool(runner_tools)

            errors = tool.validate_params({"note": "测试笔记", "category": "training"})

            assert len(errors) == 0

    def test_validate_params_update_memory_optional_category(self):
        """测试 UpdateMemoryTool 可选分类参数"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = UpdateMemoryTool(runner_tools)

            # 只提供 note，不提供 category
            errors = tool.validate_params({"note": "测试笔记"})

            assert len(errors) == 0


class TestUpdateMemoryToolSchema:
    """UpdateMemoryTool schema 测试"""

    def test_to_schema_format(self):
        """测试转换为 OpenAI function schema 格式"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = UpdateMemoryTool(runner_tools)

            schema = tool.to_schema()

            assert schema["type"] == "function"
            assert "function" in schema
            assert schema["function"]["name"] == "update_memory"
            assert "description" in schema["function"]
            assert "parameters" in schema["function"]

    def test_schema_parameters_structure(self):
        """测试 schema 参数结构"""
        with patch("src.core.storage.StorageManager"):
            runner_tools = RunnerTools()
            tool = UpdateMemoryTool(runner_tools)

            schema = tool.to_schema()
            params = schema["function"]["parameters"]

            assert params["type"] == "object"
            assert "properties" in params
            assert "note" in params["properties"]
            assert "category" in params["properties"]
