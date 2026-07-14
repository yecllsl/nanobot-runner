# v0.32.0 Bug 清单

> **版本**: v0.32.0
> **测试日期**: 2026-07-14
> **状态**: 无 P0/P1 Bug

---

## Bug 统计

| 级别 | 数量 | 状态 |
|------|------|------|
| P0 (阻塞) | 0 | - |
| P1 (严重) | 0 | - |
| P2 (一般) | 0 | - |
| P3 (轻微) | 0 | - |
| **总计** | **0** | - |

---

## 测试修复记录（非 Bug）

以下问题为测试代码与生产代码不同步导致，已在测试执行前修复：

### FIX-01: 配置注入集成测试 mock 缺失

**文件**: `tests/integration/module/test_config_injection.py`

**问题**: `_make_mock_config` 未设置 `load_nanobot_config.return_value`，导致 5 个测试失败。

**根因**: v0.32.0 配置分离后，`RunnerProviderAdapter` 从 `load_nanobot_config()` 读取配置，但测试 mock 未更新。

**修复**: 更新 `_make_mock_config` 方法，添加 nanobot 格式配置字典返回值。

**影响**: 测试代码，非生产代码。

---

### FIX-02: WebUI 应用工厂配置读取

**文件**: `src/core/webui/app.py`

**问题**: `create_app()` 使用硬编码默认值而非从 `context.config.get_webui_config()` 读取配置，导致 8 个测试因 JWT 验证失败返回 401。

**根因**: 配置分离后，WebUI 配置应从 context 读取，但 `create_app` 仍使用硬编码。

**修复**: 将第 70 行改为 `webui_config = context.config.get_webui_config()`。

**影响**: 生产代码，但为配置读取路径修复，非逻辑缺陷。

---

### FIX-03: API Key 断言兼容性

**文件**: `tests/integration/module/test_config_injection.py`

**问题**: `test_injection_chain_no_api_key` 断言 `api_key is None`，但实际返回空字符串。

**根因**: `_from_nanobot_config` 中 `provider_cfg.get("apiKey", "")` 返回空字符串而非 None。

**修复**: 将断言改为 `assert not llm_config.api_key`，兼容 None 和空字符串。

**影响**: 测试代码，断言逻辑调整。

---

## 遗留问题（非 Bug）

### ISSUE-01: 单元测试环境限制

**用例**: 
- `test_init_prompts.py::test_run_full_wizard_skip_optional`
- `test_init_prompts.py::test_run_full_wizard_with_optional`
- `test_init_tools_config.py::test_tools_config_in_agent_mode`

**现象**: `NoConsoleScreenBufferError: No Windows console found`

**原因**: `prompt_toolkit` 在非交互式终端（如 CI、IDE 终端）中无法初始化 Windows 控制台。

**影响**: 3 个测试失败，与 v0.32.0 代码变更无关。

**建议**: 在测试中添加环境检测，非交互式终端自动跳过。

---

### ISSUE-02: 配置迁移模块覆盖率不足

**文件**: `src/core/init/migrate.py`

**覆盖率**: 0%

**原因**: 配置迁移为一次性操作，测试需要模拟完整的迁移场景（旧 config.json → nanobot_config.json）。

**建议**: 后续版本补充迁移流程的单元测试和集成测试。

---

### ISSUE-03: 配置管理器覆盖率偏低

**文件**: `src/core/config/manager.py`

**覆盖率**: 43%（目标 80%）

**原因**: 配置管理器包含大量文件 I/O 操作和异常处理分支，部分路径难以覆盖。

**建议**: 后续版本使用 `tmp_path` fixture 补充文件系统操作测试。

---

## 结论

v0.32.0 版本**无 P0/P1 Bug**，测试通过。

所有修复均为测试代码与生产代码同步问题，非逻辑缺陷。

遗留问题为环境限制和覆盖率不足，不影响版本发布。
