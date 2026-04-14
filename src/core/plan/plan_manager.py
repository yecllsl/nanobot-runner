# 训练计划管理器
# 管理训练计划的生命周期，包括创建、查询、更新、取消等操作

import json
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

from src.core.models import PlanStatus, TrainingPlan

if TYPE_CHECKING:
    from src.core.context import AppContext

logger = logging.getLogger(__name__)


class PlanStatusTransition:
    """计划状态转换规则"""

    TRANSITIONS = {
        PlanStatus.DRAFT: [PlanStatus.ACTIVE, PlanStatus.CANCELLED],
        PlanStatus.ACTIVE: [
            PlanStatus.PAUSED,
            PlanStatus.COMPLETED,
            PlanStatus.CANCELLED,
        ],
        PlanStatus.PAUSED: [PlanStatus.ACTIVE, PlanStatus.CANCELLED],
        PlanStatus.COMPLETED: [],  # 已完成状态不可转换
        PlanStatus.CANCELLED: [],  # 已取消状态不可转换
    }

    @classmethod
    def can_transition(cls, from_status: PlanStatus, to_status: PlanStatus) -> bool:
        """
        检查状态转换是否合法

        Args:
            from_status: 当前状态
            to_status: 目标状态

        Returns:
            bool: 是否可以转换
        """
        allowed_transitions = cls.TRANSITIONS.get(from_status, [])
        return to_status in allowed_transitions


class PlanManagerError(Exception):
    """计划管理器异常"""

    pass


class PlanManager:
    """训练计划管理器"""

    def __init__(self, context: "AppContext"):
        """
        初始化计划管理器

        Args:
            context: AppContext 实例
        """
        self.context = context
        self.config = context.config
        self.data_dir = self.config.data_dir
        self.plans_file = self.data_dir / "training_plans.json"
        self._plans: dict[str, dict[str, Any]] = {}
        self._load_plans()

    def _load_plans(self) -> None:
        """从文件加载计划"""
        if not self.plans_file.exists():
            logger.info("计划文件不存在，创建新文件")
            self._save_plans()
            return

        try:
            with open(self.plans_file, encoding="utf-8") as f:
                data = json.load(f)
                self._plans = data.get("plans", {})
            logger.info(f"成功加载 {len(self._plans)} 个训练计划")
        except Exception as e:
            logger.error(f"加载训练计划失败：{e}")
            self._plans = {}

    def _save_plans(self) -> None:
        """保存计划到文件"""
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            data = {
                "version": "1.0",
                "updated_at": datetime.now().isoformat(),
                "plans": self._plans,
            }
            with open(self.plans_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"成功保存 {len(self._plans)} 个训练计划")
        except Exception as e:
            logger.error(f"保存训练计划失败：{e}")
            raise PlanManagerError(f"保存训练计划失败：{e}") from e

    def create_plan(self, plan: TrainingPlan) -> str:
        """
        创建训练计划

        Args:
            plan: 训练计划

        Returns:
            str: 计划ID

        Raises:
            PlanManagerError: 当创建失败时
        """
        if not plan.plan_id:
            raise PlanManagerError("计划ID不能为空")

        if plan.plan_id in self._plans:
            raise PlanManagerError(f"计划ID已存在：{plan.plan_id}")

        plan_dict = plan.to_dict()
        plan_dict["status"] = PlanStatus.DRAFT.value
        plan_dict["created_at"] = datetime.now().isoformat()
        plan_dict["updated_at"] = datetime.now().isoformat()

        self._plans[plan.plan_id] = plan_dict
        self._save_plans()

        logger.info(f"创建训练计划成功：{plan.plan_id}")
        return plan.plan_id

    def get_plan(self, plan_id: str) -> TrainingPlan | None:
        """
        获取训练计划

        Args:
            plan_id: 计划ID

        Returns:
            Optional[TrainingPlan]: 训练计划，不存在返回None
        """
        plan_dict = self._plans.get(plan_id)
        if not plan_dict:
            return None

        try:
            return TrainingPlan.from_dict(plan_dict)
        except Exception as e:
            logger.error(f"解析训练计划失败：{e}")
            return None

    def get_plan_status(self, plan_id: str) -> PlanStatus | None:
        """
        获取计划状态

        Args:
            plan_id: 计划ID

        Returns:
            Optional[PlanStatus]: 计划状态，不存在返回None
        """
        plan_dict = self._plans.get(plan_id)
        if not plan_dict:
            return None

        status_str = plan_dict.get("status")
        if status_str:
            return PlanStatus(status_str)
        return None

    def update_plan(self, plan_id: str, updates: dict[str, Any]) -> bool:
        """
        更新训练计划

        Args:
            plan_id: 计划ID
            updates: 更新内容

        Returns:
            bool: 是否更新成功

        Raises:
            PlanManagerError: 当更新失败时
        """
        if plan_id not in self._plans:
            raise PlanManagerError(f"计划不存在：{plan_id}")

        plan_dict = self._plans[plan_id]

        if "status" in updates:
            new_status = PlanStatus(updates["status"])
            current_status = PlanStatus(plan_dict.get("status", PlanStatus.DRAFT.value))

            if not PlanStatusTransition.can_transition(current_status, new_status):
                raise PlanManagerError(
                    f"状态转换不合法：{current_status.value} -> {new_status.value}"
                )

        for key, value in updates.items():
            if key not in ["plan_id", "created_at"]:
                plan_dict[key] = value

        plan_dict["updated_at"] = datetime.now().isoformat()
        self._save_plans()

        logger.info(f"更新训练计划成功：{plan_id}")
        return True

    def cancel_plan(self, plan_id: str, reason: str) -> bool:
        """
        取消训练计划

        Args:
            plan_id: 计划ID
            reason: 取消原因

        Returns:
            bool: 是否取消成功

        Raises:
            PlanManagerError: 当取消失败时
        """
        if plan_id not in self._plans:
            raise PlanManagerError(f"计划不存在：{plan_id}")

        plan_dict = self._plans[plan_id]
        current_status = PlanStatus(plan_dict.get("status", PlanStatus.DRAFT.value))

        if not PlanStatusTransition.can_transition(
            current_status, PlanStatus.CANCELLED
        ):
            raise PlanManagerError(f"当前状态不允许取消：{current_status.value}")

        plan_dict["status"] = PlanStatus.CANCELLED.value
        plan_dict["cancelled_at"] = datetime.now().isoformat()
        plan_dict["cancel_reason"] = reason
        plan_dict["updated_at"] = datetime.now().isoformat()

        self._save_plans()

        logger.info(f"取消训练计划成功：{plan_id}，原因：{reason}")
        return True

    def activate_plan(self, plan_id: str) -> bool:
        """
        激活训练计划

        Args:
            plan_id: 计划ID

        Returns:
            bool: 是否激活成功

        Raises:
            PlanManagerError: 当激活失败时
        """
        if plan_id not in self._plans:
            raise PlanManagerError(f"计划不存在：{plan_id}")

        plan_dict = self._plans[plan_id]
        current_status = PlanStatus(plan_dict.get("status", PlanStatus.DRAFT.value))

        if not PlanStatusTransition.can_transition(current_status, PlanStatus.ACTIVE):
            raise PlanManagerError(f"当前状态不允许激活：{current_status.value}")

        plan_dict["status"] = PlanStatus.ACTIVE.value
        plan_dict["activated_at"] = datetime.now().isoformat()
        plan_dict["updated_at"] = datetime.now().isoformat()

        self._save_plans()

        logger.info(f"激活训练计划成功：{plan_id}")
        return True

    def pause_plan(self, plan_id: str) -> bool:
        """
        暂停训练计划

        Args:
            plan_id: 计划ID

        Returns:
            bool: 是否暂停成功

        Raises:
            PlanManagerError: 当暂停失败时
        """
        if plan_id not in self._plans:
            raise PlanManagerError(f"计划不存在：{plan_id}")

        plan_dict = self._plans[plan_id]
        current_status = PlanStatus(plan_dict.get("status", PlanStatus.DRAFT.value))

        if not PlanStatusTransition.can_transition(current_status, PlanStatus.PAUSED):
            raise PlanManagerError(f"当前状态不允许暂停：{current_status.value}")

        plan_dict["status"] = PlanStatus.PAUSED.value
        plan_dict["paused_at"] = datetime.now().isoformat()
        plan_dict["updated_at"] = datetime.now().isoformat()

        self._save_plans()

        logger.info(f"暂停训练计划成功：{plan_id}")
        return True

    def complete_plan(self, plan_id: str) -> bool:
        """
        完成训练计划

        Args:
            plan_id: 计划ID

        Returns:
            bool: 是否完成成功

        Raises:
            PlanManagerError: 当完成失败时
        """
        if plan_id not in self._plans:
            raise PlanManagerError(f"计划不存在：{plan_id}")

        plan_dict = self._plans[plan_id]
        current_status = PlanStatus(plan_dict.get("status", PlanStatus.DRAFT.value))

        if not PlanStatusTransition.can_transition(
            current_status, PlanStatus.COMPLETED
        ):
            raise PlanManagerError(f"当前状态不允许完成：{current_status.value}")

        plan_dict["status"] = PlanStatus.COMPLETED.value
        plan_dict["completed_at"] = datetime.now().isoformat()
        plan_dict["updated_at"] = datetime.now().isoformat()

        self._save_plans()

        logger.info(f"完成训练计划成功：{plan_id}")
        return True

    def list_plans(
        self,
        status: PlanStatus | None = None,
        limit: int = 100,
    ) -> list[TrainingPlan]:
        """
        列出训练计划

        Args:
            status: 过滤状态，不指定则列出全部
            limit: 返回数量限制

        Returns:
            List[TrainingPlan]: 训练计划列表
        """
        plans = []

        for plan_dict in self._plans.values():
            if status:
                plan_status = plan_dict.get("status")
                if plan_status != status.value:
                    continue

            try:
                plan = TrainingPlan.from_dict(plan_dict)
                plans.append(plan)
            except Exception as e:
                logger.error(f"解析训练计划失败：{e}")
                continue

        plans.sort(
            key=lambda p: p.created_at if hasattr(p, "created_at") else "", reverse=True
        )

        return plans[:limit]

    def delete_plan(self, plan_id: str) -> bool:
        """
        删除训练计划

        Args:
            plan_id: 计划ID

        Returns:
            bool: 是否删除成功

        Raises:
            PlanManagerError: 当删除失败时
        """
        if plan_id not in self._plans:
            raise PlanManagerError(f"计划不存在：{plan_id}")

        del self._plans[plan_id]
        self._save_plans()

        logger.info(f"删除训练计划成功：{plan_id}")
        return True

    def get_active_plan(self) -> TrainingPlan | None:
        """
        获取当前激活的训练计划

        Returns:
            Optional[TrainingPlan]: 激活的训练计划，无则返回None
        """
        for plan_dict in self._plans.values():
            if plan_dict.get("status") == PlanStatus.ACTIVE.value:
                try:
                    return TrainingPlan.from_dict(plan_dict)
                except Exception as e:
                    logger.error(f"解析训练计划失败：{e}")
                    continue

        return None
