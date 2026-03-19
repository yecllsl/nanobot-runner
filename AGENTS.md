# AGENTS.md

Agent 工作指南。

## 项目概述

Nanobot Runner - 基于 nanobot-ai 的桌面端私人 AI 跑步助理。通过 Parquet + Polars 实现本地数据隐私与企业级 BI 能力的平衡。

**核心技术栈**: Python 3.11+, nanobot-ai, Typer + Rich (CLI), Polars (计算引擎), Apache Parquet (存储), fitparse (FIT解析)

**当前版本**: 0.3.1

## 常用命令

```bash
# 依赖管理
uv venv                                    # 创建虚拟环境
uv sync --all-extras                       # 同步依赖
uv cache clean; if($?) { uv sync --reinstall }  # 清理重装

# 运行项目
uv run nanobotrun --help
uv run nanobotrun import <path> [--force]  # 导入FIT文件/目录
uv run nanobotrun stats [--year YYYY | --start DATE --end DATE]
uv run nanobotrun chat                     # Agent交互
uv run nanobotrun version

# 测试
uv run pytest                              # 全部测试
uv run pytest tests/{unit,integration,e2e,performance}/
uv run pytest --cov=src --cov-report=term-missing --cov-report=html

# 代码质量
uv run black src tests; uv run isort src tests; uv run mypy src; uv run bandit -r src

# 构建
uv build                                   # 产物在 dist/
```

## 架构

### 目录结构

```
src/
├── core/           # 核心逻辑: parser, storage, indexer, importer, analytics, config, schema, decorators
├── agents/tools.py # Agent工具集 (RunnerTools)
├── notify/feishu.py# 飞书推送 (FeishuBot)
├── cli.py          # CLI入口
└── cli_formatter.py

tests/
├── unit/           # 单元测试
├── integration/{module,scene}/  # 集成测试
├── e2e/            # 端到端测试 (含 v0_2_0/)
├── performance/    # 性能测试
└── data/{fixtures,real_fit_files,validation}/

docs/               # 项目文档
```

### 数据流

- **导入**: FIT → `FitParser` → `IndexManager`(去重) → `StorageManager`(Parquet按年分片)
- **查询**: `StorageManager` → `AnalyticsEngine` → `RunnerTools`
- **通知**: 结果 → `FeishuBot`

### 核心组件

| 组件 | 职责 |
|------|------|
| `ImportService` | 编排导入流程 |
| `AnalyticsEngine` | 数据分析(VDOT/TSS/心率漂移/训练负荷) |
| `RunnerTools` | Agent工具层封装 |
| `StorageManager` | Parquet读写 |
| `ConfigManager` | 配置管理(~/.nanobot-runner/config.json) |
| `ParquetSchema` | 数据结构规范与验证 |
| `decorators` | 通用装饰器(错误处理/存储初始化) |

### 数据存储

**nanobot Workspace 目录结构**：

系统将 `~/.nanobot-runner` 作为 nanobot workspace，遵循 nanobot-ai 标准结构：

```
~/.nanobot-runner/
├── data/                    # 业务数据存储（本项目扩展）
│   ├── activities_*.parquet # 运动数据（按年分片）
│   ├── profile.json         # 结构化画像数据（计算用）
│   ├── plans/               # 训练计划存储
│   │   └── {plan_id}.json
│   └── index.json           # 去重索引（SHA256）
├── memory/                  # 记忆系统（nanobot标准）
│   ├── MEMORY.md            # 长期记忆/用户画像（Agent上下文）
│   └── HISTORY.md           # 事件日志（可搜索历史）
├── sessions/                # 会话历史（nanobot标准）
│   └── feishu_{chat_id}.jsonl
├── skills/                  # 技能扩展（nanobot标准）
│   ├── training_plan/
│   │   └── SKILL.md         # 训练计划生成技能
│   ├── injury_prediction/
│   │   └── SKILL.md         # 伤病风险预警技能
│   └── vdot_prediction/
│       └── SKILL.md         # VDOT预测技能
├── AGENTS.md                # Agent行为准则
├── SOUL.md                  # 人格、价值观、语气风格
├── USER.md                  # 用户画像（辅助）
├── HEARTBEAT.md             # 定时任务
└── config.json              # 应用配置
```

**初始化机制**：

> ⚠️ **重要**：workspace 目录结构由 nanobot-ai 框架自动初始化，无需自定义实现。

当启动 nanobot-runner 应用时，nanobot-ai 框架会检测 `workspace=~/.nanobot-runner` 是否存在或为空，自动创建缺失的标准结构：

| 自动创建的文件/目录 | 说明 |
|-------------------|------|
| `AGENTS.md` | Agent 行为准则模板 |
| `SOUL.md` | 人格、价值观、语气风格 |
| `USER.md` | 用户画像模板 |
| `memory/MEMORY.md` | 长期记忆初始文件 |
| `memory/HISTORY.md` | 事件日志初始文件 |
| `skills/` | 技能目录（如版本默认带） |

**应用需自行创建的目录**：
- `data/`：业务数据存储目录
- `data/plans/`：训练计划存储目录
- `logs/`：日志文件目录

**设计原则**：完全复用 nanobot 的初始化逻辑，避免重复实现。

### Schema 必填字段

`activity_id`, `timestamp`, `source_file`, `filename`, `total_distance`, `total_timer_time`

## 核心功能

### AnalyticsEngine

VDOT计算、TSS计算、跑步摘要统计、心率漂移分析、训练负荷(ATL/CTL)、VDOT趋势

### RunnerTools 工具

`get_running_stats`, `get_recent_runs`, `calculate_vdot_for_run`, `get_vdot_trend`, `get_hr_drift_analysis`, `get_training_load`, `query_by_date_range`, `query_by_distance`

### FeishuBot

`send_text`, `send_card`, `send_import_notification`, `send_daily_report`

### cli_formatter

`format_duration`, `format_pace`, `format_distance`, `format_stats_panel`, `format_runs_table`, `format_vdot_trend`, `format_agent_response`

### decorators

`handle_tool_errors`(异常捕获), `require_storage`(存储初始化), `handle_empty_data`(空数据处理), `validate_date_format`(日期验证)

## 开发注意事项

### 环境

- Python >= 3.11 (nanobot-ai 要求)
- Windows PowerShell 5.1: 用 `; if($?) { cmd }` 替代 `&&`

### Polars

- 读取用 `scan_parquet` (LazyFrame), 写入用 `write_parquet(compression='snappy')`
- 合并用 `pl.concat()`, 相关性用 `pl.corr()`

### FIT文件

Garmin 设备导出，fitparse 解析。测试数据在 `tests/data/`

### Agent工具

新增工具需同时更新 `RunnerTools` 类和 `TOOL_DESCRIPTIONS` 字典

## CI/CD (GitHub Actions)

1. **code-quality**: black, isort, mypy, bandit
2. **test**: pytest (Python 3.11/3.12)
3. **build**: 构建打包
4. **release**: main分支打tag触发

覆盖率上传 Codecov

## 常见问题

```bash
# 依赖问题
uv cache clean; uv sync --reinstall

# Windows 激活失败
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

mypy 配置宽松: `warn_return_any`, `disallow_untyped_defs`, `check_untyped_defs` 均为 false

## 待实现

- [ ] Agent自然语言交互完善
- [ ] TSS/ATL/CTL完整计算
- [ ] 每日晨报自动生成
- [ ] 更多分析指标与可视化
- [ ] 配速字段存储优化
