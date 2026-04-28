# UAT 数据分析测试用例（UAT-009 ~ UAT-014）

> **返回精简版指南**: [../用户验收测试指南.md](../用户验收测试指南.md)

---

## UAT-009: VDOT 趋势分析

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证 VDOT 趋势分析功能 |
| **前置条件** | 已导入包含长距离跑步记录（≥1500m）的 FIT 文件 |
| **执行命令** | `uv run nanobotrun analysis vdot` |
| **预期结果** | 退出码为0，输出包含 VDOT 数值列表和趋势分析 |
| **优先级** | P0 |

**自动化判定规则**:
```json
{
  "pass_condition": "exit_code == 0 AND stdout contains 'VDOT' AND stdout contains '趋势'",
  "fail_condition": "exit_code != 0 OR stdout contains '错误:' OR stdout is empty"
}
```

**结果记录**:
- [ ] 通过 / [ ] 失败
- VDOT 数值列表: _____
- 趋势方向: _____
- 异常信息（如失败）: _____

---

## UAT-010: VDOT 限制输出

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证 VDOT 限制输出条数功能 |
| **前置条件** | UAT-009 已通过 |
| **执行命令** | `uv run nanobotrun analysis vdot --limit 20` |
| **预期结果** | 退出码为0，输出包含≤20条 VDOT 记录 |
| **优先级** | P0 |

**自动化判定规则**:
```json
{
  "pass_condition": "exit_code == 0 AND stdout contains 'VDOT' AND line_count <= 20",
  "fail_condition": "exit_code != 0 OR stdout contains '错误:'"
}
```

**结果记录**:
- [ ] 通过 / [ ] 失败
- 实际输出条数: _____
- 限制值: 20
- 异常信息（如失败）: _____

---

## UAT-011: 训练负荷分析

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证训练负荷分析功能（ATL/CTL/TSB） |
| **前置条件** | 已导入≥10个 FIT 文件 |
| **执行命令** | `uv run nanobotrun analysis load` |
| **预期结果** | 退出码为0，输出包含 ATL、CTL、TSB 数值 |
| **优先级** | P0 |

**自动化判定规则**:
```json
{
  "pass_condition": "exit_code == 0 AND stdout contains 'ATL' AND stdout contains 'CTL' AND stdout contains 'TSB'",
  "fail_condition": "exit_code != 0 OR stdout contains '错误:' OR stdout is empty"
}
```

**结果记录**:
- [ ] 通过 / [ ] 失败
- ATL 值: _____
- CTL 值: _____
- TSB 值: _____
- 异常信息（如失败）: _____

---

## UAT-012: 训练负荷天数

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证指定天数范围的训练负荷分析 |
| **前置条件** | UAT-011 已通过 |
| **执行命令** | `uv run nanobotrun analysis load --days 60` |
| **预期结果** | 退出码为0，输出包含60天的训练负荷数据 |
| **优先级** | P0 |

**自动化判定规则**:
```json
{
  "pass_condition": "exit_code == 0 AND stdout contains 'ATL' AND stdout contains '60天'",
  "fail_condition": "exit_code != 0 OR stdout contains '错误:'"
}
```

**结果记录**:
- [ ] 通过 / [ ] 失败
- 指定天数: 60
- 数据点数量: _____
- 异常信息（如失败）: _____

---

## UAT-013: 心率漂移分析

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证心率漂移分析功能 |
| **前置条件** | 已导入包含心率数据的 FIT 文件 |
| **执行命令** | `uv run nanobotrun analysis hr-drift` |
| **预期结果** | 退出码为0，输出包含相关性系数和漂移判定结果 |
| **优先级** | P0 |

**自动化判定规则**:
```json
{
  "pass_condition": "exit_code == 0 AND stdout contains '心率漂移' AND stdout contains '相关性'",
  "fail_condition": "exit_code != 0 OR stdout contains '错误:' OR stdout is empty"
}
```

**结果记录**:
- [ ] 通过 / [ ] 失败
- 相关性系数: _____
- 漂移判定: _____
- 异常信息（如失败）: _____

---

## UAT-014: 心率漂移判定

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证心率漂移判定逻辑 |
| **前置条件** | 已导入带心率数据的长距离跑步记录 |
| **执行命令** | `uv run nanobotrun analysis hr-drift --activity-id <活动ID>` |
| **预期结果** | 相关性系数<-0.7 判定为漂移，>-0.7 判定为正常 |
| **优先级** | P0 |

**自动化判定规则**:
```json
{
  "pass_condition": "exit_code == 0 AND ( (correlation < -0.7 AND stdout contains '漂移') OR (correlation >= -0.7 AND stdout contains '正常') )",
  "fail_condition": "exit_code != 0 OR stdout contains '错误:'"
}
```

**结果记录**:
- [ ] 通过 / [ ] 失败
- 活动 ID: _____
- 相关性系数: _____
- 判定结果: _____
- 异常信息（如失败）: _____
