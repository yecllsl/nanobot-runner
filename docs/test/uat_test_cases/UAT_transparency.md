# UAT AI 透明化测试用例（UAT-048 ~ UAT-051）

> **返回精简版指南**: [../用户验收测试指南.md](../用户验收测试指南.md)

---

## UAT-048: 查看 AI 决策追踪

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证 `transparency show` 命令功能 |
| **前置条件** | 已完成环境初始化，Agent 有过交互记录 |
| **执行命令** | `uv run nanobotrun transparency show --limit 10` |
| **预期结果** | 退出码为0，输出包含决策记录列表（时间、类型、置信度、工具） |
| **优先级** | P1 |

**自动化判定规则**:
```json
{
  "pass_condition": "exit_code == 0 AND (stdout contains '决策记录' OR stdout contains '暂无决策记录')",
  "fail_condition": "exit_code != 0 OR stdout contains '错误:' OR stdout contains '失败'"
}
```

**结果记录**:
- [ ] 通过 / [ ] 失败
- 决策记录数量: _____
- 最新决策时间: _____
- 异常信息（如失败）: _____

---

## UAT-049: 查看决策详情

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证 `transparency show --decision-id` 命令功能 |
| **前置条件** | UAT-048 已通过（有决策记录） |
| **执行命令** | `uv run nanobotrun transparency show --decision-id <id> --level detailed` |
| **预期结果** | 退出码为0，输出包含详细决策路径、数据来源、工具调用 |
| **优先级** | P1 |

**自动化判定规则**:
```json
{
  "pass_condition": "exit_code == 0 AND (stdout contains '决策路径' OR stdout contains '数据来源')",
  "fail_condition": "exit_code != 0 OR stdout contains '错误:' OR stdout contains '失败'"
}
```

**结果记录**:
- [ ] 通过 / [ ] 失败
- 决策 ID: _____
- 决策类型: _____
- 数据来源数量: _____
- 异常信息（如失败）: _____

---

## UAT-050: AI 状态看板

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证 `transparency dashboard` 命令功能 |
| **前置条件** | 已完成环境初始化 |
| **执行命令** | `uv run nanobotrun transparency dashboard` |
| **预期结果** | 退出码为0，输出包含AI状态洞察看板（进化等级、建议质量等） |
| **优先级** | P1 |

**自动化判定规则**:
```json
{
  "pass_condition": "exit_code == 0 AND (stdout contains 'AI状态' OR stdout contains '进化等级')",
  "fail_condition": "exit_code != 0 OR stdout contains '错误:' OR stdout contains '失败'"
}
```

**结果记录**:
- [ ] 通过 / [ ] 失败
- 进化等级: _____
- 建议质量评分: _____
- 异常信息（如失败）: _____

---

## UAT-051: 训练洞察报告

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证 `transparency insight` 命令功能 |
| **前置条件** | 已导入训练数据（≥10个 FIT 文件） |
| **执行命令** | `uv run nanobotrun transparency insight` |
| **预期结果** | 退出码为0，输出包含训练洞察报告（模式分析、恢复趋势等） |
| **优先级** | P1 |

**自动化判定规则**:
```json
{
  "pass_condition": "exit_code == 0 AND (stdout contains '训练洞察' OR stdout contains '训练模式')",
  "fail_condition": "exit_code != 0 OR stdout contains '错误:' OR stdout contains '失败'"
}
```

**结果记录**:
- [ ] 通过 / [ ] 失败
- 训练模式: _____
- 恢复状态: _____
- 洞察摘要: _____
- 异常信息（如失败）: _____
