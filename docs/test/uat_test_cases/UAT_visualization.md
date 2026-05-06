# UAT 数据可视化测试用例（UAT-061 ~ UAT-065）

> **返回精简版指南**: [../用户验收测试指南.md](../用户验收测试指南.md)

---

## UAT-061: VDOT趋势图

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证终端内VDOT趋势折线图渲染功能 |
| **前置条件** | 已初始化环境，已导入跑步数据（至少包含5条有效VDOT计算数据） |
| **执行命令** | `uv run nanobotrun viz vdot --days 30` |
| **预期结果** | 退出码为0，终端显示VDOT趋势折线图，包含时间轴和VDOT数值 |
| **优先级** | P0 |

**自动化判定规则**:
```json
{
  "pass_condition": "exit_code == 0 AND stdout contains 'VDOT' AND (stdout contains '趋势' OR stdout contains 'chart')",
  "fail_condition": "exit_code != 0 OR stdout contains '错误:' OR stdout contains '无数据'"
}
```

**人工验收要点**:
- [ ] 图表正常渲染，无乱码或错位
- [ ] 时间轴显示清晰（X轴）
- [ ] VDOT数值标注准确（Y轴）
- [ ] 数据点数量与--days参数匹配
- [ ] 图表标题和图例清晰

**结果记录**:
- [ ] 通过 / [ ] 失败
- 数据条数: _____
- 渲染耗时: _____秒
- 异常信息（如失败）: _____

---

## UAT-062: VDOT多时间范围

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证不同时间范围的VDOT趋势图显示 |
| **前置条件** | UAT-061已通过，数据覆盖至少90天 |
| **执行命令** | 1. `uv run nanobotrun viz vdot --days 7`<br>2. `uv run nanobotrun viz vdot --days 90`<br>3. `uv run nanobotrun viz vdot --days 365` |
| **预期结果** | 三次命令退出码均为0，分别显示7天/90天/365天的VDOT趋势图 |
| **优先级** | P0 |

**自动化判定规则**:
```json
{
  "pass_condition": "all three commands exit_code == 0 AND each stdout contains 'VDOT'",
  "fail_condition": "any command exit_code != 0 OR stdout contains '错误:'"
}
```

**人工验收要点**:
- [ ] 7天图：数据点较少，趋势清晰
- [ ] 90天图：数据点适中，能看出趋势变化
- [ ] 365天图：数据点较多，整体趋势明显
- [ ] 各时间范围图表无重叠或混淆
- [ ] 图表缩放合理，数据可读

**结果记录**:
- [ ] 通过 / [ ] 失败
- 7天数据条数: _____
- 90天数据条数: _____
- 365天数据条数: _____
- 异常信息（如失败）: _____

---

## UAT-063: 训练负荷曲线

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证CTL/ATL/TSB三线同屏显示功能 |
| **前置条件** | 已导入跑步数据（至少包含30天数据） |
| **执行命令** | `uv run nanobotrun viz load --days 30` |
| **预期结果** | 退出码为0，终端显示CTL/ATL/TSB三条曲线，TSB正负区域颜色区分 |
| **优先级** | P0 |

**自动化判定规则**:
```json
{
  "pass_condition": "exit_code == 0 AND stdout contains 'CTL' AND stdout contains 'ATL' AND stdout contains 'TSB'",
  "fail_condition": "exit_code != 0 OR stdout contains '错误:' OR stdout contains '无数据'"
}
```

**人工验收要点**:
- [ ] 三条曲线（CTL/ATL/TSB）清晰可辨
- [ ] 图例标注正确
- [ ] TSB正值和负值区域颜色区分明显
- [ ] 时间轴显示清晰
- [ ] 数值范围合理，无异常极值

**结果记录**:
- [ ] 通过 / [ ] 失败
- CTL平均值: _____
- ATL平均值: _____
- TSB当前值: _____
- 渲染耗时: _____秒
- 异常信息（如失败）: _____

---

## UAT-064: 心率区间分布

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证心率区间堆叠柱状图渲染功能 |
| **前置条件** | 已导入带心率数据的跑步记录（至少包含5条） |
| **执行命令** | `uv run nanobotrun viz hr-zones --start 2024-01-01 --end 2024-12-31` |
| **预期结果** | 退出码为0，终端显示心率区间堆叠柱状图，包含各区间占比 |
| **优先级** | P0 |

**自动化判定规则**:
```json
{
  "pass_condition": "exit_code == 0 AND stdout contains '心率' AND (stdout contains '区间' OR stdout contains 'zone')",
  "fail_condition": "exit_code != 0 OR stdout contains '错误:' OR stdout contains '无心率数据'"
}
```

**人工验收要点**:
- [ ] 堆叠柱状图正常渲染
- [ ] 各心率区间（Z1-Z5）颜色区分明显
- [ ] 图例标注清晰
- [ ] 日期范围过滤生效
- [ ] 区间占比数据准确

**结果记录**:
- [ ] 通过 / [ ] 失败
- 数据条数: _____
- Z1占比: _____%
- Z2占比: _____%
- Z3占比: _____%
- Z4占比: _____%
- Z5占比: _____%
- 异常信息（如失败）: _____

---

## UAT-065: 可视化年龄计算

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证使用指定年龄计算心率区间的功能 |
| **前置条件** | UAT-064已通过 |
| **执行命令** | `uv run nanobotrun viz hr-zones --start 2024-01-01 --end 2024-12-31 --age 30` |
| **预期结果** | 退出码为0，使用指定年龄（30岁）计算心率区间并显示图表 |
| **优先级** | P1 |

**自动化判定规则**:
```json
{
  "pass_condition": "exit_code == 0 AND stdout contains '心率' AND stdout contains '30'",
  "fail_condition": "exit_code != 0 OR stdout contains '错误:'"
}
```

**人工验收要点**:
- [ ] 年龄参数生效，心率区间计算基于指定年龄
- [ ] 最大心率 = 220 - 30 = 190
- [ ] 各区间阈值与年龄匹配
- [ ] 图表显示正常

**结果记录**:
- [ ] 通过 / [ ] 失败
- 指定年龄: _____
- 计算的最大心率: _____
- 异常信息（如失败）: _____

---

## 测试环境要求

| 要求 | 说明 |
|------|------|
| **终端环境** | 支持ANSI转义序列的终端（Windows Terminal、iTerm2等） |
| **Python版本** | 3.11+ |
| **依赖包** | plotext（终端图表渲染库） |
| **测试数据** | 至少包含30天跑步数据，覆盖多种运动类型 |
| **显示分辨率** | 终端宽度≥80字符，高度≥24行 |

## 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| 图表显示乱码 | 终端不支持ANSI转义 | 使用Windows Terminal或配置终端编码 |
| 无数据提示 | 数据不足或日期范围无数据 | 检查导入数据，调整日期范围 |
| 渲染失败 | plotext未安装 | 运行 `uv sync` 安装依赖 |
| 心率区间不准确 | 年龄配置错误 | 使用--age参数指定正确年龄 |
