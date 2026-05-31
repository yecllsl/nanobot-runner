# WebUI Settings API 拦截设计

> 日期: 2026-05-28
> 版本: v0.27.0
> 状态: 已批准

## 背景

nanobot-runner 的设计原则是**配置独立性**：所有配置从 `~/.nanobot-runner/config.json` 读取，不依赖底座 nanobot 的 `~/.nanobot/config.json`。

WebUI 功能通过 nanobot 的 `WebSocketChannel` 提供，其 Settings API（`/api/settings/update`、`/api/settings/provider/update`、`/api/settings/web-search/update`）直接读写 `~/.nanobot/config.json`，违反了这一原则。

## 问题

| 层面 | 行为 | 是否符合独立配置原则 |
|------|------|---------------------|
| WebSocket 通道启动 | 从 nanobot-runner 配置注入 | ✅ 符合 |
| LLM 配置读取 | 通过 `RunnerProviderAdapter` | ✅ 符合 |
| **WebUI Settings API** | **直接读写 `~/.nanobot/config.json`** | ❌ **违反** |

具体影响：
1. 用户在 WebUI 修改 LLM 配置 → 写入 `~/.nanobot/config.json`
2. gateway 重启 → 从 `~/.nanobot-runner/config.json` 读取 → WebUI 修改丢失
3. 两份配置不同步，造成混乱

## 方案：Monkey-patch 拦截写操作

### 核心思路

在 `RunnerProviderAdapter` 构建完 nanobot 配置后，对 `WebSocketChannel._dispatch_http` 做 monkey-patch，拦截 3 个写操作端点，返回 403 Forbidden。

### 拦截端点

| 端点 | 原行为 | 拦截后行为 |
|------|--------|-----------|
| `/api/settings/update` | 修改 model/provider，写入 `~/.nanobot/config.json` | 403 + 提示信息 |
| `/api/settings/provider/update` | 修改 provider API key/base，写入 `~/.nanobot/config.json` | 403 + 提示信息 |
| `/api/settings/web-search/update` | 修改搜索引擎配置，写入 `~/.nanobot/config.json` | 403 + 提示信息 |

### 不拦截端点

| 端点 | 原因 |
|------|------|
| `/api/settings` (GET) | 只读，用于 WebUI 显示当前配置 |
| `/api/sessions` | 会话管理，不涉及配置 |
| `/webui/bootstrap` | Token 签发，不涉及配置 |
| `/api/commands` | 命令面板，不涉及配置 |

### 实现位置

`src/core/provider_adapter.py` 的 `RunnerProviderAdapter._build_nanobot_config_from_runner()` 方法末尾，构建完 config 后调用 patch 函数。

### 错误响应格式

```json
{
  "error": "Settings updates are managed by nanobot-runner config. Use 'nanobotrun system init' or edit ~/.nanobot-runner/config.json"
}
```

HTTP 状态码：403 Forbidden

### 代码结构

```python
# provider_adapter.py 顶层
_BLOCKED_SETTINGS_PATHS = frozenset({
    "/api/settings/update",
    "/api/settings/provider/update",
    "/api/settings/web-search/update",
})

def _patch_websocket_settings_api() -> None:
    """拦截 WebUI Settings 写操作，防止写入 ~/.nanobot/config.json"""
    from nanobot.channels.websocket import WebSocketChannel
    _original_dispatch = WebSocketChannel._dispatch_http

    async def _runner_dispatch_http(self, connection, request):
        from nanobot.channels.websocket import _parse_request_path, _http_error
        got, _ = _parse_request_path(request.path)
        if got in _BLOCKED_SETTINGS_PATHS:
            return _http_error(403, "Settings updates are managed by nanobot-runner config. Use 'nanobotrun system init' or edit ~/.nanobot-runner/config.json")
        return await _original_dispatch(self, connection, request)

    WebSocketChannel._dispatch_http = _runner_dispatch_http
```

在 `_build_nanobot_config_from_runner()` 末尾调用 `_patch_websocket_settings_api()`。

## 测试策略

1. **单元测试**：验证 monkey-patch 后，3 个写端点返回 403
2. **单元测试**：验证读端点 `/api/settings` 仍正常返回 200
3. **集成测试**：启动 gateway + WebUI，确认界面只读，修改操作被拦截

## 风险与缓解

| 风险 | 缓解措施 |
|------|---------|
| nanobot 升级改路径名 | `_BLOCKED_SETTINGS_PATHS` 集中定义，易于更新 |
| monkey-patch 影响其他场景 | 仅在 `_build_nanobot_config_from_runner` 中调用，非 WebUI 模式不触发 |
| WebUI 前端显示错误 | 403 响应包含明确提示信息，前端应能正常展示 |
