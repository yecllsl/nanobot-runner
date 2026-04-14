# 测试辅助函数
# 用于创建 Mock 对象和测试上下文

from unittest.mock import MagicMock

from src.core.context import AppContext


def create_mock_context(
    storage=None,
    config=None,
    indexer=None,
    parser=None,
    importer=None,
    analytics=None,
    profile_engine=None,
    profile_storage=None,
    session_repo=None,
    report_service=None,
    plan_manager=None,
) -> AppContext:
    """
    创建 Mock 应用上下文

    Args:
        storage: Mock 存储管理器（可选）
        config: Mock 配置管理器（可选）
        indexer: Mock 索引管理器（可选）
        parser: Mock 解析器（可选）
        importer: Mock 导入服务（可选）
        analytics: Mock 分析引擎（可选）
        profile_engine: Mock 用户画像引擎（可选）
        profile_storage: Mock 用户画像存储管理器（可选）
        session_repo: Mock Session数据仓储（可选）
        report_service: Mock 报告服务（可选）
        plan_manager: Mock 训练计划管理器（可选）

    Returns:
        AppContext: Mock 应用上下文
    """
    if storage is None:
        storage = MagicMock()

    if config is None:
        config = MagicMock()
        config.data_dir = MagicMock()
        config.index_file = MagicMock()

    if indexer is None:
        indexer = MagicMock()

    if parser is None:
        parser = MagicMock()

    if importer is None:
        importer = MagicMock()

    if analytics is None:
        analytics = MagicMock()

    if profile_engine is None:
        profile_engine = MagicMock()

    if profile_storage is None:
        profile_storage = MagicMock()

    if session_repo is None:
        session_repo = MagicMock()

    if report_service is None:
        report_service = MagicMock()

    if plan_manager is None:
        plan_manager = MagicMock()

    return AppContext(
        config=config,
        storage=storage,
        indexer=indexer,
        parser=parser,
        importer=importer,
        analytics=analytics,
        profile_engine=profile_engine,
        profile_storage=profile_storage,
        session_repo=session_repo,
        report_service=report_service,
        plan_manager=plan_manager,
    )
