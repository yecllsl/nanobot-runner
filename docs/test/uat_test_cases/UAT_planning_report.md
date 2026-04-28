# UAT 训练计划与报告测试用例（UAT-015 ~ UAT-020）

> **返回精简版指南**: [../用户验收测试指南.md](../用户验收测试指南.md)

---

## UAT-015: 智能训练建议

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证智能训练建议功能 |
| **前置条件** | 已导入训练数据，已创建训练计划 |
| **执行命令** | `uv run nanobotrun plan advice <plan_id>` |
| **预期结果** | 退出码为0，输出包含训练建议和风险提示 |
| **优先级** | P0 |

**自动化判定规则**:
```json
{
  "pass_condition": "exit_code == 0 AND stdout contains '建议' AND stdout contains '风险'",
  "fail_condition": "exit_code != 0 OR stdout contains '错误:' OR stdout is empty"
}
```

**结果记录**:
- [ ] 通过 / [ ] 失败
- 计划 ID: _____
- 建议摘要: _____
- 风险提示: _____
- 异常信息（如失败）: _____

---

## UAT-016: 目标达成评估

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证目标达成评估功能 |
| **前置条件** | 已导入训练数据，已设定目标 |
| **执行命令** | `uv run nanobotrun plan evaluate <plan_id>` |
| **预期结果** | 退出码为0，输出包含达成概率和置信区间 |
| **优先级** | P0 |

**自动化判定规则**:
```json
{
  "pass_condition": "exit_code == 0 AND stdout contains '达成概率' AND stdout contains '置信区间'",
  "fail_condition": "exit_code != 0 OR stdout contains '错误:' OR stdout is empty"
}
```

**结果记录**:
- [ ] 通过 / [ ] 失败
- 计划 ID: _____
- 达成概率: _____
- 置信区间: _____
- 异常信息（如失败）: _____

---

## UAT-017: 长期周期规划

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证长期周期规划功能 |
| **前置条件** | 已导入训练数据 |
| **执行命令** | `uv run nanobotrun plan long-term <distance> <target_date>` |
| **预期结果** | 退出码为0，输出包含多周期训练计划 |
| **优先级** | P0 |

**自动化判定规则**:
```json
{
  "pass_condition": "exit_code == 0 AND stdout contains '周期' AND stdout contains '基础期'",
  "fail_condition": "exit_code != 0 OR stdout contains '错误:' OR stdout is empty"
}
```

**结果记录**:
- [ ] 通过 / [ ] 失败
- 目标距离: _____
- 目标日期: _____
- 周期数量: _____
- 异常信息（如失败）: _____

---

## UAT-018: 周报生成

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证周报生成功能 |
| **前置条件** | 已导入本周训练数据 |
| **执行命令** | `uv run nanobotrun report generate --type weekly` |
| **预期结果** | 退出码为0，输出包含周报内容 |
| **优先级** | P0 |

**自动化判定规则**:
```json
{
  "pass_condition": "exit_code == 0 AND (stdout contains '周报' OR stdout contains 'Weekly')",
  "fail_condition": "exit_code != 0 OR stdout contains '错误:' OR stdout is empty"
}
```

**结果记录**:
- [ ] 通过 / [ ] 失败
- 周报内容摘要: _____
- 异常信息（如失败）: _____

---

## UAT-019: 月报生成

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证月报生成功能 |
| **前置条件** | 已导入本月训练数据 |
| **执行命令** | `uv run nanobotrun report generate --type monthly` |
| **预期结果** | 退出码为0，输出包含月报内容 |
| **优先级** | P0 |

**自动化判定规则**:
```json
{
  "pass_condition": "exit_code == 0 AND (stdout contains '月报' OR stdout contains 'Monthly')",
  "fail_condition": "exit_code != 0 OR stdout contains '错误:' OR stdout is empty"
}
```

**结果记录**:
- [ ] 通过 / [ ] 失败
- 月报内容摘要: _____
- 异常信息（如失败）: _____

---

## UAT-020: 报告导出

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证报告导出为文件功能 |
| **前置条件** | UAT-018 或 UAT-019 已通过 |
| **执行命令** | `uv run nanobotrun report generate --type weekly --output report.md` |
| **预期结果** | 退出码为0，指定路径生成 Markdown 文件 |
| **优先级** | P0 |

**自动化判定规则**:
```json
{
  "pass_condition": "exit_code == 0 AND file_exists('report.md') AND file_size > 0",
  "fail_condition": "exit_code != 0 OR NOT file_exists('report.md')"
}
```

**结果记录**:
- [ ] 通过 / [ ] 失败
- 输出文件路径: _____
- 文件大小: _____
- 异常信息（如失败）: _____
