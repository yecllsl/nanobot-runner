# v0.22.0 质量收口版本 — 四迭代详细执行计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 通过系统化UAT验证、缺陷收敛、质量兜底、需求洞察，完成v0.22.0质量收口版本交付

**Architecture:** v0.22无新模块/新CLI命令/新Agent工具，聚焦质量保障。UAT采用AI Agent+用户交互模式执行，Agent逐个执行测试用例并实时收集用户反馈。缺陷修复遵循TDD流程，质量兜底覆盖边界测试/性能基线/数据一致性/兼容性/文档完整性。

**Tech Stack:** Python 3.11+ / Typer+Rich CLI / Polars 0.20+ / scikit-learn 1.5+ / uv / pytest

---

## 文件结构总览

```
docs/
├── test/
│   ├── uat_test_cases/
│   │   ├── UAT_body_signal.md          # 新增：v0.19身体信号UAT用例
│   │   ├── UAT_prediction.md           # 新增：v0.20 ML预测UAT用例
│   │   ├── UAT_twin.md                 # 新增：v0.21数字孪生UAT用例
│   │   └── UAT_gateway_agent_enhanced.md # 新增：Gateway/Agent Chat增强UAT用例
│   ├── 用户验收测试指南.md              # 修改：扩展覆盖v0.19-v0.21+Gateway增强
│   ├── UAT测试执行报告_v0.22.0.md      # 新增：v0.22 UAT执行报告
│   ├── UAT反馈记录表.md                # 新增：用户反馈收集表
│   ├── 性能测试报告_v0.22.0.md         # 新增：性能测试报告
│   └── 缺陷跟踪表_v0.22.0.md          # 新增：缺陷跟踪表
├── planning/
│   ├── task_list_v0.22.0.md            # 已存在：任务清单
│   └── execution_plan_v0.22.0.md       # 本文件
├── architecture/
│   └── review/                         # 新增目录
│       ├── 缺陷修复报告_v0.22.0.md     # 新增
│       ├── 质量兜底报告_v0.22.0.md     # 新增
│       └── 回归验证报告_v0.22.0.md     # 新增
├── requirements/
│   └── 需求洞察报告_v0.22.0.md         # 新增
├── devops/
│   ├── 发布报告_v0.22.0.md             # 新增
│   └── 发布后观察报告_v0.22.0.md       # 新增
└── guides/
    └── (按需更新现有文档)
```

---

## Sprint 1：UAT验证（第1-2周）

**交付目标:** UAT测试完成，缺陷清单输出
**准入条件:** 架构设计v9.0.0已确认
**准出条件:** UAT报告输出，P0用例100%记录

### AI Agent + 用户交互 UAT 执行模式

**核心设计原则：** Agent逐个执行UAT测试用例，每执行完一个用例，收集用户反馈信息并记录。

**交互协议：**

```
┌─────────┐         ┌─────────┐
│ AI Agent │         │  用户    │
└────┬────┘         └────┬────┘
     │  1.展示测试用例描述    │
     │─────────────────────>│
     │  2.执行CLI命令        │
     │──────────────────────│ (终端输出)
     │  3.展示执行结果       │
     │─────────────────────>│
     │  4.请求用户判定       │
     │─────────────────────>│
     │  5.用户反馈(通过/失败/ │
     │     阻塞+评论)        │
     │<─────────────────────│
     │  6.记录反馈到文件     │
     │──────────────────────│
     │  7.进入下一用例       │
     │──────────────────────│
```

**反馈收集格式（每个用例）：**

```markdown
| 用例ID | 执行时间 | CLI命令 | 预期结果 | 实际结果 | 用户判定 | 用户评论 | 痛点标记 |
|--------|---------|---------|---------|---------|---------|---------|---------|
| UAT-001 | 2026-05-16 10:30 | nanobotrun data import ... | 成功导入 | 成功导入 | ✅通过 | 无 | - |
```

**用户判定选项：**
- ✅ 通过：实际结果与预期一致
- ❌ 失败：实际结果与预期不一致
- ⏸️ 阻塞：无法执行（环境/依赖问题）
- ⚠️ 部分通过：核心功能正常但有轻微偏差

---

### Task S1-01: 编写UAT测试指南（T-01-01）

**Files:**
- Modify: `docs/test/用户验收测试指南.md`
- Create: `docs/test/uat_test_cases/UAT_body_signal.md`
- Create: `docs/test/uat_test_cases/UAT_prediction.md`
- Create: `docs/test/uat_test_cases/UAT_twin.md`
- Create: `docs/test/UAT反馈记录表.md`

- [ ] **Step 1: 创建v0.19身体信号UAT用例文件**

创建 `docs/test/uat_test_cases/UAT_body_signal.md`，包含以下用例：

```markdown
# UAT - 身体信号分析模块 (v0.19)

## UAT-071: HRV分析 - 7天窗口
- 优先级: P0
- 前置条件: 已导入≥7天的跑步数据
- 操作步骤:
  1. 执行 `uv run nanobotrun analysis hrv --days 7`
- 预期结果: 显示7天HRV分析结果，包含RMSSD/SDNN/HRV趋势
- 验证要点: 数值在合理范围，趋势图正常显示

## UAT-072: HRV分析 - 30天窗口
- 优先级: P1
- 前置条件: 已导入≥30天的跑步数据
- 操作步骤:
  1. 执行 `uv run nanobotrun analysis hrv --days 30`
- 预期结果: 显示30天HRV分析结果
- 验证要点: 与7天结果对比，趋势一致

## UAT-073: HRV分析 - 90天窗口
- 优先级: P1
- 前置条件: 已导入≥90天的跑步数据
- 操作步骤:
  1. 执行 `uv run nanobotrun analysis hrv --days 90`
- 预期结果: 显示90天HRV分析结果
- 验证要点: 长期趋势可见

## UAT-074: 心率恢复分析
- 优先级: P0
- 前置条件: 已导入含心率数据的跑步记录
- 操作步骤:
  1. 执行 `uv run nanobotrun analysis hr-recovery`
- 预期结果: 显示心率恢复分析结果
- 验证要点: 恢复速率数值合理

## UAT-075: 疲劳度评估
- 优先级: P0
- 前置条件: 已导入近期跑步数据
- 操作步骤:
  1. 执行 `uv run nanobotrun analysis fatigue`
- 预期结果: 显示疲劳度评分和恢复建议
- 验证要点: 疲劳度评分0-100范围，建议合理

## UAT-076: 恢复状态查看
- 优先级: P0
- 前置条件: 已导入近期跑步数据
- 操作步骤:
  1. 执行 `uv run nanobotrun analysis recovery`
- 预期结果: 显示恢复状态评估
- 验证要点: 恢复状态为green/yellow/red之一

## UAT-077: 今日身体状态
- 优先级: P0
- 前置条件: 已导入近期跑步数据
- 操作步骤:
  1. 执行 `uv run nanobotrun status today`
- 预期结果: 显示今日身体状态面板（恢复状态/疲劳度/数据质量/训练建议/预警）
- 验证要点: 面板完整显示所有字段，数值合理

## UAT-078: 本周身体状态摘要
- 优先级: P1
- 前置条件: 已导入本周跑步数据
- 操作步骤:
  1. 执行 `uv run nanobotrun status weekly`
- 预期结果: 显示本周身体状态摘要
- 验证要点: 周汇总数据合理

## UAT-079: 身体信号 - 数据不足场景
- 优先级: P1
- 前置条件: 无跑步数据或数据极少
- 操作步骤:
  1. 清空测试数据目录
  2. 执行 `uv run nanobotrun status today`
- 预期结果: 显示数据不足提示，不崩溃
- 验证要点: 优雅降级，提示用户导入数据

## UAT-080: 身体信号 - 无心率数据场景
- 优先级: P1
- 前置条件: 已导入跑步数据但无心率信息
- 操作步骤:
  1. 导入不含心率数据的FIT文件
  2. 执行 `uv run nanobotrun analysis hrv --days 7`
- 预期结果: 显示数据不足提示或降级提示
- 验证要点: 不崩溃，给出明确提示
```

- [ ] **Step 2: 创建v0.20 ML预测UAT用例文件**

创建 `docs/test/uat_test_cases/UAT_prediction.md`，包含以下用例：

```markdown
# UAT - ML智能预测模块 (v0.20)

## UAT-081: VDOT趋势预测
- 优先级: P0
- 前置条件: 已导入≥18个月跑步数据(400+条)
- 操作步骤:
  1. 执行 `uv run nanobotrun predict vdot`
- 预期结果: 显示VDOT趋势预测，含ML增强/参数化/基础三种模式结果
- 验证要点: 预测值合理，置信区间显示正常

## UAT-082: VDOT预测 - 数据不足场景
- 优先级: P1
- 前置条件: 跑步数据<200条
- 操作步骤:
  1. 执行 `uv run nanobotrun predict vdot`
- 预期结果: 降级为基础预测模式，显示数据积累建议
- 验证要点: 降级提示清晰，不崩溃

## UAT-083: 比赛成绩预测
- 优先级: P0
- 前置条件: 已导入充足跑步数据
- 操作步骤:
  1. 执行 `uv run nanobotrun predict race`
- 预期结果: 显示5K/10K/半马/全马预测成绩
- 验证要点: 预测时间格式HH:MM:SS，配速格式M'SS"/km

## UAT-084: 伤病风险预测
- 优先级: P0
- 前置条件: 已导入充足跑步数据
- 操作步骤:
  1. 执行 `uv run nanobotrun predict injury-risk`
- 预期结果: 显示7日/28日伤病风险百分比和风险因子
- 验证要点: 风险值0-100%，风险因子可解释

## UAT-085: 训练响应预测
- 优先级: P0
- 前置条件: 已导入充足跑步数据
- 操作步骤:
  1. 执行 `uv run nanobotrun predict response --type threshold --duration 60 --intensity high`
- 预期结果: 显示VDOT影响/疲劳影响/恢复时间/伤病风险增量
- 验证要点: 各项数值合理，恢复时间>0

## UAT-086: 预测状态总览
- 优先级: P0
- 前置条件: 已导入跑步数据
- 操作步骤:
  1. 执行 `uv run nanobotrun predict status`
- 预期结果: 显示三模型就绪状态和数据充足度
- 验证要点: VDOT/比赛/伤病三项状态清晰

## UAT-087: 模型状态查看
- 优先级: P1
- 前置条件: 已训练或未训练模型
- 操作步骤:
  1. 执行 `uv run nanobotrun predict model status --type all`
- 预期结果: 显示模型状态表格（类型/状态/版本/训练时间/样本数/验证误差）
- 验证要点: 表格完整，状态与实际一致

## UAT-088: 模型训练 - VDOT
- 优先级: P1
- 前置条件: 已导入充足跑步数据(≥400条)
- 操作步骤:
  1. 执行 `uv run nanobotrun predict model train --type vdot`
- 预期结果: 训练成功，显示训练完成消息
- 验证要点: 训练完成无报错，耗时<60秒

## UAT-089: 模型训练 - 伤病
- 优先级: P1
- 前置条件: 已导入充足跑步数据
- 操作步骤:
  1. 执行 `uv run nanobotrun predict model train --type injury`
- 预期结果: 训练成功，显示训练完成消息
- 验证要点: 训练完成无报错

## UAT-090: 模型回滚
- 优先级: P1
- 前置条件: 已训练至少2个版本的模型
- 操作步骤:
  1. 执行 `uv run nanobotrun predict model rollback --type vdot`
- 预期结果: 回滚成功，显示回滚消息
- 验证要点: 回滚后模型版本号减小

## UAT-091: 预测 - 数据不足降级链路
- 优先级: P0
- 前置条件: 数据量分别处于L1/L2/L3层级
- 操作步骤:
  1. L3(<200条): 执行 `uv run nanobotrun predict vdot` → 基础模式
  2. L2(200-400条): 执行 `uv run nanobotrun predict vdot` → 参数化模式
  3. L1(400+条): 执行 `uv run nanobotrun predict vdot` → ML增强模式
- 预期结果: 各层级自动降级到对应模式
- 验证要点: 降级逻辑正确，提示清晰
```

- [ ] **Step 3: 创建v0.21数字孪生UAT用例文件**

创建 `docs/test/uat_test_cases/UAT_twin.md`，包含以下用例：

```markdown
# UAT - 数字孪生引擎模块 (v0.21)

## UAT-092: 跑者状态快照
- 优先级: P0
- 前置条件: 已导入充足跑步数据
- 操作步骤:
  1. 执行 `uv run nanobotrun twin snapshot`
- 预期结果: 显示5维度跑者状态向量面板（体能/负荷/身体信号/风险/训练模式）
- 验证要点: 5个维度数据完整，VDOT/CTL/ATL/TSB/ACWR/疲劳度/风险值均显示

## UAT-093: What-If推演 - 系统计划引用
- 优先级: P0
- 前置条件: 已有训练计划(plan_id)
- 操作步骤:
  1. 执行 `uv run nanobotrun twin simulate --plan-id <plan_id>`
- 预期结果: 显示推演结果（VDOT变化/风险变化/恢复余量/综合评分）
- 验证要点: 推演结果数值合理，综合评分0-100

## UAT-094: What-If推演 - 手动构建计划
- 优先级: P0
- 前置条件: 已导入充足跑步数据
- 操作步骤:
  1. 执行 `uv run nanobotrun twin simulate --name "测试计划" --weeks '[{"weekly_volume_km":50,"easy_ratio":0.7,"tempo_ratio":0.15,"interval_ratio":0.15,"long_run_km":25}]'`
- 预期结果: 显示推演结果
- 验证要点: 推演完成无报错，结果合理

## UAT-095: What-If推演 - 不同预测模式
- 优先级: P1
- 前置条件: 已导入充足跑步数据
- 操作步骤:
  1. 执行 `uv run nanobotrun twin simulate --name "基础模式" --weeks '[{"weekly_volume_km":40,"easy_ratio":0.8,"tempo_ratio":0.1,"interval_ratio":0.1,"long_run_km":20}]' --type basic`
  2. 执行同上但 `--type parametric`
  3. 执行同上但 `--type ml_enhanced`
- 预期结果: 三种模式均返回推演结果，精度递增
- 验证要点: 降级链路正常，basic最简，ml_enhanced最详

## UAT-096: 多计划对比 - 系统计划引用
- 优先级: P0
- 前置条件: 已有≥2个训练计划
- 操作步骤:
  1. 执行 `uv run nanobotrun twin compare --plan-ids plan_001,plan_002`
- 预期结果: 显示对比表格和推荐方案
- 验证要点: 对比维度完整，推荐方案有理由

## UAT-097: 多计划对比 - 手动构建
- 优先级: P1
- 前置条件: 已导入充足跑步数据
- 操作步骤:
  1. 执行 `uv run nanobotrun twin compare --plans '[{"name":"保守","weeks":[{"weekly_volume_km":30,"easy_ratio":0.8,"tempo_ratio":0.1,"interval_ratio":0.1,"long_run_km":15}]},{"name":"激进","weeks":[{"weekly_volume_km":60,"easy_ratio":0.6,"tempo_ratio":0.2,"interval_ratio":0.2,"long_run_km":30}]}]'`
- 预期结果: 显示两个计划对比结果
- 验证要点: 对比结果合理，推荐方案有依据

## UAT-098: 孪生 - 数据不足场景
- 优先级: P1
- 前置条件: 无跑步数据或数据极少
- 操作步骤:
  1. 清空测试数据目录
  2. 执行 `uv run nanobotrun twin snapshot`
- 预期结果: 显示数据不足提示或降级结果
- 验证要点: 不崩溃，给出明确提示

## UAT-099: 孪生 - 状态向量缓存验证
- 优先级: P1
- 前置条件: 已导入充足跑步数据
- 操作步骤:
  1. 执行 `uv run nanobotrun twin snapshot`（首次，应计算）
  2. 立即再次执行 `uv run nanobotrun twin snapshot`（应命中缓存）
- 预期结果: 第二次执行明显更快
- 验证要点: 缓存文件存在于 `~/.nanobot-runner/twin/state_vector.json`

## UAT-100: 孪生 - 推演结果合理性
- 优先级: P0
- 前置条件: 已导入充足跑步数据
- 操作步骤:
  1. 执行保守计划推演（低周跑量30km）
  2. 执行激进计划推演（高周跑量70km）
  3. 对比两者VDOT变化和风险变化
- 预期结果: 激进计划VDOT提升更大但风险更高
- 验证要点: 推演逻辑符合运动科学常识
```

- [ ] **Step 4: 更新UAT测试指南覆盖v0.19-v0.21**

修改 `docs/test/用户验收测试指南.md`，在测试范围表格中新增：

| 模块 | 覆盖功能 | 优先级 | 用例编号 |
|------|---------|--------|---------|
| 身体信号分析(v0.19) | HRV分析/心率恢复/疲劳度/恢复状态/身体状态 | P0 | UAT-071 ~ UAT-080 |
| ML智能预测(v0.20) | VDOT预测/比赛预测/伤病预测/训练响应/模型管理 | P0 | UAT-081 ~ UAT-091 |
| 数字孪生(v0.21) | 状态快照/What-If推演/计划对比 | P0 | UAT-092 ~ UAT-100 |
| Gateway/Agent增强 | Gateway异常/Agent Chat增强/性能边界 | P0/P1 | UAT-101 ~ UAT-115 |

更新用例总数为 70(原有) + 30(v0.19~v0.21) + 15(Gateway/Agent增强) = 115 个

- [ ] **Step 5: 创建UAT反馈记录表模板**

创建 `docs/test/UAT反馈记录表.md`：

```markdown
# v0.22.0 UAT 反馈记录表

> **测试日期**: 2026-05-XX
> **测试环境**: Windows / Python 3.11+ / uv
> **测试模式**: AI Agent + 用户交互

## 反馈记录

| 用例ID | 模块 | 执行时间 | CLI命令 | 预期结果 | 实际结果 | 用户判定 | 用户评论 | 痛点标记 |
|--------|------|---------|---------|---------|---------|---------|---------|---------|
| UAT-001 | 数据导入 | | | | | | | |

## 痛点汇总

| 痛点ID | 来源用例 | 痛点分类 | 痛点描述 | 严重程度 | 用户原话 |
|--------|---------|---------|---------|---------|---------|
| PAIN-001 | | 功能性/易用性/性能/文档 | | | |

## 用户总体评价

- 最满意的功能：
- 最不满意的功能：
- 改进建议：
```

- [ ] **Step 6: 验证UAT指南完整性**

Run: `uv run python -c "import pathlib; files=list(pathlib.Path('docs/test/uat_test_cases').glob('UAT_*.md')); print(f'UAT用例文件数: {len(files)}'); [print(f'  - {f.name}') for f in sorted(files)]"`
Expected: 输出13个UAT用例文件（10原有 + 3新增）

- [ ] **Step 7: Commit**

```bash
git add docs/test/uat_test_cases/UAT_body_signal.md docs/test/uat_test_cases/UAT_prediction.md docs/test/uat_test_cases/UAT_twin.md docs/test/UAT反馈记录表.md docs/test/用户验收测试指南.md
git commit -m "docs(uat): add v0.19-v0.21 UAT test cases and feedback template"
```

---

### Task S1-02: 准备UAT测试环境

**Files:**
- 无代码文件修改，仅环境操作

- [ ] **Step 1: 创建隔离测试环境**

```powershell
# 清理并创建测试目录
if (Test-Path ".nanobot-runner-uat") { Remove-Item -Recurse -Force ".nanobot-runner-uat" }
New-Item -ItemType Directory -Path ".nanobot-runner-uat\test-data" -Force
New-Item -ItemType Directory -Path ".nanobot-runner-uat\data" -Force

# 设置环境变量
$env:NANOBOT_CONFIG_DIR="$PWD\.nanobot-runner-uat"
$env:NANOBOT_DATA_DIR="$PWD\.nanobot-runner-uat\data"
$env:NANOBOT_WORKSPACE_DIR="$PWD\.nanobot-runner-uat"
$env:PYTHONIOENCODING="utf-8"
```

- [ ] **Step 2: 复制真实FIT文件到测试目录**

```powershell
# 复制15-20个FIT文件（覆盖所有类型：轻松跑/间歇/长距离/恢复跑）
Copy-Item "D:\yecll\Downloads\coros\test-fit-files\*.fit" -Destination ".nanobot-runner-uat\test-data\" -Recurse
```

- [ ] **Step 3: 初始化测试环境**

```powershell
uv run nanobotrun system init
```

Expected: 初始化成功，配置文件生成

- [ ] **Step 4: 导入测试数据**

```powershell
uv run nanobotrun data import .nanobot-runner-uat\test-data\
```

Expected: 成功导入所有FIT文件，显示去重统计

- [ ] **Step 5: 验证数据导入**

```powershell
uv run nanobotrun data stats
```

Expected: 显示导入的跑步记录统计

---

### Task S1-03: 执行UAT-v0.5~v0.17模块验证（T-01-02）— AI Agent+用户交互模式

**Files:**
- Modify: `docs/test/UAT反馈记录表.md`

**执行模式说明：** Agent按模块分组逐个执行UAT用例，每执行完一个用例后，向用户展示执行结果并请求判定。用户可选择 ✅通过/❌失败/⏸️阻塞/⚠️部分通过，并附加评论。Agent将反馈实时记录到反馈记录表。

- [ ] **Step 1: 执行数据导入模块UAT（UAT-001 ~ UAT-005）**

Agent逐个执行以下用例，每个用例执行后收集用户反馈：

```
用例 UAT-001: 单文件导入
  命令: uv run nanobotrun data import <单个FIT文件路径>
  预期: 成功导入，显示导入统计
  → 执行后询问用户: "UAT-001执行完毕，实际结果是否符合预期？(✅通过/❌失败/⏸️阻塞/⚠️部分通过 + 评论)"

用例 UAT-002: 批量导入
  命令: uv run nanobotrun data import <目录路径>
  预期: 批量导入所有FIT文件

用例 UAT-003: 重复导入去重
  命令: uv run nanobotrun data import <已导入的文件>
  预期: SHA256去重，跳过已导入文件

用例 UAT-004: 异常文件处理
  命令: uv run nanobotrun data import <非FIT文件>
  预期: 优雅报错，不影响其他文件

用例 UAT-005: 强制重新导入
  命令: uv run nanobotrun data import <文件> --force
  预期: 忽略去重，强制重新导入
```

每完成一个用例，Agent执行：
1. 记录CLI输出到反馈记录表
2. 询问用户判定
3. 记录用户反馈（判定+评论+痛点标记）
4. 如有痛点，同步记录到痛点汇总表

- [ ] **Step 2: 执行数据查询模块UAT（UAT-006 ~ UAT-008）**

同上交互模式，逐个执行并收集反馈。

- [ ] **Step 3: 执行数据分析模块UAT（UAT-009 ~ UAT-014）**

同上交互模式，逐个执行并收集反馈。重点关注：
- VDOT计算准确性
- TSS/ATL/CTL/TSB计算准确性
- 心率漂移分析结果

- [ ] **Step 4: 执行训练计划与报告模块UAT（UAT-015 ~ UAT-020）**

同上交互模式。特别注意UAT-019（周报告）在v0.18.0 UAT中曾发现BUG-001。

- [ ] **Step 5: 执行MCP工具与Gateway模块UAT（UAT-028 ~ UAT-042）**

同上交互模式。

- [ ] **Step 6: 执行Cron训练提醒模块UAT（UAT-043 ~ UAT-047）**

同上交互模式。

- [ ] **Step 7: 执行AI透明化模块UAT（UAT-048 ~ UAT-051）**

同上交互模式。

- [ ] **Step 8: 执行偏好管理模块UAT（UAT-052 ~ UAT-055）**

同上交互模式。

- [ ] **Step 9: 执行技能管理模块UAT（UAT-056 ~ UAT-060）**

同上交互模式。

- [ ] **Step 10: 执行Gateway异常场景UAT（UAT-101 ~ UAT-106）**

逐个执行并收集用户反馈。这是v0.22新增的Gateway异常场景测试，需重点验证：
- UAT-101: Gateway无LLM配置启动 → 退出码1，提示配置缺失
- UAT-102: Gateway飞书通道连接失败 → 退出码1，提示认证失败
- UAT-103: Gateway消息处理超时 → 响应<30秒，超时友好提示
- UAT-104: Gateway并发消息处理 → 5条消息全部响应，无丢失
- UAT-105: MCP工具不可用降级 → 返回降级提示，不崩溃
- UAT-106: Gateway处理超长消息 → 拒绝/截断，不崩溃

**前置条件**: 需要Gateway服务可用（部分用例需飞书测试环境或Mock）

- [ ] **Step 11: 执行Agent Chat增强UAT（UAT-107 ~ UAT-112）**

逐个执行并收集用户反馈。重点验证：
- UAT-107: Agent Chat无LLM配置启动 → 退出码1，提示配置
- UAT-108: Agent Chat对话中断恢复 → Ctrl+C后重新进入正常
- UAT-109: Agent Chat多轮对话上下文保持 → 5轮对话上下文准确
- UAT-110: Agent Chat上下文窗口溢出 → 50轮后自动截断，不崩溃
- UAT-111: Agent Chat无效输入处理 → 空消息/特殊字符/超长文本友好响应
- UAT-112: Agent Chat工具调用失败 → 明确提示无法完成，不崩溃

- [ ] **Step 12: 执行Gateway/Agent性能边界UAT（UAT-113 ~ UAT-115）**

逐个执行并收集用户反馈。重点验证：
- UAT-113: 大数据量查询性能 → ≥1000条记录查询<10秒
- UAT-114: Gateway长时间运行稳定性 → 4小时加速验证，内存增长<20%
- UAT-115: 消息队列积压处理 → 100条消息按序处理，无丢失

**注意**: UAT-114可降级为4小时加速验证（原计划24小时），UAT-115需编写测试脚本自动化。

- [ ] **Step 13: 汇总v0.5~v0.17模块+Gateway/Agent增强UAT反馈**

将所有收集到的用户反馈整理到 `docs/test/UAT反馈记录表.md`，统计：
- 各模块通过率
- 失败用例清单
- 痛点汇总
- 用户总体评价
- Gateway/Agent异常用例通过率（P0必须100%）

---

### Task S1-04: 执行UAT-v0.18~v0.21模块验证（T-01-03）— AI Agent+用户交互模式

**Files:**
- Modify: `docs/test/UAT反馈记录表.md`

- [ ] **Step 1: 执行数据可视化模块UAT（UAT-061 ~ UAT-065）**

逐个执行并收集用户反馈。重点关注v0.18.0 UAT中发现的BUG-002/003/004是否已修复。

- [ ] **Step 2: 执行数据导出模块UAT（UAT-066 ~ UAT-070）**

逐个执行并收集用户反馈。

- [ ] **Step 3: 执行身体信号分析模块UAT（UAT-071 ~ UAT-080）**

逐个执行并收集用户反馈。这是v0.19新增模块，需重点验证：
- HRV分析数值合理性
- 疲劳度评估与主观感受一致性
- 数据不足场景的降级处理

- [ ] **Step 4: 执行ML智能预测模块UAT（UAT-081 ~ UAT-091）**

逐个执行并收集用户反馈。这是v0.20新增模块，需重点验证：
- 三层降级策略（ML增强/参数化/基础）
- 模型训练和回滚流程
- 预测结果合理性

- [ ] **Step 5: 执行数字孪生模块UAT（UAT-092 ~ UAT-100）**

逐个执行并收集用户反馈。这是v0.21新增模块，需重点验证：
- 5维度状态向量完整性
- What-If推演结果合理性
- 计划对比推荐逻辑
- 缓存机制有效性

- [ ] **Step 6: 汇总v0.18~v0.21模块UAT反馈**

整理到反馈记录表，统计新增模块通过率。

---

### Task S1-05: 执行UAT-性能测试（T-01-04）

**Files:**
- Create: `docs/test/性能测试报告_v0.22.0.md`

- [ ] **Step 1: ML预测性能测试**

```powershell
# 测试VDOT预测响应时间
Measure-Command { uv run nanobotrun predict vdot }
```

Expected: <5秒

- [ ] **Step 2: What-If推演性能测试**

```powershell
# 测试推演响应时间
Measure-Command { uv run nanobotrun twin simulate --name "性能测试" --weeks '[{"weekly_volume_km":50,"easy_ratio":0.7,"tempo_ratio":0.15,"interval_ratio":0.15,"long_run_km":25}]' }
```

Expected: <10秒

- [ ] **Step 3: 状态聚合性能测试**

```powershell
# 测试状态快照响应时间
Measure-Command { uv run nanobotrun twin snapshot }
```

Expected: <3秒（首次计算）；<1秒（缓存命中）

- [ ] **Step 4: 批量导入性能测试**

```powershell
# 测试批量导入响应时间
Measure-Command { uv run nanobotrun data import .nanobot-runner-uat\test-data\ }
```

Expected: 单文件<2秒，批量20文件<30秒

- [ ] **Step 5: Gateway并发处理性能测试**

```powershell
# 测试Gateway并发消息响应时间（需飞书测试环境或Mock）
# 发送5条并发消息，测量最长响应时间
# Expected: 每条响应<15秒
```

- [ ] **Step 6: 记录性能测试结果并收集用户反馈**

将性能数据记录到 `docs/test/性能测试报告_v0.22.0.md`，询问用户对性能是否满意。

- [ ] **Step 7: Commit**

```bash
git add docs/test/性能测试报告_v0.22.0.md
git commit -m "docs(perf): add v0.22.0 performance test report"
```

---

### Task S1-06: 生成UAT测试报告（T-01-05）

**Files:**
- Create: `docs/test/UAT测试执行报告_v0.22.0.md`
- Create: `docs/test/缺陷跟踪表_v0.22.0.md`

- [ ] **Step 1: 汇总UAT测试数据**

从反馈记录表提取：
- 总用例数/通过数/失败数/阻塞数
- P0/P1分别的通过率
- 各模块通过率

- [ ] **Step 2: 创建缺陷跟踪表**

创建 `docs/test/缺陷跟踪表_v0.22.0.md`：

```markdown
# v0.22.0 缺陷跟踪表

| Bug ID | 关联用例 | 模块 | 严重等级 | 标题 | 状态 | 修复人 | 修复日期 | 回归结果 |
|--------|---------|------|---------|------|------|-------|---------|---------|
| BUG-2201 | | | 致命/严重/一般/轻微 | | 待修复 | | | |
```

- [ ] **Step 3: 生成UAT测试执行报告**

创建 `docs/test/UAT测试执行报告_v0.22.0.md`，包含：
1. 测试概述（范围/环境/人员）
2. 测试执行统计（模块维度+版本维度+优先级维度）
3. P0用例执行详情
4. P1用例执行详情
5. 失败用例分析
6. Bug清单（关联缺陷跟踪表）
7. 用户反馈摘要（来自反馈记录表）
8. 风险评估
9. 结论与建议

- [ ] **Step 4: 验证准出条件**

检查：
- [ ] P0用例100%已执行并记录
- [ ] P1用例≥90%已执行并记录
- [ ] 所有失败用例已记录到缺陷跟踪表
- [ ] 用户反馈已收集到反馈记录表

- [ ] **Step 5: Commit**

```bash
git add docs/test/UAT测试执行报告_v0.22.0.md docs/test/缺陷跟踪表_v0.22.0.md docs/test/UAT反馈记录表.md
git commit -m "docs(uat): add v0.22.0 UAT execution report and defect tracking"
```

---

## Sprint 2：缺陷收敛+质量兜底（第3-4周）

**交付目标:** 缺陷收敛+质量兜底完成
**准入条件:** Sprint 1准出通过（UAT报告输出，P0用例100%记录）
**准出条件:** 致命/严重缺陷清零；质量兜底报告输出

### Task S2-01: 缺陷分级与分配（T-02-01）

**Files:**
- Modify: `docs/test/缺陷跟踪表_v0.22.0.md`

- [ ] **Step 1: 按四级标准对UAT缺陷分级**

对缺陷跟踪表中每个Bug按以下标准分级：
- **致命**: 系统崩溃/数据丢失/核心功能完全不可用
- **严重**: 核心功能异常/计算结果错误/数据不一致
- **一般**: 非核心功能异常/显示错误/体验不佳
- **轻微**: UI细节/文案/建议性改进

- [ ] **Step 2: 分配修复优先级**

按分级确定修复顺序：
1. 致命 → 立即修复（P0）
2. 严重 → 本迭代必须修复（P0）
3. 一般 → 修复率≥80%（P1）
4. 轻微 → 视情况修复（P2）

- [ ] **Step 3: 更新缺陷跟踪表**

补充每个Bug的分级标注和修复优先级。

---

### Task S2-02: 修复致命/严重缺陷（T-02-02）

**Files:**
- 修改: `src/core/` 和 `src/cli/` 中对应模块的代码
- 修改: `tests/` 中对应测试文件

**TDD流程：** 每个缺陷修复必须遵循 RED→GREEN→REFACTOR 循环。

- [ ] **Step 1: 对每个致命/严重缺陷执行TDD修复**

对于每个致命/严重Bug（BUG-2201, BUG-2202, ...），执行：

1. **RED - 编写失败测试**：编写能复现Bug的单元测试
   ```python
   def test_bug_2201_weekly_report_vdot_trend():
       """复现BUG-2201: 周报告VDOT趋势访问方式错误"""
       # ... 复现步骤
       result = handler.generate_weekly_report()
       assert result is not None  # 不应抛出AttributeError
   ```

2. **运行测试确认失败**：`uv run pytest tests/path/test.py::test_bug_2201 -v`

3. **GREEN - 编写最小修复代码**：修改源码使测试通过

4. **运行测试确认通过**：`uv run pytest tests/path/test.py::test_bug_2201 -v`

5. **REFACTOR - 重构优化**：确保代码符合规范

6. **运行全量测试**：`uv run pytest tests/unit/ -v`

- [ ] **Step 2: 运行lint和typecheck**

```powershell
uv run ruff check src/ tests/
uv run mypy src/ --ignore-missing-imports
```

Expected: 无错误

- [ ] **Step 3: 更新缺陷跟踪表**

将已修复的Bug状态更新为"已修复"，记录修复日期。

- [ ] **Step 4: Commit每个修复**

```bash
git add src/core/xxx/yyy.py tests/unit/xxx/test_yyy.py
git commit -m "fix(xxx): resolve BUG-2201 weekly report VdotTrendItem access error"
```

---

### Task S2-03: 修复一般缺陷（T-02-03）

**Files:**
- 修改: `src/core/` 和 `src/cli/` 中对应模块的代码
- 修改: `tests/` 中对应测试文件

- [ ] **Step 1: 对每个一般缺陷执行TDD修复**

同S2-02的TDD流程，修复率目标≥80%。

- [ ] **Step 2: 运行lint和typecheck**

```powershell
uv run ruff check src/ tests/
uv run mypy src/ --ignore-missing-imports
```

- [ ] **Step 3: 更新缺陷跟踪表**

- [ ] **Step 4: Commit每个修复**

---

### Task S2-04: 缺陷回归验证（T-02-04）

**Files:**
- Create: `docs/architecture/review/回归验证报告_v0.22.0.md`

- [ ] **Step 1: 执行全量单元测试**

```powershell
uv run pytest tests/unit/ -v --tb=short
```

Expected: 全部通过

- [ ] **Step 2: 对每个已修复Bug执行回归验证**

逐个执行原UAT失败用例，确认修复有效：
- 重新执行对应UAT用例的CLI命令
- 验证预期结果
- 检查是否引入新问题

- [ ] **Step 3: 运行集成测试**

```powershell
uv run pytest tests/integration/ -v --tb=short
```

Expected: 全部通过

- [ ] **Step 4: 生成回归验证报告**

创建 `docs/architecture/review/回归验证报告_v0.22.0.md`，包含：
- 已修复Bug清单及回归结果
- 新引入问题清单（如有）
- 全量测试执行结果

- [ ] **Step 5: Commit**

```bash
git add docs/architecture/review/回归验证报告_v0.22.0.md
git commit -m "docs(review): add v0.22.0 regression verification report"
```

---

### Task S2-05: 边界测试补充（T-03-01）

**Files:**
- Create: `tests/unit/test_boundary_core.py`
- Create: `tests/unit/test_boundary_prediction.py`
- Create: `tests/unit/test_boundary_twin.py`

- [ ] **Step 1: 编写核心计算边界测试**

创建 `tests/unit/test_boundary_core.py`，覆盖：

```python
class TestVDOTBoundary:
    def test_vdot_zero_distance(self): ...
    def test_vdot_extreme_pace(self): ...
    def test_vdot_minimum_distance_1500m(self): ...

class TestTSSBoundary:
    def test_tss_zero_duration(self): ...
    def test_tss_extreme_if(self): ...

class TestLoadBoundary:
    def test_ctl_no_sessions(self): ...
    def test_atl_single_session(self): ...
    def test_tsb_extreme_values(self): ...
```

- [ ] **Step 2: 编写预测模块边界测试**

创建 `tests/unit/test_boundary_prediction.py`，覆盖：

```python
class TestPredictionBoundary:
    def test_predict_no_data(self): ...
    def test_predict_single_session(self): ...
    def test_predict_extreme_vdot(self): ...
    def test_injury_risk_all_zero_features(self): ...
```

- [ ] **Step 3: 编写孪生模块边界测试**

创建 `tests/unit/test_boundary_twin.py`，覆盖：

```python
class TestTwinBoundary:
    def test_snapshot_no_data(self): ...
    def test_simulate_zero_volume(self): ...
    def test_simulate_extreme_volume(self): ...
    def test_compare_single_plan(self): ...
    def test_compare_five_plans_limit(self): ...
```

- [ ] **Step 4: 运行边界测试**

```powershell
uv run pytest tests/unit/test_boundary_*.py -v
```

Expected: 全部通过

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_boundary_core.py tests/unit/test_boundary_prediction.py tests/unit/test_boundary_twin.py
git commit -m "test(boundary): add boundary test cases for core/prediction/twin modules"
```

---

### Task S2-06: 性能基线建立（T-03-02）

**Files:**
- Create: `docs/test/性能基线_v0.22.0.md`

- [ ] **Step 1: 测量关键操作性能基准**

使用PowerShell的 `Measure-Command` 测量：

| 操作 | 命令 | 基准值 |
|------|------|--------|
| ML-VDOT预测 | `nanobotrun predict vdot` | <5秒 |
| What-If推演 | `nanobotrun twin simulate ...` | <10秒 |
| 状态聚合 | `nanobotrun twin snapshot` | <3秒 |
| 批量导入(20文件) | `nanobotrun data import ...` | <30秒 |
| 单文件导入 | `nanobotrun data import <file>` | <2秒 |
| VDOT分析 | `nanobotrun analysis vdot` | <2秒 |
| 训练负荷 | `nanobotrun analysis load` | <2秒 |
| 周报告 | `nanobotrun report weekly` | <5秒 |
| HRV分析 | `nanobotrun analysis hrv` | <3秒 |
| 伤病预测 | `nanobotrun predict injury-risk` | <5秒 |

- [ ] **Step 2: 记录性能基线到文档**

创建 `docs/test/性能基线_v0.22.0.md`，记录每个操作的平均响应时间、最大响应时间、测试数据量。

- [ ] **Step 3: Commit**

```bash
git add docs/test/性能基线_v0.22.0.md
git commit -m "docs(perf): establish v0.22.0 performance baseline"
```

---

### Task S2-07: 数据一致性验证（T-03-03）

**Files:**
- Create: `tests/integration/test_data_consistency.py`

- [ ] **Step 1: 编写数据一致性验证测试**

创建 `tests/integration/test_data_consistency.py`：

```python
class TestDataConsistency:
    def test_vdot_calculation_consistency(self):
        """验证VDOT计算与v0.21基线一致"""

    def test_tss_calculation_consistency(self):
        """验证TSS计算与v0.21基线一致"""

    def test_ctl_atl_tsb_consistency(self):
        """验证CTL/ATL/TSB计算与v0.21基线一致"""

    def test_training_load_consistency(self):
        """验证训练负荷指标与v0.21基线一致"""
```

- [ ] **Step 2: 运行一致性验证测试**

```powershell
uv run pytest tests/integration/test_data_consistency.py -v
```

Expected: 全部通过

- [ ] **Step 3: 记录不一致项（如有）**

对不一致项进行根因分析，记录到质量兜底报告中。

- [ ] **Step 4: Commit**

```bash
git add tests/integration/test_data_consistency.py
git commit -m "test(consistency): add data consistency verification tests"
```

---

### Task S2-08: 历史数据兼容性验证（T-03-04）

**Files:**
- Create: `tests/integration/test_backward_compatibility.py`

- [ ] **Step 1: 编写兼容性验证测试**

创建 `tests/integration/test_backward_compatibility.py`：

```python
class TestBackwardCompatibility:
    def test_v019_data_loading(self):
        """验证v0.19及之前的数据可正常加载"""

    def test_parquet_schema_compatibility(self):
        """验证Parquet文件Schema向后兼容"""

    def test_config_migration(self):
        """验证配置文件迁移兼容性"""
```

- [ ] **Step 2: 运行兼容性验证测试**

```powershell
uv run pytest tests/integration/test_backward_compatibility.py -v
```

Expected: 全部通过

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_backward_compatibility.py
git commit -m "test(compat): add backward compatibility verification tests"
```

---

### Task S2-09: 文档完整性检查（T-03-05）

**Files:**
- Create: `docs/architecture/review/质量兜底报告_v0.22.0.md`

- [ ] **Step 1: 检查功能-文档映射完整性**

逐模块检查：

| 模块 | CLI命令文档 | API文档 | 用户指南 | 状态 |
|------|-----------|--------|---------|------|
| 数据导入/查询 | ✅/❌ | ✅/❌ | ✅/❌ | |
| 数据分析 | ✅/❌ | ✅/❌ | ✅/❌ | |
| 训练计划 | ✅/❌ | ✅/❌ | ✅/❌ | |
| 报告生成 | ✅/❌ | ✅/❌ | ✅/❌ | |
| MCP/Gateway | ✅/❌ | ✅/❌ | ✅/❌ | |
| Cron提醒 | ✅/❌ | ✅/❌ | ✅/❌ | |
| 透明化 | ✅/❌ | ✅/❌ | ✅/❌ | |
| 偏好管理 | ✅/❌ | ✅/❌ | ✅/❌ | |
| 技能管理 | ✅/❌ | ✅/❌ | ✅/❌ | |
| 可视化 | ✅/❌ | ✅/❌ | ✅/❌ | |
| 导出 | ✅/❌ | ✅/❌ | ✅/❌ | |
| 身体信号(v0.19) | ✅/❌ | ✅/❌ | ✅/❌ | |
| ML预测(v0.20) | ✅/❌ | ✅/❌ | ✅/❌ | |
| 数字孪生(v0.21) | ✅/❌ | ✅/❌ | ✅/❌ | |

- [ ] **Step 2: 补充缺失文档**

对检查中发现的缺失文档进行补充更新。

- [ ] **Step 3: 生成质量兜底报告**

创建 `docs/architecture/review/质量兜底报告_v0.22.0.md`，汇总：
- 边界测试结果
- 性能基线数据
- 数据一致性验证结果
- 兼容性验证结果
- 文档完整性检查结果
- 质量评估结论

- [ ] **Step 4: 验证准出条件**

检查：
- [ ] 致命/严重缺陷100%修复
- [ ] 一般缺陷修复率≥80%
- [ ] 边界测试全部通过
- [ ] 性能基线已建立
- [ ] 数据一致性验证通过
- [ ] 兼容性验证通过
- [ ] 文档完整性100%

- [ ] **Step 5: Commit**

```bash
git add docs/architecture/review/质量兜底报告_v0.22.0.md
git commit -m "docs(quality): add v0.22.0 quality assurance report"
```

---

## Sprint 3：需求洞察+反馈改进（第5-6周）

**交付目标:** 需求洞察+反馈改进完成
**准入条件:** Sprint 2准出通过（致命/严重缺陷清零；质量兜底报告输出）
**准出条件:** 需求洞察报告+改进实现报告输出

### Task S3-01: 收集UAT反馈与痛点（T-04-01）

**Files:**
- Modify: `docs/test/UAT反馈记录表.md`

- [ ] **Step 1: 整理Sprint 1收集的用户反馈**

从UAT反馈记录表中提取所有用户评论和痛点标记，按分类整理：

| 分类 | 定义 | 示例 |
|------|------|------|
| 功能性 | 功能缺失或不符合预期 | "推演结果无法保存" |
| 易用性 | 操作复杂或理解困难 | "命令参数太多记不住" |
| 性能 | 响应慢或资源占用高 | "模型训练时间太长" |
| 文档 | 文档缺失或不清晰 | "不知道怎么设置环境变量" |

- [ ] **Step 2: 补充收集用户反馈**

通过以下渠道补充：
1. 回顾Sprint 1 UAT执行过程中的用户评论
2. 与用户进行1次深度访谈（30分钟），聚焦：
   - 最常用的3个功能
   - 最不满意的3个体验
   - 最期望的3个改进
3. 整理访谈记录到反馈记录表

- [ ] **Step 3: 形成痛点清单**

输出结构化痛点清单，每个痛点包含：
- 痛点ID
- 来源（UAT用例/访谈/观察）
- 分类（功能性/易用性/性能/文档）
- 描述
- 严重程度（高/中/低）
- 用户原话

---

### Task S3-02: 痛点分析与需求转化（T-04-02）

**Files:**
- Create: `docs/requirements/需求洞察报告_v0.22.0.md`（初稿）

- [ ] **Step 1: 对每个痛点进行根因分析**

使用5-Why方法分析痛点根因：

```
痛点: "推演结果无法保存"
  Why1: 为什么无法保存？→ 推演命令没有--output参数
  Why2: 为什么没有--output参数？→ v0.21未实现导出功能
  Why3: 为什么未实现？→ 优先级低于核心推演功能
  根因: 功能缺失，需新增推演结果导出能力
```

- [ ] **Step 2: 优先级排序**

按 影响范围 × 解决价值 矩阵排序：

| 痛点 | 影响范围(1-5) | 解决价值(1-5) | 综合得分 | 优先级 |
|------|-------------|-------------|---------|--------|
| PAIN-001 | | | | |

- [ ] **Step 3: 转化为需求条目**

将高优先级痛点转化为具体需求条目：

```markdown
## 新需求条目

### REQ-NEW-001: [需求名称]
- 来源痛点: PAIN-XXX
- 需求描述: [具体描述]
- 验收标准: [可测试的标准]
- 建议版本: v0.23/v0.24/待定
- 预估工时: Xh
```

目标：识别≥3个有效痛点，形成≥2个新需求条目

---

### Task S3-03: 输出需求洞察报告（T-04-03）

**Files:**
- Create: `docs/requirements/需求洞察报告_v0.22.0.md`

- [ ] **Step 1: 编写需求洞察报告**

报告结构：
1. **概述**：洞察方法、数据来源、时间范围
2. **痛点清单**：分类汇总、严重程度分布
3. **根因分析**：每个痛点的5-Why分析
4. **优先级排序**：影响范围×解决价值矩阵
5. **新需求条目**：≥2个具体需求条目
6. **改进建议**：短期可落地+长期规划
7. **附录**：用户原话、访谈记录

- [ ] **Step 2: 验证洞察质量**

检查：
- [ ] 痛点识别≥3个
- [ ] 新需求条目≥2个
- [ ] 每个痛点有根因分析
- [ ] 优先级排序有量化依据

- [ ] **Step 3: Commit**

```bash
git add docs/requirements/需求洞察报告_v0.22.0.md
git commit -m "docs(insight): add v0.22.0 requirement insight report"
```

---

### Task S3-04: 改进项筛选与排期（T-05-01）

**Files:**
- Modify: `docs/requirements/需求洞察报告_v0.22.0.md`

- [ ] **Step 1: 筛选高优先级改进项**

从需求洞察报告中筛选可在v0.22迭代内完成的改进项：
- 准入标准：工时≤8h + 无架构变更 + 无新依赖
- 排除标准：需新增模块/需架构评审/工时>8h

- [ ] **Step 2: 评估实现成本**

对每个候选改进项评估：
- 涉及文件数
- 代码变更量
- 测试工作量
- 文档更新量

- [ ] **Step 3: 制定排期**

按优先级和工时排期，总工时控制在16h以内（Sprint 3剩余时间）。

---

### Task S3-05: 实现高优先级改进项（T-05-02）

**Files:**
- 修改: `src/` 中对应模块代码
- 修改: `tests/` 中对应测试文件

- [ ] **Step 1: 对每个改进项执行TDD开发**

对每个高优先级改进项，遵循 RED→GREEN→REFACTOR：
1. 编写失败测试
2. 运行测试确认失败
3. 编写最小实现
4. 运行测试确认通过
5. 重构优化
6. 运行全量测试

- [ ] **Step 2: 运行lint和typecheck**

```powershell
uv run ruff check src/ tests/
uv run mypy src/ --ignore-missing-imports
```

- [ ] **Step 3: Commit每个改进项**

```bash
git add src/xxx/yyy.py tests/unit/xxx/test_yyy.py
git commit -m "feat(xxx): implement improvement item - [description]"
```

---

### Task S3-06: 改进效果验证（T-05-03）

**Files:**
- Create: `docs/architecture/review/改进实现报告_v0.22.0.md`

- [ ] **Step 1: 用户验证改进效果**

对每个改进项，邀请用户验证：
1. 执行改进后的CLI命令
2. 对比改进前后的体验
3. 收集用户满意度反馈

- [ ] **Step 2: 生成改进实现报告**

创建 `docs/architecture/review/改进实现报告_v0.22.0.md`，包含：
- 改进项清单及实现状态
- 每个改进项的验证结果
- 用户满意度反馈
- 未完成项说明

- [ ] **Step 3: 验证准出条件**

检查：
- [ ] 高优先级改进项完成率≥80%
- [ ] 每个改进项经过用户验证
- [ ] 需求洞察报告已完成
- [ ] 改进实现报告已输出

- [ ] **Step 4: Commit**

```bash
git add docs/architecture/review/改进实现报告_v0.22.0.md
git commit -m "docs(improvement): add v0.22.0 improvement implementation report"
```

---

## Sprint 4：发布+观察+复盘（第7-9周）

**交付目标:** 发布+观察+复盘
**准入条件:** Sprint 3准出通过（需求洞察报告+改进实现报告输出）
**准出条件:** 发布后观察报告+过程改进建议输出

### Task S4-01: 发布就绪检查（T-06-01）

**Files:**
- Create: `docs/devops/发布就绪检查单_v0.22.0.md`

- [ ] **Step 1: 逐项确认发布就绪条件**

| 检查项 | 状态 | 证据 |
|--------|------|------|
| UAT通过（P0 100%, P1 ≥90%） | ✅/❌ | UAT测试执行报告 |
| 需求洞察完成 | ✅/❌ | 需求洞察报告 |
| 改进完成（≥80%） | ✅/❌ | 改进实现报告 |
| 致命/严重缺陷清零 | ✅/❌ | 缺陷跟踪表 |
| 一般缺陷修复≥80% | ✅/❌ | 缺陷跟踪表 |
| 性能测试通过 | ✅/❌ | 性能测试报告 |
| 边界测试通过 | ✅/❌ | 测试执行结果 |
| 数据一致性验证通过 | ✅/❌ | 一致性验证结果 |
| 兼容性验证通过 | ✅/❌ | 兼容性验证结果 |
| 文档更新完成 | ✅/❌ | 文档完整性检查 |
| 版本号一致 | ✅/❌ | pyproject.toml/README.md/CHANGELOG.md |
| 回滚方案就绪 | ✅/❌ | 回滚方案文档 |

- [ ] **Step 2: 处理未通过项**

对未通过的检查项，评估是否阻塞发布：
- 阻塞项：必须修复后才能发布
- 非阻塞项：记录为已知问题，在发布说明中标注

- [ ] **Step 3: 生成发布就绪检查单**

创建 `docs/devops/发布就绪检查单_v0.22.0.md`

---

### Task S4-02: 发布说明与文档更新（T-06-02）

**Files:**
- Modify: `CHANGELOG.md`
- Modify: `README.md`
- Modify: `pyproject.toml`（版本号）
- Modify: `AGENTS.md`
- Create: `docs/devops/发布报告_v0.22.0.md`

- [ ] **Step 1: 更新版本号**

修改 `pyproject.toml` 中版本号为 `0.22.0`
修改 `README.md` 中版本号
修改 `src/__init__.py` 中 `__version__`

- [ ] **Step 2: 更新CHANGELOG.md**

新增v0.22.0条目：

```markdown
## [0.22.0] - 2026-05-XX

### 质量收口
- 完成v0.5-v0.21全版本UAT验证（115个用例，含Gateway/Agent增强）
- 修复X个致命/严重缺陷，X个一般缺陷
- 建立性能基线（ML预测<5s/推演<10s/聚合<3s）
- 完成数据一致性验证和兼容性验证
- 完成边界测试补充

### 需求洞察
- 识别X个用户痛点
- 形成X个新需求条目
- 实现X个高优先级改进项

### 已知问题
- [列出未修复的轻微缺陷]
```

- [ ] **Step 3: 更新AGENTS.md**

同步更新AGENTS.md中的版本信息和命令参考。

- [ ] **Step 4: 编写发布报告**

创建 `docs/devops/发布报告_v0.22.0.md`，包含：
- 变更摘要
- 升级指南
- 已知问题
- 回滚方案

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml README.md CHANGELOG.md AGENTS.md src/__init__.py docs/devops/
git commit -m "release(v0.22.0): update version, changelog, and release notes"
```

---

### Task S4-03: 发布后7天观察（T-06-03）

**Files:**
- Create: `docs/devops/发布后观察报告_v0.22.0.md`

- [ ] **Step 1: 建立观察机制**

发布后7天内每日检查：
- CLI命令执行是否正常
- 数据导入/分析/预测功能是否正常
- 是否有新的报错或异常

- [ ] **Step 2: 记录观察日志**

每日记录：
| 日期 | 检查项 | 结果 | 异常描述 |
|------|--------|------|---------|
| Day1 | 数据导入 | ✅ | - |
| Day1 | VDOT分析 | ✅ | - |
| ... | | | |

- [ ] **Step 3: 生成观察报告**

7天后创建 `docs/devops/发布后观察报告_v0.22.0.md`：
- 观察期概要
- 每日检查记录
- 发现的问题及处理
- 结论（是否稳定）

- [ ] **Step 4: Commit**

```bash
git add docs/devops/发布后观察报告_v0.22.0.md
git commit -m "docs(release): add v0.22.0 post-release observation report"
```

---

### Task S4-04: v0.22过程复盘（T-07-01）

**Files:**
- Create: `docs/architecture/review/过程复盘_v0.22.0.md`（初稿）

- [ ] **Step 1: 回顾Sprint 1-4执行情况**

按维度复盘：

| 维度 | 回顾要点 |
|------|---------|
| 进度 | 各Sprint是否按时完成？延期原因？ |
| 质量 | UAT通过率是否达标？缺陷修复率？ |
| 流程 | AI Agent+用户交互UAT模式效果？TDD执行情况？ |
| 协作 | 用户反馈收集是否充分？痛点识别是否准确？ |
| 风险 | 是否出现未预见风险？应对是否及时？ |

- [ ] **Step 2: 识别可改进点**

目标：识别≥3个可改进点，每个包含：
- 问题描述
- 根因分析
- 改进建议
- 预期效果

---

### Task S4-05: 输出过程改进建议（T-07-02）

**Files:**
- Create: `docs/architecture/review/过程改进建议_v0.22.0.md`

- [ ] **Step 1: 编写过程改进建议文档**

结构：
1. **复盘总结**：v0.22全过程回顾
2. **可改进点清单**：≥3个改进点
3. **改进建议**：每个改进点的具体建议
4. **后续版本参考**：对v0.23-v0.25的建议
5. **附录**：复盘数据

- [ ] **Step 2: 验证最终准出条件**

检查：
- [ ] 发布后7天内无P0级问题
- [ ] 发布后观察报告已输出
- [ ] 过程改进建议已输出
- [ ] 所有文档已归档

- [ ] **Step 3: Commit**

```bash
git add docs/architecture/review/过程复盘_v0.22.0.md docs/architecture/review/过程改进建议_v0.22.0.md
git commit -m "docs(retro): add v0.22.0 retrospective and process improvement suggestions"
```

---

## 附录A：AI Agent + 用户交互 UAT 执行脚本规范

### Agent执行每个UAT用例的标准流程

```
1. Agent读取用例描述
   → 输出: "正在执行 UAT-XXX: [用例名称]"
   → 输出: "前置条件: [条件描述]"
   → 输出: "操作步骤: [步骤描述]"
   → 输出: "预期结果: [预期描述]"

2. Agent执行CLI命令
   → 在终端执行对应命令
   → 捕获标准输出和错误输出

3. Agent展示执行结果
   → 输出: "执行结果:"
   → 展示CLI输出（截取关键部分）
   → 对比预期结果

4. Agent请求用户判定
   → 使用 AskUserQuestion 工具
   → 问题: "UAT-XXX执行完毕，请判定结果："
   → 选项:
     - ✅ 通过：实际结果与预期一致
     - ❌ 失败：实际结果与预期不一致
     - ⏸️ 阻塞：无法执行
     - ⚠️ 部分通过：核心功能正常但有偏差

5. Agent收集用户评论
   → 如果用户选择 ❌/⏸️/⚠️：
     → 追问: "请描述具体问题或评论："
   → 如果用户选择 ✅：
     → 追问: "是否有改进建议？（可直接回复'无'跳过）"

6. Agent记录反馈
   → 更新 UAT反馈记录表.md
   → 如有痛点标记，同步更新痛点汇总

7. Agent进入下一用例
   → 输出: "---"
   → 回到步骤1
```

### 批量执行模式

当用户希望批量执行多个用例时，Agent可以：
1. 按模块分组执行（如"数据导入模块5个用例"）
2. 每个模块执行完后汇总结果，再询问是否继续下一模块
3. 用户可随时中断，Agent保存当前进度

### 进度保存与恢复

- 每完成一个用例，立即将反馈写入 `UAT反馈记录表.md`
- 中断后恢复时，从反馈记录表中读取已执行用例，跳过已完成的
- 进度文件：`docs/test/UAT反馈记录表.md`

---

## 附录B：版本成功标准速查

| 维度 | 标准 | 测量方式 | 对应Sprint |
|------|------|----------|-----------|
| UAT通过率 | P0用例100%，P1用例≥90% | UAT测试报告 | Sprint 1 |
| 缺陷修复率 | 致命/严重100%，一般≥80% | 缺陷跟踪报告 | Sprint 2 |
| 需求洞察 | 识别≥3个有效痛点，形成≥2个新需求 | 需求洞察报告 | Sprint 3 |
| 反馈改进 | 高优先级改进项完成率≥80% | 改进实现报告 | Sprint 3 |
| 发布质量 | 发布后7天内无P0级问题 | 发布后观察报告 | Sprint 4 |
| 文档完整度 | 100%功能有对应文档 | 文档检查清单 | Sprint 2 |
