# v0.29.0 Bug清单

**版本**: v0.29.0  
**分支**: feature/v0.29.0  
**更新日期**: 2026-06-09  

---

## Bug列表

| Bug ID | 模块 | 严重等级 | 标题 | 状态 | 创建时间 | 修复时间 |
|--------|------|---------|------|------|---------|---------|
| BUG-001 | 集成测试 | 一般 | 集成测试路径前缀错误导致认证测试失败 | 已闭环 | 2026-06-09 | 2026-06-09 |
| BUG-002 | WebUI路由 | 一般 | evolution路由方法名和属性访问错误（类型检查发现） | 已闭环 | 2026-06-09 | 2026-06-09 |

---

## Bug详情

### BUG-001: 集成测试路径前缀错误

| 字段 | 内容 |
|------|------|
| **Bug ID** | BUG-001 |
| **所属模块** | 集成测试 |
| **严重等级** | 一般（测试代码Bug，不影响业务代码） |
| **Bug标题** | 集成测试路径前缀错误导致认证测试失败 |
| **前置条件** | 运行 `pytest tests/integration/module/test_webui_v0290_routes.py` |
| **复现步骤** | 1. 执行集成测试 `TestAuthEnforcement` 类下的3个测试用例<br>2. 测试访问 `/api/webui/plan/list` 等路径<br>3. 期望返回401（认证拦截），实际返回200 |
| **实际结果** | 返回200（SPA fallback路由捕获请求返回index.html） |
| **预期结果** | 返回401（认证中间件拦截未认证请求） |
| **根因分析** | 测试用例使用了错误的路径前缀 `/api/webui/`，而 [app.py](file:///d:/yecll/Documents/LocalCode/RunFlowAgent.worktrees/feature-v0.29.0/src/core/webui/app.py#L109-L111) 中实际注册的前缀是 `/api/`。错误路径被SPA fallback路由 `/{path:path}` 捕获 |
| **修复建议** | 将测试文件中所有 `/api/webui/` 前缀修正为 `/api/` |
| **修复文件** | [test_webui_v0290_routes.py](file:///d:/yecll/Documents/LocalCode/RunFlowAgent.worktrees/feature-v0.29.0/tests/integration/module/test_webui_v0290_routes.py) |
| **修复方式** | 修改10处路径引用（TestRouteRegistration 7处 + TestAuthEnforcement 3处） |
| **验证结果** | 回归测试12 passed |
| **状态** | 已闭环 |

---

### BUG-002: evolution路由方法名和属性访问错误

| 字段 | 内容 |
|------|------|
| **Bug ID** | BUG-002 |
| **所属模块** | WebUI路由 - evolution |
| **严重等级** | 一般（运行时不会报错，但类型检查不通过） |
| **Bug标题** | evolution路由方法名和属性访问错误（类型检查发现） |
| **前置条件** | 运行 `mypy src/core/webui/routes/evolution.py --ignore-missing-imports` |
| **复现步骤** | 1. 执行类型检查<br>2. 发现2个attr-defined错误 |
| **实际结果** | mypy报告2个错误：<br>- `"EvolutionEngine" has no attribute "check_triggers"`<br>- `"EvolutionEngine" has no attribute "_store"` |
| **预期结果** | 类型检查0 errors |
| **根因分析** | 1. [evolution.py:42](file:///d:/yecll/Documents/LocalCode/RunFlowAgent.worktrees/feature-v0.29.0/src/core/webui/routes/evolution.py#L42) 调用了 `check_triggers()`，但 [evolution_engine.py:268](file:///d:/yecll/Documents/LocalCode/RunFlowAgent.worktrees/feature-v0.29.0/src/core/evolution/evolution_engine.py#L268) 实际方法名为 `check_evolution_triggers()`<br>2. [evolution.py:160](file:///d:/yecll/Documents/LocalCode/RunFlowAgent.worktrees/feature-v0.29.0/src/core/webui/routes/evolution.py#L160) 直接访问 `context.evolution_engine._store`，但 EvolutionEngine 没有 `_store` 属性，该属性属于 EvolutionReporter |
| **修复建议** | 1. 修正方法调用名<br>2. 在 EvolutionEngine 中新增公共方法封装 `_store` 访问 |
| **修复文件** | [evolution.py](file:///d:/yecll/Documents/LocalCode/RunFlowAgent.worktrees/feature-v0.29.0/src/core/webui/routes/evolution.py)、[evolution_engine.py](file:///d:/yecll/Documents/LocalCode/RunFlowAgent.worktrees/feature-v0.29.0/src/core/evolution/evolution_engine.py#L312-L336) |
| **修复方式** | 1. `check_triggers()` → `check_evolution_triggers()`<br>2. 新增 `get_available_report_months()` 方法，委托给 `_evolution_reporter._store` |
| **验证结果** | mypy 0 errors，回归测试47 passed |
| **状态** | 已闭环 |

---

## Bug统计

### 按严重等级

| 严重等级 | 数量 | 已闭环 | 修复中 | 待修复 |
|---------|------|--------|--------|--------|
| 致命 | 0 | 0 | 0 | 0 |
| 严重 | 0 | 0 | 0 | 0 |
| 一般 | 2 | 2 | 0 | 0 |
| 优化 | 0 | 0 | 0 | 0 |

### 按模块

| 模块 | 数量 |
|------|------|
| 集成测试 | 1 |
| WebUI路由 | 1 |

### 修复率

| 指标 | 数值 |
|------|------|
| 总Bug数 | 2 |
| 已修复 | 2 |
| 修复率 | 100% |
