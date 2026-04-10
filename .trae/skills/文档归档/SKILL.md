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
│   ├── 上线结论_*.md
│   ├── E2E测试报告_*.md
│   ├── E2E测试基线分析报告_*.md
│   ├── 测试完善报告_*.md
│   └── strategy_*.md
├── devops/          # 运维相关文档
│   ├── 流水线执行报告_*.md
│   └── 发布报告_*.md
├── development/     # 开发相关文档
│   ├── 开发交付报告_*.md
│   ├── Bug修复报告_*.md
│   ├── 代码优化报告_*.md
│   └── 文档评估报告_*.md
├── review/          # 评审相关文档
│   ├── 代码评审报告_*.md
│   └── 架构评审报告_*.md
├── planning/        # 规划相关文档
│   └── task_list_*.md
└── architecture/    # 架构相关文档
    ├── 架构设计_*.md
    ├── 重构规划方案_*.md
    └── 功能分析_*.md
```

### 2.2 创建命令
```bash
mkdir -p docs/archive/v{版本号}/{test,devops,development,review,planning,architecture}
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

### 3.5 规划文档
*   **源目录**：`docs/planning/`
*   **目标目录**：`docs/archive/v{版本号}/planning/`
*   **移动文件**：
    *   `task_list_{版本号}.md`

### 3.6 架构文档
*   **源目录**：`docs/architecture/`
*   **目标目录**：`docs/archive/v{版本号}/architecture/`
*   **移动文件**：
    *   `架构设计_{版本号}.md`
    *   `重构规划方案_{版本号}.md`
    *   `功能分析_{版本号}.md`
    *   其他架构相关文档

### 3.7 移动命令示例
```bash
# 测试文档
mv docs/test/reports/测试报告_v0.9.0.md docs/archive/v0.9.0/test/
mv docs/test/reports/Bug清单_v0.9.0.md docs/archive/v0.9.0/test/
mv docs/test/reports/回归报告_v0.9.0.md docs/archive/v0.9.0/test/
mv docs/test/reports/上线结论_v0.9.0.md docs/archive/v0.9.0/test/
mv docs/test/strategy_v0.9.0.md docs/archive/v0.9.0/test/
mv docs/test/测试完善报告_v0.9.0.md docs/archive/v0.9.0/test/

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

# 规划文档
mv docs/planning/task_list_v0.9.0.md docs/archive/v0.9.0/planning/

# 架构文档
mv docs/architecture/v0.9.0重构规划方案.md docs/archive/v0.9.0/architecture/
```

## 第四步：压缩归档目录
将归档目录压缩为.zip文件，减少IDE索引负担。

### 4.1 压缩命令
```bash
# Windows PowerShell
Compress-Archive -Path "docs\archive\v{版本号}" -DestinationPath "docs\archive\v{版本号}-archive.zip"

# Linux/macOS
cd docs/archive && zip -r v{版本号}-archive.zip v{版本号}/
```

### 4.2 删除原始归档目录
压缩完成后，删除原始归档目录，减少IDE索引负担。

```bash
# Windows PowerShell
Remove-Item -Path "docs\archive\v{版本号}" -Recurse -Force

# Linux/macOS
rm -rf docs/archive/v{版本号}/
```

### 4.3 为什么删除原始目录？

**删除的好处**：
- ✅ **提高IDE效率**：减少IDE索引的文件数量，提升启动和搜索速度
- ✅ **提高Agent效率**：减少Agent扫描文件的数量，提升查找速度
- ✅ **保持工作区整洁**：避免归档文件干扰日常开发
- ✅ **不影响Git历史**：Git已记录所有文件版本，可随时恢复

**不删除的问题**：
- ❌ IDE需要索引大量归档文件，影响性能
- ❌ 文件搜索变慢，需要搜索更多文件
- ❌ Agent查找文件速度变慢
- ❌ 工作区不整洁，影响开发体验

---

## 第五步：更新归档索引
更新 `docs/archive/README.md`，添加新版本的归档记录。

### 5.1 README.md 内容模板
```markdown
# 版本文档归档

本目录用于归档各版本的项目文档索引。**注意：实际的归档文件以.zip格式保存在本地，不提交到Git仓库。**

---

## 📁 归档策略

### Git管理策略

- ✅ **Git历史记录**：所有文档的历史版本已通过Git版本控制记录
- ✅ **本地备份**：归档文件以.zip格式保存在本地，不提交到Git
- ✅ **.gitignore**：已配置排除.zip文件，避免仓库体积膨胀

### 查看历史版本

```bash
# 查看文档历史
git log --oneline docs/

# 查看特定版本的文档
git show v0.9.0:docs/

# 恢复特定版本的文档
git checkout v0.9.0 -- docs/
```

---

## 📁 目录结构

```
docs/archive/
├── .gitignore           # 排除.zip文件
├── README.md            # 本文件（归档索引）
├── v0.9.0-archive.zip   # v0.9.0版本归档（本地备份，不提交）
├── v0.8.0-archive.zip   # v0.8.0版本归档（本地备份，不提交）
└── v0.6.0-archive.zip   # v0.6.0版本归档（本地备份，不提交）
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

---

## 第六步：配置.gitignore
确保.zip文件不会被提交到Git仓库。

### 6.1 创建.gitignore文件
在`docs/archive/`目录下创建`.gitignore`文件：

```bash
# 创建.gitignore文件
cat > docs/archive/.gitignore << 'EOF'
# 归档目录的Git忽略规则
# 排除所有.zip文件
*.zip

# 但保留README.md
!README.md
EOF
```

### 6.2 提交到Git
```bash
git add docs/archive/.gitignore
git add docs/archive/README.md
git commit -m "docs: 归档v{版本号}版本文档

- 归档测试、运维、开发、评审文档
- 压缩归档目录为.zip文件
- 更新归档索引README.md
- 配置.gitignore排除.zip文件"
```

---

## 第七步：标准化汇报
归档完成后，使用以下格式汇报：
### 📦 文档归档报告
*   **版本号**：[版本号]
*   **归档文件**：`docs/archive/v{版本号}-archive.zip`（本地备份）
*   **归档内容**：
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
    *   ✅ 项目目录已清理
    *   ✅ 归档目录已压缩
    *   ✅ 原始归档目录已删除
*   **Git提交**：
    *   ✅ .gitignore已配置
    *   ✅ README.md已更新
    *   ✅ 变更已提交到Git
*   **性能优化**：
    *   ✅ IDE索引文件减少，性能提升
    *   ✅ Agent查找速度提升
    *   ✅ 工作区整洁
---
**后续建议**：项目目录已整洁，可以开始下一个版本的开发工作。
