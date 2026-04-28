# UAT 数据导入与查询测试用例（UAT-001 ~ UAT-008）

> **返回精简版指南**: [../用户验收测试指南.md](../用户验收测试指南.md)

---

## UAT-001: 单文件导入

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证 FIT 文件导入功能 |
| **前置条件** | 已初始化环境，已准备有效 FIT 文件 |
| **执行命令** | `uv run nanobotrun data import "<fit文件路径>"` |
| **预期结果** | 退出码为0，输出包含"导入成功"或"✓" |
| **优先级** | P0 |

**自动化判定规则**:
```json
{
  "pass_condition": "exit_code == 0 AND (stdout contains '导入成功' OR stdout contains '✓')",
  "fail_condition": "exit_code != 0 OR stdout contains '导入失败' OR stdout contains '错误:'"
}
```

**结果记录**:
- [ ] 通过 / [ ] 失败
- 文件路径: _____
- 导入耗时: _____秒
- 异常信息（如失败）: _____

---

## UAT-002: 批量导入

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证批量导入功能 |
| **前置条件** | 已准备包含多个 FIT 文件的目录（≥10个） |
| **执行命令** | `uv run nanobotrun data import "<包含多个FIT文件的目录>"` |
| **预期结果** | 退出码为0，输出包含"导入完成"或"成功:"，显示导入统计信息 |
| **优先级** | P0 |

**自动化判定规则**:
```json
{
  "pass_condition": "exit_code == 0 AND stdout contains '导入完成' AND stdout contains '成功:'",
  "fail_condition": "exit_code != 0 OR stdout contains '导入失败' OR stdout contains '错误:'"
}
```

**结果记录**:
- [ ] 通过 / [ ] 失败
- 文件总数: _____
- 成功导入数: _____
- 跳过数: _____
- 失败数: _____
- 导入耗时: _____秒
- 异常信息（如失败）: _____

---

## UAT-003: 数据去重

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证重复文件导入时的去重机制 |
| **前置条件** | UAT-001 已通过（已导入至少一个文件） |
| **执行命令** | `uv run nanobotrun data import "<已导入的FIT文件>"` |
| **预期结果** | 退出码为0，输出包含"跳过"或"已存在"或"重复" |
| **优先级** | P0 |

**自动化判定规则**:
```json
{
  "pass_condition": "exit_code == 0 AND (stdout contains '跳过' OR stdout contains '已存在' OR stdout contains '重复')",
  "fail_condition": "exit_code != 0 OR stdout contains '错误:'"
}
```

**结果记录**:
- [ ] 通过 / [ ] 失败
- 去重提示信息: _____
- 异常信息（如失败）: _____

---

## UAT-004: 强制重新导入

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证强制重新导入功能 |
| **前置条件** | UAT-003 已通过（文件已导入） |
| **执行命令** | `uv run nanobotrun data import "<已导入的FIT文件>" --force` |
| **预期结果** | 退出码为0，输出包含"导入成功"或"覆盖" |
| **优先级** | P1 |

**自动化判定规则**:
```json
{
  "pass_condition": "exit_code == 0 AND (stdout contains '导入成功' OR stdout contains '覆盖')",
  "fail_condition": "exit_code != 0 OR stdout contains '错误:'"
}
```

**结果记录**:
- [ ] 通过 / [ ] 失败
- 实际输出: _____
- 异常信息（如失败）: _____

---

## UAT-005: 异常文件处理

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证异常文件导入时的错误处理 |
| **前置条件** | 已准备异常文件（空文件、损坏文件、非 FIT 文件） |
| **执行命令** | `uv run nanobotrun data import "<异常文件路径>"` |
| **预期结果** | 退出码为1，输出包含"错误:"和"建议:" |
| **优先级** | P1 |

**自动化判定规则**:
```json
{
  "pass_condition": "exit_code == 1 AND stdout contains '错误:' AND stdout contains '建议:'",
  "fail_condition": "exit_code == 0 OR (exit_code == 1 AND NOT stdout contains '错误:')"
}
```

**结果记录**:
- [ ] 通过 / [ ] 失败
- 异常文件类型: _____
- 错误信息: _____
- 建议信息: _____
- 异常信息（如失败）: _____

---

## UAT-006: 当前年份统计

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证当前年份数据统计功能 |
| **前置条件** | 已导入当前年份的 FIT 文件（≥5个） |
| **执行命令** | `uv run nanobotrun data stats` |
| **预期结果** | 退出码为0，输出包含统计信息（总距离、总时长、总次数等） |
| **优先级** | P0 |

**自动化判定规则**:
```json
{
  "pass_condition": "exit_code == 0 AND stdout contains '[Stats] 统计信息' AND stdout contains '总距离' AND stdout contains '总时长'",
  "fail_condition": "exit_code != 0 OR stdout contains '错误:' OR stdout is empty"
}
```

**结果记录**:
- [ ] 通过 / [ ] 失败
- 总距离: _____ km
- 总时长: _____
- 总次数: _____
- 异常信息（如失败）: _____

---

## UAT-007: 指定年份统计

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证指定年份数据统计功能 |
| **前置条件** | 已导入指定年份的 FIT 文件 |
| **执行命令** | `uv run nanobotrun data stats --year 2024` |
| **预期结果** | 退出码为0，输出包含指定年份的统计信息 |
| **优先级** | P0 |

**自动化判定规则**:
```json
{
  "pass_condition": "exit_code == 0 AND stdout contains '2024' AND stdout contains '统计信息'",
  "fail_condition": "exit_code != 0 OR stdout contains '错误:'"
}
```

**结果记录**:
- [ ] 通过 / [ ] 失败
- 指定年份: _____
- 统计信息摘要: _____
- 异常信息（如失败）: _____

---

## UAT-008: 日期范围过滤

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证日期范围过滤功能 |
| **前置条件** | 已导入跨多个日期的 FIT 文件 |
| **执行命令** | `uv run nanobotrun data stats --start 2024-01-01 --end 2024-03-31` |
| **预期结果** | 退出码为0，输出包含指定日期范围的统计信息 |
| **优先级** | P0 |

**自动化判定规则**:
```json
{
  "pass_condition": "exit_code == 0 AND stdout contains '统计信息' AND stdout contains '2024-01'",
  "fail_condition": "exit_code != 0 OR stdout contains '错误:'"
}
```

**结果记录**:
- [ ] 通过 / [ ] 失败
- 日期范围: _____
- 统计信息摘要: _____
- 异常信息（如失败）: _____
