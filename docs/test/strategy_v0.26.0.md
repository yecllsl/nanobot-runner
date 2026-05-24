# v0.26.0 测试策略与规范

> **文档版本**: v1.0.0
> **适用版本**: v0.26.0
> **主题**: 底座升级 + 新特性适配
> **制定日期**: 2026-05-24
> **基线版本**: v0.25.0
> **底座版本**: nanobot-ai >=0.2.0

---

## 1. 测试概述

### 1.1 版本目标

安全升级 nanobot-ai 底座到 0.2.0，适配 GoalState/推理可见化/Model Presets 三项新特性，确保零功能回归。

### 1.2 测试范围

| 范围类型 | 说明 |
|---------|------|
| **在测范围** | nanobot-ai 0.2.0 底座兼容性、GoalState 适配、推理可见化适配、Model Presets 适配、配置向后兼容、性能回归 |
| **不在测范围** | WebUI（v0.27.0）、FallbackProvider（独立评估）、MCP Resources/Prompts（独立评估）、业务代码重构 |
| **回归范围** | v0.23-v0.25 全部已有功能（决策追踪/个性化学习/自适应进化/数字孪生/ML预测/身体信号/数据管理/CLI） |

### 1.3 测试类型分布

| 测试类型 | 占比 | 说明 |
|---------|------|------|
| 兼容性测试 | 35% | 底座 API 兼容性、配置兼容性、依赖兼容性 |
| 功能测试 | 30% | GoalState/推理可见化/Model Presets 功能验证 |
| 回归测试 | 25% | v0.25.0 全量功能回归 |
| 性能测试 | 5% | Hook 延迟、推理延迟、CLI 响应时间 |
| 代码质量 | 5% | ruff/mypy/覆盖率门禁 |

---

## 2. 准入准出门禁规则（可量化）

### 2.1 测试准入标准（开发交付 → 测试接收）

| 序号 | 准入项 | 量化标准 | 验证命令 |
|------|--------|---------|---------|
| A-01 | 单元测试基线通过 | pytest 全量通过，失败数 = 0 | `uv run pytest tests/ -x --timeout=60` |
| A-02 | 代码静态检查通过 | ruff 无新增错误 | `uv run ruff check src/` |
| A-03 | 类型检查通过 | mypy 无新增错误 | `uv run mypy src/ --ignore-missing-imports` |
| A-04 | 底座版本确认 | nanobot-ai >= 0.2.0 | `uv run python -c "import nanobot; print(nanobot.__version__)"` |
| A-05 | 依赖无冲突 | uv sync --dry-run 无冲突 | `uv sync --dry-run` |
| A-06 | 配置向后兼容 | 现有 config.json 可正常加载 | `uv run python -c "from src.core.config.manager import ConfigManager; ConfigManager(allow_default=True)"` |

**准入判定**: 6 项全部通过方可进入测试执行阶段；任一未通过退回开发工程师修复。

### 2.2 测试准出标准（测试完成 → 发布准入）

| 序号 | 准出项 | 量化标准 | 优先级 |
|------|--------|---------|--------|
| Q-01 | P0 用例通过率 | 100% | 致命 |
| Q-02 | P1 用例通过率 | >= 95% | 严重 |
| Q-03 | P2 用例通过率 | >= 80% | 一般 |
| Q-04 | 致命 bug 数 | = 0 | 致命 |
| Q-05 | 严重 bug 数 | = 0 | 严重 |
| Q-06 | 一般 bug 修复率 | >= 90% | 一般 |
| Q-07 | 代码覆盖率 | core>=80%, agents>=70%, cli>=60% | 严重 |
| Q-08 | 升级零回归 | v0.25.0 核心 CLI 命令全部可用 | 致命 |
| Q-09 | Hook 兼容性延迟 | DecisionLogHook 接入延迟 < 100ms | 严重 |
| Q-10 | 推理流式延迟 | 推理可见化增加延迟 < 50ms | 严重 |
| Q-11 | 性能退化上限 | 核心 CLI 命令响应时间退化 <= 20% | 一般 |
| Q-12 | ruff/mypy 通过 | 无新增错误 | 严重 |

**准出判定**: Q-01/Q-04/Q-08 为致命项，任一不满足禁止发布；Q-02/Q-05/Q-07/Q-09/Q-10/Q-12 为严重项，不满足需评估风险后决定；其余为一般项。

---

## 3. 测试阶段与进度计划

### 3.1 测试阶段

| 阶段 | 周期 | 目标 | 产出物 |
|------|------|------|--------|
| **S1: 底座兼容性验证** | 1d | 确认 nanobot-ai 0.2.0 API 兼容性、修复测试失败 | 兼容性测试报告 |
| **S2: 新特性功能测试** | 2d | GoalState/推理可见化/Model Presets 功能验证 | 功能测试报告 |
| **S3: 全量回归测试** | 2d | v0.23-v0.25 全功能回归 | 回归测试报告 |
| **S4: 性能与质量验收** | 1d | 性能基准、覆盖率、代码质量 | 质量验收报告 |

### 3.2 测试执行顺序

```
S1: 底座兼容性验证
  ├─ 依赖升级验证 (REQ-D-01)
  ├─ API 兼容性验证 (REQ-D-02)
  ├─ 配置兼容性验证 (REQ-D-04)
  ├─ 依赖冲突预检 (REQ-D-05)
  └─ ToolRegistry 注册验证 (REQ-D-06)

S2: 新特性功能测试
  ├─ GoalState 适配测试 (REQ-D-07)
  ├─ 推理可见化适配测试 (REQ-D-08)
  └─ Model Presets 适配测试 (REQ-D-09)

S3: 全量回归测试
  ├─ 决策追踪回归 (v0.23)
  ├─ 个性化学习回归 (v0.24)
  ├─ 自适应进化回归 (v0.25)
  ├─ 数字孪生回归 (v0.21)
  ├─ ML 预测回归 (v0.20)
  └─ 数据管理/CLI 回归 (v0.5-v0.19)

S4: 性能与质量验收
  ├─ 性能回归检查 (REQ-D-10)
  ├─ 覆盖率检查
  ├─ ruff/mypy 检查
  └─ 质量评估与发布建议
```

---

## 4. 测试用例清单

### 4.1 P0 用例（核心业务流程，必须 100% 覆盖）

#### TC-P0-01 ~ TC-P0-06: 底座依赖升级 (REQ-D-01)

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 类型 |
|--------|---------|---------|---------|---------|------|
| TC-P0-01 | pyproject.toml 版本升级验证 | 项目代码库可用 | 1. 读取 pyproject.toml<br>2. 检查 nanobot-ai 版本约束 | 版本约束为 `>=0.2.0` | 兼容性 |
| TC-P0-02 | nanobot-ai 安装验证 | uv 环境正常 | 1. 执行 `uv sync`<br>2. 检查安装日志 | nanobot-ai 0.2.0 成功安装，无报错 | 兼容性 |
| TC-P0-03 | nanobot-ai 版本号确认 | 安装完成 | 1. 执行 `uv run python -c "import nanobot; print(nanobot.__version__)"` | 输出版本号 >= 0.2.0 | 兼容性 |
| TC-P0-04 | AgentHook 接口可导入 | 安装完成 | 1. 执行 `from nanobot.agent.hook import AgentHook, AgentHookContext` | 导入成功，无 ImportError | 兼容性 |
| TC-P0-05 | 全量 pytest 基线通过 | 安装完成 | 1. 执行 `uv run pytest tests/ -x --timeout=60` | 失败数 = 0 | 回归 |
| TC-P0-06 | ruff/mypy 基线通过 | 安装完成 | 1. `uv run ruff check src/`<br>2. `uv run mypy src/ --ignore-missing-imports` | 无新增错误 | 质量 |

#### TC-P0-07 ~ TC-P0-10: API 兼容性验证 (REQ-D-02)

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 类型 |
|--------|---------|---------|---------|---------|------|
| TC-P0-07 | DecisionLogHook 继承 AgentHook | nanobot-ai 0.2.0 已安装 | 1. 检查 `DecisionLogHook(AgentHook)` 继承关系 | 是 AgentHook 的直接子类 | 兼容性 |
| TC-P0-08 | DecisionLogHook 可实例化 | 依赖注入环境就绪 | 1. 创建 EvolutionEngine mock<br>2. 实例化 DecisionLogHook | 实例化成功，无 TypeError | 兼容性 |
| TC-P0-09 | AgentHookContext mock 兼容 | 0.2.0 已安装 | 1. 创建 MagicMock(spec=AgentHookContext)<br>2. 调用 hook 各生命周期方法 | 无 AttributeError | 兼容性 |
| TC-P0-10 | Tool 基类兼容性 | 0.2.0 已安装 | 1. 检查 `BaseTool` 继承 `nanobot.Tool`<br>2. 检查 `cast_params` 方法存在 | 继承正确，方法存在 | 兼容性 |

#### TC-P0-11 ~ TC-P0-15: 测试修复 (REQ-D-03)

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 类型 |
|--------|---------|---------|---------|---------|------|
| TC-P0-11 | 因 API 变更导致的失败用例全部修复 | 基线测试已执行 | 1. 识别所有 FAILED 用例<br>2. 确认修复后重新执行 | 原失败用例全部 PASS | 回归 |
| TC-P0-12 | ruff 无新增错误 | 代码已修改 | 1. `uv run ruff check src/` | 错误数 = 0 | 质量 |
| TC-P0-13 | mypy 无新增错误 | 代码已修改 | 1. `uv run mypy src/ --ignore-missing-imports` | 错误数 = 0 | 质量 |
| TC-P0-14 | 新增测试文件可执行 | 测试已编写 | 1. `uv run pytest tests/unit/core/evolution/test_goal_state.py -v`<br>2. `uv run pytest tests/unit/core/evolution/test_reasoning.py -v`<br>3. `uv run pytest tests/unit/cli/test_model_cli.py -v` | 全部 PASS | 功能 |
| TC-P0-15 | 全量测试最终通过 | 所有修改完成 | 1. `uv run pytest tests/ --timeout=60` | 失败数 = 0 | 回归 |

#### TC-P0-16 ~ TC-P0-22: GoalState 适配 (REQ-D-07)

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 类型 |
|--------|---------|---------|---------|---------|------|
| TC-P0-16 | DecisionLog 数据模型包含 goal_state 字段 | models.py 已修改 | 1. 创建 DecisionLog 实例，传入 goal_state="全马破4"<br>2. 断言 goal_state 字段值 | goal_state == "全马破4" | 功能 |
| TC-P0-17 | DecisionLog goal_state 省略时默认为 None | models.py 已修改 | 1. 创建 DecisionLog 实例，不传入 goal_state<br>2. 断言 goal_state 值 | goal_state is None | 边界 |
| TC-P0-18 | goal_state_raw 提取 metadata 中的 goal_state | hook 已实例化 | 1. 调用 `hook.goal_state_raw({"goal_state": "半马PB130"})` | 返回 "半马PB130" | 功能 |
| TC-P0-19 | goal_state_raw 空 metadata 返回 None | hook 已实例化 | 1. 调用 `hook.goal_state_raw({})`<br>2. 调用 `hook.goal_state_raw(None)` | 均返回 None | 边界 |
| TC-P0-20 | after_iteration 读取 metadata goal_state 并写入 DecisionLog | engine+hook 就绪 | 1. mock_context.metadata = {"goal_state": "全马破4"}<br>2. finalize_content + after_iteration<br>3. 查询决策历史 | 最新 DecisionLog.goal_state == "全马破4" | 集成 |
| TC-P0-21 | finalize_content 读取 metadata goal_state | engine+hook 就绪 | 1. mock_context.metadata = {"goal_state": "目标A"}<br>2. finalize_content<br>3. 查询决策历史 | DecisionLog.goal_state == "目标A" | 集成 |
| TC-P0-22 | SOUL.md 包含 GoalState 使用指导 | SOUL.md 已更新 | 1. 读取 templates/SOUL.md<br>2. 搜索 "GoalState" 关键词 | 包含 GoalState 使用指导段落 | 文档 |

#### TC-P0-23 ~ TC-P0-29: 推理可见化适配 (REQ-D-08)

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 类型 |
|--------|---------|---------|---------|---------|------|
| TC-P0-23 | emit_reasoning 追加推理片段到缓冲区 | hook 已实例化 | 1. 调用 emit_reasoning(ctx, "片段1")<br>2. 调用 emit_reasoning(ctx, "片段2")<br>3. 检查 _reasoning_buffer | buffer == ["片段1", "片段2"] | 功能 |
| TC-P0-24 | emit_reasoning_end 标记推理完成 | hook 已实例化 | 1. 调用 emit_reasoning_end(ctx)<br>2. 检查 _reasoning_complete | _reasoning_complete is True | 功能 |
| TC-P0-25 | finalize_content 将推理写入 prediction_snapshot | engine+hook 就绪 | 1. emit_reasoning("第一步")<br>2. emit_reasoning("第二步")<br>3. emit_reasoning_end<br>4. finalize_content<br>5. 查询决策历史 | prediction_snapshot["reasoning"] == "第一步\n第二步" | 集成 |
| TC-P0-26 | 无推理时 prediction_snapshot 为 None | engine+hook 就绪 | 1. 直接 finalize_content<br>2. 查询决策历史 | prediction_snapshot is None | 边界 |
| TC-P0-27 | finalize_content 后缓冲区清空 | engine+hook 就绪 | 1. emit_reasoning("内容")<br>2. finalize_content<br>3. 检查 _reasoning_buffer | buffer == [] | 状态 |
| TC-P0-28 | before_iteration 重置推理状态 | hook 已实例化 | 1. emit_reasoning + emit_reasoning_end<br>2. before_iteration<br>3. 检查 buffer 和 complete | buffer == [], complete is False | 状态 |
| TC-P0-29 | 推理内容与最终建议逻辑一致 | 端到端场景 | 1. 触发 Agent 决策流程<br>2. 检查 DecisionLog 中 reasoning 与 recommendation_text 逻辑关联 | 推理过程支持最终建议 | 场景 |

#### TC-P0-30 ~ TC-P0-34: Model Presets 适配 (REQ-D-09)

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 类型 |
|--------|---------|---------|---------|---------|------|
| TC-P0-30 | AppConfig Schema 包含 model_presets 字段 | schema.py 已修改 | 1. 创建 AppConfig 实例，传入 model_presets<br>2. 验证字段存在 | model_presets 字段存在且类型正确 | 功能 |
| TC-P0-31 | model_presets 字段验证通过 | schema.py 已修改 | 1. AppConfig.validate({..., "model_presets": {"fast": {...}}}) | is_valid is True | 功能 |
| TC-P0-32 | ModelHandler.list_presets 返回预设列表 | handler 已实例化 | 1. mock config 包含 2 个 preset<br>2. 调用 list_presets() | 返回列表，长度=2，字段完整 | 功能 |
| TC-P0-33 | model list CLI 命令显示预设 | CLI 已注册 | 1. `runner.invoke(app, ["model", "list"])`<br>2. 检查输出 | exit_code=0，输出包含预设名称 | CLI |
| TC-P0-34 | model list 无预设时显示友好提示 | CLI 已注册 | 1. mock list_presets 返回 []<br>2. 执行命令 | 输出包含"暂无"或"无预设" | 边界 |

### 4.2 P1 用例（重要功能，高优先级覆盖）

#### TC-P1-01 ~ TC-P1-06: 配置兼容性验证 (REQ-D-04)

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 类型 |
|--------|---------|---------|---------|---------|------|
| TC-P1-01 | 现有 config.json 可被 0.2.0 Config loader 加载 | 存在旧配置 | 1. `ConfigManager(allow_default=True)` | 加载成功，无异常 | 兼容性 |
| TC-P1-02 | 旧配置无 model_presets 时正常运行 | schema 已更新 | 1. AppConfig.from_dict({"version":"0.25.0","data_dir":"/tmp"}) | 实例化成功，model_presets is None | 边界 |
| TC-P1-03 | AppConfig 未知字段被过滤 | schema 已更新 | 1. from_dict 传入含未知字段的配置 | 未知字段被忽略，不抛异常 | 边界 |
| TC-P1-04 | nanobot-ai 0.2.0 配置 Schema 变更适配 | 0.2.0 已安装 | 1. 检查 nanobot.config.schema 变更<br>2. 确认 RunFlowAgent 配置加载不受影响 | 无 breaking change | 兼容性 |
| TC-P1-05 | 配置 to_dict 包含 model_presets | schema 已更新 | 1. 创建含 model_presets 的 AppConfig<br>2. 调用 to_dict() | 字典包含 model_presets 键 | 功能 |
| TC-P1-06 | Pydantic 向后兼容验证 | 0.2.0 已安装 | 1. 确认 nanobot-ai 0.2.0 新增字段均有默认值 | 旧配置无需手动修改 | 兼容性 |

#### TC-P1-07 ~ TC-P1-09: 依赖冲突预检 (REQ-D-05)

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 类型 |
|--------|---------|---------|---------|---------|------|
| TC-P1-07 | uv sync --dry-run 无冲突 | pyproject.toml 已更新 | 1. `uv sync --dry-run` | 无依赖冲突报错 | 兼容性 |
| TC-P1-08 | pydantic 版本兼容 | 0.2.0 已安装 | 1. `uv run python -c "import pydantic; print(pydantic.__version__)"` | 版本 >= 2.0.0 | 兼容性 |
| TC-P1-09 | 间接依赖列表检查 | 0.2.0 已安装 | 1. `uv pip list` 检查关键依赖版本 | 无版本冲突 | 兼容性 |

#### TC-P1-10 ~ TC-P1-12: ToolRegistry 注册验证 (REQ-D-06)

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 类型 |
|--------|---------|---------|---------|---------|------|
| TC-P1-10 | RunnerTools 工具正常注册 | 0.2.0 已安装 | 1. `from src.agents.tools import RunnerTools`<br>2. 检查工具实例化 | 无 ImportError/TypeError | 兼容性 |
| TC-P1-11 | Evolution 工具正常注册 | 0.2.0 已安装 | 1. `from src.agents.tools_evolution import *` | 导入成功 | 兼容性 |
| TC-P1-12 | 工具 schema 格式合规 | 0.2.0 已安装 | 1. 调用 tool.to_schema()<br>2. 检查返回结构 | 符合 OpenAI function calling 规范 | 兼容性 |

#### TC-P1-13 ~ TC-P1-16: 性能回归检查 (REQ-D-10)

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 类型 |
|--------|---------|---------|---------|---------|------|
| TC-P1-13 | data import 响应时间退化 <= 20% | 有 v0.25.0 基线 | 1. 计时执行 data import | 耗时 <= 基线 * 1.2 | 性能 |
| TC-P1-14 | analysis vdot 响应时间退化 <= 20% | 有 v0.25.0 基线 | 1. 计时执行 analysis vdot | 耗时 <= 基线 * 1.2 | 性能 |
| TC-P1-15 | plan create 响应时间退化 <= 20% | 有 v0.25.0 基线 | 1. 计时执行 plan create | 耗时 <= 基线 * 1.2 | 性能 |
| TC-P1-16 | evolution status 响应时间退化 <= 20% | 有 v0.25.0 基线 | 1. 计时执行 evolution status | 耗时 <= 基线 * 1.2 | 性能 |

### 4.3 P2 用例（边缘场景，可选覆盖）

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 类型 |
|--------|---------|---------|---------|---------|------|
| TC-P2-01 | DecisionLogHook 无 TwinEngine 时 runner_state 回退 | hook 已实例化 | 1. finalize_content 不带 twin_engine | runner_state 字段值为 None | 降级 |
| TC-P2-02 | DecisionLogHook TwinEngine 获取失败时回退 | mock twin 抛异常 | 1. mock twin.get_current_snapshot 抛 RuntimeError<br>2. finalize_content | runner_state 字段值为 None，无未捕获异常 | 异常 |
| TC-P2-03 | recommendation_text 超长截断 | engine+hook 就绪 | 1. finalize_content 传入 600 字符内容 | 存储长度 <= 500 | 边界 |
| TC-P2-04 | log_decision 抛异常不影响 finalize_content 返回 | mock engine 抛异常 | 1. mock engine.log_decision 抛 RuntimeError<br>2. finalize_content | 原样返回 content，无未捕获异常 | 异常 |
| TC-P2-05 | ModelHandler 配置读取异常时返回空列表 | mock config 抛异常 | 1. mock config.load_config 抛异常<br>2. list_presets | 返回 [] 或抛出预期异常 | 异常 |
| TC-P2-06 | 多次 finalize_content 防重复记录 | engine+hook 就绪 | 1. 连续调用 finalize_content 两次 | 决策历史只新增 1 条 | 边界 |
| TC-P2-07 | emit_reasoning 传入空字符串不追加 | hook 已实例化 | 1. emit_reasoning(ctx, "") | buffer 长度不变 | 边界 |
| TC-P2-08 | EvolutionController 月度复盘包含 goal_state_active | controller 已实例化 | 1. 检查 _check_monthly_review_trigger 的 trigger_condition | 包含 goal_state_active 字段 | 功能 |
| TC-P2-09 | 全量测试最慢 20 个用例耗时记录 | 全量测试完成 | 1. `pytest --durations=20` | 记录并归档性能基线 | 性能 |
| TC-P2-10 | nanobot-ai 0.2.0 新增 Provider API 验证 | 0.2.0 已安装 | 1. 检查 `nanobot.providers.factory.make_provider` 存在 | 导入成功 | 兼容性 |

---

## 5. 场景级集成测试

### 5.1 场景: 底座升级零回归验证

```gherkin
场景: 升级后核心业务流程闭环
  给定 nanobot-ai 已从 0.1.5.post2 升级到 0.2.0
  当 执行以下核心 CLI 命令序列:
    | 命令 |
    | nanobotrun data import <sample.fit> |
    | nanobotrun analysis vdot |
    | nanobotrun plan create --goal "全马破4" --race-date 2024-12-01 |
    | nanobotrun evolution status |
    | nanobotrun model list |
  那么 所有命令 exit_code = 0
  并且 输出内容符合预期格式
  并且 无异常堆栈信息
```

### 5.2 场景: GoalState 跨对话目标追踪

```gherkin
场景: 创建计划后新对话可回忆目标
  给定 用户已创建训练计划，GoalState 为 "全马破4"
  当 Agent 在新对话中处理用户查询
  那么 DecisionLogHook 从 context.metadata 读取 goal_state
  并且 DecisionLog.goal_state == "全马破4"
  并且 Agent 回复中体现对当前目标的认知
```

### 5.3 场景: 推理可见化端到端

```gherkin
场景: Agent 推理过程被记录并可追溯
  给定 Agent 正在处理训练建议请求
  当 nanobot-ai 0.2.0 触发推理回调
  那么 DecisionLogHook.emit_reasoning() 被调用
  并且 推理片段追加到 _reasoning_buffer
  并且 finalize_content 后 prediction_snapshot 包含完整推理链
  并且 推理内容与支持建议逻辑一致
```

---

## 6. 性能测试策略

### 6.1 性能基线

| 指标 | v0.25.0 基线 | v0.26.0 上限 | 测试方法 |
|------|-------------|-------------|---------|
| DecisionLogHook 接入延迟 | < 100ms | < 100ms | 在 test_decision_log_hook.py 中计时 before_iteration/finalize_content |
| 推理可见化增加延迟 | 0ms | < 50ms | 对比开启/关闭 emit_reasoning 的 finalize_content 耗时 |
| data import | 记录基线 | <= 基线*1.2 | 使用 sample FIT 文件计时 |
| analysis vdot | 记录基线 | <= 基线*1.2 | CLI 命令计时 |
| plan create | 记录基线 | <= 基线*1.2 | CLI 命令计时 |
| evolution status | 记录基线 | <= 基线*1.2 | CLI 命令计时 |
| pytest 全量耗时 | 记录基线 | <= 基线*1.2 | `pytest tests/ --timeout=60` 总耗时 |

### 6.2 性能测试命令

```bash
# Hook 延迟微基准
uv run pytest tests/unit/core/evolution/test_decision_log_hook.py -v --durations=10

# 推理延迟对比
uv run pytest tests/unit/core/evolution/test_reasoning.py -v --durations=10

# CLI 响应计时 (PowerShell)
Measure-Command { uv run nanobotrun analysis vdot }
Measure-Command { uv run nanobotrun evolution status }
Measure-Command { uv run nanobotrun model list }

# 全量测试耗时
Measure-Command { uv run pytest tests/ --timeout=60 }
```

---

## 7. 覆盖率要求

### 7.1 模块覆盖率门禁

| 模块 | 最低覆盖率 | 测试重点 |
|------|-----------|---------|
| `src/core/evolution/` | >= 85% | DecisionLogHook、models、engine |
| `src/core/config/` | >= 80% | schema、manager |
| `src/agents/` | >= 70% | tools、tools_evolution |
| `src/cli/` | >= 60% | commands、handlers |
| `src/core/` 整体 | >= 80% | 全部子模块 |

### 7.2 覆盖率检查命令

```bash
# 全量覆盖率
uv run pytest tests/unit/ --cov=src --cov-report=term-missing --cov-fail-under=80

# 按模块检查
uv run pytest tests/unit/core/evolution/ --cov=src.core.evolution --cov-report=term-missing
uv run pytest tests/unit/core/config/ --cov=src.core.config --cov-report=term-missing
uv run pytest tests/unit/cli/ --cov=src.cli --cov-report=term-missing
uv run pytest tests/unit/agents/ --cov=src.agents --cov-report=term-missing
```

---

## 8. Bug 管理规范

### 8.1 严重等级定义

| 等级 | 定义 | 示例 | 修复时限 |
|------|------|------|---------|
| 致命 | 阻断核心业务流程，无法继续测试 | pytest 全量失败、CLI 核心命令崩溃、数据损坏 | 4h |
| 严重 | 核心功能异常，影响主流程使用 | DecisionLogHook 不兼容、GoalState 未写入、推理丢失 | 1d |
| 一般 | 非核心功能异常，不影响主流程 | model list 输出格式异常、边界条件处理不完善 | 3d |
| 优化 | 体验/规范类问题，不影响功能 | 提示文案优化、日志级别调整 | 可选 |

### 8.2 Bug 跟踪流程

```
发现 → 记录到 /docs/test/项目bug清单.md → 提交开发工程师 → 修复 → 回归测试 → 更新状态
```

### 8.3 Bug 清单模板字段

- bug ID、所属模块、严重等级、bug 标题
- 复现步骤、实际结果、预期结果
- 根因分析、修复建议、出现版本
- 优先级、测试人员、创建时间、状态

---

## 9. 测试环境要求

### 9.1 环境配置

| 项 | 要求 |
|----|------|
| OS | Windows 10/11 或 macOS 13+ |
| Python | 3.11+ |
| 包管理 | uv (latest) |
| 底座 | nanobot-ai >= 0.2.0 |
| 测试框架 | pytest + pytest-cov + pytest-timeout |

### 9.2 测试数据

- 使用 `tests/data/fixtures/` 下样本 FIT 文件
- 严禁使用真实用户 GPS/心率/个人信息
- Mock 外部 API（飞书、LLM）

---

## 10. 风险与缓解

| 风险 | 等级 | 影响 | 缓解措施 | 测试应对 |
|------|------|------|---------|---------|
| nanobot-ai 0.2.0 API breaking change | 低 | 升级后功能异常 | 0.2.0 对 AgentHook 纯增量扩展 | 全量兼容性测试覆盖 |
| 间接依赖冲突 | 中 | 安装失败或运行时异常 | uv sync --dry-run 预检 | 依赖冲突预检用例 |
| config.json Schema 不兼容 | 低 | 旧配置加载失败 | Pydantic 向后兼容，新增字段有默认值 | 配置兼容性验证 |
| 推理可见化增加延迟 | 低 | Agent 响应变慢 | 缓冲区操作 O(1) | 性能回归检查 |
| GoalState 跨对话失效 | 中 | 新对话无法回忆目标 | metadata 读取 + SOUL.md 指导 | 场景级集成测试 |
| 性能退化超阈值 | 低 | 用户体验下降 | 基准测试对比 | 性能回归检查 |

---

## 11. 交付物清单

| 交付物 | 路径 | 说明 |
|--------|------|------|
| 测试策略文档 | `docs/test/strategy_v0.26.0.md` | 本文档 |
| 全量测试用例清单 | `docs/test/cases_v0.26.0.md` | 用例详细设计（如需要可单独输出） |
| 兼容性测试报告 | `docs/test/report_compatibility_v0.26.0.md` | S1 阶段产出 |
| 功能测试报告 | `docs/test/report_feature_v0.26.0.md` | S2 阶段产出 |
| 回归测试报告 | `docs/test/report_regression_v0.26.0.md` | S3 阶段产出 |
| 质量验收报告 | `docs/test/report_acceptance_v0.26.0.md` | S4 阶段产出 |
| 项目 bug 清单 | `docs/test/项目bug清单_v0.26.0.md` | 实时更新 |
| 性能基准数据 | `docs/test/performance_baseline_v0.26.0.md` | 性能测试结果 |

---

## 12. 测试执行检查表

### 12.1 每日检查项

- [ ] 全量 pytest 通过（失败数 = 0）
- [ ] 新增 bug 已记录并同步开发工程师
- [ ] 致命/严重 bug 修复进度已跟进
- [ ] 覆盖率未跌破门禁线

### 12.2 阶段出口检查项

**S1 出口**:
- [ ] TC-P0-01 ~ TC-P0-06 全部 PASS
- [ ] TC-P0-07 ~ TC-P0-10 全部 PASS
- [ ] TC-P1-07 ~ TC-P1-09 全部 PASS
- [ ] 无致命 bug

**S2 出口**:
- [ ] TC-P0-16 ~ TC-P0-34 全部 PASS
- [ ] TC-P1-01 ~ TC-P1-06 全部 PASS
- [ ] TC-P1-10 ~ TC-P1-12 全部 PASS
- [ ] 场景级集成测试（5.1~5.3）全部 PASS

**S3 出口**:
- [ ] v0.23-v0.25 核心功能回归用例全部 PASS
- [ ] 全量 pytest 失败数 = 0

**S4 出口**:
- [ ] TC-P1-13 ~ TC-P1-16 性能退化 <= 20%
- [ ] 覆盖率满足门禁（core>=80%, agents>=70%, cli>=60%）
- [ ] ruff/mypy 无新增错误
- [ ] 准出标准 Q-01~Q-12 全部满足

---

*文档版本: v1.0.0 | 更新日期: 2026-05-24 | 测试工程师制定*
