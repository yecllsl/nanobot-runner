# 测试策略 - Sprint 2

**项目**: Nanobot Runner
**版本**: Sprint 2
**制定日期**: 2026-04-03
**制定人**: 测试工程师智能体

---

## 一、测试范围

### 1.1 测试对象

本次测试针对 Sprint 2 开发的核心功能模块：

| 模块 | 组件 | 说明 |
|------|------|------|
| **M5: CalendarTool** | 日历同步工具 | 完整的增删改生命周期管理 |
| **M7: PlanManager** | 训练计划管理器 | CRUD操作和状态管理 |
| **数据模型** | TrainingPlan/DailyPlan | 序列化和反序列化 |

### 1.2 测试类型

| 测试类型 | 说明 | 测试对象 |
|---------|------|---------|
| **单元测试** | 模块级别功能测试 | CalendarTool, PlanManager |
| **集成测试** | 模块间协作测试 | CalendarTool + FeishuCalendarSync |
| **E2E测试** | 端到端业务流程测试 | 训练计划创建→同步→管理全流程 |

### 1.3 MVP核心需求覆盖

根据 PRD 需求文档，Sprint 2 实现的 MVP 需求：

| 功能ID | 功能名称 | 优先级 | 测试范围 |
|--------|---------|--------|---------|
| F1 | 训练计划意图解析 | P0 | 后续Sprint |
| F2 | 用户画像与历史数据整合 | P0 | 后续Sprint |
| F3 | 训练计划生成 | P0 | 后续Sprint |
| F4 | 硬性规则校验 | P0 | 后续Sprint |
| F5 | 多维分析验证 | P0 | 后续Sprint |
| **F6** | **日历同步（增删改生命周期）** | **P0** | **本次测试** |
| **F7** | **训练计划管理（CRUD+状态管理）** | **P1** | **本次测试** |
| F8 | 智能训练提醒 | P1 | 后续Sprint |

---

## 二、门禁规则

### 2.1 准入规则

测试准入需满足以下条件：

| 规则ID | 规则名称 | 准入条件 | 验证方式 |
|--------|---------|---------|---------|
| AR-01 | 代码评审通过 | 代码评审报告结论为"通过" | 确认代码评审报告存在 |
| AR-02 | 单元测试通过 | 测试通过率 ≥ 100% | 执行 pytest，收集结果 |
| AR-03 | 单元测试覆盖率 | 核心模块覆盖率 ≥ 80% | 执行 coverage.py |
| AR-04 | 代码规范检查 | black/isort/mypy 零警告 | 执行检查命令 |

### 2.2 准出规则

测试准出需满足以下条件：

| 规则ID | 规则名称 | 准出条件 | 验证方式 |
|--------|---------|---------|---------|
| ER-01 | 功能测试通过率 | P0-P1级用例通过率 = 100% | 执行功能测试 |
| ER-02 | 集成测试通过率 | 集成测试通过率 ≥ 95% | 执行集成测试 |
| ER-03 | 无致命/严重bug | 致命bug数 = 0，严重bug数 = 0 | Bug清单检查 |
| ER-04 | 一般bug修复率 | 一般bug修复率 ≥ 90% | Bug清单检查 |

### 2.3 覆盖率要求

| 模块类型 | 覆盖率要求 | 说明 |
|---------|-----------|------|
| **core** | ≥ 80% | 核心业务逻辑模块 |
| **CalendarTool** | ≥ 80% | 日历同步工具 |
| **PlanManager** | ≥ 80% | 训练计划管理器 |
| **数据模型** | ≥ 80% | TrainingPlan/DailyPlan |

---

## 三、测试用例设计

### 3.1 CalendarTool 测试用例

#### 3.1.1 预同步检查测试

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|---------|--------|
| TC-M5-001 | 预同步检查-全部检查项 | API配置正常 | 调用 pre_sync_check() | 返回所有检查项结果 | P0 |
| TC-M5-002 | 预同步检查-网络检查 | 网络正常 | 调用 _check_network() | 返回 healthy=True | P0 |
| TC-M5-003 | 预同步检查-令牌检查 | Token有效 | 调用 _check_token() | 返回 healthy=True | P0 |
| TC-M5-004 | 预同步检查-日历权限 | 有日历权限 | 调用 _check_calendar_permission() | 返回 healthy=True | P0 |
| TC-M5-005 | 预同步检查-日历ID | 日历ID已配置 | 调用 _check_calendar_id() | 返回 healthy=True | P0 |
| TC-M5-006 | 预同步检查-指定检查项 | API配置正常 | 调用 pre_sync_check([NETWORK, TOKEN]) | 仅返回指定项 | P1 |

#### 3.1.2 乐观更新测试

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|---------|--------|
| TC-M5-007 | 乐观更新-创建上下文 | 无 | 调用 optimistic_update() | 创建上下文成功 | P0 |
| TC-M5-008 | 乐观更新-回滚 | 上下文存在 | 触发异常后调用 _rollback_optimistic_update() | 回滚成功 | P0 |
| TC-M5-009 | 乐观更新-上下文清理 | 上下文过期 | 手动清理过期上下文 | 清理成功 | P1 |

#### 3.1.3 批量同步测试

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|---------|--------|
| TC-M5-010 | 批量同步-成功场景 | 10个计划 | 调用 batch_sync(10个计划) | synced_count=10 | P0 |
| TC-M5-011 | 批量同步-部分失败 | 10个计划，1个失败 | 调用 batch_sync(10个计划) | synced_count=9, failed_count=1 | P0 |
| TC-M5-012 | 批量同步-指定批次大小 | 25个计划 | 调用 batch_sync(25个计划, batch_size=10) | 分3批处理 | P0 |
| TC-M5-013 | 批量同步-空列表 | 无计划 | 调用 batch_sync([]) | success=True | P1 |

#### 3.1.4 生命周期管理测试

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|---------|--------|
| TC-M5-014 | 同步计划-CREATE模式 | 有效计划 | 调用 sync_plan(plan, CREATE) | 同步成功 | P0 |
| TC-M5-015 | 同步计划-UPDATE模式 | 有event_id | 调用 sync_plan(plan, UPDATE) | 更新成功 | P0 |
| TC-M5-016 | 同步计划-DELETE模式 | 有event_id | 调用 sync_plan(plan, DELETE) | 删除成功 | P0 |
| TC-M5-017 | 同步单日训练-CREATE | 有效日计划 | 调用 sync_daily_workout(daily_plan) | 同步成功 | P0 |
| TC-M5-018 | 同步单日训练-UPDATE | 有event_id | 调用 sync_daily_workout(daily_plan, UPDATE) | 更新成功 | P0 |
| TC-M5-019 | 同步单日训练-DELETE | 有event_id | 调用 sync_daily_workout(daily_plan, DELETE) | 删除成功 | P0 |
| TC-M5-020 | 同步单日训练-无event_id更新 | 无event_id | 调用 sync_daily_workout(daily_plan, UPDATE) | 返回失败 | P0 |

### 3.2 PlanManager 测试用例

#### 3.2.1 CRUD操作测试

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|---------|--------|
| TC-M7-001 | 创建计划-成功 | 无 | 调用 create_plan(plan) | 返回plan_id | P0 |
| TC-M7-002 | 创建计划-无ID | plan_id为空 | 调用 create_plan(无ID计划) | 抛出异常 | P0 |
| TC-M7-003 | 创建计划-重复ID | 计划已存在 | 调用 create_plan(重复ID) | 抛出异常 | P0 |
| TC-M7-004 | 创建计划-自动设置状态 | 无 | 创建计划后检查 | status=DRAFT | P0 |
| TC-M7-005 | 获取计划-成功 | 计划存在 | 调用 get_plan(plan_id) | 返回计划对象 | P0 |
| TC-M7-006 | 获取计划-不存在 | 计划不存在 | 调用 get_plan(不存在ID) | 返回None | P0 |
| TC-M7-007 | 更新计划-成功 | 计划存在 | 调用 update_plan(plan_id, updates) | 更新成功 | P0 |
| TC-M7-008 | 更新计划-不存在 | 计划不存在 | 调用 update_plan(不存在ID) | 抛出异常 | P0 |
| TC-M7-009 | 删除计划-成功 | 计划存在 | 调用 delete_plan(plan_id) | 删除成功 | P0 |
| TC-M7-010 | 删除计划-不存在 | 计划不存在 | 调用 delete_plan(不存在ID) | 抛出异常 | P0 |
| TC-M7-011 | 列出计划-全部 | 多个计划 | 调用 list_plans() | 返回全部计划 | P0 |
| TC-M7-012 | 列出计划-按状态 | 有多种状态 | 调用 list_plans(status=ACTIVE) | 仅返回ACTIVE | P0 |
| TC-M7-013 | 列出计划-带限制 | 多个计划 | 调用 list_plans(limit=5) | 最多返回5个 | P1 |

#### 3.2.2 状态管理测试

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|---------|--------|
| TC-M7-014 | 激活计划-DRAFT→ACTIVE | 状态DRAFT | 调用 activate_plan(plan_id) | 状态变为ACTIVE | P0 |
| TC-M7-015 | 暂停计划-ACTIVE→PAUSED | 状态ACTIVE | 调用 pause_plan(plan_id) | 状态变为PAUSED | P0 |
| TC-M7-016 | 完成计划-ACTIVE→COMPLETED | 状态ACTIVE | 调用 complete_plan(plan_id) | 状态变为COMPLETED | P0 |
| TC-M7-017 | 取消计划-DRAFT→CANCELLED | 状态DRAFT | 调用 cancel_plan(plan_id, reason) | 状态变为CANCELLED | P0 |
| TC-M7-018 | 取消计划-ACTIVE→CANCELLED | 状态ACTIVE | 调用 cancel_plan(plan_id, reason) | 状态变为CANCELLED | P0 |
| TC-M7-019 | 恢复计划-PAUSED→ACTIVE | 状态PAUSED | 调用 activate_plan(plan_id) | 状态变为ACTIVE | P0 |
| TC-M7-020 | 激活计划-非法转换 | 状态COMPLETED | 调用 activate_plan(plan_id) | 抛出异常 | P0 |
| TC-M7-021 | 状态查询-成功 | 计划存在 | 调用 get_plan_status(plan_id) | 返回状态 | P0 |
| TC-M7-022 | 状态查询-不存在 | 计划不存在 | 调用 get_plan_status(不存在ID) | 返回None | P0 |

#### 3.2.3 高级功能测试

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|---------|--------|
| TC-M7-023 | 获取激活计划-有激活 | 有ACTIVE计划 | 调用 get_active_plan() | 返回ACTIVE计划 | P0 |
| TC-M7-024 | 获取激活计划-无激活 | 无ACTIVE计划 | 调用 get_active_plan() | 返回None | P0 |
| TC-M7-025 | 获取激活计划-多个激活 | 有多个ACTIVE | 调用 get_active_plan() | 返回第一个 | P1 |
| TC-M7-026 | 状态转换验证-DRAFT→COMPLETED | 状态DRAFT | 调用 update_plan(status=COMPLETED) | 抛出异常 | P0 |
| TC-M7-027 | 状态转换验证-CANCELLED→ACTIVE | 状态CANCELLED | 调用 activate_plan(plan_id) | 抛出异常 | P0 |

### 3.3 集成测试用例

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|---------|--------|
| TC-INT-001 | CalendarTool+PlanManager | 都已初始化 | 创建计划→同步到日历→验证event_id | event_id已设置 | P0 |
| TC-INT-002 | 完整生命周期 | 日历服务正常 | 创建→激活→更新→完成→查询状态 | 状态正确变化 | P0 |
| TC-INT-003 | 批量同步+状态管理 | 多个计划 | 批量创建→批量同步→验证状态 | 状态一致 | P1 |
| TC-INT-004 | 并发操作 | 多线程 | 并发创建/更新/查询计划 | 无数据损坏 | P1 |

### 3.4 E2E测试用例

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|---------|--------|
| TC-E2E-001 | 训练计划完整流程 | 飞书配置正常 | 1.创建训练计划 2.激活计划 3.同步到日历 4.查询验证 | 全流程成功 | P0 |
| TC-E2E-002 | 计划调整流程 | 已有同步计划 | 1.调整计划 2.更新日历 3.验证更新 | 日历已更新 | P0 |
| TC-E2E-003 | 计划取消流程 | 已有同步计划 | 1.取消计划 2.删除日历 3.验证删除 | 日历已清理 | P0 |

---

## 四、测试数据

### 4.1 测试数据构造规范

| 数据类型 | 构造方式 | 存储位置 |
|---------|---------|---------|
| TrainingPlan | 使用测试夹具工厂函数 | tests/fixtures/plans.py |
| DailyPlan | 使用测试夹具工厂函数 | tests/fixtures/plans.py |
| 配置数据 | Mock ConfigManager | tests/conftest.py |
| 飞书API | Mock FeishuCalendarSync | tests/conftest.py |

### 4.2 测试夹具

```python
@pytest.fixture
def sample_training_plan():
    """创建测试用训练计划"""
    return TrainingPlan(
        plan_id="test_plan_001",
        user_id="test_user",
        plan_type=PlanType.MARATHON,
        fitness_level=FitnessLevel.INTERMEDIATE,
        start_date="2026-04-01",
        end_date="2026-06-30",
        goal_distance_km=42.195,
        goal_date="2026-06-15",
        weeks=[]
    )

@pytest.fixture
def sample_daily_plan():
    """创建测试用日训练计划"""
    return DailyPlan(
        date="2026-04-01",
        workout_type=WorkoutType.EASY,
        distance_km=8.0,
        duration_min=50
    )
```

---

## 五、测试环境

### 5.1 环境要求

| 环境 | 配置要求 | 说明 |
|------|---------|------|
| **开发环境** | 本地Python 3.11+ | 开发调试用 |
| **测试环境** | 同开发环境 | 隔离的测试数据 |
| **Mock服务** | unittest.mock | 模拟飞书API等外部依赖 |

### 5.2 依赖安装

```bash
# 安装测试依赖
uv pip install pytest pytest-asyncio pytest-mock pytest-cov

# 同步依赖
uv sync --all-extras
```

---

## 六、测试执行计划

### 6.1 测试执行顺序

```
1. 单元测试 (60个用例)
   └── CalendarTool (20个)
   └── PlanManager (40个)

2. 集成测试 (4个用例)
   └── 模块间协作测试

3. E2E测试 (3个用例)
   └── 端到端流程测试
```

### 6.2 执行命令

```bash
# 单元测试
uv run pytest tests/unit/core/plan/ -v --cov=src/core/plan --cov-report=term-missing

# 集成测试
uv run pytest tests/integration/ -v

# E2E测试
uv run pytest tests/e2e/ -v

# 全部测试
uv run pytest tests/ -v --cov=src --cov-report=term-missing
```

### 6.3 测试报告

| 报告类型 | 报告文件 | 说明 |
|---------|---------|------|
| 单元测试报告 | `tests/unit/test_report.txt` | pytest-html输出 |
| 覆盖率报告 | `coverage_report/index.html` | coverage.py输出 |
| 测试总结 | `/docs/test/测试报告_Sprint2.md` | 轮次测试报告 |

---

## 七、风险与应对

### 7.1 测试风险

| 风险ID | 风险描述 | 影响程度 | 应对措施 |
|--------|---------|---------|---------|
| R1 | 飞书API调用限制 | 中 | 使用Mock，避免真实API调用 |
| R2 | 测试数据构造复杂 | 低 | 预先定义测试夹具 |
| R3 | 并发测试环境 | 低 | 使用线程锁控制 |

### 7.2 风险缓解

1. **Mock策略**：所有外部依赖使用 unittest.mock 模拟
2. **测试隔离**：每个测试用例独立，互不影响
3. **数据清理**：测试前后清理临时数据

---

## 八、验收标准

### 8.1 测试通过标准

| 标准ID | 标准描述 | 达标值 |
|--------|---------|--------|
| SC-01 | P0级用例通过率 | 100% |
| SC-02 | P1级用例通过率 | ≥ 95% |
| SC-03 | 单元测试覆盖率 | ≥ 80% |
| SC-04 | 致命Bug数 | 0 |
| SC-05 | 严重Bug数 | 0 |

### 8.2 上线门禁

满足以下条件，可进入发布环节：

1. ✅ P0-P1级用例100%通过
2. ✅ 无致命/严重级bug
3. ✅ 一般级bug修复率≥90%
4. ✅ 核心业务流程全量闭环
5. ✅ 符合需求验收标准

---

## 九、后续测试建议

### 9.1 后续Sprint测试计划

| Sprint | 测试模块 | 测试类型 |
|--------|---------|---------|
| Sprint 3 | IntentParser, PlanGenerator | 单元测试+集成测试 |
| Sprint 3 | HardValidator, PlanAnalyzer | 单元测试+集成测试 |
| Sprint 4 | NotifyTool, 智能提醒 | 单元测试+集成测试+E2E |
| Sprint 4 | 全流程集成 | E2E测试 |

### 9.2 长期质量保障

1. **持续集成**：每次提交自动运行单元测试
2. **覆盖率监控**：核心模块覆盖率低于80%禁止合并
3. **回归测试**：每次发布前运行全量测试

---

**测试策略版本**: v1.0.0
**制定日期**: 2026-04-03

---

*后续建议：执行 测试执行 开始执行测试。*
