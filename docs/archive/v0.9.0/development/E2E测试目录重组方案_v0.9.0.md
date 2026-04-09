# E2E测试目录重组方案

**创建日期**: 2026-04-09
**创建人**: 架构师智能体
**版本**: v1.0

---

## 📋 执行摘要

本方案提出将E2E测试从按版本组织改为按功能模块组织，以提高测试代码的可维护性和可读性。

---

## 📊 当前目录结构

```
tests/e2e/
├── v0_9_0/                           # v0.9.0版本的E2E测试
│   ├── __init__.py
│   ├── test_cli_split.py             # CLI分层测试
│   ├── test_dependency_injection.py  # 依赖注入测试
│   ├── test_performance_optimization.py  # 性能优化测试
│   └── test_session_repository.py    # Session仓储测试
├── test_performance.py               # 性能测试
├── test_plan_e2e.py                  # 训练计划E2E测试
└── test_user_journey.py              # 用户旅程测试
```

**问题**：
- ⚠️ 按版本组织会导致测试代码冗余
- ⚠️ 测试代码分散，不便于统一管理
- ⚠️ 新版本开发时需要创建新的版本目录

---

## 🎯 目标目录结构

```
tests/e2e/
├── architecture/                     # 架构相关测试
│   ├── __init__.py
│   ├── test_dependency_injection.py  # 依赖注入测试
│   ├── test_cli_layering.py          # CLI分层测试
│   └── test_session_repository.py    # Session仓储测试
├── performance/                      # 性能测试
│   ├── __init__.py
│   ├── test_lazyframe_performance.py # LazyFrame性能测试
│   └── test_query_performance.py     # 查询性能测试
├── user_journey/                     # 用户旅程测试
│   ├── __init__.py
│   └── test_complete_workflow.py     # 完整工作流测试
├── plan/                             # 训练计划测试
│   ├── __init__.py
│   └── test_plan_workflow.py         # 训练计划工作流测试
├── conftest.py                       # E2E测试配置
└── README.md                         # E2E测试说明
```

**优点**：
- ✅ 按功能模块组织，便于查找和维护
- ✅ 测试代码集中，避免冗余
- ✅ 随版本演进更新测试，而不是创建新目录
- ✅ 对于重大架构变更，创建专门的迁移测试

---

## 📝 重组步骤

### Phase 1: 创建新目录结构

```bash
# 创建新目录
mkdir -p tests/e2e/architecture
mkdir -p tests/e2e/performance
mkdir -p tests/e2e/user_journey
mkdir -p tests/e2e/plan

# 创建__init__.py文件
touch tests/e2e/architecture/__init__.py
touch tests/e2e/performance/__init__.py
touch tests/e2e/user_journey/__init__.py
touch tests/e2e/plan/__init__.py
```

### Phase 2: 移动测试文件

```bash
# 架构测试
mv tests/e2e/v0_9_0/test_dependency_injection.py tests/e2e/architecture/
mv tests/e2e/v0_9_0/test_cli_split.py tests/e2e/architecture/test_cli_layering.py
mv tests/e2e/v0_9_0/test_session_repository.py tests/e2e/architecture/

# 性能测试
mv tests/e2e/v0_9_0/test_performance_optimization.py tests/e2e/performance/test_lazyframe_performance.py
mv tests/e2e/test_performance.py tests/e2e/performance/test_query_performance.py

# 用户旅程测试
mv tests/e2e/test_user_journey.py tests/e2e/user_journey/test_complete_workflow.py

# 训练计划测试
mv tests/e2e/test_plan_e2e.py tests/e2e/plan/test_plan_workflow.py
```

### Phase 3: 清理旧目录

```bash
# 删除v0_9_0目录
rm -rf tests/e2e/v0_9_0
```

### Phase 4: 创建配置文件

```bash
# 创建conftest.py
touch tests/e2e/conftest.py

# 创建README.md
touch tests/e2e/README.md
```

### Phase 5: 更新CI配置

```yaml
# .github/workflows/ci.yml
# 无需修改，因为CI配置使用的是 tests/e2e/ 目录
# 会自动执行所有子目录下的测试
```

---

## ⚠️ 潜在影响

### 1. 测试执行

**影响**：
- ✅ CI配置无需修改，会自动执行所有子目录下的测试
- ⚠️ 本地开发时需要更新测试路径

**缓解措施**：
- 更新AGENTS.md中的测试执行命令
- 更新开发指南中的测试说明

### 2. 测试导入

**影响**：
- ⚠️ 测试文件内部的导入路径可能需要更新

**缓解措施**：
- 检查所有测试文件的导入路径
- 更新相对导入为绝对导入

### 3. 文档引用

**影响**：
- ⚠️ 文档中引用的测试路径需要更新

**缓解措施**：
- 更新AGENTS.md中的测试路径
- 更新开发指南中的测试路径

---

## 🎯 验收标准

1. ✅ 所有测试文件已移动到新目录
2. ✅ 所有测试文件可正常执行
3. ✅ CI配置无需修改即可执行测试
4. ✅ 文档已更新测试路径
5. ✅ 旧目录已清理

---

## 📊 风险评估

| 风险 | 等级 | 影响 | 缓解措施 |
|------|------|------|----------|
| 测试执行失败 | 中 | CI流水线失败 | 先在本地验证所有测试可执行 |
| 导入路径错误 | 低 | 测试无法运行 | 检查所有导入路径 |
| 文档不一致 | 低 | 开发者困惑 | 同步更新所有文档 |

---

## 🎉 总结

**建议**：
- ✅ 立即执行重组，提高测试代码的可维护性
- ✅ 先在本地验证所有测试可执行
- ✅ 同步更新所有相关文档

**预期收益**：
- ✅ 测试代码组织更加清晰
- ✅ 避免版本间的测试代码冗余
- ✅ 便于维护和扩展

---

**创建完成时间**: 2026-04-09
**方案版本**: v1.0
**方案状态**: 📋 待执行
