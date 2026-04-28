# v0.14.0 AI教练进化版 测试策略

> **文档版本**: v1.0  
> **创建日期**: 2026-04-28  
> **适用版本**: v0.14.0  
> **维护者**: 测试工程师智能体  
> **测试策略类型**: 版本专项测试策略

---

## 1. 测试目标与范围

### 1.1 测试目标

| 目标 | 说明 | 优先级 |
|------|------|--------|
| 验证AI教练长期记忆功能正确性 | 记忆读写、版本管理、跨会话连贯 | P0 |
| 验证AI人格进化功能正确性 | 人格自动进化、用户可控、版本管理 | P0 |
| 验证记忆与人格协同工作 | Dream集成、偏好学习闭环 | P0 |
| 验证性能指标达标 | 记忆加载<100ms、反馈处理<500ms | P0 |
| 验证偏好提取准确率 | 偏好提取准确率>85% | P1 |

### 1.2 测试范围

#### ✅ 纳入测试范围

| 模块 | 测试类型 | 负责人 | 状态 |
|------|---------|--------|------|
| `src/core/memory/` 记忆管理模块 | 单元测试 + 集成测试 | 开发工程师 | ✅ 待测试 |
| `src/core/personality/` 人格进化模块 | 单元测试 + 集成测试 | 开发工程师 | ✅ 待测试 |
| 记忆+人格协同场景 | 场景级集成测试 | 测试工程师 | 📋 新增 |
| Dream集成场景 | 场景级集成测试 | 测试工程师 | 📋 新增 |
| 端到端用户旅程 | E2E全链路测试 | 测试工程师 | 📋 新增 |
| 性能测试 | 专项性能测试 | 测试工程师 | 📋 新增 |

#### ❌ 不纳入测试范围

- nanobot-ai框架Memory/Dream核心功能（仅测试集成点）
- LLM模型输出内容的不确定性验证
- 第三方依赖内部实现

---

## 2. 测试类型与策略

### 2.1 单元测试（Unit Testing）

**职责**: 开发工程师主责，测试工程师负责规范指导和结果校验

**覆盖范围**:
- `MemoryManager`: 记忆读写、备份恢复、版本管理、偏好存取
- `DreamIntegration`: Dream配置管理、自动归档/提取开关、状态报告
- `PersonalizationEngine`: 建议个性化、强度调整、偏好权重
- `PreferenceLearner`: 反馈学习、偏好更新、投票机制、重置功能
- `FeedbackLoop`: 反馈收集、处理、效果追踪、统计
- 数据模型: `MemoryVersion`, `Personality`, `UserPreferences`, `FeedbackRecord`, `PersonalizedSuggestion`

**覆盖率要求**:
| 模块 | 最低覆盖率 | 当前状态 |
|------|-----------|---------|
| `src/core/memory/` | ≥80% | 📋 待测试 |
| `src/core/personality/` | ≥80% | 📋 待测试 |

**Mock策略**:
- ✅ 必须Mock文件系统IO（使用临时目录）
- ✅ 必须Mock配置文件读写
- ❌ 禁止Mock内部业务逻辑（学习算法、个性化逻辑）

### 2.2 集成测试（Integration Testing）

**职责划分**:
| 测试类型 | 目录 | 负责人 |
|---------|------|--------|
| 模块内集成测试 | `tests/integration/module/` | 开发工程师 |
| 场景级集成测试 | `tests/integration/scene/` | 测试工程师 |

**场景级集成测试覆盖**:
- 记忆写入→读取→备份→恢复完整链路
- 反馈收集→偏好学习→人格进化完整链路
- Dream配置→自动归档→偏好提取完整链路
- 跨会话记忆连贯性验证
- 人格版本回溯验证

### 2.3 端到端测试（E2E Testing）

**职责**: 测试工程师主责

**覆盖范围**:
- AI教练记忆用户偏好的完整用户旅程
- AI人格进化的完整用户旅程
- 记忆+人格协同的完整用户旅程

**测试环境**:
- 使用临时测试目录，不影响真实用户数据
- Mock所有外部依赖（LLM API）
- 使用模拟用户反馈数据

### 2.4 性能测试（Performance Testing）

**覆盖范围**:
- 记忆加载时间 < 100ms
- 偏好数据加载时间 < 100ms
- 反馈处理响应时间 < 500ms
- 记忆备份创建时间
- 人格进化计算时间

---

## 3. 门禁规则

### 3.1 测试准入规则

代码进入测试环节前，必须满足以下条件：

| 条件 | 验证方式 | 责任人 |
|------|---------|--------|
| 需求规格说明书已评审通过 | `PRD_NanobotRunner_v0.13-0.15.md` 存在且v2.0 | 架构师 |
| 架构设计说明书已评审通过 | `架构设计说明书_v0.13-0.15.md` 存在 | 架构师 |
| 开发完成并通过自测 | 开发者自测报告 | 开发工程师 |
| 单元测试覆盖率达标 | `pytest --cov` 报告（memory≥80%, personality≥80%） | 开发工程师 |
| 代码质量检查通过 | `ruff check` 零警告 | 开发工程师 |
| 类型检查通过 | `mypy` 无新增错误 | 开发工程师 |
| 无未解决的P0/P1 Bug | Bug清单状态 | 开发工程师 |

**准入验证命令**:
```bash
# 代码质量检查
uv run ruff check src/core/memory/ src/core/personality/
uv run ruff format --check src/core/memory/ src/core/personality/
uv run mypy src/core/memory/ src/core/personality/ --ignore-missing-imports

# 单元测试覆盖率
uv run pytest tests/unit/core/memory/ tests/unit/core/personality/ --cov=src/core/memory --cov=src/core/personality --cov-report=term-missing

# 覆盖率验证
# memory ≥ 80% | personality ≥ 80%
```

### 3.2 测试准出规则

测试完成并允许发布，必须满足以下条件：

| 条件 | 标准 | 验证方式 |
|------|------|---------|
| P0级用例通过率 | 100% | 测试报告 |
| P1级用例通过率 | ≥95% | 测试报告 |
| 致命Bug | 0个 | Bug清单 |
| 严重Bug | 0个 | Bug清单 |
| 一般Bug修复率 | ≥90% | Bug清单 |
| 核心业务流程 | 全量闭环 | E2E测试报告 |
| 记忆加载时间 | < 100ms | 性能测试报告 |
| 偏好提取准确率 | > 85% | 功能测试报告 |
| 跨会话记忆连贯 | 100% | 功能测试报告 |
| 性能退化 | 无显著退化 | 性能测试报告 |
| 安全合规 | 无敏感信息泄露 | 安全扫描报告 |

**准出验证命令**:
```bash
# 全量测试执行
uv run pytest tests/ -v --tb=short

# v0.14.0专项测试执行
uv run pytest tests/unit/core/memory/ tests/unit/core/personality/ -v
uv run pytest tests/integration/scene/ -k "memory or personality or dream" -v
uv run pytest tests/e2e/ -k "v014 or memory or personality" -v
uv run pytest tests/performance/ -k "memory or personality" -v
```

### 3.3 上线门禁规则

**绝对禁止发布的情况**:
- ❌ 存在任何致命或严重级Bug
- ❌ P0级用例通过率 < 100%
- ❌ 核心业务流程未闭环（记忆连贯、人格进化）
- ❌ 记忆加载时间 ≥ 100ms
- ❌ 偏好提取准确率 ≤ 85%
- ❌ 测试报告未输出或未评审通过
- ❌ 安全扫描发现敏感信息泄露

**允许发布的条件**（全部满足）:
- ✅ P0-P1级用例100%通过
- ✅ 无致命/严重级Bug
- ✅ 一般级Bug修复率≥90%
- ✅ 核心业务流程全量闭环
- ✅ 记忆加载 < 100ms，跨会话记忆连贯 100%
- ✅ 偏好提取准确率 > 85%
- ✅ 符合需求验收标准（REQ-014-001, REQ-014-002）
- ✅ 测试报告已输出并评审通过

---

## 4. 测试用例设计规范

### 4.1 v0.14.0核心测试用例清单

#### 4.1.1 记忆管理模块测试用例

| 用例ID | 模块 | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 类型 | 阶段 |
|--------|------|---------|---------|---------|---------|--------|------|------|
| TC-MEM-001 | memory | 正常读取记忆文件 | 记忆文件存在 | 调用read_memory() | 返回记忆内容 | P0 | 功能 | 单元 |
| TC-MEM-002 | memory | 读取不存在的记忆文件 | 记忆文件不存在 | 调用read_memory() | 返回空字符串 | P0 | 边界 | 单元 |
| TC-MEM-003 | memory | 正常写入记忆文件 | 工作区已创建 | 调用write_memory(content) | 文件写入成功 | P0 | 功能 | 单元 |
| TC-MEM-004 | memory | 读取用户画像 | 用户画像文件存在 | 调用read_user_profile() | 返回用户画像内容 | P0 | 功能 | 单元 |
| TC-MEM-005 | memory | 写入用户画像 | 工作区已创建 | 调用write_user_profile(content) | 文件写入成功 | P0 | 功能 | 单元 |
| TC-MEM-006 | memory | 读取AI人格数据 | personality.json存在 | 调用read_personality() | 返回Personality实例 | P0 | 功能 | 单元 |
| TC-MEM-007 | memory | 写入AI人格数据 | 工作区已创建 | 调用write_personality(personality) | 文件写入成功 | P0 | 功能 | 单元 |
| TC-MEM-008 | memory | 保存偏好到记忆 | 记忆文件存在 | 调用save_preference_to_memory(preferences) | 偏好追加到MEMORY.md | P0 | 功能 | 单元 |
| TC-MEM-009 | memory | 从记忆加载偏好 | MEMORY.md包含偏好 | 调用load_preference_from_memory() | 返回偏好字典 | P0 | 功能 | 单元 |
| TC-MEM-010 | memory | 更新记忆上下文 | 记忆文件存在 | 调用update_memory_context(key, value) | 上下文更新成功 | P1 | 功能 | 单元 |
| TC-MEM-011 | memory | 创建记忆备份 | 记忆文件存在 | 调用create_backup() | 备份目录创建，包含版本信息 | P0 | 功能 | 单元 |
| TC-MEM-012 | memory | 恢复记忆备份 | 备份目录存在 | 调用restore_backup(backup_path) | 记忆文件恢复成功 | P0 | 功能 | 单元 |
| TC-MEM-013 | memory | 列出记忆版本 | 有多个备份 | 调用list_versions() | 返回版本列表 | P1 | 功能 | 单元 |
| TC-MEM-014 | memory | 获取记忆统计 | 记忆文件存在 | 调用get_memory_stats() | 返回统计信息 | P1 | 功能 | 单元 |
| TC-MEM-015 | memory | 跨会话记忆连贯 | 记忆已写入 | 新会话调用read_memory() | 返回之前写入的内容 | P0 | 集成 | 场景 |
| TC-MEM-016 | memory | 记忆版本回溯 | 有多个备份 | 恢复到指定版本 | 记忆内容回退到该版本 | P1 | 功能 | 场景 |

#### 4.1.2 Dream集成模块测试用例

| 用例ID | 模块 | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 类型 | 阶段 |
|--------|------|---------|---------|---------|---------|--------|------|------|
| TC-DREAM-001 | dream | 获取Dream配置 | config.json存在 | 调用get_dream_config() | 返回Dream配置 | P0 | 功能 | 单元 |
| TC-DREAM-002 | dream | 更新Dream配置 | config.json存在 | 调用update_dream_config(**kwargs) | 配置更新成功 | P0 | 功能 | 单元 |
| TC-DREAM-003 | dream | 启用自动归档 | config.json存在 | 调用enable_auto_archive() | auto_archive=true | P0 | 功能 | 单元 |
| TC-DREAM-004 | dream | 禁用自动归档 | config.json存在 | 调用disable_auto_archive() | auto_archive=false | P0 | 功能 | 单元 |
| TC-DREAM-005 | dream | 启用偏好自动提取 | config.json存在 | 调用enable_auto_extract_preferences() | auto_extract_preferences=true | P0 | 功能 | 单元 |
| TC-DREAM-006 | dream | 禁用偏好自动提取 | config.json存在 | 调用disable_auto_extract_preferences() | auto_extract_preferences=false | P0 | 功能 | 单元 |
| TC-DREAM-007 | dream | 设置记忆整理频率 | config.json存在 | 调用set_frequency("weekly") | frequency=weekly | P1 | 功能 | 单元 |
| TC-DREAM-008 | dream | 设置无效频率 | config.json存在 | 调用set_frequency("invalid") | 返回false | P1 | 边界 | 单元 |
| TC-DREAM-009 | dream | 获取Dream状态 | config.json存在 | 调用get_dream_status() | 返回状态报告 | P1 | 功能 | 单元 |
| TC-DREAM-010 | dream | 手动触发Dream整理 | Dream已启用 | 调用trigger_dream() | 触发成功 | P1 | 功能 | 单元 |
| TC-DREAM-011 | dream | Dream未启用时触发 | Dream未启用 | 调用trigger_dream() | 返回失败信息 | P1 | 边界 | 单元 |
| TC-DREAM-012 | dream | Dream配置持久化 | 更新配置 | 重新加载配置 | 配置保持更新后的值 | P0 | 集成 | 场景 |

#### 4.1.3 个性化引擎测试用例

| 用例ID | 模块 | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 类型 | 阶段 |
|--------|------|---------|---------|---------|---------|--------|------|------|
| TC-PER-001 | personality | 个性化建议-沟通风格 | 偏好设置为brief | 调用personalize_suggestion() | 返回精简后的建议 | P0 | 功能 | 单元 |
| TC-PER-002 | personality | 个性化建议-详细程度 | 偏好设置为concise | 调用personalize_suggestion() | 返回简洁的建议 | P0 | 功能 | 单元 |
| TC-PER-003 | personality | 个性化建议-训练时段 | 上下文包含训练时段 | 调用personalize_suggestion() | 返回适配时段的建议 | P1 | 功能 | 单元 |
| TC-PER-004 | personality | 调整建议强度-低强度 | 强度设置为low | 调用adjust_intensity() | 语气弱化 | P0 | 功能 | 单元 |
| TC-PER-005 | personality | 调整建议强度-高强度 | 强度设置为high | 调用adjust_intensity() | 语气强化 | P0 | 功能 | 单元 |
| TC-PER-006 | personality | 获取偏好权重 | 引擎已初始化 | 调用get_preference_weights() | 返回权重字典 | P1 | 功能 | 单元 |
| TC-PER-007 | personality | 更新用户偏好 | 引擎已初始化 | 调用update_preferences(new_prefs) | 偏好更新 | P0 | 功能 | 单元 |
| TC-PER-008 | personality | 更新AI人格 | 引擎已初始化 | 调用update_personality(new_personality) | 人格更新 | P0 | 功能 | 单元 |
| TC-PER-009 | personality | 个性化置信度计算 | 有多个偏好因素 | 调用_compute_confidence() | 返回0.0-1.0的置信度 | P1 | 功能 | 单元 |
| TC-PER-010 | personality | 沟通风格-鼓励型 | 偏好设置为encouraging | 调用personalize_suggestion() | 添加鼓励语气 | P1 | 功能 | 单元 |
| TC-PER-011 | personality | 沟通风格-分析型 | 偏好设置为analytical | 调用personalize_suggestion() | 添加分析说明 | P1 | 功能 | 单元 |

#### 4.1.4 偏好学习器测试用例

| 用例ID | 模块 | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 类型 | 阶段 |
|--------|------|---------|---------|---------|---------|--------|------|------|
| TC-LEARN-001 | learner | 从正面反馈学习训练时段 | 学习器已初始化 | 调用learn_from_feedback(训练时段反馈) | 偏好更新为反馈的时段 | P0 | 功能 | 单元 |
| TC-LEARN-002 | learner | 从正面反馈学习沟通风格 | 学习器已初始化 | 调用learn_from_feedback(沟通风格反馈) | 偏好更新为反馈的风格 | P0 | 功能 | 单元 |
| TC-LEARN-003 | learner | 从正面反馈学习训练强度 | 学习器已初始化 | 调用learn_from_feedback(训练强度反馈) | 偏好更新为反馈的强度 | P0 | 功能 | 单元 |
| TC-LEARN-004 | learner | 从负面反馈降低权重 | 有正面投票 | 调用learn_from_feedback(负面反馈) | 相关偏好投票降低 | P0 | 功能 | 单元 |
| TC-LEARN-005 | learner | 投票阈值触发更新 | 多次同类反馈 | 调用learn_from_feedback()多次 | 达到阈值后偏好更新 | P0 | 功能 | 单元 |
| TC-LEARN-006 | learner | 直接更新偏好模型 | 学习器已初始化 | 调用update_preference_model(updates) | 偏好直接更新 | P0 | 功能 | 单元 |
| TC-LEARN-007 | learner | 获取学习到的偏好 | 有学习历史 | 调用get_learned_preferences() | 返回当前偏好 | P1 | 功能 | 单元 |
| TC-LEARN-008 | learner | 重置偏好 | 有学习历史 | 调用reset_preferences() | 偏好恢复默认，历史清空 | P1 | 功能 | 单元 |
| TC-LEARN-009 | learner | 重置AI人格 | 有学习历史 | 调用reset_personality() | 人格恢复默认 | P1 | 功能 | 单元 |
| TC-LEARN-010 | learner | 获取反馈统计 | 有反馈历史 | 调用get_feedback_stats() | 返回统计数据 | P1 | 功能 | 单元 |
| TC-LEARN-011 | learner | 学习速率控制 | 不同learning_rate | 调用learn_from_feedback() | 学习速率影响更新速度 | P1 | 边界 | 单元 |
| TC-LEARN-012 | learner | 中文关键词提取 | 中文反馈内容 | 调用learn_from_feedback() | 正确提取中文偏好 | P1 | 功能 | 单元 |

#### 4.1.5 反馈闭环测试用例

| 用例ID | 模块 | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 类型 | 阶段 |
|--------|------|---------|---------|---------|---------|--------|------|------|
| TC-FEED-001 | feedback | 收集用户反馈 | 反馈闭环已初始化 | 调用collect_feedback() | 返回FeedbackRecord | P0 | 功能 | 单元 |
| TC-FEED-002 | feedback | 处理反馈更新偏好 | 有反馈记录 | 调用process_feedback() | 偏好根据反馈更新 | P0 | 功能 | 单元 |
| TC-FEED-003 | feedback | 追踪建议效果-接受 | 有个性化建议 | 调用track_suggestion_effect(accepted=True) | 记录接受效果 | P0 | 功能 | 单元 |
| TC-FEED-004 | feedback | 追踪建议效果-拒绝 | 有个性化建议 | 调用track_suggestion_effect(accepted=False) | 记录拒绝效果，触发负面反馈 | P0 | 功能 | 单元 |
| TC-FEED-005 | feedback | 获取效果统计 | 有效果追踪记录 | 调用get_effect_stats() | 返回统计数据 | P1 | 功能 | 单元 |
| TC-FEED-006 | feedback | 反馈闭环完整流程 | 反馈闭环已初始化 | 收集→处理→追踪→统计 | 完整闭环执行成功 | P0 | 集成 | 场景 |

#### 4.1.6 数据模型测试用例

| 用例ID | 模块 | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 类型 | 阶段 |
|--------|------|---------|---------|---------|---------|--------|------|------|
| TC-MODEL-001 | models | MemoryVersion序列化 | 创建MemoryVersion | 调用to_dict() | 返回字典 | P1 | 功能 | 单元 |
| TC-MODEL-002 | models | UserPreferences序列化/反序列化 | 创建UserPreferences | to_dict() → from_dict() | 数据一致 | P0 | 功能 | 单元 |
| TC-MODEL-003 | models | Personality序列化/反序列化 | 创建Personality | to_dict() → from_dict() | 数据一致 | P0 | 功能 | 单元 |
| TC-MODEL-004 | models | PersonalizedSuggestion序列化 | 创建PersonalizedSuggestion | 调用to_dict() | 返回字典 | P1 | 功能 | 单元 |
| TC-MODEL-005 | models | FeedbackRecord序列化 | 创建FeedbackRecord | 调用to_dict() | 返回字典 | P1 | 功能 | 单元 |
| TC-MODEL-006 | models | PersonalityVersion序列化 | 创建PersonalityVersion | 调用to_dict() | 返回字典 | P1 | 功能 | 单元 |
| TC-MODEL-007 | models | UserPreferences默认值 | 无参数 | UserPreferences.default() | 返回默认偏好 | P1 | 功能 | 单元 |
| TC-MODEL-008 | models | Personality默认值 | 无参数 | Personality.default() | 返回默认人格 | P1 | 功能 | 单元 |

#### 4.1.7 场景级集成测试用例

| 用例ID | 模块 | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 类型 | 阶段 |
|--------|------|---------|---------|---------|---------|--------|------|------|
| TC-SCENE-001 | scene | 记忆写入→读取→备份→恢复 | 临时工作区 | 写入记忆→读取验证→创建备份→恢复备份→验证内容 | 全流程成功 | P0 | 集成 | 场景 |
| TC-SCENE-002 | scene | 反馈收集→偏好学习→人格进化 | 反馈闭环已初始化 | 收集多次反馈→偏好更新→人格调整 | 完整进化链路 | P0 | 集成 | 场景 |
| TC-SCENE-003 | scene | Dream配置→自动归档→偏好提取 | Dream已配置 | 启用自动归档→启用偏好提取→触发Dream | 配置生效 | P0 | 集成 | 场景 |
| TC-SCENE-004 | scene | 跨会话记忆连贯性 | 第一次会话写入记忆 | 新会话读取记忆 | 记忆内容一致 | P0 | 集成 | 场景 |
| TC-SCENE-005 | scene | 人格版本回溯 | 有多个人格版本 | 回退到指定版本 | 人格恢复到该版本 | P1 | 集成 | 场景 |
| TC-SCENE-006 | scene | 偏好学习准确率验证 | 构造已知偏好反馈 | 多次反馈学习→对比学习结果 | 准确率>85% | P0 | 集成 | 场景 |
| TC-SCENE-007 | scene | 记忆+人格协同工作 | 记忆和人格已初始化 | 从记忆加载偏好→应用到人格→生成建议 | 协同工作正常 | P0 | 集成 | 场景 |

#### 4.1.8 E2E用户旅程测试用例

| 用例ID | 模块 | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 类型 | 阶段 |
|--------|------|---------|---------|---------|---------|--------|------|------|
| TC-E2E-001 | e2e | AI教练记住训练偏好 | 初始状态 | 1.用户多次表达偏好 2.关闭应用 3.重新打开 4.验证AI记得偏好 | AI记住并应用偏好 | P0 | E2E | E2E |
| TC-E2E-002 | e2e | AI人格进化用户旅程 | 初始状态 | 1.用户多次反馈 2.观察人格变化 3.验证沟通风格贴合 | 人格逐步进化 | P0 | E2E | E2E |
| TC-E2E-003 | e2e | 用户查看和修改偏好数据 | 有学习到的偏好 | 1.查看当前偏好 2.修改偏好 3.验证修改生效 | 用户可控进化 | P0 | E2E | E2E |
| TC-E2E-004 | e2e | 记忆版本回溯用户旅程 | 有多个记忆版本 | 1.查看版本历史 2.选择版本回溯 3.验证记忆恢复 | 版本回溯成功 | P1 | E2E | E2E |

#### 4.1.9 性能测试用例

| 用例ID | 模块 | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 类型 | 阶段 |
|--------|------|---------|---------|---------|---------|--------|------|------|
| TC-PERF-001 | perf | 记忆加载时间 | 记忆文件存在 | 调用read_memory()计时 | < 100ms | P0 | 性能 | 性能 |
| TC-PERF-002 | perf | 偏好数据加载时间 | personality.json存在 | 调用read_personality()计时 | < 100ms | P0 | 性能 | 性能 |
| TC-PERF-003 | perf | 反馈处理响应时间 | 反馈闭环已初始化 | 调用process_feedback()计时 | < 500ms | P0 | 性能 | 性能 |
| TC-PERF-004 | perf | 记忆备份创建时间 | 记忆文件存在 | 调用create_backup()计时 | < 1秒 | P1 | 性能 | 性能 |
| TC-PERF-005 | perf | 人格进化计算时间 | 有足够反馈 | 调用learn_from_feedback()计时 | < 100ms | P1 | 性能 | 性能 |

---

## 5. 测试执行计划

### 5.1 测试阶段划分

| 阶段 | 测试类型 | 执行顺序 | 预计用例数 | 通过标准 |
|------|---------|---------|-----------|---------|
| 第一阶段 | 单元测试 | 1 | ~50 | 100%通过 |
| 第二阶段 | 模块内集成测试 | 2 | ~15 | ≥95%通过 |
| 第三阶段 | 场景级集成测试 | 3 | ~7 | 100%通过 |
| 第四阶段 | E2E测试 | 4 | ~4 | 100%通过 |
| 第五阶段 | 性能测试 | 5 | ~5 | 100%通过 |

### 5.2 测试执行命令

```bash
# 第一阶段：单元测试
uv run pytest tests/unit/core/memory/ tests/unit/core/personality/ -v --tb=short

# 第二阶段：模块内集成测试
uv run pytest tests/integration/module/ -k "memory or personality or dream" -v

# 第三阶段：场景级集成测试
uv run pytest tests/integration/scene/ -k "memory or personality or dream" -v

# 第四阶段：E2E测试
uv run pytest tests/e2e/ -k "memory or personality" -v

# 第五阶段：性能测试
uv run pytest tests/performance/ -k "memory or personality" -v

# 覆盖率报告
uv run pytest tests/unit/core/memory/ tests/unit/core/personality/ --cov=src/core/memory --cov=src/core/personality --cov-report=term-missing
```

---

## 6. 测试环境配置

### 6.1 测试数据构造

**记忆测试数据**:
```python
@pytest.fixture
def temp_workspace(tmp_path):
    """创建临时工作区"""
    workspace = tmp_path / "test_workspace"
    workspace.mkdir()
    return workspace

@pytest.fixture
def sample_memory_content():
    """样本记忆内容"""
    return """# 项目记忆

## 训练历史
- 2024-01-01: 5km 轻松跑
- 2024-01-03: 10km 节奏跑

## 用户偏好
- training_time: morning
- communication_style: encouraging

## 上下文信息
- 目标: 半马完赛
"""

@pytest.fixture
def sample_preferences():
    """样本偏好数据"""
    return {
        "training_time": "morning",
        "training_intensity": "medium",
        "communication_style": "encouraging",
    }
```

**人格测试数据**:
```python
@pytest.fixture
def sample_personality():
    """样本AI人格"""
    return Personality(
        communication_style="encouraging",
        suggestion_approach="gradual",
        empathy_level=0.8,
        humor_level=0.3,
        motivation_style="supportive",
    )

@pytest.fixture
def sample_feedback():
    """样本反馈数据"""
    return FeedbackRecord(
        id="fb_001",
        feedback_type=FeedbackType.POSITIVE,
        content="我喜欢简洁的建议",
        preference_category=PreferenceCategory.COMMUNICATION_STYLE,
    )
```

### 6.2 Mock策略

```python
from unittest.mock import MagicMock, patch

@pytest.fixture
def mock_llm_api():
    """Mock LLM API调用"""
    with patch("src.core.personality.personalization_engine.LLMAPI") as mock:
        mock.return_value.generate.return_value = "个性化建议内容"
        yield mock

@pytest.fixture
def mock_config_file(tmp_path):
    """Mock配置文件"""
    config_path = tmp_path / "config.json"
    config_data = {
        "dream": {
            "enabled": True,
            "frequency": "daily",
            "auto_archive": True,
            "auto_extract_preferences": True,
        }
    }
    config_path.write_text(json.dumps(config_data))
    return config_path
```

---

## 7. 风险评估与应对

### 7.1 技术风险

| 风险ID | 风险描述 | 概率 | 影响 | 缓解措施 |
|--------|---------|------|------|---------|
| R001 | 记忆文件并发读写冲突 | 中 | 高 | 测试文件锁机制 |
| R002 | 偏好学习过度拟合 | 中 | 中 | 测试学习速率控制 |
| R003 | Dream集成与nanobot SDK版本不兼容 | 低 | 高 | 测试SDK版本兼容性 |
| R004 | 记忆加载时间不达标 | 低 | 高 | 性能基准测试 |

### 7.2 业务风险

| 风险ID | 风险描述 | 概率 | 影响 | 缓解措施 |
|--------|---------|------|------|---------|
| R005 | 偏好提取准确率不达标 | 中 | 高 | 增加测试样本，优化提取逻辑 |
| R006 | 人格进化效果不明显 | 中 | 中 | 用户调研，调整进化参数 |

---

## 8. 验收标准映射

### 8.1 REQ-014-001 AI教练长期记忆

| 验收标准 | 对应用例 | 验证方法 |
|---------|---------|---------|
| AI可自动归档对话历史 | TC-DREAM-003, TC-DREAM-012 | 功能测试 |
| AI可自动提取用户偏好 | TC-DREAM-005, TC-SCENE-006 | 功能测试 |
| 跨会话记忆连贯 | TC-MEM-015, TC-SCENE-004, TC-E2E-001 | 集成测试 + E2E |
| 记忆加载时间 < 100ms | TC-PERF-001 | 性能测试 |

### 8.2 REQ-014-002 AI人格进化

| 验收标准 | 对应用例 | 验证方法 |
|---------|---------|---------|
| AI人格可根据用户反馈进化 | TC-LEARN-001~005, TC-FEED-001~004, TC-SCENE-002 | 功能测试 + 集成测试 |
| 用户可查看和修改偏好数据 | TC-E2E-003 | E2E测试 |
| 用户满意度 > 4.3/5 | TC-E2E-002 | 用户调研（测试阶段模拟） |

---

## 9. 测试统计

| 统计项 | 数量 |
|--------|------|
| **测试用例总数** | ~91 |
| **P0级用例数** | ~45 |
| **P1级用例数** | ~46 |
| **单元测试用例** | ~50 |
| **集成测试用例** | ~22 |
| **E2E测试用例** | ~4 |
| **性能测试用例** | ~5 |
| **门禁规则数** | 15 |
| **验收标准覆盖** | 100% |

---

*本测试策略文档由测试工程师智能体基于需求规格说明书v2.0和架构设计说明书v6.1编写*
