# 智能跑步计划功能 UAT 测试指南

> **文档版本**: v1.0
> **创建日期**: 2026-04-21
> **文档状态**: 正式发布
> **适用范围**: v0.10.0 - v0.12.0 智能跑步计划功能
> **对齐文档**: 《UC_智能跑步计划用例.md》《REQ_需求规格说明书.md》

---

## 1. 文档目的

本文档面向**真实用户**（技术型严肃跑者），指导如何利用**个人历史运动数据**完成智能跑步计划功能的验收测试（UAT）。

核心难点：如何将过去几年的真实跑步数据转化为可执行的测试场景，确保测试结果反映真实使用体验，而非理想化的模拟数据。

---

## 2. 测试环境准备

### 2.1 环境要求

| 项目 | 要求 | 验证方式 |
|------|------|---------|
| 操作系统 | Windows 10/11 | `winver` |
| Python | 3.12+（通过 uv 管理） | `uv python list` |
| 项目分支 | `feature-AI-Running-Plan` | `git branch --show-current` |
| 数据目录 | `~/.nanobot-runner/data/` 存在历史数据 | `ls ~/.nanobot-runner/data/` |

### 2.2 历史数据准备

**前提**：用户已有过去几年的跑步数据（FIT 文件已导入，存储为 Parquet 格式）。

#### 步骤 1：确认数据完整性

```powershell
# 查看数据目录
ls ~/.nanobot-runner/data/

# 预期输出：
# activities_2023.parquet
# activities_2024.parquet
# activities_2025.parquet
# index.json
# profile.json
```

#### 步骤 2：验证数据量

```powershell
# 查看各年份数据统计
uv run nanobotrun data stats --year 2024
uv run nanobotrun data stats --year 2025

# 关键指标检查：
# - 跑步次数 ≥ 50 次（建议至少 3 个月数据）
# - 总距离 ≥ 500km
# - 包含不同训练类型（轻松跑、长距离、间歇跑等）
```

#### 步骤 3：确认 VDOT 计算基础

```powershell
# 查看当前 VDOT（基于历史数据自动计算）
uv run nanobotrun analytics vdot

# 预期输出示例：
# 当前 VDOT: 45.2
# 最近 30 天趋势: 上升
# 历史最高: 48.1 (2024-03-15)
```

> **数据不足的处理**：如果历史数据少于 30 次跑步，VDOT 计算可能不准确。建议先导入更多 FIT 文件，或使用 `--vdot` 参数手动指定当前 VDOT 值进行测试。

### 2.3 初始化系统

```powershell
# 如果尚未初始化
uv run nanobotrun system init

# 验证初始化成功
uv run nanobotrun system status
```

---

## 3. UAT 测试场景（按用户使用顺序）

### 第一阶段：制定计划

---

#### UAT-01 评估目标达成概率

**对应用例**: UC-PLAN-01
**测试目标**: 验证系统能否基于历史数据，理性评估目标可行性

##### 测试数据准备

利用历史数据中的 VDOT 趋势，选择 3 个不同难度的目标：

| 场景 | 目标类型 | 目标值 | 依据 |
|------|---------|--------|------|
| 保守目标 | vdot | 当前 VDOT + 2 | 历史数据显示 3 个月内可达 |
| 挑战目标 | vdot | 当前 VDOT + 5 | 需要 12-16 周系统训练 |
| 激进目标 | marathon | 14400 秒（4 小时全马） | 需要大幅提升 |

##### 测试步骤

```powershell
# 步骤 1：获取当前 VDOT
uv run nanobotrun analytics vdot
# 记录输出值，假设为 42.0

# 步骤 2：评估保守目标（VDOT 从 42 提升到 44）
uv run nanobotrun plan evaluate vdot 44 --vdot 42 --weeks 8

# 预期输出：
# - 达成概率 > 70%
# - 关键风险：无或较少
# - 改进建议：具体可操作

# 步骤 3：评估挑战目标（VDOT 从 42 提升到 47）
uv run nanobotrun plan evaluate vdot 47 --vdot 42 --weeks 16

# 预期输出：
# - 达成概率 40%-70%
# - 关键风险：训练负荷、伤病风险
# - 改进建议：需要系统训练

# 步骤 4：评估激进目标（4 小时全马）
uv run nanobotrun plan evaluate marathon 14400 --vdot 42 --weeks 20

# 预期输出：
# - 达成概率 < 40%
# - 关键风险：跑量不足、经验不足
# - 改进建议：建议先完成半马
```

##### 验收标准

| 检查项 | 通过标准 | 实际结果 |
|--------|---------|---------|
| 概率计算合理 | 保守 > 挑战 > 激进 | □ 通过 □ 失败 |
| 风险识别准确 | 至少识别 1 个关键风险 | □ 通过 □ 失败 |
| 建议可操作 | 建议具体，非空泛描述 | □ 通过 □ 失败 |
| 响应时间 | < 500ms | □ 通过 □ 失败 |

---

#### UAT-02 生成长期训练规划

**对应用例**: UC-PLAN-02
**测试目标**: 验证系统能否基于历史数据和目标，生成科学的周期化训练计划

##### 测试数据准备

使用 UAT-01 中评估通过的目标（建议选保守或挑战目标），结合历史训练偏好：

- 从历史数据中查看自己通常每周训练几天
- 查看历史最长单次跑步距离
- 查看历史周跑量范围

##### 测试步骤

```powershell
# 步骤 1：生成 16 周全马备赛计划（中级水平）
uv run nanobotrun plan long-term "2026秋季全马备赛" --vdot 42 --target 47 --race "北京马拉松" --date 2026-10-18 --weeks 16 --level intermediate

# 预期输出：
# - 包含 4 个训练周期（基础期、提升期、巅峰期、减量期）
# - 各周期跑量范围合理（基础期 30-40km/周，巅峰期 60-80km/周）
# - 包含关键里程碑（如：第 8 周半马测试赛）

# 步骤 2：验证计划已持久化
uv run nanobotrun plan list

# 预期输出：
# - 显示刚创建的计划
# - 状态为 draft
# - 包含计划 ID（如 plan_20260421_xxxxxx）

# 步骤 3：查看计划详情（记录 plan_id 用于后续测试）
# 假设 plan_id = plan_20260421_001
```

##### 验收标准

| 检查项 | 通过标准 | 实际结果 |
|--------|---------|---------|
| 周期划分合理 | 包含基础/提升/巅峰/减量四个阶段 | □ 通过 □ 失败 |
| 跑量递进科学 | 周跑量逐步增加，无突变 | □ 通过 □ 失败 |
| 里程碑清晰 | 至少包含 2 个关键里程碑 | □ 通过 □ 失败 |
| 计划持久化 | plan list 可查看到计划 | □ 通过 □ 失败 |

---

### 第二阶段：执行计划

---

#### UAT-03 记录训练计划执行反馈

**对应用例**: UC-PLAN-03
**测试目标**: 验证系统能否准确记录每日训练执行情况

##### 测试数据准备

使用 UAT-02 生成的计划，选取计划中的 3 个不同日期，模拟真实训练记录：

| 日期 | 训练类型 | 完成度 | 体感 | 备注 |
|------|---------|--------|------|------|
| 计划第 1 天 | 轻松跑 | 100% | 4 | 轻松完成 |
| 计划第 3 天 | 间歇跑 | 80% | 7 | 最后两组没完成 |
| 计划第 5 天 | 长距离跑 | 60% | 8 | 下雨提前结束 |

##### 测试步骤

```powershell
# 假设 plan_id = plan_20260421_001

# 步骤 1：记录正常完成的轻松跑
uv run nanobotrun plan log plan_20260421_001 2026-04-21 --completion 1.0 --effort 4 --notes "轻松完成" --distance 8 --duration 48 --hr 142

# 预期输出：
# [OK] 记录成功
#   完成度: 100%
#   体感评分: 4/10
#   备注: 轻松完成

# 步骤 2：记录部分完成的间歇跑
uv run nanobotrun plan log plan_20260421_001 2026-04-23 --completion 0.8 --effort 7 --notes "最后两组没完成"

# 步骤 3：记录提前结束的长距离跑
uv run nanobotrun plan log plan_20260421_001 2026-04-25 --completion 0.6 --effort 8 --notes "下雨提前结束"

# 步骤 4：验证数据持久化（重启后数据不丢失）
# 关闭终端，重新打开后查看
uv run nanobotrun plan stats plan_20260421_001
```

##### 边界场景测试

```powershell
# 边界 1：计划不存在
uv run nanobotrun plan log invalid_plan_id 2026-04-21 --completion 1.0
# 预期：错误提示"计划不存在：invalid_plan_id"，退出码 1

# 边界 2：日期不在计划范围内
uv run nanobotrun plan log plan_20260421_001 2027-01-01 --completion 1.0
# 预期：错误提示"日期不存在"，退出码 1

# 边界 3：完成度超出范围
uv run nanobotrun plan log plan_20260421_001 2026-04-21 --completion 1.5
# 预期：错误提示"完成度必须在0.0-1.0之间"，退出码 1

# 边界 4：体感评分超出范围
uv run nanobotrun plan log plan_20260421_001 2026-04-21 --completion 1.0 --effort 11
# 预期：错误提示"体感评分必须在1-10之间"，退出码 1
```

##### 验收标准

| 检查项 | 通过标准 | 实际结果 |
|--------|---------|---------|
| CLI 记录成功 | 3 次记录均返回成功 | □ 通过 □ 失败 |
| 数据持久化 | 重启后可查询到记录 | □ 通过 □ 失败 |
| 边界校验正确 | 4 个边界场景均正确拦截 | □ 通过 □ 失败 |
| 错误提示清晰 | 每个错误包含具体原因 | □ 通过 □ 失败 |

---

### 第三阶段：获得反馈

---

#### UAT-04 查看计划执行统计

**对应用例**: UC-PLAN-04
**测试目标**: 验证系统能否基于历史执行记录，提供完整的统计报告

##### 测试步骤

```powershell
# 步骤 1：查看计划执行统计（使用 UAT-03 记录的数据）
uv run nanobotrun plan stats plan_20260421_001

# 预期输出包含：
# - 计划天数、完成天数、完成率
# - 平均体感评分
# - 总距离、总时长
# - 平均心率、平均心率漂移（如有数据）

# 步骤 2：验证统计准确性
# 手动计算：
# - 完成率 = 完成天数 / 计划天数
# - 平均体感 = (4 + 7 + 8) / 3 = 6.3
# 与系统输出对比
```

##### 验收标准

| 检查项 | 通过标准 | 实际结果 |
|--------|---------|---------|
| 指标完整 | 包含完成率、体感、跑量、时长 | □ 通过 □ 失败 |
| 数据准确 | 统计值与手动计算一致 | □ 通过 □ 失败 |
| 响应时间 | < 500ms | □ 通过 □ 失败 |

---

#### UAT-05 分析训练响应模式

**对应用例**: UC-PLAN-05
**测试目标**: 验证系统能否识别用户对不同训练类型的适应程度

##### 测试数据准备

需要至少 3 次不同训练类型的执行记录。利用 UAT-03 已记录的 3 次训练：
- 轻松跑（完成度 100%，体感 4）
- 间歇跑（完成度 80%，体感 7）
- 长距离跑（完成度 60%，体感 8）

> **利用历史数据的增强测试**：如果用户历史数据中包含多种训练类型，可先执行更多记录，使分析更准确：

```powershell
# 补充记录（基于历史真实训练数据）
# 假设用户历史记录显示：
# - 2024 年完成过 20 次轻松跑，平均体感 4.2
# - 2024 年完成过 8 次间歇跑，平均体感 7.5
# - 2024 年完成过 5 次长距离跑，平均体感 6.8

# 在当前计划中补充记录，模拟历史模式
uv run nanobotrun plan log plan_20260421_001 2026-04-27 --completion 1.0 --effort 4 --notes "轻松跑"
uv run nanobotrun plan log plan_20260421_001 2026-04-29 --completion 0.9 --effort 7 --notes "间歇跑"
uv run nanobotrun plan log plan_20260421_001 2026-05-01 --completion 0.7 --effort 8 --notes "长距离跑"
```

##### 测试步骤

```powershell
# 此功能仅支持 Agent 模式
uv run nanobotrun agent chat

# 在对话中输入：
# "分析我最近的训练响应"

# 预期输出：
# - 最适应的训练类型（高完成率 + 低体感 + 低心率漂移）
# - 最不适应的训练类型
# - 训练建议
```

##### 验收标准

| 检查项 | 通过标准 | 实际结果 |
|--------|---------|---------|
| 识别最佳类型 | 轻松跑应显示为最适应 | □ 通过 □ 失败 |
| 识别最差类型 | 长距离或间歇跑显示为最不适应 | □ 通过 □ 失败 |
| 建议合理 | 建议针对薄弱环节 | □ 通过 □ 失败 |

---

#### UAT-06 获取智能训练建议

**对应用例**: UC-PLAN-06
**测试目标**: 验证系统能否基于多维数据，提供训练、恢复、营养、伤病预防的综合建议

##### 测试数据准备

从历史数据中提取以下信息：

```powershell
# 查看当前 VDOT
uv run nanobotrun analytics vdot

# 查看最近 4 周跑量（从历史 Parquet 数据计算）
# 假设当前周跑量 = 45km

# 查看训练一致性（最近 4 周有训练的天数 / 总天数）
# 假设一致性 = 0.75（每周训练 5-6 天）
```

##### 测试步骤

```powershell
# 步骤 1：CLI 模式获取建议
uv run nanobotrun plan advice --vdot 42 --volume 45 --consistency 0.75 --risk low --goal marathon

# 预期输出包含四类建议：
# - 训练建议：如"建议增加长距离跑比例"
# - 恢复建议：如"每周安排 1-2 天完全休息"
# - 营养建议：如"长距离跑后 30 分钟内补充碳水"
# - 伤病预防：如"每周 2 次力量训练"

# 步骤 2：验证建议质量
# 检查每项建议是否：
# - 基于实际数据（而非通用模板）
# - 具体可操作（而非"注意休息"等空泛描述）
# - 有优先级标注（高/中/低）
# - 有置信度标注（百分比）
```

##### 验收标准

| 检查项 | 通过标准 | 实际结果 |
|--------|---------|---------|
| 四维度覆盖 | 训练/恢复/营养/伤病预防均有建议 | □ 通过 □ 失败 |
| 基于实际数据 | 建议引用用户具体数据 | □ 通过 □ 失败 |
| 优先级排序 | 高优先级建议排在前面 | □ 通过 □ 失败 |
| 建议可操作 | 每项建议具体明确 | □ 通过 □ 失败 |

---

### 第四阶段：改进计划

---

#### UAT-07 获取计划调整建议

**对应用例**: UC-PLAN-07
**测试目标**: 验证系统能否基于执行数据，主动提供个性化调整建议

##### 测试步骤

```powershell
# 步骤 1：获取调整建议
uv run nanobotrun plan suggest plan_20260421_001

# 预期输出：
# - 建议列表（按优先级排序）
# - 每条建议包含：优先级、内容、置信度、原因

# 步骤 2：验证建议合理性
# 基于 UAT-03 的记录数据：
# - 长距离跑完成度仅 60%，体感 8 → 应建议降低长距离跑强度
# - 间歇跑完成度 80%，体感 7 → 可能建议保持或微调
# - 轻松跑完成度 100%，体感 4 → 可能建议适当增加
```

##### 验收标准

| 检查项 | 通过标准 | 实际结果 |
|--------|---------|---------|
| 建议针对性 | 建议与执行数据相关 | □ 通过 □ 失败 |
| 优先级排序 | 高优先级建议在前 | □ 通过 □ 失败 |
| 置信度标注 | 每条建议有置信度 | □ 通过 □ 失败 |

---

#### UAT-08 自然语言调整训练计划

**对应用例**: UC-PLAN-08
**测试目标**: 验证系统能否通过自然语言指令，安全地调整训练计划

##### 测试步骤

```powershell
# 场景 1：合理调整（减量）
uv run nanobotrun plan adjust plan_20260421_001 "下周减量20%"

# 预期输出：
# - 显示调整预览
# - 询问确认
# - 确认后执行调整

# 场景 2：合理调整（修改训练类型）
uv run nanobotrun plan adjust plan_20260421_001 "把周三的间歇跑改成轻松跑"

# 预期输出：
# - 显示调整预览
# - 确认后执行

# 场景 3：不合理调整（应被规则拦截）
uv run nanobotrun plan adjust plan_20260421_001 "下周跑量增加50%"

# 预期输出：
# - 拒绝调整
# - 提示"周跑量增幅不能超过10%"
# - 给出建议调整幅度

# 场景 4：跳过确认
uv run nanobotrun plan adjust plan_20260421_001 "下周减量10%" --no-confirm

# 预期输出：
# - 直接执行调整
# - 返回调整成功
```

##### 验收标准

| 检查项 | 通过标准 | 实际结果 |
|--------|---------|---------|
| 自然语言理解 | 正确解析调整意图 | □ 通过 □ 失败 |
| 规则拦截有效 | 跑量增幅 > 10% 被拦截 | □ 通过 □ 失败 |
| 确认机制 | 默认需要确认 | □ 通过 □ 失败 |
| --no-confirm 有效 | 跳过确认直接执行 | □ 通过 □ 失败 |

---

#### UAT-09 Agent 对话式计划管理

**对应用例**: UC-PLAN-09
**测试目标**: 验证系统能否通过自然语言对话，完成计划全生命周期管理

##### 测试步骤

```powershell
# 启动 Agent 对话
uv run nanobotrun agent chat

# 在对话中依次输入以下指令，验证意图识别和工具调用：

# 制定阶段
"帮我评估一下VDOT从42提升到47需要多久"
"制定一个16周全马备赛计划"

# 执行阶段
"记录今天跑了10公里，完成度90%，体感7分"

# 反馈阶段
"我的计划执行得怎么样"
"分析我最近的训练响应"

# 改进阶段
"有什么调整建议吗"
"下周减量20%"

# 预期：
# - 每个指令被正确识别意图
# - 调用对应工具并返回结果
# - 多轮对话保持上下文
```

##### 验收标准

| 检查项 | 通过标准 | 实际结果 |
|--------|---------|---------|
| 意图识别 | 7 个指令均正确识别 | □ 通过 □ 失败 |
| 工具调用 | 每个指令调用正确工具 | □ 通过 □ 失败 |
| 上下文保持 | 多轮对话不丢失上下文 | □ 通过 □ 失败 |
| 错误解释 | 规则校验失败时解释清晰 | □ 通过 □ 失败 |

---

## 4. 历史数据驱动的增强测试

本节指导如何利用**过去几年的真实运动数据**，进行更深度的 UAT 验证。

### 4.1 基于历史 VDOT 趋势的目标评估测试

#### 测试思路

利用历史数据中的 VDOT 变化趋势，验证目标评估的准确性：

1. 从历史数据中找到 VDOT 的最高点和最低点
2. 计算历史 VDOT 提升速度（如：3 个月提升 3 点）
3. 用这个速度作为基准，评估系统给出的达成概率是否合理

#### 测试步骤

```powershell
# 步骤 1：查看历史 VDOT 趋势
uv run nanobotrun analytics vdot --trend

# 记录关键数据：
# - 历史最高 VDOT：___（日期：___）
# - 历史最低 VDOT：___（日期：___）
# - 最近 3 个月 VDOT 变化：___ → ___

# 步骤 2：基于历史趋势设定目标
# 如果历史数据显示 3 个月提升 3 点，则：
# - 设定 3 个月提升 3 点的目标 → 达成概率应 > 70%
# - 设定 3 个月提升 8 点的目标 → 达成概率应 < 40%

# 步骤 3：验证评估结果
uv run nanobotrun plan evaluate vdot <目标值> --vdot <当前值> --weeks 12

# 步骤 4：对比历史实际达成情况
# 如果历史上曾达成过类似目标，系统评估概率应偏高
# 如果历史上从未达成过类似目标，系统评估概率应偏低
```

### 4.2 基于历史训练负荷的计划生成测试

#### 测试思路

利用历史训练负荷数据（周跑量、训练频率、最长单次距离），验证生成的计划是否符合用户实际能力：

1. 从历史数据计算平均周跑量、最大周跑量
2. 验证生成的计划周跑量范围是否在用户能力范围内
3. 验证计划的跑量递进是否符合"10% 原则"

#### 测试步骤

```powershell
# 步骤 1：计算历史训练负荷
# 使用 Polars 直接查询 Parquet 数据（高级用户）
uv run python -c "
import polars as pl
df = pl.read_parquet('$env:USERPROFILE/.nanobot-runner/data/activities_2024.parquet')
# 按周聚合跑量
df = df.with_columns(pl.col('timestamp').dt.week().alias('week'))
weekly = df.group_by('week').agg(pl.col('session_total_distance').sum() / 1000)
print('平均周跑量:', weekly['session_total_distance'].mean())
print('最大周跑量:', weekly['session_total_distance'].max())
"

# 步骤 2：生成计划并验证
uv run nanobotrun plan long-term "测试计划" --vdot <当前值> --weeks 16 --level intermediate

# 步骤 3：验证计划跑量范围
# - 基础期周跑量应接近历史平均周跑量
# - 巅峰期周跑量不应超过历史最大周跑量的 120%
# - 跑量递进每周不超过 10%
```

### 4.3 基于历史训练响应的个性化建议测试

#### 测试思路

利用历史数据中不同训练类型的完成情况，验证系统建议是否个性化：

1. 统计历史各训练类型的完成率、平均体感
2. 找出用户最适应和最不适应的训练类型
3. 验证系统建议是否针对用户的薄弱环节

#### 测试步骤

```powershell
# 步骤 1：统计历史训练类型分布
uv run python -c "
import polars as pl
df = pl.read_parquet('$env:USERPROFILE/.nanobot-runner/data/activities_2024.parquet')
# 按距离分类训练类型
df = df.with_columns(
    pl.when(pl.col('session_total_distance') < 5000).then('短距离')
    .when(pl.col('session_total_distance') < 15000).then('中距离')
    .otherwise('长距离').alias('训练类型')
)
stats = df.group_by('训练类型').agg([
    pl.col('session_total_distance').count().alias('次数'),
    pl.col('session_total_distance').mean().alias('平均距离'),
])
print(stats)
"

# 步骤 2：获取智能建议
uv run nanobotrun plan advice --vdot <当前值> --volume <周跑量> --consistency <一致性> --risk low

# 步骤 3：验证建议个性化程度
# - 如果历史数据显示长距离跑完成率低，建议应包含"逐步增加长距离跑"
# - 如果历史数据显示间歇跑体感高，建议应包含"降低间歇跑强度"
# - 建议不应是通用模板，而应引用用户具体数据
```

### 4.4 基于历史伤病史的风险评估测试

#### 测试思路

如果用户历史数据中包含伤病记录（可通过备注字段标记），验证系统的风险评估和建议：

1. 查看历史数据中是否有伤病相关记录
2. 验证系统是否识别伤病风险
3. 验证系统是否给出针对性的伤病预防建议

#### 测试步骤

```powershell
# 步骤 1：查看历史伤病记录（如果有）
uv run python -c "
import polars as pl
df = pl.read_parquet('$env:USERPROFILE/.nanobot-runner/data/activities_2024.parquet')
# 搜索包含伤病关键词的记录
# 注意：需要根据实际 schema 调整字段名
print('检查历史数据中是否有伤病相关记录')
"

# 步骤 2：获取包含伤病风险评估的建议
uv run nanobotrun plan advice --vdot <当前值> --volume <周跑量> --consistency <一致性> --risk high

# 步骤 3：验证伤病预防建议
# - 应包含力量训练建议
# - 应包含跑姿调整建议
# - 应包含拉伸和恢复建议
```

### 4.5 基于历史比赛成绩的目标设定测试

#### 测试思路

利用用户历史比赛成绩（半马、全马等），验证目标评估和计划生成的准确性：

1. 从历史数据中找到最佳比赛成绩
2. 设定比历史最佳更好的目标
3. 验证系统评估是否考虑了历史成绩

#### 测试步骤

```powershell
# 步骤 1：查看历史最佳成绩
uv run nanobotrun analytics stats --year 2024
# 找到最长距离、最快配速的比赛

# 步骤 2：基于历史最佳设定目标
# 假设历史最佳半马成绩为 1:50:00（6600 秒）
# 设定目标为 1:45:00（6300 秒）
uv run nanobotrun plan evaluate half_marathon 6300 --vdot <当前值> --weeks 16

# 步骤 3：验证评估合理性
# - 如果历史最佳是 1:50，目标 1:45 需要提升 5 分钟
# - 达成概率应在 40%-70% 之间（取决于当前训练状态）
```

---

## 5. 跨年度数据整合测试

### 5.1 多年度数据合并查询

#### 测试思路

验证系统能否正确合并查询多个年份的历史数据，用于目标评估和计划生成：

```powershell
# 步骤 1：确认有多个年份的数据
ls ~/.nanobot-runner/data/activities_*.parquet

# 步骤 2：查看跨年度统计
uv run nanobotrun analytics stats

# 步骤 3：基于跨年度数据评估目标
uv run nanobotrun plan evaluate vdot <目标值> --vdot <当前值> --weeks 16

# 验证：系统应使用所有年份的数据计算 VDOT 趋势，而非仅使用最近一年
```

### 5.2 数据一致性验证

#### 测试思路

验证多个年份的数据在合并查询时的一致性：

```powershell
# 步骤 1：分别查看各年份数据量
uv run nanobotrun analytics stats --year 2023
uv run nanobotrun analytics stats --year 2024
uv run nanobotrun analytics stats --year 2025

# 步骤 2：查看合并后的总数据量
uv run nanobotrun analytics stats

# 验证：总数据量 = 各年份数据量之和
```

---

## 6. 真实场景端到端测试

### 6.1 完整用户旅程测试

**测试目标**: 模拟真实用户从制定计划到改进计划的完整流程

#### 测试场景

假设用户是一位有 2 年跑步经验的严肃跑者：
- 当前 VDOT: 42
- 历史最佳半马: 1:50:00
- 平均周跑量: 35km
- 目标: 6 个月内完成全马，成绩 4:00:00

#### 测试步骤

```powershell
# 第 1 天：评估目标
uv run nanobotrun plan evaluate marathon 14400 --vdot 42 --weeks 24

# 第 1 天：生成计划
uv run nanobotrun plan long-term "2026全马备赛" --vdot 42 --target 45 --race "上海马拉松" --date 2026-11-29 --weeks 24 --level intermediate

# 第 1-7 天：执行计划并记录（每天一条记录）
uv run nanobotrun plan log <plan_id> 2026-04-21 --completion 1.0 --effort 4 --notes "轻松跑 8km"
uv run nanobotrun plan log <plan_id> 2026-04-22 --completion 0.0 --effort 0 --notes "休息"
uv run nanobotrun plan log <plan_id> 2026-04-23 --completion 0.8 --effort 7 --notes "间歇跑 6km"
uv run nanobotrun plan log <plan_id> 2026-04-24 --completion 1.0 --effort 4 --notes "轻松跑 6km"
uv run nanobotrun plan log <plan_id> 2026-04-25 --completion 1.0 --effort 5 --notes "节奏跑 10km"
uv run nanobotrun plan log <plan_id> 2026-04-26 --completion 0.0 --effort 0 --notes "休息"
uv run nanobotrun plan log <plan_id> 2026-04-27 --completion 0.9 --effort 6 --notes "长距离跑 18km"

# 第 8 天：查看统计
uv run nanobotrun plan stats <plan_id>

# 第 8 天：获取建议
uv run nanobotrun plan advice --vdot 42 --volume 48 --consistency 0.71 --risk low --goal marathon

# 第 8 天：获取调整建议
uv run nanobotrun plan suggest <plan_id>

# 第 8 天：调整计划
uv run nanobotrun plan adjust <plan_id> "下周长距离跑增加到20km"
```

#### 验收标准

| 检查项 | 通过标准 | 实际结果 |
|--------|---------|---------|
| 全流程闭环 | 9 个用例全部执行通过 | □ 通过 □ 失败 |
| 数据一致性 | 各阶段数据传递正确 | □ 通过 □ 失败 |
| 用户体验 | 命令响应快速，提示清晰 | □ 通过 □ 失败 |

---

## 7. 测试数据构造指南

### 7.1 使用历史数据构造测试场景

如果用户希望基于真实历史数据进行更深入的测试，可以使用以下方法：

#### 方法 1：直接查询 Parquet 数据

```powershell
# 查看某段时间的跑步记录
uv run python -c "
import polars as pl
df = pl.read_parquet('$env:USERPROFILE/.nanobot-runner/data/activities_2024.parquet')
# 筛选 2024 年 3 月的数据
df = df.filter(
    (pl.col('timestamp') >= '2024-03-01') &
    (pl.col('timestamp') < '2024-04-01')
)
print(f'2024年3月共 {df.height} 次跑步')
print(f'总距离: {df[\"session_total_distance\"].sum() / 1000:.1f}km')
print(f'平均心率: {df[\"session_avg_heart_rate\"].mean():.0f}bpm')
"
```

#### 方法 2：构造特定训练类型的记录

```powershell
# 基于历史数据中的训练类型分布，构造当前计划的执行记录
# 假设历史数据显示：
# - 轻松跑占 50%，平均距离 8km，平均体感 4
# - 间歇跑占 15%，平均距离 6km，平均体感 7
# - 长距离跑占 15%，平均距离 18km，平均体感 6
# - 休息占 20%

# 在当前计划中按此比例记录
```

### 7.2 构造边界场景数据

```powershell
# 构造极低完成度场景
uv run nanobotrun plan log <plan_id> <date> --completion 0.0 --effort 10 --notes "完全没跑"

# 构造极高完成度场景
uv run nanobotrun plan log <plan_id> <date> --completion 1.0 --effort 1 --notes "超轻松完成"

# 构造连续高强度训练场景（连续 5 天体感 >= 7）
# 用于验证系统是否能识别过度训练风险
```

---

## 8. 测试结果记录

### 8.1 测试执行记录表

| 测试编号 | 测试名称 | 执行日期 | 执行结果 | 备注 |
|---------|---------|---------|---------|------|
| UAT-01 | 评估目标达成概率 | | □ 通过 □ 失败 | |
| UAT-02 | 生成长期训练规划 | | □ 通过 □ 失败 | |
| UAT-03 | 记录训练执行反馈 | | □ 通过 □ 失败 | |
| UAT-04 | 查看计划执行统计 | | □ 通过 □ 失败 | |
| UAT-05 | 分析训练响应模式 | | □ 通过 □ 失败 | |
| UAT-06 | 获取智能训练建议 | | □ 通过 □ 失败 | |
| UAT-07 | 获取计划调整建议 | | □ 通过 □ 失败 | |
| UAT-08 | 自然语言调整训练计划 | | □ 通过 □ 失败 | |
| UAT-09 | Agent 对话式计划管理 | | □ 通过 □ 失败 | |

### 8.2 Bug 记录表

| Bug ID | 所属模块 | 严重等级 | Bug 标题 | 复现步骤 | 状态 |
|--------|---------|---------|---------|---------|------|
| | | | | | |

### 8.3 测试结论

- [ ] P0 级用例全部通过
- [ ] P1 级用例通过率 ≥ 90%
- [ ] 无致命/严重 Bug
- [ ] 历史数据驱动测试全部通过
- [ ] 端到端全流程闭环

**测试结论**: □ 通过，建议上线  □ 不通过，需修复后重新测试

**不通过原因**（如适用）:

---

## 9. 附录

### 9.1 常用 CLI 命令速查

| 功能 | 命令 |
|------|------|
| 系统初始化 | `uv run nanobotrun system init` |
| 查看 VDOT | `uv run nanobotrun analytics vdot` |
| 评估目标 | `uv run nanobotrun plan evaluate <type> <value> --vdot <vdot> --weeks <n>` |
| 生成计划 | `uv run nanobotrun plan long-term "<name>" --vdot <vdot> --weeks <n>` |
| 记录执行 | `uv run nanobotrun plan log <plan_id> <date> --completion <r> --effort <n>` |
| 查看统计 | `uv run nanobotrun plan stats <plan_id>` |
| 获取建议 | `uv run nanobotrun plan advice --vdot <vdot> --volume <km>` |
| 获取调整建议 | `uv run nanobotrun plan suggest <plan_id>` |
| 调整计划 | `uv run nanobotrun plan adjust <plan_id> "<request>"` |
| Agent 对话 | `uv run nanobotrun agent chat` |

### 9.2 数据目录结构

```
~/.nanobot-runner/
├── data/
│   ├── activities_2023.parquet    # 2023 年跑步数据
│   ├── activities_2024.parquet    # 2024 年跑步数据
│   ├── activities_2025.parquet    # 2025 年跑步数据
│   ├── training_plans.json        # 训练计划
│   ├── profile.json               # 用户画像
│   └── index.json                 # 数据索引
├── memory/
│   ├── MEMORY.md                  # Agent 记忆
│   └── HISTORY.md                 # 事件日志
└── config.json                    # 应用配置
```

### 9.3 测试数据检查脚本

```powershell
# 一键检查测试数据完整性
uv run python -c "
from pathlib import Path
import polars as pl
import json

data_dir = Path.home() / '.nanobot-runner' / 'data'

# 检查 Parquet 文件
parquet_files = list(data_dir.glob('activities_*.parquet'))
print(f'数据文件数量: {len(parquet_files)}')

total_records = 0
for f in parquet_files:
    df = pl.read_parquet(f)
    print(f'  {f.name}: {df.height} 条记录')
    total_records += df.height

print(f'总记录数: {total_records}')

# 检查训练计划
plans_file = data_dir / 'training_plans.json'
if plans_file.exists():
    with open(plans_file, encoding='utf-8') as f:
        plans = json.load(f)
    print(f'训练计划数量: {len(plans.get(\"plans\", {}))}')
else:
    print('训练计划文件不存在')

# 检查用户画像
profile_file = data_dir / 'profile.json'
if profile_file.exists():
    with open(profile_file, encoding='utf-8') as f:
        profile = json.load(f)
    print(f'用户画像: 已配置')
else:
    print('用户画像文件不存在')
"
```

---

## 10. 文档修订记录

| 版本 | 日期 | 修订内容 | 修订人 |
|------|------|---------|--------|
| v1.0 | 2026-04-21 | 初始版本，基于 UC_智能跑步计划用例.md 编写 UAT 指南 | 测试工程师 |

---

> **使用说明**: 本文档为 UAT 验收测试指南，测试人员应按顺序执行 UAT-01 至 UAT-09，记录测试结果。历史数据驱动的增强测试（第 4 节）为可选测试，建议有充足历史数据的用户执行。
