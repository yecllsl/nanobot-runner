# Bug 修复报告 v0.30.0

**版本**: v0.30.0  
**日期**: 2026-06-21  
**修复人**: AI Agent

---

## 1. Bug 清单

### Bug #1: nanobot.webui.http_utils 模块不存在

**优先级**: P0  
**严重程度**: 高  
**影响范围**: WebUI 启动、WebSocket 通道配置

**问题描述**:  
集成测试失败，错误信息：
```
ModuleNotFoundError: No module named 'nanobot.webui.http_utils'
```

**根因分析**:  
nanobot-ai 0.2.1 中 `http_utils` 模块不存在。代码错误地从 `nanobot.webui.http_utils` 导入 `http_error` 和 `parse_request_path`，但这些函数实际位于 `nanobot.channels.websocket` 模块中（带下划线前缀：`_http_error` 和 `_parse_request_path`）。

**修复方案**:  
修改 `src/core/provider_adapter.py` 第 29-36 行：
```python
# 修复前
from nanobot.webui.http_utils import (
    http_error as _http_error,
)
from nanobot.webui.http_utils import (
    parse_request_path as _parse_request_path,
)

# 修复后
from nanobot.channels.websocket import (
    WebSocketChannel,
    _http_error,
    _parse_request_path,
)
```

**验证结果**: ✅ 已修复，所有相关测试通过

---

### Bug #2: MagicMock 导致 Pydantic 验证失败

**优先级**: P0  
**严重程度**: 高  
**影响范围**: 集成测试、WebUI 配置注入

**问题描述**:  
集成测试失败，错误信息：
```
catalogTtlSeconds: Input should be greater than or equal to 60
[type=greater_than_equal, input_value=<MagicMock ...>, input_type=MagicMock]
```

**根因分析**:  
测试代码中 `mock_config.load_config()` 返回 MagicMock 对象，而非真实字典。nanobot 0.2.1 中 `CliAppsToolConfig` 的 `catalogTtlSeconds` 字段要求 `>= 60`，MagicMock 对象无法通过 Pydantic 验证。

**修复方案**:  
在 `tests/integration/test_webui_startup.py` 中，为所有使用 `MagicMock()` 的测试用例添加：
```python
mock_config.load_config.return_value = {}
```

涉及测试类：
- `TestWebUIConfigInjection._make_mock_config()`
- `TestChannelManagerWebUI.test_full_injection_to_channel_manager()`
- `TestGatewayStartWebUIE2E` 的所有测试方法

**验证结果**: ✅ 已修复，所有相关测试通过

---

### Bug #3: nanobot 0.2.1 ChannelManager 调用 discover_enabled

**优先级**: P1  
**严重程度**: 中  
**影响范围**: 集成测试、ChannelManager 初始化

**问题描述**:  
集成测试超时（>30s），堆栈显示卡在 `ChannelManager._init_channels()` 中导入飞书模块。

**根因分析**:  
nanobot 0.2.1 中 `ChannelManager._init_channels()` 从调用 `discover_all()` 改为调用 `discover_enabled()`。测试代码仅 mock 了 `discover_all()`，未 mock `discover_enabled()`，导致实际导入飞书等慢速模块。

**修复方案**:  
1. 在 `tests/integration/test_webui_startup.py` 中添加 `_mock_discover_enabled()` 函数
2. 修改 `_create_channel_manager()` 同时 mock 两个函数：
```python
with patch("nanobot.channels.registry.discover_all", _mock_discover_all):
    with patch("nanobot.channels.registry.discover_enabled", _mock_discover_enabled):
        return ChannelManager(config=config, bus=bus)
```

**验证结果**: ✅ 已修复，所有相关测试通过

---

## 2. 修复文件清单

| 文件路径 | 修改类型 | 说明 |
|---------|---------|------|
| `src/core/provider_adapter.py` | 修改 | 修复 http_utils 模块导入 |
| `tests/integration/test_webui_startup.py` | 修改 | 修复 MagicMock 返回值、添加 discover_enabled mock |

---

## 3. 测试验证

### 3.1 单元测试
- **执行结果**: ✅ 4226 passed, 1 skipped
- **覆盖率**: 81%
- **耗时**: 15.23s

### 3.2 集成测试
- **执行结果**: ✅ 25 passed
- **耗时**: 23.18s
- **关键测试**:
  - `TestWebUIConfigInjection`: 6/6 通过
  - `TestChannelManagerWebUI`: 5/5 通过
  - `TestGatewayStartWebUIE2E`: 5/5 通过
  - `TestWebSocketServerStartup`: 9/9 通过

### 3.3 E2E 测试
- **执行状态**: 待执行

---

## 4. 影响评估

### 4.1 功能影响
- ✅ WebUI 启动流程正常
- ✅ WebSocket 通道配置正确
- ✅ Gateway 启动集成正常
- ✅ 无新功能引入

### 4.2 兼容性
- ✅ 向后兼容 nanobot-ai 0.2.0
- ✅ 向前兼容 nanobot-ai 0.2.1

### 4.3 性能影响
- ✅ 无性能退化
- ✅ 测试执行时间正常

---

## 5. 结论

**修复状态**: ✅ 全部修复  
**测试状态**: ✅ 单元测试和集成测试全部通过  
**上线建议**: 建议执行 E2E 测试后上线

---

**下一步**:
1. 执行 E2E 测试验证完整链路
2. 生成回归测试报告
3. 执行上线前验证
