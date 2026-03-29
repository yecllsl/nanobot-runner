# 代码质量门禁指南

## 概述

本文档定义了 Nanobot Runner 项目的代码质量门禁标准，基于 v0.4.1 版本发布过程中的经验教训，确保代码质量和发布流程的稳定性。

## 质量门禁架构

```
┌─────────────────────────────────────────────────────────────────┐
│                      代码质量门禁                                 │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────┐ │
│  │   格式化     │  │   类型检查   │  │   安全扫描   │  │  测试   │ │
│  │   black     │  │   mypy      │  │   bandit    │  │  pytest │ │
│  │   isort     │  │             │  │             │  │         │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └────┬────┘ │
│         │                │                │              │      │
│         ▼                ▼                ▼              ▼      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    合并阻断策略                            │  │
│  │  • 格式化失败 → 阻断                                       │  │
│  │  • 安全高危 → 阻断                                         │  │
│  │  • 测试失败 → 阻断                                         │  │
│  │  • 类型警告 → 非阻断（逐步收紧）                            │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## 门禁检查项

### 1. 代码格式化检查

| 属性 | 说明 |
|------|------|
| **工具** | black |
| **版本** | >=23.0.0,<24.0.0 |
| **配置** | `line-length = 88` |
| **门禁要求** | 零警告 |
| **失败处理** | 阻断合并 |

**本地检查命令**:
```bash
uv run black --check src/ tests/
```

**自动修复命令**:
```bash
uv run black src/ tests/
```

**CI配置**:
```yaml
- name: Check code formatting with black
  run: |
    python -m black --check src/ tests/
```

### 2. 导入排序检查

| 属性 | 说明 |
|------|------|
| **工具** | isort |
| **版本** | >=5.12.0,<6.0.0 |
| **配置** | `profile = "black"` |
| **门禁要求** | 零警告 |
| **失败处理** | 阻断合并 |

**本地检查命令**:
```bash
uv run isort --check-only src/ tests/
```

**自动修复命令**:
```bash
uv run isort src/ tests/
```

**CI配置**:
```yaml
- name: Check import sorting with isort
  run: |
    python -m isort --check-only src/ tests/
```

### 3. 类型检查

| 属性 | 说明 |
|------|------|
| **工具** | mypy |
| **版本** | >=1.0.0,<2.0.0 |
| **配置** | 宽松模式（逐步收紧） |
| **门禁要求** | 警告可接受 |
| **失败处理** | 非阻断（v0.4.1） |

**本地检查命令**:
```bash
uv run mypy src/ --ignore-missing-imports
```

**CI配置**:
```yaml
- name: Type checking with mypy
  run: |
    python -m mypy src/ --ignore-missing-imports --install-types --non-interactive || echo "mypy检查失败，但继续执行"
  continue-on-error: true
```

**类型检查升级计划**:

| 版本 | 目标 | mypy配置 |
|------|------|----------|
| v0.4.1 | 建立基线 | 宽松模式 |
| v0.4.2 | 核心模块80% | 收紧配置 |
| v0.5.0 | 全模块80% | 严格模式 |

### 4. 安全扫描

| 属性 | 说明 |
|------|------|
| **工具** | bandit |
| **版本** | >=1.7.0,<2.0.0 |
| **配置** | 跳过 B101, B601 |
| **门禁要求** | 高危漏洞=0 |
| **失败处理** | 阻断合并 |

**本地检查命令**:
```bash
uv run bandit -r src/ -s B101,B601
```

**CI配置**:
```yaml
- name: Security scan with bandit
  run: |
    python -m bandit -r src/ -f json -o bandit-report.json -s B101,B601 || echo "bandit检查失败，但继续执行"
  continue-on-error: true
```

**跳过的检查项说明**:
- `B101`: assert_used - 允许使用assert（测试代码需要）
- `B601`: paramiko_calls - 不使用paramiko库

### 5. 测试质量门禁

| 检查项 | 要求 | 工具配置 |
|--------|------|----------|
| 单元测试通过率 | 100% | pytest tests/unit/ |
| 集成测试通过率 | 100% | pytest tests/integration/ |
| 代码覆盖率 | core≥80%, agents≥70%, cli≥60% | pytest --cov=src |
| 测试执行时间 | 单测试<30秒 | pytest-timeout |

**本地测试命令**:
```bash
# 单元测试
uv run pytest tests/unit/ -v --cov=src --cov-report=term-missing

# 集成测试
uv run pytest tests/integration/ -v

# 全量测试（含覆盖率）
uv run pytest --cov=src --cov-report=xml --cov-report=term-missing
```

**CI配置**:
```yaml
- name: Run unit tests
  run: |
    python -m pytest tests/unit/ -v --cov=src --cov-report=term-missing --tb=short

- name: Run integration tests
  run: |
    python -m pytest tests/integration/ -v --tb=short
```

## 本地预提交检查脚本

### Windows (PowerShell)

```powershell
# pre-commit-check.ps1
$ErrorActionPreference = "Stop"

Write-Host "=== 开始代码质量预检查 ===" -ForegroundColor Cyan

# 1. 代码格式化检查
Write-Host "`n[1/5] 检查代码格式化 (black)..." -ForegroundColor Yellow
try {
    uv run black --check src/ tests/
    Write-Host "✓ 代码格式化检查通过" -ForegroundColor Green
} catch {
    Write-Host "✗ 代码格式化检查失败，运行 'uv run black src/ tests/' 修复" -ForegroundColor Red
    exit 1
}

# 2. 导入排序检查
Write-Host "`n[2/5] 检查导入排序 (isort)..." -ForegroundColor Yellow
try {
    uv run isort --check-only src/ tests/
    Write-Host "✓ 导入排序检查通过" -ForegroundColor Green
} catch {
    Write-Host "✗ 导入排序检查失败，运行 'uv run isort src/ tests/' 修复" -ForegroundColor Red
    exit 1
}

# 3. 类型检查
Write-Host "`n[3/5] 类型检查 (mypy)..." -ForegroundColor Yellow
uv run mypy src/ --ignore-missing-imports
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ 类型检查通过" -ForegroundColor Green
} else {
    Write-Host "⚠ 类型检查有警告（非阻断）" -ForegroundColor Yellow
}

# 4. 安全扫描
Write-Host "`n[4/5] 安全扫描 (bandit)..." -ForegroundColor Yellow
uv run bandit -r src/ -s B101,B601
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ 安全扫描通过" -ForegroundColor Green
} else {
    Write-Host "✗ 安全扫描发现高危漏洞" -ForegroundColor Red
    exit 1
}

# 5. 单元测试
Write-Host "`n[5/5] 运行单元测试..." -ForegroundColor Yellow
uv run pytest tests/unit/ --cov=src --cov-fail-under=80
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ 单元测试通过" -ForegroundColor Green
} else {
    Write-Host "✗ 单元测试失败" -ForegroundColor Red
    exit 1
}

Write-Host "`n=== 所有检查通过 ===" -ForegroundColor Green
```

### Linux/Mac (Bash)

```bash
#!/bin/bash
# pre-commit-check.sh

set -e

echo "=== 开始代码质量预检查 ==="

# 1. 代码格式化检查
echo -e "\n[1/5] 检查代码格式化 (black)..."
if uv run black --check src/ tests/; then
    echo "✓ 代码格式化检查通过"
else
    echo "✗ 代码格式化检查失败，运行 'uv run black src/ tests/' 修复"
    exit 1
fi

# 2. 导入排序检查
echo -e "\n[2/5] 检查导入排序 (isort)..."
if uv run isort --check-only src/ tests/; then
    echo "✓ 导入排序检查通过"
else
    echo "✗ 导入排序检查失败，运行 'uv run isort src/ tests/' 修复"
    exit 1
fi

# 3. 类型检查
echo -e "\n[3/5] 类型检查 (mypy)..."
if uv run mypy src/ --ignore-missing-imports; then
    echo "✓ 类型检查通过"
else
    echo "⚠ 类型检查有警告（非阻断）"
fi

# 4. 安全扫描
echo -e "\n[4/5] 安全扫描 (bandit)..."
if uv run bandit -r src/ -s B101,B601; then
    echo "✓ 安全扫描通过"
else
    echo "✗ 安全扫描发现高危漏洞"
    exit 1
fi

# 5. 单元测试
echo -e "\n[5/5] 运行单元测试..."
if uv run pytest tests/unit/ --cov=src --cov-fail-under=80; then
    echo "✓ 单元测试通过"
else
    echo "✗ 单元测试失败"
    exit 1
fi

echo -e "\n=== 所有检查通过 ==="
```

## CI环境差异处理

### v0.4.1发现的问题

1. **mypy类型检查失败**
   - 原因：CI环境缺少types-requests类型存根
   - 解决：显式安装 `pip install types-requests`

2. **缓存污染**
   - 原因：pip缓存导致旧版本依赖
   - 解决：使用 `--no-cache-dir` 参数

3. **环境差异**
   - 原因：本地与CI Python版本差异
   - 解决：统一使用Python 3.11

### 推荐的CI配置

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
  code-quality:
    name: Code Quality Check
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ env.PYTHON_VERSION }}
        
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -e .[dev,test] --no-cache-dir
        pip install types-requests  # 显式安装类型存根
        
    - name: Check code formatting
      run: python -m black --check src/ tests/
      
    - name: Check import sorting
      run: python -m isort --check-only src/ tests/
      
    - name: Type checking
      run: |
        python -m mypy src/ --ignore-missing-imports || echo "类型检查有警告"
      continue-on-error: true
      
    - name: Security scan
      run: python -m bandit -r src/ -s B101,B601
```

## 质量门禁检查清单

### 提交前检查

- [ ] 本地运行black检查通过
- [ ] 本地运行isort检查通过
- [ ] 本地运行mypy检查（无错误）
- [ ] 本地运行bandit检查通过
- [ ] 单元测试通过率100%
- [ ] 代码覆盖率达标

### 代码审查检查

- [ ] 代码符合类型注解规范
- [ ] 无硬编码敏感信息
- [ ] 错误处理完善
- [ ] 文档字符串完整

### 发布前检查

- [ ] CI Pipeline全部通过
- [ ] 测试覆盖率报告已生成
- [ ] 安全扫描无高危漏洞
- [ ] 版本号已更新

## 常见问题

### Q1: 为什么CI通过但本地失败？

可能原因：
1. 缓存问题 → 运行 `uv cache clean; uv sync --reinstall`
2. 依赖版本差异 → 检查 `uv pip list`
3. Python版本差异 → 确保使用Python 3.11

### Q2: 如何临时跳过某个检查？

**不推荐**，但紧急情况下可以：

```bash
# 跳过特定检查（仅本地）
uv run pytest -k "not slow"  # 跳过慢测试

# CI中（需要修改workflow，谨慎使用）
continue-on-error: true
```

### Q3: 类型检查警告太多怎么办？

1. 优先处理核心模块（core/、agents/）
2. 使用 `# type: ignore` 标记已知问题（添加注释说明原因）
3. 逐步重构旧代码，添加类型注解

---

*文档版本: 1.0*  
*适用版本: v0.4.1+*  
*最后更新: 2026-03-29*
