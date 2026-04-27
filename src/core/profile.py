# 用户画像引擎
# 基于历史跑步数据构建用户画像，包括体能水平、训练模式、伤病风险等维度
# 双存储持久化：profile.json (结构化数据) + MEMORY.md (Agent 观察笔记)

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

import polars as pl

from src.core.anomaly_data_filter import AnomalyDataFilter
from src.core.injury_risk_analyzer import InjuryRiskAnalyzer
from src.core.logger import get_logger
from src.core.models import FitnessLevel
from src.core.training_history_analyzer import TrainingHistoryAnalyzer
from src.core.user_profile_manager import (
    InjuryRiskLevel,
    RunnerProfile,
    TrainingPattern,
    UserProfileManager,
)

if TYPE_CHECKING:
    from src.core.context import AppContext

logger = get_logger(__name__)


class ProfileStorageManager:
    """画像双存储管理器，管理 profile.json 和 MEMORY.md 的持久化"""

    def __init__(self, workspace_dir: Path | None = None) -> None:
        """
        初始化画像存储管理器

        Args:
            workspace_dir: nanobot workspace 目录，默认为 ~/.nanobot-runner
        """
        self.workspace_dir = workspace_dir or Path.home() / ".nanobot-runner"
        self.profile_json_path = self.workspace_dir / "data" / "profile.json"
        self.memory_md_path = self.workspace_dir / "memory" / "MEMORY.md"

        # 确保目录存在
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """确保必要的目录存在"""
        try:
            self.workspace_dir.mkdir(parents=True, exist_ok=True)
            (self.workspace_dir / "data").mkdir(parents=True, exist_ok=True)
            (self.workspace_dir / "memory").mkdir(parents=True, exist_ok=True)
            logger.debug(f"画像存储目录初始化完成：{self.workspace_dir}")
        except OSError as e:
            logger.error(f"创建画像存储目录失败：{e}")
            raise RuntimeError(f"无法创建画像存储目录：{e}") from e

    def save_profile_json(self, profile: RunnerProfile) -> bool:
        """
        保存画像到 profile.json

        Args:
            profile: RunnerProfile 对象

        Returns:
            bool: 保存是否成功

        Raises:
            RuntimeError: 当保存失败时
        """
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
        """
        从 profile.json 加载画像

        Returns:
            Optional[RunnerProfile]: 画像对象，如果文件不存在或加载失败则返回 None

        Raises:
            RuntimeError: 当加载失败时（非文件不存在的情况）
        """
        try:
            if not self.profile_json_path.exists():
                logger.debug(f"profile.json 不存在：{self.profile_json_path}")
                return None

            with open(self.profile_json_path, encoding="utf-8") as f:
                profile_data = json.load(f)

            # 转换回 RunnerProfile 对象
            profile = self._dict_to_profile(profile_data)
            logger.info(f"从 profile.json 加载画像成功：{profile.user_id}")
            return profile
        except json.JSONDecodeError as e:
            logger.error(f"profile.json 格式错误：{e}")
            raise RuntimeError(f"profile.json 格式错误：{e}") from e
        except Exception as e:
            logger.error(f"加载 profile.json 失败：{e}")
            raise RuntimeError(f"加载 profile.json 失败：{e}") from e

    def save_memory_md(
        self,
        content: str,
        profile: RunnerProfile | None = None,
        append: bool = False,
    ) -> bool:
        """
        保存内容到 MEMORY.md

        Args:
            content: 要保存的内容（Markdown 格式）
            profile: 可选的画像对象，用于自动添加画像摘要
            append: 是否追加模式，False 表示覆盖

        Returns:
            bool: 保存是否成功

        Raises:
            RuntimeError: 当保存失败时
        """
        try:
            # 如果提供 profile，自动添加画像摘要
            if profile:
                content = self._generate_memory_content(content, profile)

            # 追加模式：读取现有内容
            if append and self.memory_md_path.exists():
                with open(self.memory_md_path, encoding="utf-8") as f:
                    existing_content = f.read()
                content = existing_content + "\n\n" + content

            with open(self.memory_md_path, "w", encoding="utf-8") as f:
                f.write(content)

            logger.info(f"MEMORY.md 保存成功 ({'追加' if append else '覆盖'}模式)")
            return True
        except Exception as e:
            logger.error(f"保存 MEMORY.md 失败：{e}")
            raise RuntimeError(f"保存 MEMORY.md 失败：{e}") from e

    def load_memory_md(self) -> str | None:
        """
        从 MEMORY.md 加载内容

        Returns:
            Optional[str]: MEMORY.md 内容，如果文件不存在则返回 None

        Raises:
            RuntimeError: 当加载失败时（非文件不存在的情况）
        """
        try:
            if not self.memory_md_path.exists():
                logger.debug(f"MEMORY.md 不存在：{self.memory_md_path}")
                return None

            with open(self.memory_md_path, encoding="utf-8") as f:
                content = f.read()

            logger.info("MEMORY.md 加载成功")
            return content
        except Exception as e:
            logger.error(f"加载 MEMORY.md 失败：{e}")
            raise RuntimeError(f"加载 MEMORY.md 失败：{e}") from e

    def sync_dual_storage(
        self,
        profile: RunnerProfile,
        memory_content: str | None = None,
        sync_direction: str = "json_to_md",
    ) -> bool:
        """
        双存储同步

        Args:
            profile: RunnerProfile 对象
            memory_content: 可选的 MEMORY.md 内容
            sync_direction: 同步方向
                - "json_to_md": 从 profile.json 同步到 MEMORY.md（默认）
                - "md_to_json": 从 MEMORY.md 同步到 profile.json（保留 Agent 笔记）
                - "bidirectional": 双向同步（合并）

        Returns:
            bool: 同步是否成功

        Raises:
            ValueError: 当 sync_direction 参数无效时
            RuntimeError: 当同步失败时
        """
        if sync_direction not in ["json_to_md", "md_to_json", "bidirectional"]:
            raise ValueError(
                f"无效的同步方向：{sync_direction}，必须是 json_to_md, md_to_json, 或 bidirectional"
            )

        try:
            if sync_direction == "json_to_md":
                # 从 profile.json 同步到 MEMORY.md
                return self._sync_json_to_md(profile)
            elif sync_direction == "md_to_json":
                # 从 MEMORY.md 同步到 profile.json（保留 Agent 笔记）
                return self._sync_md_to_json(profile)
            else:  # bidirectional
                # 双向同步
                return self._sync_bidirectional(profile, memory_content)
        except Exception as e:
            logger.error(f"双存储同步失败：{e}")
            raise RuntimeError(f"双存储同步失败：{e}") from e

    def merge_profile_to_md(
        self,
        profile: RunnerProfile,
        preserve_agent_notes: bool = True,
    ) -> bool:
        """
        智能合并画像到 MEMORY.md，保留 Agent 观察笔记

        Args:
            profile: RunnerProfile 对象
            preserve_agent_notes: 是否保留 Agent 添加的观察笔记（通过 @agent 标记）

        Returns:
            bool: 合并是否成功

        Raises:
            RuntimeError: 当合并失败时
        """
        try:
            # 读取现有的 MEMORY.md
            existing_content = ""
            agent_notes = []

            if self.memory_md_path.exists():
                with open(self.memory_md_path, encoding="utf-8") as f:
                    existing_content = f.read()

                # 提取 Agent 笔记（如果 preserve_agent_notes 为 True）
                if preserve_agent_notes:
                    agent_notes = self._extract_agent_notes(existing_content)

            # 生成新的 MEMORY.md 内容
            new_content = self._generate_memory_content("", profile)

            # 追加 Agent 笔记
            if agent_notes:
                new_content += "\n\n## Agent 观察笔记\n\n"
                for note in agent_notes:
                    new_content += f"- {note}\n"

            # 追加原有内容（如果有）
            if existing_content and preserve_agent_notes:
                # 如果保留 Agent 笔记，只追加非 Agent 笔记部分
                non_agent_content = self._remove_agent_notes(existing_content)
                if non_agent_content.strip():
                    new_content += "\n\n" + non_agent_content
            elif existing_content and not preserve_agent_notes:
                # 如果不保留 Agent 笔记，追加移除 Agent 笔记后的内容
                non_agent_content = self._remove_agent_notes(existing_content)
                if non_agent_content.strip():
                    new_content += "\n\n" + non_agent_content

            # 保存
            with open(self.memory_md_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            logger.info("智能合并画像到 MEMORY.md 成功")
            return True
        except Exception as e:
            logger.error(f"智能合并失败：{e}")
            raise RuntimeError(f"智能合并失败：{e}") from e

    def _dict_to_profile(self, profile_data: dict[str, Any]) -> RunnerProfile:
        """
        将字典转换为 RunnerProfile 对象

        Args:
            profile_data: 画像字典数据

        Returns:
            RunnerProfile: 画像对象

        Raises:
            ValueError: 当数据格式无效时
        """
        try:
            # 处理日期
            profile_date_str = profile_data.get(
                "profile_date", datetime.now().isoformat()
            )
            profile_date = datetime.fromisoformat(profile_date_str)

            # 处理枚举
            fitness_level_str = profile_data.get("fitness_level", "beginner")
            fitness_level = FitnessLevel(fitness_level_str)

            training_pattern_str = profile_data.get("training_pattern", "rest")
            training_pattern = TrainingPattern(training_pattern_str)

            injury_risk_level_str = profile_data.get("injury_risk_level", "low")
            injury_risk_level = InjuryRiskLevel(injury_risk_level_str)

            # 创建对象
            profile = RunnerProfile(
                user_id=profile_data.get("user_id", "default_user"),
                profile_date=profile_date,
                total_activities=profile_data.get("total_activities", 0),
                total_distance_km=profile_data.get("total_distance_km", 0.0),
                total_duration_hours=profile_data.get("total_duration_hours", 0.0),
                avg_vdot=profile_data.get("avg_vdot", 0.0),
                max_vdot=profile_data.get("max_vdot", 0.0),
                fitness_level=fitness_level,  # type: ignore[arg-type]
                weekly_avg_distance_km=profile_data.get("weekly_avg_distance_km", 0.0),
                weekly_avg_duration_hours=profile_data.get(
                    "weekly_avg_duration_hours", 0.0
                ),
                training_pattern=training_pattern,
                avg_heart_rate=profile_data.get("avg_heart_rate"),  # type: ignore[arg-type]
                max_heart_rate=profile_data.get("max_heart_rate"),  # type: ignore[arg-type]
                resting_heart_rate=profile_data.get("resting_heart_rate"),  # type: ignore[arg-type]
                injury_risk_level=injury_risk_level,
                injury_risk_score=profile_data.get("injury_risk_score", 0.0),
                atl=profile_data.get("atl", 0.0),
                ctl=profile_data.get("ctl", 0.0),
                tsb=profile_data.get("tsb", 0.0),
                avg_pace_min_per_km=profile_data.get("avg_pace_min_per_km", 0.0),
                favorite_running_time=profile_data.get(
                    "favorite_running_time", "morning"
                ),
                consistency_score=profile_data.get("consistency_score", 0.0),
                data_quality_score=profile_data.get("data_quality_score", 0.0),
                analysis_period_days=profile_data.get("analysis_period_days", 0),
                notes=profile_data.get("notes", []),
            )

            return profile
        except Exception as e:
            logger.error(f"字典转画像对象失败：{e}")
            raise ValueError(f"字典转画像对象失败：{e}") from e

    def _generate_memory_content(
        self,
        custom_content: str,
        profile: RunnerProfile,
    ) -> str:
        """
        生成 MEMORY.md 内容（包含画像摘要）

        Args:
            custom_content: 自定义内容
            profile: RunnerProfile 对象

        Returns:
            str: 生成的 Markdown 内容
        """
        content = "# 跑步记忆与观察笔记\n\n"
        content += f"*最后更新：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n"

        # 画像摘要
        content += "## 用户画像摘要\n\n"
        content += f"- **用户 ID**: {profile.user_id}\n"
        content += f"- **总活动次数**: {profile.total_activities}\n"
        content += f"- **总跑量**: {profile.total_distance_km:.2f} km\n"
        content += f"- **总时长**: {profile.total_duration_hours:.2f} 小时\n"
        content += f"- **平均 VDOT**: {profile.avg_vdot:.2f}\n"
        content += f"- **最大 VDOT**: {profile.max_vdot:.2f}\n"
        content += f"- **体能水平**: {profile.fitness_level.value}\n"
        content += f"- **训练模式**: {profile.training_pattern.value}\n"
        content += f"- **伤病风险**: {profile.injury_risk_level.value} ({profile.injury_risk_score:.1f})\n"

        # 训练负荷
        content += "\n## 训练负荷\n\n"
        content += f"- **ATL (急性)**: {profile.atl:.2f}\n"
        content += f"- **CTL (慢性)**: {profile.ctl:.2f}\n"
        content += f"- **TSB (压力平衡)**: {profile.tsb:.2f}\n"

        # 心率指标
        if profile.avg_heart_rate:
            content += "\n## 心率指标\n\n"
            content += f"- **平均心率**: {profile.avg_heart_rate:.1f} bpm\n"
            if profile.max_heart_rate:
                content += f"- **最大心率**: {profile.max_heart_rate:.1f} bpm\n"
            if profile.resting_heart_rate:
                content += f"- **静息心率**: {profile.resting_heart_rate:.1f} bpm\n"

        # 其他指标
        content += "\n## 其他指标\n\n"
        content += f"- **平均配速**: {profile.avg_pace_min_per_km:.2f} min/km\n"
        content += f"- **偏好训练时间**: {profile.favorite_running_time}\n"
        content += f"- **训练一致性**: {profile.consistency_score:.1f}/100\n"
        content += f"- **数据质量**: {profile.data_quality_score:.1f}/100\n"

        # 自定义内容
        if custom_content.strip():
            content += "\n" + custom_content

        return content

    def _extract_agent_notes(self, content: str) -> list[str]:
        """
        从 MEMORY.md 内容中提取 Agent 笔记

        Agent 笔记通过 @agent 标记识别

        Args:
            content: MEMORY.md 内容

        Returns:
            List[str]: Agent 笔记列表
        """
        agent_notes = []

        # 查找 @agent 标记的行
        pattern = r"^\s*-\s*\@agent\s+(.+)$"
        for line in content.split("\n"):
            match = re.match(pattern, line, re.MULTILINE)
            if match:
                agent_notes.append(match.group(1).strip())

        return agent_notes

    def _remove_agent_notes(self, content: str) -> str:
        """
        从 MEMORY.md 内容中移除 Agent 笔记

        Args:
            content: MEMORY.md 内容

        Returns:
            str: 移除 Agent 笔记后的内容
        """
        lines = content.split("\n")
        filtered_lines = []

        # 过滤掉 @agent 标记的行
        for line in lines:
            if "@agent" not in line:
                filtered_lines.append(line)

        return "\n".join(filtered_lines)

    def _sync_json_to_md(self, profile: RunnerProfile) -> bool:
        """
        从 profile.json 同步到 MEMORY.md

        Args:
            profile: RunnerProfile 对象

        Returns:
            bool: 同步是否成功
        """
        # 生成 MEMORY.md 内容
        content = self._generate_memory_content("", profile)

        # 保存
        with open(self.memory_md_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info("从 profile.json 同步到 MEMORY.md 成功")
        return True

    def _sync_md_to_json(self, profile: RunnerProfile) -> bool:
        """
        从 MEMORY.md 同步到 profile.json（保留 Agent 笔记）

        Args:
            profile: RunnerProfile 对象

        Returns:
            bool: 同步是否成功
        """
        # 保存 profile.json
        self.save_profile_json(profile)

        # 读取 MEMORY.md，提取 Agent 笔记
        agent_notes = []
        if self.memory_md_path.exists():
            with open(self.memory_md_path, encoding="utf-8") as f:
                content = f.read()
            agent_notes = self._extract_agent_notes(content)

        # 将 Agent 笔记添加到 profile.notes
        if agent_notes:
            profile.notes.extend(agent_notes)
            self.save_profile_json(profile)

        logger.info("从 MEMORY.md 同步到 profile.json 成功")
        return True

    def _sync_bidirectional(
        self, profile: RunnerProfile, memory_content: str | None = None
    ) -> bool:
        """
        双向同步（合并）

        Args:
            profile: RunnerProfile 对象
            memory_content: 可选的 MEMORY.md 内容

        Returns:
            bool: 同步是否成功
        """
        # 1. 保存 profile.json
        self.save_profile_json(profile)

        # 2. 从现有 MEMORY.md 提取 Agent 笔记
        agent_notes = []
        if self.memory_md_path.exists():
            with open(self.memory_md_path, encoding="utf-8") as f:
                existing_content = f.read()
            agent_notes = self._extract_agent_notes(existing_content)

        # 3. 生成新的 MEMORY.md 内容（包含 Agent 笔记）
        new_content = self._generate_memory_content("", profile)
        if agent_notes:
            new_content += "\n\n## Agent 观察笔记\n\n"
            for note in agent_notes:
                new_content += f"- @agent {note}\n"

        # 4. 追加自定义内容
        if memory_content:
            new_content += "\n\n" + memory_content

        # 5. 保存 MEMORY.md
        with open(self.memory_md_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        logger.info("双向同步成功")
        return True


class ProfileStaleStatus(Enum):
    """画像保鲜期状态"""

    FRESH = "新鲜"  # <= 7 天
    STALE = "过期"  # > 7 天
    MISSING = "缺失"  # 无画像数据


@dataclass
class AnomalyFilterRule:
    """异常过滤规则数据结构"""

    field_name: str  # 字段名称
    condition: str  # 条件表达式（如 ">", "<", ">=", "<=", "=="）
    threshold: float  # 阈值
    action: str  # 动作："filter" (过滤) 或 "clip" (截断)
    clip_value: float | None = None  # 截断值（当 action 为 clip 时使用）
    description: str | None = None  # 规则描述


# 异常过滤规则配置
ANOMALY_FILTER_RULES: list[AnomalyFilterRule] = [
    # 心率异常过滤
    AnomalyFilterRule(
        field_name="avg_heart_rate",
        condition="<",
        threshold=30,
        action="filter",
        description="过滤平均心率过低的数据（< 30 bpm）",
    ),
    AnomalyFilterRule(
        field_name="avg_heart_rate",
        condition=">",
        threshold=220,
        action="filter",
        description="过滤平均心率过高的数据（> 220 bpm）",
    ),
    AnomalyFilterRule(
        field_name="max_heart_rate",
        condition="<",
        threshold=50,
        action="filter",
        description="过滤最大心率过低的数据（< 50 bpm）",
    ),
    AnomalyFilterRule(
        field_name="max_heart_rate",
        condition=">",
        threshold=250,
        action="filter",
        description="过滤最大心率过高的数据（> 250 bpm）",
    ),
    # 距离异常过滤
    AnomalyFilterRule(
        field_name="total_distance",
        condition="<",
        threshold=100,
        action="filter",
        description="过滤距离过短的数据（< 100 米）",
    ),
    AnomalyFilterRule(
        field_name="total_distance",
        condition=">",
        threshold=100000,
        action="filter",
        description="过滤距离过长的数据（> 100 公里）",
    ),
    # 时长异常过滤
    AnomalyFilterRule(
        field_name="total_timer_time",
        condition="<",
        threshold=60,
        action="filter",
        description="过滤时长过短的数据（< 1 分钟）",
    ),
    AnomalyFilterRule(
        field_name="total_timer_time",
        condition=">",
        threshold=28800,
        action="filter",
        description="过滤时长过长的数据（> 8 小时）",
    ),
    # 配速异常过滤（通过距离和时长计算）
    AnomalyFilterRule(
        field_name="pace_min_per_km",
        condition=">",
        threshold=20,
        action="filter",
        clip_value=20.0,
        description="过滤配速过慢的数据（> 20 min/km）",
    ),
    # VDOT 异常过滤
    AnomalyFilterRule(
        field_name="vdot",
        condition="<",
        threshold=20,
        action="filter",
        description="过滤 VDOT 过低的数据（< 20）",
    ),
    AnomalyFilterRule(
        field_name="vdot",
        condition=">",
        threshold=85,
        action="filter",
        description="过滤 VDOT 过高的数据（> 85）",
    ),
]


@dataclass
class RunnerProfile:  # type: ignore[no-redef]
    """跑者画像数据结构"""

    # 基本信息
    user_id: str
    profile_date: datetime
    total_activities: int = 0
    total_distance_km: float = 0.0
    total_duration_hours: float = 0.0

    # 体能指标
    avg_vdot: float = 0.0
    max_vdot: float = 0.0
    fitness_level: FitnessLevel = FitnessLevel.BEGINNER

    # 训练模式指标
    weekly_avg_distance_km: float = 0.0
    weekly_avg_duration_hours: float = 0.0
    training_pattern: TrainingPattern = TrainingPattern.REST

    # 心率指标
    avg_heart_rate: float | None = None
    max_heart_rate: float | None = None
    resting_heart_rate: float | None = None

    # 伤病风险
    injury_risk_level: InjuryRiskLevel = InjuryRiskLevel.LOW
    injury_risk_score: float = 0.0

    # 训练负荷
    atl: float = 0.0  # 急性训练负荷
    ctl: float = 0.0  # 慢性训练负荷
    tsb: float = 0.0  # 训练压力平衡

    # 其他指标
    avg_pace_min_per_km: float = 0.0
    favorite_running_time: str = "morning"  # morning, afternoon, evening
    consistency_score: float = 0.0  # 训练一致性评分 (0-100)

    # 元数据
    data_quality_score: float = 0.0  # 数据质量评分 (0-100)
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


class ProfileEngine:
    """用户画像引擎"""

    def __init__(self, context: AppContext) -> None:
        """
        初始化画像引擎

        Args:
            context: AppContext 实例
        """
        self.context = context
        self.storage = context.storage
        self.storage_manager = ProfileStorageManager()
        self.user_profile_manager = UserProfileManager(context.storage)
        self.injury_risk_analyzer = InjuryRiskAnalyzer()
        self.training_history_analyzer = TrainingHistoryAnalyzer(context.storage)
        self.anomaly_data_filter = AnomalyDataFilter()

    def build_profile(
        self,
        user_id: str = "default_user",
        days: int = 90,
        age: int = 30,
        resting_hr: int = 60,
    ) -> RunnerProfile:
        """
        基于历史数据构建用户画像

        Args:
            user_id: 用户 ID
            days: 分析天数，默认 90 天
            age: 年龄，用于计算最大心率
            resting_hr: 静息心率

        Returns:
            RunnerProfile: 用户画像对象

        Raises:
            ValueError: 当参数无效时
            RuntimeError: 当数据读取失败时
        """
        # 参数验证
        if days <= 0:
            raise ValueError("分析天数必须为正数")
        if age <= 0 or age > 120:
            raise ValueError("年龄必须在 1-120 之间")
        if resting_hr <= 0 or resting_hr > 200:
            raise ValueError("静息心率必须在合理范围内")

        # 读取数据
        lf = self._load_activity_data(days)

        # 检查是否有数据
        if self._is_empty_lazyframe(lf):
            return self._create_empty_profile(user_id, days)

        # 收集数据
        profile = RunnerProfile(user_id=user_id, profile_date=datetime.now())
        profile.analysis_period_days = days

        # 计算基础统计
        self._calculate_basic_stats(lf, profile)

        # 计算 VDOT 指标
        self._calculate_vdot_metrics(lf, profile)

        # 计算训练模式
        self._calculate_training_pattern(lf, profile, days)

        # 计算心率指标
        self._calculate_hr_metrics(lf, profile)

        # 计算训练负荷
        self._calculate_training_load(lf, profile)

        # 计算伤病风险（使用内部方法）
        self._calculate_injury_risk_internal(profile, age, resting_hr)

        # 计算其他指标
        self._calculate_additional_metrics(lf, profile, days)

        # 计算数据质量评分
        self._calculate_data_quality(lf, profile)

        return profile

    def get_fitness_level(self, avg_vdot: float) -> FitnessLevel:
        """
        根据平均 VDOT 值判断体能水平

        Args:
            avg_vdot: 平均 VDOT 值

        Returns:
            FitnessLevel: 体能水平等级

        Notes:
            - VDOT < 30: 初学者
            - VDOT 30-45: 中级
            - VDOT 45-60: 进阶
            - VDOT >= 60: 精英
        """
        if avg_vdot < 30:
            return FitnessLevel.BEGINNER
        elif avg_vdot < 45:
            return FitnessLevel.INTERMEDIATE
        elif avg_vdot < 60:
            return FitnessLevel.ADVANCED
        else:
            return FitnessLevel.ELITE

    def get_training_pattern(self, weekly_avg_distance_km: float) -> TrainingPattern:
        """
        根据周平均跑量判断训练模式

        Args:
            weekly_avg_distance_km: 周平均跑量（公里）

        Returns:
            TrainingPattern: 训练模式类型

        Notes:
            - < 10km: 休息型
            - 10-30km: 轻松型
            - 30-50km: 适度型
            - 50-80km: 高强度型
            - >= 80km: 极限型
        """
        if weekly_avg_distance_km < 10:
            return TrainingPattern.REST
        elif weekly_avg_distance_km < 30:
            return TrainingPattern.LIGHT
        elif weekly_avg_distance_km < 50:
            return TrainingPattern.MODERATE
        elif weekly_avg_distance_km < 80:
            return TrainingPattern.INTENSE
        else:
            return TrainingPattern.EXTREME

    def _calculate_injury_risk_internal(
        self,
        profile: RunnerProfile,
        age: int,
        resting_hr: int,
    ) -> None:
        """
        内部方法：计算伤病风险并更新画像

        Args:
            profile: 跑者画像对象
            age: 年龄
            resting_hr: 静息心率
        """
        self.calculate_injury_risk(profile, age, resting_hr)
        # 结果已经通过 calculate_injury_risk 更新到 profile

    def calculate_injury_risk(
        self,
        profile: RunnerProfile,
        age: int = 30,
        resting_hr: int = 60,
    ) -> dict[str, Any]:
        """
        计算伤病风险评分

        风险评估维度：
        1. 训练负荷突变（ATL/CTL 比率）
        2. 训练一致性
        3. 心率漂移
        4. 恢复情况（TSB）
        5. 年龄因素

        Args:
            profile: 跑者画像对象
            age: 年龄
            resting_hr: 静息心率

        Returns:
            dict: 伤病风险评估结果，包含：
                - risk_score: 风险评分 (0-100)
                - risk_level: 风险等级 (低/中/高)
                - risk_factors: 风险因素列表
                - recommendations: 建议列表

        Raises:
            ValueError: 当参数无效时
        """
        result = self.injury_risk_analyzer.calculate_injury_risk(
            profile, age, resting_hr
        )

        return {
            "risk_score": result.risk_score,
            "risk_level": result.risk_level.value,
            "risk_factors": result.risk_factors,
            "recommendations": result.recommendations,
        }

    def _load_activity_data(self, days: int) -> pl.LazyFrame:
        """
        加载指定天数的活动数据

        Args:
            days: 分析天数

        Returns:
            pl.LazyFrame: 活动数据 LazyFrame
        """
        from datetime import datetime, timedelta

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        try:
            lf = self.storage.read_parquet()

            if len(lf.collect_schema()) == 0:
                return lf

            lf = self._normalize_column_names(lf)

            if "timestamp" in lf.collect_schema().names():
                lf = lf.filter(pl.col("timestamp") >= start_date).filter(
                    pl.col("timestamp") <= end_date
                )

            return lf
        except Exception as e:
            raise RuntimeError(f"读取活动数据失败：{e}") from e

    def _normalize_column_names(self, lf: pl.LazyFrame) -> pl.LazyFrame:
        """
        规范化列名，将 session_ 前缀的列名映射为标准列名

        Args:
            lf: LazyFrame 对象

        Returns:
            pl.LazyFrame: 列名规范化后的 LazyFrame
        """
        schema = lf.collect_schema()
        columns = schema.names()

        column_mapping = {
            "session_total_distance": "total_distance",
            "session_total_timer_time": "total_timer_time",
            "session_avg_heart_rate": "avg_heart_rate",
            "session_max_heart_rate": "max_heart_rate",
            "session_avg_speed": "avg_speed",
            "session_max_speed": "max_speed",
            "session_avg_cadence": "avg_cadence",
            "session_max_cadence": "max_cadence",
            "session_avg_power": "avg_power",
            "session_max_power": "max_power",
            "session_total_calories": "total_calories",
            "session_total_ascent": "total_ascent",
            "session_total_descent": "total_descent",
            "session_start_time": "start_time",
        }

        rename_map = {}
        for old_name, new_name in column_mapping.items():
            if old_name in columns and new_name not in columns:
                rename_map[old_name] = new_name

        if rename_map:
            lf = lf.rename(rename_map)
            logger.debug(f"列名映射: {rename_map}")

        return lf

    def _is_empty_lazyframe(self, lf: pl.LazyFrame) -> bool:
        """
        检查 LazyFrame 是否为空

        Args:
            lf: LazyFrame 对象

        Returns:
            bool: 是否为空
        """
        try:
            # 检查是否有列
            if len(lf.collect_schema()) == 0:
                return True

            # 检查是否有数据
            df = lf.collect()
            return df.is_empty()
        except Exception:
            return True

    def _create_empty_profile(self, user_id: str, days: int) -> RunnerProfile:
        """
        创建空画像（无数据时）

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

    def _calculate_basic_stats(self, lf: pl.LazyFrame, profile: RunnerProfile) -> None:
        """
        计算基础统计数据

        Args:
            lf: LazyFrame 对象
            profile: 画像对象
        """
        try:
            df = lf.collect()

            if df.is_empty():
                return

            if "start_time" in df.columns:
                activities = df.group_by("start_time").agg(
                    [
                        pl.col("total_distance").first(),
                        pl.col("total_timer_time").first(),
                    ]
                )
                profile.total_activities = activities.height
                profile.total_distance_km = (
                    float(activities["total_distance"].sum()) / 1000.0
                )
                profile.total_duration_hours = (
                    float(activities["total_timer_time"].sum()) / 3600.0
                )
            else:
                profile.total_activities = df.height
                profile.total_distance_km = float(df["total_distance"].sum()) / 1000.0
                profile.total_duration_hours = (
                    float(df["total_timer_time"].sum()) / 3600.0
                )

            if profile.total_distance_km > 0 and profile.total_duration_hours > 0:
                profile.avg_pace_min_per_km = (
                    profile.total_duration_hours * 60
                ) / profile.total_distance_km
        except Exception as e:
            logger.warning(f"计算基础统计失败：{e}")

    def _calculate_vdot_metrics(self, lf: pl.LazyFrame, profile: RunnerProfile) -> None:
        """
        计算 VDOT 指标

        Args:
            lf: LazyFrame 对象
            profile: 画像对象
        """
        try:
            analytics = self.context.analytics

            df = lf.collect()

            if df.is_empty():
                return

            if "start_time" in df.columns:
                activities = df.group_by("start_time").agg(
                    [
                        pl.col("total_distance").first(),
                        pl.col("total_timer_time").first(),
                    ]
                )
                activity_rows = activities.iter_rows(named=True)
            else:
                activity_rows = df.iter_rows(named=True)

            vdot_values = []
            for row in activity_rows:
                distance_raw = row.get("total_distance")
                duration_raw = row.get("total_timer_time")
                distance = float(distance_raw) if distance_raw is not None else 0.0
                duration = float(duration_raw) if duration_raw is not None else 0.0

                if distance >= 1500 and duration > 0:
                    try:
                        vdot = analytics.calculate_vdot(distance, duration)
                        vdot_values.append(vdot)
                    except ValueError:
                        pass

            if vdot_values:
                profile.avg_vdot = sum(vdot_values) / len(vdot_values)
                profile.max_vdot = max(vdot_values)
                profile.fitness_level = self.get_fitness_level(profile.avg_vdot)  # type: ignore[assignment]
        except Exception as e:
            logger.warning(f"计算 VDOT 指标失败：{e}")

    def _calculate_training_pattern(
        self, lf: pl.LazyFrame, profile: RunnerProfile, days: int
    ) -> None:
        """
        计算训练模式

        Args:
            lf: LazyFrame 对象
            profile: 画像对象
            days: 分析天数
        """
        try:
            df = lf.collect()

            if df.is_empty():
                return

            # 计算周数
            weeks = max(days / 7, 1)

            # 计算周平均跑量
            profile.weekly_avg_distance_km = profile.total_distance_km / weeks
            profile.weekly_avg_duration_hours = profile.total_duration_hours / weeks

            # 判断训练模式
            profile.training_pattern = self.get_training_pattern(
                profile.weekly_avg_distance_km
            )
        except Exception as e:
            logger.warning(f"计算训练模式失败：{e}")

    def _calculate_hr_metrics(self, lf: pl.LazyFrame, profile: RunnerProfile) -> None:
        """
        计算心率指标

        Args:
            lf: LazyFrame 对象
            profile: 画像对象
        """
        try:
            df = lf.collect()

            if df.is_empty():
                return

            # 检查是否有心率字段
            if "avg_heart_rate" not in df.columns:
                return

            # 过滤有效心率数据
            hr_df = df.filter(
                (pl.col("avg_heart_rate").is_not_null())
                & (pl.col("avg_heart_rate") > 0)
            )

            if not hr_df.is_empty():
                avg_hr = hr_df["avg_heart_rate"].mean()
                max_hr = hr_df["max_heart_rate"].max()
                profile.avg_heart_rate = float(avg_hr) if avg_hr is not None else None  # type: ignore[arg-type,assignment]
                profile.max_heart_rate = float(max_hr) if max_hr is not None else None  # type: ignore[arg-type,assignment]
        except Exception as e:
            logger.warning(f"计算心率指标失败：{e}")

    def _calculate_training_load(
        self, lf: pl.LazyFrame, profile: RunnerProfile
    ) -> None:
        """
        计算训练负荷（ATL/CTL/TSB）

        Args:
            lf: LazyFrame 对象
            profile: 画像对象
        """
        try:
            analytics = self.context.analytics

            df = lf.collect()

            if df.is_empty():
                return

            # 计算每次跑步的 TSS
            tss_values = []
            for row in df.iter_rows(named=True):
                tss = analytics.calculate_tss_for_run(
                    distance_m=row.get("total_distance") or 0,
                    duration_s=row.get("total_timer_time") or 0,
                    avg_heart_rate=row.get("avg_heart_rate"),
                )
                if tss > 0:
                    tss_values.append(tss)

            if tss_values:
                # 计算 ATL 和 CTL
                load_data = analytics.calculate_atl_ctl(tss_values)
                profile.atl = load_data.get("atl", 0.0)
                profile.ctl = load_data.get("ctl", 0.0)
                profile.tsb = profile.ctl - profile.atl
        except Exception as e:
            logger.warning(f"计算训练负荷失败：{e}")

    def _calculate_additional_metrics(
        self, lf: pl.LazyFrame, profile: RunnerProfile, days: int
    ) -> None:
        """
        计算其他指标（训练时间偏好、一致性等）

        Args:
            lf: LazyFrame 对象
            profile: 画像对象
            days: 分析天数
        """
        try:
            df = lf.collect()

            if df.is_empty():
                return

            if "start_time" in df.columns:
                activities = df.group_by("start_time").agg(
                    [pl.col("start_time").first().alias("activity_start_time")]
                )
                profile.favorite_running_time = self._analyze_running_time_preference(
                    activities["activity_start_time"]
                )
            elif "timestamp" in df.columns:
                activities = df.group_by("timestamp").agg(
                    [pl.col("timestamp").first().alias("activity_start_time")]
                )
                profile.favorite_running_time = self._analyze_running_time_preference(
                    activities["activity_start_time"]
                )

            profile.consistency_score = self._calculate_consistency_score(df, days)
        except Exception as e:
            logger.warning(f"计算其他指标失败：{e}")

    def _analyze_running_time_preference(self, timestamps: pl.Series) -> str:
        """
        分析跑步时间偏好

        Args:
            timestamps: 时间戳序列（UTC 时间）

        Returns:
            str: 偏好时间段（morning/afternoon/evening）
        """
        try:
            beijing_hours = [
                (t + timedelta(hours=8)).hour for t in timestamps.to_list()
            ]

            morning_count = sum(1 for h in beijing_hours if 5 <= h < 12)
            afternoon_count = sum(1 for h in beijing_hours if 12 <= h < 18)
            evening_count = sum(1 for h in beijing_hours if h >= 18 or h < 5)

            if morning_count >= afternoon_count and morning_count >= evening_count:
                return "morning"
            elif afternoon_count >= evening_count:
                return "afternoon"
            else:
                return "evening"
        except Exception:
            return "morning"

    def _calculate_consistency_score(self, df: pl.DataFrame, days: int) -> float:
        """
        计算训练一致性评分（0-100）

        基于：
        1. 每周跑步天数
        2. 训练间隔的规律性

        Args:
            df: DataFrame 对象
            days: 分析天数

        Returns:
            float: 一致性评分 (0-100)
        """
        try:
            if df.is_empty():
                return 0.0

            # 计算每周跑步天数
            weeks = max(days / 7, 1)
            total_runs = df.height
            runs_per_week = total_runs / weeks

            # 基础分：基于每周跑步次数（满分 60 分）
            base_score = min(runs_per_week / 5 * 60, 60)

            # 规律性评分（满分 40 分）
            if total_runs >= 2:
                # 计算训练间隔的标准差
                timestamps = df["timestamp"].sort()
                intervals = []
                for i in range(1, len(timestamps)):
                    # Polars 的 timedelta 直接转换为秒
                    delta = timestamps[i] - timestamps[i - 1]
                    # 转换为天数（delta 是 timedelta 对象）
                    if hasattr(delta, "total_seconds"):
                        interval_days = delta.total_seconds() / 86400
                    else:
                        # Polars 表达式的情况
                        interval_days = delta.dt.total_seconds() / 86400
                    intervals.append(interval_days)

                if intervals:
                    intervals_series = pl.Series(intervals)
                    std_dev_value = intervals_series.std()
                    std_dev = float(std_dev_value) if std_dev_value is not None else 0.0  # type: ignore[arg-type]

                    # 标准差越小，规律性越好（满分 40 分）
                    # 标准差 0 天 = 40 分，标准差 3 天 = 0 分
                    regularity_score = max(40 - (std_dev / 3 * 40), 0)
                else:
                    regularity_score = 0
            else:
                regularity_score = 0

            consistency_score = base_score + regularity_score
            return min(max(consistency_score, 0), 100)
        except Exception:
            return 0.0

    def _calculate_data_quality(self, lf: pl.LazyFrame, profile: RunnerProfile) -> None:
        """
        计算数据质量评分（0-100）

        基于：
        1. 数据完整性（必填字段）
        2. 心率数据覆盖率
        3. 数据量充足度

        Args:
            lf: LazyFrame 对象
            profile: 画像对象
        """
        try:
            df = lf.collect()

            if df.is_empty():
                profile.data_quality_score = 0.0
                return

            score = 0.0

            # 1. 数据量充足度（满分 40 分）
            # 90 天内至少 10 次跑步为满分
            runs_per_90_days = df.height / max(profile.analysis_period_days / 90, 1)
            quantity_score = min(runs_per_90_days / 10 * 40, 40)
            score += quantity_score

            # 2. 心率数据覆盖率（满分 40 分）
            if "avg_heart_rate" in df.columns:
                hr_df = df.filter(
                    (pl.col("avg_heart_rate").is_not_null())
                    & (pl.col("avg_heart_rate") > 0)
                )
                hr_ratio = hr_df.height / df.height
                hr_score = hr_ratio * 40
                score += hr_score

            # 3. 距离数据完整性（满分 20 分）
            distance_df = df.filter(
                (pl.col("total_distance").is_not_null())
                & (pl.col("total_distance") > 0)
            )
            distance_ratio = distance_df.height / df.height
            distance_score = distance_ratio * 20
            score += distance_score

            profile.data_quality_score = min(max(score, 0), 100)
        except Exception as e:
            logger.warning(f"计算数据质量评分失败：{e}")
            profile.data_quality_score = 0.0

    def check_freshness(
        self,
        profile: RunnerProfile | None = None,
        freshness_days: int = 7,
    ) -> ProfileStaleStatus:
        """
        检查画像保鲜期

        基于画像最后更新时间判断是否过期

        Args:
            profile: 画像对象，如果为 None 则尝试从 storage 加载
            freshness_days: 保鲜期天数，默认 7 天

        Returns:
            ProfileStaleStatus: 画像保鲜期状态

        Raises:
            RuntimeError: 当加载画像失败时
        """
        try:
            # 如果未提供 profile，尝试从 storage 加载
            if profile is None:
                profile = self.storage_manager.load_profile_json()

            # 检查是否存在画像
            if profile is None:
                logger.debug("画像不存在，状态为 MISSING")
                return ProfileStaleStatus.MISSING

            # 计算时间差
            now = datetime.now()
            time_diff = now - profile.profile_date

            # 判断是否过期
            if time_diff.total_seconds() <= freshness_days * 24 * 3600:
                logger.debug(f"画像新鲜（{time_diff.days} 天前更新）")
                return ProfileStaleStatus.FRESH
            else:
                logger.debug(
                    f"画像过期（{time_diff.days} 天前更新，阈值{freshness_days}天）"
                )
                return ProfileStaleStatus.STALE

        except Exception as e:
            logger.error(f"检查画像保鲜期失败：{e}")
            raise RuntimeError(f"检查画像保鲜期失败：{e}") from e

    def filter_anomaly_data(
        self,
        data: pl.LazyFrame,
        rules: list[AnomalyFilterRule] | None = None,
        strict_mode: bool = False,
    ) -> pl.LazyFrame:
        """
        过滤异常数据

        根据预定义的异常过滤规则过滤数据集中的异常记录

        Args:
            data: 输入的 LazyFrame 数据
            rules: 过滤规则列表，如果为 None 则使用 ANOMALY_FILTER_RULES
            strict_mode: 严格模式，如果为 True 则过滤掉任何触发规则的数据，
                        如果为 False 则仅过滤严重异常数据

        Returns:
            pl.LazyFrame: 过滤后的 LazyFrame

        Raises:
            ValueError: 当输入数据为空或规则无效时
            RuntimeError: 当过滤失败时

        Notes:
            - 支持两种过滤动作：filter（直接过滤）和 clip（截断到阈值）
            - 严格模式下，所有规则都会生效
            - 非严格模式下，仅严重异常数据会被过滤（如心率<30 或>220）
        """
        try:
            # 检查输入数据
            if len(data.collect_schema()) == 0:
                raise ValueError("输入数据为空")

            # 使用默认规则
            if rules is None:
                rules = ANOMALY_FILTER_RULES

            if not rules:
                logger.debug("未提供过滤规则，返回原始数据")
                return data

            # 逐条应用过滤规则
            filtered_data = data
            for rule in rules:
                try:
                    # 检查字段是否存在
                    if rule.field_name not in filtered_data.collect_schema().names():
                        logger.debug(
                            f"字段 {rule.field_name} 不存在，跳过规则：{rule.description}"
                        )
                        continue

                    # 构建过滤条件
                    condition = self._build_filter_condition(rule, strict_mode)
                    if condition is None:
                        continue

                    # 应用过滤
                    if rule.action == "filter":
                        # 过滤掉不满足条件的数据（保留满足条件的数据）
                        if rule.condition == "<":
                            filtered_data = filtered_data.filter(
                                pl.col(rule.field_name) >= rule.threshold
                            )
                        elif rule.condition == ">":
                            filtered_data = filtered_data.filter(
                                pl.col(rule.field_name) <= rule.threshold
                            )
                        elif rule.condition == "<=":
                            filtered_data = filtered_data.filter(
                                pl.col(rule.field_name) > rule.threshold
                            )
                        elif rule.condition == ">=":
                            filtered_data = filtered_data.filter(
                                pl.col(rule.field_name) < rule.threshold
                            )
                        elif rule.condition == "==":
                            filtered_data = filtered_data.filter(
                                pl.col(rule.field_name) != rule.threshold
                            )
                        logger.debug(f"应用过滤规则：{rule.description}")

                    elif rule.action == "clip":
                        # 截断处理
                        if rule.condition == ">" and rule.clip_value is not None:
                            filtered_data = filtered_data.with_columns(
                                pl.when(pl.col(rule.field_name) > rule.threshold)
                                .then(rule.clip_value)
                                .otherwise(pl.col(rule.field_name))
                                .alias(rule.field_name)
                            )
                            logger.debug(f"应用截断规则：{rule.description}")

                except Exception as e:
                    logger.warning(f"应用规则失败（{rule.field_name}）: {e}")
                    if strict_mode:
                        raise

            logger.info(
                f"异常数据过滤完成，原始行数：{data.collect().height}, "
                f"过滤后行数：{filtered_data.collect().height}"
            )
            return filtered_data

        except Exception as e:
            logger.error(f"异常数据过滤失败：{e}")
            raise RuntimeError(f"异常数据过滤失败：{e}") from e

    def _build_filter_condition(
        self,
        rule: AnomalyFilterRule,
        strict_mode: bool,
    ) -> pl.Expr | None:
        """
        构建过滤条件表达式

        Args:
            rule: 过滤规则
            strict_mode: 严格模式

        Returns:
            Optional[pl.Expr]: 过滤条件表达式，如果为 None 表示不应用此规则
        """
        # 非严格模式下，仅应用严重异常规则
        if not strict_mode:
            # 严重异常阈值
            severe_thresholds = {
                "avg_heart_rate": [(30, "<"), (220, ">")],
                "max_heart_rate": [(50, "<"), (250, ">")],
                "total_distance": [(100, "<"), (100000, ">")],
                "total_timer_time": [(60, "<"), (28800, ">")],
            }

            if rule.field_name in severe_thresholds:
                thresholds = severe_thresholds[rule.field_name]
                if (rule.threshold, rule.condition) not in thresholds:
                    logger.debug(f"非严格模式，跳过非严重异常规则：{rule.field_name}")
                    return None

        # 构建条件表达式
        return pl.col(rule.field_name)
