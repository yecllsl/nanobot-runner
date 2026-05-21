# EvolutionConfig 配置类单元测试

from __future__ import annotations

import pytest

from src.core.evolution.config import EvolutionConfig


class TestEvolutionConfigDefaults:
    """EvolutionConfig 默认值测试"""

    def test_default_data_dir(self):
        """测试默认数据目录"""
        config = EvolutionConfig()
        assert config.data_dir == "~/.nanobot-runner"

    def test_default_async_write_enabled(self):
        """测试默认异步写入开关"""
        config = EvolutionConfig()
        assert config.async_write_enabled is False

    def test_default_async_write_queue_size(self):
        """测试默认异步写入队列大小"""
        config = EvolutionConfig()
        assert config.async_write_queue_size == 100

    def test_default_async_write_max_retries(self):
        """测试默认异步写入最大重试次数"""
        config = EvolutionConfig()
        assert config.async_write_max_retries == 3

    def test_default_async_write_retry_backoff(self):
        """测试默认异步写入重试退避时间"""
        config = EvolutionConfig()
        assert config.async_write_retry_backoff == 1.0

    def test_default_feedback_prompt_frequency(self):
        """测试默认反馈提示频率"""
        config = EvolutionConfig()
        assert config.feedback_prompt_frequency == 3

    def test_default_runner_state_fields(self):
        """测试默认跑者状态追踪字段"""
        config = EvolutionConfig()
        assert config.runner_state_fields == [
            "vdot",
            "ctl",
            "atl",
            "tsb",
            "fatigue_score",
        ]


class TestEvolutionConfigCustomValues:
    """EvolutionConfig 自定义值测试"""

    def test_custom_values(self):
        """测试自定义配置值"""
        config = EvolutionConfig(
            data_dir="/custom/path",
            async_write_enabled=True,
            async_write_queue_size=200,
            async_write_max_retries=5,
            async_write_retry_backoff=2.5,
            feedback_prompt_frequency=5,
            runner_state_fields=["vdot", "ctl"],
        )
        assert config.data_dir == "/custom/path"
        assert config.async_write_enabled is True
        assert config.async_write_queue_size == 200
        assert config.async_write_max_retries == 5
        assert config.async_write_retry_backoff == 2.5
        assert config.feedback_prompt_frequency == 5
        assert config.runner_state_fields == ["vdot", "ctl"]


class TestEvolutionConfigFrozen:
    """EvolutionConfig 不可变性测试"""

    def test_frozen_immutable(self):
        """测试frozen dataclass不可修改"""
        config = EvolutionConfig()
        with pytest.raises(AttributeError):
            config.data_dir = "/new/path"  # type: ignore[misc]

    def test_frozen_runner_state_fields_immutable(self):
        """测试frozen dataclass的runner_state_fields不可重新赋值"""
        config = EvolutionConfig()
        with pytest.raises(AttributeError):
            config.runner_state_fields = ["new_field"]  # type: ignore[misc]


class TestEvolutionConfigToDict:
    """EvolutionConfig to_dict 测试"""

    def test_to_dict_default_values(self):
        """测试默认值序列化为字典"""
        config = EvolutionConfig()
        d = config.to_dict()
        assert d["data_dir"] == "~/.nanobot-runner"
        assert d["async_write_enabled"] is False
        assert d["async_write_queue_size"] == 100
        assert d["async_write_max_retries"] == 3
        assert d["async_write_retry_backoff"] == 1.0
        assert d["feedback_prompt_frequency"] == 3
        assert d["runner_state_fields"] == [
            "vdot",
            "ctl",
            "atl",
            "tsb",
            "fatigue_score",
        ]

    def test_to_dict_returns_list_for_runner_state_fields(self):
        """测试runner_state_fields序列化为list"""
        config = EvolutionConfig()
        d = config.to_dict()
        assert isinstance(d["runner_state_fields"], list)

    def test_to_dict_custom_values(self):
        """测试自定义值序列化为字典"""
        config = EvolutionConfig(
            data_dir="/custom",
            async_write_enabled=True,
            feedback_prompt_frequency=7,
        )
        d = config.to_dict()
        assert d["data_dir"] == "/custom"
        assert d["async_write_enabled"] is True
        assert d["feedback_prompt_frequency"] == 7


class TestEvolutionConfigFromDict:
    """EvolutionConfig from_dict 测试"""

    def test_from_dict_all_fields(self):
        """测试从完整字典创建配置"""
        d = {
            "data_dir": "/from/dict",
            "async_write_enabled": True,
            "async_write_queue_size": 50,
            "async_write_max_retries": 2,
            "async_write_retry_backoff": 0.5,
            "feedback_prompt_frequency": 10,
            "runner_state_fields": ["vdot", "ctl"],
        }
        config = EvolutionConfig.from_dict(d)
        assert config.data_dir == "/from/dict"
        assert config.async_write_enabled is True
        assert config.async_write_queue_size == 50
        assert config.async_write_max_retries == 2
        assert config.async_write_retry_backoff == 0.5
        assert config.feedback_prompt_frequency == 10
        assert config.runner_state_fields == ["vdot", "ctl"]

    def test_from_dict_partial_fields(self):
        """测试从部分字典创建配置（缺失字段使用默认值）"""
        d = {"data_dir": "/partial"}
        config = EvolutionConfig.from_dict(d)
        assert config.data_dir == "/partial"
        assert config.async_write_enabled is False
        assert config.feedback_prompt_frequency == 3

    def test_from_dict_ignores_invalid_keys(self):
        """测试from_dict忽略无效key"""
        d = {
            "data_dir": "/valid",
            "unknown_key": "should_be_ignored",
            "another_invalid": 42,
        }
        config = EvolutionConfig.from_dict(d)
        assert config.data_dir == "/valid"
        # 确保无效key不会导致异常

    def test_from_dict_roundtrip(self):
        """测试to_dict/from_dict往返一致性"""
        original = EvolutionConfig(
            data_dir="/roundtrip",
            async_write_enabled=True,
            async_write_queue_size=150,
            feedback_prompt_frequency=6,
            runner_state_fields=["vdot", "fatigue_score"],
        )
        d = original.to_dict()
        restored = EvolutionConfig.from_dict(d)
        assert restored.data_dir == original.data_dir
        assert restored.async_write_enabled == original.async_write_enabled
        assert restored.async_write_queue_size == original.async_write_queue_size
        assert restored.async_write_max_retries == original.async_write_max_retries
        assert restored.async_write_retry_backoff == original.async_write_retry_backoff
        assert restored.feedback_prompt_frequency == original.feedback_prompt_frequency
        assert restored.runner_state_fields == original.runner_state_fields


class TestEvolutionConfigValidation:
    """EvolutionConfig 验证规则测试"""

    def test_feedback_prompt_frequency_zero_raises(self):
        """测试feedback_prompt_frequency=0应抛出ValueError"""
        with pytest.raises(ValueError, match="feedback_prompt_frequency"):
            EvolutionConfig(feedback_prompt_frequency=0)

    def test_feedback_prompt_frequency_negative_raises(self):
        """测试feedback_prompt_frequency为负数应抛出ValueError"""
        with pytest.raises(ValueError, match="feedback_prompt_frequency"):
            EvolutionConfig(feedback_prompt_frequency=-1)

    def test_feedback_prompt_frequency_one_is_valid(self):
        """测试feedback_prompt_frequency=1是合法的"""
        config = EvolutionConfig(feedback_prompt_frequency=1)
        assert config.feedback_prompt_frequency == 1

    def test_async_write_queue_size_zero_raises(self):
        """测试async_write_queue_size=0应抛出ValueError"""
        with pytest.raises(ValueError, match="async_write_queue_size"):
            EvolutionConfig(async_write_queue_size=0)

    def test_async_write_queue_size_negative_raises(self):
        """测试async_write_queue_size为负数应抛出ValueError"""
        with pytest.raises(ValueError, match="async_write_queue_size"):
            EvolutionConfig(async_write_queue_size=-1)

    def test_async_write_queue_size_one_is_valid(self):
        """测试async_write_queue_size=1是合法的"""
        config = EvolutionConfig(async_write_queue_size=1)
        assert config.async_write_queue_size == 1

    def test_async_write_max_retries_negative_raises(self):
        """测试async_write_max_retries为负数应抛出ValueError"""
        with pytest.raises(ValueError, match="async_write_max_retries"):
            EvolutionConfig(async_write_max_retries=-1)

    def test_async_write_max_retries_zero_is_valid(self):
        """测试async_write_max_retries=0是合法的（不重试）"""
        config = EvolutionConfig(async_write_max_retries=0)
        assert config.async_write_max_retries == 0


class TestEvolutionConfigV024:
    """EvolutionConfig v0.24校准配置扩展测试"""

    def test_default_calibration_fields(self):
        config = EvolutionConfig()
        assert config.calibration_alpha == 0.7
        assert config.calibration_max_amplitude == 0.10
        assert config.calibration_min_samples == 10
        assert config.response_min_fidelity == 0.7
        assert config.response_min_samples_per_type == 5
        assert config.window_min_months == 6

    def test_custom_calibration_fields(self):
        config = EvolutionConfig(
            calibration_alpha=0.5,
            calibration_max_amplitude=0.15,
            calibration_min_samples=20,
            response_min_fidelity=0.8,
            response_min_samples_per_type=8,
            window_min_months=3,
        )
        assert config.calibration_alpha == 0.5
        assert config.calibration_max_amplitude == 0.15

    def test_calibration_alpha_validation(self):
        with pytest.raises(ValueError, match="calibration_alpha"):
            EvolutionConfig(calibration_alpha=0.0)
        with pytest.raises(ValueError, match="calibration_alpha"):
            EvolutionConfig(calibration_alpha=1.1)

    def test_calibration_max_amplitude_validation(self):
        with pytest.raises(ValueError, match="calibration_max_amplitude"):
            EvolutionConfig(calibration_max_amplitude=0.0)
        with pytest.raises(ValueError, match="calibration_max_amplitude"):
            EvolutionConfig(calibration_max_amplitude=1.5)

    def test_calibration_min_samples_validation(self):
        with pytest.raises(ValueError, match="calibration_min_samples"):
            EvolutionConfig(calibration_min_samples=0)

    def test_response_min_fidelity_validation(self):
        with pytest.raises(ValueError, match="response_min_fidelity"):
            EvolutionConfig(response_min_fidelity=0.0)
        with pytest.raises(ValueError, match="response_min_fidelity"):
            EvolutionConfig(response_min_fidelity=1.5)

    def test_response_min_samples_per_type_validation(self):
        with pytest.raises(ValueError, match="response_min_samples_per_type"):
            EvolutionConfig(response_min_samples_per_type=0)

    def test_window_min_months_validation(self):
        with pytest.raises(ValueError, match="window_min_months"):
            EvolutionConfig(window_min_months=0)

    def test_to_dict_includes_v024_fields(self):
        config = EvolutionConfig()
        d = config.to_dict()
        assert "calibration_alpha" in d
        assert "calibration_max_amplitude" in d
        assert "calibration_min_samples" in d
        assert "response_min_fidelity" in d
        assert "response_min_samples_per_type" in d
        assert "window_min_months" in d

    def test_from_dict_compatible_with_v023(self):
        v023_data = {
            "data_dir": "~/.nanobot-runner",
            "async_write_enabled": False,
            "feedback_prompt_frequency": 5,
            "some_unknown_field": "ignored",
        }
        config = EvolutionConfig.from_dict(v023_data)
        assert config.feedback_prompt_frequency == 5
        assert config.calibration_alpha == 0.7
