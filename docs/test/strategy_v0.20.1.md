# v0.20.1 ML核心修复 — 测试策略

> **文档版本**: v1.0
> **创建日期**: 2026-05-11
> **目标版本**: v0.20.1
> **对齐文档**:
> - [需求规格说明书 v8.2](../requirements/REQ_需求规格说明书.md)
> - [架构设计说明书 v7.1.0](../architecture/架构设计说明书.md)
> - [产品规划方案 v9.1](../product/产品规划方案.md)
> - [开发任务清单 v1.0](../planning/task_list_v0.20.1.md)
> - [实施计划 v1.0](../planning/implementation_plan_v0.20.1.md)
> - [测试策略与规范 v3.1](./测试策略与规范.md)
> - [v0.20.0 测试策略](./strategy_v0.20.0.md)

---

## 1. 测试范围

### 1.1 版本概述

**版本主题**: ML核心修复 —— 补全v0.20.0未实现的ML训练与推理核心能力
**核心目标**: 让ML增强预测从"架构完整但核心空心的壳"变为"真正可训练、可推理、可交付"的功能
**问题根因**: v0.20.0开发过程中，自底向上实现了数据模型/CLI/Agent工具/降级策略等"壳"，但ML模型训练(GradientBoosting的fit)和基于真实特征的推理从未实现，导致整个系统实际运行在基础预测模式

### 1.2 v0.20.1 增量变更范围

| 变更类别 | 变更内容 | 影响范围 |
|---------|---------|---------|
| 依赖注入修复 | AppContext新增4个延迟属性 + prediction_engine DI链修复 | `src/core/base/context.py` |
| 特征工程修复 | 25个特征从真实数据源获取（原全部=0） | `src/core/prediction/feature_engine.py` |
| VDOT ML训练推理 | 3个分位数GBDT训练 + SHAP分析 + 冷启动 | `src/core/prediction/vdot_predictor.py` |
| 伤病 ML训练推理 | LR+GBDT集成训练 + 伤病标签持久化 | `src/core/prediction/injury_predictor.py` |
| 比赛个人化 | 跑者分类 + Riegel拟合 + 赛前修正 | `src/core/prediction/race_predictor.py` |
| 训练响应真实化 | Banister IR参数真实化 | `src/core/prediction/training_response_predictor.py` |
| Agent工具补全 | ReportInjuryTool + ManagePredictionModelTool | `src/agents/tools.py` |
| 模型持久化补全 | predictions.parquet + 增量学习触发 | `src/core/prediction/model_manager.py` |
| CLI命令对齐 | predict model子命令组 + Rich进度条 + ML标注 | `src/cli/commands/prediction.py` |
| PredictionEngine补全 | manage_model() rollback分支 | `src/core/prediction/prediction_engine.py` |

### 1.3 测试需求覆盖

| 需求ID | 需求名称 | 优先级 | v0.20.0状态 | v0.20.1增量 | 测试类型 |
|--------|---------|--------|-------------|------------|---------|
| REQ-0.20-01 | ML-VDOT趋势预测引擎 | P0 | 架构+降级已完成，ML训练推理缺失 | ML训练推理+SHAP+冷启动 | 单元+集成+E2E |
| REQ-0.20-02 | 个人化比赛成绩预测 | P0 | 架构已完成，个人化硬编码 | 跑者分类+Riegel拟合+赛前修正 | 单元+集成+E2E |
| REQ-0.20-03 | ML伤病风险预测 | P0 | 架构+降级已完成，ML推理硬编码 | LR+GBDT集成+伤病标签持久化 | 单元+集成+E2E |
| REQ-0.20-04 | 伤病报告工具 | P1 | PredictionEngine已实现，Agent层缺失 | ReportInjuryTool + 持久化 | 单元+集成 |
| REQ-0.20-05 | 训练响应预测工具 | P1 | 架构已完成，参数硬编码 | Banister IR参数真实化 | 单元+集成 |
| REQ-0.20-06 | 模型管理与校准 | P1 | 基础实现，缺持久化+rollback | predictions.parquet+增量学习+rollback | 单元+集成+E2E |
| REQ-0.20-07 | 数据充足度评估 | P1 | 已实现 | 依赖注入修复后自动生效 | 回归验证 |

### 1.4 不纳入测试范围

- v0.20.0已测试通过的降级策略、数据模型、CLI基础命令（仅做回归验证）
- 第三方依赖内部实现（scikit-learn、scipy、shap、joblib等）
- nanobot-ai框架核心功能
- 操作系统级别的文件系统行为
- LLM模型输出内容的不确定性验证
- v0.21+版本功能（数字孪生、多视角验证等）

---

## 2. 测试类型与策略

### 2.1 单元测试（Unit Testing）

**职责**: 开发工程师主责，测试工程师负责规范指导和结果校验

**v0.20.1 增量覆盖范围**:

| 模块 | 测试文件 | 增量用例数 | 说明 |
|------|---------|-----------|------|
| `src/core/base/context.py` | `test_context_prediction.py` | 8 | AppContext 4个新属性 + DI链验证 |
| `src/core/prediction/feature_engine.py` | `test_feature_engine_integration.py` | 6 | 特征值非零验证（Mock依赖） |
| `src/core/prediction/vdot_predictor.py` | `test_vdot_predictor.py` | 10 | ML训练+推理+SHAP+冷启动 |
| `src/core/prediction/injury_predictor.py` | `test_injury_predictor.py` | 10 | LR+GBDT集成+标签持久化 |
| `src/core/prediction/race_predictor.py` | `test_race_predictor.py` | 6 | 跑者分类+Riegel拟合+赛前修正 |
| `src/core/prediction/model_manager.py` | `test_model_manager.py` | 8 | predictions.parquet+增量学习+sklearn兼容 |
| `src/core/prediction/prediction_engine.py` | `test_prediction_engine.py` | 2 | rollback分支 |
| `src/agents/tools.py` | `test_tools.py` | 2 | ReportInjuryTool + ManagePredictionModelTool |

**覆盖率要求**:

| 模块 | 最低覆盖率 | 说明 |
|------|-----------|------|
| `src/core/prediction/` | ≥80% | 核心预测逻辑（与v0.20.0一致） |
| `src/core/prediction/vdot_predictor.py` | ≥85% | ML训练推理核心 |
| `src/core/prediction/injury_predictor.py` | ≥85% | ML训练推理核心 |
| `src/core/prediction/feature_engine.py` | ≥85% | 特征提取核心 |
| `src/core/prediction/model_manager.py` | ≥80% | 持久化核心 |
| `src/core/base/context.py` | ≥80% | 依赖注入链 |

### 2.2 集成测试（Integration Testing）

**职责划分**:

| 测试类型 | 目录 | 负责人 |
|---------|------|--------|
| 模块内集成测试 | `tests/integration/module/` | 开发工程师 |
| 场景级集成测试 | `tests/integration/scene/` | 测试工程师 |

**v0.20.1 场景级集成测试覆盖**:

| 场景ID | 场景名称 | 覆盖链路 | 优先级 |
|--------|---------|---------|--------|
| SCN-01 | 数据充足→特征提取→VDOT ML训练→推理→SHAP分析 | FeatureEngine→VDOTPredictor.train_model()→_run_ml_inference()→get_feature_importance() | P0 |
| SCN-02 | 数据充足→特征提取→伤病LR+GBDT训练→集成推理→风险时间线 | FeatureEngine→InjuryPredictor.train_model()→_run_ml_inference() | P0 |
| SCN-03 | 比赛记录≥3→Riegel拟合→跑者分类→个人化预测→配速策略 | RacePredictor._classify_runner_type()→fit_riegel_curve()→predict_race() | P0 |
| SCN-04 | 数据不足→自动降级→基础预测→提示信息 | DataAssessor→降级链路→prediction_type="basic" | P0 |
| SCN-05 | 伤病报告→标签持久化→模型训练→风险预测 | report_injury()→injury_labels/→train_model()→predict_injury_risk() | P1 |
| SCN-06 | 模型管理→版本回滚→预测校准 | ModelManager.rollback()→load_model()→predict() | P1 |
| SCN-07 | 新数据导入→预测缓存失效→增量学习触发 | data import→check_auto_update()→增量训练 | P1 |
| SCN-08 | BodySignalEngine→InjuryPredictor数据流 | body_signal_engine→FeatureEngine→InjuryPredictor | P1 |
| SCN-09 | CLI predict→PredictionEngine→降级链路 | CLI命令→PredictionEngine→三层降级 | P0 |
| SCN-10 | Agent工具→PredictionEngine→超时处理 | Agent工具调用→PredictionEngine→超时降级 | P1 |

### 2.3 端到端测试（E2E Testing）

**职责**: 测试工程师主责

**v0.20.1 E2E测试覆盖**:

| 用例ID | 用例名称 | 用户旅程 | 优先级 |
|--------|---------|---------|--------|
| E2E-01 | 数据充足用户首次使用ML预测 | 导入数据→predict status→predict vdot --days 30→查看ML增强预测结果+SHAP分析 | P0 |
| E2E-02 | 数据不足用户降级体验 | 导入少量数据→predict vdot --days 30→查看降级提示→了解数据积累建议 | P0 |
| E2E-03 | 伤病风险全流程 | predict injury-risk --days 21→查看风险时间线→report_injury→再次预测验证标签生效 | P0 |
| E2E-04 | 比赛预测个人化流程 | 导入含比赛记录数据→predict race --distance marathon→查看个人化预测+配速策略 | P0 |
| E2E-05 | 模型管理全流程 | predict model status→predict model train --type vdot→predict model rollback→验证回滚效果 | P1 |
| E2E-06 | 数据积累后自动升级 | 初始数据不足→持续导入→数据达标→自动触发ML训练→预测类型从basic升级为ml_enhanced | P1 |

**测试环境**: 使用临时测试目录，Mock所有外部依赖，使用`tests/data/fixtures/`下的样本FIT文件

### 2.4 回归测试范围

v0.20.1 必须对以下 v0.20.0 已实现功能执行回归验证：

| 回归范围 | 验证内容 | 优先级 |
|---------|---------|--------|
| 降级策略 | 数据不足→基础预测、数据中等→参数化基线 两条降级链路不受影响 | P0 |
| 数据模型 | VDOTPrediction/RacePredictionResult/InjuryRiskPrediction 等 frozen dataclass 序列化/反序列化正常 | P0 |
| CLI基础命令 | predict status/vdot/race/injury-risk 基础参数校验和输出格式正常 | P0 |
| Agent工具 | predict_vdot_trend/predict_race_result/predict_injury_risk/check_prediction_status 5个已有工具正常 | P0 |
| 现有单元测试 | `tests/unit/core/prediction/` 下所有已有测试用例全部通过 | P0 |
| 现有集成测试 | `tests/integration/module/` 下已有测试用例全部通过 | P0 |

---

## 3. 门禁规则

### 3.1 测试准入规则

代码进入测试环节前，必须满足以下条件：

| 条件 | 验证方式 | 责任人 |
|------|---------|--------|
| 需求规格说明书已评审通过 | 文档存在且版本匹配(v8.2) | 架构师 |
| 架构设计说明书已评审通过 | 文档存在且版本匹配(v7.1.0) | 架构师 |
| 开发任务清单已确认 | 文档存在(`task_list_v0.20.1.md`) | 架构师 |
| 开发完成并通过自测 | 开发者自测报告 | 开发工程师 |
| 单元测试覆盖率达标 | `pytest --cov` 报告（prediction模块≥80%） | 开发工程师 |
| 代码质量检查通过 | `ruff check` 零警告 | 开发工程师 |
| 类型检查通过 | `mypy` 无新增错误 | 开发工程师 |
| 无未解决的P0/P1 Bug | Bug清单状态 | 开发工程师 |
| ML依赖安装验证 | `uv run python -c "import sklearn, scipy, shap, joblib"` | 开发工程师 |
| v0.20.0回归测试通过 | `pytest tests/unit/core/prediction/ -v` 全部通过 | 开发工程师 |

**准入验证命令**:
```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/ --ignore-missing-imports
uv run pytest tests/unit/ --cov=src/core/prediction --cov-report=term-missing
uv run python -c "import sklearn, scipy, shap, joblib; print('ML dependencies OK')"
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
| ML训练可用 | 数据充足时train_model()返回success=True | 单元测试+集成测试 |
| ML推理可用 | 数据充足时prediction_type="ml_enhanced" | 端到端测试 |
| 特征非零 | 有数据时FeatureEngine特征值≠0 | 单元测试 |
| VDOT预测准确率 | ML预测误差<5%（对比基础预测8%） | 性能测试 |
| 伤病预警召回率 | 3周前置预警召回率>75% | 性能测试 |
| 性能要求 | ML预测响应<5秒，模型训练<5分钟 | 性能测试 |
| 降级策略 | 数据不足时自动降级，不阻塞用户 | E2E测试 |
| 安全合规 | 无敏感信息泄露，模型本地存储 | 安全扫描 |
| 无回归 | v0.20.0已有功能全部正常 | 回归测试 |

**准出验证命令**:
```bash
uv run pytest tests/ -v --tb=short
uv run pytest tests/integration/ -v
uv run pytest tests/e2e/ -v
```

### 3.3 上线门禁规则

**绝对禁止发布的情况**:
- 存在任何致命或严重级Bug
- P0级用例通过率 < 100%
- ML训练不可用（train_model()失败或返回training_samples=0）
- ML推理不可用（prediction_type永远不为"ml_enhanced"）
- FeatureEngine特征值在有数据时仍为0
- VDOT预测准确率不达标（ML预测误差≥5%）
- 伤病预警召回率<75%
- 降级策略失效（数据不足时阻塞用户或崩溃）
- 核心业务流程未闭环
- v0.20.0已有功能出现回归
- 测试报告未输出或未评审通过

**允许发布的条件**（全部满足）:
- P0-P1级用例100%通过
- 无致命/严重级Bug
- 一般级Bug修复率≥90%
- 核心业务流程全量闭环
- ML训练与推理功能可用
- FeatureEngine特征值非零
- VDOT预测准确率达标
- 伤病预警召回率>75%
- 性能要求达标
- 降级策略正常
- 无回归问题
- 符合需求验收标准
- 测试报告已输出并评审通过

---

## 4. 测试用例清单

### 4.1 P0需求测试用例

#### 4.1.1 R01: AppContext依赖注入链修复

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 类型 |
|--------|---------|---------|---------|---------|--------|------|
| TC-CTX-001 | training_load_analyzer属性存在且类型正确 | AppContextFactory.create() | 访问context.training_load_analyzer | 返回TrainingLoadAnalyzer实例，非None | P0 | 单元 |
| TC-CTX-002 | vdot_calculator属性存在且类型正确 | AppContextFactory.create() | 访问context.vdot_calculator | 返回VDOTCalculator实例，非None | P0 | 单元 |
| TC-CTX-003 | race_prediction_engine属性存在且类型正确 | AppContextFactory.create() | 访问context.race_prediction_engine | 返回RacePredictionEngine实例，非None | P0 | 单元 |
| TC-CTX-004 | injury_risk_analyzer属性存在且类型正确 | AppContextFactory.create() | 访问context.injury_risk_analyzer | 返回InjuryRiskAnalyzer实例，非None | P0 | 单元 |
| TC-CTX-005 | FeatureEngine接收全部5个依赖 | AppContextFactory.create() | 检查prediction_engine._vdot_predictor._feature_engine | session_repo/training_load_analyzer/hrv_analyzer/body_signal_engine/vdot_calculator均非None | P0 | 单元 |
| TC-CTX-006 | VDOTPredictor接收race_engine参数 | AppContextFactory.create() | 检查prediction_engine._vdot_predictor._race_engine | race_engine非None | P0 | 单元 |
| TC-CTX-007 | RacePredictor接收race_engine+body_signal_engine | AppContextFactory.create() | 检查prediction_engine._race_predictor | _race_engine和_body_signal_engine均非None | P0 | 单元 |
| TC-CTX-008 | InjuryPredictor接收injury_analyzer参数 | AppContextFactory.create() | 检查prediction_engine._injury_predictor._injury_analyzer | injury_analyzer非None | P0 | 单元 |
| TC-CTX-009 | 4个新属性使用get_extension/set_extension单例模式 | AppContextFactory.create() | 两次访问同一属性 | 返回同一实例（id()相同） | P0 | 单元 |
| TC-CTX-010 | mypy类型检查无新增错误 | DI链修复完成 | `mypy src/core/base/context.py --ignore-missing-imports` | 无错误输出 | P0 | 静态分析 |

#### 4.1.2 R02: FeatureEngine特征提取真实化

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 类型 |
|--------|---------|---------|---------|---------|--------|------|
| TC-FEAT-001 | VDOT特征weekly_volume_km非零 | Mock session_repo返回有数据 | 调用extract_vdot_features() | weekly_volume_km > 0 | P0 | 单元 |
| TC-FEAT-002 | VDOT特征ctl_value非零 | Mock training_load_analyzer | 调用extract_vdot_features() | ctl_value > 0 | P0 | 单元 |
| TC-FEAT-003 | VDOT特征tsb_value非零 | Mock training_load_analyzer | 调用extract_vdot_features() | tsb_value != 0 | P0 | 单元 |
| TC-FEAT-004 | VDOT特征fatigue_score非零 | Mock body_signal_engine | 调用extract_vdot_features() | fatigue_score > 0 | P0 | 单元 |
| TC-FEAT-005 | 伤病特征atl_ctl_ratio非零 | Mock training_load_analyzer | 调用extract_injury_features() | atl_ctl_ratio > 0 | P0 | 单元 |
| TC-FEAT-006 | 比赛特征current_vdot非零 | Mock vdot_calculator | 调用extract_race_features() | current_vdot > 0 | P0 | 单元 |
| TC-FEAT-007 | 特征缺失时跳过并记录warning | Mock依赖部分返回None | 调用特征提取 | 不抛异常，warning日志包含缺失特征名 | P0 | 单元 |
| TC-FEAT-008 | 同日缓存机制正常 | 同一天两次调用 | 两次调用extract_vdot_features() | 第二次使用缓存，不重复计算 | P0 | 单元 |
| TC-FEAT-009 | 日期变更缓存失效 | 跨天两次调用 | Mock日期变更后调用 | 缓存失效，重新计算特征 | P0 | 单元 |
| TC-FEAT-010 | 特征提取耗时<3秒 | Mock依赖，正常数据量 | 计时调用extract_vdot_features() | 耗时 < 3秒 | P0 | 性能 |

#### 4.1.3 R03: VDOTPredictor ML训练与推理

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 类型 |
|--------|---------|---------|---------|---------|--------|------|
| TC-VDOT-101 | 数据充足时train_model()训练3个分位数模型 | Mock 400+条特征数据 | 调用train_model() | 返回ModelTrainingResult(success=True)，training_samples>0 | P0 | 单元 |
| TC-VDOT-102 | 训练后模型持久化到磁盘 | train_model()成功 | 检查~/.nanobot-runner/models/ | 存在vdot_p10/p50/p90三个.joblib文件 | P0 | 单元 |
| TC-VDOT-103 | 训练后模型可加载并推理 | 模型已持久化 | 调用_run_ml_inference() | prediction_type="ml_enhanced"，返回有效VDOTPrediction | P0 | 单元 |
| TC-VDOT-104 | 分位数回归输出(p10, p50, p90)置信区间 | ML模型已训练 | 调用predict_vdot() | p10 < p50 < p90，区间合理 | P0 | 单元 |
| TC-VDOT-105 | SHAP特征重要性输出Top3 | ML模型已训练 | 调用get_feature_importance() | 返回3个VDOTFactor，含name/weight/direction | P0 | 单元 |
| TC-VDOT-106 | SHAP超时降级为sklearn内置feature_importances_ | Mock SHAP计算超时 | 调用get_feature_importance() | 降级为sklearn feature_importances_，不抛异常 | P0 | 单元 |
| TC-VDOT-107 | _predict_parametric()使用真实TSS序列 | Mock session_repo返回TSS数据 | 调用_predict_parametric() | 使用真实TSS序列，非np.full(30, 50.0) | P0 | 单元 |
| TC-VDOT-108 | 首次预测自动训练（冷启动） | 数据充足但无模型文件 | 调用predict_vdot() | 自动触发train_model()，Rich进度条显示 | P0 | 单元 |
| TC-VDOT-109 | 模型文件损坏自动重训 | 模型文件被破坏 | 调用predict_vdot() | 自动重新训练，不阻塞用户 | P0 | 单元 |
| TC-VDOT-110 | 数据不足时train_model()返回降级 | Mock <200条数据 | 调用train_model() | 返回ModelTrainingResult(success=False)，含降级原因 | P0 | 单元 |
| TC-VDOT-111 | ML预测推理耗时<2秒 | ML模型已训练 | 计时调用_run_ml_inference() | 耗时 < 2秒 | P0 | 性能 |
| TC-VDOT-112 | SHAP分析耗时<5秒 | ML模型已训练 | 计时调用get_feature_importance() | 耗时 < 5秒 | P0 | 性能 |

#### 4.1.4 R04: InjuryPredictor ML训练与推理

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 类型 |
|--------|---------|---------|---------|---------|--------|------|
| TC-INJ-101 | 数据充足时train_model()训练LR+GBDT集成 | Mock 300+条特征数据 | 调用train_model() | 返回ModelTrainingResult(success=True) | P0 | 单元 |
| TC-INJ-102 | LR+GBDT集成权重0.4/0.6 | 模型已训练 | 检查集成预测概率 | LR概率×0.4 + GBDT概率×0.6 = 集成概率 | P0 | 单元 |
| TC-INJ-103 | CalibratedClassifierCV校准概率 | 模型已训练 | 检查LR模型 | LR被CalibratedClassifierCV包装，method='isotonic' | P0 | 单元 |
| TC-INJ-104 | _run_ml_inference()使用真实模型推理 | 模型已训练 | 调用_run_ml_inference() | 风险值非硬编码，prediction_type="ml_enhanced" | P0 | 单元 |
| TC-INJ-105 | 风险时间线输出7/14/21天概率 | 模型已训练 | 调用predict_injury_risk(days=21) | 返回risk_timeline含day_7/day_14/day_21概率 | P0 | 单元 |
| TC-INJ-106 | Top3风险因子含贡献度 | 模型已训练 | 调用predict_injury_risk() | 返回3个RiskFactor，贡献度之和≈1.0 | P0 | 单元 |
| TC-INJ-107 | AcuteLoadRisk/ChronicRisk/BodySignalRisk从特征值计算 | 模型已训练 | 调用predict_injury_risk() | 三个风险分量从特征值计算，非硬编码 | P0 | 单元 |
| TC-INJ-108 | report_injury()持久化到磁盘 | 调用report_injury() | 检查~/.nanobot-runner/injury_labels/ | 存在{injury_id}.json文件，含完整伤病信息 | P0 | 单元 |
| TC-INJ-109 | 伤病标签三级体系 | 调用report_injury() | 分别传入confirmed/suspected/unconfirmed | 标签正确存储和读取 | P0 | 单元 |
| TC-INJ-110 | load_injury_labels()加载已有标签 | 已有伤病标签文件 | 调用load_injury_labels() | 返回标签列表，用于模型训练 | P0 | 单元 |
| TC-INJ-111 | 无伤病标签时使用规则基线伪标签 | 无伤病标签文件 | 调用train_model() | 使用规则基线生成伪标签，训练不中断 | P0 | 单元 |
| TC-INJ-112 | 三层降级完整：ML→LR→规则基线 | 不同数据量 | 分别测试300+/100-300/<100条 | prediction_type分别为ml_enhanced/parametric/basic | P0 | 单元 |

#### 4.1.5 R05: RacePredictor个人化实现

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 类型 |
|--------|---------|---------|---------|---------|--------|------|
| TC-RACE-101 | 跑者分类为"speed" | Mock短距离成绩相对好 | 调用_classify_runner_type() | 返回"speed" | P0 | 单元 |
| TC-RACE-102 | 跑者分类为"endurance" | Mock长距离成绩相对好 | 调用_classify_runner_type() | 返回"endurance" | P0 | 单元 |
| TC-RACE-103 | 跑者分类为"balanced" | Mock各距离成绩均衡 | 调用_classify_runner_type() | 返回"balanced" | P0 | 单元 |
| TC-RACE-104 | Riegel曲线拟合基于真实比赛数据 | Mock 3次+比赛记录 | 调用fit_riegel_curve() | 返回个人化riegel_exponent（0.95-1.15） | P0 | 单元 |
| TC-RACE-105 | 赛前状态修正集成BodySignalEngine | Mock疲劳度高 | 调用predict_race() | 预测成绩下调2-5% | P0 | 单元 |
| TC-RACE-106 | 恢复状态好时成绩上调 | Mock TSB>0 | 调用predict_race() | 预测成绩上调1-3% | P0 | 单元 |
| TC-RACE-107 | 全马配速策略输出每5km分段 | 个人化模型可用 | 调用predict_race(distance=marathon) | 返回pace_strategy含8个分段配速 | P0 | 单元 |
| TC-RACE-108 | 预测历史记录保存到predictions.parquet | 执行比赛预测 | 检查predictions.parquet | 新增一条PredictionRecord | P0 | 单元 |

### 4.2 P1需求测试用例

#### 4.2.1 R06: TrainingResponsePredictor真实化

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 类型 |
|--------|---------|---------|---------|---------|--------|------|
| TC-TR-001 | Banister IR模型参数有生理学意义 | Mock训练数据 | 调用predict_training_response() | fitness/fatigue参数在合理范围 | P1 | 单元 |
| TC-TR-002 | 恢复时间估算合理 | 不同训练类型 | 分别测试轻松跑/节奏跑/间歇跑 | 恢复时间：<12h / 24-48h / 48-72h | P1 | 单元 |
| TC-TR-003 | prediction_type为"parametric"或"basic" | 正常调用 | 调用predict_training_response() | prediction_type非None，为parametric或basic | P1 | 单元 |
| TC-TR-004 | 返回TrainingResponse数据结构完整 | 正常调用 | 调用predict_training_response() | 所有字段非None，类型正确 | P1 | 单元 |

#### 4.2.2 R07: Agent工具补全

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 类型 |
|--------|---------|---------|---------|---------|--------|------|
| TC-AGENT-001 | ReportInjuryTool完整实现 | PredictionEngine已实现report_injury | 调用ReportInjuryTool | 返回JSON格式{success, data, message} | P1 | 单元 |
| TC-AGENT-002 | ManagePredictionModelTool支持status操作 | PredictionEngine已实现manage_model | 调用ManagePredictionModelTool(action="status") | 返回模型状态信息JSON | P1 | 单元 |
| TC-AGENT-003 | ManagePredictionModelTool支持train操作 | 数据充足 | 调用ManagePredictionModelTool(action="train") | 返回训练结果JSON | P1 | 单元 |
| TC-AGENT-004 | ManagePredictionModelTool支持rollback操作 | 有历史版本 | 调用ManagePredictionModelTool(action="rollback") | 返回回滚结果JSON | P1 | 单元 |
| TC-AGENT-005 | TOOL_DESCRIPTIONS包含7个预测工具 | 工具注册完成 | 检查TOOL_DESCRIPTIONS | 含predict_vdot_trend等7个工具描述 | P1 | 单元 |

#### 4.2.3 R08: ModelManager数据持久化补全

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 类型 |
|--------|---------|---------|---------|---------|--------|------|
| TC-MGR-001 | record_prediction()写入predictions.parquet | 正常调用 | 调用record_prediction() | predictions.parquet文件存在，含新记录 | P1 | 单元 |
| TC-MGR-002 | predictions.parquet按年分片 | 跨年数据 | 写入2024和2025年记录 | 生成predictions_2024.parquet和predictions_2025.parquet | P1 | 单元 |
| TC-MGR-003 | query_predictions()按类型和日期筛选 | 已有预测记录 | 调用query_predictions(type="vdot", start=..., end=...) | 返回符合条件的记录列表 | P1 | 单元 |
| TC-MGR-004 | check_and_update_actual()回填偏差 | 有预测记录+实际结果 | 调用check_and_update_actual() | 偏差字段被更新 | P1 | 单元 |
| TC-MGR-005 | 增量学习触发：新增≥50条 | 新增50+条数据 | 调用trigger_auto_update_if_needed() | 返回True，触发增量训练 | P1 | 单元 |
| TC-MGR-006 | 增量学习触发：距上次>30天 | 距上次训练>30天 | 调用trigger_auto_update_if_needed() | 返回True，触发增量训练 | P1 | 单元 |
| TC-MGR-007 | 增量学习触发：误差超阈值 | 预测误差超过阈值 | 调用trigger_auto_update_if_needed() | 返回True，触发增量训练 | P1 | 单元 |
| TC-MGR-008 | sklearn版本不兼容自动重训 | Mock版本不匹配 | 调用load_model() | 自动触发重训，不抛异常 | P1 | 单元 |

#### 4.2.4 R09: CLI命令对齐

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 类型 |
|--------|---------|---------|---------|---------|--------|------|
| TC-CLI-001 | predict model status --type all | 模型已训练 | 执行命令 | 显示所有模型状态，Rich格式化 | P1 | E2E |
| TC-CLI-002 | predict model train --type vdot | 数据充足 | 执行命令 | 显示Rich进度条，训练完成后显示结果 | P1 | E2E |
| TC-CLI-003 | predict vdot输出ML增强标注 | 数据充足 | 执行`predict vdot --days 30` | 输出"🧠 ML增强预测 \| 模型置信度: 高/中/低" | P1 | E2E |
| TC-CLI-004 | predict vdot输出参数化模型标注 | 数据中等 | 执行`predict vdot --days 30` | 输出"📊 参数化模型预测" | P1 | E2E |
| TC-CLI-005 | predict vdot输出数据不足提示 | 数据不足 | 执行`predict vdot --days 30` | 输出"当前数据量XX，建议积累更多数据" | P1 | E2E |
| TC-CLI-006 | --help三段式帮助信息 | 无 | 执行`predict model --help` | 含Description + Arguments + Examples | P1 | E2E |

### 4.3 场景级集成测试用例

| 用例ID | 用例名称 | 覆盖链路 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|---------|---------|--------|
| TC-SCN-01 | VDOT ML训练→推理→SHAP全链路 | FeatureEngine→VDOTPredictor | Mock 400+条数据 | 1.提取特征 2.训练模型 3.ML推理 4.SHAP分析 | 全链路无异常，prediction_type="ml_enhanced"，SHAP输出Top3 | P0 |
| TC-SCN-02 | 伤病LR+GBDT训练→推理→风险时间线 | FeatureEngine→InjuryPredictor | Mock 300+条数据 | 1.提取特征 2.训练LR+GBDT 3.集成推理 4.风险时间线 | 全链路无异常，risk_timeline含7/14/21天概率 | P0 |
| TC-SCN-03 | 比赛Riegel拟合→跑者分类→个人化预测 | RacePredictor | Mock 3次+比赛记录 | 1.拟合Riegel 2.分类跑者 3.个人化预测 4.配速策略 | 跑者分类非"balanced"，riegel_exponent≠1.06 | P0 |
| TC-SCN-04 | 数据不足→降级→基础预测 | DataAssessor→降级链路 | Mock <200条数据 | 1.评估数据充足度 2.降级 3.基础预测 | prediction_type="basic"，输出降级提示 | P0 |
| TC-SCN-05 | 伤病报告→标签持久化→模型训练 | report_injury→train_model | 已有伤病标签 | 1.提交伤病报告 2.检查持久化 3.用标签训练 | 标签文件存在，训练使用真实标签 | P1 |
| TC-SCN-06 | 模型回滚→预测校准 | ModelManager→Predictor | 有多个模型版本 | 1.查看版本 2.回滚 3.验证预测使用回滚版本 | 回滚后预测使用指定版本模型 | P1 |
| TC-SCN-07 | 新数据导入→缓存失效→增量学习 | data import→ModelManager | 已有模型+新数据 | 1.导入新数据 2.检查缓存失效 3.触发增量学习 | 缓存失效，增量学习触发 | P1 |
| TC-SCN-08 | BodySignalEngine→InjuryPredictor数据流 | BodySignalEngine→FeatureEngine→InjuryPredictor | v0.19数据可用 | 1.获取身体信号 2.提取伤病特征 3.伤病预测 | 身体信号数据正确传递到伤病预测 | P1 |
| TC-SCN-09 | CLI→PredictionEngine→降级链路 | CLI→PredictionEngine | 不同数据量 | 1.执行CLI命令 2.经过PredictionEngine 3.降级输出 | CLI输出与prediction_type一致 | P0 |
| TC-SCN-10 | Agent工具→PredictionEngine→超时处理 | Agent工具→PredictionEngine | Mock超时场景 | 1.Agent调用工具 2.超时 3.降级处理 | 超时后降级为基础预测，不阻塞Agent | P1 |

### 4.4 E2E测试用例

| 用例ID | 用例名称 | 用户旅程 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|---------|---------|--------|
| TC-E2E-01 | 数据充足用户ML预测全流程 | 导入→评估→预测→分析 | 18个月+数据 | 1.predict status 2.predict vdot --days 30 3.查看ML标注+SHAP | 全流程无异常，显示ML增强预测+特征重要性 | P0 |
| TC-E2E-02 | 数据不足用户降级体验 | 导入→评估→降级预测 | <200条数据 | 1.predict status 2.predict vdot --days 30 | 显示数据不足评估+降级提示+基础预测结果 | P0 |
| TC-E2E-03 | 伤病风险全流程 | 评估→预测→报告→再预测 | 18个月+数据 | 1.predict injury-risk 2.查看风险时间线 3.report_injury 4.再次预测 | 风险时间线正确，伤病报告持久化，再预测使用新标签 | P0 |
| TC-E2E-04 | 比赛预测个人化全流程 | 评估→预测→配速策略 | 3次+比赛记录 | 1.predict race --distance marathon 2.查看个人化标注+配速策略 | 显示跑者类型+个人化预测+分段配速 | P0 |
| TC-E2E-05 | 模型管理全流程 | 查看→训练→回滚 | 数据充足 | 1.predict model status 2.predict model train --type vdot 3.predict model rollback | 状态正确，训练成功，回滚生效 | P1 |
| TC-E2E-06 | 数据积累自动升级 | 不足→积累→达标→升级 | 初始数据不足 | 1.初始predict vdot(basic) 2.持续导入数据 3.再次predict vdot(ml_enhanced) | prediction_type从basic升级为ml_enhanced | P1 |

### 4.5 回归测试用例

| 用例ID | 用例名称 | 回归范围 | 操作步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|---------|--------|
| TC-REG-001 | v0.20.0降级策略不受影响 | 三层降级 | 分别测试数据充足/中等/不足场景 | 降级链路与v0.20.0行为一致 | P0 |
| TC-REG-002 | v0.20.0数据模型序列化正常 | frozen dataclass | 实例化→序列化→反序列化 | 所有字段类型正确，frozen=True | P0 |
| TC-REG-003 | v0.20.0 CLI基础命令正常 | predict status/vdot/race/injury-risk | 执行各命令 | 参数校验和输出格式与v0.20.0一致 | P0 |
| TC-REG-004 | v0.20.0 Agent工具正常 | 5个已有工具 | 调用各工具 | 返回JSON格式正确，功能正常 | P0 |
| TC-REG-005 | v0.20.0单元测试全量通过 | tests/unit/core/prediction/ | `pytest tests/unit/core/prediction/ -v` | 全部通过，无失败用例 | P0 |
| TC-REG-006 | v0.20.0集成测试全量通过 | tests/integration/module/ | `pytest tests/integration/module/ -v` | 全部通过，无失败用例 | P0 |

---

## 5. 测试用例统计

| 维度 | 数量 |
|------|------|
| **P0用例总数** | 68 |
| **P1用例总数** | 32 |
| **总用例数** | 100 |
| 单元测试用例 | 78 |
| 集成测试用例 | 10 |
| E2E测试用例 | 6 |
| 回归测试用例 | 6 |
| 性能测试用例 | 3 |
| 静态分析用例 | 1 |

### 5.1 按任务分布

| 任务 | 任务名称 | 用例数 | P0 | P1 |
|------|---------|--------|----|-----|
| R01 | AppContext依赖注入链修复 | 10 | 10 | 0 |
| R02 | FeatureEngine特征提取真实化 | 10 | 10 | 0 |
| R03 | VDOTPredictor ML训练与推理 | 12 | 12 | 0 |
| R04 | InjuryPredictor ML训练与推理 | 12 | 12 | 0 |
| R05 | RacePredictor个人化实现 | 8 | 8 | 0 |
| R06 | TrainingResponsePredictor真实化 | 4 | 0 | 4 |
| R07 | Agent工具补全 | 5 | 0 | 5 |
| R08 | ModelManager数据持久化补全 | 8 | 0 | 8 |
| R09 | CLI命令对齐 | 6 | 0 | 6 |
| SCN | 场景级集成测试 | 10 | 5 | 5 |
| E2E | 端到端测试 | 6 | 4 | 2 |
| REG | 回归测试 | 6 | 6 | 0 |

---

## 6. 测试执行计划

### 6.1 执行阶段

| 阶段 | 内容 | 依赖 | 预计工时 |
|------|------|------|---------|
| **阶段1: 准入验证** | 代码质量检查 + 覆盖率检查 + v0.20.0回归 | 开发完成 | 2小时 |
| **阶段2: 单元测试** | R01-R08全部单元测试用例执行 | 阶段1通过 | 8小时 |
| **阶段3: 集成测试** | 场景级集成测试（SCN-01~SCN-10） | 阶段2通过 | 6小时 |
| **阶段4: E2E测试** | 端到端测试（E2E-01~E2E-06） | 阶段3通过 | 4小时 |
| **阶段5: 回归验证** | v0.20.0全量回归 + 性能测试 | 阶段4通过 | 4小时 |
| **阶段6: 报告输出** | 测试报告 + Bug清单 + 质量评估 | 阶段5通过 | 2小时 |

### 6.2 执行顺序

```
准入验证 → 单元测试(R01→R02→R03/R04/R05并行→R06/R07/R08并行) → 集成测试 → E2E测试 → 回归验证 → 报告输出
```

### 6.3 关键验证命令

```bash
# 阶段1: 准入验证
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/ --ignore-missing-imports
uv run pytest tests/unit/core/prediction/ -v --tb=short

# 阶段2: 单元测试
uv run pytest tests/unit/core/base/test_context_prediction.py -v
uv run pytest tests/unit/core/prediction/test_feature_engine_integration.py -v
uv run pytest tests/unit/core/prediction/test_vdot_predictor.py -v
uv run pytest tests/unit/core/prediction/test_injury_predictor.py -v
uv run pytest tests/unit/core/prediction/test_race_predictor.py -v
uv run pytest tests/unit/core/prediction/test_model_manager.py -v
uv run pytest tests/unit/core/prediction/ -v --cov=src/core/prediction --cov-report=term-missing

# 阶段3: 集成测试
uv run pytest tests/integration/module/test_prediction_integration.py -v

# 阶段4: E2E测试
uv run pytest tests/e2e/ -v

# 阶段5: 全量回归
uv run pytest tests/ -v --tb=short
```

---

## 7. 风险与缓解

| 风险 | 等级 | 影响范围 | 缓解措施 |
|------|------|---------|---------|
| sklearn训练在少量数据下过拟合 | 🔴 高 | R03, R04 | 设置最小数据门槛(400条)、正则化、交叉验证 |
| 伤病标签数据稀少导致模型欠拟合 | 🟡 中 | R04 | 规则基线生成伪标签、强正则化、类别权重平衡 |
| SHAP计算耗时超时 | 🟡 中 | R03, R04 | 采样近似(max_evals=100)、超时降级为feature_importances_ |
| AppContext扩展影响现有功能 | 🔴 高 | R01 | 回归测试覆盖、新增属性使用get_extension/set_extension模式 |
| FeatureEngine依赖模块接口不匹配 | 🟡 中 | R02 | 先检查各模块实际API，必要时适配 |
| v0.20.0已有功能回归 | 🔴 高 | 全模块 | 每个阶段后执行回归测试，增量修改使用默认参数 |
| ML模型文件与sklearn版本不兼容 | 🟡 中 | R08 | 存储sklearn版本号，加载时校验，不兼容自动重训 |

---

## 8. 版本成功标准

| 维度 | 标准 | 测量方式 |
|------|------|----------|
| 功能完成 | P0任务100%完成 | 任务清单核对 |
| ML训练可用 | 数据充足时train_model()返回success=True | 单元测试 TC-VDOT-101 |
| ML推理可用 | 数据充足时prediction_type="ml_enhanced" | 端到端测试 TC-E2E-01 |
| 特征非零 | 有数据时FeatureEngine特征值≠0 | 单元测试 TC-FEAT-001~006 |
| 代码质量 | ruff/mypy/pytest全通过 | CI检查 |
| 无回归 | v0.20.0已有功能全部正常 | 回归测试 TC-REG-001~006 |
| P0用例通过率 | 100% | 测试报告 |
| P1用例通过率 | ≥95% | 测试报告 |
| 致命/严重Bug | 0个 | Bug清单 |

---

**后续建议**: 测试策略评审通过后，建议执行 `test-execution` 开始执行测试。