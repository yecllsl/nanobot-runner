# CLI 使用指南

> **文档版本**: v0.19.0 | **更新日期**: 2026-05-06
> **当前基线**: v0.18.0 | **规划版本**: v0.19.0

## 1. 概述

Nanobot Runner 提供命令行界面（CLI），用于导入跑步数据、查看统计信息和与 Agent 交互。

**v0.9.0 架构变更**: CLI 已按领域拆分为独立模块，命令采用分组结构（如 `nanobotrun data import`）。
**v0.19.0 新增**: 身体信号分析命令（`analysis hrv/fatigue/recovery` 和 `status`）。

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
uv sync --all-extras

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

**v0.17.0 增强**: Gateway 服务现已集成 Hook 系统、Cron 定时任务和 MCP 工具管理。

```bash
# 启动飞书机器人Gateway服务（集成所有功能）
uv run nanobotrun gateway start

# 启动时显示详细日志
uv run nanobotrun gateway start --verbose --logs

# 指定端口
uv run nanobotrun gateway start --port 18790
```

**Gateway 功能特性** (v0.17.0):
- **Hook 系统**: 支持流式输出、进度追踪、错误处理
- **Cron 定时任务**: 自动训练提醒、天气感知建议
- **MCP 工具**: 动态工具加载和管理
- **Subagent 支持**: 子智能体任务委派

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

**文档版本**: v0.16.0
**最后更新**: 2026-04-29
**关联文档**: [Agent配置指南](./agent_config_guide.md) | [更新日志](../../CHANGELOG.md)
