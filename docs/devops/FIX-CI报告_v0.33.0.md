# FIX-CI 报告 v0.33.0

> **报告日期**: 2026-07-24
> **关联版本**: v0.33.0
> **修复类型**: 配置型错误（pyproject.toml 配置修复 + workflow 回退）

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
[[tool.uv.index]]
name = "tsinghua"
url = "https://pypi.tuna.tsinghua.edu.cn/simple"
default = true
```

该配置是本地开发便利配置，但被纳入版本控制后，在 CI 环境中：
1. CI 中虽然指定了 `--index-url https://pypi.org/simple`，但 uv 跨平台解析时仍会回退到默认索引（Tsinghua）
2. Tsinghua 镜像在 GitHub Actions runner 上返回 **403 Forbidden**
3. 导致 fastapi 等包在 darwin/macOS 平台分片上无法解析

### 1.3 首次修复尝试（失败）

首次修复（commit `a25813f`）在 ci.yml 和 release.yml 中添加 `--no-default-index`，但 CI runner 的 uv 版本不支持该参数：

```
error: unexpected argument '--no-default-index' found
tip: a similar argument exists: '--default-index'
```

### 1.4 影响范围

| 工作流 | 影响 | 首次出现 |
|--------|------|---------|
| ci.yml (code-quality) | 依赖安装失败 | 6d10739 |
| ci.yml (test) | 依赖安装失败 | 同上 |
| ci.yml (build) | 依赖安装失败 | 同上 |
| release.yml | 潜在问题 | 5f6a130 |

---

## 2. 修复方案（最终版）

### 2.1 修复策略

将 Tsinghua 镜像配置从 `pyproject.toml` 移到本地 `uv.toml`（不纳入版本控制），从根本上消除 CI 环境对本地镜像的依赖。

### 2.2 修改文件

| 文件 | 变更 | 说明 |
|------|------|------|
| `pyproject.toml` | 删除 `[[tool.uv.index]]` 段（4 行） | 移除 Tsinghua 镜像配置 |
| `uv.toml`（新建，本地） | 新增 `[[index]]` 配置 | 本地开发使用 Tsinghua 镜像 |
| `.gitignore` | 新增 `uv.toml` | 确保本地 uv.toml 不被提交 |
| `ci.yml` | 回退到原始命令 | 无需 `--no-default-index` |
| `release.yml` | 回退到原始命令 | 同上 |

### 2.3 修复后数据流

```
本地开发: pyproject.toml 无索引配置 → uv.toml 提供 Tsinghua 镜像 → 下载加速
CI 环境:  pyproject.toml 无索引配置 → 默认 PyPI → 正常下载
```

### 2.4 修复验证

本地验证 uv 仍能正确解析依赖：

```bash
uv sync --dry-run 2>&1
```

---

## 3. 修复记录

| 项目 | 值 |
|------|-----|
| 错误类型 | 配置型错误 |
| 修复文件 | `pyproject.toml`（删除 4 行）、`.gitignore`（新增 2 行）、`ci.yml`（回退 3 处）、`release.yml`（回退 1 处） |
| 新建文件 | `uv.toml`（本地） |
| 修复提交 | a25813f（首次修复失败）→ 待提交（最终修复） |
| CI 运行状态 | 待重新触发 |
| 关联文档 | [CI 流水线执行报告](../devops/流水线执行报告_v0.33.0.md)（待生成） |

---

## 4. 经验教训

- 本地开发便利配置（Tsinghua 镜像）不应纳入 `pyproject.toml` 版本控制，应使用本地 `uv.toml` 隔离
- CI 环境的 `uv` 版本可能与本地不同，使用 CLI 参数前需确认兼容性
- 修复 CI 问题时，最优方案是消除配置差异本身，而非在 workflow 中打补丁

---

**报告生成时间**: 2026-07-24
**报告版本**: v2.0
**关联版本**: v0.33.0