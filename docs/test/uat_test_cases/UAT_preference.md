# UAT 偏好管理测试用例（UAT-052 ~ UAT-055）

> **返回精简版指南**: [../用户验收测试指南.md](../用户验收测试指南.md)

---

## UAT-052: 查看当前偏好

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证 `preference show` 命令功能 |
| **前置条件** | 已完成环境初始化 |
| **执行命令** | `uv run nanobotrun preference show` |
| **预期结果** | 退出码为0，输出包含当前用户偏好设置（训练时段、强度、沟通风格等） |
| **优先级** | P1 |

**自动化判定规则**:
```json
{
  "pass_condition": "exit_code == 0 AND (stdout contains '当前用户偏好' OR stdout contains '训练时段')",
  "fail_condition": "exit_code != 0 OR stdout contains '错误:' OR stdout contains '失败'"
}
```

**结果记录**:
- [ ] 通过 / [ ] 失败
- 训练时段: _____
- 训练强度: _____
- 沟通风格: _____
- 异常信息（如失败）: _____

---

## UAT-053: 设置偏好

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证 `preference set` 命令功能 |
| **前置条件** | UAT-052 已通过 |
| **执行命令** | 1. `uv run nanobotrun preference set training_time morning` 2. `uv run nanobotrun preference set training_intensity high` |
| **预期结果** | 退出码为0，输出包含"偏好已更新" |
| **优先级** | P1 |

**自动化判定规则**:
```json
{
  "pass_condition": "exit_code == 0 AND stdout contains '偏好已更新'",
  "fail_condition": "exit_code != 0 OR stdout contains '错误:' OR stdout contains '失败'"
}
```

**结果记录**:
- [ ] 通过 / [ ] 失败
- 设置字段1: _____ = _____
- 设置字段2: _____ = _____
- 异常信息（如失败）: _____

---

## UAT-054: 重置偏好

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证 `preference reset` 命令功能 |
| **前置条件** | UAT-053 已通过（偏好已修改） |
| **执行命令** | `uv run nanobotrun preference reset` |
| **预期结果** | 退出码为0，输出包含"偏好已重置为默认值" |
| **优先级** | P1 |

**自动化判定规则**:
```json
{
  "pass_condition": "exit_code == 0 AND stdout contains '偏好已重置为默认值'",
  "fail_condition": "exit_code != 0 OR stdout contains '错误:' OR stdout contains '失败'"
}
```

**结果记录**:
- [ ] 通过 / [ ] 失败
- 重置后偏好摘要: _____
- 异常信息（如失败）: _____

---

## UAT-055: 反馈统计

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证 `preference feedback-stats` 命令功能 |
| **前置条件** | 已完成环境初始化 |
| **执行命令** | `uv run nanobotrun preference feedback-stats` |
| **预期结果** | 退出码为0，输出包含反馈统计数据（总反馈数、正/负/中性反馈等） |
| **优先级** | P1 |

**自动化判定规则**:
```json
{
  "pass_condition": "exit_code == 0 AND (stdout contains '反馈统计' OR stdout contains '总反馈数')",
  "fail_condition": "exit_code != 0 OR stdout contains '错误:' OR stdout contains '失败'"
}
```

**结果记录**:
- [ ] 通过 / [ ] 失败
- 总反馈数: _____
- 正面反馈: _____
- 负面反馈: _____
- 异常信息（如失败）: _____
