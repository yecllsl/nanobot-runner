# UserProfileManager 单元测试

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.core.user_profile_manager import (
    FitnessLevel,
    InjuryRiskLevel,
    ProfileStorageManager,
    RunnerProfile,
    TrainingPattern,
    UserProfileManager,
)


@pytest.fixture
def temp_workspace(tmp_path: Path) -> Path:
    """创建临时工作目录"""
    workspace = tmp_path / "test_workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "data").mkdir(parents=True, exist_ok=True)
    (workspace / "memory").mkdir(parents=True, exist_ok=True)
    return workspace


@pytest.fixture
def mock_storage() -> MagicMock:
    """创建模拟 StorageManager"""
    return MagicMock()


@pytest.fixture
def profile_manager(
    temp_workspace: Path, mock_storage: MagicMock
) -> UserProfileManager:
    """创建 UserProfileManager 实例"""
    return UserProfileManager(mock_storage, temp_workspace)


@pytest.fixture
def storage_manager(temp_workspace: Path) -> ProfileStorageManager:
    """创建 ProfileStorageManager 实例"""
    return ProfileStorageManager(temp_workspace)


@pytest.fixture
def sample_profile() -> RunnerProfile:
    """创建示例画像"""
    return RunnerProfile(
        user_id="test_user",
        profile_date=datetime.now(),
        total_activities=50,
        total_distance_km=500.0,
        total_duration_hours=50.0,
        avg_vdot=45.0,
        max_vdot=48.0,
        fitness_level=FitnessLevel.INTERMEDIATE,
        weekly_avg_distance_km=35.0,
        weekly_avg_duration_hours=4.0,
        training_pattern=TrainingPattern.LIGHT,
        avg_heart_rate=150,
        max_heart_rate=180,
        resting_heart_rate=60,
        injury_risk_level=InjuryRiskLevel.LOW,
        injury_risk_score=20.0,
        atl=50.0,
        ctl=60.0,
        tsb=10.0,
        avg_pace_min_per_km=5.5,
        favorite_running_time="morning",
        consistency_score=85.0,
        data_quality_score=90.0,
        analysis_period_days=90,
        notes=["测试备注"],
    )


class TestRunnerProfile:
    """RunnerProfile 测试类"""

    def test_to_dict_success(self, sample_profile: RunnerProfile) -> None:
        """测试转换为字典"""
        result = sample_profile.to_dict()

        assert result["user_id"] == "test_user"
        assert result["total_activities"] == 50
        assert result["total_distance_km"] == 500.0
        assert result["fitness_level"] == "intermediate"
        assert result["training_pattern"] == "light"
        assert result["injury_risk_level"] == "low"


class TestProfileStorageManager:
    """ProfileStorageManager 测试类"""

    def test_init_creates_directories(self, temp_workspace: Path) -> None:
        """测试初始化时创建目录"""
        _ = ProfileStorageManager(temp_workspace)

        assert (temp_workspace / "data").exists()
        assert (temp_workspace / "memory").exists()

    def test_save_profile_json_success(
        self, storage_manager: ProfileStorageManager, sample_profile: RunnerProfile
    ) -> None:
        """测试保存画像到 JSON"""
        result = storage_manager.save_profile_json(sample_profile)

        assert result is True
        assert storage_manager.profile_json_path.exists()

    def test_load_profile_json_success(
        self, storage_manager: ProfileStorageManager, sample_profile: RunnerProfile
    ) -> None:
        """测试从 JSON 加载画像"""
        storage_manager.save_profile_json(sample_profile)

        loaded = storage_manager.load_profile_json()

        assert loaded is not None
        assert loaded.user_id == sample_profile.user_id
        assert loaded.total_activities == sample_profile.total_activities

    def test_load_profile_json_not_exists(
        self, storage_manager: ProfileStorageManager
    ) -> None:
        """测试加载不存在的画像"""
        result = storage_manager.load_profile_json()

        assert result is None

    def test_save_memory_md_success(
        self, storage_manager: ProfileStorageManager, sample_profile: RunnerProfile
    ) -> None:
        """测试保存画像到 MEMORY.md"""
        result = storage_manager.save_memory_md(sample_profile)

        assert result is True
        assert storage_manager.memory_md_path.exists()

        content = storage_manager.memory_md_path.read_text(encoding="utf-8")
        assert "跑者画像" in content
        assert sample_profile.user_id in content

    def test_generate_memory_content(
        self, storage_manager: ProfileStorageManager, sample_profile: RunnerProfile
    ) -> None:
        """测试生成 MEMORY.md 内容"""
        content = storage_manager._generate_memory_content(sample_profile)

        assert "# 跑者画像" in content
        assert sample_profile.user_id in content
        assert "基础信息" in content
        assert "体能水平" in content
        assert "训练模式" in content
        assert "心率数据" in content
        assert "训练负荷" in content
        assert "伤病风险" in content

    def test_dict_to_profile_conversion(
        self, storage_manager: ProfileStorageManager, sample_profile: RunnerProfile
    ) -> None:
        """测试字典与画像对象的相互转换"""
        profile_dict = sample_profile.to_dict()
        converted = storage_manager._dict_to_profile(profile_dict)

        assert converted.user_id == sample_profile.user_id
        assert converted.total_activities == sample_profile.total_activities
        assert converted.fitness_level == sample_profile.fitness_level

    def test_load_profile_json_with_invalid_json(
        self, storage_manager: ProfileStorageManager
    ) -> None:
        """测试加载无效 JSON 文件"""
        storage_manager.profile_json_path.write_text("invalid json", encoding="utf-8")

        result = storage_manager.load_profile_json()

        assert result is None


class TestUserProfileManager:
    """UserProfileManager 测试类"""

    def test_save_profile_success(
        self, profile_manager: UserProfileManager, sample_profile: RunnerProfile
    ) -> None:
        """测试保存画像"""
        result = profile_manager.save_profile(sample_profile)

        assert result is True

    def test_load_profile_success(
        self, profile_manager: UserProfileManager, sample_profile: RunnerProfile
    ) -> None:
        """测试加载画像"""
        profile_manager.save_profile(sample_profile)

        loaded = profile_manager.load_profile()

        assert loaded is not None
        assert loaded.user_id == sample_profile.user_id

    def test_load_profile_not_exists(self, profile_manager: UserProfileManager) -> None:
        """测试加载不存在的画像"""
        result = profile_manager.load_profile()

        assert result is None

    def test_get_fitness_level_beginner(
        self, profile_manager: UserProfileManager
    ) -> None:
        """测试获取体能水平 - 初学者"""
        result = profile_manager.get_fitness_level(25.0)
        assert result == FitnessLevel.BEGINNER

    def test_get_fitness_level_intermediate(
        self, profile_manager: UserProfileManager
    ) -> None:
        """测试获取体能水平 - 中级"""
        result = profile_manager.get_fitness_level(40.0)
        assert result == FitnessLevel.INTERMEDIATE

    def test_get_fitness_level_advanced(
        self, profile_manager: UserProfileManager
    ) -> None:
        """测试获取体能水平 - 高级"""
        result = profile_manager.get_fitness_level(55.0)
        assert result == FitnessLevel.ADVANCED

    def test_get_fitness_level_elite(self, profile_manager: UserProfileManager) -> None:
        """测试获取体能水平 - 精英"""
        result = profile_manager.get_fitness_level(65.0)
        assert result == FitnessLevel.ELITE

    def test_get_training_pattern_casual(
        self, profile_manager: UserProfileManager
    ) -> None:
        """测试获取训练模式 - 休息型"""
        result = profile_manager.get_training_pattern(15.0)
        assert result == TrainingPattern.REST

    def test_get_training_pattern_regular(
        self, profile_manager: UserProfileManager
    ) -> None:
        """测试获取训练模式 - 轻松型"""
        result = profile_manager.get_training_pattern(35.0)
        assert result == TrainingPattern.LIGHT

    def test_get_training_pattern_intensive(
        self, profile_manager: UserProfileManager
    ) -> None:
        """测试获取训练模式 - 适度型"""
        result = profile_manager.get_training_pattern(55.0)
        assert result == TrainingPattern.MODERATE

    def test_get_training_pattern_professional(
        self, profile_manager: UserProfileManager
    ) -> None:
        """测试获取训练模式 - 高强度型"""
        result = profile_manager.get_training_pattern(80.0)
        assert result == TrainingPattern.INTENSE

    def test_create_empty_profile(self, profile_manager: UserProfileManager) -> None:
        """测试创建空画像"""
        profile = profile_manager.create_empty_profile("test_user", 90)

        assert profile.user_id == "test_user"
        assert profile.analysis_period_days == 90
        assert profile.data_quality_score == 0.0
        assert "暂无跑步数据" in profile.notes[0]
