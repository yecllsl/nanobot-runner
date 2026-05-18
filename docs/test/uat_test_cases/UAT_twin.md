# UAT - 数字孪生引擎模块 (v0.21)

> **模块版本**: v0.21.0
> **用例范围**: UAT-092 ~ UAT-100
> **优先级分布**: P0: 4个, P1: 5个

---

## UAT-092: 跑者状态快照

- **优先级**: P0
- **前置条件**: 已导入充足跑步数据（≥30天）
- **操作步骤**:
  1. 执行 `uv run nanobotrun twin snapshot`
- **预期结果**: 显示5维度跑者状态向量面板：
  - 体能维度：VDOT值、VDOT趋势
  - 负荷维度：CTL、ATL、TSB、ACWR
  - 身体信号：疲劳度、恢复状态
  - 风险维度：7日/28日伤病风险
  - 训练模式：训练频率、跑量分布
- **验证要点**: 5个维度数据完整显示，VDOT/CTL/ATL/TSB/ACWR/疲劳度/风险值均有数值

## UAT-093: What-If推演 - 系统计划引用

- **优先级**: P0
- **前置条件**: 已有训练计划（plan_id），可通过 `nanobotrun plan list` 查看
- **操作步骤**:
  1. 先执行 `uv run nanobotrun plan list` 获取plan_id
  2. 执行 `uv run nanobotrun twin simulate --plan-id <plan_id>`
- **预期结果**: 显示推演结果，包含：
  - VDOT变化（当前→推演后）
  - 风险变化
  - 恢复余量
  - 综合评分（0-100）
- **验证要点**: 推演结果数值合理，综合评分0-100，变化方向符合运动科学

## UAT-094: What-If推演 - 手动构建计划

- **优先级**: P0
- **前置条件**: 已导入充足跑步数据
- **操作步骤**:
  1. 执行 `uv run nanobotrun twin simulate --name "测试计划" --weeks '[{"weekly_volume_km":50,"easy_ratio":0.7,"tempo_ratio":0.15,"interval_ratio":0.15,"long_run_km":25}]'`
- **预期结果**: 显示推演结果面板
- **验证要点**: 推演完成无报错，结果合理（VDOT提升、风险变化、综合评分）

## UAT-095: What-If推演 - 不同预测模式

- **优先级**: P1
- **前置条件**: 已导入充足跑步数据
- **操作步骤**:
  1. 执行 `uv run nanobotrun twin simulate --name "基础模式" --weeks '[{"weekly_volume_km":40,"easy_ratio":0.8,"tempo_ratio":0.1,"interval_ratio":0.1,"long_run_km":20}]' --type basic`
  2. 执行同上但 `--type parametric`
  3. 执行同上但 `--type ml_enhanced`（需已训练模型）
- **预期结果**: 三种模式均返回推演结果，精度递增
- **验证要点**: 降级链路正常，basic最简结果，parametric中等，ml_enhanced最详细

## UAT-096: 多计划对比 - 系统计划引用

- **优先级**: P0
- **前置条件**: 已有≥2个训练计划
- **操作步骤**:
  1. 先执行 `uv run nanobotrun plan list` 获取plan_id列表
  2. 执行 `uv run nanobotrun twin compare --plan-ids <plan_id_1>,<plan_id_2>`
- **预期结果**: 显示对比表格和推荐方案
- **验证要点**: 对比维度完整（VDOT提升40%+风险控制30%+恢复余量20%+恢复状态10%），推荐方案有理由

## UAT-097: 多计划对比 - 手动构建

- **优先级**: P1
- **前置条件**: 已导入充足跑步数据
- **操作步骤**:
  1. 执行 `uv run nanobotrun twin compare --plans '[{"name":"保守","weeks":[{"weekly_volume_km":30,"easy_ratio":0.8,"tempo_ratio":0.1,"interval_ratio":0.1,"long_run_km":15}]},{"name":"激进","weeks":[{"weekly_volume_km":60,"easy_ratio":0.6,"tempo_ratio":0.2,"interval_ratio":0.2,"long_run_km":30}]}]'`
- **预期结果**: 显示两个计划对比结果，含推荐方案
- **验证要点**: 对比结果合理，推荐方案有依据，保守计划风险更低

## UAT-098: 孪生 - 数据不足场景

- **优先级**: P1
- **前置条件**: 无跑步数据或数据极少
- **操作步骤**:
  1. 在空数据环境下执行 `uv run nanobotrun twin snapshot`
- **预期结果**: 显示数据不足提示或降级结果（data_quality=empty/limited）
- **验证要点**: 不崩溃，给出明确提示，状态向量各维度有默认值

## UAT-099: 孪生 - 状态向量缓存验证

- **优先级**: P1
- **前置条件**: 已导入充足跑步数据
- **操作步骤**:
  1. 执行 `uv run nanobotrun twin snapshot`（首次，应触发计算）
  2. 立即再次执行 `uv run nanobotrun twin snapshot`（应命中缓存）
  3. 检查缓存文件 `~/.nanobot-runner/twin/state_vector.json` 是否存在
- **预期结果**: 第二次执行明显更快（缓存命中）
- **验证要点**: 缓存文件存在且内容有效，TTL=24h

## UAT-100: 孪生 - 推演结果合理性

- **优先级**: P0
- **前置条件**: 已导入充足跑步数据
- **操作步骤**:
  1. 执行保守计划推演：`uv run nanobotrun twin simulate --name "保守" --weeks '[{"weekly_volume_km":30,"easy_ratio":0.8,"tempo_ratio":0.1,"interval_ratio":0.1,"long_run_km":15}]'`
  2. 执行激进计划推演：`uv run nanobotrun twin simulate --name "激进" --weeks '[{"weekly_volume_km":70,"easy_ratio":0.5,"tempo_ratio":0.25,"interval_ratio":0.25,"long_run_km":35}]'`
  3. 对比两者VDOT变化和风险变化
- **预期结果**: 激进计划VDOT提升更大但风险更高
- **验证要点**: 推演逻辑符合运动科学常识——高负荷=高收益+高风险
