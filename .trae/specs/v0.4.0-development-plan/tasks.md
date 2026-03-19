# v0.4.0 迭代开发任务清单

## 阶段 1：画像系统实现（M1 - Day 1-3）

- [x] **Task 1.1**: 开发准备 - 确认开发环境和依赖
  - [x] 验证虚拟环境已激活
  - [x] 验证依赖已安装（`uv sync --all-extras`）
  - [x] 确认开发工具可用（black, isort, mypy, bandit, pytest）

- [x] **Task 1.2**: T001 - 用户画像引擎实现（8h）
  - [x] 定义画像数据结构（RunnerProfile, FitnessLevel, TrainingPattern 等）
  - [x] 实现 `build_profile()` 方法
  - [x] 实现 `get_fitness_level()` 方法
  - [x] 实现 `get_training_pattern()` 方法
  - [x] 实现 `calculate_injury_risk()` 方法
  - [x] 编写单元测试（覆盖率 ≥ 80%）
  - [x] 代码质量检查（black, isort, mypy, bandit）

- [x] **Task 1.3**: T002 - 画像双存储持久化（6h）
  - [x] 实现 `save_profile_json()` 方法（profile.json）
  - [x] 实现 `load_profile_json()` 方法
  - [x] 实现 `save_memory_md()` 方法（MEMORY.md）
  - [x] 实现 `load_memory_md()` 方法
  - [x] 实现 `sync_dual_storage()` 双存储同步方法
  - [x] 实现 `merge_profile_to_md()` 智能合并方法
  - [x] 编写单元测试（覆盖率 ≥ 80%）
  - [x] 代码质量检查

- [x] **Task 1.4**: T003 - 画像保鲜期与异常过滤（4h）
  - [x] 实现 `check_freshness()` 方法
  - [x] 定义 `ProfileStaleStatus` 数据结构
  - [x] 定义 `ANOMALY_FILTER_RULES` 异常过滤规则
  - [x] 实现 `filter_anomaly_data()` 方法
  - [x] 编写单元测试（覆盖率 ≥ 80%）
  - [x] 代码质量检查

- [x] **Task 1.5**: M1 里程碑验收
  - [x] 确认 T001-T003 全部完成
  - [x] 运行全量测试（`uv run pytest tests/unit/core/test_profile.py`）
  - [x] 生成覆盖率报告（`uv run pytest --cov=src/core/profile --cov-report=html`）
  - [x] 代码质量检查（`uv run black src; uv run isort src; uv run mypy src; uv run bandit -r src`）
  - [x] 提交开发交付报告

## 阶段 2：训练计划实现（M2 - Day 4-7）

- [x] **Task 2.1**: T004 - 训练计划引擎实现（12h）
  - [x] 定义训练计划数据结构（TrainingPlan, WeeklySchedule, DailyPlan）
  - [x] 实现 `generate_plan()` 方法
  - [x] 实现 `adjust_plan()` 方法（含心率漂移/主观疲劳度参数）
  - [x] 实现 `get_daily_workout()` 方法
  - [x] 实现 `get_phase_config_by_fitness_level()` 动态阶段配置
  - [x] 定义 `PHASE_CONFIG` 阶段划分配置
  - [x] 编写单元测试（覆盖率 ≥ 80%）
  - [x] 代码质量检查

- [x] **Task 2.2**: T005 - 飞书日历同步服务（8h）
  - [x] 实现 `FeishuCalendarSync` 类
  - [x] 实现 `sync_plan()` 方法
  - [x] 实现 `sync_daily_workout()` 方法
  - [x] 实现 `build_calendar_event()` 日历事件构建
  - [x] 封装飞书日历 API 调用
  - [x] 编写单元测试（覆盖率 ≥ 80%）
  - [x] 代码质量检查

- [x] **Task 2.3**: T006 - 飞书反向同步与 Webhook 集成（6h）
  - [x] 实现 `FeishuCalendarWebhookHandler` 类
  - [x] 实现 Webhook 路由配置（`POST /webhook/calendar`）
  - [x] 实现冲突检测与解决策略
  - [x] 配置飞书事件订阅
  - [x] 编写单元测试（覆盖率 ≥ 80%）
  - [x] 代码质量检查

- [x] **Task 2.4**: M2 里程碑验收
  - [x] 确认 T004-T006 全部完成
  - [x] 运行全量测试（127 个测试全部通过）
  - [x] 生成覆盖率报告
  - [x] 代码质量检查
  - [x] 提交开发交付报告

## 阶段 3:飞书集成（M3 - Day 8-9）

- [x] **Task 3.1**: T007 - 飞书机器人 Channel（4h）
  - [x] 配置飞书机器人 Channel
  - [x] 实现消息接收和响应逻辑
  - [x] 实现命令解析
  - [x] 编写集成测试
  - [x] 代码质量检查

- [x] **Task 3.2**: T008 - Agent 系统提示词配置（4h）
  - [x] 编写 Agent 系统提示词（SOUL.md 模板）
  - [x] 配置 Agent 行为准则（AGENTS.md 模板）
  - [x] 配置 Agent 工具调用权限（配置指南）
  - [x] 文档质量检查
  - [x] 输出交付文档（3 个模板 + 配置指南）

- [x] **Task 3.3**: T009 - 新增工具注册（含记忆更新工具）（6h）
  - [x] 实现 `UpdateMemoryTool` 工具
  - [x] 注册所有新增工具到 RunnerTools
  - [x] 更新 `TOOL_DESCRIPTIONS` 字典
  - [x] 编写工具单元测试（30 个用例，通过率 100%）
  - [x] 代码质量检查（black, isort, mypy, bandit 全部通过）

- [x] **Task 3.4**: M3 里程碑验收
  - [x] 确认 T007-T009 全部完成
  - [x] 运行全量测试（94 个测试全部通过）
  - [x] 生成覆盖率报告
  - [x] 代码质量检查
  - [x] 提交开发交付报告

## 阶段 4：增强功能（M4 - Day 10）

- [ ] **Task 4.1**: T010 - 比赛预测引擎（4h）
  - [ ] 实现公式拟合预测算法
  - [ ] 实现多距离预测功能
  - [ ] 编写单元测试
  - [ ] 代码质量检查

- [ ] **Task 4.2**: T011 - 训练回顾报告生成（6h）
  - [ ] 实现报告生成逻辑
  - [ ] 实现报告模板引擎
  - [ ] 编写单元测试
  - [ ] 代码质量检查

- [ ] **Task 4.3**: T012 - 报告推送配置（4h）
  - [ ] 实现飞书推送集成
  - [ ] 配置推送触发条件
  - [ ] 编写集成测试
  - [ ] 代码质量检查

- [ ] **Task 4.4**: M4 里程碑验收
  - [ ] 确认 T010-T012 全部完成
  - [ ] 运行全量测试
  - [ ] 生成覆盖率报告
  - [ ] 代码质量检查
  - [ ] 提交开发交付报告

## 阶段 5：测试与发布（M5 - Day 11）

- [ ] **Task 5.1**: T013 - 单元测试 - 核心模块（2h）
  - [ ] 补充核心模块单元测试
  - [ ] 确保覆盖率 ≥ 80%
  - [ ] 运行测试并生成报告

- [ ] **Task 5.2**: T014 - 集成测试（2h）
  - [ ] 执行场景集成测试
  - [ ] 验证模块间交互
  - [ ] 记录测试结果

- [ ] **Task 5.3**: T015-T020 - 文档与质量检查（2h）
  - [ ] 更新开发文档
  - [ ] 运行代码质量检查
  - [ ] 准备发布材料

- [ ] **Task 5.4**: M5 里程碑验收
  - [ ] 确认所有测试通过
  - [ ] 确认文档完善
  - [ ] 准备发布评审

# 任务依赖关系

- [Task 1.2] T001 - 无依赖，可独立启动
- [Task 1.3] T002 - 依赖 [Task 1.2] T001
- [Task 1.4] T003 - 依赖 [Task 1.3] T002
- [Task 2.1] T004 - 依赖 [Task 1.2] T001
- [Task 2.2] T005 - 依赖 [Task 2.1] T004
- [Task 2.3] T006 - 依赖 [Task 2.2] T005
- [Task 3.1] T007 - 依赖 [Task 1.2] T001, [Task 2.1] T004
- [Task 3.2] T008 - 依赖 [Task 3.1] T007
- [Task 3.3] T009 - 依赖 [Task 3.2] T008
- [Task 4.1] T010 - 依赖 [Task 1.2] T001
- [Task 4.2] T011 - 依赖 [Task 1.2] T001
- [Task 4.3] T012 - 依赖 [Task 4.2] T011
- [Task 5.1] T013-T020 - 依赖所有功能开发任务

# 并行开发建议

**可并行执行的任务组**：
- Task 1.2 (T001) → 完成后，可并行启动：Task 2.1 (T004), Task 4.1 (T010), Task 4.2 (T011)
- Task 2.1 (T004) 和 Task 4.1 (T010) 和 Task 4.2 (T011) 可并行开发

**关键路径**：
T001 → T002 → T003（画像系统链）
T001 → T004 → T005 → T006（训练计划链）
T001+T004 → T007 → T008 → T009（飞书集成链）
