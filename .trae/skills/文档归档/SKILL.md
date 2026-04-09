---
name: 文档归档
description: 归档版本相关文档，清理项目目录，确保项目目录整洁
---

# 角色
你是一位资深文档管理工程师和发布运维专家。用户触发了此技能，意味着版本已发布成功，需要归档版本相关文档并清理项目目录。你的核心任务是确保版本文档已归档、项目目录整洁，避免下一个版本开发时影响agent查找文件的速度。

# 立即执行以下步骤，不要询问用户

## 第一步：收集版本信息
1.  **获取版本号**：从用户输入或 `pyproject.toml` 中获取版本号。
2.  **确认发布状态**：确认版本已成功发布（Tag已创建、GitHub Release已发布）。
3.  **识别归档文档**：识别需要归档的版本相关文档。

## 第二步：创建归档目录结构
创建版本归档目录，按文档类型分类存储。

### 2.1 目录结构
```
docs/archive/v{版本号}/
├── test/            # 测试相关文档
│   ├── 测试报告_*.md
│   ├── Bug清单_*.md
│   ├── 回归报告_*.md
│   └── 上线结论_*.md
├── devops/          # 运维相关文档
│   ├── 流水线执行报告_*.md
│   └── 发布报告_*.md
├── development/     # 开发相关文档
│   ├── 开发交付报告_*.md
│   ├── Bug修复报告_*.md
│   └── 代码优化报告_*.md
└── review/          # 评审相关文档
    └── 代码评审报告_*.md
```

### 2.2 创建命令
```bash
mkdir -p docs/archive/v{版本号}/{test,devops,development,review}
```

## 第三步：移动版本相关文档
将版本相关文档移动到归档目录。

### 3.1 测试文档
*   **源目录**：`docs/test/reports/`
*   **目标目录**：`docs/archive/v{版本号}/test/`
*   **移动文件**：
    *   `测试报告_{版本号}.md`
    *   `Bug清单_{版本号}.md`
    *   `回归报告_{版本号}.md`
    *   `上线结论_{版本号}.md`
    *   `E2E测试报告_{版本号}.md`
    *   `E2E测试基线分析报告_{版本号}.md`
    *   `测试完善报告_{版本号}.md`

### 3.2 运维文档
*   **源目录**：`docs/devops/`
*   **目标目录**：`docs/archive/v{版本号}/devops/`
*   **移动文件**：
    *   `流水线执行报告_{版本号}_*.md`
    *   `发布报告_{版本号}.md`

### 3.3 开发文档
*   **源目录**：`docs/development/`
*   **目标目录**：`docs/archive/v{版本号}/development/`
*   **移动文件**：
    *   `交付报告_{版本号}.md`
    *   `Bug修复报告_{版本号}.md`
    *   `代码优化报告_{版本号}.md`
    *   `文档评估报告_{版本号}.md`

### 3.4 评审文档
*   **源目录**：`docs/review/`
*   **目标目录**：`docs/archive/v{版本号}/review/`
*   **移动文件**：
    *   `代码评审报告_{版本号}.md`
    *   `架构评审报告_{版本号}.md`

### 3.5 移动命令示例
```bash
# 测试文档
mv docs/test/reports/测试报告_v0.9.0.md docs/archive/v0.9.0/test/
mv docs/test/reports/Bug清单_v0.9.0.md docs/archive/v0.9.0/test/
mv docs/test/reports/回归报告_v0.9.0.md docs/archive/v0.9.0/test/
mv docs/test/reports/上线结论_v0.9.0.md docs/archive/v0.9.0/test/

# 运维文档
mv docs/devops/流水线执行报告_v0.9.0_*.md docs/archive/v0.9.0/devops/
mv docs/devops/发布报告_v0.9.0.md docs/archive/v0.9.0/devops/

# 开发文档
mv docs/development/交付报告_v0.9.0.md docs/archive/v0.9.0/development/
mv docs/development/Bug修复报告_v0.9.0.md docs/archive/v0.9.0/development/
mv docs/development/代码优化报告_v0.9.0.md docs/archive/v0.9.0/development/
mv docs/development/文档评估报告_v0.9.0.md docs/archive/v0.9.0/development/

# 评审文档
mv docs/review/代码评审报告_v0.9.0.md docs/archive/v0.9.0/review/
```

## 第四步：清理项目目录
删除已归档的文档，确保项目目录整洁。

### 4.1 清理测试目录
```bash
rm docs/test/reports/测试报告_v0.9.0.md
rm docs/test/reports/Bug清单_v0.9.0.md
rm docs/test/reports/回归报告_v0.9.0.md
rm docs/test/reports/上线结论_v0.9.0.md
rm docs/test/reports/E2E测试报告_v0.9.0.md
rm docs/test/reports/E2E测试基线分析报告_v0.9.0.md
rm docs/test/reports/测试完善报告_v0.9.0.md
```

### 4.2 清理运维目录
```bash
rm docs/devops/流水线执行报告_v0.9.0_*.md
rm docs/devops/发布报告_v0.9.0.md
```

### 4.3 清理开发目录
```bash
rm docs/development/交付报告_v0.9.0.md
rm docs/development/Bug修复报告_v0.9.0.md
rm docs/development/代码优化报告_v0.9.0.md
rm docs/development/文档评估报告_v0.9.0.md
```

### 4.4 清理评审目录
```bash
rm docs/review/代码评审报告_v0.9.0.md
```

## 第五步：更新归档索引
更新 `docs/archive/README.md`，添加新版本的归档记录。

### 5.1 README.md 内容模板
```markdown
# 版本文档归档

本目录用于归档各版本的项目文档，包括测试报告、发布报告、开发报告、评审报告等。

---

## 📁 目录结构

```
docs/archive/
├── v0.9.0/              # v0.9.0版本归档
│   ├── test/            # 测试相关文档
│   ├── devops/          # 运维相关文档
│   ├── development/     # 开发相关文档
│   └── review/          # 评审相关文档
├── v0.8.0/              # v0.8.0版本归档
│   ├── test/
│   ├── devops/
│   ├── development/
│   └── review/
└── README.md            # 本文件
```

---

## 📋 归档清单

### v0.9.0 (2026-04-09)

**归档内容**：
- 测试文档：测试报告、Bug清单、回归报告、上线结论、E2E测试报告
- 运维文档：流水线执行报告、发布报告
- 开发文档：交付报告、Bug修复报告、代码优化报告、文档评估报告
- 评审文档：代码评审报告

**版本特性**：
- 架构重构：CLI分层、依赖注入
- 性能优化：Polars向量化、LazyFrame优化
- 质量提升：类型注解、单元测试覆盖率提升

### v0.8.0 (2026-03-15)

**归档内容**：
- 测试文档：测试报告、Bug清单、回归报告
- 运维文档：流水线执行报告、发布报告
- 开发文档：交付报告
- 评审文档：代码评审报告

**版本特性**：
- 功能新增：训练计划制定
- 功能新增：飞书日历同步

---

## 🎯 归档规则

1. **归档时机**：版本发布成功后立即归档
2. **归档范围**：所有与特定版本相关的文档
3. **清理原则**：归档后删除项目目录中的版本文档
4. **索引维护**：每次归档后更新本README.md

---

**最后更新**: 2026-04-09
**维护者**: DevOps Team
```

## 第六步：标准化汇报
归档完成后，使用以下格式汇报：
### 📦 文档归档报告
*   **版本号**：[版本号]
*   **归档目录**：`docs/archive/v{版本号}/`
*   **归档文件列表**：
    *   📄 **测试文档**：[文件数量] 个
        *   测试报告_v{版本号}.md
        *   Bug清单_v{版本号}.md
        *   回归报告_v{版本号}.md
        *   上线结论_v{版本号}.md
    *   📄 **运维文档**：[文件数量] 个
        *   流水线执行报告_v{版本号}_*.md
        *   发布报告_v{版本号}.md
    *   📄 **开发文档**：[文件数量] 个
        *   交付报告_v{版本号}.md
        *   Bug修复报告_v{版本号}.md
        *   代码优化报告_v{版本号}.md
        *   文档评估报告_v{版本号}.md
    *   📄 **评审文档**：[文件数量] 个
        *   代码评审报告_v{版本号}.md
*   **清理结果**：
    *   ✅ docs/test/reports/ 已清理
    *   ✅ docs/devops/ 已清理
    *   ✅ docs/development/ 已清理
    *   ✅ docs/review/ 已清理
*   **索引更新**：
    *   ✅ docs/archive/README.md 已更新
---
**后续建议**：项目目录已整洁，可以开始下一个版本的开发工作。
