# Checklist

## T005: 晨报推送调度（使用 nanobot.cron）

- [x] `report` 命令已实现
- [x] 使用 `nanobot.cron.CronService` 实现定时调度
- [x] 支持 `--push` 参数推送到飞书
- [x] 支持 `--schedule` 参数配置推送时间
- [x] 支持 `--enable/--disable` 参数启用/禁用定时推送
- [x] 推送时间准确 (误差 < 1 分钟)
- [x] 单元测试覆盖率 ≥ 80%

## T006: 飞书晨报推送（双方案支持）

### 方案 A: nanobot 飞书通道（推荐）
- [x] 检测 nanobot 飞书配置是否存在
- [x] 使用 `nanobot.channels.feishu` 发送消息
- [x] 支持飞书卡片消息格式

### 方案 B: HTTP Webhook（兼容）
- [x] 使用现有 `FeishuBot` 类
- [x] 完善 `send_daily_report()` 方法
- [x] 推送失败重试机制（最多 3 次）
- [x] Webhook 未配置时返回友好提示
- [x] 单元测试覆盖率 ≥ 85%

## 总体验收

- [x] 所有新增代码在 `src/cli.py` 和 `src/notify/feishu.py` 中
- [x] 所有单元测试在 `tests/unit/test_cli.py` 和 `tests/unit/test_feishu.py` 中
- [x] 所有测试通过 (`uv run pytest tests/unit/ -v`)
- [x] 代码格式化通过 (`uv run black src/`)
- [x] 总体覆盖率 ≥ 80%

## 架构符合性验证

- [x] T005 使用 `nanobot.cron.CronService`（符合 nanobot-ai 集成原则）
- [x] T006 支持双方案（nanobot 飞书通道 / HTTP Webhook）
- [x] 无冗余代码
- [x] 正确使用 nanobot-ai 底座能力
