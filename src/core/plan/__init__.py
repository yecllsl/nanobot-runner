"""
训练计划模块

包含训练计划生成、校验、分析、日历同步、计划管理等核心功能
"""

from src.core.plan.cron_callback import CronCallbackHandler
from src.core.plan.hard_validator import HardValidator
from src.core.plan.plan_adjustment_validator import (
    PlanAdjustmentValidator,
    RulePriority,
    ValidationRule,
)
from src.core.plan.plan_analyzer import PlanAnalyzer
from src.core.plan.plan_execution_repository import (
    PlanExecutionRepository,
    PlanExecutionRepositoryError,
)
from src.core.plan.plan_generator import PlanGenerator
from src.core.plan.plan_manager import PlanManager, PlanStatus
from src.core.plan.plan_modification_dialog import (
    DialogContext,
    DialogState,
    DialogTurn,
    PlanModificationDialogManager,
)
from src.core.plan.prompt_template_engine import (
    PromptTemplateEngine,
    TemplateNotFoundError,
)
from src.core.plan.training_reminder_manager import (
    ReminderRecord,
    ReminderSchedule,
    ReminderStatus,
    TrainingReminderManager,
)
from src.core.plan.training_response_analyzer import TrainingResponseAnalyzer

__all__ = [
    "PlanGenerator",
    "HardValidator",
    "PlanAnalyzer",
    "PlanManager",
    "PlanStatus",
    "PlanExecutionRepository",
    "PlanExecutionRepositoryError",
    "TrainingReminderManager",
    "ReminderStatus",
    "ReminderRecord",
    "ReminderSchedule",
    "TrainingResponseAnalyzer",
    "PlanAdjustmentValidator",
    "ValidationRule",
    "RulePriority",
    "PlanModificationDialogManager",
    "DialogState",
    "DialogContext",
    "DialogTurn",
    "PromptTemplateEngine",
    "TemplateNotFoundError",
    "CronCallbackHandler",
]
