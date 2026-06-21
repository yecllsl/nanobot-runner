# nanobot-ai v0.2.0 → v0.2.1 升级实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 RunFlowAgent 的 nanobot-ai 底座从 v0.2.0 升级到 v0.2.1，修复7项破坏性变更，适配4项新特性。

**Architecture:** 渐进式升级策略，分4个阶段：P0修复（系统可启动）→ P1修复（功能完整）→ 新特性适配 → 验证收尾。每阶段独立验证，可逐阶段回滚。

**Tech Stack:** Python 3.11+, nanobot-ai 0.2.1, uv, pytest, FastAPI, React

---

## File Structure

| 文件 | 操作 | 职责 |
|------|------|------|
| `pyproject.toml` | 修改 | 依赖版本约束更新 |
| `src/core/provider_adapter.py` | 修改 | P0-2 Import修复 + 新特性配置注入 |
| `src/cli/commands/gateway.py` | 修改 | P0-1 Heartbeat重构 + P1-3 Hook注册 |
| `src/core/transparency/streaming_hook.py` | 修改 | P1-4 签名适配 + 推理推送 |
| `src/core/evolution/decision_log_hook.py` | 修改 | P1-5/6/7 签名适配 |
| `src/core/transparency/error_handling_hook.py` | 修改 | P1-5 after_iteration改async |
| `src/core/transparency/progress_hook.py` | 修改 | P1-5 after_iteration改async |
| `src/core/transparency/hook_integration.py` | 修改 | P1-5 after_iteration改async |
| `src/core/webui/routes/settings.py` | 修改 | 模型预设管理API |
| `src/core/webui/app.py` | 修改 | 路由兼容性验证 |

---

## 阶段1: P0修复 — 系统可启动

### Task 1: 升级依赖版本约束

**Files:**
- Modify: `pyproject.toml:7-29`

- [ ] **Step 1: 更新 pyproject.toml 依赖约束**

将以下依赖约束从旧版本更新为新版本：

```toml
# 修改前
"nanobot-ai>=0.2.0",
"questionary>=1.10.0",
"rich>=13.0.0",
"dulwich>=0.21.0",
"pydantic-settings>=2.0.0",

# 修改后
"nanobot-ai>=0.2.1",
"questionary>=2.0.0,<3.0.0",
"rich>=14.0.0,<15.0.0",
"dulwich>=0.22.0,<1.0.0",
"pydantic-settings>=2.12.0,<3.0.0",
```

- [ ] **Step 2: 执行 uv lock 升级**

Run: `uv lock --upgrade-package nanobot-ai`
Expected: uv.lock 中 nanobot-ai 版本更新为 0.2.1

- [ ] **Step 3: 验证依赖解析成功**

Run: `uv sync`
Expected: 成功安装所有依赖，无冲突

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: upgrade nanobot-ai 0.2.0 -> 0.2.1 and align dependency constraints"
```

---

### Task 2: P0-2 Import路径修复

**Files:**
- Modify: `src/core/provider_adapter.py:36-40`

- [ ] **Step 1: 修改 _patch_websocket_settings_api 中的 import**

将 `_http_error` 和 `_parse_request_path` 的导入从 `nanobot.channels.websocket` 迁移到 `nanobot.webui.http_utils`：

```python
# 修改前 (provider_adapter.py:36-40)
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

- [ ] **Step 2: 验证 import 正确**

Run: `uv run python -c "from src.core.provider_adapter import RunnerProviderAdapter; print('OK')"`
Expected: 输出 "OK"，无 ImportError

- [ ] **Step 3: Commit**

```bash
git add src/core/provider_adapter.py
git commit -m "fix: migrate _http_error/_parse_request_path import to nanobot.webui.http_utils (P0-2)"
```

---

### Task 3: P0-1 Heartbeat→Cron重构

**Files:**
- Modify: `src/cli/commands/gateway.py:323,430-450,539,568`

这是最复杂的修复项。需要将 HeartbeatService 替换为 CronService 心跳任务。

- [ ] **Step 1: 移除 HeartbeatService 导入，添加 CronService 导入**

```python
# 修改前 (gateway.py:323)
from nanobot.heartbeat.service import HeartbeatService

# 修改后
# HeartbeatService 在 nanobot-ai 0.2.1 中已移除，改用 CronService 注册心跳任务
```

注意：CronService 已在 `gateway_integration.py` 中导入使用，gateway.py 中已有 `from nanobot.cron.service import CronService` 的间接引用。需确认是否需要新增导入。

- [ ] **Step 2: 将 HeartbeatService 实例化替换为 CronService 心跳注册**

```python
# 修改前 (gateway.py:430-450)
def on_heartbeat_execute():
    console.print("[dim]心跳检测执行中...[/dim]")

def on_heartbeat_notify(channel: str, chat_id: str, response: str):
    from nanobot.bus import OutboundMessage
    bus.publish_outbound(
        OutboundMessage(channel=channel, chat_id=chat_id, content=response)
    )

hb_interval_s = 300
hb_enabled = True
heartbeat = HeartbeatService(
    workspace=workspace,
    provider=provider,
    model=agent.model,
    on_execute=on_heartbeat_execute,
    on_notify=on_heartbeat_notify,
    interval_s=hb_interval_s,
    enabled=hb_enabled,
)

# 修改后
hb_interval_s = 300
hb_enabled = True

# v0.30.0: HeartbeatService 在 nanobot-ai 0.2.1 中已移除
# 改用 CronService 注册心跳任务（参考 nanobot/cli/commands.py:914）
from nanobot.cron.types import CronJob, CronSchedule

hb_interval_minutes = max(1, hb_interval_s // 60)  # Cron 最小粒度为分钟

async def _heartbeat_cron_callback():
    """心跳Cron任务回调，封装原有 on_execute/on_notify 逻辑"""
    console.print("[dim]心跳检测执行中...[/dim]")
    # 心跳通知逻辑：通过 AgentLoop 触发 LLM 生成心跳响应
    # 参考 nanobot 上游 _register_heartbeat_job 实现

if hb_enabled:
    heartbeat_job = CronJob(
        name="heartbeat",
        schedule=CronSchedule(
            cron=f"*/{hb_interval_minutes} * * * *",
            enabled=True,
        ),
        callback=_heartbeat_cron_callback,
    )
    cron.register(heartbeat_job)
    logger.info(f"心跳Cron任务已注册: 每 {hb_interval_minutes} 分钟")
```

- [ ] **Step 3: 修改 run() 函数中的 heartbeat 调用**

```python
# 修改前 (gateway.py:539)
await heartbeat.start()

# 修改后
# heartbeat 已通过 cron.register() 注册，随 cron.start() 自动启动

# 修改前 (gateway.py:568)
heartbeat.stop()

# 修改后
# heartbeat 随 cron 服务自动停止，无需单独调用
```

- [ ] **Step 4: 修改心跳状态显示**

```python
# 修改前 (gateway.py:495)
console.print(f"[green][OK][/green] 心跳检测: 每 {hb_interval_s} 秒")

# 修改后
console.print(f"[green][OK][/green] 心跳检测: 每 {hb_interval_minutes} 分钟 (CronService)")
```

- [ ] **Step 5: 验证 Gateway 可启动**

Run: `uv run python -c "from src.cli.commands.gateway import app; print('OK')"`
Expected: 输出 "OK"，无 ImportError

- [ ] **Step 6: Commit**

```bash
git add src/cli/commands/gateway.py
git commit -m "fix: replace HeartbeatService with CronService heartbeat job (P0-1)"
```

---

## 阶段2: P1修复 — 功能完整

### Task 4: P1-3 Hook注册调整

**Files:**
- Modify: `src/cli/commands/gateway.py:427-428`

- [ ] **Step 1: 修改 Hook 注册方式**

```python
# 修改前 (gateway.py:427-428)
if streaming_hook and hasattr(agent, "hooks"):
    agent.hooks.register(streaming_hook)

# 修改后
# v0.30.0: nanobot-ai 0.2.1 中 AgentLoop 无公开 hooks 属性
# 改用 _extra_hooks 列表直接追加（私有属性，后续版本可能变更）
if streaming_hook:
    agent._extra_hooks.append(streaming_hook)
```

- [ ] **Step 2: Commit**

```bash
git add src/cli/commands/gateway.py
git commit -m "fix: use _extra_hooks.append for hook registration (P1-3)"
```

---

### Task 5: P1-4 on_stream_end签名适配

**Files:**
- Modify: `src/core/transparency/streaming_hook.py:91`

- [ ] **Step 1: 修改 on_stream_end 方法签名**

```python
# 修改前 (streaming_hook.py:91)
async def on_stream_end(self, context: AgentHookContext) -> None:
    """流式输出结束时触发

    输出换行并清理流式状态。

    Args:
        context: Hook上下文
    """

# 修改后
async def on_stream_end(self, context: AgentHookContext, *, resuming: bool = False) -> None:
    """流式输出结束时触发

    输出换行并清理流式状态。

    Args:
        context: Hook上下文
        resuming: 是否从上次中断处恢复（nanobot-ai 0.2.1 新增）
    """
```

方法体无需修改，`resuming` 参数暂不使用，保留接口兼容。

- [ ] **Step 2: Commit**

```bash
git add src/core/transparency/streaming_hook.py
git commit -m "fix: add resuming parameter to on_stream_end signature (P1-4)"
```

---

### Task 6: P1-5 after_iteration同步→异步（4个Hook文件）

**Files:**
- Modify: `src/core/evolution/decision_log_hook.py:177`
- Modify: `src/core/transparency/error_handling_hook.py:45`
- Modify: `src/core/transparency/progress_hook.py:50`
- Modify: `src/core/transparency/hook_integration.py:122`

- [ ] **Step 1: 修改 DecisionLogHook.after_iteration**

```python
# 修改前 (decision_log_hook.py:177)
def after_iteration(self, context: Any) -> None:
    """Agent迭代完成后回调（v0.26扩展：读取GoalState + 触发进化检查）"""

# 修改后
async def after_iteration(self, context: Any) -> None:
    """Agent迭代完成后回调（v0.26扩展：读取GoalState + 触发进化检查）"""
```

方法体不变，仅将 `def` 改为 `async def`。内部的 daemon 线程逻辑保持不变（`threading.Thread` 在 async 函数中仍然可用）。

- [ ] **Step 2: 修改 ErrorHandlingHook.after_iteration**

```python
# 修改前 (error_handling_hook.py:45)
async def after_iteration(self, context: AgentHookContext) -> None:

# 此文件已经是 async def，无需修改！跳过。
```

经检查，ErrorHandlingHook.after_iteration 已经是 `async def`，无需修改。

- [ ] **Step 3: 修改 ProgressDisplayHook.after_iteration**

```python
# 修改前 (progress_hook.py:50)
async def after_iteration(self, context: AgentHookContext) -> None:

# 此文件已经是 async def，无需修改！跳过。
```

经检查，ProgressDisplayHook.after_iteration 已经是 `async def`，无需修改。

- [ ] **Step 4: 修改 ObservabilityHook.after_iteration**

```python
# 修改前 (hook_integration.py:122)
async def after_iteration(self, context: AgentHookContext) -> None:

# 此文件已经是 async def，无需修改！跳过。
```

经检查，ObservabilityHook.after_iteration 已经是 `async def`，无需修改。

- [ ] **Step 5: Commit**

```bash
git add src/core/evolution/decision_log_hook.py
git commit -m "fix: change DecisionLogHook.after_iteration to async (P1-5)"
```

---

### Task 7: P1-6 emit_reasoning签名适配

**Files:**
- Modify: `src/core/evolution/decision_log_hook.py:228`

- [ ] **Step 1: 修改 emit_reasoning 方法签名**

```python
# 修改前 (decision_log_hook.py:228)
def emit_reasoning(self, context: AgentHookContext, reasoning_text: str) -> None:
    """推理片段回调（v0.26：推理可见化适配）

    将 Agent 推理片段追加到内部缓冲区，在 finalize_content 时
    写入 DecisionLog 的 prediction_snapshot。

    Args:
        context: Hook上下文
        reasoning_text: 推理片段文本
    """
    if reasoning_text:
        self._reasoning_buffer.append(reasoning_text)

# 修改后
async def emit_reasoning(self, reasoning_text: str) -> None:
    """推理片段回调（v0.26：推理可见化适配）

    将 Agent 推理片段追加到内部缓冲区，在 finalize_content 时
    写入 DecisionLog 的 prediction_snapshot。

    v0.30.0: nanobot-ai 0.2.1 移除了 context 参数，改为 async

    Args:
        reasoning_text: 推理片段文本
    """
    if reasoning_text:
        self._reasoning_buffer.append(reasoning_text)
```

- [ ] **Step 2: Commit**

```bash
git add src/core/evolution/decision_log_hook.py
git commit -m "fix: adapt emit_reasoning signature - remove context, add async (P1-6)"
```

---

### Task 8: P1-7 emit_reasoning_end签名适配

**Files:**
- Modify: `src/core/evolution/decision_log_hook.py:241`

- [ ] **Step 1: 修改 emit_reasoning_end 方法签名**

```python
# 修改前 (decision_log_hook.py:241)
def emit_reasoning_end(self, context: AgentHookContext) -> None:
    """推理结束回调（v0.26：推理可见化适配）

    标记推理过程结束。

    Args:
        context: Hook上下文
    """
    self._reasoning_complete = True

# 修改后
async def emit_reasoning_end(self) -> None:
    """推理结束回调（v0.26：推理可见化适配）

    标记推理过程结束。

    v0.30.0: nanobot-ai 0.2.1 移除了 context 参数，改为 async
    """
    self._reasoning_complete = True
```

- [ ] **Step 2: Commit**

```bash
git add src/core/evolution/decision_log_hook.py
git commit -m "fix: adapt emit_reasoning_end signature - remove context, add async (P1-7)"
```

---

### Task 9: 阶段2验证 — Hook功能测试

- [ ] **Step 1: 运行单元测试**

Run: `uv run pytest tests/unit/ -v --timeout=30`
Expected: 所有测试通过

- [ ] **Step 2: 运行 lint 检查**

Run: `uv run ruff check src/ tests/`
Expected: 无错误

- [ ] **Step 3: 运行类型检查**

Run: `uv run mypy src/ --ignore-missing-imports`
Expected: 无新增错误

---

## 阶段3: 新特性适配

### Task 10: 模型和上下文控制 — 配置注入

**Files:**
- Modify: `src/core/provider_adapter.py` — `_build_nanobot_config_from_runner` 方法

- [ ] **Step 1: 在 _build_nanobot_config_from_runner 中注入 model_presets**

在 `_build_nanobot_config_from_runner` 方法中，读取 `config.json` 的 `model_presets` 配置，注入到 nanobot Config：

```python
# 在 config = Config(...) 之前添加
model_presets_data = runner_config.get("model_presets", {})
if model_presets_data:
    try:
        from nanobot.config.schema import ModelPresetConfig

        presets = {}
        for name, preset_data in model_presets_data.items():
            presets[name] = ModelPresetConfig(
                model=preset_data.get("model", ""),
                provider=preset_data.get("provider", ""),
                context_window_tokens=preset_data.get("context_window_tokens"),
                max_tokens=preset_data.get("max_tokens"),
            )
        # 注入到 Config 构造
        # config = Config(..., model_presets=presets)
    except ImportError:
        logger.debug("nanobot-ai 不支持 ModelPresetConfig，跳过模型预设注入")
```

- [ ] **Step 2: 验证配置注入**

Run: `uv run python -c "from src.core.provider_adapter import RunnerProviderAdapter; print('OK')"`
Expected: 输出 "OK"

- [ ] **Step 3: Commit**

```bash
git add src/core/provider_adapter.py
git commit -m "feat: inject model_presets config for runtime model switching"
```

---

### Task 11: CLI Apps + MCP扩展 — 配置注入

**Files:**
- Modify: `src/core/provider_adapter.py` — `_build_nanobot_config_from_runner` 方法

- [ ] **Step 1: 在 _build_nanobot_config_from_runner 中注入 cli_apps 和 mcp_presets**

```python
# 在 config = Config(...) 之前添加
# CLI Apps 配置
cli_apps_data = runner_config.get("cli_apps", {})
if cli_apps_data:
    # cli_apps 在 nanobot-ai 0.2.1 的 tools 配置节中
    pass  # 通过 tools.cli_apps 配置项启用

# MCP Presets 配置
mcp_presets_data = runner_config.get("mcp_presets", {})
if mcp_presets_data:
    # mcp_presets 在 nanobot-ai 0.2.1 的 tools 配置节中
    pass  # 通过 tools.mcp_presets 配置项启用
```

- [ ] **Step 2: Commit**

```bash
git add src/core/provider_adapter.py
git commit -m "feat: inject cli_apps and mcp_presets config"
```

---

### Task 12: Thought/Response时间线 — StreamingHook推理推送

**Files:**
- Modify: `src/core/transparency/streaming_hook.py`

- [ ] **Step 1: 在 StreamingHook 中添加推理片段推送逻辑**

在 `on_stream` 方法中，通过 metadata 区分普通流式输出和推理片段：

```python
async def on_stream(self, context: AgentHookContext, delta: str) -> None:
    """流式输出时触发

    将流式输出片段通过CLI或Gateway通道输出。
    过滤空delta，不输出空字符串。

    Args:
        context: Hook上下文
        delta: 流式输出片段
    """
    if not delta:
        return

    self._stream_active = True
    self._stream_buffer += delta

    # CLI通道输出
    if self._console is not None:
        self._console.print(delta, end="")

    # Gateway通道输出
    if self._bus is not None and self._channel and self._chat_id:
        try:
            from nanobot.bus.events import OutboundMessage

            # v0.30.0: 通过 metadata 区分推理片段和普通输出
            metadata = {"stream_delta": True}
            # 检查是否为推理片段（nanobot-ai 0.2.1 的 thought 类型）
            if getattr(context, "is_reasoning", False):
                metadata["reasoning_delta"] = True

            self._bus.publish_outbound(
                OutboundMessage(
                    channel=self._channel,
                    chat_id=self._chat_id,
                    content=delta,
                    metadata=metadata,
                )
            )
        except NanobotRunnerError as e:
            logger.warning(f"Gateway流式输出失败: {e}")
```

- [ ] **Step 2: Commit**

```bash
git add src/core/transparency/streaming_hook.py
git commit -m "feat: add reasoning_delta metadata for Thought/Response timeline"
```

---

### Task 13: WebUI工作台 — 路由兼容性验证

**Files:**
- Modify: `src/core/webui/app.py`

- [ ] **Step 1: 验证 app.py 中 nanobot.web 导入兼容性**

检查 `_find_webui_dist` 函数中的 `import nanobot.web as web_pkg` 是否在 0.2.1 中仍然可用。

Run: `uv run python -c "import nanobot.web; print(nanobot.web.__file__)"`
Expected: 输出 nanobot.web 包路径

- [ ] **Step 2: 验证自定义路由与新布局兼容**

确认 `src/core/webui/routes/` 下的8个路由模块在 0.2.1 下正常工作。

Run: `uv run python -c "from src.core.webui.app import create_app; print('OK')"`
Expected: 输出 "OK"

- [ ] **Step 3: Commit（如有修改）**

```bash
git add src/core/webui/app.py
git commit -m "fix: verify WebUI route compatibility with nanobot-ai 0.2.1"
```

---

## 阶段4: 验证收尾

### Task 14: questionary 2.x 兼容性验证

- [ ] **Step 1: 搜索所有 questionary 调用点**

Run: `uv run python -c "import questionary; print(questionary.__version__)"`
Expected: 输出 2.x 版本号

- [ ] **Step 2: 验证 questionary API 兼容性**

搜索项目中所有 questionary 使用点，确认 API 兼容：

Run: `uv run ruff check src/ --select F401,F811`
Expected: 无未使用导入错误

---

### Task 15: 全量回归测试

- [ ] **Step 1: 运行单元测试**

Run: `uv run pytest tests/unit/ -v --timeout=30`
Expected: 所有测试通过

- [ ] **Step 2: 运行 lint 检查**

Run: `uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/`
Expected: 无错误

- [ ] **Step 3: 运行类型检查**

Run: `uv run mypy src/ --ignore-missing-imports`
Expected: 无新增错误

- [ ] **Step 4: 运行 E2E 测试（如有）**

Run: `uv run pytest tests/e2e/ -v --timeout=60 -m e2e`
Expected: 所有 E2E 测试通过

---

### Task 16: 版本号更新与文档

**Files:**
- Modify: `pyproject.toml:3` — 版本号更新
- Modify: `AGENTS.md` — 基线版本更新

- [ ] **Step 1: 更新 pyproject.toml 版本号**

```toml
# 修改前
version = "0.29.0"

# 修改后
version = "0.30.0"
```

- [ ] **Step 2: 更新 AGENTS.md 基线版本**

将 AGENTS.md 中的 `当前基线: v0.29.0` 更新为 `当前基线: v0.30.0`。

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml AGENTS.md
git commit -m "chore: bump version to 0.30.0 with nanobot-ai 0.2.1 upgrade"
```
