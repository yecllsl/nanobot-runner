---
name: document-archive
description: Use when a version has been successfully released and version-specific documents need to be archived. Triggered to reduce IDE indexing overhead, clean workspace clutter, and preserve release artifacts.
---

# Overview

将版本发布后的相关文档归档压缩，清理工作区，减少 IDE 和 Agent 的文件扫描负担。

## When to Use

- 版本已成功发布，需要清理版本相关文档
- 项目目录文档过多，影响 IDE 索引或 Agent 查找速度
- 症状关键词：文档散乱、IDE 卡顿、Agent 文件扫描慢、版本文档未归档

## When NOT to Use

- 版本尚未发布（应先使用 solo-auto-release）
- 文档仍在频繁更新中

## Common Mistakes

| 错误 | 后果 | 修复 |
|------|------|------|
| 遗漏部分版本文档未归档 | 工作区仍然杂乱 | 使用 PowerShell 扫描命令强制检查残留 |
| 未验证压缩文件完整性就删除原目录 | 数据丢失 | 必须确认 zip 文件大小合理且可解压 |
| 将 zip 文件提交到 Git | 仓库膨胀 | 必须配置 .gitignore 排除 *.zip |

# 立即执行以下步骤，不要询问用户

## 第一步：收集版本信息
1.  **获取版本号**：从用户输入或 `pyproject.toml` 中获取版本号。
2.  **确认发布状态**：确认版本已成功发布（Tag已创建、GitHub Release已发布）。
3.  **识别归档文档**：识别需要归档的版本相关文档。

### 1.1 扫描所有版本文档（关键步骤）

**重要**：必须全面扫描所有文档目录，避免遗漏。

```bash
# Windows PowerShell - 扫描所有包含版本号的文档
Get-ChildItem -Path "docs" -Recurse -Filter "*v{版本号}*" | Select-Object FullName

# 或者扫描所有包含版本号的文档（另一种命名格式）
Get-ChildItem -Path "docs" -Recurse -Filter "*_{版本号}*" | Select-Object FullName
```

### 1.2 必须检查的文档目录

| 目录 | 文档类型 | 文件模式 |
|------|---------|---------|
| `docs/test/reports/` | 测试文档 | `测试报告_{版本号}.md`、`Bug清单.md` |
| `docs/devops/` | 运维文档 | `流水线执行报告_{版本号}_*.md`、`发布报告_{版本号}.md` |
| `docs/development/` | 开发文档 | `交付报告_{版本号}.md`、`开发交付报告_{版本号}_*.md` |
| `docs/review/` | 评审文档 | `代码评审报告_{版本号}.md` |
| `docs/planning/` | 规划文档 | `task_list_{版本号}.md` |
| `docs/architecture/` | 架构文档 | `架构设计说明书_{版本号}_*.md`、`{版本号}_*.md` |

## 第二步：创建归档目录结构
创建版本归档目录，按文档类型分类存储。

### 2.1 目录结构与创建命令
```bash
mkdir -p docs/archive/v{版本号}/{test,devops,development,review,planning,architecture}
```

| 子目录 | 存放文档类型 |
|--------|-------------|
| `test/` | 测试报告、Bug清单、回归报告、strategy |
| `devops/` | 流水线执行报告、发布报告 |
| `development/` | 交付报告、Bug修复报告、优化报告 |
| `review/` | 代码评审报告、架构评审报告 |
| `planning/` | task_list |
| `architecture/` | 架构设计、重构规划、功能分析 |

## 第三步：移动版本相关文档

| 文档类型 | 源目录 | 目标目录 | 文件模式 |
|----------|--------|----------|----------|
| 测试文档 | `docs/test/reports/` | `docs/archive/v{版本号}/test/` | `测试报告`、`Bug清单`、`回归报告`、`strategy` |
| 运维文档 | `docs/devops/` | `docs/archive/v{版本号}/devops/` | `流水线执行报告`、`发布报告` |
| 开发文档 | `docs/development/` | `docs/archive/v{版本号}/development/` | `交付报告`、`Bug修复报告`、`优化报告` |
| 评审文档 | `docs/review/` | `docs/archive/v{版本号}/review/` | `代码评审报告`、`架构评审报告` |
| 规划文档 | `docs/planning/` | `docs/archive/v{版本号}/planning/` | `task_list` |
| 架构文档 | `docs/architecture/` | `docs/archive/v{版本号}/architecture/` | `架构设计`、`重构规划`、`功能分析` |

### 移动命令示例
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

## 第四步：验证归档完整性
**重要**：移动文档后，必须验证所有版本文档都已归档，避免遗漏。

### 4.1 验证命令
```bash
# Windows PowerShell - 检查是否还有遗漏的版本文档
Get-ChildItem -Path "docs" -Recurse -Filter "*v{版本号}*" | Select-Object FullName

# 如果有输出，说明还有遗漏的文档
```

### 4.2 验证标准
- ✅ 输出为空：所有版本文档已归档
- ❌ 输出不为空：还有遗漏的文档，需要补充归档

### 4.3 常见遗漏文档
根据经验，以下文档容易遗漏：
- `docs/planning/task_list_{版本号}.md` - 任务清单
- `docs/architecture/{版本号}_*.md` - 架构设计文档
- `docs/architecture/架构设计说明书_{版本号}_*.md` - 架构设计说明书
- `docs/development/开发交付报告_{版本号}_*.md` - 开发交付报告

## 第五步：压缩归档目录
将归档目录压缩为.zip文件，减少IDE索引负担。

### 4.1 压缩命令
```bash
# Windows PowerShell
Compress-Archive -Path "docs\archive\v{版本号}" -DestinationPath "docs\archive\v{版本号}-archive.zip"

# Linux/macOS
cd docs/archive && zip -r v{版本号}-archive.zip v{版本号}/
```

### 4.2 验证压缩文件
**重要**：删除原始目录前，必须验证压缩文件是否创建成功。

```bash
# Windows PowerShell
Get-ChildItem -Path "docs\archive" | Where-Object { $_.Name -like "v{版本号}-archive.zip" }

# Linux/macOS
ls -lh docs/archive/v{版本号}-archive.zip
```

确认输出中包含`v{版本号}-archive.zip`文件，且文件大小合理（不为0字节）。

### 4.3 删除原始归档目录
压缩成功后，删除原始归档目录，减少IDE索引负担。

```bash
# Windows PowerShell
Remove-Item -Path "docs\archive\v{版本号}" -Recurse -Force

# Linux/macOS
rm -rf docs/archive/v{版本号}/
```

### 4.4 验证删除结果
```bash
# Windows PowerShell
Get-ChildItem -Path "docs\archive"

# Linux/macOS
ls -la docs/archive/
```

确认输出中：
- ✅ 包含`v{版本号}-archive.zip`文件
- ✅ 不包含`v{版本号}`目录

### 4.5 为什么删除原始目录？

删除原始目录可减少 IDE 和 Agent 的文件扫描负担，保持工作区整洁。Git 已记录历史，数据不会丢失。

---

## 第六步：更新归档索引
更新 `docs/archive/README.md`，添加新版本的归档记录。

### 5.1 更新目录结构
在 README.md 的"目录结构"部分添加新版本归档文件条目。

### 5.2 添加归档记录
在 README.md 的"归档清单"部分添加新版本记录，包含归档内容和版本特性摘要。

### 5.3 更新最后更新日期
更新 README.md 末尾的"最后更新"日期和版本特性摘要。

### 5.4 验证README.md更新
执行 `git status` 确认 `docs/archive/README.md` 出现在 modified 列表中。

---

## 第七步：配置.gitignore（首次归档时执行）
确保 `.zip` 文件不被提交到 Git 仓库。

```bash
# Windows PowerShell
"*.zip`n!README.md" | Out-File -FilePath "docs\archive\.gitignore" -Encoding utf8

# Linux/macOS
echo -e "*.zip\n!README.md" > docs/archive/.gitignore
```

---

## 第八步：提交到Git

```bash
# 添加所有变更（含删除）
git add -u

# 提交
git commit -m "docs: archive v{version} documents"

# 推送
git push origin main
```

---

## 第九步：标准化汇报
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

**相关技能**：
- **前置依赖**：solo-auto-release（版本发布成功后执行归档）
- **协同技能**：document-update（文档更新完成后方可归档）
