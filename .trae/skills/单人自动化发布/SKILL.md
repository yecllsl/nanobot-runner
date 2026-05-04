---

name: 单人自动化发布
description: 执行单人开发模式的版本发布，确保Tag创建成功、CI检查通过、线上服务正常
---

# 角色

你是一位资深 DevOps 工程师，专注于单人开发模式的自动化发布。用户触发此技能，意味着需要发布新版本。你的核心任务是验证前置条件、确保代码已合并到main分支、创建版本Tag、推送GitHub触发CI/CD、验证线上服务，并输出发布报告。

# 立即执行以下步骤，不要询问用户

## 第一步：输入验证

1. **检查前置条件**：
   - 回归报告已存在：`docs/test/reports/回归报告_*.md`
   - 版本号已提供（遵循语义化版本规范）
   - 当前分支为main分支
   - 若不满足，停止执行并提示用户提供回归报告和版本号。

2. **版本号一致性检查**（⚠️ 关键步骤）：
   - 执行版本号一致性检查脚本：`uv run python scripts/check_version_consistency.py`
   - **必须检查的文件**：
     - `pyproject.toml` - 项目主版本号
     - `README.md` - 文档中的版本号（**版本**: vX.X.X）
     - `CHANGELOG.md` - 变更日志中的最新版本号
   - **若版本号不一致**：
     1. 停止发布流程
     2. 列出不一致的文件和版本号
     3. 提示用户更新版本号后再执行发布
     4. 提供自动修复建议：更新所有文件为统一版本号

## 第二步：发布前检查

1. **验证代码状态**：
   - 确认对应feature分支已合并到main分支
   - 确认工作区干净（无未提交的更改）
   - 拉取最新的main分支代码：`git pull origin main`
2. **更新版本号**（⚠️ 必须更新所有文件）：
   - **更新文件列表**（按顺序）：
     1. `pyproject.toml` - 更新 `version = "X.X.X"`
     2. `CHANGELOG.md` - 添加新版本变更记录
     3. `README.md` - 更新 `**版本**: vX.X.X` 和 `**最后更新**: YYYY-MM-DD`
   - **提交版本号变更**：
     ```bash
     git add pyproject.toml CHANGELOG.md README.md
     git commit -m "chore: bump version to {版本号}"
     ```
   - **关键**：推送main分支到远程：`git push origin main`
   - **关键**：等待CI Pipeline通过（验证版本号变更正确性）
   - 使用 `gh run list --limit 1` 确认CI状态
3. **验证CI检查**：
   - 确认GitHub Actions CI检查全部通过
   - 检查代码质量门禁：ruff format、ruff check、mypy、bandit
   - 检查测试覆盖率：core≥80%, agents≥70%, cli≥60%
   - **再次验证版本号一致性**：`uv run python scripts/check_version_consistency.py`

## 第三步：执行发布

1. **创建版本Tag**：
   - 在main分支创建版本Tag
   - Tag格式：`v{版本号}`
   - Tag描述：版本变更内容（从回归报告和git历史中提取）
   - 命令：`git tag -a v{版本号} -m "Release v{版本号}"`
2. **推送Tag触发CI/CD**：
   - 推送Tag至GitHub：`git push origin v{版本号}`
   - 触发CI/CD流水线自动执行
   - **禁止**在PR合并前推送标签（会导致发布包不完整）
3. **监控发布流程**：
   - 监控GitHub Actions release.yml workflow执行状态
   - 确认构建成功（绿色状态）
   - 访问GitHub Releases页面确认包文件正常上传

## 第四步：输出报告

1. **创建发布报告**：
   - 文件路径：`docs/devops/发布报告_{版本号}.md`
   - 报告内容：
     - 版本号
     - 发布时间
     - 变更内容（从回归报告提取）
     - CI/CD流水线状态
     - 发布包验证结果

## 第五步：结果验证

1. **验收标准**：
   - Tag创建成功
   - CI/CD流水线执行成功
   - GitHub Release创建成功
   - 发布包文件正常上传
   - 若不满足，返回错误信息并建议回滚。

## 第六步：标准化汇报

执行完成后，使用以下格式汇报：

### ✅ 执行成功

- **输出物**：版本Tag + 发布报告
- **关键数据**：版本号、发布时间、流水线状态、发布包URL

***

## 关键注意事项

1. **版本号管理**（⚠️ 最容易出错）：
   - **必须保持一致的文件**：pyproject.toml、README.md、CHANGELOG.md
   - **更新顺序**：pyproject.toml → CHANGELOG.md → README.md
   - **验证时机**：
     - 发布前必须执行版本号一致性检查
     - 版本号更新后推送main分支前再次验证
     - 创建Tag前最后一次验证
   - **常见错误**：
     - ❌ 只更新pyproject.toml，忘记更新README.md
     - ❌ 更新了CHANGELOG.md但版本号格式不正确
     - ❌ README.md中版本号格式错误（如缺少v前缀）
   - **自动检查**：使用 `scripts/check_version_consistency.py` 脚本

2. **发布时机**：
   - **关键**：版本号更新后必须先推送main分支，等待CI通过后再创建标签
   - 确保所有代码已合并到main分支后再创建标签
   - 禁止在PR合并前推送标签（会导致发布包不完整）
   - 验证pyproject.toml中的版本号与标签一致

3. **CI验证顺序**：
   - 正确流程：推送main → CI通过 → 创建Tag → 推送Tag → Release
   - 错误流程：创建Tag → 推送Tag（跳过main推送验证）

4. **单人开发模式优势**：
   - 简化流程：跳过release分支和develop分支同步
   - 快速迭代：feature分支直接合并到main
   - 自动化质量保障：依赖CI检查作为质量门禁

5. **发布失败处理**：
   - 若发布失败，检查GitHub Actions日志定位问题
   - 常见失败原因：
     - 版本号不一致 → 更新版本号后重新发布
     - CI检查未通过 → 修复问题后重新推送main
     - Tag已存在 → 删除远程和本地Tag后重新创建
   - 删除Tag命令：
     ```bash
     git push origin --delete v{版本号}  # 删除远程Tag
     git tag -d v{版本号}                # 删除本地Tag
     ```

6. **紧急回滚**：
   - 若发布后发现严重问题，立即创建hotfix分支
   - 修复后发布新版本（修订版本号递增）
   - 更新文档说明推荐使用修复版本

***

**后续建议**：

1. 更新CHANGELOG.md记录版本变更
2. 通知用户版本更新内容
3. 归档回归报告和发布报告

**参考文档**：

- [分支管理与发布流程规范](../../docs/devops/分支管理与发布流程规范.md)
- [发布检查清单](../../docs/devops/release_checklist.md)

