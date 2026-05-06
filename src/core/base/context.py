# 应用上下文管理
# 提供依赖注入和统一的对象管理

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.core.analytics import AnalyticsEngine
from src.core.base.profile import ProfileEngine, ProfileStorageManager
from src.core.config.env_manager import EnvManager
from src.core.config.manager import ConfigManager
from src.core.plan.plan_manager import PlanManager
from src.core.report.service import ReportService
from src.core.storage.importer import ImportService
from src.core.storage.indexer import IndexManager
from src.core.storage.parquet_manager import StorageManager
from src.core.storage.parser import FitParser
from src.core.storage.session_repository import SessionRepository


@dataclass
class AppContext:
    """
    应用上下文

    集中管理所有核心组件的实例，支持依赖注入和测试。

    Attributes:
        config: 配置管理器
        storage: 存储管理器
        indexer: 索引管理器
        parser: FIT 文件解析器
        importer: 导入服务
        analytics: 分析引擎
        profile_engine: 用户画像引擎
        profile_storage: 用户画像存储管理器
        session_repo: Session数据仓储
        report_service: 报告服务
        plan_manager: 训练计划管理器
    """

    config: ConfigManager
    storage: StorageManager
    indexer: IndexManager
    parser: FitParser
    importer: ImportService
    analytics: AnalyticsEngine
    profile_engine: ProfileEngine
    profile_storage: ProfileStorageManager
    session_repo: SessionRepository
    report_service: ReportService
    plan_manager: PlanManager

    # 可选的扩展组件
    _extensions: dict = field(default_factory=dict)

    def get_extension(self, name: str) -> Any | None:
        """
        获取扩展组件

        Args:
            name: 扩展组件名称

        Returns:
            扩展组件实例，不存在则返回 None
        """
        return self._extensions.get(name)

    def set_extension(self, name: str, instance: Any) -> None:
        """
        设置扩展组件

        Args:
            name: 扩展组件名称
            instance: 扩展组件实例
        """
        self._extensions[name] = instance

    @property
    def plan_execution_repo(self) -> Any:
        """获取计划执行仓储（v0.10.0新增）"""
        from src.core.plan.plan_execution_repository import PlanExecutionRepository

        repo = self.get_extension("plan_execution_repo")
        if repo is None:
            repo = PlanExecutionRepository(self.plan_manager)
            self.set_extension("plan_execution_repo", repo)
        return repo

    @property
    def training_response_analyzer(self) -> Any:
        """获取训练响应分析器（v0.10.0新增）"""
        from src.core.plan.training_response_analyzer import TrainingResponseAnalyzer

        analyzer = self.get_extension("training_response_analyzer")
        if analyzer is None:
            analyzer = TrainingResponseAnalyzer(self.plan_execution_repo)
            self.set_extension("training_response_analyzer", analyzer)
        return analyzer

    @property
    def plan_adjustment_validator(self) -> Any:
        """获取计划调整校验器（v0.11.0新增）"""
        from src.core.plan.plan_adjustment_validator import PlanAdjustmentValidator

        validator = self.get_extension("plan_adjustment_validator")
        if validator is None:
            validator = PlanAdjustmentValidator()
            self.set_extension("plan_adjustment_validator", validator)
        return validator

    @property
    def prompt_template_engine(self) -> Any:
        """获取Prompt模板引擎（v0.11.0新增）"""
        from src.core.plan.prompt_template_engine import PromptTemplateEngine

        engine = self.get_extension("prompt_template_engine")
        if engine is None:
            engine = PromptTemplateEngine()
            self.set_extension("prompt_template_engine", engine)
        return engine

    @property
    def plan_modification_dialog_manager(self) -> Any:
        """获取计划修改对话管理器（v0.11.0新增）"""
        from src.core.plan.plan_modification_dialog import PlanModificationDialogManager

        manager = self.get_extension("plan_modification_dialog_manager")
        if manager is None:
            manager = PlanModificationDialogManager(
                validator=self.plan_adjustment_validator,
                prompt_engine=self.prompt_template_engine,
            )
            self.set_extension("plan_modification_dialog_manager", manager)
        return manager

    @property
    def goal_prediction_engine(self) -> Any:
        """获取目标预测引擎（v0.12.0新增）"""
        from src.core.plan.goal_prediction_engine import GoalPredictionEngine

        engine = self.get_extension("goal_prediction_engine")
        if engine is None:
            engine = GoalPredictionEngine()
            self.set_extension("goal_prediction_engine", engine)
        return engine

    @property
    def long_term_plan_generator(self) -> Any:
        """获取长期规划生成器（v0.12.0新增）"""
        from src.core.plan.long_term_plan_generator import LongTermPlanGenerator

        generator = self.get_extension("long_term_plan_generator")
        if generator is None:
            generator = LongTermPlanGenerator()
            self.set_extension("long_term_plan_generator", generator)
        return generator

    @property
    def smart_advice_engine(self) -> Any:
        """获取智能建议引擎（v0.12.0新增）"""
        from src.core.plan.smart_advice_engine import SmartAdviceEngine

        engine = self.get_extension("smart_advice_engine")
        if engine is None:
            engine = SmartAdviceEngine()
            self.set_extension("smart_advice_engine", engine)
        return engine

    @property
    def training_reminder_manager(self) -> Any:
        """获取训练提醒管理器（v0.17.0新增）"""
        from src.core.plan.training_reminder_manager import TrainingReminderManager

        manager = self.get_extension("training_reminder_manager")
        if manager is None:
            manager = TrainingReminderManager(data_dir=self.config.data_dir)
            self.set_extension("training_reminder_manager", manager)
        return manager

    @property
    def cron_callback_handler(self) -> Any:
        """获取Cron回调处理器（v0.17.0新增）"""
        from src.core.plan.cron_callback import CronCallbackHandler

        handler = self.get_extension("cron_callback_handler")
        if handler is None:
            handler = CronCallbackHandler(
                reminder_manager=self.training_reminder_manager,
            )
            self.set_extension("cron_callback_handler", handler)
        return handler

    @property
    def gateway_integration(self) -> Any:
        """获取Gateway集成器（v0.17.0新增）"""
        from src.core.plan.gateway_integration import GatewayIntegration

        integration = self.get_extension("gateway_integration")
        if integration is None:
            integration = GatewayIntegration(
                workspace=self.config.base_dir,
                data_dir=self.config.data_dir,
            )
            self.set_extension("gateway_integration", integration)
        return integration

    @property
    def ask_user_confirm_manager(self) -> Any:
        """获取异步确认管理器（v0.17.0新增，实验性功能）"""
        from src.core.plan.ask_user_confirm import AskUserConfirmManager

        manager = self.get_extension("ask_user_confirm_manager")
        if manager is None:
            manager = AskUserConfirmManager()
            self.set_extension("ask_user_confirm_manager", manager)
        return manager

    @property
    def chart_renderer(self) -> Any:
        """获取图表渲染器（v0.18.0新增）"""
        from src.core.visualization.plotext_renderer import PlotextRenderer

        renderer = self.get_extension("chart_renderer")
        if renderer is None:
            renderer = PlotextRenderer()
            self.set_extension("chart_renderer", renderer)
        return renderer

    @property
    def export_engine(self) -> Any:
        """获取导出引擎（v0.18.0新增）"""
        from src.core.export.engine import ExportEngine

        engine = self.get_extension("export_engine")
        if engine is None:
            engine = ExportEngine(storage=self.storage, analytics=self.analytics)
            self.set_extension("export_engine", engine)
        return engine

    @property
    def body_signal_engine(self) -> Any:
        """获取身体信号引擎（v0.19.0新增）"""
        from src.core.body_signal.body_signal_engine import BodySignalEngine
        from src.core.body_signal.fatigue_assessor import FatigueAssessor
        from src.core.body_signal.hrv_analyzer import HRVAnalyzer
        from src.core.body_signal.recovery_monitor import RecoveryMonitor
        from src.core.calculators.training_load_analyzer import TrainingLoadAnalyzer
        from src.core.config.body_signal_config import BodySignalConfig

        engine = self.get_extension("body_signal_engine")
        if engine is None:
            config = BodySignalConfig()
            training_load_analyzer = TrainingLoadAnalyzer()
            hrv_analyzer = HRVAnalyzer(session_repo=self.session_repo, config=config)
            fatigue_assessor = FatigueAssessor(
                session_repo=self.session_repo,
                training_load_analyzer=training_load_analyzer,
                config=config,
            )
            recovery_monitor = RecoveryMonitor(
                session_repo=self.session_repo,
                training_load_analyzer=training_load_analyzer,
                hrv_analyzer=hrv_analyzer,
                config=config,
            )
            engine = BodySignalEngine(
                hrv_analyzer=hrv_analyzer,
                fatigue_assessor=fatigue_assessor,
                recovery_monitor=recovery_monitor,
                advice_engine=self.smart_advice_engine,
                config=config,
            )
            self.set_extension("body_signal_engine", engine)
        return engine


class AppContextFactory:
    """
    应用上下文工厂

    负责创建和配置 AppContext 实例，支持自定义依赖注入。
    """

    @staticmethod
    def create(
        config: ConfigManager | None = None,
        storage: StorageManager | None = None,
        indexer: IndexManager | None = None,
        parser: FitParser | None = None,
        importer: ImportService | None = None,
        analytics: AnalyticsEngine | None = None,
        profile_engine: ProfileEngine | None = None,
        profile_storage: ProfileStorageManager | None = None,
        session_repo: SessionRepository | None = None,
        report_service: ReportService | None = None,
        plan_manager: PlanManager | None = None,
        allow_default: bool = False,
    ) -> AppContext:
        """
        创建应用上下文

        支持依赖注入，未提供的组件将自动创建默认实例。

        Args:
            config: 配置管理器（可选）
            storage: 存储管理器（可选）
            indexer: 索引管理器（可选）
            parser: FIT 文件解析器（可选）
            importer: 导入服务（可选）
            analytics: 分析引擎（可选）
            profile_engine: 用户画像引擎（可选）
            profile_storage: 用户画像存储管理器（可选）
            session_repo: Session数据仓储（可选）
            report_service: 报告服务（可选）
            plan_manager: 训练计划管理器（可选）
            allow_default: 是否允许使用默认配置（配置文件不存在时）

        Returns:
            配置好的 AppContext 实例
        """
        import os

        env_file: Path | None = None
        if env_path := os.getenv("NANOBOT_CONFIG_DIR"):
            env_file = Path(env_path) / ".env.local"
        else:
            env_file = Path.home() / ".nanobot-runner" / ".env.local"

        EnvManager(env_file=env_file).load_env()

        # 创建或使用提供的配置管理器
        if config is None:
            config = ConfigManager(allow_default=allow_default)

        # 创建或使用提供的存储管理器
        if storage is None:
            storage = StorageManager(config.data_dir)

        # 创建或使用提供的索引管理器
        if indexer is None:
            indexer = IndexManager(config.index_file)

        # 创建或使用提供的解析器
        if parser is None:
            parser = FitParser()

        # 创建或使用提供的分析引擎
        if analytics is None:
            analytics = AnalyticsEngine(storage)

        # 创建或使用提供的用户画像存储管理器
        if profile_storage is None:
            profile_storage = ProfileStorageManager()

        # 创建或使用提供的Session数据仓储
        if session_repo is None:
            session_repo = SessionRepository(storage)

        # 创建AppContext实例（importer、plan_manager、profile_engine和report_service稍后设置）
        context = AppContext(
            config=config,
            storage=storage,
            indexer=indexer,
            parser=parser,
            importer=None,  # type: ignore
            analytics=analytics,
            profile_engine=None,  # type: ignore
            profile_storage=profile_storage,
            session_repo=session_repo,
            report_service=None,  # type: ignore
            plan_manager=None,  # type: ignore
        )

        # 创建或使用提供的导入服务（需要AppContext）
        if importer is None:
            importer = ImportService(context)

        # 设置importer
        context.importer = importer

        # 创建或使用提供的训练计划管理器（需要AppContext）
        if plan_manager is None:
            plan_manager = PlanManager(context)

        # 设置plan_manager
        context.plan_manager = plan_manager

        # 创建或使用提供的报告服务（需要AppContext）
        if report_service is None:
            report_service = ReportService(context)

        # 设置report_service
        context.report_service = report_service

        # 创建或使用提供的用户画像引擎（需要AppContext）
        if profile_engine is None:
            profile_engine = ProfileEngine(context)

        # 设置profile_engine
        context.profile_engine = profile_engine

        return context

    @staticmethod
    def create_for_testing(
        config: ConfigManager | None = None,
        storage: StorageManager | None = None,
        indexer: IndexManager | None = None,
        parser: FitParser | None = None,
        importer: ImportService | None = None,
        analytics: AnalyticsEngine | None = None,
        profile_engine: ProfileEngine | None = None,
        profile_storage: ProfileStorageManager | None = None,
        session_repo: SessionRepository | None = None,
        report_service: ReportService | None = None,
        plan_manager: PlanManager | None = None,
        allow_default: bool = False,
    ) -> AppContext:
        """
        创建用于测试的应用上下文

        与 create() 方法相同，但明确表示用于测试场景。
        支持注入 Mock 对象进行单元测试。

        Args:
            config: 配置管理器（可选）
            storage: 存储管理器（可选）
            indexer: 索引管理器（可选）
            parser: FIT 文件解析器（可选）
            importer: 导入服务（可选）
            analytics: 分析引擎（可选）
            profile_engine: 用户画像引擎（可选）
            profile_storage: 用户画像存储管理器（可选）
            session_repo: Session数据仓储（可选）
            report_service: 报告服务（可选）
            plan_manager: 训练计划管理器（可选）

        Returns:
            配置好的 AppContext 实例
        """
        return AppContextFactory.create(
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
            allow_default=allow_default,
        )


# 全局上下文实例（延迟初始化）
_global_context: AppContext | None = None


def get_context() -> AppContext:
    """
    获取全局应用上下文

    如果全局上下文不存在，则创建默认实例。
    适用于简单场景，不推荐在测试中使用。

    Returns:
        全局 AppContext 实例
    """
    global _global_context
    if _global_context is None:
        _global_context = AppContextFactory.create()
    return _global_context


def set_context(context: AppContext) -> None:
    """
    设置全局应用上下文

    用于在应用启动时设置自定义上下文，或在测试中注入 Mock 上下文。

    Args:
        context: 要设置的 AppContext 实例
    """
    global _global_context
    _global_context = context


def reset_context() -> None:
    """
    重置全局应用上下文

    用于测试清理，确保测试之间相互隔离。
    """
    global _global_context
    _global_context = None
