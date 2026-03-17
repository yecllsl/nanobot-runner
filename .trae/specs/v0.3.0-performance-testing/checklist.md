# Checklist

## T007: 性能测试

- [x] 创建 `tests/performance/` 目录
- [x] 实现查询性能测试（日期范围、距离范围）
- [x] 实现 VDOT 趋势查询性能测试
- [x] 实现训练负荷计算性能测试
- [x] 实现晨报生成性能测试
- [x] 所有性能测试通过
- [x] 生成性能测试报告

## T008: 测试覆盖率提升

- [x] 运行覆盖率报告，识别低覆盖率模块
- [x] `src/core/analytics.py` 覆盖率 ≥ 85% (实际: 95%)
- [x] `src/agents/tools.py` 覆盖率 ≥ 85% (实际: 94%)
- [x] `src/notify/feishu.py` 覆盖率 ≥ 80% (实际: 96%)
- [x] `src/cli_formatter.py` 覆盖率 ≥ 80% (实际: 91%)
- [x] 总体覆盖率 ≥ 80% (实际: 87%)
- [x] 所有单元测试通过

## Bug修复: test_cli.py CPU使用率问题

- [x] 分析问题根因: `test_chat` 触发 `_run_chat()` 无限循环
- [x] 使用 `patch` 模拟 `_run_chat` 函数避免真正执行交互式循环
- [x] 验证修复: 33个测试在1.66秒内完成，无CPU飙升

## 总体验收

- [x] 性能测试目录结构完整
- [x] 性能测试报告已生成
- [x] 覆盖率报告已生成
- [x] 单元测试通过 (`uv run pytest tests/unit/ -v`)
- [x] 总体覆盖率 ≥ 80% (实际: 87%)
