# 用户画像管理器
# 管理用户画像的构建、存储和加载
#
# 拆分说明 (Task 20):
#   - RunnerProfile 数据类已迁移至 src.core.base.profile_schema（唯一真实来源）
#   - ProfileStorageManager 已迁移至 src.core.base.profile_storage
#   - 本文件保留 UserProfileManager 类，通过 re-exports 保持向后兼容

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from src.core.base.logger import get_logger
from src.core.base.profile_schema import RunnerProfile
from src.core.base.profile_storage import ProfileStorageManager
from src.core.models import FitnessLevel, InjuryRiskLevel, TrainingPattern

if TYPE_CHECKING:
    from src.core.storage.parquet_manager import StorageManager

logger = get_logger(__name__)

# Re-exports: 保持向后兼容
# 外部代码 `from src.core.user_profile_manager import RunnerProfile` 仍然有效
__all__ = [
    "RunnerProfile",
    "ProfileStorageManager",
    "UserProfileManager",
    "InjuryRiskLevel",
    "TrainingPattern",
    "FitnessLevel",
]


class UserProfileManager:
    """用户画像管理器"""

    def __init__(
        self,
        storage_manager: StorageManager,
        workspace_dir: Path | None = None,
    ) -> None:
        """
        初始化用户画像管理器

        Args:
            storage_manager: StorageManager 实例
            workspace_dir: 工作目录
        """
        self.storage = storage_manager
        self.storage_manager = ProfileStorageManager(workspace_dir)

    def save_profile(self, profile: RunnerProfile) -> bool:
        """
        保存画像（双存储）

        Args:
            profile: 画像对象

        Returns:
            bool: 保存是否成功
        """
        json_success = self.storage_manager.save_profile_json(profile)
        md_success = self.storage_manager.save_memory_md("", profile)
        return json_success and md_success

    def load_profile(self) -> RunnerProfile | None:
        """
        加载画像

        Returns:
            Optional[RunnerProfile]: 画像对象
        """
        return self.storage_manager.load_profile_json()

    def get_fitness_level(self, avg_vdot: float) -> FitnessLevel:
        """
        根据平均 VDOT 获取体能水平

        Args:
            avg_vdot: 平均 VDOT 值

        Returns:
            FitnessLevel: 体能水平
        """
        if avg_vdot < 35:
            return FitnessLevel.BEGINNER
        elif avg_vdot < 50:
            return FitnessLevel.INTERMEDIATE
        elif avg_vdot < 60:
            return FitnessLevel.ADVANCED
        else:
            return FitnessLevel.ELITE

    def get_training_pattern(self, weekly_avg_distance_km: float) -> TrainingPattern:
        """
        根据周均距离获取训练模式

        Args:
            weekly_avg_distance_km: 周均距离（公里）

        Returns:
            TrainingPattern: 训练模式
        """
        if weekly_avg_distance_km < 20:
            return TrainingPattern.REST
        elif weekly_avg_distance_km < 50:
            return TrainingPattern.LIGHT
        elif weekly_avg_distance_km < 70:
            return TrainingPattern.MODERATE
        elif weekly_avg_distance_km < 100:
            return TrainingPattern.INTENSE
        else:
            return TrainingPattern.EXTREME

    def create_empty_profile(self, user_id: str, days: int = 90) -> RunnerProfile:
        """
        创建空画像

        Args:
            user_id: 用户 ID
            days: 分析天数

        Returns:
            RunnerProfile: 空画像对象
        """
        profile = RunnerProfile(user_id=user_id, profile_date=datetime.now())
        profile.analysis_period_days = days
        profile.data_quality_score = 0.0
        profile.notes.append("暂无跑步数据，请先导入 FIT 文件")
        return profile
