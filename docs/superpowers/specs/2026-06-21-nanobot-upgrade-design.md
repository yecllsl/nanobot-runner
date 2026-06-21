# nanobot-ai v0.2.0 → v0.2.1 升级设计文档

> **版本**: v1.0 | **日期**: 2026-06-21
> **项目**: RunFlowAgent v0.30.0 | **基线**: v0.29.0

---

## 1. 概述

### 1.1 升级目标

将 RunFlowAgent 的 nanobot-ai 底座从 v0.2.0 升级到 v0.2.1（"The Workbench Release"），修复7项破坏性变更，适配4项新特性。

### 1.2 升级范围

- **破坏性变更修复**：7项（2项P0阻塞 + 5项P1签名适配）
- **新特性适配**：4项（WebUI工作台、模型上下文控制、CLI Apps+MCP扩展、Thought/Response时间线）
- **monkey-patch**：保留现状（v0.2.1范围内目标未变更）

### 1.3 实施策略

**渐进式升级**：P0修复→P1修复→新特性适配→验证收尾，每阶段独立验证。

---

## 2. 破坏性变更修复

### 2.1 依赖升级

**文件**: `pyproject.toml`

| 依赖 | 当前约束 | 升级后约束 | 原因 |
|------|---------|-----------|------|
| nanobot-ai | `>=0.2.0` | `>=0.2.1` | 目标版本 |
| questionary | `>=1.10.0` | `>=2.0.0,<3.0.0` | 对齐nanobot-ai 0.2.1 |
| rich | `>=13.0.0` | `>=14.0.0,<15.0.0` | 对齐nanobot-ai 0.2.1 |
| dulwich | `>=0.21.0` | `>=0.22.0,<1.0.0` | 对齐nanobot-ai 0.2.1 |
| pydantic-settings | `>=2.0.0` | `>=2.12.0,<3.0.0` | 对齐nanobot-ai 0.2.1 |

执行：`uv lock --upgrade-package nanobot-ai`，确认 uv.lock 锁定 0.2.1。

### 2.2 P0-2: Import路径修复

**文件**: `src/core/provider_adapter.py:36-40`

```python
# 修改前
from nanobot.channels.websocket import (
    WebSocketChannel,
    _http_error,
    _parse_request_path,
)

# 修改后
from nanobot.channels.websocket import WebSocketChannel
from nanobot.webui.http_utils import (
    http_error as _http_error,
    parse_request_path as _parse_request_path,
)
```

**根因**: v0.2.1 将 `_http_error`/`_parse_request_path` 从 `nanobot.channels.websocket` 迁移到 `nanobot.webui.http_utils`，并重命名为 `http_error`/`parse_request_path`。

### 2.3 P0-1: Heartbeat→Cron重构

**文件**: `src/cli/commands/gateway.py:323,442-450,539,568`

**修改内容**:

1. 移除 `from nanobot.heartbeat.service import HeartbeatService` 导入
2. 将 HeartbeatService 实例化替换为 CronService 心跳任务注册
3. 参考上游 `nanobot/cli/commands.py:914` 的 `_register_heartbeat_job` 实现

```python
# 修改前
from nanobot.heartbeat.service import HeartbeatService
# ...
heartbeat = HeartbeatService(
    workspace=workspace,
    provider=provider,
    model=agent.model,
    on_execute=on_heartbeat_execute,
    on_notify=on_heartbeat_notify,
    interval_s=hb_interval_s,
    enabled=hb_enabled,
)
# ...
await heartbeat.start()
# ...
heartbeat.stop()

# 修改后
from nanobot.cron.service import CronService
from nanobot.cron.types import CronSchedule, CronJob
# ...
# 注册心跳Cron任务（替代HeartbeatService）
heartbeat_cron = CronService(workspace=workspace)
heartbeat_interval_minutes = max(1, hb_interval_s // 60)  # Cron最小粒度为分钟
heartbeat_schedule = CronSchedule(
    cron=f"*/{heartbeat_interval_minutes} * * * *",
    enabled=hb_enabled,
)
heartbeat_cron.register(
    CronJob(
        name="heartbeat",
        schedule=heartbeat_schedule,
        callback=_heartbeat_cron_callback,  # 封装原有 on_execute/on_notify 逻辑
    )
)
# ...
await heartbeat_cron.start()
# ...
await heartbeat_cron.stop()
```

**心跳回调适配**: 将 `on_heartbeat_execute`/`on_heartbeat_notify` 封装为 CronJob 回调函数。

### 2.4 P1-3: Hook注册调整

**文件**: `src/cli/commands/gateway.py:427-428`

```python
# 修改前（静默失效：hasattr返回False）
if streaming_hook and hasattr(agent, "hooks"):
    agent.hooks.register(streaming_hook)

# 修改后
if streaming_hook:
    agent._extra_hooks.append(streaming_hook)
```

**注意**: `_extra_hooks` 是 v0.2.1 的私有属性。备选方案是通过 AgentLoop 构造函数 `hooks=` 参数传入，但需在实例化时已知所有 Hook，与当前延迟注册模式不兼容。本次采用 `_extra_hooks.append`，加注释标记。

### 2.5 P1-4: on_stream_end签名适配

**文件**: `src/core/transparency/streaming_hook.py:91`

```python
# 修改前
async def on_stream_end(self, context: AgentHookContext) -> None:

# 修改后
async def on_stream_end(self, context: AgentHookContext, *, resuming: bool = False) -> None:
```

v0.2.1 新增 `resuming: bool` 关键字参数，表示是否从上次中断处恢复。默认值 `False` 保持向后兼容。

### 2.6 P1-5: after_iteration同步→异步

**文件**: `src/core/evolution/decision_log_hook.py:177`

```python
# 修改前
def after_iteration(self, context: Any) -> None:

# 修改后
async def after_iteration(self, context: Any) -> None:
```

**同步影响**: `after_iteration` 内部调用了 `self._evolution_engine.check_evolution_triggers()`，当前在 daemon 线程中执行。改为 async 后，需确保该调用在异步上下文中正确执行。

**其他Hook同步修改**: 以下Hook的 `after_iteration` 也需同步改为 async：
- `src/core/transparency/error_handling_hook.py:45` — ErrorHandlingHook.after_iteration
- `src/core/transparency/progress_hook.py:50` — ProgressDisplayHook.after_iteration
- `src/core/transparency/hook_integration.py:122` — ObservabilityHook.after_iteration

### 2.7 P1-6: emit_reasoning签名适配

**文件**: `src/core/evolution/decision_log_hook.py:228`

```python
# 修改前
def emit_reasoning(self, context: AgentHookContext, reasoning_text: str) -> None:

# 修改后
async def emit_reasoning(self, reasoning_text: str) -> None:
```

变更：移除 `context` 参数 + 改为 async。`context` 在原实现中未使用，移除无影响。

### 2.8 P1-7: emit_reasoning_end签名适配

**文件**: `src/core/evolution/decision_log_hook.py:241`

```python
# 修改前
def emit_reasoning_end(self, context: AgentHookContext) -> None:

# 修改后
async def emit_reasoning_end(self) -> None:
```

变更：移除 `context` 参数 + 改为 async。`context` 在原实现中未使用，移除无影响。

---

## 3. v0.2.1新特性适配

### 3.1 模型和上下文控制

**价值**: 运行时灵活切换模型和上下文窗口，适配不同场景。

**适配方案**:

1. **配置注入**: 在 `RunnerProviderAdapter._build_nanobot_config_from_runner()` 中注入 `model_presets` 配置
2. **WebUI管理**: 设置中心页面增加模型预设管理API（`/api/settings/model-presets`）
3. **运行时切换**: AgentLoop 支持通过 `model_preset` 参数切换模型

**修改文件**:
- `src/core/provider_adapter.py` — 注入 model_presets 到 nanobot Config
- `src/core/webui/routes/settings.py` — 新增预设管理API端点

### 3.2 CLI Apps + MCP扩展

**价值**: 新增 `run_cli_app` 工具和MCP预设管理，扩展Agent能力边界。

**适配方案**:

1. **配置注入**: 在 `_build_nanobot_config_from_runner()` 中注入 `cli_apps` 和 `mcp_presets` 配置
2. **MCP预设**: 支持从 `config.json` 读取 MCP 服务器预设列表
3. **CLI Apps**: 启用 nanobot-ai 内置的 `run_cli_app` 工具

**修改文件**:
- `src/core/provider_adapter.py` — 注入 cli_apps/mcp_presets 配置

### 3.3 Thought/Response时间线

**价值**: 推理过程与响应分离展示，增强可观测性。

**适配方案**:

1. **后端**: `emit_reasoning`/`emit_reasoning_end` 已在 P1-6/7 修复中适配
2. **WebSocket推送**: 推理片段通过 `OutboundMessage.metadata` 的 `reasoning_delta` 字段推送到前端
3. **StreamingHook扩展**: 在 `on_stream` 中区分普通流式输出和推理片段，分别推送

**修改文件**:
- `src/core/transparency/streaming_hook.py` — 推理片段通过bus推送
- WebUI前端 — 新增推理时间线组件

### 3.4 WebUI工作台转型

**价值**: 从聊天界面升级为日常agent工作台，用户体验显著提升。

**适配方案**:

1. **前端适配**: 适配 nanobot-ai 0.2.1 的新 WebUI 布局（工作台模式）
2. **路由兼容**: 确保自定义 WebUI 路由（evolution/plan/settings）与新布局兼容
3. **静态文件**: monkey-patch 的 `_default_webui_dist` 继续生效

**修改文件**:
- WebUI前端 — 适配工作台布局
- `src/core/webui/app.py` — 路由兼容性验证

---

## 4. 验证策略

### 4.1 渐进式验证

| 阶段 | 验证内容 | 验证方式 |
|------|---------|---------|
| 阶段1（P0修复后） | 系统可启动 | `uv run nanobotrun gateway start --webui`，确认无ImportError |
| 阶段2（P1修复后） | Hook功能正常 | 流式输出/推理可见化/决策日志/错误处理 |
| 阶段3（新特性后） | 新特性功能 | 模型切换/MCP预设/时间线/工作台 |
| 阶段4（全量回归） | 无回归 | `uv run pytest tests/unit/` + `tests/e2e/` |

### 4.2 回滚预案

- 保留 v0.2.0 的 `uv.lock` 快照
- 每阶段在独立 commit 中完成，可逐阶段回滚
- 遇阻时 `git checkout` 回退到上一个验证通过的 commit

### 4.3 风险缓解

| 风险 | 缓解措施 |
|------|---------|
| CronService心跳实现差异 | 参考上游 `_register_heartbeat_job`，启动后立即验证 |
| `_extra_hooks` 为私有属性 | 加注释标记；备选方案通过构造函数 `hooks=` 参数传入 |
| questionary 2.x API不兼容 | 升级前审查所有 questionary 调用点 |
| WebUI前端与v0.2.1不兼容 | 优先使用项目自定义前端，回退到nanobot内置 |

---

## 5. 修改文件清单

| 文件 | 修改类型 | 优先级 |
|------|---------|--------|
| `pyproject.toml` | 依赖版本约束更新 | P0 |
| `src/core/provider_adapter.py` | P0-2 Import路径修复 + 新特性配置注入 | P0 |
| `src/cli/commands/gateway.py` | P0-1 Heartbeat重构 + P1-3 Hook注册 | P0 |
| `src/core/transparency/streaming_hook.py` | P1-4 签名适配 + 推理推送 | P1 |
| `src/core/evolution/decision_log_hook.py` | P1-5/6/7 签名适配 | P1 |
| `src/core/transparency/error_handling_hook.py` | P1-5 after_iteration改async | P1 |
| `src/core/transparency/progress_hook.py` | P1-5 after_iteration改async | P1 |
| `src/core/transparency/hook_integration.py` | P1-5 after_iteration改async | P1 |
| `src/core/webui/routes/settings.py` | 模型预设管理API | P2 |
| `src/core/webui/app.py` | 路由兼容性验证 | P2 |
| WebUI前端 | 工作台布局适配 + 推理时间线组件 | P2 |

---

## 6. 参考信息

- **综合评审报告**: `docs/architecture/upgrade_feasibility_report_comprehensive.md`
- **GLM-5.1报告**: `docs/architecture/upgrade_feasibility_report_GLM5.1.md`
- **GLM-5.2报告**: `docs/architecture/upgrade_feasibility_report_GLM5.2.md`
- **Qwen-3.7报告**: `docs/architecture/upgrade_feasibility_report_qwen3.7.md`
- **上游参考**: `nanobot/cli/commands.py:914` — `_register_heartbeat_job`
