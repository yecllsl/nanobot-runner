# TUI 图形界面方案分析

> **文档版本**: v1.0
> **创建日期**: 2026-05-19
> **基线版本**: v0.22.0
> **对齐文档**:
> - [架构设计说明书](架构设计说明书.md)
> - [产品规划方案](../product/产品规划方案.md)

---

## 1. 背景与目标

### 1.1 问题陈述

Nanobot Runner 当前仅提供 CLI 交互方式（Typer + Rich），对非技术用户存在以下门槛：

- 命令行操作不直觉，需记忆命令语法
- 终端输出与输入混杂，信息回看困难
- Agent Chat 模式下聊天记录无法独立滚动翻阅
- 图表（plotext）和表格与对话流混杂，视觉层次不清
- 工具调用过程对用户不可见，缺乏信任感

### 1.2 目标

提供一个**最简 GUI 实现**，使一般用户能够：

1. 通过图形界面完成核心操作（数据导入、查看分析、Agent 对话）
2. 不改变现有架构和业务逻辑
3. 保持单用户本地运行，不引入 Web/云端依赖
4. 渐进式迁移，CLI 与 GUI 并存

---

## 2. 方案对比

### 2.1 候选方案

| 方案 | 技术栈 | 优势 | 劣势 | 改动量 |
|------|--------|------|------|--------|
| **A. Textual TUI** | Textual | 与 Rich 生态无缝衔接；终端内运行；零依赖冲突 | 仍是终端，非传统窗口GUI | ★☆☆ 最小 |
| **B. Gradio WebUI** | Gradio | 开箱即用；自带图表；用户最熟悉（浏览器） | 引入 Web 依赖；需启动本地服务器 | ★★☆ 中等 |
| **C. NiceGUI** | NiceGUI | 现代 Web UI；组件丰富；Python 原生 | 较重；异步模型需适配 | ★★★ 较大 |
| **D. PyQt/PySide** | Qt | 原生桌面；功能最强 | 学习曲线陡；打包体积大 | ★★★ 最大 |

### 2.2 推荐方案：Textual TUI（首选）

**核心理由**：

1. **与现有架构零摩擦** — 项目已重度依赖 Rich，Textual 是 Rich 同一作者的作品，Rich 对象可直接嵌入 Textual 组件
2. **最小改动量** — 现有 handler 层和 `AppContext` 依赖注入完全复用，只需新增 TUI 界面层
3. **终端内即 GUI** — Textual 提供鼠标可点击、可滚动的"类 GUI"体验，远比裸 CLI 友好
4. **打包不变** — 无需额外打包步骤，`uv run nanobotrun tui` 即可启动

**备选方案：Gradio WebUI**

如果目标用户完全无法接受终端界面，浏览器界面更直觉。Gradio 的 `gr.Plot` 可直接渲染 matplotlib 图表，替代 plotext。本地 `launch(server_name="127.0.0.1")` 不违反"无 Web UI"约束（仍是本地单用户）。

### 2.3 新增依赖

```toml
# Textual 方案（首选）
"textual>=0.50.0"

# Gradio 方案（备选）
"gradio>=4.0.0"
```

---

## 3. 架构设计

### 3.1 分层复用

现有代码的分层设计天然支持 TUI 接入：

```
现有层：
  CLI Commands → Handlers → AppContext (核心业务)
                              ↑
新增层：                        │
  TUI Screens ─────────────────┘
     │
     └→ ChatScreen
          ├── 复用 AgentLoop + RunnerTools（零改动）
          ├── 复用 StreamingHook（适配 Textual 的 Live 更新）
          └── 复用 formatter.py 的格式化逻辑（Rich → Textual 无缝）
```

关键适配点：

- **AgentLoop 和工具集完全复用**，TUI 只替换交互层
- **Rich 对象可直接嵌入 Textual** — `Static(format_stats_panel(data))` 即可
- **流式输出** — 将 `CLIStreamingManager` 的 `on_delta` 回调对接到 Textual 的 `update()` 方法

### 3.2 目录结构

```
src/
├── cli/                        # 现有 CLI 不变
│   ├── commands/
│   │   └── tui.py              # 新增 `nanobotrun tui` 命令入口
│   └── ...
├── tui/                        # 新增 TUI 层
│   ├── __init__.py
│   ├── app.py                  # Textual Application 入口
│   ├── screens/                # 各功能页面
│   │   ├── __init__.py
│   │   ├── chat_screen.py      # Agent Chat 页面（核心入口）
│   │   ├── dashboard_screen.py # 主仪表盘（VDOT/训练负荷/恢复状态）
│   │   ├── import_screen.py    # 数据导入（拖拽 FIT 文件）
│   │   ├── analysis_screen.py  # 分析结果展示
│   │   └── plan_screen.py      # 训练计划
│   └── widgets/                # 可复用组件
│       ├── __init__.py
│       ├── chat_message.py     # 聊天气泡组件
│       ├── chart_widget.py     # 图表组件（复用 plotext 或 rich 绘图）
│       ├── metric_card.py      # 指标卡片组件
│       └── tool_call_card.py   # 工具调用折叠卡片
└── core/                       # 现有核心模块不变
```

### 3.3 CLI 入口

在 `src/cli/commands/tui.py` 中新增命令：

```python
@app.command()
def tui() -> None:
    """启动图形界面模式"""
    from src.tui.app import NanobotTUI
    NanobotTUI().run()
```

注册到 `app.py`：

```python
app.add_typer(tui_app, name="tui")
```

---

## 4. Agent Chat TUI 设计

### 4.1 Chat 作为核心入口

Chat 页面应作为 TUI 的**默认首页**，用户一打开就能自然语言交互，同时 Tab 可切换到结构化页面。

### 4.2 界面布局

```
┌─ Nanobot Runner ──────────────────────────────────────────┐
│ [💬 Chat] [📊 Dashboard] [📋 Plan] [⚙ Settings]          │
├───────────────────────────────────────────────────────────┤
│                                                           │
│  🤖 Bot  │ Nanobot Runner Agent 已就绪                    │
│          │ 模型: deepseek-chat                            │
│          │ MCP工具: weather, calendar                     │
│          │                                                │
│  👤 您   │ 我最近跑步状态怎么样？                          │
│          │                                                │
│  🤖 Bot  │ 根据您最近的数据：                              │
│          │                                                │
│          │  ┌─ 训练负荷 ──────────────────────┐           │
│          │  │ ATL: 52  CTL: 65  TSB: +13     │           │
│          │  │ 状态: 体能充沛，适合高强度训练    │           │
│          │  └────────────────────────────────┘           │
│          │                                                │
│          │ 🔧 调用了 get_training_load                    │
│          │                                                │
│  👤 您   │ 我的VDOT趋势呢？                               │
│          │                                                │
│  🤖 Bot  │ 近期VDOT变化如下：                              │
│          │  ┌─ VDOT趋势图 ────────────────────┐          │
│          │  │     ╱‾‾╲    ╱‾‾‾╲              │          │
│          │  │  ╱╲╱    ╲╱╲╱    ╲             │          │
│          │  │ ╱          ╲      ╲╱           │          │
│          │  │ 44.2 → 46.8 (↑2.6)            │          │
│          │  └────────────────────────────────┘          │
│                                                           │
├───────────────────────────────────────────────────────────┤
│ > 输入消息...                                    [发送]   │
├───────────────────────────────────────────────────────────┤
│ VDOT 46.8 | TSB +13 | 今日恢复 85%                       │
└───────────────────────────────────────────────────────────┘
```

### 4.3 体验提升对比

| 维度 | CLI Chat（现状） | TUI Chat（Textual） |
|------|-----------------|-------------------|
| **对话布局** | 输入输出混流 | 上下分区：聊天区 + 固定输入栏 |
| **历史回看** | 终端滚动，容易丢失 | 聊天区独立滚动，随时翻阅 |
| **消息区分** | 颜色区分，易混淆 | 头像+气泡，视觉清晰 |
| **工具调用** | 不可见或日志输出 | 内联折叠卡片，点击可展开详情 |
| **图表展示** | plotext 终端图 | 嵌入式图表组件，支持交互 |
| **表格数据** | Rich Table 滚走 | 可折叠/可滚动的数据卡片 |
| **流式输出** | spinner + 逐字 | 打字机效果 + 实时渲染 Markdown |
| **多任务** | 阻塞式 | 可后台执行，切换 Tab 查看其他页面 |
| **快捷操作** | 只能打字 | 侧栏快捷按钮（导入数据/查看报告等） |

### 4.4 现有代码复用映射

| 现有模块 | TUI 复用方式 |
|---------|-------------|
| `AgentLoop` + `RunnerTools` | 直接复用，零改动 |
| `StreamingHook` | 适配 `on_delta` → Textual `update()` |
| `formatter.py` 的 `format_stats_panel` | `Static(format_stats_panel(data))` 直接嵌入 |
| `formatter.py` 的 `format_runs_table` | 嵌入 Textual 的 `DataTable` 或 Rich Table |
| `CLIStreamingManager` | 改写为 `TUIStreamingManager`，回调对接 Textual |
| `AppContext` 依赖注入 | `get_context()` 不变 |

---

## 5. 其他核心页面

### 5.1 Dashboard 仪表盘

展示用户最关心的实时指标：

- 今日身体状态（恢复度/疲劳度/HRV）
- VDOT 当前值与趋势箭头
- 训练负荷三角（ATL/CTL/TSB）
- 本周训练摘要（距离/时长/次数）
- 下一次训练计划提醒

### 5.2 Import 数据导入

- 文件选择器（替代 CLI 的路径参数）
- 拖拽导入 FIT 文件
- 导入进度条
- 去重检测结果展示

### 5.3 Analysis 分析页

- VDOT 趋势图（可切换 7/30/90/365 天）
- 训练负荷图（ATL/CTL/TSB 曲线）
- 心率区间分布
- HRV 趋势

### 5.4 Plan 训练计划页

- 当前计划概览（日历视图）
- 计划执行反馈录入
- 计划调整交互

---

## 6. 实施优先级

| 优先级 | 功能 | 价值 |
|--------|------|------|
| **P0** | Chat 页面 + Dashboard 仪表盘 + 数据导入 | 核心交互闭环 |
| **P1** | Analysis 分析结果页（VDOT趋势/HR区间/训练负荷图表） | 数据洞察可视化 |
| **P2** | Plan 训练计划交互 + 报告查看 | 训练管理 |
| **P3** | 高级功能（数字孪生/预测/导出/偏好设置） | 完整功能覆盖 |

---

## 7. 风险与约束

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| Textual 在 Windows 终端兼容性 | 部分终端渲染异常 | 推荐使用 Windows Terminal；降级到 CLI |
| plotext 图表嵌入 Textual | 两者都操作终端，可能冲突 | 改用 Rich 的 sparkline 或 ASCII 图表 |
| Agent 异步调用与 Textual 事件循环 | 两个 async loop 冲突 | 使用 `asyncio.run_in_executor` 或 Textual 的 `run_worker` |
| 新增依赖体积 | textual 约 5MB | 可接受，远小于 Qt/Gradio |

---

## 8. 总结

Textual TUI 是最符合项目现状的 GUI 方案：

- **与 Rich 生态天然融合**，现有格式化代码零改动复用
- **Agent Chat 作为核心入口**，自然语言交互 + 结构化页面并行
- **改动最小**，新增 TUI 层与 CLI 层并存，核心业务逻辑不变
- **渐进式迁移**，P0 先做 Chat + Dashboard + Import，其余功能逐步补齐

如果未来用户群体明确需要浏览器界面，可再引入 Gradio 作为备选方案，两者架构兼容。
