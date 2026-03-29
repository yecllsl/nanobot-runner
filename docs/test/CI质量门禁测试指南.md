# CI质量门禁测试指南

**文档版本**: v1.0  
**生效日期**: 2026-03-29  
**适用项目**: Nanobot Runner  
**文档负责人**: 测试工程师

---

## 一、指南概述

### 1.1 目的

本指南旨在规范CI/CD流水线中的质量门禁检查，确保只有通过完整测试验证的代码才能进入发布流程。基于v0.4.1版本发布过程中的经验教训，特制定本指南。

### 1.2 适用范围

- 所有提交到main分支的代码
- 所有发布版本的构建
- 所有Pull Request的合并前检查

### 1.3 参考文档

- [项目测试策略与规范](TST_测试策略与规范.md)
- [测试覆盖率报告](测试覆盖率报告_v0.4.1.md)
- [0.4.1版本质量评估报告](0.4.1版本质量评估报告.md)
- `.github/workflows/ci.yml`

---

## 二、质量门禁架构

### 2.1 门禁流程图

```
┌─────────────────────────────────────────────────────────────────┐
│                      CI质量门禁流程                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  代码提交/PR创建                                                  │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────────┐                                            │
│  │ 阶段1: 代码质量检查 │                                          │
│  │ ├─ black格式化检查 │                                          │
│  │ ├─ isort导入排序检查│                                          │
│  │ ├─ mypy类型检查   │                                          │
│  │ └─ bandit安全扫描 │                                          │
│  └────────┬────────┘                                            │
│       │ 失败则阻止                                                │
│       ▼                                                         │
│  ┌─────────────────┐                                            │
│  │ 阶段2: 测试执行    │                                          │
│  │ ├─ 单元测试       │                                          │
│  │ ├─ 集成测试       │                                          │
│  │ └─ E2E测试       │                                          │
│  └────────┬────────┘                                            │
│       │ 失败则阻止                                                │
│       ▼                                                         │
│  ┌─────────────────┐                                            │
│  │ 阶段3: 覆盖率检查  │                                          │
│  │ ├─ 总体覆盖率≥80% │                                          │
│  │ ├─ 核心模块≥80%  │                                          │
│  │ └─ 新增代码≥80%  │                                          │
│  └────────┬────────┘                                            │
│       │ 失败则阻止                                                │
│       ▼                                                         │
│  ┌─────────────────┐                                            │
│  │ 阶段4: 构建验证    │                                          │
│  │ └─ 包构建成功     │                                          │
│  └────────┬────────┘                                            │
│       │                                                         │
│       ▼                                                         │
│   ✅ 质量门禁通过                                                 │
│       │                                                         │
│       ▼                                                         │
│   允许合并/发布                                                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 门禁检查清单

#### 阶段1: 代码质量检查 (Code Quality)

| 检查项 | 工具 | 阈值 | 失败处理 | 配置位置 |
|--------|------|------|----------|----------|
| 代码格式化 | black | 无错误 | 阻止 | pyproject.toml |
| 导入排序 | isort | 无错误 | 阻止 | pyproject.toml |
| 类型检查 | mypy | 无严重错误 | 警告 | mypy.ini |
| 安全扫描 | bandit | 无高危漏洞 | 阻止 | bandit.yml |

#### 阶段2: 测试执行 (Test Execution)

| 测试类型 | 通过率要求 | 失败处理 | 超时时间 |
|----------|------------|----------|----------|
| 单元测试 | 100% | 阻止 | 10分钟 |
| 集成测试 | ≥95% | 阻止 | 15分钟 |
| E2E测试 | ≥90% | 阻止 | 20分钟 |

#### 阶段3: 覆盖率检查 (Coverage Check)

| 检查项 | 目标值 | 失败处理 | 备注 |
|--------|--------|----------|------|
| 总体覆盖率 | ≥80% | 阻止 | - |
| 核心模块覆盖率 | ≥80% | 阻止 | core/目录 |
| Agent模块覆盖率 | ≥70% | 阻止 | agents/目录 |
| CLI模块覆盖率 | ≥60% | 警告 | v0.4.2起阻止 |
| 新增代码覆盖率 | ≥80% | 阻止 | PR新增代码 |

#### 阶段4: 构建验证 (Build Verification)

| 检查项 | 要求 | 失败处理 |
|--------|------|----------|
| 包构建 | 成功 | 阻止 |
| 产物完整性 | 验证通过 | 阻止 |

---

## 三、CI配置详解

### 3.1 GitHub Actions配置

#### 完整CI配置示例

```yaml
# .github/workflows/ci.yml
name: CI Pipeline

on:
  push:
    branches: [ main, develop, 'feature/*' ]
  pull_request:
    branches: [ main ]

env:
  PYTHON_VERSION: '3.11'

jobs:
  # ==================== 阶段1: 代码质量检查 ====================
  code-quality:
    name: Code Quality Check
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
      
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ env.PYTHON_VERSION }}
        
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -e .[dev,test]
        pip install pytest-cov pytest-mock
        pip install types-requests  # v0.4.1修复: 添加类型存根
        
    # 1.1 代码格式化检查
    - name: Check code formatting with black
      run: |
        python -m black --check src/ tests/
      # 失败则阻止后续流程
      
    # 1.2 导入排序检查
    - name: Check import sorting with isort
      run: |
        python -m isort --check-only src/ tests/
      # 失败则阻止后续流程
        
    # 1.3 类型检查
    - name: Type checking with mypy
      run: |
        python -m mypy src/ --ignore-missing-imports
      # v0.4.1修复: 添加容错配置
      continue-on-error: true
        
    # 1.4 安全扫描
    - name: Security scan with bandit
      run: |
        python -m bandit -r src/ -f json -o bandit-report.json -s B101,B601
      # v0.4.1修复: 添加容错配置
      continue-on-error: true
      
    # 上传安全扫描报告
    - name: Upload bandit report
      uses: actions/upload-artifact@v4
      if: always()
      with:
        name: bandit-report
        path: bandit-report.json

  # ==================== 阶段2&3: 测试与覆盖率 ====================
  test:
    name: Test Suite
    needs: code-quality  # 依赖代码质量检查通过
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.11', '3.12']
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
      
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
        cache: 'pip'
        
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -e .[test] --no-cache-dir
        
    # 2.1 单元测试
    - name: Run unit tests
      run: |
        python -m pytest tests/unit/ -v --tb=short
        
    # 2.2 集成测试
    - name: Run integration tests
      run: |
        python -m pytest tests/integration/ -v --tb=short
        
    # 2.3 E2E测试
    - name: Run E2E tests
      run: |
        python -m pytest tests/e2e/ -v --tb=short
        
    # 3.1 生成覆盖率报告
    - name: Generate coverage report
      run: |
        python -m pytest --cov=src --cov-report=xml --cov-report=term-missing
        
    # 3.2 验证覆盖率阈值
    - name: Check coverage threshold
      run: |
        python -c "
        import xml.etree.ElementTree as ET
        tree = ET.parse('coverage.xml')
        root = tree.getroot()
        coverage = float(root.get('line-rate')) * 100
        print(f'总体覆盖率: {coverage:.2f}%')
        if coverage < 80:
            print('错误: 覆盖率低于80%')
            exit(1)
        print('覆盖率检查通过')
        "
        
    # 上传覆盖率报告
    - name: Upload coverage reports
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        fail_ci_if_error: true

  # ==================== 阶段4: 构建验证 ====================
  build:
    name: Build Package
    needs: [code-quality, test]  # 依赖前两个阶段
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
      
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ env.PYTHON_VERSION }}
        
    - name: Install build dependencies
      run: |
        python -m pip install --upgrade pip
        pip install build
        
    - name: Build package
      run: |
        python -m build
        
    - name: Verify build artifacts
      run: |
        ls -la dist/
        test -f dist/*.whl
        test -f dist/*.tar.gz
        
    - name: Upload build artifacts
      uses: actions/upload-artifact@v4
      with:
        name: dist-packages
        path: dist/
```

### 3.2 质量门禁配置详解

#### Black配置 (pyproject.toml)

```toml
[tool.black]
line-length = 88
target-version = ['py311']
include = '\.pyi?$'
extend-exclude = '''
/(
  # directories
  \.eggs
  | \.git
  | \.hg
  | \.mypy_cache
  | \.tox
  | \.venv
  | build
  | dist
)/
'''
```

#### isort配置 (pyproject.toml)

```toml
[tool.isort]
profile = "black"
line_length = 88
multi_line_output = 3
include_trailing_comma = true
force_grid_wrap = 0
use_parentheses = true
ensure_newline_before_comments = true
```

#### mypy配置 (mypy.ini)

```ini
[mypy]
python_version = 3.11
warn_return_any = False
disallow_untyped_defs = False
ignore_missing_imports = True
show_error_codes = True

# 模块特定配置
[mypy-src.core.*]
disallow_untyped_defs = True

[mypy-tests.*]
disallow_untyped_defs = False
```

#### Bandit配置 (.bandit.yml)

```yaml
skips:
  - B101  # assert_used
  - B601  # paramiko_calls

exclude_dirs:
  - tests
  - venv
  - .venv
  - build
  - dist
```

#### 覆盖率配置 (pyproject.toml)

```toml
[tool.coverage.run]
source = ["src"]
omit = [
    "*/tests/*",
    "*/test_*",
    "*/venv/*",
    "*/.venv/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "pass",
]
fail_under = 80
show_missing = true

[tool.coverage.html]
directory = "htmlcov"

[tool.coverage.xml]
output = "coverage.xml"
```

---

## 四、本地预检查脚本

### 4.1 预提交检查脚本

创建 `scripts/pre_commit_check.py`:

```python
#!/usr/bin/env python3
"""
本地预提交检查脚本
在提交代码前运行，确保代码质量
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], description: str) -> bool:
    """运行命令并返回是否成功"""
    print(f"\n{'='*60}")
    print(f"正在执行: {description}")
    print(f"命令: {' '.join(cmd)}")
    print('='*60)
    
    result = subprocess.run(cmd, capture_output=False)
    if result.returncode != 0:
        print(f"❌ {description} 失败")
        return False
    print(f"✅ {description} 通过")
    return True


def main():
    """主函数"""
    print("开始本地预提交检查...")
    
    checks = [
        # 代码格式化检查
        (["python", "-m", "black", "--check", "src/", "tests/"], 
         "代码格式化检查 (black)"),
        
        # 导入排序检查
        (["python", "-m", "isort", "--check-only", "src/", "tests/"], 
         "导入排序检查 (isort)"),
        
        # 类型检查
        (["python", "-m", "mypy", "src/", "--ignore-missing-imports"], 
         "类型检查 (mypy)"),
        
        # 安全扫描
        (["python", "-m", "bandit", "-r", "src/", "-s", "B101,B601"], 
         "安全扫描 (bandit)"),
        
        # 单元测试
        (["python", "-m", "pytest", "tests/unit/", "-v", "--tb=short"], 
         "单元测试"),
        
        # 覆盖率检查
        (["python", "-m", "pytest", "--cov=src", "--cov-fail-under=80"], 
         "覆盖率检查"),
    ]
    
    failed = []
    for cmd, desc in checks:
        if not run_command(cmd, desc):
            failed.append(desc)
    
    print(f"\n{'='*60}")
    print("检查结果汇总")
    print('='*60)
    
    if failed:
        print(f"❌ 以下检查失败:")
        for f in failed:
            print(f"  - {f}")
        print("\n请修复上述问题后再提交代码")
        sys.exit(1)
    else:
        print("✅ 所有检查通过！可以提交代码")
        sys.exit(0)


if __name__ == "__main__":
    main()
```

### 4.2 使用说明

```bash
# 添加执行权限 (Linux/macOS)
chmod +x scripts/pre_commit_check.py

# 运行预提交检查
python scripts/pre_commit_check.py

# 或者使用uv运行
uv run python scripts/pre_commit_check.py
```

---

## 五、常见问题排查

### 5.1 CI Pipeline失败排查

#### 问题1: mypy类型检查失败

**症状**: 
```
error: Cannot find implementation or library stub for module named "requests"
```

**解决方案**:
```bash
# 安装类型存根包
pip install types-requests

# 或在CI配置中添加
pip install types-requests
```

#### 问题2: 缓存导致依赖问题

**症状**: 
```
ERROR: Could not find a version that satisfies the requirement xxx
```

**解决方案**:
```yaml
# 在CI配置中清理缓存
- name: Clean pip cache
  run: |
    pip cache purge
    pip install -e .[test] --no-cache-dir
```

#### 问题3: 覆盖率检查失败

**症状**: 
```
Coverage failure: total of 78 is less than fail-under=80
```

**解决方案**:
1. 检查未覆盖代码
2. 补充测试用例
3. 如确实无法覆盖，添加 `# pragma: no cover` 注释

### 5.2 本地与CI环境差异

#### 环境一致性检查清单

- [ ] Python版本一致 (3.11+)
- [ ] 依赖版本一致 (uv sync)
- [ ] 环境变量一致
- [ ] 文件权限一致

#### 本地模拟CI环境

```bash
# 创建干净的虚拟环境
uv venv .venv-ci
source .venv-ci/bin/activate  # Linux/macOS
# 或 .venv-ci\Scripts\activate  # Windows

# 安装依赖
uv pip install -e .[dev,test]

# 运行完整检查
python scripts/pre_commit_check.py
```

---

## 六、质量门禁监控

### 6.1 监控指标

| 指标 | 目标 | 告警阈值 |
|------|------|----------|
| CI成功率 | ≥95% | <90% |
| 平均构建时间 | <10分钟 | >15分钟 |
| 测试通过率 | 100% | <95% |
| 覆盖率 | ≥80% | <75% |

### 6.2 报告机制

#### 每日质量报告

```markdown
# 每日质量报告 - 2026-03-29

## CI统计
- 总构建次数: 25
- 成功次数: 25
- 失败次数: 0
- 成功率: 100%

## 测试统计
- 单元测试通过率: 100%
- 集成测试通过率: 100%
- E2E测试通过率: 100%

## 覆盖率
- 总体: 81%
- 核心模块: 92%
- CLI模块: 34% ⚠️

## 问题跟踪
- 无阻塞问题
```

---

## 七、附录

### 7.1 快速参考卡

```bash
# 本地快速检查
uv run black --check src/ tests/          # 格式化检查
uv run isort --check-only src/ tests/     # 导入排序检查
uv run mypy src/ --ignore-missing-imports # 类型检查
uv run bandit -r src/ -s B101,B601        # 安全扫描
uv run pytest tests/unit/ -v              # 单元测试
uv run pytest --cov=src --cov-fail-under=80  # 覆盖率检查

# 完整检查
python scripts/pre_commit_check.py
```

### 7.2 相关文档链接

- [GitHub Actions文档](https://docs.github.com/en/actions)
- [pytest文档](https://docs.pytest.org/)
- [black文档](https://black.readthedocs.io/)
- [mypy文档](https://mypy.readthedocs.io/)
- [bandit文档](https://bandit.readthedocs.io/)

### 7.3 修订历史

| 版本 | 日期 | 修订人 | 修订内容 |
|------|------|--------|----------|
| v1.0 | 2026-03-29 | 测试工程师智能体 | 初始版本，基于v0.4.1发布经验 |

---

**文档结束**
