# Checklist

## T002: ATL/CTL/TSB 计算

- [x] `get_training_load()` 方法已实现
- [x] ATL 计算使用 EWMA（7天窗口）
- [x] CTL 计算使用 EWMA（42天窗口）
- [x] TSB = CTL - ATL 计算正确
- [x] 数据不足时返回友好提示
- [x] 提供体能状态评估
- [x] 提供训练建议
- [x] 性能要求: 1000 条记录计算时间 < 2 秒
- [x] 单元测试覆盖率 ≥ 90%

## T003: 训练负荷趋势分析

- [x] `get_training_load_trend()` 方法已实现
- [x] 返回每日训练负荷数据（日期、TSS、ATL、CTL、TSB）
- [x] 包含体能状态评估
- [x] 支持日期范围参数
- [x] 性能要求: 90 天数据计算时间 < 3 秒
- [x] 单元测试覆盖率 ≥ 85%

## T004: 晨报内容生成

- [x] `generate_daily_report()` 方法已实现
- [x] 晨报内容完整（日期、问候语、体能状态、训练摘要、建议）
- [x] 训练建议基于训练负荷数据生成
- [x] 语言风格友好且专业
- [x] 生成时间 < 1 秒
- [x] 单元测试覆盖率 ≥ 85%

## 总体验收

- [x] 所有新增方法在 `src/core/analytics.py` 中
- [x] 所有单元测试在 `tests/unit/test_analytics.py` 中
- [x] 所有测试通过 (`uv run pytest tests/unit/test_analytics.py -v`)
- [x] 代码格式化通过 (`uv run black src/core/analytics.py`)
- [x] 总体覆盖率: **94%** (超过 85% 要求)
