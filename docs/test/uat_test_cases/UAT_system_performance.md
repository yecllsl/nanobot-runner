# UAT 系统管理与性能测试用例（UAT-021 ~ UAT-027）

> **返回精简版指南**: [../用户验收测试指南.md](../用户验收测试指南.md)

---

## UAT-021: 配置验证

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证配置有效性检查 |
| **前置条件** | 已完成初始化 |
| **执行命令** | `uv run nanobotrun system validate` |
| **预期结果** | 退出码为0，输出包含"配置验证通过"或"✓" |
| **优先级** | P1 |

**自动化判定规则**:
```json
{
  "pass_condition": "exit_code == 0 AND (stdout contains '配置验证通过' OR stdout contains '✓')",
  "fail_condition": "exit_code == 1 OR stdout contains '✗ 配置验证失败' OR stdout contains '错误:'"
}
```

**结果记录**:
- [ ] 通过 / [ ] 失败
- 验证结果: _____
- 耗时: _____秒
- 异常信息（如失败）: _____

---

## UAT-022: 数据迁移

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证从旧版本配置迁移功能 |
| **前置条件** | 存在旧版本 nanobot 配置（~/.nanobot/config.json） |
| **执行命令** | `uv run nanobotrun system init --force --skip-optional` |
| **预期结果** | 退出码为0，输出包含"初始化完成"或"配置验证通过" |
| **优先级** | P1 |

**说明**: 此测试仅在存在旧版本配置时执行。若无旧配置，标记为"不适用"。

**自动化判定规则**:
```json
{
  "pass_condition": "exit_code == 0 AND (stdout contains '初始化完成' OR stdout contains '配置验证通过')",
  "fail_condition": "exit_code == 1 OR stdout contains '初始化失败' OR stdout contains '错误:'"
}
```

**结果记录**:
- [ ] 通过 / [ ] 失败 / [ ] 不适用
- 验证结果: _____
- 耗时: _____秒
- 异常信息（如失败）: _____

---

## UAT-023: 启动 Agent 对话

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证 AI 助手交互功能 |
| **前置条件** | 已配置 LLM API 密钥（NANOBOT_LLM_API_KEY） |
| **执行命令** | `uv run nanobotrun agent chat` |
| **预期结果** | Agent 正常启动，显示欢迎信息，进入交互模式 |
| **验收方式** | 人工观察 |
| **优先级** | P1 |

**人工验收要点**:
- [ ] Agent 能正常启动并显示欢迎信息
- [ ] 输入简单问题能得到相关回答
- [ ] 无报错或异常退出
- [ ] 对话流畅，回答准确

**结果记录**:
- [ ] 通过 / [ ] 失败
- 启动耗时: _____秒
- 异常信息（如失败）: _____

---

## UAT-024: 自然语言查询

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证自然语言数据查询 |
| **前置条件** | 已进入 Agent 对话模式，已导入训练数据 |
| **测试输入** | 1. "我上周跑了多少次？" 2. "我的 VDOT 趋势如何？" 3. "分析我的心率漂移" |
| **预期结果** | Agent 理解查询意图，返回准确数据，调用对应工具 |
| **验收方式** | 人工观察 |
| **优先级** | P1 |

**人工验收要点**:
- [ ] Agent 能理解自然语言查询意图
- [ ] 返回的数据与实际跑步数据一致
- [ ] 回答格式清晰易读
- [ ] 能正确调用数据查询工具

**结果记录**:
- [ ] 通过 / [ ] 失败
- 查询1回答准确性: _____
- 查询2回答准确性: _____
- 查询3回答准确性: _____
- 异常信息（如失败）: _____

---

## UAT-025: 批量导入性能

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证大批量 FIT 文件导入性能 |
| **前置条件** | 已准备≥50个真实 FIT 文件 |
| **测试数据** | 50-100个 FIT 文件（覆盖不同日期、类型） |
| **执行命令** | `uv run nanobotrun data import "<包含50-100个FIT文件的目录>"` |
| **预期结果** | 退出码为0，全部导入成功，耗时<60秒 |
| **性能要求** | 50个文件<30秒，100个文件<60秒 |
| **优先级** | P1 |

**自动化判定规则**:
```json
{
  "pass_condition": "exit_code == 0 AND stdout contains '导入完成' AND stdout contains '成功:'",
  "performance_check_50": "duration < 30s (50 files)",
  "performance_check_100": "duration < 60s (100 files)",
  "fail_condition": "exit_code != 0 OR '成功:' count == 0 OR duration exceeds limit"
}
```

**结果记录**:
- [ ] 通过 / [ ] 失败
- 文件总数: _____
- 成功导入数: _____
- 耗时: _____秒
- 平均单文件耗时: _____秒
- 异常信息（如失败）: _____

---

## UAT-026: 数据查询性能

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证大数据量下查询性能 |
| **前置条件** | 已导入≥100个 FIT 文件 |
| **执行命令** | `uv run nanobotrun data stats` |
| **预期结果** | 退出码为0，输出统计信息，耗时<3秒 |
| **性能要求** | 100条记录<2秒，500条记录<5秒 |
| **优先级** | P1 |

**自动化判定规则**:
```json
{
  "pass_condition": "exit_code == 0 AND stdout contains '[Stats] 统计信息'",
  "performance_check_100": "duration < 2s (100 records)",
  "performance_check_500": "duration < 5s (500 records)",
  "fail_condition": "exit_code != 0 OR duration exceeds limit"
}
```

**结果记录**:
- [ ] 通过 / [ ] 失败
- 数据记录总数: _____
- 耗时: _____秒
- 异常信息（如失败）: _____

---

## UAT-027: 报告生成性能

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证报告生成性能 |
| **前置条件** | 已导入≥50个 FIT 文件 |
| **执行命令** | `uv run nanobotrun report weekly` |
| **预期结果** | 退出码为0，输出周报，耗时<5秒 |
| **性能要求** | 周报<5秒，月报<8秒 |
| **优先级** | P1 |

**自动化判定规则**:
```json
{
  "pass_condition": "exit_code == 0 AND (stdout contains '[Weekly] 周报' OR stdout contains '周报')",
  "performance_check_weekly": "duration < 5s",
  "performance_check_monthly": "duration < 8s",
  "fail_condition": "exit_code != 0 OR duration exceeds limit"
}
```

**结果记录**:
- [ ] 通过 / [ ] 失败
- 报告类型: _____
- 耗时: _____秒
- 异常信息（如失败）: _____
