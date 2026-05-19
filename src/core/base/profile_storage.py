# 画像双存储管理器
# 管理 profile.json 和 MEMORY.md 的持久化
# 本模块从 profile.py 拆分而来 (Task 20)

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from src.core.base.logger import get_logger
from src.core.base.profile_schema import RunnerProfile
from src.core.models import FitnessLevel, InjuryRiskLevel, TrainingPattern

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

    def save_profile_json(self, profile: RunnerProfile | dict[str, Any]) -> bool:
        """
        保存画像到 profile.json

        Args:
            profile: RunnerProfile 对象或字典

        Returns:
            bool: 保存是否成功

        Raises:
            RuntimeError: 当保存失败时
        """
        try:
            if isinstance(profile, dict):
                profile_data = profile.copy()
                user_id = profile_data.get("user_id", "default_user")
            else:
                profile_data = profile.to_dict()
                user_id = profile.user_id

            profile_data["updated_at"] = datetime.now().isoformat()

            with open(self.profile_json_path, "w", encoding="utf-8") as f:
                json.dump(profile_data, f, indent=2, ensure_ascii=False)

            logger.info(f"画像已保存到 profile.json: {user_id}")

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
            agent_notes: list[str] = []

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

            # 处理枚举（容错：无效值使用默认值）
            fitness_level_str = profile_data.get("fitness_level", "beginner")
            try:
                fitness_level = FitnessLevel(fitness_level_str)
            except ValueError:
                fitness_level = FitnessLevel.BEGINNER

            training_pattern_str = profile_data.get("training_pattern", "rest")
            try:
                training_pattern = TrainingPattern(training_pattern_str)
            except ValueError:
                training_pattern = TrainingPattern.REST

            injury_risk_level_str = profile_data.get("injury_risk_level", "low")
            try:
                injury_risk_level = InjuryRiskLevel(injury_risk_level_str)
            except ValueError:
                injury_risk_level = InjuryRiskLevel.LOW

            # 创建对象
            profile = RunnerProfile(
                user_id=profile_data.get("user_id", "default_user"),
                profile_date=profile_date,
                total_activities=profile_data.get("total_activities", 0),
                total_distance_km=profile_data.get("total_distance_km", 0.0),
                total_duration_hours=profile_data.get("total_duration_hours", 0.0),
                avg_vdot=profile_data.get("avg_vdot", 0.0),
                max_vdot=profile_data.get("max_vdot", 0.0),
                fitness_level=fitness_level,
                weekly_avg_distance_km=profile_data.get("weekly_avg_distance_km", 0.0),
                weekly_avg_duration_hours=profile_data.get(
                    "weekly_avg_duration_hours", 0.0
                ),
                training_pattern=training_pattern,
                avg_heart_rate=profile_data.get("avg_heart_rate"),
                max_heart_rate=profile_data.get("max_heart_rate"),
                resting_heart_rate=profile_data.get("resting_heart_rate"),
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
        agent_notes: list[str] = []

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
        agent_notes: list[str] = []
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
        agent_notes: list[str] = []
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
