# 项目Bug清单 - v0.14.0

**版本**: v0.14.0  
**创建日期**: 2026-04-28  
**更新日期**: 2026-04-28  

---

## Bug统计

| 严重等级 | 数量 | 待修复 | 修复中 | 待回归 | 已闭环 | 已驳回 |
|---------|------|--------|--------|--------|--------|--------|
| 致命 | 0 | 0 | 0 | 0 | 0 | 0 |
| 严重 | 0 | 0 | 0 | 0 | 0 | 0 |
| 一般 | 1 | 0 | 0 | 1 | 0 | 0 |
| 优化 | 3 | 0 | 0 | 3 | 0 | 0 |
| **合计** | **4** | **0** | **0** | **4** | **0** | **0** |

---

## Bug详情

### BUG-v0.14.0-001

| 字段 | 内容 |
|-----|------|
| Bug ID | BUG-v0.14.0-001 |
| 所属模块 | src/core/memory/memory_manager.py |
| 严重等级 | 一般 |
| Bug标题 | create_backup()连续调用时版本号相同，导致版本列表只返回1个 |
| 复现步骤 | 1. 初始化MemoryManager 2. 写入记忆内容 3. 调用create_backup() 4. 修改记忆内容 5. 再次调用create_backup() 6. 调用list_versions() |
| 实际结果 | list_versions()返回1个版本 |
| 预期结果 | list_versions()返回2个不同版本 |
| 根因分析 | create_backup()使用`datetime.now().strftime("%Y%m%d_%H%M%S")`生成版本号，两次调用间隔<1秒时版本号相同，导致后一次覆盖前一次 |
| 修复建议 | 版本号生成增加毫秒或随机后缀，如`datetime.now().strftime("%Y%m%d_%H%M%S_%f")`或使用UUID |
| 出现版本 | v0.14.0 |
| 优先级 | P2 |
| 测试人员 | 测试工程师智能体 |
| 创建时间 | 2026-04-28 |
| 状态 | 待回归 |

---

### BUG-v0.14.0-002

| 字段 | 内容 |
|-----|------|
| Bug ID | BUG-v0.14.0-002 |
| 所属模块 | src/core/personality/feedback_loop.py |
| 严重等级 | 优化 |
| Bug标题 | 未使用的导入Personality |
| 复现步骤 | 运行ruff check src/core/personality/feedback_loop.py |
| 实际结果 | F401错误：Personality导入但未使用 |
| 预期结果 | 无未使用导入 |
| 修复建议 | 删除第13行的`Personality,`导入 |
| 优先级 | P3 |
| 测试人员 | 测试工程师智能体 |
| 创建时间 | 2026-04-28 |
| 状态 | 待回归 |

---

### BUG-v0.14.0-003

| 字段 | 内容 |
|-----|------|
| Bug ID | BUG-v0.14.0-003 |
| 所属模块 | src/core/personality/preference_learner.py |
| 严重等级 | 优化 |
| Bug标题 | 未使用的导入datetime.datetime |
| 复现步骤 | 运行ruff check src/core/personality/preference_learner.py |
| 实际结果 | F401错误：datetime.datetime导入但未使用 |
| 预期结果 | 无未使用导入 |
| 修复建议 | 删除第6行的`from datetime import datetime`或确认是否需要使用 |
| 优先级 | P3 |
| 测试人员 | 测试工程师智能体 |
| 创建时间 | 2026-04-28 |
| 状态 | 待回归 |

---

### BUG-v0.14.0-004

| 字段 | 内容 |
|-----|------|
| Bug ID | BUG-v0.14.0-004 |
| 所属模块 | src/core/personality/preference_learner.py |
| 严重等级 | 优化 |
| Bug标题 | 嵌套if语句可合并为单个if（SIM102） |
| 复现步骤 | 运行ruff check src/core/personality/preference_learner.py |
| 实际结果 | SIM102警告：第264-265行嵌套if可合并 |
| 预期结果 | 使用`if current_pref and category in self._category_votes and current_pref in self._category_votes[category]:` |
| 修复建议 | 合并嵌套if为单个if语句 |
| 优先级 | P3 |
| 测试人员 | 测试工程师智能体 |
| 创建时间 | 2026-04-28 |
| 状态 | 待回归 |

---

## 状态说明

- **待修复**: Bug已确认，等待开发工程师修复
- **修复中**: 开发工程师正在修复
- **待回归**: 修复完成，等待测试工程师回归验证
- **已闭环**: 回归测试通过，Bug已关闭
- **已驳回**: Bug无效或无法复现，退回给提交方
