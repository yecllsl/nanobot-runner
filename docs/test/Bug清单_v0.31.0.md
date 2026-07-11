# Bug 清单 v0.31.0

> **版本**: v0.31.0（质量提升专项版本）
> **测试日期**: 2026-06-23
> **测试执行人**: AI Agent（测试工程师）
> **当前基线**: v0.30.0

---

## Bug 统计概览

| 等级 | 数量 | 已修复 | 待修复 | 已驳回 |
|------|------|--------|--------|--------|
| P0 - 阻塞 | 0 | - | - | - |
| P1 - 严重 | 0 | - | - | - |
| P2 - 一般 | 2 | 0 | 2 | 0 |
| P3 - 建议 | 0 | - | - | - |
| **合计** | **2** | **0** | **2** | **0** |

---

## Bug 详细清单

### BUG-001: WebUI E2E 测试因服务器未启动全部失败

| 字段 | 内容 |
|------|------|
| **Bug ID** | BUG-001 |
| **等级** | P2 - 一般 |
| **模块** | tests/e2e/webui |
| **发现阶段** | E2E 测试 |
| **状态** | 待修复 |
| **优先级** | 中 |

**Bug 标题**: WebUI E2E Playwright 测试因服务器未启动导致 45 个用例全部失败

**复现步骤**:
1. 执行 `uv run pytest tests/e2e/ -v --tb=short`
2. 观察所有 `tests/e2e/webui/` 下的测试用例
3. 所有 WebUI 测试报错 `net::ERR_CONNECTION_REFUSED at http://127.0.0.1:8766/`

**预期结果**: WebUI E2E 测试应能正常连接 WebUI 服务器并执行页面交互验证

**实际结果**: 所有 WebUI Playwright 测试因连接被拒绝而失败，共 45 个用例

**根因分析**: WebUI E2E 测试未在执行前自动启动 WebUI 服务器，测试框架缺少 fixture 级别的服务器启动/停止逻辑

**修复建议**:
1. 在 `tests/e2e/webui/conftest.py` 中添加 `autouse=True` 的 fixture，自动启动/停止 WebUI 服务器
2. 或在 CI 流水线中增加 WebUI 服务器启动步骤
3. 确保测试结束后正确关闭服务器进程

**影响范围**:
- test_webui_ai_chat.py: 3 个用例
- test_webui_dashboard.py: 6 个用例
- test_webui_evolution.py: 8 个用例
- test_webui_plan.py: 8 个用例
- test_webui_settings.py: 8 个用例
- test_webui_visualization.py: 12 个用例

**环境**: Windows, Python 3.11+, pytest, Playwright

**备注**: 此问题为测试环境配置问题，非代码缺陷。WebUI API 层功能已在集成测试中通过验证。

---

### BUG-002: 单元测试覆盖率低于基线

| 字段 | 内容 |
|------|------|
| **Bug ID** | BUG-002 |
| **等级** | P2 - 一般 |
| **模块** | 全局（覆盖率） |
| **发现阶段** | 单元测试 |
| **状态** | 待修复 |
| **优先级** | 中 |

**Bug 标题**: 单元测试总覆盖率 81% 低于 v0.30.0 基线 83%

**复现步骤**:
1. 执行 `uv run pytest tests/unit/ -v --cov=src --cov-report=term-missing`
2. 查看覆盖率报告
3. 总覆盖率为 81%，低于基线 83%

**预期结果**: 总覆盖率 >= 83%（对齐 v0.30.0 基线）

**实际结果**: 总覆盖率 81%，低于基线 2 个百分点

**根因分析**: 部分模块覆盖率偏低拉低整体覆盖率：
- `src/core/evolution/evolution_reporter.py`: 21%（严重偏低）
- `src/core/prediction/vdot_predictor.py`: 78%
- `src/core/base/context.py`: 78%
- `src/core/export/engine.py`: 79%
- `src/core/evolution/evolution_engine.py`: 81%
- `src/core/evolution/evolution_store.py`: 84%
- `src/core/evolution/outcome_collector.py`: 81%

**修复建议**:
1. 优先补充 `evolution_reporter.py` 的单元测试（当前仅 21%）
2. 补充 `vdot_predictor.py` 的降级路径测试
3. 补充 `context.py` 的异常分支测试
4. 目标：下一迭代将覆盖率提升至 83%

**影响范围**: 覆盖率指标未达标，但不影响核心功能正确性

**环境**: Windows, Python 3.11+, pytest-cov

**备注**: 核心模块 `src/core/` 覆盖率 81% 已满足 >=80% 的分层门禁要求，总覆盖率略低于基线。

---

## Bug 趋势分析

### 按模块分布

| 模块 | Bug 数 | 占比 |
|------|--------|------|
| tests/e2e/webui | 1 | 50% |
| 全局（覆盖率） | 1 | 50% |

### 按等级分布

| 等级 | Bug 数 | 占比 |
|------|--------|------|
| P0 - 阻塞 | 0 | 0% |
| P1 - 严重 | 0 | 0% |
| P2 - 一般 | 2 | 100% |
| P3 - 建议 | 0 | 0% |

### 按根因分类

| 根因 | Bug 数 | 占比 |
|------|--------|------|
| 测试环境配置 | 1 | 50% |
| 测试覆盖不足 | 1 | 50% |

---

## 质量优化建议

### 1. WebUI E2E 测试基础设施

- 添加 `conftest.py` 中的服务器启动 fixture
- 考虑使用 `pytest-xprocess` 或自定义 fixture 管理 WebUI 服务器生命周期
- 增加 health check 等待机制，确保服务器就绪后再执行测试

### 2. 覆盖率提升计划

| 优先级 | 模块 | 当前覆盖率 | 目标覆盖率 | 预估新增用例 |
|--------|------|----------|----------|------------|
| P0 | evolution_reporter.py | 21% | >=80% | ~15 |
| P1 | vdot_predictor.py | 78% | >=85% | ~10 |
| P1 | context.py | 78% | >=85% | ~8 |
| P2 | export/engine.py | 79% | >=85% | ~5 |

### 3. 测试耗时优化

- 当前单元测试耗时 91.77s，远超基线 15.23s
- 建议排查慢测试用例，考虑使用 `pytest-timeout` 限制单用例耗时
- 考虑使用 `pytest-xdist` 并行执行

---

**清单生成人**: AI Agent（测试工程师）
**清单生成日期**: 2026-06-23
**清单版本**: v1.0
