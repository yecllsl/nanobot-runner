# CLI 用户指南

## 概述

Nanobot Runner 提供强大的命令行界面（CLI），支持 FIT 文件导入、数据统计、报告生成和 Agent 交互等功能。

## 安装与配置

### 环境要求

- Python >= 3.11
- Windows / macOS / Linux

### 安装方式

```bash
# 使用 uv 安装（推荐）
uv venv
uv sync --all-extras

# 激活虚拟环境
# Windows PowerShell
.venv\Scripts\Activate.ps1

# Windows CMD
.venv\Scripts\activate.bat

# Linux/macOS
source .venv/bin/activate
```

### 验证安装

```bash
uv run nanobotrun --help
```

输出示例：

```
Usage: nanobotrun [OPTIONS] COMMAND [ARGS]...

  Nanobot Runner - 桌面端私人AI跑步助理

Options:
  --version   显示版本信息
  --help      显示帮助信息

Commands:
  import   导入FIT文件
  stats    查看统计数据
  report   生成报告
  chat     启动Agent交互
```

---

## 命令详解

### `import` - 导入 FIT 文件

导入 Garmin 等设备导出的 FIT 文件到本地数据库。

**基本用法：**

```bash
# 导入单个文件
uv run nanobotrun import /path/to/activity.fit

# 导入整个目录
uv run nanobotrun import /path/to/activities/

# 强制重新导入（覆盖已有数据）
uv run nanobotrun import /path/to/activity.fit --force
```

**参数说明：**

| 参数 | 说明 | 示例 |
|------|------|------|
| `PATH` | FIT 文件或目录路径 | `/data/runs/2024/` |
| `--force` | 强制导入，忽略去重 | `--force` |

**输出示例：**

```
✓ 发现 15 个 FIT 文件
  [████████████████████] 100%  正在导入...

✓ 导入完成
  成功: 15
  跳过: 3 (重复文件)
  失败: 0

  总距离: 125.5 km
  总时长: 12:30:00
```

**常见问题：**

1. **导入失败**
   - 检查文件是否为有效的 FIT 格式
   - 确认文件未损坏
   - 查看日志：`~/.nanobot-runner/logs/nanobot-runner.log`

2. **重复导入**
   - 系统基于文件 SHA256 指纹自动去重
   - 使用 `--force` 强制重新导入

---

### `stats` - 查看统计数据

查看跑步统计数据，支持按年份和日期范围筛选。

**基本用法：**

```bash
# 查看所有时间的统计
uv run nanobotrun stats

# 查看指定年份
uv run nanobotrun stats --year 2024

# 查看日期范围
uv run nanobotrun stats --start 2024-01-01 --end 2024-12-31
```

**参数说明：**

| 参数 | 说明 | 示例 |
|------|------|------|
| `--year` | 指定年份 | `--year 2024` |
| `--start` | 开始日期 | `--start 2024-01-01` |
| `--end` | 结束日期 | `--end 2024-12-31` |

**输出示例：**

```
╔══════════════════════════════════════════════════════════╗
║                    跑步统计 (2024)                       ║
╠══════════════════════════════════════════════════════════╣
║  总次数:        156 次                                   ║
║  总距离:        1,250.5 km                               ║
║  总时长:        125:30:00                                ║
║  平均距离:      8.0 km                                   ║
║  平均时长:      48:20                                    ║
║  平均配速:      6'02"/km                                 ║
║  平均心率:      145 bpm                                  ║
╚══════════════════════════════════════════════════════════╝
```

---

### `report` - 生成报告

生成跑步分析报告，支持多种报告类型和推送选项。

**基本用法：**

```bash
# 生成周报
uv run nanobotrun report --type weekly

# 生成月报
uv run nanobotrun report --type monthly

# 生成年报
uv run nanobotrun report --type yearly --year 2024

# 推送到飞书
uv run nanobotrun report --type weekly --push
```

**参数说明：**

| 参数 | 说明 | 可选值 | 示例 |
|------|------|--------|------|
| `--type` | 报告类型 | `weekly`, `monthly`, `yearly` | `--type weekly` |
| `--year` | 指定年份 | 整数 | `--year 2024` |
| `--push` | 推送到飞书 | 标志 | `--push` |

**输出示例：**

```
📊 生成周报 (2024-03-11 ~ 2024-03-17)
  [████████████████████] 100%

✓ 报告生成完成

📈 本周概览
  跑步次数: 5 次
  总距离: 42.5 km
  总时长: 4:15:00
  平均配速: 6'00"/km

🏃 详细记录
  周一  10.0 km  1:00:00  6'00"/km
  周三   8.5 km  0:50:00  5'53"/km
  周五  12.0 km  1:12:00  6'00"/km
  周六   6.0 km  0:35:00  5'50"/km
  周日   6.0 km  0:38:00  6'20"/km

📊 VDOT 趋势
  本周平均: 45.2 (+0.5)

💡 训练建议
  本周训练量适中，建议下周增加一次长距离慢跑。
```

---

### `chat` - 启动 Agent 交互

启动交互式 Agent，支持自然语言查询跑步数据。

**基本用法：**

```bash
# 启动交互模式
uv run nanobotrun chat

# 直接执行单条命令
uv run nanobotrun chat --command "我今年跑了多少次？"
```

**交互示例：**

```
🤖 Nanobot Runner AI 助手
   输入 'exit' 或 'quit' 退出

> 我今年跑了多少次？
📊 查询结果
   2024年您共跑了 156 次
   总距离: 1,250.5 km
   总时长: 125:30:00

> 查看最近5次跑步
📋 最近跑步记录
   1. 2024-03-17  10.0 km  1:00:00  6'00"/km
   2. 2024-03-16   8.0 km  0:48:00  6'00"/km
   3. 2024-03-15  12.0 km  1:12:00  6'00"/km
   4. 2024-03-13   6.0 km  0:35:00  5'50"/km
   5. 2024-03-11  10.0 km  1:00:00  6'00"/km

> 我的VDOT是多少？
🏃 VDOT 分析
   当前 VDOT: 45.2
   水平: 中等偏上
   趋势: 上升 (+0.5/月)

> exit
👋 再见！
```

**支持的查询类型：**

| 查询类型 | 示例 |
|----------|------|
| 统计查询 | "我今年跑了多少次？" |
| 趋势分析 | "我的VDOT趋势如何？" |
| 记录查询 | "查看最近10次跑步" |
| 日期范围 | "1月份跑了哪些步？" |
| 距离筛选 | "我跑过哪些半马？" |
| 训练负荷 | "我的训练负荷如何？" |
| 心率分析 | "分析这次跑步的心率" |

---

## 高级用法

### 批量导入脚本

```bash
#!/bin/bash
# import_all.sh - 批量导入所有历史数据

for year in 2020 2021 2022 2023 2024; do
    echo "导入 $year 年数据..."
    uv run nanobotrun import "/data/garmin/$year" --force
done
```

### 定时生成周报

```bash
#!/bin/bash
# weekly_report.sh - 每周一生成并推送周报

# 生成周报并推送
uv run nanobotrun report --type weekly --push

# 记录日志
echo "周报已生成: $(date)" >> ~/.nanobot-runner/reports.log
```

添加到 crontab（Linux/macOS）：

```bash
# 每周一早上8点生成周报
0 8 * * 1 /path/to/weekly_report.sh
```

### 数据备份

```bash
#!/bin/bash
# backup.sh - 备份数据

BACKUP_DIR="/backup/nanobot-runner/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

# 复制数据文件
cp -r ~/.nanobot-runner/data "$BACKUP_DIR/"
cp -r ~/.nanobot-runner/config "$BACKUP_DIR/"

# 压缩
tar -czf "$BACKUP_DIR.tar.gz" "$BACKUP_DIR"
rm -rf "$BACKUP_DIR"

echo "备份完成: $BACKUP_DIR.tar.gz"
```

---

## 配置说明

### 首次运行与初始化

**自动初始化机制**：

> ⚠️ **重要**：workspace 目录结构由 nanobot-ai 框架自动初始化，无需手动创建。

当首次运行 `nanobotrun` 命令时，nanobot-ai 框架会自动检测并创建必要的目录结构：

```bash
# 首次运行任意命令即可触发初始化
uv run nanobotrun --help
```

**自动创建的文件/目录**：

| 文件/目录 | 说明 |
|----------|------|
| `AGENTS.md` | Agent 行为准则模板 |
| `SOUL.md` | 人格、价值观、语气风格 |
| `USER.md` | 用户画像模板 |
| `memory/MEMORY.md` | 长期记忆初始文件 |
| `memory/HISTORY.md` | 事件日志初始文件 |
| `skills/` | 技能目录（如版本默认带） |

**应用自动创建的目录**：

首次执行 `import` 命令时，应用会自动创建业务数据目录：

| 目录 | 说明 |
|-----|------|
| `data/` | 业务数据存储目录 |
| `data/plans/` | 训练计划存储目录 |
| `logs/` | 日志文件目录 |

### 配置文件位置

```
~/.nanobot-runner/              # nanobot workspace（主目录）
├── config.json                 # 应用配置文件
├── data/                       # 业务数据目录
│   ├── activities_2023.parquet # 运动数据（按年分片）
│   ├── activities_2024.parquet
│   ├── profile.json            # 用户画像数据
│   ├── plans/                  # 训练计划
│   └── index.json              # 去重索引
├── memory/                     # 记忆系统
│   ├── MEMORY.md               # 长期记忆/用户画像
│   └── HISTORY.md              # 事件日志
├── sessions/                   # 会话历史
├── skills/                     # 技能扩展
├── logs/                       # 日志目录
│   └── nanobot-runner.log
├── AGENTS.md                   # Agent行为准则
├── SOUL.md                     # 人格设定
├── USER.md                     # 用户画像
└── HEARTBEAT.md                # 定时任务

~/.nanobot/                     # nanobot 框架配置目录
└── config.json                 # 框架配置（LLM Provider等）
```

### 配置项说明

```json
{
  "data_dir": "~/.nanobot-runner/data",
  "log_level": "INFO",
  "log_format": "text",
  "feishu": {
    "enabled": false,
    "webhook_url": ""
  }
}
```

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `data_dir` | 数据存储目录 | `~/.nanobot-runner/data` |
| `log_level` | 日志级别 | `INFO` |
| `log_format` | 日志格式 | `text` |
| `feishu.enabled` | 启用飞书推送 | `false` |
| `feishu.webhook_url` | 飞书 webhook 地址 | `""` |

---

## 故障排查

### 常见问题

#### 1. 命令未找到

**问题：** `nanobotrun: command not found`

**解决：**

```bash
# 确保使用 uv run 运行
uv run nanobotrun --help

# 或激活虚拟环境后运行
.venv\Scripts\Activate.ps1  # Windows
nanobotrun --help
```

#### 2. 导入失败

**问题：** FIT 文件导入失败

**解决：**

```bash
# 检查文件有效性
uv run nanobotrun import /path/to/file.fit --verbose

# 查看详细日志
cat ~/.nanobot-runner/logs/nanobot-runner.log
```

#### 3. 统计数据为空

**问题：** `stats` 命令显示无数据

**解决：**

```bash
# 检查数据目录
ls ~/.nanobot-runner/data/

# 确认有导入记录
uv run nanobotrun stats --year 2024
```

#### 4. Agent 无响应

**问题：** `chat` 命令无响应或报错

**解决：**

```bash
# 检查 nanobot-ai 安装
uv pip show nanobot-ai

# 重新安装依赖
uv sync --reinstall
```

---

## 最佳实践

### 1. 定期导入数据

建议每周导入一次新数据，保持数据更新：

```bash
# 每周日导入
uv run nanobotrun import /data/garmin/latest/
```

### 2. 定期生成报告

设置定时任务自动生成周报/月报：

```bash
# 生成周报
uv run nanobotrun report --type weekly

# 生成月报
uv run nanobotrun report --type monthly
```

### 3. 数据备份

定期备份数据目录：

```bash
# 备份数据
cp -r ~/.nanobot-runner/data /backup/$(date +%Y%m%d)/
```

### 4. 日志管理

日志文件会自动轮转，保留最近 5 个备份（每个 10MB）。

---

## 相关文档

- [API 参考文档](../api/analytics_engine.md) - 数据分析引擎 API
- [RunnerTools API](../api/runner_tools.md) - Agent 工具集 API
- [StorageManager API](../api/storage_manager.md) - 存储管理器 API

---

*文档版本: v0.3.0*
*更新时间: 2026-03-17*
