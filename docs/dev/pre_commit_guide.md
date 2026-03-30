# Pre-commit配置指南

## 概述

本文档说明如何在 Nanobot Runner 项目中配置和使用 pre-commit 钩子，在代码提交前自动执行代码质量检查，避免将不符合规范的代码推送到仓库。

## 什么是Pre-commit

Pre-commit 是一个在代码提交前自动运行检查的工具框架，可以：
- 自动格式化代码
- 运行代码质量检查
- 阻止不符合规范的代码提交
- 减少CI失败率

## 安装配置

### 1. 安装pre-commit

```bash
# 使用uv安装（推荐）
uv pip install pre-commit

# 或使用pip
pip install pre-commit
```

### 2. 创建配置文件

在项目根目录创建 `.pre-commit-config.yaml`：

```yaml
# .pre-commit-config.yaml
# Nanobot Runner Pre-commit配置

# 默认属性
default_stages: [pre-commit]
default_language_version:
  python: python3.11

# 钩子仓库列表
repos:
  # 1. Pre-commit基础钩子
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      # 检查YAML语法
      - id: check-yaml
        name: Check YAML syntax
      
      # 检查JSON语法
      - id: check-json
        name: Check JSON syntax
        exclude: ".vscode/"
      
      # 检查TOML语法
      - id: check-toml
        name: Check TOML syntax
      
      # 检查合并冲突标记
      - id: check-merge-conflict
        name: Check merge conflicts
      
      # 检查调试语句
      - id: debug-statements
        name: Check debug statements
        language_version: python3.11
      
      # 去除行尾空格
      - id: trailing-whitespace
        name: Trim trailing whitespace
        args: [--markdown-linebreak-ext=md]
      
      # 确保文件末尾有空行
      - id: end-of-file-fixer
        name: Fix end of files
      
      # 检查大文件
      - id: check-added-large-files
        name: Check large files
        args: ['--maxkb=1000']

  # 2. Black代码格式化
  - repo: https://github.com/psf/black
    rev: 23.12.1
    hooks:
      - id: black
        name: Black code formatter
        language_version: python3.11
        args: ['--line-length=88']
        files: ^(src|tests)/.*\.py$

  # 3. isort导入排序
  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks:
      - id: isort
        name: isort import sorter
        args: ['--profile=black', '--line-length=88']
        files: ^(src|tests)/.*\.py$

  # 4. mypy类型检查（可选，可能较慢）
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        name: mypy type checker
        additional_dependencies:
          - types-requests
          - types-setuptools
        args: ['--ignore-missing-imports']
        files: ^src/.*\.py$
        # 类型检查可能较慢，设为可选
        stages: [manual]

  # 5. Bandit安全扫描
  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.7
    hooks:
      - id: bandit
        name: Bandit security scanner
        args: ['-r', 'src/', '-s', 'B101,B601']
        files: ^src/.*\.py$
        # 安全扫描可能较慢，设为可选
        stages: [manual]

  # 6. 提交信息检查
  - repo: https://github.com/commitizen-tools/commitizen
    rev: v3.13.0
    hooks:
      - id: commitizen
        name: Commit message check
        stages: [commit-msg]
```

### 3. 安装Git钩子

```bash
# 安装pre-commit钩子到.git/hooks/
pre-commit install

# 安装commit-msg钩子（提交信息检查）
pre-commit install --hook-type commit-msg
```

### 4. 测试配置

```bash
# 对所有文件运行检查
pre-commit run --all-files

# 对特定文件运行检查
pre-commit run --files src/core/storage.py

# 运行特定钩子
pre-commit run black --all-files
```

## 使用指南

### 正常提交流程

```bash
# 1. 修改代码
git add src/core/storage.py

# 2. 提交（pre-commit自动运行）
git commit -m "feat(storage): 添加数据压缩功能"

# 3. 如果钩子修复了代码，需要重新add和commit
git add src/core/storage.py
git commit -m "feat(storage): 添加数据压缩功能"
```

### 跳过Pre-commit（不推荐）

```bash
# 紧急情况下跳过所有钩子
git commit -m "fix: 紧急修复" --no-verify

# 跳过特定钩子
SKIP=black git commit -m "feat: 新功能"
```

### 手动运行检查

```bash
# 检查所有文件
pre-commit run --all-files

# 检查最近修改的文件
pre-commit run

# 检查特定钩子
pre-commit run black --all-files
pre-commit run isort --all-files
```

## 与CI的集成

### 为什么需要两者

| 场景 | Pre-commit | CI |
|------|------------|-----|
| 运行时机 | 本地提交前 | Push/PR时 |
| 目的 | 快速反馈 | 最终把关 |
| 强制性 | 可跳过 | 不可跳过 |
| 覆盖范围 | 修改的文件 | 全量检查 |

### 推荐的CI配置

```yaml
# .github/workflows/ci.yml
jobs:
  pre-commit:
    name: Pre-commit checks
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Run pre-commit
        uses: pre-commit/action@v3.0.0
```

## 配置优化

### 性能优化

```yaml
# .pre-commit-config.yaml

# 使用本地仓库（更快）
repos:
  - repo: local
    hooks:
      - id: black-local
        name: black (local)
        entry: uv run black
        language: system
        types: [python]
        files: ^(src|tests)/.*\.py$
      
      - id: isort-local
        name: isort (local)
        entry: uv run isort
        language: system
        types: [python]
        files: ^(src|tests)/.*\.py$

# 或配置缓存
default_language_version:
  python: python3.11

# 设置超时时间（秒）
default_timeout: 120
```

### 分阶段配置

```yaml
# .pre-commit-config.yaml

# 快速检查（每次提交）
repos:
  - repo: https://github.com/psf/black
    rev: 23.12.1
    hooks:
      - id: black
        stages: [pre-commit]  # 默认阶段

# 慢速检查（手动运行）
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        stages: [manual]  # 手动触发

# 提交信息检查
  - repo: https://github.com/commitizen-tools/commitizen
    rev: v3.13.0
    hooks:
      - id: commitizen
        stages: [commit-msg]
```

运行手动阶段的钩子：

```bash
pre-commit run --hook-stage manual mypy
```

## 常见问题

### Q1: Pre-commit安装失败

```bash
# 问题：权限不足
# 解决：使用用户安装
pip install --user pre-commit

# 或添加到PATH
export PATH="$HOME/.local/bin:$PATH"
```

### Q2: 钩子运行太慢

```bash
# 方案1：跳过慢速钩子
SKIP=mypy,bandit git commit -m "feat: 新功能"

# 方案2：使用本地钩子（见配置优化）

# 方案3：将慢速钩子设为manual阶段
```

### Q3: Black和isort冲突

```yaml
# 确保isort配置与black兼容
- repo: https://github.com/pycqa/isort
  rev: 5.13.2
  hooks:
    - id: isort
      args: ['--profile=black', '--line-length=88']
```

### Q4: mypy找不到依赖

```yaml
# 在additional_dependencies中添加
- repo: https://github.com/pre-commit/mirrors-mypy
  rev: v1.8.0
  hooks:
    - id: mypy
      additional_dependencies:
        - types-requests
        - types-setuptools
        - polars
```

### Q5: Windows下脚本无法执行

```bash
# 确保Git Bash或PowerShell可以执行脚本
# 在Git Bash中：
pre-commit install

# 或在PowerShell中（管理员）：
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
pre-commit install
```

## 提交信息规范

### Commitizen配置

```yaml
# .pre-commit-config.yaml
- repo: https://github.com/commitizen-tools/commitizen
  rev: v3.13.0
  hooks:
    - id: commitizen
      stages: [commit-msg]
```

### 提交信息格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Type类型**：
- `feat`: 新功能
- `fix`: 修复
- `docs`: 文档
- `style`: 格式（不影响代码运行）
- `refactor`: 重构
- `test`: 测试
- `chore`: 构建/工具

**示例**：
```
feat(storage): 添加Parquet数据压缩功能

- 支持snappy、zstd压缩算法
- 自动检测最佳压缩方式
- 添加压缩率统计

Closes #123
```

## 检查清单

- [ ] Pre-commit已安装
- [ ] `.pre-commit-config.yaml`已创建
- [ ] Git钩子已安装 (`pre-commit install`)
- [ ] 本地测试通过 (`pre-commit run --all-files`)
- [ ] 提交信息规范已配置（可选）

---

*文档版本: 1.0*  
*适用版本: v0.4.1+*  
*最后更新: 2026-03-29*
