# UAT Cron 训练提醒测试用例（UAT-043 ~ UAT-047）

> **返回精简版指南**: [../用户验收测试指南.md](../用户验收测试指南.md)

---

## UAT-043: 查看训练提醒状态

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证 `cron status` 命令功能 |
| **前置条件** | 已完成环境初始化 |
| **执行命令** | `uv run nanobotrun cron status` |
| **预期结果** | 退出码为0，输出包含"训练提醒配置"、"今日提醒状态" |
| **优先级** | P0 |

**自动化判定规则**:
```json
{
  "pass_condition": "exit_code == 0 AND (stdout contains '训练提醒配置' OR stdout contains '提醒状态')",
  "fail_condition": "exit_code != 0 OR stdout contains '错误:' OR stdout contains '失败'"
}
```

**结果记录**:
- [ ] 通过 / [ ] 失败
- 提醒启用状态: _____
- Cron表达式: _____
- 今日状态: _____
- 异常信息（如失败）: _____

---

## UAT-044: 启用训练提醒

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证 `cron enable` 命令功能 |
| **前置条件** | UAT-043 已通过 |
| **执行命令** | `uv run nanobotrun cron enable --cron "0 7 * * *" --advance 30` |
| **预期结果** | 退出码为0，输出包含"训练提醒已启用"，显示Cron配置 |
| **优先级** | P0 |

**自动化判定规则**:
```json
{
  "pass_condition": "exit_code == 0 AND stdout contains '训练提醒已启用'",
  "fail_condition": "exit_code != 0 OR stdout contains '错误:' OR stdout contains '失败'"
}
```

**结果记录**:
- [ ] 通过 / [ ] 失败
- Cron表达式: _____
- 提前分钟数: _____
- 天气检查: _____
- 异常信息（如失败）: _____

---

## UAT-045: 禁用训练提醒

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证 `cron disable` 命令功能 |
| **前置条件** | UAT-044 已通过（提醒已启用） |
| **执行命令** | `uv run nanobotrun cron disable` |
| **预期结果** | 退出码为0，输出包含"训练提醒已禁用" |
| **优先级** | P0 |

**自动化判定规则**:
```json
{
  "pass_condition": "exit_code == 0 AND stdout contains '训练提醒已禁用'",
  "fail_condition": "exit_code != 0 OR stdout contains '错误:' OR stdout contains '失败'"
}
```

**结果记录**:
- [ ] 通过 / [ ] 失败
- 实际输出: _____
- 异常信息（如失败）: _____

---

## UAT-046: 手动触发训练提醒

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证 `cron trigger` 命令功能 |
| **前置条件** | UAT-044 已通过（提醒已启用），存在今日训练计划 |
| **执行命令** | 1. `uv run nanobotrun cron trigger` 2. `uv run nanobotrun cron trigger --force` |
| **预期结果** | 退出码为0，输出包含触发结果（已发送/无计划/免打扰等） |
| **优先级** | P0 |

**自动化判定规则**:
```json
{
  "pass_condition": "exit_code == 0 AND (stdout contains '训练提醒已发送' OR stdout contains '今日无训练计划' OR stdout contains '免打扰')",
  "fail_condition": "exit_code != 0 OR stdout contains '错误:' OR stdout contains '失败'"
}
```

**结果记录**:
- [ ] 通过 / [ ] 失败
- 触发结果: _____
- 是否强制发送: _____
- 异常信息（如失败）: _____

---

## UAT-047: 查看提醒历史

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证 `cron history` 命令功能 |
| **前置条件** | UAT-046 已执行（有触发记录） |
| **执行命令** | 1. `uv run nanobotrun cron history --days 7` 2. `uv run nanobotrun cron history --clear` |
| **预期结果** | 退出码为0，显示历史记录或清理成功提示 |
| **优先级** | P0 |

**自动化判定规则**:
```json
{
  "pass_condition": "exit_code == 0 AND (stdout contains '天无提醒记录' OR stdout contains '已清理')",
  "fail_condition": "exit_code != 0 OR stdout contains '错误:' OR stdout contains '失败'"
}
```

**结果记录**:
- [ ] 通过 / [ ] 失败
- 历史记录数量: _____
- 清理记录数量: _____
- 异常信息（如失败）: _____
