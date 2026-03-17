# Checklist

## T001: TSS 计算功能

- [x] `calculate_tss_for_run()` 方法已实现
- [x] 心率数据缺失时返回 0
- [x] 时长为 0 时返回 0
- [x] TSS 值范围合理 (0-500)
- [x] 计算结果与 TrainingPeaks 标准一致 (误差 < 5%)
- [x] 单元测试覆盖率 ≥ 90%

## T009: 配速分布分析

- [x] `get_pace_distribution()` 方法已实现
- [x] 配速区间划分合理 (5 个区间)
- [x] 返回配速趋势分析数据
- [x] 性能要求: 计算时间 < 2 秒
- [x] 单元测试覆盖率 ≥ 85%

## T010: 心率区间分析

- [x] `get_heart_rate_zones()` 方法已实现
- [x] 心率区间划分符合运动科学原理 (5 个区间)
- [x] 支持自定义年龄参数
- [x] 性能要求: 计算时间 < 2 秒
- [x] 单元测试覆盖率 ≥ 85%

## T011: 训练效果评估

- [x] `get_training_effect()` 方法已实现
- [x] 有氧/无氧效果评估合理
- [x] 提供恢复时间估算
- [x] 性能要求: 计算时间 < 2 秒
- [x] 单元测试覆盖率 ≥ 85%

## 总体验收

- [x] 所有新增方法在 `src/core/analytics.py` 中
- [x] 所有单元测试在 `tests/unit/test_analytics.py` 中
- [x] 所有测试通过 (`uv run pytest tests/unit/test_analytics.py -v`)
- [x] 代码格式化通过 (`uv run black src/core/analytics.py`)
- [x] 总体覆盖率: **92%** (超过 85% 要求)
