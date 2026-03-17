# Tasks

## 晨报推送调度与飞书集成任务

---

### Task 1: T005 - 实现晨报推送调度（使用 nanobot.cron）

**负责模块**: `src/cli.py`  
**预估工时**: 4h  
**优先级**: P0  
**前置依赖**: T004 ✅ 已完成

**任务描述**:
使用 `nanobot.cron.CronService` 实现晨报推送调度，支持即时生成和定时推送。

**实现步骤**:
- [x] SubTask 1.1: 在 `src/cli.py` 中添加 `report` 命令
- [x] SubTask 1.2: 集成 `nanobot.cron.CronService` 实现定时调度
- [x] SubTask 1.3: 实现 `--push` 参数，支持推送到飞书
- [x] SubTask 1.4: 实现 `--schedule` 参数，配置推送时间
- [x] SubTask 1.5: 实现 `--enable/--disable` 参数，启用/禁用定时推送
- [x] SubTask 1.6: 编写单元测试，覆盖率 ≥ 80%

**验收标准**:
- [x] 实现 `report` 命令
- [x] 使用 `nanobot.cron.CronService` 实现定时调度
- [x] 支持配置推送时间
- [x] 支持启用/禁用推送
- [x] 推送时间准确 (误差 < 1 分钟)
- [x] 单元测试覆盖率 ≥ 80%

---

### Task 2: T006 - 完善飞书晨报推送（使用 nanobot 飞书通道或 HTTP Webhook）

**负责模块**: `src/notify/feishu.py`  
**预估工时**: 3h  
**优先级**: P0  
**前置依赖**: T004 ✅ 已完成

**任务描述**:
实现飞书晨报推送功能，支持两种方案：
- **方案 A（推荐）**: 使用 `nanobot.channels.feishu.FeishuChannel` 发送消息
- **方案 B（兼容）**: 使用现有 `FeishuBot` 通过 HTTP Webhook 发送消息

**实现步骤**:
- [x] SubTask 2.1: 检测是否配置了飞书机器人（nanobot config）
- [x] SubTask 2.2: 如果配置了飞书机器人，使用 `nanobot.channels.feishu` 发送消息
- [x] SubTask 2.3: 如果未配置，使用现有 `FeishuBot` 通过 HTTP Webhook 发送消息
- [x] SubTask 2.4: 完善 `send_daily_report()` 方法，使用飞书卡片消息格式
- [x] SubTask 2.5: 添加推送失败重试机制（最多 3 次）
- [x] SubTask 2.6: 编写单元测试,覆盖率 ≥ 85%

**验收标准**:
- [x] 支持两种推送方案（nanobot 飞书通道 / HTTP Webhook）
- [x] 消息格式正确 (飞书卡片消息)
- [x] 推送失败重试机制（最多 3 次）
- [x] Webhook 未配置时返回友好提示
- [x] 单元测试覆盖率 ≥ 85%

---

# Task Dependencies
**无依赖关系** - T005 和 T006 可并行执行

```
T004 (晨报内容生成) ✅ 已完成
    ↓
    ├── T005 (晨报推送调度) ✅ 已完成
    └── T006 (飞书晨报推送) ✅ 已完成
```
---

# 执行说明
**执行智能体**: 开发工程师智能体  
**执行指令**: DEV-05 功能迭代  
**执行方式**: 并行执行 T005 和 T006  
**预计总工时**: 7 小时

**执行结果**:
- T005: ✅ 完成（覆盖率 94%）
- T006: ✅ 完成（覆盖率 96%）
