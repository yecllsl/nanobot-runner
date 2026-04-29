# v0.10.0 依赖注入单元测试
# 覆盖 AppContext 扩展属性 + AppContextFactory 创建逻辑

from unittest.mock import MagicMock, patch

from src.core.base.context import (
    get_context,
    reset_context,
    set_context,
)
from src.core.plan.plan_execution_repository import PlanExecutionRepository
from src.core.plan.training_response_analyzer import TrainingResponseAnalyzer
from tests.conftest import create_mock_context


class TestAppContextPlanExecutionExtensions:
    """AppContext v0.10.0 扩展属性测试"""

    def test_plan_execution_repo_lazy_init(self):
        """测试 plan_execution_repo 延迟初始化"""
        context = create_mock_context()

        repo = context.plan_execution_repo
        assert repo is not None
        assert isinstance(repo, PlanExecutionRepository)

    def test_plan_execution_repo_cached(self):
        """测试 plan_execution_repo 缓存机制"""
        context = create_mock_context()

        repo1 = context.plan_execution_repo
        repo2 = context.plan_execution_repo
        assert repo1 is repo2

    def test_plan_execution_repo_stored_in_extensions(self):
        """测试 plan_execution_repo 存储在扩展字典中"""
        context = create_mock_context()

        repo = context.plan_execution_repo
        assert context.get_extension("plan_execution_repo") is repo

    def test_training_response_analyzer_lazy_init(self):
        """测试 training_response_analyzer 延迟初始化"""
        context = create_mock_context()

        analyzer = context.training_response_analyzer
        assert analyzer is not None
        assert isinstance(analyzer, TrainingResponseAnalyzer)

    def test_training_response_analyzer_cached(self):
        """测试 training_response_analyzer 缓存机制"""
        context = create_mock_context()

        analyzer1 = context.training_response_analyzer
        analyzer2 = context.training_response_analyzer
        assert analyzer1 is analyzer2

    def test_training_response_analyzer_stored_in_extensions(self):
        """测试 training_response_analyzer 存储在扩展字典中"""
        context = create_mock_context()

        analyzer = context.training_response_analyzer
        assert context.get_extension("training_response_analyzer") is analyzer

    def test_custom_plan_execution_repo(self):
        """测试自定义 plan_execution_repo"""
        context = create_mock_context()
        mock_repo = MagicMock()

        context.set_extension("plan_execution_repo", mock_repo)

        assert context.plan_execution_repo is mock_repo

    def test_custom_training_response_analyzer(self):
        """测试自定义 training_response_analyzer"""
        context = create_mock_context()
        mock_analyzer = MagicMock()

        context.set_extension("training_response_analyzer", mock_analyzer)

        assert context.training_response_analyzer is mock_analyzer


class TestAppContextExtensionsBase:
    """AppContext 扩展机制基础测试"""

    def test_get_extension_not_exists(self):
        """测试获取不存在的扩展"""
        context = create_mock_context()
        assert context.get_extension("nonexistent") is None

    def test_set_and_get_extension(self):
        """测试设置和获取扩展"""
        context = create_mock_context()
        mock_obj = MagicMock()

        context.set_extension("test_key", mock_obj)
        assert context.get_extension("test_key") is mock_obj

    def test_set_extension_overwrite(self):
        """测试覆盖已有扩展"""
        context = create_mock_context()
        mock_obj1 = MagicMock()
        mock_obj2 = MagicMock()

        context.set_extension("test_key", mock_obj1)
        context.set_extension("test_key", mock_obj2)
        assert context.get_extension("test_key") is mock_obj2


class TestGlobalContextPlanExecution:
    """全局上下文 v0.10.0 扩展测试"""

    def setup_method(self):
        reset_context()

    def teardown_method(self):
        reset_context()

    def test_get_context_has_plan_execution_repo(self):
        """测试全局上下文包含 plan_execution_repo"""
        with patch("src.core.storage.StorageManager"):
            context = get_context()
            assert hasattr(context, "plan_execution_repo")

    def test_get_context_has_training_response_analyzer(self):
        """测试全局上下文包含 training_response_analyzer"""
        with patch("src.core.storage.StorageManager"):
            context = get_context()
            assert hasattr(context, "training_response_analyzer")

    def test_set_context_preserves_extensions(self):
        """测试设置上下文后扩展属性可用"""
        mock_context = create_mock_context()
        mock_repo = MagicMock()
        mock_context.set_extension("plan_execution_repo", mock_repo)

        set_context(mock_context)

        assert get_context().plan_execution_repo is mock_repo

    def test_reset_context_clears_global(self):
        """测试重置上下文清除全局实例"""
        with patch("src.core.storage.StorageManager"):
            context1 = get_context()
            reset_context()
            context2 = get_context()
            assert context1 is not context2
