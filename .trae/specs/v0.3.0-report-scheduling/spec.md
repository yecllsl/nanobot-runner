# v0.3.0 迭代晨报推送调度与飞书集成 Spec

## Why

T004 已完成晨报内容生成，现在需要实现晨报推送调度和飞书集成，让用户能够定时接收每日晨报。

## What Changes

- **T005**: 实现晨报推送调度 - **使用 nanobot.cron.CronService** 实现定时调度
- **T006**: 完善飞书晨报推送 - **使用 nanobot.channels.feishu.FeishuChannel** 实现推送

## Impact

- Affected specs: `src/cli.py`, `src/notify/feishu.py`
- Affected code: 
  - `src/cli.py` - 新增 `report` 命令，集成 `nanobot.cron.CronService`
  - `src/notify/feishu.py` - **重构为使用 nanobot 飞书通道** 或保留为兼容层
  - `tests/unit/test_cli.py` - 新增单元测试
  - `tests/unit/test_feishu.py` - 新增单元测试

## nanobot-ai 能力评估（更新）

### ✅ nanobot.cron - 定时任务调度

nanobot-ai 提供了完整的定时任务调度功能：

### ✅ nanobot.channels.feishu - 飞书通道

**重大发现**: nanobot-ai **内置了完整的飞书通道**，支持：
- WebSocket 长连接
- 接收飞书消息
- 发送飞书消息
- 富媒体解析
- 卡片消息

**架构图**:
```
飞书用户/群聊
    ↓
飞书开放平台 (事件 im.message.receive_v1)
    ↓
nanobot FeishuChannel (WebSocket 长连接)
    ↓
MessageBus (Inbound Queue)
    ↓
Agent Loop (ReAct 循环)
    ↓
Memory / Skills / Tools
    ↓
Outbound Queue
    ↓
FeishuChannel
    ↓
飞书用户/群聊
```

**关键点**: nanobot 的飞书通道主要用于**接收消息**，要发送主动推送消息，我们需要：
1. 使用 nanobot 的飞书通道发送消息
2. 或者保留现有的 FeishuBot 作为简化方案（HTTP Webhook）

## ADDED Requirements

### Requirement: 晨报推送调度 (T005)

系统 SHALL 使用 `nanobot.cron.CronService` 实现晨报推送调度功能。

#### Scenario: 即时生成晨报

- **WHEN** 用户执行 `nanobotrun report` 命令
- **THEN** 系统生成当日晨报并显示在终端

#### Scenario: 推送到飞书

- **WHEN** 用户执行 `nanobotrun report --push` 命令
- **THEN** 系统生成晨报并通过飞书通道推送

#### Scenario: 配置定时推送

- **WHEN** 用户执行 `nanobotrun report --schedule 07:00` 命令
- **THEN** 系统使用 `nanobot.cron.CronService` 创建定时任务

---

### Requirement: 飞书晨报推送 (T006)

系统 SHALL 使用 `nanobot.channels.feishu` 或兼容方案实现飞书晨报推送功能。

#### Scenario: 使用 nanobot 飞书通道（推荐）

- **WHEN** 配置了飞书机器人
- **THEN** 使用 `nanobot.channels.feishu.FeishuChannel` 发送消息

#### Scenario: 使用 HTTP Webhook（兼容方案）

- **WHEN** 未配置飞书机器人
- **THEN** 使用现有的 `FeishuBot` 通过 HTTP Webhook 发送消息

## MODIFIED Requirements

无（新增功能）

## REMOVED Requirements

无

## 任务依赖关系

```
T004 (晨报内容生成) ✅ 已完成
    ↓
    ├── T005 (晨报推送调度) ← 使用 nanobot.cron
    └── T006 (飞书晨报推送) ← 使用 nanobot.channels.feishu 或 FeishuBot
```

**执行顺序**: T005 和 T006 可并行执行

## 技术说明

### 方案 A: 使用 nanobot 飞书通道（推荐）

**优势**:
- WebSocket 长连接，- 支持富媒体、卡片消息
- 与 Agent Loop 集成

**配置示例**:
```json
// ~/.nanobot/config.json
{
  "channels": {
    "feishu": {
      "enabled": true,
      "app_id": "cli_xxx",
      "app_secret": "xxx",
      "encrypt_key": "xxx",
      "verification_token": "xxx"
    }
  }
}
```

### 方案 B: 使用 HTTP Webhook（兼容方案）

**优势**:
- 精简配置
- 无需飞书机器人
- 适合简单推送

**适用场景**: 用户未配置飞书机器人时的降级方案

## CLI 命令设计

```bash
# 即时生成晨报
nanobotrun report

# 推送到飞书
nanobotrun report --push

# 配置定时推送（使用 nanobot.cron）
nanobotrun report --schedule 07:00

# 启用/禁用定时推送
nanobotrun report --enable
nanobotrun report --disable
```
