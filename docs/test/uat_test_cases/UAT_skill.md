# UAT 技能管理测试用例（UAT-056 ~ UAT-060）

> **返回精简版指南**: [../用户验收测试指南.md](../用户验收测试指南.md)

---

## UAT-056: 技能列表

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证 `skill list` 命令功能 |
| **前置条件** | 已完成环境初始化 |
| **执行命令** | `uv run nanobotrun skill list` |
| **预期结果** | 退出码为0，输出包含技能列表（名称、版本、描述、状态） |
| **优先级** | P1 |

**自动化判定规则**:
```json
{
  "pass_condition": "exit_code == 0 AND (stdout contains '可用技能列表' OR stdout contains '未发现任何技能')",
  "fail_condition": "exit_code != 0 OR stdout contains '错误:' OR stdout contains '失败'"
}
```

**结果记录**:
- [ ] 通过 / [ ] 失败
- 技能数量: _____
- 启用数量: _____
- 技能列表摘要: _____
- 异常信息（如失败）: _____

---

## UAT-057: 启用技能

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证 `skill enable` 命令功能 |
| **前置条件** | UAT-056 已通过（存在可用技能） |
| **执行命令** | `uv run nanobotrun skill enable <skill_name>` |
| **预期结果** | 退出码为0，输出包含"技能已启用" |
| **优先级** | P1 |

**自动化判定规则**:
```json
{
  "pass_condition": "exit_code == 0 AND stdout contains '技能已启用'",
  "fail_condition": "exit_code != 0 OR stdout contains '错误:' OR stdout contains '失败'"
}
```

**结果记录**:
- [ ] 通过 / [ ] 失败
- 技能名称: _____
- 实际输出: _____
- 异常信息（如失败）: _____

---

## UAT-058: 禁用技能

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证 `skill disable` 命令功能 |
| **前置条件** | UAT-057 已通过（技能已启用） |
| **执行命令** | `uv run nanobotrun skill disable <skill_name>` |
| **预期结果** | 退出码为0，输出包含"技能已禁用" |
| **优先级** | P1 |

**自动化判定规则**:
```json
{
  "pass_condition": "exit_code == 0 AND stdout contains '技能已禁用'",
  "fail_condition": "exit_code != 0 OR stdout contains '错误:' OR stdout contains '失败'"
}
```

**结果记录**:
- [ ] 通过 / [ ] 失败
- 技能名称: _____
- 实际输出: _____
- 异常信息（如失败）: _____

---

## UAT-059: 导入技能

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证 `skill import` 命令功能 |
| **前置条件** | 已准备有效的技能目录 |
| **执行命令** | `uv run nanobotrun skill import <skill_path>` |
| **预期结果** | 退出码为0，输出包含"技能导入成功" |
| **优先级** | P1 |

**说明**: 此测试仅在存在有效技能目录时执行。若无技能目录，标记为"不适用"。

**自动化判定规则**:
```json
{
  "pass_condition": "exit_code == 0 AND stdout contains '技能导入成功'",
  "fail_condition": "exit_code != 0 OR stdout contains '错误:' OR stdout contains '失败'",
  "skip_condition": "技能目录不存在"
}
```

**结果记录**:
- [ ] 通过 / [ ] 失败 / [ ] 不适用
- 技能路径: _____
- 实际输出: _____
- 异常信息（如失败）: _____

---

## UAT-060: 技能详情

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证 `skill show` 命令功能 |
| **前置条件** | UAT-056 已通过（存在可用技能） |
| **执行命令** | `uv run nanobotrun skill show <skill_name>` |
| **预期结果** | 退出码为0，输出包含技能详细信息（名称、版本、描述、标签、依赖、工具） |
| **优先级** | P1 |

**自动化判定规则**:
```json
{
  "pass_condition": "exit_code == 0 AND (stdout contains '技能' OR stdout contains '版本')",
  "fail_condition": "exit_code != 0 OR stdout contains '错误:' OR stdout contains '失败'"
}
```

**结果记录**:
- [ ] 通过 / [ ] 失败
- 技能名称: _____
- 技能版本: _____
- 技能描述: _____
- 异常信息（如失败）: _____
