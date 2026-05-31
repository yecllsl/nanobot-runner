# v0.27.0 测试策略

> **版本**: v0.27.0
> **创建日期**: 2026-05-31
> **需求依据**: REQ_需求规格说明书.md v12.1 §5.3
> **架构依据**: 架构设计说明书.md v16.0.0 §10
> **代码评审**: 代码评审报告（有条件通过，2项Important待修复）

---

## 1. 测试目标

验证 v0.27.0 WebUI 基础功能（配置驱动启用 nanobot-ai 内置 WebUI）的正确性、完整性和向后兼容性，确保：
- 所有 P0 功能需求（REQ-D-11 至 REQ-D-13、REQ-D-17 至 REQ-D-18）可正常工作
- 所有 P1/P2 功能需求（REQ-D-14 至 REQ-D-16、REQ-D-19 至 REQ-D-20）可用
- 非功能需求（NFR-D-11 至 NFR-D-16）达标
- 现有功能零回归（v0.26.0 功能不受影响）

---

## 2. 测试范围

### 2.1 包含的测试项

| 模块 | 测试类型 | 测试项 |
|------|---------|--------|
| ConfigManager | 单元测试 | WebSocket 配置读取、环境变量覆盖、默认值处理 |
| RunnerProviderAdapter | 单元测试 | WebSocket 配置构建、品牌字段写入、webui_enabled 参数 |
| Gateway CLI | 集成测试 | `--webui` 标志、启动信息显示、向后兼容 |
| WebSocket 通道 | 集成测试 | 连接建立、token 认证、流式输出 |
| WebUI 页面 | 端到端测试 | 页面加载、Agent 对话、工具调用 |
| 现有功能 | 回归测试 | 飞书通道、CLI 命令、Agent 工具 |

### 2.2 不包含的测试项

- WebUI 前端 UI 测试（v0.28.0 数据可视化）
- 性能压力测试（非 v0.27.0 核心目标）
- 多用户并发测试（单用户项目）

---

## 3. 测试策略

### 3.1 单元测试（核心模块）

| 模块 | 覆盖率要求 | 测试文件 |
|------|-----------|---------|
| ConfigManager (WebSocket) | ≥80% | `tests/unit/config/test_websocket_config.py` |
| RunnerProviderAdapter | ≥80% | `tests/unit/core/test_provider_adapter.py` |
| Gateway CLI 命令 | ≥60% | `tests/unit/cli/test_gateway.py`（如有） |

**测试场景**：
- ✅ 正常路径：配置存在、参数正确
- ⚠️ 边界条件：配置节不存在、环境变量缺失
- ❌ 异常路径：配置项类型错误、端口冲突

### 3.2 集成测试（端到端验证）

| 测试项 | 验收标准 | 测试文件 |
|--------|---------|---------|
| WebUI 启动 | Gateway 启动后 WebSocket 通道可用 | `tests/integration/test_webui_startup.py` |
| 页面加载 | HTTP GET 返回 WebUI SPA 页面 | 同上 |
| Token 认证 | WebSocket 连接需要 token | 同上 |
| Agent 对话 | 通过 WebSocket 发送消息并收到响应 | 同上 |
| 向后兼容 | 不加 `--webui` 时飞书通道正常 | 同上 |

### 3.3 回归测试

| 测试项 | 验收标准 | 测试文件 |
|--------|---------|---------|
| 现有 CLI 命令 | `data import`、`analysis vdot`、`plan create` 正常工作 | `tests/unit/` 现有测试 |
| 飞书通道 | Gateway 启动后飞书通道可连接 | `tests/integration/` 现有测试 |
| Agent 工具 | 所有工具正常注册和调用 | `tests/unit/agents/` 现有测试 |

---

## 4. 准入准出规则

### 4.1 测试准入

- [x] 开发交付报告已提交（代码已提交到 feature/v0.27.0 分支）
- [x] 代码评审通过（有条件通过，2项Important已修复）
- [x] 单元测试覆盖率 ≥80%（core 模块）
- [x] 本地核心场景验证通过（开发者自测通过）

### 4.2 测试准出

| 指标 | 阈值 | 验证方式 |
|------|------|---------|
| 单元测试通过率 | 100% | `uv run pytest tests/unit/ -v` |
| 集成测试通过率 | ≥95% | `uv run pytest tests/integration/ -v` |
| 代码覆盖率 | core≥80%, cli≥60% | `uv run pytest --cov=src/core --cov=src/cli` |
| Lint 检查 | 0 errors | `uv run ruff check src/ tests/` |
| 类型检查 | 0 new errors | `uv run mypy src/ --ignore-missing-imports` |
| WebUI 启动验证 | 手动验证通过 | `nanobotrun gateway start --webui` |

---

## 5. 测试用例清单

### 5.1 功能测试用例

| 用例ID | 需求 | 描述 | 预期结果 | 优先级 |
|--------|------|------|---------|--------|
| TC-01 | REQ-D-11 | WebUI 启动 | Gateway 启动后浏览器访问 http://127.0.0.1:8765 可加载页面 | P0 |
| TC-02 | REQ-D-12 | 工具调用 | WebUI 中调用 RunFlowAgent 工具返回正确结果 | P0 |
| TC-03 | REQ-D-13 | 流式输出 | Agent 回复逐字展示，delta 间隔<200ms | P0 |
| TC-04 | REQ-D-14 | 多会话管理 | WebUI 中可创建/切换/删除对话 | P1 |
| TC-05 | REQ-D-15 | 基础设置 | WebUI 设置面板可切换模型 | P1 |
| TC-06 | REQ-D-16 | 品牌自定义 | WebUI 显示 "Nanobot-Runner" 和 🏃‍♂️ | P2 |
| TC-07 | REQ-D-17 | WebSocket 配置 | config.json 可配置 WebSocket 通道 | P0 |
| TC-08 | REQ-D-18 | 安全认证 | WebSocket 默认启用 token 认证 | P0 |
| TC-09 | REQ-D-19 | Gateway 命令增强 | `--webui` 标志启用 WebSocket 通道 | P1 |
| TC-10 | REQ-D-20 | 统一会话模式 | `unified_session=True` 时多通道共享会话 | P2 |

### 5.2 非功能测试用例

| 用例ID | 需求 | 描述 | 验收标准 | 优先级 |
|--------|------|------|---------|--------|
| TC-NFR-01 | NFR-D-11 | WebUI 首屏加载 | 页面加载时间 < 3s | P1 |
| TC-NFR-02 | NFR-D-12 | WebSocket 连接延迟 | 连接建立 < 100ms | P1 |
| TC-NFR-03 | NFR-D-13 | 流式输出延迟 | delta 展示延迟 < 200ms | P1 |
| TC-NFR-04 | NFR-D-14 | 工具调用兼容性 | 成功率与飞书通道一致（≥99%） | P1 |
| TC-NFR-05 | NFR-D-15 | 安全默认 | 仅监听 127.0.0.1，token 认证启用 | P0 |
| TC-NFR-06 | NFR-D-16 | 向后兼容 | 不启用 WebUI 时飞书/CLI 正常 | P0 |

### 5.3 回归测试用例

| 用例ID | 描述 | 预期结果 | 优先级 |
|--------|------|---------|--------|
| TC-REG-01 | `data import` 命令 | 正常导入 FIT 文件 | P0 |
| TC-REG-02 | `analysis vdot` 命令 | 正常输出 VDOT 分析 | P0 |
| TC-REG-03 | `plan create` 命令 | 正常创建训练计划 | P0 |
| TC-REG-04 | `evolution status` 命令 | 正常输出进化状态 | P0 |
| TC-REG-05 | 飞书通道对话 | 正常接收和回复消息 | P0 |
| TC-REG-06 | Agent 工具注册 | 所有工具正常可用 | P0 |

---

## 6. 测试环境

| 项目 | 配置 |
|------|------|
| 操作系统 | Windows 11 (PowerShell 7+) |
| Python 版本 | 3.11+ |
| 包管理器 | uv |
| nanobot-ai 版本 | ≥0.2.0 |
| 测试数据 | tests/data/ 脱敏测试数据 |

---

## 7. 风险与缓解

| 风险 | 等级 | 影响 | 缓解措施 |
|------|------|------|---------|
| nanobot-ai WebUI 版本变更 | 低 | 页面加载失败 | 锁定 nanobot-ai 版本，记录当前可用版本 |
| WebSocket 端口冲突 | 中 | 8765 端口被占用 | 测试前检查端口可用性，支持环境变量覆盖 |
| Token 认证配置错误 | 中 | 无法建立 WebSocket 连接 | 提供明确的 token 获取和配置指引 |
| 集成测试环境依赖 | 低 | 需要真实 Gateway 进程 | Mock 或使用测试端口，避免依赖外部服务 |

---

## 8. 测试执行计划

### 8.1 执行顺序

1. **单元测试**（自动执行）：`uv run pytest tests/unit/ -v`
2. **Lint 检查**（自动执行）：`uv run ruff check src/ tests/` + `uv run mypy src/`
3. **集成测试**（半自动执行）：`uv run pytest tests/integration/ -v`
4. **手动验证**：启动 Gateway，浏览器访问 WebUI

### 8.2 通过标准

- 单元测试通过率 ≥100%
- 集成测试通过率 ≥95%
- Lint 检查 0 errors
- 手动验证核心场景通过（WebUI 加载、Agent 对话）

---

## 9. 测试报告输出

测试执行完成后输出：
- `/docs/test/测试报告_v0.27.0.md` - 详细测试报告
- `/docs/test/Bug清单_v0.27.0.md`（如有Bug）
- `/docs/test/上线结论_v0.27.0.md` - 上线建议
