# 测试目录结构规范

**文档版本**: v1.0  
**生效日期**: 2026-03-02  
**适用项目**: Nanobot Runner  
**文档负责人**: 测试工程师

---

## 一、目录结构总览

```
tests/
├── unit/                          # 单元测试目录
│   ├── __init__.py
│   ├── test_cli.py                # CLI模块单元测试
│   ├── test_config.py             # 配置管理单元测试
│   ├── test_parser.py            # FIT解析单元测试
│   ├── test_importer.py           # 数据导入单元测试
│   ├── test_analytics.py          # 分析引擎单元测试
│   ├── test_indexer.py            # 索引管理单元测试
│   ├── test_storage.py            # 存储管理单元测试
│   ├── test_tools.py              # Agent工具单元测试
│   └── test_feishu.py             # 飞书集成单元测试
├── integration/                    # 集成测试目录
│   ├── module/                    # 模块间集成测试
│   │   ├── __init__.py
│   │   ├── test_import_flow.py    # 数据导入流程测试
│   │   ├── test_analytics_flow.py # 分析流程测试
│   │   └── test_cli_flow.py       # CLI流程测试
│   └── scene/                    # 场景级集成测试
│       ├── __init__.py
│       ├── test_full_workflow.py  # 完整业务流程测试
│       └── test_error_handling.py # 错误处理场景测试
├── e2e/                           # 端到端测试目录
│   ├── __init__.py
│   ├── test_user_journey.py       # 用户旅程测试
│   └── test_performance.py        # 性能E2E测试
├── performance/                   # 性能测试目录
│   ├── __init__.py
│   ├── test_import_perf.py        # 导入性能测试
│   ├── test_query_perf.py        # 查询性能测试
│   └── test_memory_perf.py       # 内存性能测试
├── data/                          # 测试数据目录
│   ├── fixtures/                  # 测试夹具数据
│   │   ├── sample.fit             # 示例FIT文件
│   │   ├── large_dataset.parquet # 大数据集
│   │   └── config_template.yaml  # 配置模板
│   ├── mock/                      # 模拟数据
│   │   ├── fit_mock_data.py       # FIT模拟数据生成
│   │   └── analytics_mock.py      # 分析数据模拟
│   └── validation/                # 验证数据
│       ├── expected_results.json  # 预期结果
│       └── benchmark_data.csv     # 基准数据
├── reports/                       # 测试报告目录
│   ├── unit/                      # 单元测试报告
│   ├── integration/               # 集成测试报告
│   ├── e2e/                       # E2E测试报告
│   ├── performance/               # 性能测试报告
│   └── coverage/                  # 覆盖率报告
├── scripts/                       # 测试脚本目录
│   ├── setup_test_env.py          # 测试环境设置
│   ├── run_all_tests.py           # 全量测试执行
│   ├── generate_test_data.py      # 测试数据生成
│   └── cleanup_test_data.py       # 测试数据清理
└── config/                        # 测试配置目录
    ├── pytest.ini                 # pytest配置
    ├── coverage.rc               # 覆盖率配置
    └── test_constants.py         # 测试常量定义

```

---

## 二、目录详细说明

### 2.1 单元测试目录 (`tests/unit/`)

**用途**: 测试单个函数、类的独立功能  
**文件命名规范**: `test_<模块名>.py`  
**类命名规范**: `Test<类名>`  
**方法命名规范**: `test_<功能描述>`

**示例结构**:
```python
# tests/unit/test_analytics.py
class TestAnalyticsEngine:
    """测试分析引擎"""
    
    def test_calculate_vdot_success(self):
        """测试成功计算VDOT"""
        # 测试代码
        
    def test_calculate_vdot_edge_cases(self):
        """测试边界条件VDOT计算"""
        # 测试代码
```

### 2.2 集成测试目录 (`tests/integration/`)

#### 2.2.1 模块间集成测试 (`module/`)
**用途**: 测试模块间的数据流和接口兼容性

**示例文件**:
- `test_import_flow.py`: 测试数据导入完整流程
- `test_analytics_flow.py`: 测试数据分析完整流程

#### 2.2.2 场景级集成测试 (`scene/`)
**用途**: 测试完整业务场景和用户操作流程

**示例文件**:
- `test_full_workflow.py`: 测试从导入到分析的完整流程
- `test_error_handling.py`: 测试异常场景的处理

### 2.3 端到端测试目录 (`tests/e2e/`)

**用途**: 模拟真实用户操作，验证系统整体功能  
**测试重点**: 用户体验、业务流程完整性

**示例文件**:
```python
# tests/e2e/test_user_journey.py
class TestUserJourney:
    """测试用户完整旅程"""
    
    def test_import_and_analyze_workflow(self):
        """测试导入和分析完整流程"""
        # 模拟用户操作步骤
```

### 2.4 性能测试目录 (`tests/performance/`)

**用途**: 验证系统性能指标和资源使用情况  
**测试重点**: 响应时间、内存占用、CPU使用率

**示例文件**:
```python
# tests/performance/test_import_perf.py
class TestImportPerformance:
    """测试导入性能"""
    
    def test_large_file_import_performance(self):
        """测试大文件导入性能"""
        # 性能测试代码
```

### 2.5 测试数据目录 (`tests/data/`)

#### 2.5.1 测试夹具数据 (`fixtures/`)
**用途**: 预定义的测试数据文件

**文件类型**:
- `.fit`: 标准FIT格式文件
- `.parquet`: Parquet数据文件
- `.yaml/.json`: 配置文件模板

#### 2.5.2 模拟数据 (`mock/`)
**用途**: 动态生成的模拟数据

**示例文件**:
```python
# tests/data/mock/fit_mock_data.py
def generate_mock_fit_data():
    """生成模拟FIT数据"""
    # 数据生成逻辑
```

#### 2.5.3 验证数据 (`validation/`)
**用途**: 预期结果和基准数据

**文件类型**:
- `.json`: 预期结果数据
- `.csv`: 基准性能数据

### 2.6 测试报告目录 (`tests/reports/`)

**用途**: 存储各类测试报告和覆盖率数据

**报告类型**:
- HTML格式的详细测试报告
- JSON格式的机器可读报告
- 覆盖率报告和统计图表

### 2.7 测试脚本目录 (`tests/scripts/`)

**用途**: 测试相关的辅助脚本

**脚本功能**:
- 测试环境设置和清理
- 测试数据生成和管理
- 测试执行和结果分析

### 2.8 测试配置目录 (`tests/config/`)

**用途**: 测试相关的配置文件

**配置文件**:
- `pytest.ini`: pytest运行配置
- `coverage.rc`: 覆盖率统计配置
- `test_constants.py`: 测试常量定义

---

## 三、文件命名规范

### 3.1 测试文件命名

| 测试类型 | 命名模式 | 示例 |
|---------|---------|------|
| 单元测试 | `test_<模块名>.py` | `test_analytics.py` |
| 集成测试 | `test_<流程名>_flow.py` | `test_import_flow.py` |
| 场景测试 | `test_<场景名>_scene.py` | `test_full_workflow.py` |
| E2E测试 | `test_<旅程名>_journey.py` | `test_user_journey.py` |
| 性能测试 | `test_<功能>_perf.py` | `test_import_perf.py` |

### 3.2 测试类命名

| 测试类型 | 命名模式 | 示例 |
|---------|---------|------|
| 单元测试 | `Test<类名>` | `TestAnalyticsEngine` |
| 集成测试 | `Test<模块>Integration` | `TestAnalyticsIntegration` |
| 场景测试 | `Test<场景名>Scenario` | `TestFullWorkflowScenario` |
| E2E测试 | `Test<旅程名>Journey` | `TestUserJourney` |

### 3.3 测试方法命名

| 测试类型 | 命名模式 | 示例 |
|---------|---------|------|
| 功能测试 | `test_<功能>_success` | `test_calculate_vdot_success` |
| 边界测试 | `test_<功能>_edge_cases` | `test_calculate_vdot_edge_cases` |
| 错误测试 | `test_<功能>_error` | `test_calculate_vdot_error` |
| 性能测试 | `test_<功能>_performance` | `test_import_performance` |

---

## 四、测试数据管理规范

### 4.1 测试数据分类

| 数据类型 | 存储位置 | 使用场景 | 生命周期 |
|---------|---------|---------|----------|
| 静态测试数据 | `tests/data/fixtures/` | 单元测试、集成测试 | 长期保存 |
| 动态模拟数据 | `tests/data/mock/` | 需要动态生成的测试 | 测试时生成 |
| 验证数据 | `tests/data/validation/` | 结果验证、基准测试 | 长期保存 |

### 4.2 测试数据安全

- **禁止使用真实用户数据**
- 所有测试数据必须经过脱敏处理
- 测试数据文件需要版本控制
- 定期清理过期的测试数据

### 4.3 测试数据生成规范

```python
# tests/data/mock/fit_mock_data.py

def generate_sample_fit_data():
    """
    生成示例FIT数据
    
    Returns:
        dict: FIT格式的模拟数据
    """
    return {
        "timestamp": "2024-01-01T10:00:00Z",
        "heart_rate": 150,
        "distance": 5000.0,
        "duration": 1800
    }
```

---

## 五、测试执行规范

### 5.1 测试执行命令

| 测试类型 | 执行命令 | 报告生成 |
|---------|---------|---------|
| 单元测试 | `pytest tests/unit/ -v` | `--cov-report=html` |
| 集成测试 | `pytest tests/integration/ -v` | `--html=reports/integration.html` |
| E2E测试 | `pytest tests/e2e/ -v` | `--html=reports/e2e.html` |
| 性能测试 | `pytest tests/performance/ -v` | `--benchmark-json=reports/performance.json` |
| 全量测试 | `pytest tests/ -v` | 综合报告 |

### 5.2 测试环境设置

```python
# tests/scripts/setup_test_env.py

def setup_test_environment():
    """设置测试环境"""
    # 1. 创建测试数据库
    # 2. 配置测试参数
    # 3. 准备测试数据
    # 4. 启动测试服务
```

### 5.3 测试数据清理

```python
# tests/scripts/cleanup_test_data.py

def cleanup_test_data():
    """清理测试数据"""
    # 1. 删除临时文件
    # 2. 清理测试数据库
    # 3. 重置配置
    # 4. 关闭测试服务
```

---

## 六、测试报告规范

### 6.1 报告格式要求

| 报告类型 | 格式 | 包含内容 | 存储位置 |
|---------|------|---------|----------|
| 单元测试报告 | HTML | 覆盖率、通过率、失败详情 | `tests/reports/unit/` |
| 集成测试报告 | HTML | 接口测试结果、数据流验证 | `tests/reports/integration/` |
| E2E测试报告 | HTML | 用户旅程测试结果、截图 | `tests/reports/e2e/` |
| 性能测试报告 | JSON+HTML | 性能指标、对比分析 | `tests/reports/performance/` |
| 覆盖率报告 | HTML | 代码覆盖率详情、未覆盖行 | `tests/reports/coverage/` |

### 6.2 报告命名规范

| 报告类型 | 命名模式 | 示例 |
|---------|---------|------|
| 单元测试 | `unit_report_<日期>.html` | `unit_report_20260302.html` |
| 集成测试 | `integration_report_<日期>.html` | `integration_report_20260302.html` |
| E2E测试 | `e2e_report_<日期>.html` | `e2e_report_20260302.html` |
| 性能测试 | `performance_report_<日期>.json` | `performance_report_20260302.json` |
| 覆盖率 | `coverage_report_<日期>.html` | `coverage_report_20260302.html` |

---

## 七、最佳实践指南

### 7.1 测试代码编写规范

1. **单一职责原则**: 每个测试用例只测试一个功能点
2. **可读性优先**: 测试代码要清晰易懂
3. **独立性**: 测试用例之间相互独立
4. **可重复性**: 测试结果应该可重复

### 7.2 测试数据管理最佳实践

1. **最小化数据**: 使用最小的必要数据完成测试
2. **数据隔离**: 不同测试用例使用独立的数据
3. **数据版本控制**: 测试数据文件需要版本管理
4. **定期清理**: 定期清理无用的测试数据

### 7.3 测试执行最佳实践

1. **自动化执行**: 测试执行应该完全自动化
2. **快速反馈**: 测试结果应该快速反馈
3. **持续集成**: 集成到CI/CD流程中
4. **结果分析**: 定期分析测试结果趋势

---

## 八、附录

### 8.1 目录结构检查清单

- [ ] 所有测试目录已创建
- [ ] 测试文件命名符合规范
- [ ] 测试数据分类存储
- [ ] 测试报告目录就绪
- [ ] 测试脚本功能完整
- [ ] 配置文件正确设置

### 8.2 参考文档

- [项目测试策略与规范](file:///d:/yecll/Documents/LocalCode/RunFlowAgent/docs/test/项目测试策略与规范.md)
- pytest官方文档
- Python单元测试最佳实践

### 8.3 修订历史

| 版本 | 修订日期 | 修订内容 | 修订人 |
|------|---------|---------|--------|
| v1.0 | 2026-03-02 | 初始版本 | 测试工程师 |

---

**文档审批**:  
测试经理: ___________ 日期: _________  
技术负责人: ___________ 日期: _________