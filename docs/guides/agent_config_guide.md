# Agent 配置指南

## 1. 概述

本指南介绍如何配置 Nanobot Runner 的 Agent 系统，包括人格设定、行为准则和记忆系统。

## 2. 配置文件结构

### 2.1 目录结构

**v0.9.4 更新**: 配置文件结构已扩展，支持环境变量配置和备份管理。

```
~/.nanobot-runner/
├── AGENTS.md          # Agent行为准则
├── SOUL.md            # 人格设定
├── USER.md            # 用户画像
├── config.json        # 应用配置
├── .env.local         # 环境变量配置（v0.9.4 新增）
├── backups/           # 配置备份目录（v0.9.4 新增）
│   └── backup_YYYYMMDD_HHMMSS/
│       ├── backup_info.json
│       └── config.json
├── memory/
│   ├── MEMORY.md      # 长期记忆
│   └── HISTORY.md     # 事件日志
└── data/
    ├── activities_*.parquet
    └── profile.json   # 结构化画像数据
```

### 2.2 配置分离原则

| 类型 | 位置 | 说明 |
|------|------|------|
| LLM Provider | `~/.nanobot/config.json` | 框架级配置 |
| 飞书通道 | `~/.nanobot/config.json` | 框架级配置 |
| Agent行为 | `~/.nanobot-runner/AGENTS.md` | 业务配置 |
| 人格设定 | `~/.nanobot-runner/SOUL.md` | 业务配置 |
| 用户画像 | `~/.nanobot-runner/USER.md` | 业务配置 |
| 环境变量 | `~/.nanobot-runner/.env.local` | 敏感配置（v0.9.4 新增） |
| 配置备份 | `~/.nanobot-runner/backups/` | 自动备份（v0.9.4 新增） |

## 3. 核心配置文件

### 3.1 AGENTS.md - 行为准则

定义 Agent 的工作方式和行为规范：

```markdown
# AGENTS.md

Agent 工作指南 - Nanobot Runner

## 核心栈
Python 3.11+, nanobot-ai, Typer+Rich CLI, Polars, Parquet, fitparse

## 常用命令
- 依赖管理: uv venv, uv sync --all-extras
- 运行: uv run nanobotrun --help
- 测试: uv run pytest
- 代码质量: ruff format, ruff check, mypy, bandit

## 代码风格
- 导入顺序: 标准库 → 第三方库 → 本地模块
- 命名约定: PascalCase(类), snake_case(函数/变量)
- 类型注解: 新代码必须添加类型注解
```

### 3.2 SOUL.md - 人格设定

定义 Agent 的性格和交互风格：

```markdown
# SOUL.md

## 身份
你是一个专业的跑步助理 AI，专注于帮助用户管理和分析跑步数据。

## 性格特点
- 专业严谨：提供准确的数据分析
- 友好亲切：以鼓励的方式与用户交流
- 主动建议：根据数据提供训练建议

## 交互风格
- 使用简洁清晰的语言
- 优先展示关键数据
- 提供可操作的建议
```

### 3.3 USER.md - 用户画像

存储用户的基本信息和偏好：

```markdown
# USER.md

## 基本信息
- 跑步目标: 提高马拉松成绩
- 训练频率: 每周3-4次
- 当前水平: 中级跑者

## 偏好设置
- 语言: 中文
- 配速单位: 分/公里
- 距离单位: 公里
```

## 4. 应用配置

### 4.1 config.json 结构

**v0.9.4 更新**: 配置结构已扩展，支持更多配置项。
**v0.16.0 更新**: 配置管理已迁移至 `src.core.config` 模块。

```json
{
  "version": "0.16.0",
  "data_dir": "~/.nanobot-runner/data",
  "default_year": 2024,
  "timezone": "Asia/Shanghai",
  "llm_provider": "anthropic",
  "llm_model": "claude-3-5-sonnet-20241022",
  "enable_feishu": false,
  "user_profile": {
    "height_cm": 175,
    "weight_kg": 70,
    "resting_hr": 60,
    "max_hr": 190,
    "weekly_mileage_km": 50
  }
}
```

### 4.2 配置项说明

| 配置项 | 类型 | 说明 | 版本 |
|--------|------|------|------|
| `version` | string | 配置文件版本 | v0.9.4 |
| `data_dir` | string | 数据存储目录 | - |
| `default_year` | int | 默认查询年份 | - |
| `timezone` | string | 时区设置 | - |
| `llm_provider` | string | LLM提供商 | v0.9.4 |
| `llm_model` | string | LLM模型 | v0.9.4 |
| `enable_feishu` | bool | 启用飞书集成 | v0.9.4 |
| `user_profile` | object | 用户身体参数 | v0.9.4 |

### 4.3 环境变量配置 (.env.local)

**v0.9.4 新增**: 敏感配置可通过 `.env.local` 文件管理。

```bash
# LLM API Key
NANOBOT_LLM_API_KEY=sk-your-api-key

# 飞书配置（可选）
NANOBOT_FEISHU_APP_ID=cli_xxx
NANOBOT_FEISHU_APP_SECRET=xxx
NANOBOT_FEISHU_RECEIVE_ID=ou_xxx
```

**配置优先级**: 环境变量 > 配置文件 > 默认值

### 4.4 配置验证

**v0.9.4 新增**: 使用 `nanobotrun system validate` 验证配置。

```bash
# 验证配置
uv run nanobotrun system validate

# 预期输出
✅ 配置格式验证通过
✅ 配置完整性验证通过
✅ 配置有效性验证通过
✅ 配置一致性验证通过
```

### 4.5 配置备份与恢复

**v0.9.4 新增**: 支持配置自动备份和手动恢复。

```bash
# 创建备份
uv run nanobotrun system backup

# 查看备份列表
uv run nanobotrun system backup --list

# 恢复备份
uv run nanobotrun system restore --backup-id backup_20260418_120000
```

## 5. 记忆系统

### 5.1 MEMORY.md - 长期记忆

存储用户的长期信息和重要事件：

```markdown
# MEMORY.md

## 用户画像
- PB记录: 全马 3:45:00 (2024-03)
- 目标配速: 5:15/km

## 重要事件
- 2024-03: 完成首个全马
- 2024-06: 开始系统训练

## 训练偏好
- 喜欢晨跑
- 偏好节奏跑训练
```

### 5.2 记忆更新机制

- **自动更新**：Agent 在对话中自动提取关键信息
- **手动更新**：用户可以直接编辑 MEMORY.md
- **定期清理**：建议每月整理一次记忆内容

## 6. 工具配置

### 6.1 RunnerTools 工具集

| 工具名称 | 功能描述 |
|---------|---------|
| `get_running_stats` | 获取跑步统计 |
| `get_recent_runs` | 获取最近记录 |
| `calculate_vdot_for_run` | 计算VDOT值 |
| `get_training_load` | 获取训练负荷 |
| `get_hr_drift_analysis` | 心率漂移分析 |

### 6.2 工具参数配置

工具参数遵循 OpenAI Function Calling 规范：

```json
{
  "name": "get_running_stats",
  "parameters": {
    "type": "object",
    "properties": {
      "year": {
        "type": "integer",
        "description": "查询年份，默认当前年份"
      }
    }
  }
}
```

## 7. 飞书通知配置

### 7.1 飞书应用配置

1. 在飞书开放平台创建企业自建应用
2. 获取 App ID 和 App Secret
3. 配置到 `config.json`:

```json
{
  "feishu_app_id": "your_app_id",
  "feishu_app_secret": "your_app_secret",
  "feishu_receive_id": "your_user_id"
}
```

### 7.2 通知触发条件

- 训练计划完成提醒
- 里程碑达成通知
- 异常数据警告

## 8. 最佳实践

### 8.1 配置管理

- 定期备份配置文件
- 使用版本控制管理配置变更
- 敏感信息使用环境变量

### 8.2 记忆系统维护

- 定期清理过时信息
- 保持记忆内容简洁
- 重要信息及时更新

### 8.3 性能优化

- 合理设置数据查询范围
- 使用缓存减少重复计算
- 定期清理历史数据

---

**文档版本**: v0.9.3  
**最后更新**: 2026-04-15  
**关联文档**: [CLI使用指南](./cli_usage.md)
