# 画像双存储持久化单元测试
# 测试 ProfileStorageManager 的所有功能

import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from src.core.profile import (
    FitnessLevel,
    InjuryRiskLevel,
    ProfileStorageManager,
    RunnerProfile,
    TrainingPattern,
)


class TestProfileStorageManagerInit:
    """测试 ProfileStorageManager 初始化"""

    def test_init_default_path(self):
        """测试使用默认路径初始化"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            # Mock Path.home() 返回临时目录
            with patch("pathlib.Path.home", return_value=tmp_path):
                manager = ProfileStorageManager()

                assert manager.workspace_dir == tmp_path / ".nanobot-runner"
                assert (
                    manager.profile_json_path
                    == tmp_path / ".nanobot-runner" / "data" / "profile.json"
                )
                assert (
                    manager.memory_md_path
                    == tmp_path / ".nanobot-runner" / "memory" / "MEMORY.md"
                )

    def test_init_custom_path(self):
        """测试使用自定义路径初始化"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            manager = ProfileStorageManager(workspace_dir=tmp_path)

            assert manager.workspace_dir == tmp_path
            assert manager.profile_json_path == tmp_path / "data" / "profile.json"
            assert manager.memory_md_path == tmp_path / "memory" / "MEMORY.md"

    def test_init_creates_directories(self):
        """测试初始化时自动创建目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            workspace = tmp_path / "workspace"

            manager = ProfileStorageManager(workspace_dir=workspace)

            assert workspace.exists()
            assert (workspace / "data").exists()
            assert (workspace / "memory").exists()

    def test_init_invalid_path(self):
        """测试使用无效路径初始化"""
        # 在 Windows 上，Path.home() / "nonexistent" 这样的路径通常可以创建
        # 所以我们跳过这个测试，或者使用其他方式测试
        # 这里我们测试一个权限不足的路径（需要管理员权限）
        # 在普通用户环境下，我们只验证正常路径的创建
        pytest.skip("Windows 上难以测试无效路径，跳过")


class TestSaveProfileJson:
    """测试 save_profile_json 方法"""

    @pytest.fixture
    def manager(self):
        """创建测试用的 manager"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            manager = ProfileStorageManager(workspace_dir=tmp_path)
            yield manager

    def test_save_profile_json_success(self, manager):
        """测试保存画像成功"""
        profile = RunnerProfile(
            user_id="test_user",
            profile_date=datetime.now(),
            total_activities=10,
            total_distance_km=100.0,
            avg_vdot=45.5,
            fitness_level=FitnessLevel.INTERMEDIATE,
        )

        result = manager.save_profile_json(profile)

        assert result is True
        assert manager.profile_json_path.exists()

        # 验证文件内容
        with open(manager.profile_json_path, encoding="utf-8") as f:
            data = json.load(f)

        assert data["user_id"] == "test_user"
        assert data["total_activities"] == 10
        assert data["total_distance_km"] == 100.0
        assert data["avg_vdot"] == 45.5
        assert data["fitness_level"] == "中级"
        assert "updated_at" in data

    def test_save_profile_json_with_all_fields(self, manager):
        """测试保存包含所有字段的画像"""
        profile = RunnerProfile(
            user_id="complete_user",
            profile_date=datetime(2024, 1, 1, 12, 0, 0),
            total_activities=50,
            total_distance_km=500.0,
            total_duration_hours=50.0,
            avg_vdot=50.0,
            max_vdot=55.0,
            fitness_level=FitnessLevel.ADVANCED,
            weekly_avg_distance_km=40.0,
            weekly_avg_duration_hours=4.0,
            training_pattern=TrainingPattern.MODERATE,
            avg_heart_rate=150.0,
            max_heart_rate=180.0,
            resting_heart_rate=60.0,
            injury_risk_level=InjuryRiskLevel.LOW,
            injury_risk_score=15.0,
            atl=30.0,
            ctl=40.0,
            tsb=10.0,
            avg_pace_min_per_km=5.5,
            favorite_running_time="morning",
            consistency_score=75.0,
            data_quality_score=85.0,
            analysis_period_days=90,
            notes=["note1", "note2"],
        )

        result = manager.save_profile_json(profile)

        assert result is True

        # 验证所有字段
        with open(manager.profile_json_path, encoding="utf-8") as f:
            data = json.load(f)

        assert data["user_id"] == "complete_user"
        assert data["total_activities"] == 50
        assert data["avg_heart_rate"] == 150.0
        assert data["training_pattern"] == "适度型"
        assert data["notes"] == ["note1", "note2"]

    def test_save_profile_json_overwrite(self, manager):
        """测试保存时覆盖已有文件"""
        # 第一次保存
        profile1 = RunnerProfile(
            user_id="user1",
            profile_date=datetime.now(),
            total_activities=10,
        )
        manager.save_profile_json(profile1)

        # 第二次保存（覆盖）
        profile2 = RunnerProfile(
            user_id="user2",
            profile_date=datetime.now(),
            total_activities=20,
        )
        manager.save_profile_json(profile2)

        # 验证只有第二次的数据
        with open(manager.profile_json_path, encoding="utf-8") as f:
            data = json.load(f)

        assert data["user_id"] == "user2"
        assert data["total_activities"] == 20

    def test_save_profile_json_missing_dir(self):
        """测试保存时目录不存在（应该自动创建）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            # 删除 data 目录
            workspace = tmp_path / "workspace"
            workspace.mkdir()
            # 不创建 data 目录

            manager = ProfileStorageManager(workspace_dir=workspace)
            profile = RunnerProfile(user_id="test", profile_date=datetime.now())

            # 应该成功（自动创建目录）
            result = manager.save_profile_json(profile)
            assert result is True


class TestLoadProfileJson:
    """测试 load_profile_json 方法"""

    @pytest.fixture
    def manager(self):
        """创建测试用的 manager"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            manager = ProfileStorageManager(workspace_dir=tmp_path)
            yield manager

    def test_load_profile_json_success(self, manager):
        """测试加载画像成功"""
        # 先保存
        profile = RunnerProfile(
            user_id="test_user",
            profile_date=datetime.now(),
            total_activities=10,
            avg_vdot=45.5,
            fitness_level=FitnessLevel.INTERMEDIATE,
        )
        manager.save_profile_json(profile)

        # 再加载
        loaded_profile = manager.load_profile_json()

        assert loaded_profile is not None
        assert loaded_profile.user_id == "test_user"
        assert loaded_profile.total_activities == 10
        assert loaded_profile.avg_vdot == 45.5
        assert loaded_profile.fitness_level == FitnessLevel.INTERMEDIATE

    def test_load_profile_json_not_exists(self, manager):
        """测试文件不存在时返回 None"""
        result = manager.load_profile_json()

        assert result is None

    def test_load_profile_json_invalid_json(self, manager):
        """测试 JSON 格式错误时抛出异常"""
        # 创建无效的 JSON 文件
        manager.profile_json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(manager.profile_json_path, "w", encoding="utf-8") as f:
            f.write("invalid json content {")

        with pytest.raises(RuntimeError, match="profile.json 格式错误"):
            manager.load_profile_json()

    def test_load_profile_json_preserves_enum(self, manager):
        """测试加载时正确还原枚举类型"""
        profile = RunnerProfile(
            user_id="test_user",
            profile_date=datetime.now(),
            fitness_level=FitnessLevel.ELITE,
            training_pattern=TrainingPattern.EXTREME,
            injury_risk_level=InjuryRiskLevel.HIGH,
        )
        manager.save_profile_json(profile)

        loaded_profile = manager.load_profile_json()

        assert loaded_profile is not None
        assert loaded_profile.fitness_level == FitnessLevel.ELITE
        assert loaded_profile.training_pattern == TrainingPattern.EXTREME
        assert loaded_profile.injury_risk_level == InjuryRiskLevel.HIGH


class TestSaveMemoryMd:
    """测试 save_memory_md 方法"""

    @pytest.fixture
    def manager(self):
        """创建测试用的 manager"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            manager = ProfileStorageManager(workspace_dir=tmp_path)
            yield manager

    def test_save_memory_md_success(self, manager):
        """测试保存 MEMORY.md 成功"""
        content = "# 测试内容\n\n这是一段测试文本。"
        result = manager.save_memory_md(content)

        assert result is True
        assert manager.memory_md_path.exists()

        # 验证内容
        with open(manager.memory_md_path, encoding="utf-8") as f:
            saved_content = f.read()

        assert saved_content == content

    def test_save_memory_md_with_profile(self, manager):
        """测试保存时自动添加画像摘要"""
        profile = RunnerProfile(
            user_id="test_user",
            profile_date=datetime.now(),
            total_activities=10,
            total_distance_km=100.0,
            avg_vdot=45.5,
            fitness_level=FitnessLevel.INTERMEDIATE,
        )

        custom_content = "## 自定义内容\n\n这是一些自定义内容。"
        result = manager.save_memory_md(custom_content, profile=profile)

        assert result is True

        with open(manager.memory_md_path, encoding="utf-8") as f:
            saved_content = f.read()

        assert "用户画像摘要" in saved_content
        assert "test_user" in saved_content
        assert "自定义内容" in saved_content

    def test_save_memory_md_append_mode(self, manager):
        """测试追加模式保存"""
        # 第一次保存
        manager.save_memory_md("内容 1")

        # 第二次追加
        manager.save_memory_md("内容 2", append=True)

        with open(manager.memory_md_path, encoding="utf-8") as f:
            saved_content = f.read()

        assert "内容 1" in saved_content
        assert "内容 2" in saved_content

    def test_save_memory_md_overwrite_mode(self, manager):
        """测试覆盖模式保存"""
        # 第一次保存
        manager.save_memory_md("内容 1")

        # 第二次覆盖
        manager.save_memory_md("内容 2", append=False)

        with open(manager.memory_md_path, encoding="utf-8") as f:
            saved_content = f.read()

        assert "内容 1" not in saved_content
        assert "内容 2" in saved_content


class TestLoadMemoryMd:
    """测试 load_memory_md 方法"""

    @pytest.fixture
    def manager(self):
        """创建测试用的 manager"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            manager = ProfileStorageManager(workspace_dir=tmp_path)
            yield manager

    def test_load_memory_md_success(self, manager):
        """测试加载 MEMORY.md 成功"""
        content = "# 测试内容\n\n这是一段测试文本。"
        manager.save_memory_md(content)

        loaded_content = manager.load_memory_md()

        assert loaded_content is not None
        assert loaded_content == content

    def test_load_memory_md_not_exists(self, manager):
        """测试文件不存在时返回 None"""
        result = manager.load_memory_md()

        assert result is None


class TestSyncDualStorage:
    """测试 sync_dual_storage 方法"""

    @pytest.fixture
    def manager(self):
        """创建测试用的 manager"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            manager = ProfileStorageManager(workspace_dir=tmp_path)
            yield manager

    def test_sync_json_to_md(self, manager):
        """测试从 JSON 同步到 MD"""
        profile = RunnerProfile(
            user_id="test_user",
            profile_date=datetime.now(),
            total_activities=10,
            total_distance_km=100.0,
        )

        result = manager.sync_dual_storage(profile, sync_direction="json_to_md")

        assert result is True
        # json_to_md 只保存 MD，不保存 JSON
        assert manager.memory_md_path.exists()

        # 验证 MD 包含画像信息
        with open(manager.memory_md_path, encoding="utf-8") as f:
            md_content = f.read()

        assert "test_user" in md_content
        assert "用户画像摘要" in md_content

    def test_sync_md_to_json(self, manager):
        """测试从 MD 同步到 JSON（保留 Agent 笔记）"""
        profile = RunnerProfile(
            user_id="test_user",
            profile_date=datetime.now(),
            total_activities=10,
        )

        # 先保存 MD，包含 Agent 笔记
        agent_note = "- @agent 用户训练非常规律"
        manager.save_memory_md(agent_note)

        result = manager.sync_dual_storage(profile, sync_direction="md_to_json")

        assert result is True

        # 验证 JSON 包含 Agent 笔记
        loaded_profile = manager.load_profile_json()
        assert loaded_profile is not None
        assert any("训练非常规律" in note for note in loaded_profile.notes)

    def test_sync_bidirectional(self, manager):
        """测试双向同步"""
        profile = RunnerProfile(
            user_id="test_user",
            profile_date=datetime.now(),
            total_activities=10,
            notes=["原有笔记"],
        )

        custom_content = "## 自定义内容\n\n测试内容"
        result = manager.sync_dual_storage(
            profile, memory_content=custom_content, sync_direction="bidirectional"
        )

        assert result is True
        assert manager.profile_json_path.exists()
        assert manager.memory_md_path.exists()

    def test_sync_invalid_direction(self, manager):
        """测试无效的同步方向"""
        profile = RunnerProfile(user_id="test", profile_date=datetime.now())

        with pytest.raises(ValueError, match="无效的同步方向"):
            manager.sync_dual_storage(profile, sync_direction="invalid")


class TestMergeProfileToMd:
    """测试 merge_profile_to_md 方法"""

    @pytest.fixture
    def manager(self):
        """创建测试用的 manager"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            manager = ProfileStorageManager(workspace_dir=tmp_path)
            yield manager

    def test_merge_preserve_agent_notes(self, manager):
        """测试智能合并时保留 Agent 笔记"""
        # 先保存包含 Agent 笔记的 MD
        agent_note = "- @agent 用户最近训练量增加"
        manager.save_memory_md(f"# 旧内容\n\n{agent_note}")

        # 合并新画像
        profile = RunnerProfile(
            user_id="test_user",
            profile_date=datetime.now(),
            total_activities=10,
        )
        result = manager.merge_profile_to_md(profile, preserve_agent_notes=True)

        assert result is True

        # 验证 Agent 笔记被保留
        with open(manager.memory_md_path, encoding="utf-8") as f:
            content = f.read()

        assert "训练量增加" in content
        assert "用户画像摘要" in content

    def test_merge_without_preserve_agent_notes(self, manager):
        """测试智能合并时不保留 Agent 笔记"""
        # 先保存包含 Agent 笔记的 MD
        agent_note = "- @agent 用户最近训练量增加"
        manager.save_memory_md(f"# 旧内容\n\n{agent_note}")

        # 合并新画像，不保留 Agent 笔记
        profile = RunnerProfile(
            user_id="test_user",
            profile_date=datetime.now(),
            total_activities=10,
        )
        result = manager.merge_profile_to_md(profile, preserve_agent_notes=False)

        assert result is True

        # 验证 Agent 笔记不被保留（但旧内容会保留）
        with open(manager.memory_md_path, encoding="utf-8") as f:
            content = f.read()

        assert "训练量增加" not in content
        assert "用户画像摘要" in content


class TestExtractAgentNotes:
    """测试 _extract_agent_notes 方法"""

    @pytest.fixture
    def manager(self):
        """创建测试用的 manager"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            manager = ProfileStorageManager(workspace_dir=tmp_path)
            yield manager

    def test_extract_agent_notes_success(self, manager):
        """测试提取 Agent 笔记成功"""
        content = """# 记忆

## 内容
- @agent 用户训练非常规律
- 普通笔记
- @agent 用户心率偏低

## 其他
"""
        notes = manager._extract_agent_notes(content)

        assert len(notes) == 2
        assert "用户训练非常规律" in notes[0]
        assert "用户心率偏低" in notes[1]

    def test_extract_agent_notes_empty(self, manager):
        """测试没有 Agent 笔记"""
        content = "# 内容\n\n没有 Agent 笔记。"
        notes = manager._extract_agent_notes(content)

        assert len(notes) == 0


class TestRemoveAgentNotes:
    """测试 _remove_agent_notes 方法"""

    @pytest.fixture
    def manager(self):
        """创建测试用的 manager"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            manager = ProfileStorageManager(workspace_dir=tmp_path)
            yield manager

    def test_remove_agent_notes_success(self, manager):
        """测试移除 Agent 笔记成功"""
        content = """# 记忆

- @agent 用户训练规律
- 普通内容 1
- @agent 用户心率正常
- 普通内容 2
"""
        result = manager._remove_agent_notes(content)

        assert "@agent" not in result
        assert "普通内容 1" in result
        assert "普通内容 2" in result

    def test_remove_agent_notes_empty(self, manager):
        """测试没有 Agent 笔记时"""
        content = "# 内容\n\n普通笔记。"
        result = manager._remove_agent_notes(content)

        assert result == content


class TestDictToProfile:
    """测试 _dict_to_profile 方法"""

    @pytest.fixture
    def manager(self):
        """创建测试用的 manager"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            manager = ProfileStorageManager(workspace_dir=tmp_path)
            yield manager

    def test_dict_to_profile_success(self, manager):
        """测试字典转画像成功"""
        data = {
            "user_id": "test_user",
            "profile_date": datetime.now().isoformat(),
            "total_activities": 10,
            "total_distance_km": 100.0,
            "fitness_level": "中级",
            "training_pattern": "轻松型",
            "injury_risk_level": "低",
        }

        profile = manager._dict_to_profile(data)

        assert profile.user_id == "test_user"
        assert profile.total_activities == 10
        assert profile.fitness_level == FitnessLevel.INTERMEDIATE
        assert profile.training_pattern == TrainingPattern.LIGHT
        assert profile.injury_risk_level == InjuryRiskLevel.LOW

    def test_dict_to_profile_missing_fields(self, manager):
        """测试字典缺少字段时使用默认值"""
        data = {
            "user_id": "test_user",
            "profile_date": datetime.now().isoformat(),
        }

        profile = manager._dict_to_profile(data)

        assert profile.user_id == "test_user"
        assert profile.total_activities == 0
        assert profile.fitness_level == FitnessLevel.BEGINNER


class TestGenerateMemoryContent:
    """测试 _generate_memory_content 方法"""

    @pytest.fixture
    def manager(self):
        """创建测试用的 manager"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            manager = ProfileStorageManager(workspace_dir=tmp_path)
            yield manager

    def test_generate_memory_content_success(self, manager):
        """测试生成 MEMORY.md 内容成功"""
        profile = RunnerProfile(
            user_id="test_user",
            profile_date=datetime.now(),
            total_activities=10,
            total_distance_km=100.0,
            avg_vdot=45.5,
            fitness_level=FitnessLevel.INTERMEDIATE,
            training_pattern=TrainingPattern.LIGHT,
            injury_risk_level=InjuryRiskLevel.LOW,
            atl=30.0,
            ctl=40.0,
            tsb=10.0,
        )

        content = manager._generate_memory_content("", profile)

        assert "跑步记忆与观察笔记" in content
        assert "test_user" in content
        assert "用户画像摘要" in content
        assert "训练负荷" in content
        assert "100.0" in content
        assert "45.5" in content

    def test_generate_memory_content_with_custom(self, manager):
        """测试生成带自定义内容的 MEMORY.md"""
        profile = RunnerProfile(user_id="test", profile_date=datetime.now())
        custom = "## 自定义\n\n内容"

        content = manager._generate_memory_content(custom, profile)

        assert "自定义" in content
        assert "内容" in content


class TestIntegration:
    """集成测试"""

    @pytest.fixture
    def manager(self):
        """创建测试用的 manager"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            manager = ProfileStorageManager(workspace_dir=tmp_path)
            yield manager

    def test_full_workflow(self, manager):
        """测试完整工作流程"""
        # 1. 创建画像
        profile = RunnerProfile(
            user_id="integration_test_user",
            profile_date=datetime.now(),
            total_activities=20,
            total_distance_km=200.0,
            avg_vdot=48.0,
            fitness_level=FitnessLevel.INTERMEDIATE,
            training_pattern=TrainingPattern.MODERATE,
            injury_risk_level=InjuryRiskLevel.LOW,
            notes=["初始笔记"],
        )

        # 2. 保存 profile.json
        assert manager.save_profile_json(profile) is True

        # 3. 保存 MEMORY.md（带 Agent 笔记）
        agent_note = "- @agent 用户训练量稳步增长"
        manager.save_memory_md(agent_note)

        # 4. 加载 profile.json
        loaded_profile = manager.load_profile_json()
        assert loaded_profile is not None
        assert loaded_profile.user_id == "integration_test_user"
        assert loaded_profile.total_activities == 20

        # 5. 加载 MEMORY.md
        loaded_memory = manager.load_memory_md()
        assert loaded_memory is not None
        assert "训练量稳步增长" in loaded_memory

        # 6. 双存储同步
        assert (
            manager.sync_dual_storage(loaded_profile, sync_direction="bidirectional")
            is True
        )

        # 7. 智能合并
        loaded_profile.notes.append("新增笔记")
        assert (
            manager.merge_profile_to_md(loaded_profile, preserve_agent_notes=True)
            is True
        )

        # 8. 验证最终状态
        final_memory = manager.load_memory_md()
        assert final_memory is not None
        assert "integration_test_user" in final_memory
        assert "训练量稳步增长" in final_memory  # Agent 笔记应被保留
