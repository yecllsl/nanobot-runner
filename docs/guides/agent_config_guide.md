# Agent 配置指南

## 1. 概述

本指南介绍如何配置 Nanobot Runner 的 Agent 系统，包括人格设定、行为准则和记忆系统。

## 2. 配置文件结构

### 2.1 目录结构

```
~/.nanobot-runner/
├── AGENTS.md          # Agent行为准则
├── SOUL.md            # 人格设定
├── USER.md            # 用户画像
├── config.json        # 应用配置
├── memory/
│   ├── MEMORY.md      # 长期记忆
│   └── HISTORY.md     # 事件日志
└── data/
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

```json
{
  "data_dir": "~/.nanobot-runner/data",
  "default_year": 2024,
  "timezone": "Asia/Shanghai"
}
```

### 4.2 配置项说明

| 配置项 | 类型 | 说明 |
|--------|------|------|
| `data_dir` | string | 数据存储目录 |
| `default_year` | int | 默认查询年份 |
| `timezone` | string | 时区设置 |

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
