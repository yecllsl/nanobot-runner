# FIX-CI 报告 v0.33.0

> **报告日期**: 2026-07-24
> **关联版本**: v0.33.0
> **修复类型**: 配置型错误（workflow 文件修复）

---

## 1. 问题描述

### 1.1 现象

CI Pipeline 中 `Test Suite (3.12)` 和 `Test Suite (3.11)` 在 `Install dependencies` 步骤失败：

```
× No solution found when resolving dependencies for split (markers:
│ python_full_version >= '3.11' and python_full_version < '3.13' and
│ platform_machine == 'x86_64' and sys_platform == 'darwin'):
╰─▶ Because fastapi was not found in the package registry
```

### 1.2 根因分析

`pyproject.toml` 中配置了 Tsinghua 镜像作为默认索引：

```toml
[tool.uv.index]
name = 'tsinghua'
url = 'https://pypi.tuna.tsinghua.edu.cn/simple'
default = true
```

CI workflow 虽然指定了 `--index-url https://pypi.org/simple`，但 uv 在跨平台依赖解析时仍会回退到默认索引（Tsinghua），而该镜像在 GitHub Actions runner 上返回 **403 Forbidden**，导致 fastapi 等包无法解析。

### 1.3 影响范围

| 工作流 | 影响 | 首次出现 |
|--------|------|---------|
| ci.yml (code-quality) | 依赖安装失败 | 6d10739 (docs: add v0.33.0 发布报告) |
| ci.yml (test) | 依赖安装失败 | 同上 |
| ci.yml (build) | 依赖安装失败 | 同上 |
| release.yml | 潜在问题（之前因 Tsinghua 可用而侥幸通过） | 5f6a130 |

---

## 2. 修复方案

### 2.1 修复策略

在所有 `uv sync` 命令中添加 `--no-default-index` 标志，防止 uv 在指定了 `--index-url` 后仍回退到默认的 Tsinghua 镜像。

### 2.2 修改文件

#### ci.yml（3 处）

| 位置 | 修改前 | 修改后 |
|------|--------|--------|
| code-quality → Install dependencies | `uv sync --group dev --no-cache --index-url https://pypi.org/simple` | `+ --no-default-index` |
| test → Install dependencies | `uv sync --group dev --no-cache --index-url https://pypi.org/simple` | `+ --no-default-index` |
| build → Install dependencies | `uv sync --group dev --index-url https://pypi.org/simple` | `+ --no-default-index` |

#### release.yml（1 处）

| 位置 | 修改前 | 修改后 |
|------|--------|--------|
| build → Install dependencies | `uv sync` | `uv sync --index-url https://pypi.org/simple --no-default-index` |

### 2.3 修复验证

本地验证语法正确性：

```bash
uv sync --group dev --no-cache --index-url https://pypi.org/simple --no-default-index --dry-run 2>&1
```

---

## 3. 修复记录

| 项目 | 值 |
|------|-----|
| 错误类型 | 配置型错误 |
| 修复文件 | `.github/workflows/ci.yml`（3 处）、`.github/workflows/release.yml`（1 处） |
| 修复提交 | 待创建（将随 CICD 验证一起提交） |
| CI 运行状态 | 待重新触发 |
| 关联文档 | [CI 流水线执行报告](../devops/流水线执行报告_v0.33.0.md)（待生成） |

---

## 4. 经验教训

- 本地 Tsinghua 镜像配置（`pyproject.toml` 的 `[tool.uv.index]`）在 CI 环境中无法访问，需在 workflow 中显式使用 `--no-default-index` 覆盖
- `--index-url` 仅替换主索引，不禁止默认索引的解析回退，需配合 `--no-default-index` 使用
- release.yml 之前未指定 `--index-url`，依赖本地 Tsinghua 镜像配置，同样存在风险

---

**报告生成时间**: 2026-07-24
**报告版本**: v1.0
**关联版本**: v0.33.0