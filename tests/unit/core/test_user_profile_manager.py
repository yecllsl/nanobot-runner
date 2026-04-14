# UserProfileManager单元测试
# 测试用户画像管理器的核心功能

import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock

import pytest

from src.core.models import FitnessLevel, InjuryRiskLevel, TrainingPattern
from src.core.user_profile_manager import (
    ProfileStorageManager,
    RunnerProfile,
    UserProfileManager,
)


class TestRunnerProfile:
    """RunnerProfile数据类测试"""

    def test_runner_profile_creation(self):
        """测试创建RunnerProfile"""
        profile = RunnerProfile(
            user_id="test_user",
            profile_date=datetime(2024, 1, 1),
            total_activities=10,
            total_distance_km=50.0,
        )

        assert profile.user_id == "test_user"
        assert profile.total_activities == 10
        assert profile.total_distance_km == 50.0

    def test_runner_profile_to_dict(self):
        """测试转换为字典"""
        profile = RunnerProfile(
            user_id="test_user",
            profile_date=datetime(2024, 1, 1, 10, 30, 0),
            total_activities=10,
            total_distance_km=50.123,
            avg_vdot=40.5,
            fitness_level=FitnessLevel.INTERMEDIATE,
        )

        result = profile.to_dict()

        assert result["user_id"] == "test_user"
        assert result["total_activities"] == 10
        assert result["total_distance_km"] == 50.12
        assert result["avg_vdot"] == 40.5
        assert result["fitness_level"] == "intermediate"
        assert "profile_date" in result

    def test_runner_profile_default_values(self):
        """测试默认值"""
        profile = RunnerProfile(user_id="test_user", profile_date=datetime(2024, 1, 1))

        assert profile.total_activities == 0
        assert profile.total_distance_km == 0.0
        assert profile.avg_vdot == 0.0
        assert profile.fitness_level == FitnessLevel.BEGINNER
        assert profile.training_pattern == TrainingPattern.REST
        assert profile.injury_risk_level == InjuryRiskLevel.LOW
        assert profile.notes == []


class TestProfileStorageManager:
    """ProfileStorageManager测试"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def storage_manager(self, temp_dir):
        """创建ProfileStorageManager实例"""
        return ProfileStorageManager(workspace_dir=temp_dir)

    @pytest.fixture
    def sample_profile(self):
        """创建示例画像"""
        profile = RunnerProfile(
            user_id="test_user",
            profile_date=datetime(2024, 1, 1),
            total_activities=10,
            total_distance_km=50.0,
            total_duration_hours=5.0,
            avg_vdot=40.0,
            max_vdot=45.0,
            fitness_level=FitnessLevel.INTERMEDIATE,
            weekly_avg_distance_km=20.0,
            training_pattern=TrainingPattern.LIGHT,
            avg_heart_rate=150,
            max_heart_rate=180,
            resting_heart_rate=60,
            injury_risk_level=InjuryRiskLevel.LOW,
            injury_risk_score=10.0,
            atl=50.0,
            ctl=60.0,
            tsb=10.0,
            avg_pace_min_per_km=5.5,
            favorite_running_time="morning",
            consistency_score=80.0,
            data_quality_score=90.0,
            analysis_period_days=90,
            notes=["测试备注"],
        )
        return profile

    def test_init_creates_directories(self, temp_dir):
        """测试初始化创建目录"""
        storage_manager = ProfileStorageManager(workspace_dir=temp_dir)

        assert (temp_dir / "data").exists()
        assert (temp_dir / "memory").exists()

    def test_save_profile_json(self, storage_manager, sample_profile):
        """测试保存profile.json"""
        result = storage_manager.save_profile_json(sample_profile)

        assert result is True
        assert storage_manager.profile_json_path.exists()

        with open(storage_manager.profile_json_path, encoding="utf-8") as f:
            data = json.load(f)

        assert data["user_id"] == "test_user"
        assert data["total_activities"] == 10
        assert "updated_at" in data

    def test_load_profile_json(self, storage_manager, sample_profile):
        """测试加载profile.json"""
        storage_manager.save_profile_json(sample_profile)

        loaded_profile = storage_manager.load_profile_json()

        assert loaded_profile is not None
        assert loaded_profile.user_id == "test_user"
        assert loaded_profile.total_activities == 10
        assert loaded_profile.total_distance_km == 50.0

    def test_load_profile_json_not_exists(self, storage_manager):
        """测试加载不存在的profile.json"""
        result = storage_manager.load_profile_json()

        assert result is None

    def test_load_profile_json_invalid_json(self, storage_manager):
        """测试加载无效的JSON文件"""
        with open(storage_manager.profile_json_path, "w", encoding="utf-8") as f:
            f.write("invalid json content")

        result = storage_manager.load_profile_json()

        assert result is None

    def test_save_memory_md(self, storage_manager, sample_profile):
        """测试保存MEMORY.md"""
        result = storage_manager.save_memory_md(sample_profile)

        assert result is True
        assert storage_manager.memory_md_path.exists()

        with open(storage_manager.memory_md_path, encoding="utf-8") as f:
            content = f.read()

        assert "# 跑者画像" in content
        assert "test_user" in content
        assert "50.00 km" in content
        assert "intermediate" in content

    def test_generate_memory_content(self, storage_manager, sample_profile):
        """测试生成MEMORY.md内容"""
        content = storage_manager._generate_memory_content(sample_profile)

        assert "# 跑者画像" in content
        assert "test_user" in content
        assert "## 基础信息" in content
        assert "## 体能水平" in content
        assert "## 训练模式" in content
        assert "## 心率数据" in content
        assert "## 训练负荷" in content
        assert "## 伤病风险" in content
        assert "测试备注" in content

    def test_dict_to_profile(self, storage_manager):
        """测试字典转换为画像"""
        data = {
            "user_id": "test_user",
            "profile_date": "2024-01-01T10:00:00",
            "total_activities": 10,
            "total_distance_km": 50.0,
            "fitness_level": "intermediate",
            "training_pattern": "light",
            "injury_risk_level": "low",
        }

        profile = storage_manager._dict_to_profile(data)

        assert profile.user_id == "test_user"
        assert profile.total_activities == 10
        assert profile.fitness_level == FitnessLevel.INTERMEDIATE
        assert profile.training_pattern == TrainingPattern.LIGHT
        assert profile.injury_risk_level == InjuryRiskLevel.LOW

    def test_dict_to_profile_invalid_enum(self, storage_manager):
        """测试无效枚举值的处理"""
        data = {
            "user_id": "test_user",
            "profile_date": "2024-01-01T10:00:00",
            "fitness_level": "invalid_level",
            "training_pattern": "invalid_pattern",
            "injury_risk_level": "invalid_risk",
        }

        profile = storage_manager._dict_to_profile(data)

        assert profile.fitness_level == FitnessLevel.BEGINNER
        assert profile.training_pattern == TrainingPattern.REST
        assert profile.injury_risk_level == InjuryRiskLevel.LOW

    def test_dict_to_profile_missing_fields(self, storage_manager):
        """测试缺失字段的处理"""
        data = {"user_id": "test_user"}

        profile = storage_manager._dict_to_profile(data)

        assert profile.user_id == "test_user"
        assert profile.total_activities == 0
        assert profile.total_distance_km == 0.0


class TestUserProfileManager:
    """UserProfileManager测试"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def mock_storage(self):
        """创建mock StorageManager"""
        return Mock()

    @pytest.fixture
    def manager(self, mock_storage, temp_dir):
        """创建UserProfileManager实例"""
        return UserProfileManager(mock_storage, workspace_dir=temp_dir)

    @pytest.fixture
    def sample_profile(self):
        """创建示例画像"""
        return RunnerProfile(
            user_id="test_user",
            profile_date=datetime(2024, 1, 1),
            total_activities=10,
            total_distance_km=50.0,
            avg_vdot=40.0,
            fitness_level=FitnessLevel.INTERMEDIATE,
        )

    def test_init(self, manager, temp_dir):
        """测试初始化"""
        assert manager.storage is not None
        assert manager.storage_manager is not None
        assert manager.storage_manager.workspace_dir == temp_dir

    def test_save_profile(self, manager, sample_profile):
        """测试保存画像"""
        result = manager.save_profile(sample_profile)

        assert result is True
        assert manager.storage_manager.profile_json_path.exists()
        assert manager.storage_manager.memory_md_path.exists()

    def test_load_profile(self, manager, sample_profile):
        """测试加载画像"""
        manager.save_profile(sample_profile)

        loaded_profile = manager.load_profile()

        assert loaded_profile is not None
        assert loaded_profile.user_id == "test_user"
        assert loaded_profile.total_activities == 10

    def test_load_profile_not_exists(self, manager):
        """测试加载不存在的画像"""
        result = manager.load_profile()

        assert result is None

    def test_get_fitness_level_beginner(self, manager):
        """测试初学者水平"""
        level = manager.get_fitness_level(30.0)
        assert level == FitnessLevel.BEGINNER

    def test_get_fitness_level_intermediate(self, manager):
        """测试中级水平"""
        level = manager.get_fitness_level(40.0)
        assert level == FitnessLevel.INTERMEDIATE

    def test_get_fitness_level_advanced(self, manager):
        """测试进阶水平"""
        level = manager.get_fitness_level(55.0)
        assert level == FitnessLevel.ADVANCED

    def test_get_fitness_level_elite(self, manager):
        """测试精英水平"""
        level = manager.get_fitness_level(65.0)
        assert level == FitnessLevel.ELITE

    def test_get_fitness_level_boundary_beginner(self, manager):
        """测试初学者边界值"""
        level = manager.get_fitness_level(34.9)
        assert level == FitnessLevel.BEGINNER

    def test_get_fitness_level_boundary_intermediate(self, manager):
        """测试中级边界值"""
        level = manager.get_fitness_level(35.0)
        assert level == FitnessLevel.INTERMEDIATE

    def test_get_fitness_level_boundary_advanced(self, manager):
        """测试进阶边界值"""
        level = manager.get_fitness_level(50.0)
        assert level == FitnessLevel.ADVANCED

    def test_get_fitness_level_boundary_elite(self, manager):
        """测试精英边界值"""
        level = manager.get_fitness_level(60.0)
        assert level == FitnessLevel.ELITE

    def test_get_training_pattern_rest(self, manager):
        """测试休息型"""
        pattern = manager.get_training_pattern(10.0)
        assert pattern == TrainingPattern.REST

    def test_get_training_pattern_light(self, manager):
        """测试轻松型"""
        pattern = manager.get_training_pattern(30.0)
        assert pattern == TrainingPattern.LIGHT

    def test_get_training_pattern_moderate(self, manager):
        """测试适度型"""
        pattern = manager.get_training_pattern(60.0)
        assert pattern == TrainingPattern.MODERATE

    def test_get_training_pattern_intense(self, manager):
        """测试高强度型"""
        pattern = manager.get_training_pattern(80.0)
        assert pattern == TrainingPattern.INTENSE

    def test_get_training_pattern_extreme(self, manager):
        """测试极限型"""
        pattern = manager.get_training_pattern(120.0)
        assert pattern == TrainingPattern.EXTREME

    def test_get_training_pattern_boundary_rest(self, manager):
        """测试休息型边界值"""
        pattern = manager.get_training_pattern(19.9)
        assert pattern == TrainingPattern.REST

    def test_get_training_pattern_boundary_light(self, manager):
        """测试轻松型边界值"""
        pattern = manager.get_training_pattern(20.0)
        assert pattern == TrainingPattern.LIGHT

    def test_get_training_pattern_boundary_moderate(self, manager):
        """测试适度型边界值"""
        pattern = manager.get_training_pattern(50.0)
        assert pattern == TrainingPattern.MODERATE

    def test_get_training_pattern_boundary_intense(self, manager):
        """测试高强度型边界值"""
        pattern = manager.get_training_pattern(70.0)
        assert pattern == TrainingPattern.INTENSE

    def test_get_training_pattern_boundary_extreme(self, manager):
        """测试极限型边界值"""
        pattern = manager.get_training_pattern(100.0)
        assert pattern == TrainingPattern.EXTREME

    def test_create_empty_profile(self, manager):
        """测试创建空画像"""
        profile = manager.create_empty_profile("test_user", days=90)

        assert profile.user_id == "test_user"
        assert profile.total_activities == 0
        assert profile.total_distance_km == 0.0
        assert profile.analysis_period_days == 90
        assert profile.data_quality_score == 0.0
        assert len(profile.notes) > 0
        assert "暂无跑步数据" in profile.notes[0]


class TestIntegration:
    """集成测试"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def mock_storage(self):
        """创建mock StorageManager"""
        return Mock()

    @pytest.fixture
    def manager(self, mock_storage, temp_dir):
        """创建UserProfileManager实例"""
        return UserProfileManager(mock_storage, workspace_dir=temp_dir)

    def test_save_and_load_cycle(self, manager):
        """测试保存和加载循环"""
        profile = RunnerProfile(
            user_id="test_user",
            profile_date=datetime(2024, 1, 1),
            total_activities=10,
            total_distance_km=50.0,
            total_duration_hours=5.0,
            avg_vdot=40.0,
            max_vdot=45.0,
            fitness_level=FitnessLevel.INTERMEDIATE,
            weekly_avg_distance_km=20.0,
            weekly_avg_duration_hours=2.0,
            training_pattern=TrainingPattern.LIGHT,
            avg_heart_rate=150,
            max_heart_rate=180,
            resting_heart_rate=60,
            injury_risk_level=InjuryRiskLevel.LOW,
            injury_risk_score=10.0,
            atl=50.0,
            ctl=60.0,
            tsb=10.0,
            avg_pace_min_per_km=5.5,
            favorite_running_time="morning",
            consistency_score=80.0,
            data_quality_score=90.0,
            analysis_period_days=90,
            notes=["测试备注"],
        )

        manager.save_profile(profile)
        loaded_profile = manager.load_profile()

        assert loaded_profile is not None
        assert loaded_profile.user_id == profile.user_id
        assert loaded_profile.total_activities == profile.total_activities
        assert loaded_profile.total_distance_km == profile.total_distance_km
        assert loaded_profile.avg_vdot == profile.avg_vdot
        assert loaded_profile.fitness_level == profile.fitness_level
        assert loaded_profile.training_pattern == profile.training_pattern
        assert loaded_profile.injury_risk_level == profile.injury_risk_level

    def test_overwrite_profile(self, manager):
        """测试覆盖画像"""
        profile1 = RunnerProfile(
            user_id="test_user",
            profile_date=datetime(2024, 1, 1),
            total_activities=10,
            total_distance_km=50.0,
        )

        manager.save_profile(profile1)

        profile2 = RunnerProfile(
            user_id="test_user",
            profile_date=datetime(2024, 1, 2),
            total_activities=20,
            total_distance_km=100.0,
        )

        manager.save_profile(profile2)

        loaded_profile = manager.load_profile()

        assert loaded_profile is not None
        assert loaded_profile.total_activities == 20
        assert loaded_profile.total_distance_km == 100.0
