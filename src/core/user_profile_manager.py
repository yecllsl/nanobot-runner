# 用户画像管理器
# 管理用户画像的构建、存储和加载

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.core.base.logger import get_logger
from src.core.models import FitnessLevel, InjuryRiskLevel, TrainingPattern

if TYPE_CHECKING:
    from src.core.storage.parquet_manager import StorageManager

logger = get_logger(__name__)


@dataclass
class RunnerProfile:
    """跑者画像数据类"""

    user_id: str
    profile_date: datetime

    total_activities: int = 0
    total_distance_km: float = 0.0
    total_duration_hours: float = 0.0

    avg_vdot: float = 0.0
    max_vdot: float = 0.0
    fitness_level: FitnessLevel = FitnessLevel.BEGINNER

    weekly_avg_distance_km: float = 0.0
    weekly_avg_duration_hours: float = 0.0
    training_pattern: TrainingPattern = TrainingPattern.REST

    avg_heart_rate: int = 0
    max_heart_rate: int = 0
    resting_heart_rate: int = 0

    injury_risk_level: InjuryRiskLevel = InjuryRiskLevel.LOW
    injury_risk_score: float = 0.0

    atl: float = 0.0
    ctl: float = 0.0
    tsb: float = 0.0

    avg_pace_min_per_km: float = 0.0
    favorite_running_time: str = "morning"
    consistency_score: float = 0.0

    data_quality_score: float = 0.0
    analysis_period_days: int = 0
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "user_id": self.user_id,
            "profile_date": self.profile_date.isoformat(),
            "total_activities": self.total_activities,
            "total_distance_km": round(self.total_distance_km, 2),
            "total_duration_hours": round(self.total_duration_hours, 2),
            "avg_vdot": round(self.avg_vdot, 2),
            "max_vdot": round(self.max_vdot, 2),
            "fitness_level": self.fitness_level.value,
            "weekly_avg_distance_km": round(self.weekly_avg_distance_km, 2),
            "weekly_avg_duration_hours": round(self.weekly_avg_duration_hours, 2),
            "training_pattern": self.training_pattern.value,
            "avg_heart_rate": self.avg_heart_rate,
            "max_heart_rate": self.max_heart_rate,
            "resting_heart_rate": self.resting_heart_rate,
            "injury_risk_level": self.injury_risk_level.value,
            "injury_risk_score": round(self.injury_risk_score, 2),
            "atl": round(self.atl, 2),
            "ctl": round(self.ctl, 2),
            "tsb": round(self.tsb, 2),
            "avg_pace_min_per_km": round(self.avg_pace_min_per_km, 2),
            "favorite_running_time": self.favorite_running_time,
            "consistency_score": round(self.consistency_score, 2),
            "data_quality_score": round(self.data_quality_score, 2),
            "analysis_period_days": self.analysis_period_days,
            "notes": self.notes,
        }


class ProfileStorageManager:
    """画像双存储管理器"""

    def __init__(self, workspace_dir: Path | None = None) -> None:
        self.workspace_dir = workspace_dir or Path.home() / ".nanobot-runner"
        self.profile_json_path = self.workspace_dir / "data" / "profile.json"
        self.memory_md_path = self.workspace_dir / "memory" / "MEMORY.md"
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """确保必要的目录存在"""
        try:
            self.workspace_dir.mkdir(parents=True, exist_ok=True)
            (self.workspace_dir / "data").mkdir(parents=True, exist_ok=True)
            (self.workspace_dir / "memory").mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning(f"创建目录失败：{e}")

    def save_profile_json(self, profile: RunnerProfile) -> bool:
        """保存画像到 profile.json"""
        try:
            profile_data = profile.to_dict()
            profile_data["updated_at"] = datetime.now().isoformat()

            with open(self.profile_json_path, "w", encoding="utf-8") as f:
                json.dump(profile_data, f, indent=2, ensure_ascii=False)

            logger.info(f"画像已保存到 profile.json: {profile.user_id}")
            return True
        except Exception as e:
            logger.error(f"保存 profile.json 失败：{e}")
            raise RuntimeError(f"保存 profile.json 失败：{e}") from e

    def load_profile_json(self) -> RunnerProfile | None:
        """从 profile.json 加载画像"""
        try:
            if not self.profile_json_path.exists():
                logger.debug(f"profile.json 不存在：{self.profile_json_path}")
                return None

            with open(self.profile_json_path, encoding="utf-8") as f:
                profile_data = json.load(f)

            profile = self._dict_to_profile(profile_data)
            logger.info(f"从 profile.json 加载画像成功：{profile.user_id}")
            return profile
        except json.JSONDecodeError as e:
            logger.error(f"profile.json 格式错误：{e}")
            return None
        except Exception as e:
            logger.error(f"加载 profile.json 失败：{e}")
            raise RuntimeError(f"加载 profile.json 失败：{e}") from e

    def _dict_to_profile(self, data: dict[str, Any]) -> RunnerProfile:
        """将字典转换为 RunnerProfile 对象"""
        profile = RunnerProfile(
            user_id=data.get("user_id", "default_user"),
            profile_date=datetime.fromisoformat(
                data.get("profile_date", datetime.now().isoformat())
            ),
        )

        profile.total_activities = data.get("total_activities", 0)
        profile.total_distance_km = data.get("total_distance_km", 0.0)
        profile.total_duration_hours = data.get("total_duration_hours", 0.0)
        profile.avg_vdot = data.get("avg_vdot", 0.0)
        profile.max_vdot = data.get("max_vdot", 0.0)

        fitness_str = data.get("fitness_level", "beginner")
        profile.fitness_level = (
            FitnessLevel(fitness_str)
            if fitness_str in [e.value for e in FitnessLevel]
            else FitnessLevel.BEGINNER
        )

        profile.weekly_avg_distance_km = data.get("weekly_avg_distance_km", 0.0)
        profile.weekly_avg_duration_hours = data.get("weekly_avg_duration_hours", 0.0)

        pattern_str = data.get("training_pattern", "rest")
        profile.training_pattern = (
            TrainingPattern(pattern_str)
            if pattern_str in [e.value for e in TrainingPattern]
            else TrainingPattern.REST
        )

        profile.avg_heart_rate = data.get("avg_heart_rate", 0)
        profile.max_heart_rate = data.get("max_heart_rate", 0)
        profile.resting_heart_rate = data.get("resting_heart_rate", 0)

        risk_str = data.get("injury_risk_level", "low")
        profile.injury_risk_level = (
            InjuryRiskLevel(risk_str)
            if risk_str in [e.value for e in InjuryRiskLevel]
            else InjuryRiskLevel.LOW
        )

        profile.injury_risk_score = data.get("injury_risk_score", 0.0)
        profile.atl = data.get("atl", 0.0)
        profile.ctl = data.get("ctl", 0.0)
        profile.tsb = data.get("tsb", 0.0)
        profile.avg_pace_min_per_km = data.get("avg_pace_min_per_km", 0.0)
        profile.favorite_running_time = data.get("favorite_running_time", "morning")
        profile.consistency_score = data.get("consistency_score", 0.0)
        profile.data_quality_score = data.get("data_quality_score", 0.0)
        profile.analysis_period_days = data.get("analysis_period_days", 0)
        profile.notes = data.get("notes", [])

        return profile

    def save_memory_md(self, profile: RunnerProfile) -> bool:
        """保存画像到 MEMORY.md"""
        try:
            content = self._generate_memory_content(profile)

            with open(self.memory_md_path, "w", encoding="utf-8") as f:
                f.write(content)

            logger.info(f"画像已保存到 MEMORY.md: {profile.user_id}")
            return True
        except Exception as e:
            logger.error(f"保存 MEMORY.md 失败：{e}")
            raise RuntimeError(f"保存 MEMORY.md 失败：{e}") from e

    def _generate_memory_content(self, profile: RunnerProfile) -> str:
        """生成 MEMORY.md 内容"""
        lines = [
            "# 跑者画像",
            "",
            f"**用户ID**: {profile.user_id}",
            f"**更新时间**: {profile.profile_date.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## 基础信息",
            "",
            f"- 总跑步次数: {profile.total_activities}",
            f"- 总距离: {profile.total_distance_km:.2f} km",
            f"- 总时长: {profile.total_duration_hours:.2f} 小时",
            "",
            "## 体能水平",
            "",
            f"- 平均 VDOT: {profile.avg_vdot:.2f}",
            f"- 最高 VDOT: {profile.max_vdot:.2f}",
            f"- 体能等级: {profile.fitness_level.value}",
            "",
            "## 训练模式",
            "",
            f"- 周均距离: {profile.weekly_avg_distance_km:.2f} km",
            f"- 周均时长: {profile.weekly_avg_duration_hours:.2f} 小时",
            f"- 训练模式: {profile.training_pattern.value}",
            f"- 训练一致性: {profile.consistency_score:.1f}%",
            "",
            "## 心率数据",
            "",
            f"- 平均心率: {profile.avg_heart_rate} bpm",
            f"- 最高心率: {profile.max_heart_rate} bpm",
            f"- 静息心率: {profile.resting_heart_rate} bpm",
            "",
            "## 训练负荷",
            "",
            f"- ATL (急性训练负荷): {profile.atl:.2f}",
            f"- CTL (慢性训练负荷): {profile.ctl:.2f}",
            f"- TSB (训练压力平衡): {profile.tsb:.2f}",
            "",
            "## 伤病风险",
            "",
            f"- 风险等级: {profile.injury_risk_level.value}",
            f"- 风险分数: {profile.injury_risk_score:.2f}",
            "",
            "## 其他信息",
            "",
            f"- 平均配速: {profile.avg_pace_min_per_km:.2f} 分钟/公里",
            f"- 偏好跑步时间: {profile.favorite_running_time}",
            f"- 数据质量评分: {profile.data_quality_score:.1f}%",
            f"- 分析周期: {profile.analysis_period_days} 天",
        ]

        if profile.notes:
            lines.extend(["", "## 备注", ""])
            for note in profile.notes:
                lines.append(f"- {note}")

        return "\n".join(lines) + "\n"


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
        md_success = self.storage_manager.save_memory_md(profile)
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
