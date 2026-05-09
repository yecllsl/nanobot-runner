# v0.20.0 Bug清单

> **版本**: v0.20.0  
> **创建时间**: 2026-05-09  
> **测试轮次**: 第1轮（全量测试）

---

## Bug清单

| Bug ID | 模块 | 严重等级 | 标题 | 复现步骤 | 实际结果 | 预期结果 | 根因分析 | 修复建议 | 状态 | 优先级 | 创建时间 |
|--------|------|---------|------|---------|---------|---------|---------|---------|------|--------|---------|
| BUG-001 | prediction/feature_engine | 一般 | feature_engine.py部分特征提取逻辑未测试覆盖 | 运行覆盖率测试，检查`feature_engine.py` | 覆盖率仅62%，318-428行未覆盖 | 覆盖率应≥80% | 测试用例未覆盖复杂特征提取路径（如多特征组合、边界条件） | 补充测试用例覆盖未覆盖行，特别是`_extract_complex_features`等方法 | 待修复 | P1 | 2026-05-09 |
| BUG-002 | prediction/model_manager | 一般 | model_manager.py异常路径未覆盖 | 运行覆盖率测试，检查`model_manager.py` | 覆盖率78%，77-137行未覆盖 | 覆盖率应≥80% | 模型加载失败、版本不兼容等异常场景未测试 | 补充异常测试用例，模拟模型文件损坏、版本不匹配等场景 | 待修复 | P1 | 2026-05-09 |
| BUG-003 | prediction/config | 一般 | config.py部分配置验证逻辑未测试 | 运行覆盖率测试，检查`config.py` | 覆盖率84%，119-152行未覆盖 | 覆盖率应≥90% | 配置验证的边界条件未测试 | 补充配置验证测试用例 | 待修复 | P2 | 2026-05-09 |
| BUG-004 | 代码规范 | 优化 | prediction模块存在23个ruff导入错误 | 执行`uv run ruff check src/core/prediction/ tests/unit/core/prediction/` | 23个F401/I001错误 | 零警告 | 测试文件存在未使用的导入和导入排序问题 | 执行`uv run ruff check --fix src/core/prediction/ tests/unit/core/prediction/` | 待修复 | P2 | 2026-05-09 |
| BUG-005 | 代码规范 | 优化 | prediction模块8个文件需格式化 | 执行`uv run ruff format --check src/core/prediction/ tests/unit/core/prediction/` | 8个文件需重新格式化 | 所有文件通过格式检查 | 代码风格不一致 | 执行`uv run ruff format src/core/prediction/ tests/unit/core/prediction/` | 待修复 | P2 | 2026-05-09 |

---

## Bug统计

### 按严重等级

| 严重等级 | 数量 | 占比 |
|---------|------|------|
| 致命 | 0 | 0% |
| 严重 | 0 | 0% |
| 一般 | 3 | 60% |
| 优化 | 2 | 40% |
| **合计** | **5** | **100%** |

### 按模块

| 模块 | Bug数 |
|------|-------|
| prediction/feature_engine | 1 |
| prediction/model_manager | 1 |
| prediction/config | 1 |
| 代码规范 | 2 |

### 按状态

| 状态 | 数量 |
|------|------|
| 待修复 | 5 |
| 修复中 | 0 |
| 待回归 | 0 |
| 已闭环 | 0 |
| 已驳回 | 0 |

---

## 修复建议汇总

### 立即修复（P1）

1. **BUG-001**: 补充`feature_engine.py`测试用例，覆盖318-428行
2. **BUG-002**: 补充`model_manager.py`异常路径测试，覆盖77-137行

### 建议修复（P2）

3. **BUG-003**: 补充`config.py`配置验证测试
4. **BUG-004**: 执行`uv run ruff check --fix`自动修复导入错误
5. **BUG-005**: 执行`uv run ruff format`格式化代码
