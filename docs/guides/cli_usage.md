# CLI 使用指南

> **文档版本**: v0.30.0 | **更新日期**: 2026-06-22
> **当前基线**: v0.30.0 | **规划版本**: v1.0.0

## 1. 概述

Nanobot Runner 提供命令行界面（CLI），用于导入跑步数据、查看统计信息和与 Agent 交互。

**v0.9.0 架构变更**: CLI 已按领域拆分为独立模块，命令采用分组结构（如 `nanobotrun data import`）。
**v0.19.0 新增**: 身体信号分析命令（`analysis hrv/fatigue/recovery` 和 `status`）。
**v0.20.0 新增**: ML智能预测命令（`predict vdot/race/injury/model`）。
**v0.20.1 增强**: 预测命令全面启用ML训练与推理，新增`predict model train/rollback`子命令。
**v0.21.0 新增**: 数字孪生命令（`twin snapshot/simulate/compare`），实现What-If推演能力。
**v0.23.0 新增**: 自适应进化命令（`evolution status/history/feedback/accuracy/fidelity`），实现决策追踪与结果回填。
**v0.27.0 新增**: WebUI 模式（`gateway start --webui`），通过浏览器访问 Agent 交互界面。
**v0.28.0 新增**: WebUI 数据可视化，启用 `--webui` 后可通过浏览器访问 6 大数据页面。
**v0.29.0 新增**: WebUI 管理控制台，启用 `--webui` 后可通过浏览器访问 10 大页面（新增训练计划管理、进化引擎控制台、设置中心）。

## 2. 安装与配置

### 2.1 环境要求

- Python 3.11+
- Git
- uv 包管理器（安装脚本会自动安装）

### 2.2 一键安装（推荐）

```bash
# 一键安装
curl -fsSL https://raw.githubusercontent.com/yecllsl/nanobot-runner/main/scripts/install.sh | bash

# 指定版本安装
curl -fsSL https://raw.githubusercontent.com/yecllsl/nanobot-runner/main/scripts/install.sh | bash -s -- --version v0.9.3

# 指定安装目录
curl -fsSL https://raw.githubusercontent.com/yecllsl/nanobot-runner/main/scripts/install.sh | bash -s -- --dir ~/my-runner
```

安装脚本支持的参数：

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--version TAG` | 安装指定版本 | `main` |
| `--dir PATH` | 安装到指定目录 | `~/.nanobot-runner-app` |
| `--skip-uv` | 跳过 uv 安装 | - |
| `--verbose` | 详细输出 | - |
| `--help` | 显示帮助 | - |

> **安全提示**: 建议先下载脚本审查后再执行：
> ```bash
> curl -fsSL -o install.sh https://raw.githubusercontent.com/yecllsl/nanobot-runner/main/scripts/install.sh
> less install.sh  # 审查脚本内容
> bash install.sh
> ```

### 2.3 手动安装

```bash
# 克隆项目
git clone https://github.com/yecllsl/nanobot-runner.git
cd nanobot-runner

# 创建虚拟环境
uv venv

# 激活虚拟环境 (Windows)
.venv\Scripts\activate

# 激活虚拟环境 (Linux/macOS)
source .venv/bin/activate

# 同步依赖
uv sync

# 验证安装
uv run nanobotrun --help
```

## 3. 命令参考

### 3.1 帮助命令

```bash
# 显示帮助信息
uv run nanobotrun --help

# 显示子命令帮助
uv run nanobotrun data --help
uv run nanobotrun analysis --help

# 显示版本信息
uv run nanobotrun system version
```

### 3.2 数据管理命令 (data)

#### 导入数据

```bash
# 导入单个FIT文件
uv run nanobotrun data import path/to/activity.fit

# 导入目录下所有FIT文件
uv run nanobotrun data import path/to/fit/files/

# 强制重新导入（跳过去重检查）
uv run nanobotrun data import path/to/activity.fit --force
```

**导入流程**：
1. 解析FIT文件提取运动数据
2. 计算SHA256指纹进行去重
3. 保存到Parquet文件（按年分片）
4. 更新索引文件

#### 统计查询

```bash
# 查看当前年份统计
uv run nanobotrun data stats

# 查看指定年份统计
uv run nanobotrun data stats --year 2024

# 查看日期范围统计
uv run nanobotrun data stats --start 2024-01-01 --end 2024-12-31
```

**统计输出示例**：
```
📊 2024年跑步统计
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
总里程: 1,234.56 km
总时长: 123:45:67
总次数: 45 次
平均配速: 5'34"/km
平均距离: 27.43 km
```

### 3.3 数据分析命令 (analysis)

#### VDOT 趋势

```bash
# 查看最近10次VDOT趋势
uv run nanobotrun analysis vdot

# 查看最近20次VDOT趋势
uv run nanobotrun analysis vdot --limit 20

# 导出VDOT趋势数据到JSON
uv run nanobotrun analysis vdot --output vdot_trend.json
```

#### 训练负荷

```bash
# 查看训练负荷（ATL/CTL/TSB）
uv run nanobotrun analysis load

# 查看最近60天训练负荷
uv run nanobotrun analysis load --days 60
```

#### 心率漂移

```bash
# 分析最近一次跑步的心率漂移
uv run nanobotrun analysis hr-drift

# 分析指定跑步记录
uv run nanobotrun analysis hr-drift --run-id <activity_id>
```

#### 心率变异分析 (v0.19.0)

```bash
# 查看HRV分析（最近30天）
uv run nanobotrun analysis hrv

# 查看指定时间范围
uv run nanobotrun analysis hrv --days 7
uv run nanobotrun analysis hrv --days 90

# 心率恢复分析
uv run nanobotrun analysis hr-recovery

# 分析指定跑步记录的心率恢复
uv run nanobotrun analysis hr-recovery --run-id <activity_id>
```

**输出示例**:
```
📊 HRV分析（最近30天）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
静息心率趋势: 52 → 50 bpm (↓ 改善)
估算RMSSD: 45.2 ms
估算SDNN: 52.8 ms
心率恢复(1分钟): 28%
心率恢复(3分钟): 55%
状态评估: 恢复良好，适合中等强度训练
```

#### 疲劳度与恢复评估 (v0.19.0)

```bash
# 查看当前疲劳度评分
uv run nanobotrun analysis fatigue

# 查看恢复状态
uv run nanobotrun analysis recovery

# 查看详细恢复指标
uv run nanobotrun analysis recovery --detailed
```

**输出示例**:
```
😴 疲劳度评估
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
综合疲劳度: 45/100 (中等)
恢复状态: 🟡 适度训练
ATL: 65 (近期负荷)
CTL: 58 (体能基础)
TSB: -7 (轻微疲劳)

💡 建议: 今天适合轻松跑或休息，避免高强度训练
```

### 3.4 身体状态命令 (status) (v0.19.0)

**v0.19.0 新增**: 快速查看身体状态和训练建议。

```bash
# 查看今日身体状态
uv run nanobotrun status today

# 查看本周身体状态摘要
uv run nanobotrun status weekly

# 查看指定日期状态
uv run nanobotrun status --date 2024-01-15
```

**输出示例**:
```
📋 今日身体状态 (2024-01-15)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
静息心率: 52 bpm (正常)
恢复状态: 🟢 良好
疲劳度: 35/100 (轻度)

💡 训练建议: 今天状态不错，可以进行间歇训练或节奏跑
```

### 3.5 Agent 交互命令 (agent)

```bash
# 启动交互式对话
uv run nanobotrun agent chat
```

**交互示例**：
```
> 最近一个月跑了多少？
📊 最近30天跑步统计：
- 总里程: 85.5 km
- 总时长: 8:15:30
- 总次数: 8 次

> 我的VDOT趋势怎么样？
📈 VDOT趋势分析：
- 当前VDOT: 45.2
- 30天前: 44.8
- 变化: +0.4 (↑ 改善中)
```

### 3.6 报告生成命令 (report)

**v0.15.0 新增**: 支持 `--output` 选项将报告保存为文件。

```bash
# 生成周报
uv run nanobotrun report generate --type weekly

# 生成月报
uv run nanobotrun report generate --type monthly

# 导出周报到文件 (v0.15.0 新增)
uv run nanobotrun report generate --type weekly --output weekly_report.md

# 导出月报到文件 (v0.15.0 新增)
uv run nanobotrun report generate --type monthly --output monthly_report.md

# 查看用户画像
uv run nanobotrun report profile
```

### 3.7 训练计划命令 (plan)

**v0.10.0~v0.12.0 新增**: 智能跑步计划系统，支持计划创建、执行跟踪、调整优化。

#### 创建训练计划

```bash
# 创建马拉松训练计划
uv run nanobotrun plan create 42.195 2026-06-15 --vdot 42.0 --volume 35

# 创建半程马拉松计划
uv run nanobotrun plan create 21.1 2026-05-01 --vdot 40.0 --volume 30 --age 35
```

#### 记录训练反馈

```bash
# 记录计划执行反馈
uv run nanobotrun plan log plan_20240101 2024-01-15 --completion 0.8 --effort 6

# 完整反馈记录
uv run nanobotrun plan log plan_20240101 2024-01-15 \
  --completion 1.0 \
  --effort 4 \
  --notes "轻松完成" \
  --distance 10.5 \
  --duration 65 \
  --hr 145
```

#### 查看计划统计

```bash
# 查看计划执行统计
uv run nanobotrun plan stats plan_20240101
```

#### 调整训练计划 (v0.11.0)

```bash
# 调整计划（减量）
uv run nanobotrun plan adjust plan_20240101 --action reduce --reason "疲劳恢复"

# 调整特定日期
uv run nanobotrun plan adjust plan_20240101 --action reschedule --date 2024-01-20
```

#### 获取调整建议 (v0.11.0)

```bash
# 获取智能调整建议
uv run nanobotrun plan suggest plan_20240101
```

#### 目标达成评估 (v0.12.0)

```bash
# 评估目标达成概率
uv run nanobotrun plan evaluate plan_20240101

# 评估特定目标
uv run nanobotrun plan evaluate plan_20240101 --target-time 3:30:00
```

#### 长期规划 (v0.12.0)

```bash
# 生成多周期长期训练计划
uv run nanobotrun plan long-term 42.195 2026-10-15 \
  --vdot 45.0 \
  --volume 40 \
  --cycles 3

# 指定基础周期周数
uv run nanobotrun plan long-term 42.195 2026-10-15 \
  --vdot 45.0 \
  --base-weeks 8 \
  --build-weeks 6
```

#### 智能训练建议 (v0.12.0)

```bash
# 获取个性化训练建议
uv run nanobotrun plan advice plan_20240101

# 针对特定方面获取建议
uv run nanobotrun plan advice plan_20240101 --focus aerobic
```

### 3.8 工具管理命令 (tools)

**v0.13.0 新增**: 工具管理命令用于管理 MCP 工具服务器的配置。

#### 列出工具

```bash
# 列出所有已配置的工具
uv run nanobotrun tools list
```

#### 添加 MCP 服务器

```bash
# 添加 STDIO 类型服务器
uv run nanobotrun tools add weather \
  --command npx \
  --args '["-y","@h1deya/mcp-server-weather"]' \
  --type stdio

# 添加 SSE 类型服务器
uv run nanobotrun tools add maps \
  --url http://localhost:3000/sse \
  --type sse

# 指定启用的工具
uv run nanobotrun tools add weather \
  --command npx \
  --args '["-y","@h1deya/mcp-server-weather"]' \
  --enabled-tools "get_forecast,get_alerts"
```

#### 移除 MCP 服务器

```bash
# 移除服务器
uv run nanobotrun tools remove weather
```

#### 启用/禁用工具

```bash
# 启用服务器
uv run nanobotrun tools enable weather

# 禁用服务器
uv run nanobotrun tools disable weather

# 启用特定工具（而非整个服务器）
uv run nanobotrun tools enable weather --tool get_forecast
```

#### 导入 Claude Desktop 配置

```bash
# 从 Claude Desktop 导入配置
uv run nanobotrun tools import-claude

# 指定 Claude Desktop 配置路径
uv run nanobotrun tools import-claude --config-path /path/to/claude/config.json
```

#### 验证工具配置

```bash
# 验证工具配置
uv run nanobotrun tools validate
```

### 3.9 初始化命令 (init)

**v0.9.4 新增**: 初始化命令用于配置工作区和用户设置。

```bash
# 全新初始化（交互式）
uv run nanobotrun system init

# 迁移模式（从旧版本迁移）
uv run nanobotrun system init --mode migrate

# 修复模式（修复配置问题）
uv run nanobotrun system init --mode repair

# 自动模式（非交互式）
uv run nanobotrun system init --auto

# 指定工作区目录
uv run nanobotrun system init --workspace /path/to/workspace
```

**初始化流程**:
1. 选择 LLM Provider (OpenAI/Anthropic/DeepSeek)
2. 配置 API Key 和模型
3. 配置业务参数（身高、体重、静息心率等）
4. 配置飞书集成（可选）
5. 验证配置有效性

### 3.10 系统管理命令 (system)

```bash
# 查看版本信息
uv run nanobotrun system version

# 查看配置信息
uv run nanobotrun system config --show

# 设置配置项
uv run nanobotrun system config --set key=value

# 验证配置（v0.9.4 新增）
uv run nanobotrun system validate

# 创建备份（v0.9.4 新增）
uv run nanobotrun system backup

# 恢复备份（v0.9.4 新增）
uv run nanobotrun system restore --backup-id <id>

# 数据迁移（v0.9.4 新增）
uv run nanobotrun system migrate

# 查看备份列表（v0.9.4 新增）
uv run nanobotrun system backup --list
```

### 3.11 透明化命令 (transparency)

**v0.15.0 新增**: AI 决策透明化命令，用于查看 AI 决策过程和系统状态。

#### 查看决策追踪

```bash
# 查看最近的 AI 决策追踪日志
uv run nanobotrun transparency trace

# 查看指定数量的决策记录
uv run nanobotrun transparency trace --limit 10

# 导出决策追踪到文件
uv run nanobotrun transparency trace --output trace.md
```

#### 查看 AI 状态仪表盘

```bash
# 查看 AI 助手状态仪表盘
uv run nanobotrun transparency status

# 查看详细状态信息
uv run nanobotrun transparency status --verbose
```

#### 生成训练洞察报告

```bash
# 生成训练洞察报告
uv run nanobotrun transparency insight

# 指定时间范围
uv run nanobotrun transparency insight --days 30

# 导出洞察报告到文件
uv run nanobotrun transparency insight --output insight.md
```

### 3.12 网关服务命令 (gateway)

**v0.27.0 增强**: Gateway 服务现已集成 WebUI 数据可视化功能。
**v0.28.0 新增**: WebUI 数据可视化，6 大页面全面展示跑步数据。

```bash
# 启动飞书机器人Gateway服务（集成所有功能）
uv run nanobotrun gateway start

# 启动时显示详细日志
uv run nanobotrun gateway start --verbose --logs

# 指定端口
uv run nanobotrun gateway start --port 18790

# 启用WebUI模式（v0.27.0 新增）
uv run nanobotrun gateway start --webui

# 启用WebUI模式并显示日志
uv run nanobotrun gateway start --webui --logs
```

**Gateway 功能特性** (v0.17.0):
- **Hook 系统**: 支持流式输出、进度追踪、错误处理
- **Cron 定时任务**: 自动训练提醒、天气感知建议
- **MCP 工具**: 动态工具加载和管理
- **Subagent 支持**: 子智能体任务委派

#### WebUI 模式 (v0.27.0)

`--webui` 标志启用 WebSocket 通道，允许通过浏览器与 Agent 实时交互。启用后，Gateway 启动时会自动启动 WebSocket 服务并显示 WebUI 访问地址。

**v0.28.0 增强**: 除 AI 对话 WebUI (8765) 外，新增数据可视化 WebUI (8766)，提供 6 大数据页面。

**快速启动**:

```bash
# 1. 启动 Gateway 并启用 WebUI
uv run nanobotrun gateway start --webui

# 2. 启动成功后，终端将显示访问地址：
#    ✓ AI 对话地址: http://127.0.0.1:8765
#    ✓ 数据可视化地址: http://127.0.0.1:8766
#    Token获取: curl http://127.0.0.1:8765/token

# 3. 在浏览器中打开 http://127.0.0.1:8766 即可访问数据可视化页面
```

**WebUI 数据可视化页面 (v0.28.0)**:

| 页面 | 路径 | 内容 |
|------|------|------|
| Dashboard | `/` | 今日概览（距离/时长/配速/心率）+ 本周统计 |
| VDOT 趋势 | `/vdot` | VDOT 变化趋势图，支持预测区间 |
| 训练负荷 | `/training-load` | ATL/CTL/TSB 趋势图 + 疲劳状态指示 |
| 活动列表 | `/activities` | 跑步记录列表，支持时间/距离筛选、分页 |
| 活动详情 | `/activities/:id` | 单次跑步完整数据 + 配速/心率曲线 |
| 身体信号 | `/body-signals` | HRV/疲劳度/恢复状态卡片 |

**时间范围筛选**: 所有页面支持 7 天/30 天/90 天/365 天切换，数据与 CLI 同源。

**认证**: 所有数据页面需携带有效 Token（与 AI 对话共享认证机制）。

**`--webui` 标志说明**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--webui` | bool | `False` | 启用 WebUI（WebSocket 通道），默认关闭 |

> **注意**: `--webui` 标志与 `config.json` 中的 `websocket.enabled` 为"或"关系——任一为 `True` 即启用 WebSocket 通道。即 `--webui` 无需修改配置文件即可启用 WebUI。

#### WebSocket 配置

WebSocket 服务通过 `config.json` 中的 `websocket` 节进行配置：

```json
{
  "websocket": {
    "enabled": false,
    "host": "127.0.0.1",
    "port": 8765,
    "token": "",
    "token_issue_path": "",
    "token_issue_secret": "",
    "websocket_requires_token": true,
    "streaming": true,
    "unified_session": false
  }
}
```

**配置项说明**:

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `enabled` | bool | `false` | 是否启用 WebSocket 服务，`--webui` 标志可覆盖 |
| `host` | string | `127.0.0.1` | 监听地址。`127.0.0.1` 仅本机访问，`0.0.0.0` 允许远程访问 |
| `port` | int | `8765` | 监听端口 |
| `token` | string | `""` | 静态访问令牌，为空则不启用静态令牌验证 |
| `token_issue_path` | string | `""` | 令牌签发接口路径（如 `/token`），为空则不启用动态签发 |
| `token_issue_secret` | string | `""` | 令牌签发密钥，用于 JWT 签名，生产环境务必设置强密钥 |
| `token_ttl_s` | int | `300` | 动态签发令牌的有效时长（秒），默认 5 分钟 |
| `websocket_requires_token` | bool | `true` | WebSocket 连接是否要求携带有效令牌 |
| `allow_from` | list | `["*"]` | 允许连接的来源地址列表，`["*"]` 不限制，生产环境建议限定域名 |
| `streaming` | bool | `true` | 是否启用流式输出，开启后 Agent 响应将逐步推送 |
| `max_message_bytes` | int | `37748736` | 单条 WebSocket 消息最大字节数，默认 36MB |
| `ping_interval_s` | float | `20.0` | 心跳 ping 间隔（秒） |
| `ping_timeout_s` | float | `20.0` | 心跳 ping 超时时间（秒） |
| `ssl_certfile` | string | `""` | SSL 证书文件路径，为空则不启用 TLS 加密 |
| `ssl_keyfile` | string | `""` | SSL 私钥文件路径，配合 `ssl_certfile` 使用 |
| `unified_session` | bool | `false` | 是否启用统一会话模式，开启后 WebUI 与 CLI 共享同一会话上下文 |

#### 环境变量覆盖

WebSocket 配置支持通过环境变量覆盖 `config.json` 中的值，环境变量优先级高于配置文件：

| 环境变量 | 覆盖配置项 | 示例值 |
|----------|-----------|--------|
| `NANOBOT_WS_ENABLED` | `websocket.enabled` | `true` |
| `NANOBOT_WS_HOST` | `websocket.host` | `0.0.0.0` |
| `NANOBOT_WS_PORT` | `websocket.port` | `9090` |
| `NANOBOT_WS_TOKEN` | `websocket.token` | `my-secret-token` |
| `NANOBOT_WS_TOKEN_SECRET` | `websocket.token_issue_secret` | `jwt-signing-secret` |

**使用示例**:

```bash
# 临时修改 WebSocket 端口
$env:NANOBOT_WS_PORT="9090"; uv run nanobotrun gateway start --webui

# 允许远程访问
$env:NANOBOT_WS_HOST="0.0.0.0"; uv run nanobotrun gateway start --webui

# Linux/macOS
NANOBOT_WS_PORT=9090 NANOBOT_WS_HOST=0.0.0.0 uv run nanobotrun gateway start --webui
```

#### 安全认证

WebUI 默认启用 Token 认证（`websocket_requires_token: true`），连接 WebSocket 时需携带有效令牌。

**认证方式一：动态令牌签发（推荐）**

在 `config.json` 中配置 `token_issue_path` 和 `token_issue_secret` 后，可通过 HTTP 接口获取临时令牌：

```bash
# 配置签发路径和密钥
# config.json:
#   "token_issue_path": "/token"
#   "token_issue_secret": "your-strong-secret"

# 获取令牌
curl http://127.0.0.1:8765/token

# 返回示例：
# {"token": "eyJhbGciOiJIUzI1NiIs...", "expires_in": 300}
```

签发的令牌为 JWT 格式，有效期由 `token_ttl_s` 控制（默认 300 秒/5 分钟）。

**认证方式二：静态令牌**

在 `config.json` 中直接设置 `token` 字段，所有 WebSocket 连接需携带该令牌：

```json
{
  "websocket": {
    "token": "my-static-token",
    "websocket_requires_token": true
  }
}
```

**关闭认证（不推荐）**

仅限本地开发环境使用：

```json
{
  "websocket": {
    "websocket_requires_token": false
  }
}
```

> **安全提示**:
> - 生产环境务必设置 `token_issue_secret` 为强密钥
> - `websocket_requires_token` 应保持 `true`
> - `allow_from` 建议限定具体域名，避免使用 `["*"]`
> - 远程访问时建议配置 `ssl_certfile` 和 `ssl_keyfile` 启用 TLS 加密

### 3.13 ML智能预测命令 (predict) (v0.20.0)

**v0.20.0 新增**: ML增强预测命令，为数据充足用户提供更精准的未来洞察。
**v0.20.1 增强**: 全面启用ML训练与推理，数据充足时自动启用ML模型。

#### VDOT趋势预测

```bash
# 预测未来30天VDOT趋势
uv run nanobotrun predict vdot

# 预测指定天数
uv run nanobotrun predict vdot --days 60

# 预测90天趋势
uv run nanobotrun predict vdot --days 90
```

**输出示例**:
```
[VDOT Prediction] VDOT趋势预测
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
当前VDOT: 45.2
预测VDOT: 46.1 ([green]+0.9[/green])
置信区间: [44.8, 47.4]
置信度: 78%
趋势斜率: +0.0150/天
预测模式: 🧠 ML增强预测 | 模型置信度: 高
数据质量: SUFFICIENT
```

#### 比赛成绩预测

```bash
# 预测马拉松成绩
uv run nanobotrun predict race --distance 42.195

# 预测半程马拉松成绩
uv run nanobotrun predict race --distance 21.1

# 指定比赛日期
uv run nanobotrun predict race --distance 42.195 --date 2026-10-15
```

**输出示例**:
```
[Race Prediction] 比赛成绩预测
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
预测完赛时间: 3:45:32
最佳情况: 3:38:15
最差情况: 3:52:48
置信度: 82%
对应VDOT: 46.5
预测模式: personalized
```

#### 伤病风险预测

```bash
# 预测未来21天伤病风险
uv run nanobotrun predict injury

# 预测指定天数
uv run nanobotrun predict injury --days 30
```

**输出示例**:
```
[Injury Risk] 伤病风险预测
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
当前风险等级: 🟡 中等风险
未来21天风险趋势:
  第7天: 35% (中等)
  第14天: 42% (中等)
  第21天: 38% (中等)

主要风险因素:
  1. 近期负荷突增 (+15%)
  2. 连续训练日 (5天)
建议: 适当安排休息日，降低训练强度
```

#### 模型管理

```bash
# 查看模型状态
uv run nanobotrun predict model status

# 手动触发模型训练
uv run nanobotrun predict model train --type vdot
uv run nanobotrun predict model train --type injury
uv run nanobotrun predict model train --type all

# 回滚到上一个稳定模型版本
uv run nanobotrun predict model rollback --type vdot
```

**模型状态输出示例**:
```
[Model Status] 预测模型状态
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VDOT模型:
  版本: v1.2.0
  训练时间: 2026-05-10 14:30:00
  验证误差(MAE): 0.85
  特征数: 24
  状态: ✅ 正常

伤病模型:
  版本: v1.0.3
  训练时间: 2026-05-09 10:15:00
  验证误差(AUC): 0.82
  状态: ✅ 正常
```

建议: 适当安排休息日，降低训练强度
```

#### 模型管理

```bash
# 查看模型状态
uv run nanobotrun predict model status

# 手动触发模型训练
uv run nanobotrun predict model train --type vdot
uv run nanobotrun predict model train --type injury
uv run nanobotrun predict model train --type all

# 校准模型
uv run nanobotrun predict model calibrate --type vdot
```

### 3.14 数字孪生命令 (twin) (v0.21.0)

**v0.21.0 新增**: 数字孪生引擎命令，实现跑者状态快照和What-If训练计划推演。

#### 查看跑者状态快照

```bash
# 查看当前5维度跑者状态快照
uv run nanobotrun twin snapshot

# 以JSON格式输出
uv run nanobotrun twin snapshot --json
```

**输出示例**:
```
🏃 跑者状态快照 (2026-05-12)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 体能维度
  VDOT: 45.2 (趋势: +0.3)
  VO2max估算: 52.1 ml/kg/min

📈 负荷维度
  CTL: 58 (体能基础)
  ATL: 65 (近期负荷)
  TSB: -7 (轻微疲劳)
  ACWR: 1.12 (负荷比)

😴 身体信号维度
  疲劳度: 42/100 (中等)
  恢复状态: 🟡 适度训练
  静息心率: 52 bpm

⚠️ 风险维度
  7天伤病风险: 28% (低)
  28天伤病风险: 35% (中)
  过度训练风险: 无

🏃 训练模式维度
  周跑量: 45.2 km
  强度分布: 轻松70% | 节奏15% | 间歇15%
  长距离频率: 1次/周

数据质量: SUFFICIENT
```

#### 推演训练计划效果

```bash
# 推演指定系统训练计划（4周）
uv run nanobotrun twin simulate --plan-id plan_001

# 推演并指定周数
uv run nanobotrun twin simulate --plan-id plan_001 --weeks 8

# 手动构建计划推演
uv run nanobotrun twin simulate --name "破4计划" --weeks '[{"weekly_volume_km":50,"easy_ratio":0.7,"tempo_ratio":0.15,"interval_ratio":0.15,"long_run_km":25}]'
```

**输出示例**:
```
🔮 训练计划推演: 破4计划
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
初始状态: VDOT 45.2 | CTL 58 | TSB -7

周1: VDOT 45.3 | CTL 60 | TSB -5 | 伤病风险 25% | 置信度 92%
周2: VDOT 45.5 | CTL 62 | TSB -3 | 伤病风险 28% | 置信度 87%
周3: VDOT 45.6 | CTL 63 | TSB -2 | 伤病风险 30% | 置信度 82%
周4: VDOT 45.8 | CTL 65 | TSB 0  | 伤病风险 32% | 置信度 78%

📊 推演总结
  VDOT变化: +0.6 (4周)
  峰值伤病风险: 32% (中等)
  平均TSB: -2.5 (轻微疲劳)
  最终恢复状态: 🟡 适度训练

⚠️ 提示: 模拟结果，非确定性预测。置信度78%，推演结果仅供参考。
```

#### 对比多个训练计划

```bash
# 对比多个系统训练计划
uv run nanobotrun twin compare --plan-ids plan_001,plan_002,plan_003

# 手动构建计划对比
uv run nanobotrun twin compare --plans '[{"name":"保守","weeks":[...]},{"name":"激进","weeks":[...]}]'
```

**输出示例**:
```
📊 训练计划对比
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
计划          VDOT提升  峰值风险  平均TSB  恢复状态  推荐分
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
plan_001      +0.8      35%       -3.2     🟡       82.5  ⭐推荐
plan_002      +1.2      48%       -8.5     🔴       68.3
plan_003      +0.5      25%       +2.1     🟢       75.8

💡 推荐: plan_001
理由: 综合VDOT提升、伤病风险和恢复余量最优。
      VDOT提升适中(+0.8)，伤病风险可控(35%)，恢复状态良好。
```

---

### 3.15 自适应进化命令 (evolution) (v0.23.0)

**v0.23.0 新增**: 自适应进化引擎命令，实现AI决策自动记录、结果回填、用户反馈收集。

#### 查看进化状态

```bash
# 查看当前进化状态
uv run nanobotrun evolution status

# 以JSON格式输出
uv run nanobotrun evolution status --json
```

**输出示例**:
```
🧬 自适应进化状态
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 决策追踪
  决策总数: 156
  结果回填数: 142
  回填率: 91.0%
  反馈收集数: 48
  反馈收集率: 30.8%

📈 预测准确度
  MAE: 3.2%
  高估比例: 45%
  低估比例: 35%
  准确比例: 20%

🏃 执行忠实度
  平均忠实度: 0.82
  体积偏差: 8.5%
  时间偏差: 6.2%

⚙️ 配置
  存储路径: ~/.nanobot-runner/decisions
  异步写入: 关闭
  runner_state字段: vdot, ctl, atl, tsb, fatigue_score
```

#### 查询决策历史

```bash
# 查询最近30天的决策历史
uv run nanobotrun evolution history --days 30

# 按日期范围查询
uv run nanobotrun evolution history --start 2026-04-01 --end 2026-05-01

# 按决策类型过滤
uv run nanobotrun evolution history --type PLAN_ADJUSTMENT

# 以JSON格式输出
uv run nanobotrun evolution history --days 7 --json
```

**输出示例**:
```
📋 决策历史 (最近30天)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[2026-05-18 14:30] PLAN_ADJUSTMENT
  决策ID: abc123...
  执行状态: executed
  建议: 减少本周跑量10%，注意休息
  是否采纳: 是

[2026-05-17 08:15] TRAINING_ADVICE
  决策ID: def456...
  执行状态: executed
  建议: 今日适合轻松跑，配速6'00"-6'30"/km
  是否采纳: 是

[2026-05-16 19:45] RECOVERY_SUGGESTION
  决策ID: ghi789...
  执行状态: skipped
  建议: 疲劳度较高，建议休息1天
  是否采纳: 否
```

#### 提交用户反馈

```bash
# 通过决策ID提交反馈
uv run nanobotrun evolution feedback abc123 --score 4 --text "建议很实用" --accepted

# 列出最近5条决策供选择
uv run nanobotrun evolution feedback --recent

# 通过序号选择（选择最近第1条决策）
uv run nanobotrun evolution feedback 1 --score 5
```

**输出示例**:
```
✅ 反馈提交成功
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
决策ID: abc123...
评分: 4/5
文本反馈: 建议很实用
是否采纳: 是

感谢您的反馈！这将帮助AI更好地理解您的训练偏好。
```

#### 查看预测准确度

```bash
# 查看最近30天的预测准确度
uv run nanobotrun evolution accuracy --days 30

# 以JSON格式输出
uv run nanobotrun evolution accuracy --days 90 --json
```

**输出示例**:
```
📊 预测准确度分析 (最近30天)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📈 总体准确度
  MAE: 3.2%
  预测-实际配对数: 45

📉 偏差分析
  高估比例: 45% (20次)
  低估比例: 35% (16次)
  准确比例: 20% (9次)

💡 建议: AI倾向于高估您的训练效果，建议适当降低预期目标。
```

#### 查看执行忠实度

```bash
# 查看最近30天的执行忠实度
uv run nanobotrun evolution fidelity --days 30

# 以JSON格式输出
uv run nanobotrun evolution fidelity --days 90 --json
```

**输出示例**:
```
🏃 执行忠实度分析 (最近30天)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 总体忠实度
  平均忠实度: 0.82
  计划执行数: 28

📉 偏差分析
  体积偏差: 8.5%
  时间偏差: 6.2%

💡 建议: 您的执行忠实度较高，训练计划执行良好。
```

#### 查看校准状态 (v0.24.0)

**v0.24.0 新增**: 基于决策日志和结果记录，校准预测模型的系统性偏差。

```bash
# 查看VDOT预测校准状态
uv run nanobotrun evolution calibration --model-type vdot

# 查看伤病风险校准状态
uv run nanobotrun evolution calibration --model-type injury

# 以JSON格式输出
uv run nanobotrun evolution calibration --model-type vdot --json
```

**输出示例**:
```
📊 预测校准状态
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📈 模型: VDOT预测
  bias: +0.3
  scale: 0.97
  配对数据: 15条
  触发阈值: 10条 (已触发)
  校准前MAE: 4.2%
  校准后MAE: 3.5%

💡 建议: 模型存在轻微高估偏差 (+0.3)，已应用偏差修正。
```

#### 训练响应性分析 (v0.24.0)

**v0.24.0 新增**: 分析用户对不同训练刺激的反应，识别最有效的训练类型。

```bash
# 分析最近6个月的训练响应性
uv run nanobotrun evolution response --months 6

# 分析最近3个月
uv run nanobotrun evolution response --months 3

# 以JSON格式输出
uv run nanobotrun evolution response --months 6 --json
```

**输出示例**:
```
📈 训练响应性分析 (最近6个月)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏃 训练类型效果排名
  1. 间歇训练   VDOT提升: +1.2  样本数: 8
  2. 阈值训练   VDOT提升: +0.9  样本数: 12
  3. 长距离跑   VDOT提升: +0.5  样本数: 15
  4. 恢复跑     VDOT提升: +0.1  样本数: 20

💡 建议: 您对间歇训练响应性最强，建议在训练计划中适当增加间歇训练比例。
```

---

## 4. 输出格式

### 4.1 时长格式

- **CLI显示**: `HH:MM:SS` (如 1:23:45)
- **存储格式**: 秒数 (float)

### 4.2 配速格式

- **CLI显示**: `M'SS"/km` (如 5'30"/km)
- **存储格式**: 秒/公里 (float)

### 4.3 距离格式

- **CLI显示**: `X.XX km` (如 10.25 km)
- **存储格式**: 米 (float)

## 5. 数据存储

### 5.1 存储位置

```
~/.nanobot-runner/data/
├── activities_2023.parquet
├── activities_2024.parquet
└── index.json
```

### 5.2 数据格式

Parquet 文件 Schema：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `activity_id` | string | 活动唯一ID |
| `timestamp` | datetime | 活动时间 |
| `total_distance` | float | 总距离（米） |
| `total_timer_time` | float | 总时长（秒） |
| `avg_speed` | float | 平均速度 |
| `avg_heart_rate` | float | 平均心率 |
| `total_calories` | float | 消耗卡路里 |

## 6. 常见问题

### 6.1 导入失败

**问题**: 导入FIT文件时报错
**解决**:
1. 确认文件格式正确（.fit扩展名）
2. 检查文件是否损坏
3. 使用 `--force` 参数重试

### 6.2 数据查询为空

**问题**: 统计命令无数据返回
**解决**:
1. 确认数据已成功导入
2. 检查日期范围是否正确
3. 验证年份参数

### 6.3 环境问题

**问题**: Windows PowerShell 执行策略限制
**解决**:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## 7. 高级用法

### 7.1 批量导入

```bash
# 导入多个目录
uv run nanobotrun data import dir1/ dir2/ dir3/
```

### 7.2 数据验证

```bash
# 导入后验证数据完整性
uv run nanobotrun data stats --year 2024
```

### 7.3 性能优化

- 大量数据导入时使用 `--force` 跳过去重检查
- 定期清理旧数据文件
- 使用SSD存储提升查询性能

### 7.4 命令别名（v0.9.0 新增）

v0.9.0 支持简写命令：

```bash
# 完整命令
uv run nanobotrun data import /path/to/file.fit

# 简写命令（等价）
uv run nanobotrun d i /path/to/file.fit
```

## 8. 配置文件

### 8.1 配置位置

`~/.nanobot-runner/config.json`

### 8.2 配置示例

```json
{
  "data_dir": "~/.nanobot-runner/data",
  "default_year": 2024,
  "timezone": "Asia/Shanghai"
}
```

---

**文档版本**: v0.30.0
**最后更新**: 2026-06-22
**关联文档**: [Agent配置指南](./agent_config_guide.md) | [更新日志](../../CHANGELOG.md)
